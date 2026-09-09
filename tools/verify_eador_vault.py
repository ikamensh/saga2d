"""Buy the same army and manually escape either Vault approach through native controls."""
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
from eador.scene import BattleScene, ChoiceScene, TitleScene
from tools.eador_sources import source_name
from tools.eador_ui import PlayerInput
from tools.eador_vault_campaign import prepare_vault, vault_route
from tools.verify_eador_extraction import PlayerOrders


def verify(output, *, backend='pyglet', approach='crossfire'):
    output.mkdir(parents=True, exist_ok=True)
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'),
                      *[ROOT / 'tools' / name for name in (
                          'eador_campaign.py', 'eador_extraction_campaign.py', 'eador_ui.py',
                          'eador_vault_campaign.py', 'verify_eador_extraction.py', 'verify_eador_vault.py')]])
    hashes = {source_name(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines()
    started = time.perf_counter()
    with TemporaryDirectory(prefix='shardbound-vault-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            game.push(TitleScene(7, theme='ruins'))
            player.press('return')
            state = prepare_vault(state=player.state)
            gold, crystals, mana = state.gold, state.crystals, state.hero.mana
            selected = next(choice for choice in state.adventure_approaches() if choice.id == approach)
            # PlayerState compares and cancels the selected briefing before accepting it.
            # PlayerOrders also checks disabled evacuation, exit cycling and exact reloads.
            play = vault_route(state, approach, orders_type=PlayerOrders)
            battle, reward = state.battle, state.battle_adventure
            assert battle.outcome_reason == 'escape'
            assert any(u.alive and u.team == 'enemy' for u in battle.units)
            assert all(u.alive for u in battle.units if u.team == 'player')
            assert state.gold == gold - selected.gold_cost
            assert state.crystals == crystals - selected.crystals_cost
            rounds, destination = battle.round, state.hero.pos
            survivors = [dict(team=u.team, kind=u.kind, hp=u.hp, max_hp=u.max_hp) for u in battle.units if u.alive]
            mana_spent = mana - battle.mana
            before_gold, before_crystals = state.gold, state.crystals
            state.resolve_battle()
            assert state.gold == before_gold + reward.gold and state.crystals == before_crystals + reward.crystals
            while isinstance(game.scene, ChoiceScene):
                player.press('1')
            assert state.provinces[destination].explored
            assert reward.relic in state.inventory
            before = state.to_json()
            player.press('x')
            assert state.to_json() == before and not isinstance(game.scene, BattleScene)
            report = dict(theme='ruins', approach=approach, hero='Commander', backend=backend,
                          battle_rounds=rounds, fee_gold=selected.gold_cost, fee_crystals=selected.crystals_cost,
                          reward_gold=reward.gold, reward_crystals=reward.crystals, reward_relic=reward.relic,
                          mana_spent=mana_spent,
                          survivors=survivors, input_activations=len(player.events), exact_save_reloads=player.reloads,
                          orders=play.orders, inputs=player.events)
            changed = [str(p.relative_to(ROOT)) for p in sources
                       if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))]]
            assert not changed
            report.update(revision=revision, dirty_at_start=dirty, source_sha256=hashes,
                          source_files_changed=changed, elapsed_seconds=time.perf_counter() - started,
                          python=platform.python_version(), platform=platform.platform())
            (output / 'journey.json').write_text(json.dumps(report, indent=2) + '\n')
            print(f'Vault/{approach}: escaped in round {rounds}, {len(player.events)} inputs, '
                  f'{player.reloads} exact reloads ({backend})', flush=True)
            return report
        finally:
            game._teardown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-vault'))
    parser.add_argument('--approach', choices=('crossfire', 'unseal'), default='crossfire')
    args = parser.parse_args()
    verify(args.output, approach=args.approach)
