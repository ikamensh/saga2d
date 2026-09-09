"""Buy either Hunt army and rout the pack through visible orders, saves and entry choices."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.app import create_game
from eador.scene import BattleScene, ChoiceScene, ResultScene, TitleScene
from tools.eador_sources import source_name
from tools.audit_eador_extraction import PaidState
from tools.eador_hunt_campaign import prepare_pack_hunt, hunt_route, prepare_hunt_spears, spear_hunt_route
from tools.eador_ui import PlayerInput
from tools.verify_eador_extraction import PlayerOrders


class HuntOrders(PlayerOrders):
    def do(self, command, *args, **kwargs):
        super().do(command, *args, **kwargs)
        if command == 'end_turn' and isinstance(self.player.game.scene, BattleScene):
            self.player.capture(f'round-{self.battle.round}-after-enemies')


def verify(output, *, backend='pyglet', plan='compact'):
    output.mkdir(parents=True, exist_ok=True)
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'),
                      *[ROOT / 'tools' / name for name in (
                          'eador_campaign.py', 'eador_extraction_campaign.py', 'audit_eador_extraction.py',
                          'eador_ui.py', 'eador_hunt_campaign.py', 'verify_eador_extraction.py', 'verify_eador_pack_hunt.py')]])
    hashes = {source_name(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines()
    started = time.perf_counter()
    hero = 'Warrior' if plan == 'spears' else 'Commander'
    approach = 'lure' if plan == 'lure' else 'compact'
    with TemporaryDirectory(prefix='shardbound-hunt-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            game.push(TitleScene(7, hero_class=hero, theme='elderwild'))
            player.press('return')
            state = PaidState(player.state)
            (prepare_hunt_spears if plan == 'spears' else prepare_pack_hunt)(state=state)
            gold, crystals = state.gold, state.crystals
            selected = next(choice for choice in state.adventure_approaches() if choice.id == approach)
            play = (spear_hunt_route(state, orders_type=HuntOrders) if plan == 'spears'
                    else hunt_route(state, approach, orders_type=HuntOrders))
            battle, reward = state.battle, state.battle_adventure
            assert battle.outcome_reason == 'rout' and isinstance(game.scene, ResultScene)
            assert not any(u.alive for u in battle.units if u.team == 'enemy')
            assert all(u.alive for u in battle.units if u.team == 'player')
            assert state.gold == gold - selected.gold_cost and state.crystals == crystals - selected.crystals_cost
            player.capture('rout-victory')
            player.reload(state.to_json())
            battle = state.battle
            rows = [dict(kind=u.kind, hp=u.hp, max_hp=u.max_hp) for u in battle.units if u.team == 'player']
            report = dict(theme='elderwild', plan=plan, approach=approach, hero=hero, backend=backend,
                          logical_resolution=game.resolution, campaign_turn=state.turn, battle_rounds=battle.round,
                          fee_gold=selected.gold_cost, fee_crystals=selected.crystals_cost,
                          building_gold=state.building_gold, recruitment_gold=state.recruitment_gold,
                          reward_gold=reward.gold, reward_crystals=reward.crystals, reward_relic=reward.relic,
                          mana_spent=state.hero.mana - battle.mana, survivors=rows, troops_lost=0,
                          remaining_hp_deficit=sum(row['max_hp'] - row['hp'] for row in rows))
            before_gold, before_crystals, pos = state.gold, state.crystals, state.hero.pos
            state.resolve_battle()
            assert state.gold == before_gold + reward.gold and state.crystals == before_crystals + reward.crystals
            while isinstance(game.scene, ChoiceScene):
                player.press('1')
            assert state.provinces[pos].explored and reward.relic in state.inventory
            before = state.to_json()
            player.press('x')
            assert state.to_json() == before and not isinstance(game.scene, BattleScene)
            changed = [str(p.relative_to(ROOT)) for p in sources
                       if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))]]
            assert not changed
            report.update(input_activations=len(player.events), exact_save_reloads=player.reloads,
                          orders=play.orders, inputs=player.events, revision=revision, dirty_at_start=dirty,
                          source_sha256=hashes, source_files_changed=changed,
                          elapsed_seconds=time.perf_counter() - started,
                          python=platform.python_version(), platform=platform.platform())
            (output / 'journey.json').write_text(json.dumps(report, indent=2) + '\n')
            print(f'Hunt/{plan}: rout round {report["battle_rounds"]}, {len(player.events)} inputs, '
                  f'{player.reloads} exact reloads ({backend})', flush=True)
            return report
        finally:
            game._teardown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-pack-hunt'))
    parser.add_argument('--plan', choices=('compact', 'lure', 'spears'), default='compact')
    args = parser.parse_args()
    verify(args.output, plan=args.plan)
