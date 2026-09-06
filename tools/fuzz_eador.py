"""Soak Shardbound's campaign and real scene input with deterministic seeds.

    uv run python tools/fuzz_eador.py
    uv run python tools/fuzz_eador.py --seed 40 --seeds 100 --steps 250
    uv run python tools/fuzz_eador.py --campaigns 1000 --scenes 100 --events 100000 --report /tmp/eador-stress.json

Every command checks health, occupancy, ownership and save roundtrips. Scene
runs use mock-backend input and visible button bounds, including unfinished
battle saves, title/load, retreats and starting another shard after defeat.
Unexpected exceptions fail immediately; the printed seed reproduces the run.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from saga2d import Button# noqa: E402

from eador.app import create_game# noqa: E402
from eador.campaign_scene import CampaignPlanScene, CampaignScene  # noqa: E402
from eador.codex import CodexScene  # noqa: E402
from eador.encounter_scene import EncounterScene  # noqa: E402
from eador.model import BUILDINGS, HERO_CLASSES, RECRUITABLE, RuleError, State  # noqa: E402
from eador.worldgen import THEMES
from eador.rival_scene import RivalScene  # noqa: E402
from eador.settings_scene import SettingsScene  # noqa: E402
from eador.scene import (BattleScene, CatalogScene, ChoiceScene, HelpScene, HeroScene,
                         ResultScene, SaveScene, ShardScene, TitleScene)  # noqa: E402


def check_state(state: State) -> None:
    """Assert invariants that hold across player choices and balance changes."""
    hero = state.hero
    assert hero.pos in state.provinces
    assert 0 < hero.hp <= hero.max_hp
    assert 0 <= hero.mana <= hero.max_mana
    assert len(hero.army) <= hero.max_army
    assert len({t.id for t in hero.army}) == len(hero.army)
    assert len(state.inventory) == len(set(state.inventory))
    assert hero.relic is None or hero.relic in state.inventory
    assert all(0 < t.hp <= t.max_hp and 0 <= t.xp < t.level * 6 for t in hero.army)
    assert 0 <= hero.xp < hero.level * 12
    assert state.gold >= 0 and state.crystals >= 0
    assert state.rival.gold >= 0
    assert state.rival.pos in state.provinces
    assert len({troop.id for troop in state.rival.army}) == len(state.rival.army)
    assert all(0 < troop.hp <= troop.max_hp for troop in state.rival.army)
    for province in state.provinces.values():
        assert len(province.guards) == len(province.guard_hp)
        assert len(province.site_guards) == len(province.site_guard_hp)
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
        assert state.battle_kind in ('site', 'conquest', 'defense', 'intercept')
        assert state.battle_province in state.provinces
        alive = [u for u in battle.units if u.alive]
        assert len({u.pos for u in alive}) == len(alive)
        assert len({u.id for u in battle.units}) == len(battle.units)
        assert all(u.pos in battle.grid.cells and 0 <= u.hp <= u.max_hp for u in battle.units)
        assert all(type(u.pinned) is bool and 0 <= u.pin_cooldown <= 2 for u in battle.units)
        assert all(not u.pin_cooldown or u.can_pin for u in battle.units)
        assert all(u.effective_move_range == max(1, u.move_range - (2 if u.pinned else 0) - u.cargo_penalty) for u in battle.units)
        assert {u.id for u in battle.units if u.team == 'player'} == {0, *(t.id for t in hero.army)}
        assert 0 <= battle.mana <= hero.max_mana
        assert battle.outcome in (None, 'player', 'enemy')
        if battle.outcome == 'player':
            assert battle.unit(0).alive
            if battle.outcome_reason == 'escape':
                objective, carrier = battle.objective, battle.unit(battle.hero_id)
                assert state.battle_kind == 'site' and state.battle_adventure is not None
                assert objective.kind == 'extract' and battle.round <= objective.deadline
                assert carrier.pos in objective.exits and carrier.acted and carrier.moved
                assert any(u.alive and u.team == 'enemy' for u in battle.units)
                assert not any(u.alive and u.team == 'enemy' and battle.grid.distance(u.pos, carrier.pos) <= 1 for u in battle.units)
            elif battle.outcome_reason == 'hold':
                objective = battle.objective
                assert state.battle_encounter is not None and objective.kind == 'hold'
                assert objective.progress == objective.required and battle.round <= objective.deadline
                assert any(u.alive and u.team == 'player' and u.pos == objective.target for u in battle.units)
                assert not any(u.alive and u.team == 'enemy' and battle.grid.distance(u.pos, objective.target) <= 1 for u in battle.units)
                assert any(u.alive and u.team == 'enemy' for u in battle.units)
            else:
                assert battle.outcome_reason == 'rout'
                assert not any(u.alive and u.team == 'enemy' for u in battle.units)
    saved = state.to_json()
    assert State.from_json(saved).to_json() == saved, 'save roundtrip changed state'


def campaign_run(seed: int, steps: int, metrics: Counter, *, linked: bool = False) -> None:
    """Random commands include rejections, which must leave the save unchanged."""
    rng = random.Random(seed)
    theme = tuple(THEMES)[seed % len(THEMES)]
    hero_class = list(HERO_CLASSES)[seed % len(HERO_CLASSES)]
    state = State.new_campaign(seed, hero_class) if linked else State.new(seed, hero_class, theme=theme)
    if linked:
        # Start an equal share at each stage using real completed prior shards;
        # short random prefixes alone almost never discover a departure.
        from tools.eador_linked_campaign import play_stage, travel_selection
        for _ in range(seed % 3):
            state = play_stage(state)
            assert state.campaign.phase == 'departure', 'linked setup did not win its prior shard'
            state.advance(state.campaign.offers[(seed // 3) % 2].id, **travel_selection(state))
            metrics['setup_completed_shards'] += 1
        metrics[f'linked_start_stage.{state.campaign.stage}'] += 1
    theme = state.theme
    metrics[f'campaign_theme.{theme}'] += 1
    for _ in range(steps):
        check_state(state)
        metrics['state_checks'] += 1
        if state.choice:
            option = rng.choice(state.choice.options)
            restored = State.from_json(state.to_json())
            kind = state.choice.kind
            state.choose(option.id)
            restored.choose(option.id)
            assert state.to_json() == restored.to_json(), 'save changed choice consequences'
            metrics['choice_' + kind] += 1
            continue
        if state.campaign and state.campaign.phase in ('departure', 'recovery'):
            phase = state.campaign.phase
            selection = dict(troop_ids=tuple(rng.sample([t.id for t in state.hero.army], min(2, len(state.hero.army)))),
                             relic_ids=tuple(rng.sample(state.inventory, min(2, len(state.inventory)))))
            restored = State.from_json(state.to_json())
            offer = rng.choice(state.campaign.offers).id if phase == 'departure' else None
            for current in (state, restored):
                if phase == 'departure':
                    current.advance(offer, **selection)
                else:
                    current.recover(**selection)
            assert state.to_json() == restored.to_json(), 'save changed linked transition consequences'
            metrics['linked_' + phase] += 1
            continue
        if state.status != 'playing':
            break
        if state.battle:
            if state.battle.outcome:
                metrics['battle_' + state.battle.outcome] += 1
                state.resolve_battle()
            elif state.battle.objective.kind == 'extract' and rng.random() < .20:
                before = state.to_json()
                restored = State.from_json(before)
                reason = state.battle.evacuation_blocked_reason
                if reason is not None:
                    try:
                        state.battle.evacuate()
                    except RuleError as error:
                        assert str(error) == reason
                    else:
                        raise AssertionError('Evacuation ignored its blocking reason')
                    assert state.to_json() == before
                    metrics['rejected_evacuation_orders'] += 1
                else:
                    state.battle.evacuate(); restored.battle.evacuate()
                    assert state.to_json() == restored.to_json()
                    metrics['evacuation_orders'] += 1
            elif rng.random() < .20:
                battle = state.battle
                shooter = rng.choice([u for u in battle.units if u.alive and u.team == 'player'])
                target = rng.choice([u for u in battle.units if u.alive and u.team == 'enemy'])
                before = state.to_json()
                try:
                    expected = battle.pin_preview(shooter.id, target.id)
                except RuleError:
                    assert state.to_json() == before, 'rejected Pin preview mutated state'
                    try:
                        battle.pin(shooter.id, target.id)
                    except RuleError:
                        pass
                    else:
                        raise AssertionError('Pin command accepted a rejected forecast')
                    assert state.to_json() == before, 'rejected Pin mutated state'
                    metrics['rejected_pin_orders'] += 1
                else:
                    restored = State.from_json(before)
                    health = target.hp, shooter.hp
                    battle.pin(shooter.id, target.id)
                    restored.battle.pin(shooter.id, target.id)
                    assert (health[0] - target.hp, health[1] - shooter.hp) == expected
                    assert state.to_json() == restored.to_json(), 'save changed Pin consequences'
                    metrics['pin_orders'] += 1
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
        command = rng.choice(('build', 'recruit', 'travel', 'travel', 'explore', 'end_turn', 'equip'))
        before = state.to_json()
        try:
            if command == 'build':
                state.build(rng.choice(list(BUILDINGS)))
            elif command == 'recruit':
                state.recruit(rng.choice(RECRUITABLE))
            elif command == 'travel':
                state.travel(rng.choice(state.grid.neighbors(state.hero.pos)))
            elif command == 'explore':
                approaches = state.adventure_approaches()
                approach = rng.choice([None, 'missing', *(option.id for option in approaches)]) if approaches else None
                state.explore(approach=approach)
                if state.battle_adventure:
                    metrics['adventure_approach.' + state.battle_adventure.approach] += 1
            elif command == 'equip':
                state.equip(rng.choice([None, *state.inventory]))
            else:
                state.end_turn()
        except RuleError:
            assert state.to_json() == before, f'rejected {command} mutated state'
            metrics['rejected_commands'] += 1
        else:
            metrics[command] += 1
    metrics['random_phase_' + state.status] += 1
    if state.campaign:
        metrics['random_linked_phase_' + state.campaign.phase] += 1
    # A bounded random prefix is not a completed campaign. Finish every case
    # through public commands, recording these forced actions separately.
    for _ in range(160):
        check_state(state)
        metrics['state_checks'] += 1
        if state.choice:
            state.choose(rng.choice(state.choice.options).id)
            metrics['cleanup_choices'] += 1
        elif state.campaign and state.campaign.phase == 'departure':
            state.advance(state.campaign.offers[0].id)
            metrics['cleanup_linked_departures'] += 1
        elif state.campaign and state.campaign.phase == 'recovery':
            state.abandon_campaign()
            metrics['cleanup_declined_recovery'] += 1
        elif state.status != 'playing':
            metrics['completed_' + state.status] += 1
            break
        elif state.battle:
            if state.battle.outcome:
                state.resolve_battle()
            elif state.hero.pos == (-2, 0) and state.rival.defeats and state.battle_kind in ('conquest', 'intercept'):
                state.battle.auto_turn()
            else:
                state.retreat()
            metrics['cleanup_battles'] += 1
        elif state.hero.pos == (-2, 0) and state.rival.defeats and state.actions_left:
            # An opponent that learned to avoid a fortified hero will not keep
            # donating assaults. Leave the capital exposed through real play.
            destination = min(state.grid.neighbors(state.hero.pos),
                              key=lambda pos: (pos == state.rival.pos,
                                               state.provinces[pos].owner != 'player',
                                               sum(state.provinces[pos].guard_hp)))
            state.travel(destination)
            metrics['cleanup_departures'] += 1
        else:
            state.end_turn()
            metrics['cleanup_turns'] += 1
    else:
        raise AssertionError(f'seed {seed}: campaign did not end after 160 cleanup commands')


def scene_run(seed: int, steps: int, metrics: Counter, *, events: int | None = None) -> None:
    """Mix purposeful input with random clicks/keys, checking each rendered tick."""
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory(prefix='shardbound-fuzz-') as save_dir:
        game = create_game('Shardbound soak', backend='mock', resolution=(1280, 800), save_dir=Path(save_dir) / 'saves')
        random_phase = False
        history = deque(maxlen=25)

        def record(kind, detail):
            history.append((type(game.scene).__name__, kind, detail))
            metrics['input_events'] += 1
            if random_phase:
                metrics['random_input_events'] += 1
                metrics['random_' + kind] += 1

        def root():
            return next((s for s in game.scenes if isinstance(s, ShardScene)), None)

        def tick():
            game.tick(1 / 60)
            metrics['input_ticks'] += 1
            assert game.scene is not None and len(game.scenes) <= 4
            shard = root()
            if shard:
                check_state(shard.state)
                metrics['state_checks'] += 1
                battles = [s for s in game.scenes if isinstance(s, BattleScene)]
                assert bool(battles) == (shard.state.battle is not None), 'battle and scene stack disagree'
                assert all(s.root is shard for s in battles)
                results = [s for s in game.scenes if isinstance(s, ResultScene)]
                if shard.state.status != 'playing' and shard.state.choice is None:
                    if shard.state.campaign:
                        assert any(isinstance(s, CampaignScene) for s in game.scenes), 'linked campaign has no transition screen'
                    else:
                        assert len(results) == 1 and not results[0].is_battle, 'campaign ended without its result screen'
                elif shard.state.battle and shard.state.battle.outcome:
                    assert len(results) == 1 and results[0].is_battle, 'battle ended without its result screen'
                if shard.state.choice is not None:
                    assert any(isinstance(s, ChoiceScene) for s in game.scenes), 'saved choice has no decision screen'
            metrics['screen_' + type(game.scene).__name__] += 1

        def press(key):
            record('key', key)
            game.backend.inject_key(key)
            game.backend.inject_key(key, type='key_release')
            tick()

        def click(x, y):
            record('click', (round(x), round(y)))
            game.backend.inject_click(round(x), round(y))
            game.backend.inject_release(round(x), round(y))
            tick()

        def hover(x, y):
            record('hover', (round(x), round(y)))
            game.backend.inject_mouse_move(round(x), round(y))
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
                if rng.random() < .5:
                    press('t')
                else:
                    button('Retreat')
            elif roll < .40:
                press('g')
                metrics['defensive_order_inputs'] += 1
            elif roll < .45:
                shooters = [u for u in battle.units if u.team == 'player' and battle.pin_targets(u.id)]
                if shooters:
                    unit = rng.choice(shooters)
                    press('tab')  # Cancel an earlier aimed action before selecting the shooter.
                    click(*scene.grid.center(unit.pos))
                    press('p')
                    target = rng.choice(battle.pin_targets(unit.id))
                    click(*scene.grid.center(target.pos))
                    metrics['pin_inputs'] += 1
            elif roll < .5:
                press(rng.choice(('left', 'right', 'up', 'down', 'pageup', 'pagedown', 'f', '1', '2')))
                press('return')
                metrics['keyboard_tactical_inputs'] += 1
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
            press('l' if seed % 2 else 'return')
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
            assert isinstance(game.scene, SaveScene) and game.scene.return_to_title
            press('1')
            assert isinstance(game.scene, TitleScene)
            press('f9')
            assert isinstance(game.scene, BattleScene), 'title load lost the unfinished battle'
            assert root().state.to_json() == saved
            metrics['battle_save_load'] += 1
            random_phase = True
            initial_events = metrics['random_input_events']
            for _ in range(events if events is not None else steps):
                if events is not None and metrics['random_input_events'] - initial_events >= events:
                    break
                scene = game.scene
                if isinstance(scene, TitleScene):
                    press(rng.choice(('tab', 'left', 'right', 'l', 'return', 'f9', 'f6', 'o')))
                elif isinstance(scene, CampaignScene):
                    if scene.step == 'offers':
                        press(rng.choice(('1', '2', 'f5', 'f9', 'f6')))
                    elif scene.step == 'retinue':
                        press(rng.choice(('left', 'right', 'up', 'down', 'space', 'return', 'escape', 'q', 'f6')))
                    else:
                        press(rng.choice(('return', 'f5', 'f9', 'f6')))
                elif isinstance(scene, CampaignPlanScene):
                    press(rng.choice(('1', '2', '3', 'h', 'escape')))
                elif isinstance(scene, HelpScene):
                    button(rng.choice(('Save & title', 'Codex', 'Settings', 'Return to game', 'Return to game')))
                elif isinstance(scene, SettingsScene):
                    press(rng.choice(('up', 'down', 'left', 'right', 'return', 'escape')))
                elif isinstance(scene, EncounterScene):
                    press(rng.choice(('return', 'escape', 'c')))
                elif isinstance(scene, CodexScene):
                    press(rng.choice(('1', '2', '3', '4', '5', '6', 'tab', 'left', 'right', 'escape', 'escape')))
                elif isinstance(scene, RivalScene):
                    press(rng.choice(('l', 'escape', 'e')))
                elif isinstance(scene, ResultScene):
                    if rng.random() < .25:
                        press('f5')
                        saved = root().state.to_json()
                        press('f9')
                        assert isinstance(game.scene, ResultScene) and root().state.to_json() == saved
                        metrics['result_save_load'] += 1
                    else:
                        press('e')
                elif isinstance(scene, ChoiceScene):
                    roll = rng.random()
                    if roll < .15:
                        press('f5')
                        saved = root().state.to_json()
                        press('f9')
                        assert isinstance(game.scene, ChoiceScene) and root().state.to_json() == saved
                        metrics['choice_save_load'] += 1
                    elif roll < .25:
                        button('Hero & relics')
                    elif roll < .35:
                        press('f6')
                    else:
                        press(str(rng.randrange(len(scene.root.state.choice.options)) + 1))
                        metrics['choice_inputs'] += 1
                elif isinstance(scene, SaveScene):
                    roll = rng.random()
                    if roll < .25 and scene.root is not None and not scene.return_to_title:
                        button('Save slots' if scene.mode == 'load' else 'Load slots')
                    elif roll < .7:
                        press(str(rng.randrange(6) + 1))
                        metrics['save_browser_inputs'] += 1
                    elif roll < .8 and scene.mode == 'load':
                        backups = scene.ui.find_all(lambda control: isinstance(control, Button)
                                                    and control.text == 'Backup' and control.enabled)
                        if backups:
                            x, y, width, height = rng.choice(backups).bounds
                            click(x + width / 2, y + height / 2)
                            metrics['backup_inputs'] += 1
                        else:
                            press('escape')
                    else:
                        press('escape')
                elif isinstance(scene, HeroScene):
                    controls = scene.ui.find_all(lambda control: isinstance(control, Button)
                                                 and control.text == 'Equip' and control.enabled)
                    if controls and rng.random() < .4:
                        x, y, width, height = rng.choice(controls).bounds
                        click(x + width / 2, y + height / 2)
                        metrics['equip_inputs'] += 1
                    else:
                        press(rng.choice(('left', 'right', 'u', 'c', 'escape', 'escape')))
                elif isinstance(scene, CatalogScene):
                    press(rng.choice(('1', '2', '3', '4', '5', 'escape', 'escape')))
                elif rng.random() < .15:
                    roll = rng.random()
                    if roll < .4:
                        click(rng.randrange(game.width), rng.randrange(game.height))
                    elif roll < .6:
                        hover(rng.randrange(game.width), rng.randrange(game.height))
                    else:
                        press(rng.choice(('f1', 'f5', 'f9', 'f6', 'tab', 'escape', 'home', 'c')))
                elif isinstance(scene, BattleScene):
                    battle_input()
                else:
                    roll = rng.random()
                    if roll < .45:
                        destination = rng.choice(scene.grid.neighbors(scene.state.hero.pos))
                        click(*scene.grid.center(destination))
                        press('return')
                    else:
                        press(rng.choice(('x', 'e', 'e', 'b', 'r', 'f1', 'h', 'f6', 'c', 'v', 'j')))

            random_phase = False
            # Complete a real losing campaign, then use the replay control.
            # Every loop makes a turn or removes an overlay; a bound catches
            # broken rival progression or scene-stack loops instead of hanging.
            for _ in range(160):
                scene = game.scene
                if isinstance(scene, TitleScene):
                    press('return')
                elif isinstance(scene, CampaignScene):
                    if scene.phase == 'recovery':
                        press('q')
                    elif scene.step == 'offers':
                        press('1')
                    elif scene.step == 'retinue':
                        press('return')
                    else:
                        press('return')
                        press('return')
                        assert isinstance(game.scene, ShardScene) and game.scene.state.turn == 1
                        metrics['replays'] += 1
                        break
                elif isinstance(scene, (CatalogScene, HelpScene, SaveScene, HeroScene, CodexScene, RivalScene,
                                        SettingsScene, EncounterScene, CampaignPlanScene)):
                    press('escape')
                elif isinstance(scene, ChoiceScene):
                    press(str(rng.randrange(len(scene.root.state.choice.options)) + 1))
                elif isinstance(scene, ResultScene):
                    if scene.is_battle:
                        press('e')
                    else:
                        button('New shard')
                        press('return')
                        assert isinstance(game.scene, ShardScene) and game.scene.state.turn == 1
                        metrics['replays'] += 1
                        break
                elif isinstance(scene, BattleScene):
                    if scene.battle.outcome:
                        press('e')
                    elif (scene.root.state.hero.pos == (-2, 0) and scene.root.state.rival.defeats
                          and scene.root.state.battle_kind in ('conquest', 'intercept')):
                        press('a')
                    else:
                        button('Retreat')
                elif (scene.state.hero.pos == (-2, 0) and scene.state.rival.defeats
                      and scene.state.actions_left):
                    click(*scene.grid.center(scene.grid.neighbors(scene.state.hero.pos)[0]))
                    press('return')
                    metrics['cleanup_departures'] += 1
                else:
                    press('e')
            else:
                raise AssertionError(f'seed {seed}: no campaign outcome/replay in 160 input steps')
        finally:
            if sys.exc_info()[0] is not None:
                print(f'Failed scene seed {seed}; recent input: {list(history)}', file=sys.stderr, flush=True)
            game._teardown()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--seed', type=int, default=0, help='first reproducible seed')
    parser.add_argument('--seeds', type=int, default=12, help='number of campaign and scene runs')
    parser.add_argument('--steps', type=int, default=120, help='random commands per campaign and scene')
    parser.add_argument('--linked', action='store_true', help='exercise linked model campaigns (scene runs keep their current title flow)')
    parser.add_argument('--campaigns', type=int, help='model runs; defaults to --seeds')
    parser.add_argument('--scenes', type=int, help='scene runs; defaults to --seeds')
    parser.add_argument('--events', type=int, help='minimum total random input activations, excluding setup/cleanup/releases')
    parser.add_argument('--report', type=Path, help='write actual metrics and run metadata to JSON')
    args = parser.parse_args()
    if args.seeds < 1 or args.steps < 1:
        parser.error('--seeds and --steps must be positive')
    campaign_count = args.seeds if args.campaigns is None else args.campaigns
    scene_count = args.seeds if args.scenes is None else args.scenes
    if campaign_count < 0 or scene_count < 0 or not campaign_count + scene_count:
        parser.error('at least one campaign or scene run is required')
    if args.events is not None and (args.events < 1 or scene_count == 0):
        parser.error('--events must be positive and requires scene runs')
    started = time.perf_counter()
    campaigns, scenes = Counter(), Counter()
    project = Path(__file__).resolve().parents[1]
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=project, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--short'], cwd=project, text=True).splitlines()
    source_files = [*project.joinpath('eador').glob('*.py'), *project.joinpath('saga2d').rglob('*.py'), Path(__file__).resolve()]
    source_hashes = {str(path.relative_to(project)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in sorted(source_files)}
    for index, seed in enumerate(range(args.seed, args.seed + campaign_count)):
        if index % 25 == 0 or index + 1 == campaign_count:
            print(f'Campaign seed {seed} ({index + 1}/{campaign_count})', flush=True)
        try:
            campaign_run(seed, args.steps, campaigns, linked=args.linked)
        finally:
            if sys.exc_info()[0] is not None:
                print(f'Failed campaign seed {seed}', file=sys.stderr, flush=True)
    campaign_seconds = time.perf_counter() - started
    for index, seed in enumerate(range(args.seed, args.seed + scene_count)):
        print(f'Scene seed {seed} ({index + 1}/{scene_count})', flush=True)
        scene_run(seed, args.steps, scenes,
                  events=math.ceil(args.events / scene_count) if args.events is not None else None)
    print(f'Campaign metrics: {dict(sorted(campaigns.items()))}')
    print(f'Scene metrics: {dict(sorted(scenes.items()))}')
    elapsed = time.perf_counter() - started
    print(f'Passed {campaign_count} model campaigns and {scene_count} scene runs in {elapsed:.1f}s.')
    if args.report:
        report = {'revision': revision, 'linked': args.linked, 'dirty_at_start': dirty, 'seed': args.seed, 'campaigns': campaign_count,
                  'scenes': scene_count, 'steps': args.steps, 'requested_random_events': args.events,
                  'platform': platform.platform(), 'machine': platform.machine(), 'python': platform.python_version(),
                  'elapsed_seconds': elapsed, 'campaign_seconds': campaign_seconds,
                  'campaign_metrics': dict(campaigns), 'scene_metrics': dict(scenes), 'source_sha256': source_hashes,
                  'source_files_changed_during_run': [str(path.relative_to(project)) for path in sorted(source_files)
                                                     if hashlib.sha256(path.read_bytes()).hexdigest() != source_hashes[str(path.relative_to(project))]]}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        print(f'Report: {args.report}')


if __name__ == '__main__':
    main()
