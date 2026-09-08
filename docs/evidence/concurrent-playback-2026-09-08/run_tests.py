import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import pytest
from tools.cpu_budget import CpuBudget
budget = CpuBudget(25)
class Pace:
    def pytest_runtest_teardown(self):
        budget.checkpoint()
wall, cpu = time.monotonic(), time.process_time()
result = pytest.main(sys.argv[1:], plugins=[Pace()])
budget.checkpoint()
print(json.dumps(dict(wall_seconds=time.monotonic()-wall, cpu_seconds=time.process_time()-cpu)))
raise SystemExit(result)
