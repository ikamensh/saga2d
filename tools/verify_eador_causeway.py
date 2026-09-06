"""Earn Causeway parties, inspect their source and play saved orders through actual input."""
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
from eador.scene import ResultScene, ShardScene, TitleScene
from tools.audit_eador_aerie import Purchases
from tools.eador_causeway_campaign import (prepare_causeway, causeway_focus_route,
    causeway_guard_route, causeway_scout_route, causeway_failed_attempt, causeway_retry_route)
from tools.eador_ui import PlayerInput
from tools.verify_eador_control import ControlOrders
from tools.verify_eador_guidance import check_reading_layout
from tools.verify_eador_reading import check_page

PLANS = ('focus', 'guard', 'backstop', 'infused-guard', 'scout', 'scout-heal', 'failed-retry')


class CausewayOrders(ControlOrders):
    """Check each real order against the public model, including exact active saves."""
    def do(self, command, *args, **kwargs):
        expected = State.from_json(self.state.to_json())
        getattr(expected.battle, command)(*args, **kwargs)
        super().do(command, *args, **kwargs)
        assert self.state.to_json() == expected.to_json(), command
        if command == 'guard' and args[0] == 0 and self.battle.round == 1:
            self.player.capture('carrier-anchored')
        if command == 'move' and args == (2, (-2, 0)):
            self.player.capture('occupied-push-landing')
        if command == 'attack' and self.battle.unit(args[1]).kind == 'adept' and not self.battle.unit(args[1]).alive:
            self.player.capture('caster-finished')
        if command == 'end_turn':
            self.player.capture(f'round-{self.battle.round}-{self.battle.outcome_reason or "active"}')
            self.player.reload(self.state.to_json())


def inspect_briefing(player):
    before = player.state.to_json()
    player.press('x')
    assert isinstance(player.game.scene, EncounterScene)
    province = player.state.provinces[player.state.hero.pos]
    for percent in (100, 125):
        player.press('t'); player.press('left' if percent == 100 else 'right'); player.press('return')
        scene = player.game.scene
        assert len(scene.approaches) == 1
        player.press('1')
        labels = '\n'.join(c.text for c in scene.ui.walk() if isinstance(c, Label))
        assert ('one Repulse charge' in labels) == ('adept' in province.site_guards)
        assert f'{province.site_gold} gold · {province.site_crystals}' in labels
        assert 'round 5' in labels and 'cargo slows the hero by 1' in labels
        check_reading_layout(scene)
        player.capture(f'briefing-{percent}')
        player.press('c'); player.press('5'); player.press('end')
        while not any(entry.title == 'Runebound Causeway' for entry in player.game.scene.visible_entries):
            assert player.game.scene.page > 0
            player.press('left')
        check_page(player.game.scene)
        entries = [entry for entry in player.game.scene.visible_entries if entry.title == 'Runebound Causeway']
        assert f'{province.site_gold} gold' in entries[0].facts and 'Recorded reward:' in entries[0].facts
        player.capture(f'codex-recorded-reward-{percent}')
        player.press('escape')
        assert isinstance(player.game.scene, EncounterScene)
        assert player.state.to_json() == before
    player.press('escape')
    assert isinstance(player.game.scene, ShardScene) and player.state.to_json() == before
    player.reload(before)


