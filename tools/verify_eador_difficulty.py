"""Select three realm modes, purchase a wounded army, inspect forecasts and restart exact saves."""
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
from eador.difficulty import DIFFICULTIES
from eador.scene import TitleScene
from tools.eador_campaign import finish_battle
from tools.eador_ui import PlayerInput


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'),
                      *[ROOT / 'tools' / name for name in ('eador_campaign.py', 'eador_ui.py',
                          'verify_eador_difficulty.py', 'verify_eador_campaign.py', 'eador_linked_campaign.py')]])
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    report = dict(source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, backend=backend, platform=platform.platform(), modes=[])
    for index, (mode, rules) in enumerate(DIFFICULTIES.items()):
        with TemporaryDirectory(prefix='shardbound-difficulty-') as directory:
            saves = Path(directory) / 'saves'
            game = create_game(backend=backend, visible=False, save_dir=saves)
            player = PlayerInput(game, native=backend == 'pyglet', output=output / mode)
            try:
                game.push(TitleScene(7, hero_class='Wizard'))
                player.press(str(index + 1))
                player.capture('selected-title')
                player.press('return')
                state = player.state
                assert state.rules is rules
                assert (state.gold, state.crystals) == (rules.starting_gold, rules.starting_crystals)
                row = dict(mode=mode, rules_id=state.rules_id, opening_gold=state.gold,
                           opening_crystals=state.crystals, opening_warning=state.rival.turns_until_action)
                state.build('temple')
                for _ in range(8):
                    if state.gold >= state.recruit_cost('healer'):
                        break
                    state.end_turn()
                    if state.battle:
                        finish_battle(state)
                    assert state.status == 'playing'
                row['support_purchase_turn'] = state.turn
                state.recruit('healer'); state.explore()
                finish_battle(state)
                before = state.to_json()
                forecast = state.recovery_preview()
                hp, mana = state.hero.hp, state.hero.mana
                assert forecast.hero_hp > 0 or forecast.mana > 0
                player.press('h'); player.capture('paid-army-recovery'); player.press('escape')
                player.press('v'); player.capture('finite-rival-warning'); player.press('escape')
                assert state.to_json() == before
                state.end_turn()
                assert state.hero.hp == hp + forecast.hero_hp and state.hero.mana == mana + forecast.mana
                player.capture('realm-after-recovery')
                expected = state.to_json()
                player.reload(expected)
                player.press('f6'); player.capture('saved-mode'); player.press('escape')
                player.press('f1'); player.press('s'); player.press('1')
                player.button('Challenge' if mode != 'challenge' else 'Accessible')
                player.press('f9')
                assert state.to_json() == expected
                row.update(recovery=dict(hero_hp=forecast.hero_hp, troop_hp_ceiling=forecast.army_hp, mana=forecast.mana),
                           input_activations=len(player.events), exact_save_reloads=player.reloads,
                           window_size=game.window_size, inputs=player.events)
            finally:
                game._teardown()
            # A fresh Game uses the same real file, independent of the title's next-run choice.
            restarted = create_game(backend=backend, visible=False, save_dir=saves)
            player = PlayerInput(restarted, native=backend == 'pyglet', output=output / mode)
            try:
                restarted.push(TitleScene(99, difficulty='challenge' if mode != 'challenge' else 'accessible'))
                player.press('f9')
                assert player.state.to_json() == expected and player.state.rules is rules
                player.capture('restarted-warning')
                row['restart_inputs'] = player.events
                row['input_activations'] += len(player.events)
                row['fresh_game_restarts'] = 1
            finally:
                restarted._teardown()
            report['modes'].append(row)
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in hashes.items())
    (output / 'journey.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Three difficulty openings, paid-army forecasts and exact fresh-game restarts passed ({backend}).', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-difficulty'))
    verify(parser.parse_args().output)
