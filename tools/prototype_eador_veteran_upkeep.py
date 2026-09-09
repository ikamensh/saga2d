#!/usr/bin/env python3
"""NON-PRODUCTION: rank wages, early scarcity and replacement payback.

Two coefficients only: +1 or +2 gold per troop rank above one. A single paired
40-raw-gold ceiling is checked after wages alone leave the late realm profitable.
No shipped rules ID, profile, command, tactical formula or save schema is edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eador.model import State, RuleError, UNITS
from tools.eador_sources import source_name
from tools.prototype_eador_late_realm import MeasuredState, paid_plan, snapshot
from saga2d.testing.cpu_budget import CpuBudget
from tools.eador_linked_campaign import play_stage, travel_selection, lose_shard
from tools.eador_campaign import finish_battle


class SalaryOne(MeasuredState):
    coefficient = 1

    def wage(self, troop):
        return UNITS[troop.kind].upkeep + self.coefficient * (troop.level - 1)

    @property
    def upkeep(self):
        return sum(self.wage(t) for t in self.hero.army)

    def _unpaid_troops(self):
        # Keep the production priority, but discharge the full experimental wage.
        shortfall, departing = self.upkeep_shortfall, []
        for troop in sorted(self.hero.army, key=lambda t: (t.level, t.xp, -self.wage(t), -t.id)):
            if shortfall <= 0:
                break
            departing.append(troop)
            shortfall -= self.wage(troop)
        return departing


class SalaryTwo(SalaryOne):
    coefficient = 2


class SalaryTwoCeiling(SalaryTwo):
    @property
    def income(self):
        return min(super().income, 40 * self.rules.gold_percent // 100)


VARIANTS = {'ordinary': MeasuredState, 'wages-1': SalaryOne, 'wages-2': SalaryTwo,
            'wages-2-cap40': SalaryTwoCeiling}


def branch(payload, cls, replace=False, turns=4, *, budget=None):
    budget = CpuBudget(25) if budget is None else budget
    state = cls.from_json(json.dumps(payload))
    events = [snapshot(state)]
    if replace:
        state.replace_troop(state.hero.army[0].id, state.hero.army[0].kind)
        events.append(snapshot(state))
    for _ in range(turns):
        budget.checkpoint()
        state.end_turn()
        if state.battle:
            finish_battle(state, budget=budget)
        assert state.status == 'playing'
        encoded = state.to_json()
        state = cls.from_json(encoded)
        assert state.to_json() == encoded
        events.append(snapshot(state))
    budget.checkpoint()
    return events


def recovery_input(mode, *, budget=None):
    """Lose an actually played second shard, then select its surviving retinue."""
    budget = CpuBudget(25) if budget is None else budget
    state = play_stage(State.new_campaign(7, 'Commander', difficulty=mode), budget=budget)
    state.advance('rootward', **travel_selection(state))
    lose_shard(state, budget=budget)
    state.recover(**travel_selection(state))
    budget.checkpoint()
    return json.loads(state.to_json())


def recovery_probe(payload, cls, policy, *, budget=None):
    budget = CpuBudget(25) if budget is None else budget
    state = cls.from_json(json.dumps(payload))
    events = [snapshot(state)]
    if policy == 'shrine_first':
        state.explore()
        finish_battle(state, budget=budget)
        events.append(snapshot(state))
    elif policy == 'wait_three':
        for _ in range(3):
            budget.checkpoint()
            state.end_turn()
            if state.battle:
                finish_battle(state, budget=budget)
            events.append(snapshot(state))
    before = state.to_json()
    try:
        state.build('mage_tower')
    except RuleError as error:
        assert state.to_json() == before
        outcome = str(error)
    else:
        outcome = 'Mage Tower built'
    budget.checkpoint()
    return dict(policy=policy, events=events, result=outcome, final=snapshot(state))


def scarcity_probe(payload, cls, *, earn_first, budget=None):
    budget = CpuBudget(25) if budget is None else budget
    state = cls.from_json(json.dumps(payload))
    events = [snapshot(state)]
    if earn_first:
        state.explore()
        finish_battle(state, budget=budget)
        events.append(snapshot(state))
    state.build('barracks')
    state.recruit('militia')
    events.append(snapshot(state))
    recruited_ids = {t.id for t in state.hero.army}
    for _ in range(4):
        budget.checkpoint()
        warning = state.upkeep_shortfall
        state.end_turn()
        assert state.battle is None and state.status == 'playing'
        events.append(dict(snapshot(state), shortfall_before_turn=warning))
        encoded = state.to_json()
        state = cls.from_json(encoded)
        assert state.to_json() == encoded
    budget.checkpoint()
    return dict(earn_first=earn_first, events=events,
                deserted_ids=sorted(recruited_ids - {t.id for t in state.hero.army}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT / 'docs/evidence/veteran-upkeep-prototype.json')
    parser.add_argument('--cpu-percent', type=float, default=25,
                        help='CPU allowance as a percent of one core (default 25; 100 for explicit stress)')
    args = parser.parse_args()
    try:
        budget = CpuBudget(args.cpu_percent)
    except ValueError as error:
        parser.error(str(error))
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), Path(__file__).resolve(),
                      *(ROOT / 'tools' / name for name in ('prototype_eador_late_realm.py', 'audit_eador_difficulty.py',
                      'audit_eador_economy.py', 'eador_linked_campaign.py', 'eador_campaign.py',
                      'stress_eador_control.py'))])
    hashes = {source_name(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    examples_path = ROOT / 'docs/evidence/crystal-service-comparison.examples.json'
    examples = json.loads(examples_path.read_text())
    plans = []
    for seed, hero, theme, mode in ((0, 'Commander', 'frontier', 'standard'),
                                  (0, 'Commander', 'frontier', 'challenge'),
                                  (7, 'Scout', 'elderwild', 'standard')):
        for plan in ('economy', 'sustain', 'spells'):
            case = (seed, hero, theme, plan, mode, 'direct')
            for name, cls in VARIANTS.items():
                row = paid_plan(case, cls, budget=budget)
                assert row == paid_plan(case, cls, budget=budget)
                row['experiment'] = name
                plans.append(row)
                print(case, name, row['result']['turns'], row['result']['gold_left'], row['result']['metrics']['lost_troops'])
    late = {}
    pursuit = {}
    recovery = {}
    for name, cls in VARIANTS.items():
        late[name] = {}
        for replace in (False, True):
            events = branch(examples['late_full_roster']['state'], cls, replace, budget=budget)
            assert events == branch(examples['late_full_roster']['state'], cls, replace, budget=budget)
            late[name]['replace_same_role' if replace else 'keep'] = events
        pursuit[name] = branch(examples['pursuit_last_action']['state'], cls, True, turns=1, budget=budget)
    recovery_inputs = {mode: recovery_input(mode, budget=budget) for mode in ('standard', 'challenge')}
    for mode, payload in recovery_inputs.items():
        for name, cls in VARIANTS.items():
            for policy in ('wait_three', 'shrine_first'):
                row = recovery_probe(payload, cls, policy, budget=budget)
                assert row == recovery_probe(payload, cls, policy, budget=budget)
                recovery[f'{mode}/{name}/{policy}'] = row
    scarcity = {}
    for name, cls in VARIANTS.items():
        for earn_first in (False, True):
            row = scarcity_probe(recovery_inputs['challenge'], cls, earn_first=earn_first, budget=budget)
            assert row == scarcity_probe(recovery_inputs['challenge'], cls, earn_first=earn_first, budget=budget)
            scarcity[f'{name}/{earn_first}'] = row
    report = dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  cpu_percent=budget.percent, source_sha256=hashes,
                  examples_sha256=hashlib.sha256(examples_path.read_bytes()).hexdigest(),
                  scope='NON-PRODUCTION runtime subclasses. Two wage coefficients; one paired ceiling variant. '
                        'Fixed public automatic paid plans and deliberately idle replacement-payback controls. '
                        'No production save policy or frozen rules ID was changed. No optimal-play claim.',
                  plans=plans, late_four_turns=late, pursuit_last_action=pursuit,
                  recovery_inputs=recovery_inputs, recovery=recovery, scarcity=scarcity)
    report['source_files_changed_during_run'] = [str(p.relative_to(ROOT)) for p in sources
        if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))]]
    assert not report['source_files_changed_during_run']
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    budget.checkpoint()
    print(args.report)


if __name__ == '__main__':
    main()