def verify(output, *, backend='pyglet', plan='focus'):
    output.mkdir(parents=True, exist_ok=True)
    sources = sorted([*ROOT.glob('eador/*.py'), *ROOT.glob('saga2d/**/*.py'),
                      *ROOT.glob('tools/eador_*.py'), *[ROOT / 'tools' / name for name in (
                          'audit_eador_aerie.py', 'audit_eador_extraction.py', 'verify_eador_causeway.py',
                          'verify_eador_control.py', 'verify_eador_extraction.py',
                          'verify_eador_guidance.py', 'verify_eador_reading.py')]])
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines()
    with TemporaryDirectory(prefix='shardbound-causeway-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            hero = 'Scout' if plan.startswith('scout') else 'Commander'
            mana = {'guard': 12, 'backstop': 16, 'scout-heal': 8}.get(plan, 0)
            game.push(TitleScene(7, hero_class=hero, theme='ruins')); player.press('return')
            state = Purchases(player.state)
            prepare_causeway(state=state, mana=mana)
            arrival = json.loads(state.to_json())
            infusion = None
            if plan == 'infused-guard':
                crystals, actions, before_mana, turn = state.crystals, state.actions_left, state.hero.mana, state.turn
                state.infuse()
                assert (state.crystals, state.actions_left, state.hero.mana, state.turn) == (crystals - 3, actions - 1, before_mana + 8, turn)
                infusion = dict(crystals=3, actions=1, mana=8, turn=turn)
                player.capture('paid-infusion-before-entry')
                player.reload(state.to_json())
            inspect_briefing(player)
            failure = None
            if plan == 'failed-retry':
                failed = causeway_failed_attempt(state, orders_type=CausewayOrders)
                assert failed.battle.outcome_reason == 'deadline'
                assert any('repulses' in text for text in failed.battle.log)
                gold, crystals, xp = state.gold, state.crystals, state.hero.xp
                state.resolve_battle()
                assert (state.gold, state.crystals, state.hero.xp) == (gold - 20, crystals, xp)
                assert not state.choice and not state.provinces[state.hero.pos].explored
                province = state.provinces[state.hero.pos]
                survivors = list(zip(province.site_guards, province.site_guard_hp))
                assert survivors == [('pikeman', 28), ('ranger', 22), ('guard', 28)]
                player.reload(state.to_json())
                failure = dict(reason='deadline', retreat_fee=20, surviving_guards=survivors, orders=failed.orders)
                player.output = output / 'retry'; inspect_briefing(player)
            gold, crystals, mana = state.gold, state.crystals, state.hero.mana
            if plan == 'failed-retry':
                play = causeway_retry_route(state, orders_type=CausewayOrders)
                # Recovery is ordinary campaign play; its currency change is not an entry fee.
                gold, crystals, mana = state.gold, state.crystals, state.hero.mana
            elif plan.startswith('scout'):
                play = causeway_scout_route(state, heal=plan == 'scout-heal', orders_type=CausewayOrders)
            elif plan == 'focus':
                play = causeway_focus_route(state, heal=True, orders_type=CausewayOrders)
            else:
                play = causeway_guard_route(state, backstop=plan == 'backstop', heal=True, orders_type=CausewayOrders)
            battle, reward = state.battle, state.battle_adventure
            assert isinstance(game.scene, ResultScene)
            assert battle.outcome_reason == ('rout' if plan in ('failed-retry', 'scout-heal') else 'escape')
            assert all(u.alive for u in battle.units if u.team == 'player')
            assert (state.gold, state.crystals) == (gold, crystals)
            report = dict(plan=plan, backend=backend, arrival=arrival, campaign_turn=state.turn,
                          battle_round=battle.round, outcome_reason=battle.outcome_reason,
                          mana_spent=mana - battle.mana, infusion=infusion,
                          survivors=[dict(id=u.id, kind=u.kind, hp=u.hp, max_hp=u.max_hp)
                                     for u in battle.units if u.team == 'player'],
                          living_enemies=[dict(kind=u.kind, hp=u.hp) for u in battle.units if u.team == 'enemy' and u.alive],
                          reward=dict(gold=reward.gold, crystals=reward.crystals, relic=reward.relic),
                          purchases=state.purchases, failed_attempt=failure, orders=play.orders)
            player.capture('causeway-success'); player.reload(state.to_json())
            state.resolve_battle()
            assert (state.gold, state.crystals) == (gold + reward.gold, crystals + reward.crystals)
            while state.choice:
                state.choose(state.choice.options[0].id)
            assert state.provinces[state.hero.pos].explored
            before = state.to_json(); player.press('x')
            assert state.to_json() == before and isinstance(game.scene, ShardScene)
            player.reload(before)
            report.update(input_activations=len(player.events), exact_save_reloads=player.reloads,
                          inputs=player.events, source_revision=revision, dirty_at_start=dirty, source_sha256=hashes)
            (output / 'final-state.json').write_text(state.to_json())
        finally:
            game._teardown(); game.backend.quit()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha for path, sha in hashes.items())
    (output / 'journey.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Causeway {plan} passed ({backend}): {report["input_activations"]} inputs, {report["exact_save_reloads"]} reloads')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-causeway'))
    parser.add_argument('--plan', choices=PLANS, default='focus')
    parser.add_argument('--backend', choices=('pyglet', 'mock'), default='pyglet')
    args = parser.parse_args()
    verify(args.output, backend=args.backend, plan=args.plan)
