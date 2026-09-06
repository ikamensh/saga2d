#!/usr/bin/env python3
"""Vary legal orders in four earned relic battles and validate full campaign saves.

These are seeded policies from four seed-7 earned checkpoints, not independent
worlds or evidence of difficulty balance. The manual routes have separate tests.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.model import State
from tools.eador_campaign import finish_battle
from tools.eador_extraction_campaign import AdventureOrders
from tools.eador_relic_campaign import (drum_watch_route, prepare_censer_watch,
                                        prepare_relic_gate)
from tools.stress_eador_control import exercise


def earned_checkpoints():
    """The Drum starts just before its actual enemy Pin can be answered."""
    class PinOrders(AdventureOrders):
        pinned_save = None

        def do(self, command, *args, **kwargs):
            if command == 'rally':
                self.pinned_save = self.state.to_json()
            return super().do(command, *args, **kwargs)

    drum = drum_watch_route(orders_type=PinOrders)
    assert drum.pinned_save is not None
    return {
        'veil_censer': prepare_censer_watch(ranger=True).to_json(),
        'vanguard_drum': drum.pinned_save,
        'porter_rune': prepare_relic_gate('porter_rune').to_json(),
        'mirror_badge': prepare_relic_gate('mirror_badge').to_json(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policies', type=int, default=50, help='policies per earned checkpoint')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'),
                      *ROOT.joinpath('tools').glob('eador*campaign.py'), Path(__file__).resolve(),
                      ROOT / 'tools/stress_eador_control.py'])
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    report = {'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'dirty_at_start': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
              'source_sha256': hashes, 'policies_per_checkpoint': args.policies,
              'checkpoint_world_seed': 7}
    started, results = time.perf_counter(), {}
    for relic, saved in earned_checkpoints().items():
        metrics = Counter()
        for seed in range(args.policies):
            state = State.from_json(saved)

            def checkpoint():
                current = state.to_json()
                assert State.from_json(current).to_json() == current
                metrics['campaign_save_checks'] += 1

            exercise(seed, metrics, battle=state.battle, checkpoint=checkpoint)
            restored = State.from_json(state.to_json())
            finish_battle(state); finish_battle(restored)
            assert state.to_json() == restored.to_json(), 'Saved relic battle resolution changed the campaign'
            metrics['resolution_checks'] += 1
        results[relic] = dict(metrics)
        print(f'{relic}: {args.policies} policies passed', flush=True)
    report.update(metrics=results, elapsed_seconds=time.perf_counter() - started,
                  source_files_changed=[str(p.relative_to(ROOT)) for p in sources
                                        if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))]])
    assert not report['source_files_changed']
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(results, sort_keys=True))


if __name__ == '__main__':
    main()
