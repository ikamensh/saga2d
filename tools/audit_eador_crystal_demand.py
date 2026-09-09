#!/usr/bin/env python3
"""Quote proposed camp services at real decisions without applying either service.

The same baseline policy still executes every order. A quoted avoided wait is a
local observation, not a counterfactual campaign result or a claim about balance.
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
from eador.model import HERO_CLASSES
from eador.worldgen import THEMES
from tools.eador_sources import source_name
from tools.audit_eador_difficulty import DifficultyTrial, ROUTES
from saga2d.testing.cpu_budget import CpuBudget

PLANS = ('economy', 'sustain', 'spells', 'control', 'flight')


class DemandTrial(DifficultyTrial):
    def __init__(self, *args, examples=None, budget=None):
        super().__init__(*args, budget=budget)
        self.first_quote = None
        self.demand = Counter()
        self.first_service_points = {}
        self.examples = examples

    def battle(self):
        super().battle()
        self.observe_services('after_battle')

    def observe_services(self, phase):
        state = self.state
        if state.status != 'playing' or state.battle or state.choice or (state.encircled and state.hero.pos == (-2, 0)):
            return
        units = [(0, state.hero), *((u.id, u) for u in state.hero.army)]
        missing = {uid: u.max_hp - u.hp for uid, u in units}
        budget, party = 24, {}
        for uid in sorted(missing, key=lambda uid: (-missing[uid], uid)):
            gain = min(missing[uid], 12, budget)
            if gain:
                party[uid] = gain
                budget -= gain
        mana = min(8, state.hero.max_mana - state.hero.mana)
        infusion = mana > 0 and 'mage_tower' in state.buildings and state.crystals >= 3
        treatment = bool(party) and 'temple' in state.buildings and state.crystals >= 4
        if not infusion and not treatment:
            return
        recovery = state.recovery_preview()
        point = dict(turn=state.turn, actions=state.actions_left, crystals=state.crystals,
                     gold=state.gold, army_size=len(state.hero.army), capacity=state.hero.max_army,
                     buildings=sorted(state.buildings),
                     infusion=infusion, mana_gain=mana,
                     party_treatment=treatment, party_hp=sum(party.values()), party_gains=party,
                     equivalent_targeted_cost=2 * len(party), equivalent_targeted_orders=len(party),
                     single_treatment_best_gain=max((min(12, m) for m in missing.values()), default=0),
                     full_targeted_bill=2 * sum((m + 11) // 12 for m in missing.values()),
                     infusion_covered_by_free_rest=mana <= recovery.mana,
                     party_covered_by_free_rest=all(gain <= (recovery.hero_hp if uid == 0 else recovery.army_hp)
                                                   for uid, gain in party.items()),
                     capital_distance=state.grid.distance(state.hero.pos, (2, 0)),
                     rival_adjacent=bool(state.rival.army) and state.grid.distance(state.hero.pos, state.rival.pos) == 1,
                     rival_intent=state.rival.intent, rival_countdown=state.rival.turns_until_action,
                     upkeep_shortfall=state.upkeep_shortfall)
        self.first_service_points.setdefault(phase, point)
        if self.examples is not None:
            conditions = {
                'pre_assault_mana': phase == 'final_recovery' and infusion and mana >= 4 and
                    max(missing.values()) <= 6 and point['capital_distance'] == 1 and state.actions_left >= 2,
                'pursuit_last_action': phase == 'after_battle' and state.actions_left == 1 and point['rival_adjacent'] and
                    ((infusion and mana >= 6) or (treatment and sum(party.values()) >= 12)),
                'party_scattered': phase == 'after_battle' and treatment and len(party) >= 3 and sum(party.values()) >= 18,
                'party_single_wound': phase == 'after_battle' and treatment and len(party) == 1 and point['party_covered_by_free_rest'],
                'late_full_roster': phase == 'final_recovery' and len(state.hero.army) == state.hero.max_army and
                    state.gold >= 200 and state.crystals >= 15,
            }
            for name, matches in conditions.items():
                if matches and name not in self.examples:
                    self.examples[name] = dict(seed=self.seed, hero=self.hero_class, theme=self.theme,
                                               plan=self.plan, mode=self.mode, route=self.route_name,
                                               phase=phase, quote=point, state=json.loads(state.to_json()))

    def ready_for_final(self):
        ready = super().ready_for_final()
        if not ready:
            self.observe_services('final_recovery')
        state = self.state
        if ready or not state.actions_left or (state.encircled and state.hero.pos == (-2, 0)):
            return ready
        mana = max(0, state.hero.max_mana - 4 - state.hero.mana)
        wounds = [max(0, unit.max_hp - unit.hp - 6) for unit in (state.hero, *state.hero.army)]
        # Price hypotheses: 3 crystals for up to 8 mana; 2 for up to 12 HP
        # on one living combatant. Repeated doses can reach the existing reserve.
        infusions = (mana + 7) // 8
        treatments = sum((missing + 11) // 12 for missing in wounds)
        price = 3 * infusions + 2 * treatments
        if not price:
            return ready
        kind = 'both' if mana and any(wounds) else 'mana' if mana else 'wounds'
        self.demand['wait.' + kind] += 1
        gate = (not mana or 'mage_tower' in state.buildings) and (not any(wounds) or 'temple' in state.buildings)
        self.demand['missing_building.' + kind] += not gate
        self.demand['insufficient_crystals.' + kind] += state.crystals < price
        if gate and state.crystals >= price:
            self.demand['affordable.' + kind] += 1
            if self.first_quote is None:
                recovery = state.recovery_preview()
                hero_wait = (wounds[0] + recovery.hero_hp - 1) // recovery.hero_hp if wounds[0] else 0
                army_wait = max(((missing + recovery.army_hp - 1) // recovery.army_hp for missing in wounds[1:]), default=0)
                mana_wait = (mana + state.rules.mana_recovery - 1) // state.rules.mana_recovery
                self.first_quote = dict(turn=state.turn, kind=kind, crystals=state.crystals,
                                       price=price, remaining=state.crystals - price,
                                       gold=state.gold, infusions=infusions, treatments=treatments,
                                       mana_needed=mana, wound_needs=wounds,
                                       passive_turns_without_intervening_battles=max(hero_wait, army_wait, mana_wait),
                                       rival_intent=state.rival.intent, rival_countdown=state.rival.turns_until_action)
        return ready

    def run(self):
        result = super().run()
        result.update(first_service_quote=self.first_quote, demand=dict(self.demand),
                      first_service_points=self.first_service_points)
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=10)
    parser.add_argument('--heroes', nargs='+', choices=HERO_CLASSES, default=list(HERO_CLASSES))
    parser.add_argument('--themes', nargs='+', choices=THEMES, default=list(THEMES))
    parser.add_argument('--routes', nargs='+', choices=ROUTES, default=list(ROUTES))
    parser.add_argument('--modes', nargs='+', choices=DIFFICULTIES, default=list(DIFFICULTIES))
    parser.add_argument('--plans', nargs='+', choices=PLANS, default=list(PLANS))
    parser.add_argument('--cpu-percent', type=float, default=25,
                        help='Cooperative allowance for one CPU core; 100 disables sleeping.')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.seeds < 1:
        parser.error('--seeds must be positive')
    budget = CpuBudget(args.cpu_percent)
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), Path(__file__),
                      ROOT / 'tools/audit_eador_difficulty.py', ROOT / 'tools/audit_eador_economy.py',
                      ROOT / 'tools/eador_campaign.py', ROOT / 'tools/stress_eador_control.py'])
    hashes = {source_name(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    started, rows, examples = time.perf_counter(), [], {}
    for seed in range(args.seeds):
        for theme in args.themes:
            for hero in args.heroes:
                for route in args.routes:
                    for plan in args.plans:
                        for mode in args.modes:
                            trial = DemandTrial(seed, hero, theme, plan, mode, route, examples=examples, budget=budget)
                            result = trial.run()
                            if seed == 0 and route == 'direct':
                                baseline = DifficultyTrial(seed, hero, theme, plan, mode, route, budget=budget).run()
                                assert all(result[key] == value for key, value in baseline.items()), 'Observation changed baseline orders'
                            rows.append(result)
        print(f'{seed + 1}/{args.seeds} seeds; {len(rows)} observed campaigns', flush=True)
    groups = defaultdict(list)
    for row in rows:
        groups[row['mode']].append(row)
        groups[row['mode'] + '/' + row['plan']].append(row)
    summary = {}
    for key, group in sorted(groups.items()):
        quotes = [r['first_service_quote'] for r in group if r['first_service_quote']]
        summary[key] = dict(runs=len(group), outcomes=dict(Counter(r['status'] for r in group)),
                            campaigns_with_affordable_quote=len(quotes),
                            first_quote_kinds=dict(Counter(q['kind'] for q in quotes)),
                            mean_first_quote_price=statistics.mean(q['price'] for q in quotes) if quotes else None,
                            mean_first_quote_remaining=statistics.mean(q['remaining'] for q in quotes) if quotes else None,
                            mean_first_quote_turns=statistics.mean(q['passive_turns_without_intervening_battles'] for q in quotes) if quotes else None,
                            mean_first_quote_turn=statistics.mean(q['turn'] for q in quotes) if quotes else None,
                            demand=dict(sum((Counter(r['demand']) for r in group), Counter())))
        summary[key]['service_points'] = {}
        for phase in ('after_battle', 'final_recovery'):
            points = [r['first_service_points'][phase] for r in group if phase in r['first_service_points']]
            if not points:
                continue
            party = [p for p in points if p['party_treatment']]
            summary[key]['service_points'][phase] = dict(
                points=len(points), actions=dict(Counter(p['actions'] for p in points)),
                last_action_with_adjacent_rival=sum(p['actions'] == 1 and p['rival_adjacent'] for p in points),
                infusion_offers=sum(p['infusion'] for p in points), party_offers=len(party),
                mean_party_hp=statistics.mean(p['party_hp'] for p in party) if party else None,
                mean_targeted_equivalent_cost=statistics.mean(p['equivalent_targeted_cost'] for p in party) if party else None,
                mean_targeted_equivalent_orders=statistics.mean(p['equivalent_targeted_orders'] for p in party) if party else None,
                mean_full_targeted_bill=statistics.mean(p['full_targeted_bill'] for p in party) if party else None,
                party_lower_price=sum(p['equivalent_targeted_cost'] > 4 for p in party),
                party_higher_price=sum(p['equivalent_targeted_cost'] < 4 for p in party),
                party_free_rest_covers=sum(p['party_covered_by_free_rest'] for p in party),
                infusion_free_rest_covers=sum(p['infusion'] and p['infusion_covered_by_free_rest'] for p in points))
    report = dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, seeds=args.seeds, plans=args.plans, modes=args.modes,
                  heroes=args.heroes, themes=args.themes, routes=args.routes, cpu_percent=args.cpu_percent,
                  policy='Read-only service quotes during unchanged final recovery and post-battle decisions; no services execute; '
                         '8mana/3crystals/Tower,12HP-per-unit/2crystals/Temple, party24HP total max12each/4crystals/Temple; '
                         'first affordable quote per phase/campaign avoids counting repeat waits as independent purchases; remaining actions expose cost0vs1.',
                  elapsed_seconds=time.perf_counter() - started, summary=summary,
                  source_files_changed=[str(p.relative_to(ROOT)) for p in sources
                                        if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))]])
    assert not report['source_files_changed']
    args.report.parent.mkdir(parents=True, exist_ok=True)
    rows_path = args.report.with_suffix('.rows.json.gz')
    rows_path.write_bytes(gzip.compress(json.dumps(rows, separators=(',', ':')).encode(), mtime=0))
    report.update(rows_file=rows_path.name, rows_sha256=hashlib.sha256(rows_path.read_bytes()).hexdigest())
    examples_path = args.report.with_suffix('.examples.json')
    examples_path.write_text(json.dumps(examples, indent=2, sort_keys=True) + '\n')
    report.update(examples_file=examples_path.name, examples_sha256=hashlib.sha256(examples_path.read_bytes()).hexdigest())
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
