"""Focused integration verification, cooperatively paced to 25% of one CPU core."""
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path.cwd()))
import pytest
from tools.cpu_budget import CpuBudget

class Pace:
    def __init__(self):
        self.budget = CpuBudget(25)

    def pytest_runtest_teardown(self, item, nextitem):
        self.budget.checkpoint()

selection = [
    'tests/eador/test_concurrent_scene.py',
    'tests/eador/test_human_battle_scene.py',
    'tests/eador/test_shard_map.py',
    'tests/eador/test_shard_reading.py',
    'tests/eador/test_replacement_scene.py',
    'tests/eador/test_scene.py::test_stronghold_unlocks_recruitment_through_keyboard_and_mouse',
    'tests/eador/test_scene.py::test_adventure_choices_restore_then_equip_a_relic_through_input',
    'tests/eador/test_scene.py::test_battle_save_restores_playable_tactics_and_returns_wounds_to_map',
    'tests/eador/test_scene.py::test_keyboard_only_tactics_move_cast_attack_reload_and_retreat',
    'tests/eador/test_scene.py::test_exhausted_actions_show_complete_guidance_above_the_disabled_travel_control',
]
print('SELECTION', selection, flush=True)
paths = sorted(Path('eador').glob('*.py')) + sorted(Path('saga2d').rglob('*.py'))
paths += [Path(name.split('::')[0]) for name in selection]
hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
wall, cpu = time.monotonic(), time.process_time()
status = pytest.main(['-q', '--maxfail=1', *selection], plugins=[Pace()])
receipt = dict(selection=selection, exit_code=int(status), cpu_allowance_percent=25,
               wall_seconds=time.monotonic() - wall, cpu_seconds=time.process_time() - cpu,
               source_sha256=hashes, source_unchanged=all(
                   hashlib.sha256(path.read_bytes()).hexdigest() == hashes[str(path)] for path in paths))
Path('/tmp/concurrent-ui-final-tests.json').write_text(json.dumps(receipt, indent=2) + '\n')
print({key: receipt[key] for key in ('wall_seconds', 'cpu_seconds', 'cpu_allowance_percent',
                                   'exit_code', 'source_unchanged')}, flush=True)
sys.exit(status)
