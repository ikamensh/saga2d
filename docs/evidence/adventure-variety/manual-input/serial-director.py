"""Serialize short manual command processes while their operators reason independently."""
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

assert len(sys.argv) == 2 and sys.argv[1] in ('5', '12')
request = sys.stdin.buffer.read()
root = Path('/tmp/saga2d-adventure-variety-a7a6c50')
with open('/tmp/shardbound-adventure-manual.lock', 'a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    started = time.time()
    result = subprocess.run([
        '/Users/ikamen/ai-workspace/experiments/by_kodo/saga2d/.venv/bin/python',
        str(root / 'docs/evidence/adventure-variety/director.py'), sys.argv[1]],
        input=request, cwd=root)
    receipt = dict(seed=int(sys.argv[1]), started=started, ended=time.time(),
                   exit_code=result.returncode, request_sha256=hashlib.sha256(request).hexdigest())
    with open('/tmp/shardbound-adventure-manual-processes.jsonl', 'a') as log:
        log.write(json.dumps(receipt) + '\n')
    sys.exit(result.returncode)
