"""Earn Relief parties and play saved support/interception orders through actual input."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d import Label
from eador.app import create_game
from eador.encounter_scene import EncounterScene
from eador.model import State
from eador.scene import BattleScene, ResultScene, ShardScene, TitleScene
from tools.audit_eador_aerie import Purchases
from tools.eador_relief_campaign import (prepare_relief, relief_forward_route, relief_western_route,
                                         relief_scout_route, relief_passive_route,
                                         relief_failed_support, relief_retry_route)
from tools.eador_ui import PlayerInput
from tools.verify_eador_control import ControlOrders
from tools.verify_eador_guidance import check_reading_layout
from tools.verify_eador_reading import check_page

PLANS = {'forward': relief_forward_route, 'western': relief_western_route,
         'scout': relief_scout_route, 'passive': relief_passive_route}


class ReliefOrders(ControlOrders):
    """Each real input has the exact public model consequence, including saved enemy Rally."""
    def __init__(self, state):
        super().__init__(state)
        before = state.to_json()
        self.player.press('o')
        assert self.player.game.scene.cursor == self.battle.objective.target
        assert state.to_json() == before
        self.player.capture('relief-deployment')

    def do(self, command, *args, **kwargs):
        expected = State.from_json(self.state.to_json())
        getattr(expected.battle, command)(*args, **kwargs)
        if command == 'auto_turn':
            self.player.press('a')
            self.orders.append((command, args, kwargs))
        else:
            super().do(command, *args, **kwargs)
        assert self.state.to_json() == expected.to_json(), command
        if command in ('end_turn', 'auto_turn'):
            self.player.capture(f'round-{self.battle.round}-{self.battle.outcome_reason or self.battle.objective.progress}')
            self.player.reload(self.state.to_json())


def inspect_briefing(player):
    before = player.state.to_json()
    player.press('x')
    assert isinstance(player.game.scene, EncounterScene)
    province = player.state.provinces[player.state.hero.pos]
    for percent in (100, 125):
        player.press('t'); player.press('left' if percent == 100 else 'right'); player.press('return')
        for index, approach in enumerate(player.game.scene.approaches):
            player.press(str(index + 1))
            scene = player.game.scene
            labels = '\n'.join(c.text for c in scene.ui.walk() if isinstance(c, Label))
            assert f'{province.site_gold} gold · {province.site_crystals}' in labels
            assert 'round 4' in labels and '2 consecutive enemy turns' in labels
            assert ("Militia clears adjacent allies' Pin." in labels) == ('militia' in province.site_guards)
            assert ('Skyrider crosses occupied cells' in labels) == ('skyrider' in province.site_guards)
            check_reading_layout(scene)
            assert player.state.to_json() == before
            player.capture(f'briefing-{approach.id}-{percent}')
    player.press('c'); player.press('5'); player.press('end')
    while not any(e.title == 'Relief Column' for e in player.game.scene.visible_entries):
        assert player.game.scene.page > 0
        player.press('left')
    check_page(player.game.scene); player.capture('codex-recorded-reward-125')
    player.press('escape'); player.press('escape')
    assert isinstance(player.game.scene, ShardScene) and player.state.to_json() == before
    player.reload(before)


def verify(output, *, backend='pyglet', plan='forward', mode='standard', seed=7):
    output.mkdir(parents=True, exist_ok=True)
    sources = sorted([*ROOT.glob('eador/*.py'), *ROOT.glob('saga2d/**/*.py'),
                      *ROOT.glob('tools/eador_*.py'), *[ROOT / 'tools' / name for name in (
                          'audit_eador_aerie.py', 'audit_eador_extraction.py', 'verify_eador_relief.py',
                          'verify_eador_control.py', 'verify_eador_extraction.py',
                          'verify_eador_guidance.py', 'verify_eador_reading.py')]])
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines()
    with TemporaryDirectory(prefix='shardbound-relief-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            hero = 'Scout' if plan == 'scout' else 'Commander'
            game.push(TitleScene(seed, hero_class=hero, difficulty=mode)); player.press('return')
            state = Purchases(player.state)
            prepare_relief(state=state)
            inspect_briefing(player)
            failure = None
            if plan == 'failed-retry':
                failed = relief_failed_support(state, orders_type=ReliefOrders)
                assert failed.battle.outcome_reason == 'deadline' and not failed.battle.unit(4).alive
                assert any('rallies Skyrider' in line for line in failed.battle.log)
                gold, crystals, xp = state.gold, state.crystals, state.hero.xp
                state.resolve_battle()
                assert (state.gold, state.crystals, state.hero.xp) == (gold - 20, crystals, xp)
                assert not state.choice and not state.provinces[state.hero.pos].explored
                province = state.provinces[state.hero.pos]
                survivors = list(zip(province.site_guards, province.site_guard_hp))
                assert survivors == [('archer', 20), ('guard', 35)]
                player.reload(state.to_json())
                price, gold = state.recruit_cost('pikeman'), state.gold
                state.recruit('pikeman')
                assert state.gold == gold - price
                assert state.hero.army[-1].id != 4 and state.hero.army[-1].level == 1
                failure = dict(reason='deadline', dead_troop_ids=[4], retreat_fee=20,
                               replacement_gold=price, surviving_guards=survivors, orders=failed.orders)
                player.output = output / 'retry'; inspect_briefing(player)
            gold, crystals, mana = state.gold, state.crystals, state.hero.mana
            play = (relief_retry_route if plan == 'failed-retry' else PLANS[plan])(state, orders_type=ReliefOrders)
            battle, reward = state.battle, state.battle_adventure
            assert isinstance(game.scene, ResultScene)
            assert battle.outcome_reason == ('rout' if plan == 'failed-retry' else 'hold')
            assert all(u.alive for u in battle.units if u.team == 'player')
            assert (state.gold, state.crystals) == (gold, crystals)
            report = dict(plan=plan, mode=mode, seed=seed, backend=backend, campaign_turn=state.turn,
                          battle_round=battle.round, outcome_reason=battle.outcome_reason,
                          mana_spent=mana-battle.mana,
                          survivors=[dict(id=u.id, kind=u.kind, hp=u.hp, max_hp=u.max_hp)
                                     for u in battle.units if u.team == 'player'],
                          living_enemies=[dict(kind=u.kind, hp=u.hp) for u in battle.units if u.team == 'enemy' and u.alive],
                          reward=dict(gold=reward.gold, crystals=reward.crystals, relic=reward.relic),
                          purchases=state.purchases, failed_attempt=failure, orders=play.orders)
            player.capture('relief-success'); player.reload(state.to_json())
            state.resolve_battle()
            assert (state.gold, state.crystals) == (gold + reward.gold, crystals + reward.crystals)
            while state.choice:
                state.choose(state.choice.options[0].id)
            assert state.provinces[state.hero.pos].explored
            before = state.to_json(); player.press('x')
            assert state.to_json() == before and isinstance(game.scene, ShardScene)
            player.reload(before)
            report.update(input_activations=len(player.events), exact_save_reloads=player.reloads,
                          inputs=player.events, source_revision=revision, dirty_at_start=dirty,
                          source_sha256=hashes)
            (output / 'final-state.json').write_text(state.to_json())
        finally:
            game._teardown(); game.backend.quit()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha for path, sha in hashes.items())
    (output / 'journey.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Relief {plan}/{mode} passed ({backend}): {report["input_activations"]} inputs, {report["exact_save_reloads"]} reloads')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', choices=[*PLANS, 'failed-retry'], default='forward')
    parser.add_argument('--mode', choices=('accessible', 'standard', 'challenge'), default='standard')
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-relief'))
    args = parser.parse_args()
    verify(args.output, backend=args.backend, plan=args.plan, mode=args.mode, seed=args.seed)
