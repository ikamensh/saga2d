"""Earn, equip and use active relics in later battles through the shipped controls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['SAGA2D_SILENT'] = '1'

from eador.app import create_game
from eador.scene import ResultScene, TitleScene
from tools.eador_relic_campaign import censer_watch_route, prepare_censer_watch
from tools.eador_ui import PlayerInput
from tools.verify_eador_control import ControlOrders


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'),
                      *[ROOT / 'tools' / name for name in ('eador_campaign.py', 'eador_extraction_campaign.py',
                          'eador_relic_campaign.py', 'eador_ui.py', 'verify_eador_control.py',
                          'verify_eador_extraction.py', 'verify_eador_relics.py')]])
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    with TemporaryDirectory(prefix='shardbound-earned-relic-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            game.push(TitleScene(7))
            player.press('return')
            state = prepare_censer_watch(player.state, orders_type=ControlOrders, ranger=True)
            assert state.hero.relic == 'veil_censer' and state.battle.unit(0).abilities == ('smoke',)
            play = censer_watch_route(state, orders_type=ControlOrders)
            assert isinstance(game.scene, ResultScene)
            assert play.battle.outcome_reason == 'hold'
            assert all(u.alive for u in play.battle.units if u.team == 'player')
            assert any(u.alive for u in play.battle.units if u.team == 'enemy')
            assert play.battle.unit(0).spent_abilities == ('smoke',)
            player.capture('earned-censer-hold')
            player.reload(state.to_json())
            report = dict(relic='veil_censer', backend=backend, source_revision=revision,
                          source_sha256=hashes, platform=platform.platform(),
                          outcome_reason=play.battle.outcome_reason, battle_rounds=play.battle.round,
                          input_activations=len(player.events), exact_save_reloads=player.reloads,
                          orders=play.orders, inputs=player.events)
            province = state.provinces[state.hero.pos]
            gold, crystals = state.gold, state.crystals
            state.resolve_battle()
            assert state.gold == gold + province.site_gold and state.crystals == crystals + province.site_crystals
            while state.choice:
                state.choose(state.choice.options[0].id)
            assert province.explored
            player.reload(state.to_json())
            report.update(input_activations=len(player.events), exact_save_reloads=player.reloads,
                          inputs=player.events)
            assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
                       for name, digest in hashes.items()), 'Sources changed during the journey'
            (output / 'journey.json').write_text(json.dumps(report, indent=2) + '\n')
            print(f"Earned Censer: hold round {report['battle_rounds']}, {len(player.events)} inputs, "
                  f"{player.reloads} exact reloads ({backend})", flush=True)
            return report
        finally:
            game._teardown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-earned-relic'))
    verify(parser.parse_args().output)
