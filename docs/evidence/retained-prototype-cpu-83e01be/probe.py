"""One retained cargo continuation with a real, cooperative 25% allowance."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

root = Path.cwd()
sys.path.insert(0, str(root))
from tools.cpu_budget import CpuBudget
from tools.prototype_eador_departure_cargo import run_case

input_path = root / 'docs/evidence/departure-cargo-prototype.json'
case = json.loads(input_path.read_text())['inputs']['swords']
before = json.dumps(case, sort_keys=True)
paths = sorted([*root.glob('eador/**/*.py'), *root.glob('tools/eador*campaign.py'),
                root / 'tools/prototype_eador_departure_cargo.py', root / 'tools/audit_eador_economy.py',
                root / 'tools/cpu_budget.py'])
hashes = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
started, cpu_started = time.monotonic(), time.process_time()
budget = CpuBudget(25)
result = run_case(case, 'chest', 'magic', budget=budget)
encoded = json.dumps(result, sort_keys=True)
budget.checkpoint()
elapsed, cpu_seconds = time.monotonic() - started, time.process_time() - cpu_started
assert json.dumps(case, sort_keys=True) == before
assert all(hashlib.sha256((root / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              source_sha256=hashes, input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
              case='swords/chest/magic', cpu_percent=budget.percent, elapsed_seconds=elapsed,
              cpu_seconds=cpu_seconds, average_one_core_percent=100 * cpu_seconds / elapsed,
              outcome=result['result'], paired_battles=len(result['fights']),
              result_sha256=hashlib.sha256(encoded.encode()).hexdigest(), input_unchanged=True,
              scope='One retained paid continuation including its saved comparison battles and result serialization; '
                    'imports and source hashing excluded. Cooperative allowance, not an operating-system quota.')
print(json.dumps(report, indent=2, sort_keys=True))
