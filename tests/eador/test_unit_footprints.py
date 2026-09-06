"""Permanent health annotations belong to their unit's hex, not its neighbors."""
import gzip
import json
from pathlib import Path

import pytest

from eador.app import create_game
from eador.model import State
from eador.scene import ShardScene
from tools.eador_ui import PlayerInput


@pytest.mark.parametrize('case', ['opening', 'crowded'])
def test_health_text_stays_inside_its_occupied_hex_at_supported_reading_sizes(tmp_path, case):
    """Drawing, selecting and resizing preserve exact HP while leaving adjacent pieces unobscured."""
    if case == 'opening':
        state = State.new(7)
        state.travel((-1, 0))
    else:
        path = Path(__file__).resolve().parents[2] / 'docs/evidence/shardbound-army-plans-cd351a9/control.json.gz'
        state = State.from_json(json.loads(gzip.decompress(path.read_bytes()))['commands'][80]['before'])
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        before = state.to_json()
        for window in ((1280, 720), (1280, 800), (1920, 1080)):
            game.set_window_size(window)
            for percent in (100, 125):
                player.press('f2'); player.press('left' if percent == 100 else 'right'); player.press('return')
                scene = game.scene
                for unit in scene.battle.units:
                    if not unit.alive:
                        continue
                    cx, cy = scene.grid.center(unit.pos)
                    labels = [item for item in game.backend.texts
                              if item['text'] in (str(unit.hp), f'{unit.hp}/{unit.max_hp}')
                              and abs(item['x'] - cx) < 1 and cy <= item['y'] < cy + scene.grid.size * 2]
                    assert len(labels) == 1, (unit.name, labels)
                    label = labels[0]
                    width, height = game.backend.measure_text(label['text'], label['font_size'], label['font'])
                    for x in (cx - width / 2, cx + width / 2):
                        for y in (label['y'], label['y'] + height):
                            assert scene.grid.cell_at(x, y) == unit.pos, (unit.name, label, (x, y))
                assert player.state.to_json() == before
    finally:
        game._teardown()
        game.backend.quit()
