"""Useful evacuation guidance follows a paid Warden's actual delivery order."""
import gzip
import hashlib
import json
from pathlib import Path

from saga2d import Button
from eador.app import create_game
from eador.model import State
from eador.scene import BattleScene, ResultScene, ShardScene
from tools.eador_ui import PlayerInput


JOURNAL = Path(__file__).resolve().parents[2] / 'docs/evidence/adventure-variety/route-seed5.json.gz'
JOURNAL_SHA256 = 'cdccd3ef5ae9750098d371b6c31de7c97196aaa4091c2b7f56bebe564ccda846'


def earned_commands():
    data = JOURNAL.read_bytes()
    assert hashlib.sha256(data).hexdigest() == JOURNAL_SHA256
    return json.loads(gzip.decompress(data))['commands']


def test_ready_evacuation_takes_priority_over_the_spent_wardens_default_hint(tmp_path):
    """A legal Swap keeps Warden spent, advertises V, and escapes exactly after save/load."""
    commands = earned_commands()
    swap = commands[102]
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    player = PlayerInput(game)
    try:
        game.push(ShardScene(State.from_json(swap['before'])))
        for key in ('f2', 'right', 'return'):
            player.press(key)
        player.order(swap['command'], *swap['args'], **swap['kwargs'])
        assert player.state.to_json() == swap['after']
        scene = game.scene
        assert type(scene) is BattleScene and scene.selected == 4
        assert scene.battle.unit(4).acted and not scene.battle.unit(0).acted
        assert scene.battle.evacuation_blocked_reason is None
        shown = [text['text'] for text in game.backend.texts]
        assert 'Spent' in shown
        swap_control = scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Swap ally')
        assert not swap_control.enabled and 'unspent unit action' in swap_control.tooltip
        footer = ' '.join(text['text'] for text in game.backend.texts if text['y'] >= scene.footer_top + 40)
        assert 'V evacuates your hero and surviving army' in footer, footer
        assert 'End the round' not in footer
        player.reload(swap['after'])
        player.press('v')
        assert isinstance(game.scene, ResultScene)
        assert player.state.to_json() == commands[103]['after']
    finally:
        game.close()


def test_one_remaining_defender_has_a_singular_header(tmp_path):
    """The earned Shrine's lone surviving Brigand is reported as one foe."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    player = PlayerInput(game)
    try:
        state = earned_commands()[12]['after']
        game.push(ShardScene(State.from_json(state)))
        player.press('tab')
        assert '5 allies · 1 foe · Tab selects' in [text['text'] for text in game.backend.texts]
        assert player.state.to_json() == state
    finally:
        game.close()
