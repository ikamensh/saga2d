"""Purchase the Observatory formation and complete its hold through visible saved orders."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.app import create_game
from eador.scene import BattleScene, ChoiceScene, ResultScene, TitleScene
from tools.eador_sources import source_name
from tools.audit_eador_extraction import PaidState
from tools.eador_observatory_campaign import prepare_observatory, observatory_route, observatory_rune_route
from tools.eador_ui import PlayerInput
from tools.verify_eador_control import ControlOrders


def verify(output, *, backend='pyglet', approach='clear', support='sapper'):
    route = {'sapper': observatory_route, 'adept': observatory_rune_route}[support]
    output.mkdir(parents=True, exist_ok=True)
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'),
                      *[ROOT / 'tools' / name for name in ('eador_campaign.py', 'eador_roles_campaign.py',
                          'eador_extraction_campaign.py', 'eador_control_campaign.py', 'eador_observatory_campaign.py',
                          'audit_eador_extraction.py', 'eador_ui.py', 'verify_eador_control.py',
                          'verify_eador_extraction.py', 'verify_eador_observatory.py')]])
    hashes = {source_name(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    with TemporaryDirectory(prefix='shardbound-observatory-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            game.push(TitleScene(7, theme='ruins'))
            player.press('return')
            state = PaidState(player.state)
            prepare_observatory(state, support=support)
            gold, crystals = state.gold, state.crystals
            selected = next(choice for choice in state.adventure_approaches() if choice.id == approach)
            play = route(state, approach, orders_type=ControlOrders)
            battle, reward = state.battle, state.battle_adventure
            assert battle.outcome_reason == 'hold' and isinstance(game.scene, ResultScene)
            assert all(u.alive for u in battle.units if u.team == 'player')
            assert any(u.alive for u in battle.units if u.team == 'enemy')
            assert state.gold == gold - selected.gold_cost and state.crystals == crystals - selected.crystals_cost
            player.capture('observatory-hold-victory')
            player.reload(state.to_json())
            battle = state.battle
            survivors = [dict(kind=u.kind, hp=u.hp, max_hp=u.max_hp) for u in battle.units if u.team == 'player']
            report = dict(support=support, approach=approach, backend=backend, source_revision=revision,
                          source_sha256=hashes, platform=platform.platform(),
                          outcome_reason=battle.outcome_reason, campaign_turn=state.turn, battle_rounds=battle.round,
                          fee_gold=selected.gold_cost, fee_crystals=selected.crystals_cost,
                          building_gold=state.building_gold, recruitment_gold=state.recruitment_gold,
                          reward_gold=reward.gold, reward_crystals=reward.crystals, reward_relic=reward.relic,
                          mana_spent=state.hero.mana - battle.mana, troops_lost=0, survivors=survivors,
                          hp_deficit=sum(u['max_hp'] - u['hp'] for u in survivors))
            gold, crystals, pos = state.gold, state.crystals, state.hero.pos
            state.resolve_battle()
            assert state.gold == gold + reward.gold and state.crystals == crystals + reward.crystals
            while isinstance(game.scene, ChoiceScene):
                player.press('1')
            assert state.provinces[pos].explored and reward.relic in state.inventory
            before = state.to_json()
            player.press('x')
            assert state.to_json() == before and not isinstance(game.scene, BattleScene)
            player.reload(before)
            report.update(input_activations=len(player.events), exact_save_reloads=player.reloads,
                          orders=play.orders, inputs=player.events)
            assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
                       for name, digest in hashes.items()), 'Sources changed during the journey'
            (output / 'journey.json').write_text(json.dumps(report, indent=2) + '\n')
            print(f'Observatory/{support}/{approach}: hold round {report["battle_rounds"]}, {len(player.events)} inputs, '
                  f'{player.reloads} exact reloads ({backend})', flush=True)
            return report
        finally:
            game._teardown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-observatory'))
    parser.add_argument('--plan', choices=('sapper-clear', 'adept-covered', 'adept-clear'), default='sapper-clear')
    args = parser.parse_args()
    support, approach = args.plan.split('-')
    verify(args.output, support=support, approach=approach)
