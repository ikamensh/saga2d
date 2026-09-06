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
from eador.difficulty import DIFFICULTIES, RULESETS
from eador.model import HERO_CLASSES, State
from eador.worldgen import NORTH_ROAD, SOUTH_ROAD, THEMES
from tools.audit_eador_economy import PLANS, Trial
from tools.stress_eador_control import PLANS as SPECIALIST_PLANS, ControlTrial

ROUTES = {'direct': None, 'north': NORTH_ROAD, 'south': SOUTH_ROAD}


class DifficultyTrial(Trial):
    def __init__(self, seed, hero, theme, plan, mode, route, *, rules_id=None,
                 mana_reserve=None, adaptive_interception=False, budget=None):
        state = State.new(seed, hero, theme=theme, difficulty=mode)
        if rules_id:
            # A deliberately configured fresh experiment, never a migrated live
            # campaign or an implicit change to the shipped new-game selector.
            data = json.loads(state.to_json())
            data['rules_id'] = rules_id
            state = State.from_json(json.dumps(data))
        super().__init__(seed, hero, theme, plan, state=state, route=ROUTES[route], budget=budget)
        self.mode, self.route_name = mode, route
        self.mana_reserve, self.adaptive_interception = mana_reserve, adaptive_interception
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

    def ready_for_final(self):
        state = self.state
        missing = max([state.hero.max_hp - state.hero.hp] + [t.max_hp - t.hp for t in state.hero.army])
        reserve = state.hero.max_mana - 4 if self.mana_reserve is None else min(self.mana_reserve, state.hero.max_mana)
        for reason, required in (('wounds', missing > 6), ('mana', state.hero.mana < reserve),
                                 ('actions', not state.actions_left)):
            self.events['final_wait.' + reason] += required
        ready = missing <= 6 and state.hero.mana >= reserve and state.actions_left > 0
        self.events['final_advance'] += ready
        return ready

    def intercept(self):
        if not self.adaptive_interception:
            return super().intercept()
        state = self.state
        # Recheck the announced live position after every turn instead of walking
        # to a stale target. Do not pursue an expedition that is no longer near home.
        for _ in range(24):
            if (state.status != 'playing' or state.turn >= 60 or self.stop_reason or
                    not state.rival.army or state.grid.distance(state.rival.pos, (-2, 0)) > 2):
                return
            if not state.actions_left:
                self.rest(defend=False)
                continue
            self.events['adaptive_interception_steps'] += 1
            state.travel(state.grid.path(state.hero.pos, state.rival.pos)[1])
            if state.battle:
                self.battle()
        self.stop_reason = 'interception_bound'

    def run(self):
        result = super().run()
        result.update(mode=self.mode, rules_id=self.state.rules_id, route=self.route_name,
                      recruitment_crystals=self.recruitment_crystals, events=dict(self.events),
                      mana_reserve=self.mana_reserve, adaptive_interception=self.adaptive_interception)
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
            'decisions': dict(sum((Counter(row['events']) for row in group), Counter())),
        }
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=100)
    parser.add_argument('--routes', nargs='+', choices=ROUTES, default=list(ROUTES))
    parser.add_argument('--modes', nargs='+', choices=DIFFICULTIES, default=list(DIFFICULTIES))
    parser.add_argument('--plans', nargs='+', choices=tuple(PLANS) + tuple(SPECIALIST_PLANS), default=list(PLANS))
    parser.add_argument('--rules-id', choices=RULESETS, help='Explicit fresh experimental checkpoint profile; leaves the new-game catalog unchanged.')
    parser.add_argument('--mana-reserve', type=int, help='Alternative final assault mana reserve; default is within four of maximum.')
    parser.add_argument('--adaptive-interception', action='store_true', help='Recheck the expedition position after every turn of a defensive detour.')
    parser.add_argument('--worst-from', type=Path, help='Replay only unfinished/defeated matching cases in a retained .rows.json.gz report.')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error('--seeds must be positive')
    if args.rules_id and args.modes != [args.rules_id.rsplit('-', 1)[0]]:
        parser.error('--rules-id requires the single matching --modes entry')
    if args.mana_reserve is not None and args.mana_reserve < 0:
        parser.error('--mana-reserve must be nonnegative')
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), Path(__file__).resolve(),
                      ROOT / 'tools/audit_eador_economy.py', ROOT / 'tools/stress_eador_control.py',
                      ROOT / 'tools/eador_campaign.py'])
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    started, rows = time.perf_counter(), []
    cases = [(seed, hero, theme, plan, mode, route) for seed in range(args.seeds)
             for theme in THEMES for hero in HERO_CLASSES for route in args.routes
             for plan in args.plans for mode in args.modes]
    if args.worst_from:
        original = json.loads(gzip.decompress(args.worst_from.read_bytes()))
        cases = [(r['seed'], r['hero'], r['theme'], r['plan'], r['mode'], r['route']) for r in original
                 if r['status'] != 'victory' and r['mode'] in args.modes and
                 r['plan'] in args.plans and r['route'] in args.routes]
        if not cases:
            parser.error('--worst-from has no matching unfinished or defeated cases')
    for index, case in enumerate(cases):
        options = dict(rules_id=args.rules_id, mana_reserve=args.mana_reserve,
                       adaptive_interception=args.adaptive_interception)
        row = DifficultyTrial(*case, **options).run()
        if case[0] == 0:
            assert row == DifficultyTrial(*case, **options).run()
        rows.append(row)
        if (index + 1) % 1080 == 0 or index + 1 == len(cases):
            print(f'{len(rows)}/{len(cases)} paid campaigns checked', flush=True)
    report = {
        'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'dirty': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
        'seeds': args.seeds, 'routes': args.routes, 'modes': args.modes, 'plans': args.plans,
        'rules_id_override': args.rules_id, 'mana_reserve': args.mana_reserve,
        'adaptive_interception': args.adaptive_interception,
        'worst_from': str(args.worst_from) if args.worst_from else None,
        'policy': 'Fixed purchased plans; disclosed site itineraries; first/free approaches; explicit automatic tactics; '
                  + ('live-position' if args.adaptive_interception else 'original fixed-destination') + ' rival interception; '
                  + (f'{args.mana_reserve} mana assault reserve' if args.mana_reserve is not None else 'within-four-of-maximum assault mana')
                  + '; unchanged six-HP wound tolerance; 60-turn/40-assault policy bounds.',
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
