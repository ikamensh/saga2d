"""Retain full linked-campaign outcomes, recovery viability and source fingerprints."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eador.model import HERO_CLASSES, State
from tools.eador_linked_campaign import lose_shard, play_linked, play_stage, travel_selection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=20)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error('--seeds must be positive')
    sources = [*sorted((ROOT / 'eador').glob('*.py')), Path(__file__),
               ROOT / 'tools/eador_campaign.py', ROOT / 'tools/eador_linked_campaign.py']
    before = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    runs = []
    started = time.monotonic()
    for seed in range(args.seeds):
        if seed % 10 == 0:
            print(f'Linked seed {seed}/{args.seeds}', flush=True)
        for hero in HERO_CLASSES:
            for middle in ('rootward', 'foundries'):
                for finale in ('throne', 'gate'):
                    state = play_linked(seed, hero, middle, finale)
                    runs.append(dict(seed=seed, hero=hero, middle=middle, finale=finale, recovery=False,
                                     phase=state.campaign.phase, stages=[asdict(record) for record in state.campaign.completed]))
                if seed % 5 == 0:
                    state = play_stage(State.new_campaign(seed, hero))
                    state.advance(middle, **travel_selection(state))
                    lose_shard(state)
                    state = State.from_json(state.to_json())
                    state.recover(**travel_selection(state))
                    state = play_stage(state)
                    state.advance('gate', **travel_selection(state))
                    state = play_stage(state)
                    runs.append(dict(seed=seed, hero=hero, middle=middle, finale='gate', recovery=True,
                                     phase=state.campaign.phase, stages=[asdict(record) for record in state.campaign.completed]))
    after = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    assert before == after, 'source changed while auditing'
    report = dict(source_sha256=before, elapsed_seconds=round(time.monotonic() - started, 2),
                  policy='Public economic itinerary; first skill choice; two strongest survivors; Moonstone/Merchant Seal prioritised. '
                         'Explicit tactical auto command. Every fifth seed also loses stage 2, reloads and spends its one recovery before finishing.',
                  seeds=args.seeds, campaigns=len(runs), completed=sum(run['phase'] == 'completed' for run in runs),
                  recovery_runs=sum(run['recovery'] for run in runs), runs=runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key not in ('source_sha256', 'runs')}, indent=2))
    assert report['completed'] == report['campaigns'], 'some audited journeys did not complete; inspect report'


if __name__ == '__main__':
    main()
