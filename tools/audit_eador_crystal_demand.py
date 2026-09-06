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
from tools.audit_eador_difficulty import DifficultyTrial, ROUTES

PLANS = ('economy', 'sustain', 'spells', 'control', 'flight')


class DemandTrial(DifficultyTrial):
    def __init__(self, *args):
        super().__init__(*args)
        self.first_quote = None
        self.demand = Counter()

    def ready_for_final(self):
        ready = super().ready_for_final()
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
        result.update(first_service_quote=self.first_quote, demand=dict(self.demand))
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=10)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error('--seeds must be positive')
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), Path(__file__),
                      ROOT / 'tools/audit_eador_difficulty.py', ROOT / 'tools/audit_eador_economy.py',
                      ROOT / 'tools/eador_campaign.py', ROOT / 'tools/stress_eador_control.py'])
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    started, rows = time.perf_counter(), []
    for seed in range(args.seeds):
        for theme in THEMES:
            for hero in HERO_CLASSES:
                for route in ROUTES:
                    for plan in PLANS:
                        for mode in DIFFICULTIES:
                            trial = DemandTrial(seed, hero, theme, plan, mode, route)
                            result = trial.run()
                            if seed == 0 and route == 'direct':
                                baseline = DifficultyTrial(seed, hero, theme, plan, mode, route).run()
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
    report = dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, seeds=args.seeds, plans=PLANS, modes=list(DIFFICULTIES),
                  policy='Read-only service quotes during unchanged final recovery decisions; no services execute; '
                         '8mana/3crystals/Tower and12HP-per-unit/2crystals/Temple; first affordable quote per campaign avoids counting repeat waits as independent purchases.',
                  elapsed_seconds=time.perf_counter() - started, summary=summary,
                  source_files_changed=[str(p.relative_to(ROOT)) for p in sources
                                        if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))]])
    assert not report['source_files_changed']
    args.report.parent.mkdir(parents=True, exist_ok=True)
    rows_path = args.report.with_suffix('.rows.json.gz')
    rows_path.write_bytes(gzip.compress(json.dumps(rows, separators=(',', ':')).encode(), mtime=0))
    report.update(rows_file=rows_path.name, rows_sha256=hashlib.sha256(rows_path.read_bytes()).hexdigest())
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
