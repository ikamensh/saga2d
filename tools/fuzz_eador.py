"""Soak Shardbound's campaign and real scene input with deterministic seeds.

    uv run python tools/fuzz_eador.py
    uv run python tools/fuzz_eador.py --seed 40 --seeds 100 --steps 250

Every command checks health, occupancy, ownership and save roundtrips. Scene
runs use mock-backend input and visible button bounds, including unfinished
battle saves, title/load, retreats and starting another shard after defeat.
Unexpected exceptions fail immediately; the printed seed reproduces the run.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import random
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from saga2d import Button, Game  # noqa: E402
from eador.model import BUILDINGS, HERO_CLASSES, RECRUITABLE, RuleError, State  # noqa: E402
from eador.scene import BattleScene, CatalogScene, HelpScene, ShardScene, TitleScene  # noqa: E402


def check_state(state: State) -> None:
    """Assert invariants that hold across player choices and balance changes."""
    hero = state.hero
    assert hero.pos in state.provinces
    assert 0 < hero.hp <= hero.max_hp
    assert 0 <= hero.mana <= hero.max_mana
    assert len(hero.army) <= hero.max_army
    assert len({t.id for t in hero.army}) == len(hero.army)
    assert all(0 < t.hp <= t.max_hp and 0 <= t.xp < t.level * 6 for t in hero.army)
    assert 0 <= hero.xp < hero.level * 12
    assert state.gold >= 0 and state.crystals >= 0
    assert 0 <= state.actions_left <= (3 if hero.hero_class == 'Scout' else 2)
    assert all(pos == p.pos and p.owner in ('player', 'neutral', 'rival')
               for pos, p in state.provinces.items())
    assert state.status in ('playing', 'victory', 'defeat')
    if state.status == 'victory':
        assert state.provinces[(2, 0)].owner == 'player'
    elif state.status == 'defeat':
        assert state.provinces[(-2, 0)].owner == 'rival'
    if state.battle is None:
        assert state.battle_kind is None and state.battle_province is None
    else:
        battle = state.battle
        assert state.battle_kind in ('site', 'conquest', 'defense')
        assert state.battle_province in state.provinces
        alive = [u for u in battle.units if u.alive]
        assert len({u.pos for u in alive}) == len(alive)
        assert len({u.id for u in battle.units}) == len(battle.units)
        assert all(u.pos in battle.grid.cells and 0 <= u.hp <= u.max_hp for u in battle.units)
        assert {u.id for u in battle.units if u.team == 'player'} == {0, *(t.id for t in hero.army)}
        assert 0 <= battle.mana <= hero.max_mana
        assert battle.outcome in (None, 'player', 'enemy')
        if battle.outcome == 'player':
            assert battle.unit(0).alive and not any(u.alive and u.team == 'enemy' for u in battle.units)
    saved = state.to_json()
    assert State.from_json(saved).to_json() == saved, 'save roundtrip changed state'


def campaign_run(seed: int, steps: int, metrics: Counter) -> None:
    """Random commands include rejections, which must leave the save unchanged."""
    rng = random.Random(seed)
    state = State.new(seed, list(HERO_CLASSES)[seed % len(HERO_CLASSES)])
    for _ in range(steps):
        check_state(state)
        if state.status != 'playing':
            break
        if state.battle:
            if state.battle.outcome:
                metrics['battle_' + state.battle.outcome] += 1
                state.resolve_battle()
            elif rng.random() < .06:
                state.retreat()
                metrics['retreats'] += 1
            else:
                # Continue both copies through the same real AI, including flags
                # for movement, retaliation and spell actions saved mid-battle.
                restored = State.from_json(state.to_json())
                state.battle.auto_turn()
                restored.battle.auto_turn()
                assert state.to_json() == restored.to_json(), 'save changed battle continuation'
                metrics['battle_rounds'] += 1
            continue
        command = rng.choice(('build', 'recruit', 'travel', 'travel', 'explore', 'end_turn'))
        before = state.to_json()
        try:
            if command == 'build':
                state.build(rng.choice(list(BUILDINGS)))
            elif command == 'recruit':
                state.recruit(rng.choice(RECRUITABLE))
            elif command == 'travel':
                state.travel(rng.choice(state.grid.neighbors(state.hero.pos)))
            elif command == 'explore':
                state.explore()
            else:
                state.end_turn()
        except RuleError:
            assert state.to_json() == before, f'rejected {command} mutated state'
            metrics['rejected_commands'] += 1
        else:
            metrics[command] += 1
    check_state(state)
    metrics['campaign_' + state.status] += 1


def scene_run(seed: int, steps: int, metrics: Counter) -> None:
    """Mix purposeful input with random clicks/keys, checking each rendered tick."""
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory(prefix='shardbound-fuzz-') as save_dir:
        game = Game('Shardbound soak', backend='mock', resolution=(1280, 800), save_dir=save_dir)

        def root():
            return next((s for s in game.scenes if isinstance(s, ShardScene)), None)

        def tick():
            game.tick(1 / 60)
            metrics['input_ticks'] += 1
            assert game.scene is not None and len(game.scenes) <= 3
            shard = root()
            if shard:
                check_state(shard.state)
                battles = [s for s in game.scenes if isinstance(s, BattleScene)]
                assert bool(battles) == (shard.state.battle is not None), 'battle and scene stack disagree'
                assert all(s.root is shard for s in battles)
            metrics['screen_' + type(game.scene).__name__] += 1

        def press(key):
            game.backend.inject_key(key)
            tick()

        def click(x, y):
            game.backend.inject_click(round(x), round(y))
            tick()

        def button(label):
            control = game.scene.ui.find(lambda child: isinstance(child, Button) and child.text == label)
            assert control is not None, f'{type(game.scene).__name__} has no {label!r} button'
            x, y, width, height = control.bounds
            click(x + width / 2, y + height / 2)

        def battle_input():
            scene = game.scene
            battle = scene.battle
            if battle.outcome:
                press('e')
                return
            roll = rng.random()
            if roll < .16:
                press('a')
            elif roll < .28:
                press('e')
            elif roll < .34:
                button('Retreat')
            else:
                players = [u for u in battle.units if u.team == 'player' and u.alive]
                unit = rng.choice(players)
                # Tab also cancels any spell left selected by unrelated input.
                press('tab')
                click(*scene.grid.center(unit.pos))
                if roll > .8 and battle.spells:
                    spell = rng.choice(sorted(battle.spells))
                    press('1' if spell == 'bolt' else '2')
                    candidates = [u for u in battle.units if u.alive
                                  and (u.team == 'enemy' if spell == 'bolt' else u.team == 'player')]
                    if candidates:
                        click(*scene.grid.center(rng.choice(candidates).pos))
                    metrics['spell_inputs'] += 1
                elif battle.targets(unit.id):
                    click(*scene.grid.center(rng.choice(battle.targets(unit.id)).pos))
                    metrics['attack_inputs'] += 1
                elif battle.reachable(unit.id):
                    click(*scene.grid.center(rng.choice(sorted(battle.reachable(unit.id)))))
                    metrics['move_inputs'] += 1

        try:
            game.push(TitleScene(seed))
            tick()
            for _ in range(seed % len(HERO_CLASSES)):
                press('tab')
            press('return')
            press('b')
            press('1')
            press('escape')
            press('r')
            press('2')
            press('escape')
            press('x')
            assert isinstance(game.scene, BattleScene)
            press('f5')
            saved = root().state.to_json()
            press('a')
            press('f9')
            assert root().state.to_json() == saved, 'battle F9 did not restore F5'
            press('f1')
            button('Save & title')
            assert isinstance(game.scene, TitleScene)
            press('f9')
            assert isinstance(game.scene, BattleScene), 'title load lost the unfinished battle'
            assert root().state.to_json() == saved
            metrics['battle_save_load'] += 1
            for _ in range(steps):
                scene = game.scene
                if isinstance(scene, TitleScene):
                    press(rng.choice(('tab', 'return', 'f9')))
                elif isinstance(scene, HelpScene):
                    button('Save & title' if rng.random() < .2 else 'Return to game')
                elif isinstance(scene, CatalogScene):
                    press(rng.choice(('1', '2', '3', '4', '5', 'escape', 'escape')))
                elif rng.random() < .15:
                    if rng.random() < .5:
                        click(rng.randrange(game.width), rng.randrange(game.height))
                    else:
                        press(rng.choice(('f1', 'f5', 'f9', 'tab', 'escape', 'home')))
                elif isinstance(scene, BattleScene):
                    battle_input()
                elif scene.state.status != 'playing':
                    button('New shard')
                else:
                    roll = rng.random()
                    if roll < .45:
                        destination = rng.choice(scene.grid.neighbors(scene.state.hero.pos))
                        click(*scene.grid.center(destination))
                        press('return')
                    else:
                        press(rng.choice(('x', 'e', 'e', 'b', 'r', 'f1')))

            # Complete a real losing campaign, then use the replay control.
            # Every loop makes a turn or removes an overlay; a bound catches
            # broken rival progression or scene-stack loops instead of hanging.
            for _ in range(160):
                scene = game.scene
                if isinstance(scene, TitleScene):
                    press('return')
                elif isinstance(scene, (CatalogScene, HelpScene)):
                    press('escape')
                elif isinstance(scene, BattleScene):
                    if scene.battle.outcome:
                        press('e')
                    else:
                        button('Retreat')
                elif scene.state.status != 'playing':
                    button('New shard')
                    press('return')
                    assert isinstance(game.scene, ShardScene) and game.scene.state.turn == 1
                    metrics['replays'] += 1
                    break
                else:
                    press('e')
            else:
                raise AssertionError(f'seed {seed}: no campaign outcome/replay in 160 input steps')
        finally:
            game._teardown()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--seed', type=int, default=0, help='first reproducible seed')
    parser.add_argument('--seeds', type=int, default=12, help='number of campaign and scene runs')
    parser.add_argument('--steps', type=int, default=120, help='random commands per campaign and scene')
    args = parser.parse_args()
    if args.seeds < 1 or args.steps < 1:
        parser.error('--seeds and --steps must be positive')
    started = time.perf_counter()
    campaigns, scenes = Counter(), Counter()
    for seed in range(args.seed, args.seed + args.seeds):
        print(f'Seed {seed}: campaign + scene', flush=True)
        campaign_run(seed, args.steps, campaigns)
        scene_run(seed, args.steps, scenes)
    print(f'Campaign metrics: {dict(sorted(campaigns.items()))}')
    print(f'Scene metrics: {dict(sorted(scenes.items()))}')
    print(f'Passed {args.seeds} seeds in {time.perf_counter() - started:.1f}s.')


if __name__ == '__main__':
    main()
