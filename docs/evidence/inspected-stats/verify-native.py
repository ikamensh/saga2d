"""Native inspected-stat readouts after a paid attack; runs at 30 FPS / 25% CPU."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from saga2d import Image, Label, Row
from eador.app import create_game
from eador.model import State
from eador.scene import ShardScene
from eador.ui import icon_path
from tools.cpu_budget import CpuBudget
from tools.eador_observatory_campaign import prepare_observatory
from tools.eador_ui import PlayerInput
from tools.native_frames import tick
from tools.verify_eador_guidance import check_reading_layout

output = Path(sys.argv[1])
output.mkdir()
budget = CpuBudget(25)
prepared = prepare_observatory(budget=budget)
prepared.explore(approach='clear')
for ident, pos in ((1, (1, -1)), (0, (0, 0)), (3, (0, -1))):
    prepared.battle.move(ident, pos)
report = {'scope': __doc__, 'cases': []}
report['sources'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in [*(ROOT/'eador').glob('*.py'), *(ROOT/'saga2d').rglob('*.py')]}
for percent in (100, 125):
    state = State.from_json(prepared.to_json())
    target = next(u for u in state.battle.units if u.kind == 'guard' and u.team == 'enemy')
    expected = State.from_json(state.to_json()); expected.battle.attack(0, target.id)
    game = create_game(backend='pyglet', visible=False, save_dir=output/str(percent)/'saves')
    try:
        game.push(ShardScene(state)); tick(game)
        player = PlayerInput(game, native=True, finish_actions=False)
        player.press('f2'); player.press('right' if percent == 125 else 'left'); player.press('return')
        player.order('battle.attack', 0, target.id)
        for _ in range(36):
            tick(game); budget.checkpoint()
        assert state.to_json() == expected.to_json()
        metrics = []
        for name, value in (('attack', target.attack), ('defense', target.effective_defense), ('range', target.attack_range)):
            row = game.scene.ui.find(lambda item: isinstance(item, Row) and item.tooltip
                                     and target.name in item.tooltip and any(isinstance(child, Image)
                                     and child.image == icon_path(name) for child in item.children))
            assert row is not None
            label = next(child for child in row.children if isinstance(child, Label))
            assert label.text == str(value) and label.bounds[1] == row.bounds[1]
            metrics.append({'name': name, 'value': value, 'bounds': row.bounds, 'tooltip': row.tooltip})
        check_reading_layout(game.scene)
        game.backend.capture_frame().save(output/f'inspect-{percent}.png')
        player.reload(expected.to_json())
        report['cases'].append({'reading_scale': percent, 'metrics': metrics, 'inputs': player.events,
                                'exact_reload': True, 'resolved': expected.to_json()})
    finally:
        game.close()
    assert game.backend.window is None
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h for p,h in report['sources'].items())
(output/'receipt.json.gz').write_bytes(gzip.compress(json.dumps(report,indent=2).encode(),mtime=0))
print('Both native inspection sizes passed, with two exact reloads and closed Games.')
