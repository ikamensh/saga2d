#!/usr/bin/env python3
"""Compare disclosed paid plans and routes across frozen realm difficulties.

Fixed automatic policies establish tradeoffs and failure cases, not player
enjoyment or optimal difficulty balance. Detailed rows retain all purchases.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eador.difficulty import DIFFICULTIES
from eador.model import HERO_CLASSES, State
from eador.worldgen import NORTH_ROAD, SOUTH_ROAD, THEMES
from tools.audit_eador_economy import PLANS, Trial
from tools.stress_eador_control import PLANS as SPECIALIST_PLANS, ControlTrial

ROUTES = {'direct': None, 'north': NORTH_ROAD, 'south': SOUTH_ROAD}


class DifficultyTrial(Trial):
    def __init__(self, seed, hero, theme, plan, mode, route):
        super().__init__(seed, hero, theme, plan, state=State.new(seed, hero, theme=theme, difficulty=mode),
                         route=ROUTES[route])
        self.mode, self.route_name = mode, route
        self.events = Counter()
        self.recruitment_crystals = 0

    def invest(self):
        if self.plan in SPECIALIST_PLANS:
            ControlTrial.invest(self)
        else:
            super().invest()

    def buy(self, action, kind):
        crystals = self.state.crystals
        super().buy(action, kind)
        if action == 'recruit':
            self.recruitment_crystals += crystals - self.state.crystals

    def battle(self):
        self.events['battle.' + self.state.battle_kind] += 1
        super().battle()

    def rest(self, defend=True):
        self.events['shortfall_turns'] += self.state.upkeep_shortfall > 0
        super().rest(defend)

    def run(self):
        result = super().run()
        result.update(mode=self.mode, rules_id=self.state.rules_id, route=self.route_name,
                      recruitment_crystals=self.recruitment_crystals, events=dict(self.events))
        return result


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        for key in ((row['mode'], row['plan']), (row['mode'], row['plan'], row['route']),
                    (row['mode'], row['theme'], row['hero'], row['plan'], row['route'])):
            groups['/'.join(key)].append(row)
    results = {}
    for key, group in sorted(groups.items()):
        turns = sorted(row['turns'] for row in group)
        results[key] = {
            'runs': len(group), 'outcomes': dict(Counter(row['status'] for row in group)),
            'stop_reasons': dict(Counter(row['stop_reason'] for row in group)),
            'mean_turns': statistics.mean(turns), 'median_turns': statistics.median(turns),
            'p90_turns': turns[max(0, (len(turns) * 9 + 9) // 10 - 1)], 'max_turns': max(turns),
            'mean_casualties': statistics.mean(row['metrics']['lost_troops'] for row in group),
            'mean_recovery_turns': statistics.mean(row['metrics']['recovery_turns'] for row in group),
            'mean_mana_spent': statistics.mean(row['metrics']['mana_spent'] for row in group),
            'mean_recruitment_gold': statistics.mean(row['metrics']['recruitment_gold'] for row in group),
            'mean_building_gold': statistics.mean(row['metrics']['building_gold'] for row in group),
            'mean_crystals_spent': statistics.mean(row['building_crystals'] + row['recruitment_crystals'] for row in group),
            'mean_crystals_left': statistics.mean(row['crystals_left'] for row in group),
            'mean_gold_left': statistics.mean(row['gold_left'] for row in group),
            'mean_upkeep_gold': statistics.mean(row['upkeep_gold'] for row in group),
            'deserters': sum(row['deserters'] for row in group),
            'battle_defeats': sum(row['metrics']['defeats'] for row in group),
        }
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=100)
    parser.add_argument('--routes', nargs='+', choices=ROUTES, default=list(ROUTES))
    parser.add_argument('--modes', nargs='+', choices=DIFFICULTIES, default=list(DIFFICULTIES))
    parser.add_argument('--plans', nargs='+', choices=tuple(PLANS) + tuple(SPECIALIST_PLANS), default=list(PLANS))
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error('--seeds must be positive')
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), Path(__file__).resolve(),
                      ROOT / 'tools/audit_eador_economy.py', ROOT / 'tools/stress_eador_control.py',
                      ROOT / 'tools/eador_campaign.py'])
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    started, rows = time.perf_counter(), []
    for seed in range(args.seeds):
        for theme in THEMES:
            for hero in HERO_CLASSES:
                for route in args.routes:
                    for plan in args.plans:
                        for mode in args.modes:
                            row = DifficultyTrial(seed, hero, theme, plan, mode, route).run()
                            if seed == 0:
                                assert row == DifficultyTrial(seed, hero, theme, plan, mode, route).run()
                            rows.append(row)
        if (seed + 1) % 10 == 0 or seed + 1 == args.seeds:
            print(f'{seed + 1} seeds; {len(rows)} paid campaigns checked', flush=True)
    report = {
        'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'dirty': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
        'seeds': args.seeds, 'routes': args.routes, 'modes': args.modes, 'plans': args.plans,
        'policy': 'Fixed purchased plans; disclosed site itineraries; first/free approaches; explicit automatic tactics; '
                  'visible rival interception; conservative final recovery; 60-turn/40-assault policy bounds.',
        'source_sha256': hashes,
        'source_files_changed': [str(path.relative_to(ROOT)) for path in sources
                                 if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[str(path.relative_to(ROOT))]],
        'elapsed_seconds': time.perf_counter() - started, 'summary': summarize(rows),
    }
    assert not report['source_files_changed']
    args.report.parent.mkdir(parents=True, exist_ok=True)
    rows_path = args.report.with_suffix('.rows.json.gz')
    rows_path.write_bytes(gzip.compress(json.dumps(rows, separators=(',', ':')).encode(), mtime=0))
    report['rows_file'] = rows_path.name
    report['rows_sha256'] = hashlib.sha256(rows_path.read_bytes()).hexdigest()
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(dict(Counter((row['mode'], row['status']) for row in rows)))


if __name__ == '__main__':
    main()
