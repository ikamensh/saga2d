"""Inspect the ordinary paid replacement review after removing its empty ability row."""
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path.cwd()))
from eador.app import create_game
from eador.model import State
from eador.scene import ShardScene
from tools.cpu_budget import CpuBudget
from tools.verify_eador_guidance import check_reading_layout
from tools.verify_eador_shard_look import PacedInput

output = Path('/tmp/shardbound-replacement-row-native')
output.mkdir(exist_ok=False)
budget = CpuBudget(25)
wall, cpu = time.monotonic(), time.process_time()
game = create_game(backend='pyglet', visible=False, save_dir=output / 'saves')
player = PacedInput(game, budget, native=True, output=output)
try:
    game.set_window_size((1280, 720))
    game.push(ShardScene(State.new(7)))
    for key in ('b', '1', 'escape', 'r', 'm', '1'):
        player.press(key)
    for _ in range(game.scene.pages):
        if 'swordsman' in game.scene.visible_items:
            break
        player.press('right')
    player.press(str(game.scene.visible_items.index('swordsman') + 1))
    before = player.state.to_json()
    quote = player.state.replacement_preview(1, 'swordsman')
    check_reading_layout(game.scene)
    player.capture('01-review-100', settle=False)
    for key in ('t', 'right', 'return'):
        player.press(key)
    check_reading_layout(game.scene)
    player.capture('02-review-125', settle=False)
    assert player.state.to_json() == before
    expected = State.from_json(before)
    expected.replace_troop(1, 'swordsman')
    player.press('return')
    assert player.state.to_json() == expected.to_json()
    check_reading_layout(game.scene)
    player.capture('03-applied-125', settle=False)
    player.button('Return to shard')
    assert isinstance(game.scene, ShardScene)
    assert player.state.to_json() == expected.to_json()
    receipt = dict(before=json.loads(before), after=json.loads(expected.to_json()),
                   paid=dict(gold=quote.gold, crystals=quote.crystals, actions=quote.actions),
                   inputs=player.events, captures=['01-review-100', '02-review-125', '03-applied-125'],
                   source_sha256={str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in (Path('eador/replacement_scene.py'), Path('eador/scene.py'))})
finally:
    game.close()
assert game.backend.window is None
receipt.update(wall_seconds=time.monotonic() - wall, cpu_seconds=time.process_time() - cpu,
               cpu_allowance_percent=25, native_fps_cap=30, closed=True,
               directed_verification_not_independent_human_play=True)
(output / 'verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
print({key: receipt[key] for key in ('paid', 'captures', 'wall_seconds', 'cpu_seconds', 'closed')})
