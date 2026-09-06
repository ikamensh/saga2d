#!/usr/bin/env python3
"""Attribute earned resources and quote actual options without changing paid policies.

Default sample: seed 0 Commander, three established plans, every theme and mode.
Detached public-command quotes diagnose available alternatives; they do not claim
the player wants every option or that a lower treasury improves the game.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eador.difficulty import DIFFICULTIES
from eador.model import BUILDINGS, RECRUITABLE, RuleError, State, UNITS
from eador.worldgen import THEMES
from tools.audit_eador_difficulty import DifficultyTrial
from tools.audit_eador_economy import PLANS

FUNDS_ERRORS = {'Not enough gold or crystals.', 'Infusion requires 3 crystals.'}
COMMANDS = {'build', 'recruit', 'replace_troop', 'infuse', 'travel', 'explore',
            'end_turn', 'resolve_battle', 'retreat', 'choose', 'equip'}


def public_quote(encoded, orders, *, name, gold, crystals, kind):
    """Try only the announced orders on an independent complete save."""
    state = State.from_json(encoded)
    original = state.to_json()
    reason = None
    for command, args, kwargs in orders:
        before = state.to_json()
        try:
            getattr(state, command)(*args, **kwargs)
        except RuleError as error:
            assert state.to_json() == before
            reason = str(error)
            break
    # The quote uses normal prices and actual refusal precedence. An available
    # building followed by an unaffordable recruit is still a funded-package gap.
    return dict(name=name, kind=kind, gold=gold, crystals=crystals,
                affordable=reason is None, funds_blocked=reason in FUNDS_ERRORS,
                blocked_reason=reason, source_sha256=hashlib.sha256(original.encode()).hexdigest())


def options(state):
    if state.status != 'playing' or state.battle or state.choice:
        return None
    encoded = state.to_json()
    quotes = []
    for kind, spec in BUILDINGS.items():
        if kind not in state.buildings:
            quotes.append(public_quote(encoded, [('build', (kind,), {})], name='build.' + kind,
                                       gold=spec.cost, crystals=spec.crystals, kind='building'))
    outgoing = min(state.hero.army, key=lambda t: (t.level, t.xp, t.id), default=None)
    present = {t.kind for t in state.hero.army}
    for kind in RECRUITABLE:
        if kind in present:
            continue
        orders = []
        building = UNITS[kind].building
        price, crystals = state.recruit_cost(kind), state.recruit_crystal_cost(kind)
        if building and building not in state.buildings:
            orders.append(('build', (building,), {}))
            price += BUILDINGS[building].cost
            crystals += BUILDINGS[building].crystals
        replacing = len(state.hero.army) >= state.hero.max_army
        if replacing:
            orders.append(('replace_troop', (outgoing.id, kind), {}))
        else:
            orders.append(('recruit', (kind,), {}))
        if replacing and not state.actions_left:
            # Buying a prerequisite first must not disguise an action block as a
            # funds block. The proposed complete package cannot execute now.
            reason = state.replacement_preview(outgoing.id, kind).blocked_reason
            quote = dict(name='replace.' + kind, kind='missing_role_package', gold=price,
                         crystals=crystals, affordable=False, funds_blocked=False, blocked_reason=reason)
        else:
            quote = public_quote(encoded, orders, name=('replace.' if replacing else 'recruit.') + kind,
                                 gold=price, crystals=crystals, kind='missing_role_package')
        quote.update(outgoing=asdict(outgoing) if replacing else None,
                     prerequisites=[o[1][0] for o in orders if o[0] == 'build'])
        quotes.append(quote)
    infusion = state.infusion_preview()
    if infusion.mana:
        quotes.append(dict(name='infuse', kind='service', gold=0, crystals=infusion.crystals,
                           affordable=infusion.blocked_reason is None,
                           funds_blocked=infusion.blocked_reason in FUNDS_ERRORS,
                           blocked_reason=infusion.blocked_reason, mana_gain=infusion.mana))
    if not state.provinces[state.hero.pos].explored:
        for approach in state.adventure_approaches():
            if approach.gold_cost or approach.crystals_cost:
                quotes.append(public_quote(encoded, [('explore', (), dict(approach=approach.id))],
                                           name='approach.' + approach.id, kind='local_approach',
                                           gold=approach.gold_cost, crystals=approach.crystals_cost))
    assert state.to_json() == encoded, 'Quotes changed the real campaign'
    available = [q for q in quotes if q['affordable'] or q['funds_blocked']]
    # A stronger upper bound distinguishes one affordable order from being able
    # to buy the remaining building catalogue AND its most expensive absent role.
    missing_buildings = [(kind, spec) for kind, spec in BUILDINGS.items() if kind not in state.buildings]
    absent = [kind for kind in RECRUITABLE if kind not in present]
    completion_orders = [('build', (kind,), {}) for kind, _ in missing_buildings]
    completion_gold = sum(spec.cost for _, spec in missing_buildings)
    completion_crystals = sum(spec.crystals for _, spec in missing_buildings)
    if absent:
        kind = max(absent, key=lambda kind: (state.recruit_cost(kind), state.recruit_crystal_cost(kind)))
        completion_orders.append(('replace_troop', (outgoing.id, kind), {}) if len(state.hero.army) >= state.hero.max_army
                                 else ('recruit', (kind,), {}))
        completion_gold += state.recruit_cost(kind)
        completion_crystals += state.recruit_crystal_cost(kind)
    if absent and len(state.hero.army) >= state.hero.max_army and not state.actions_left:
        completion = dict(affordable=False, funds_blocked=False, blocked_reason='No campaign actions remain. End the turn.',
                          gold=completion_gold, crystals=completion_crystals)
    else:
        completion = public_quote(encoded, completion_orders, name='remaining_buildings_and_role',
                                  kind='catalogue_upper_bound', gold=completion_gold, crystals=completion_crystals)
    return dict(turn=state.turn, gold=state.gold, crystals=state.crystals, actions=state.actions_left,
                income=state.income, upkeep=state.upkeep, crystal_income=state.crystal_income,
                army_size=len(state.hero.army), capacity=state.hero.max_army,
                army=[asdict(t) for t in state.hero.army], buildings=sorted(state.buildings),
                position=state.hero.pos, rival=asdict(state.rival), recovery=asdict(state.recovery_preview()),
                quotes=quotes, funds_blocked=[q['name'] for q in quotes if q['funds_blocked']],
                money_unconstrained=bool(available) and all(q['affordable'] for q in available),
                no_resource_option=not available, completion=completion, _save=encoded)


class Ledger:
    """Read-only observer around the commands used by the unchanged development trial."""
    def __init__(self, state):
        self.state = state
        self.flows = defaultdict(Counter)
        self.events = []
        self.points = []
        self.add('start', state.gold, state.crystals)
        self.observe('new_game')

    def __getattr__(self, name):
        target = getattr(self.state, name)
        if name in COMMANDS:
            return lambda *args, **kwargs: self.command(name, *args, **kwargs)
        return target

    def add(self, source, gold, crystals):
        self.flows[source].update(gold=gold, crystals=crystals)

    def observe(self, phase):
        point = options(self.state)
        if point:
            point.update(phase=phase, event_index=len(self.events),
                         flows={key: dict(value) for key, value in self.flows.items()})
            self.points.append(point)

    def command(self, command, *args, **kwargs):
        state = self.state
        gold, crystals, turn = state.gold, state.crystals, state.turn
        context = dict(battle_kind=state.battle_kind, province=state.battle_province,
                       choice_kind=state.choice.kind if state.choice else None)
        if command == 'end_turn':
            context.update(income=state.income, crystal_income=state.crystal_income,
                           production=[dict(pos=p.pos, gold=p.income, crystals=p.crystals)
                                       for p in state.provinces.values() if p.owner == 'player'
                                       and not (state.encircled and p.pos == (-2, 0))],
                           market_raw_gold=8 if 'market' in state.buildings and not state.encircled else 0,
                           gold_percent=state.rules.gold_percent)
        result = getattr(state, command)(*args, **kwargs)
        delta = (state.gold - gold, state.crystals - crystals)
        if command == 'end_turn':
            # Rival movement can change the *next* income after payment. Use the
            # observed pre-turn amount, but the actual surviving army's bill.
            self.add('recurring_income', context['income'], context['crystal_income'])
            self.add('upkeep', -state.upkeep, 0)
            assert delta == (context['income'] - state.upkeep, context['crystal_income'])
        elif command in ('build', 'recruit', 'replace_troop', 'infuse', 'explore'):
            category = ('building.' + args[0] if command == 'build' else
                        {'recruit': 'recruitment', 'replace_troop': 'replacement',
                         'infuse': 'infusion', 'explore': 'paid_approach'}[command])
            self.add(category, *delta)
        elif command in ('resolve_battle', 'retreat'):
            category = ('retreat_loss' if delta[0] < 0 else
                        'site_reward' if context['battle_kind'] == 'site' else
                        'capture_reward' if context['battle_kind'] == 'conquest' else 'expedition_reward')
            self.add(category, *delta)
        elif command == 'choose' and delta != (0, 0):
            self.add('relic_sale' if delta[0] else 'duplicate_crystals', *delta)
        else:
            assert delta == (0, 0), (command, delta)
        assert sum(flow['gold'] for flow in self.flows.values()) == state.gold
        assert sum(flow['crystals'] for flow in self.flows.values()) == state.crystals
        self.events.append(dict(command=command, args=args, kwargs=kwargs, turn=turn,
                                gold_before=gold, crystals_before=crystals, delta=delta,
                                gold_after=state.gold, crystals_after=state.crystals, context=context))
        self.observe(command)
        return result


def measured(case):
    trial = DifficultyTrial(*case)
    ledger = Ledger(trial.state)
    trial.state = ledger
    result = trial.run()
    # The observer must preserve the full policy output and actual final save.
    baseline = DifficultyTrial(*case).run()
    assert result == baseline, 'Attribution changed a public campaign outcome'
    constrained = [i for i, p in enumerate(ledger.points) if p['funds_blocked']]
    last = constrained[-1] if constrained else -1
    tail = next((p for p in ledger.points[last + 1:] if p['money_unconstrained']), None)
    first = next((p for p in ledger.points if p['money_unconstrained']), None)
    last_point = ledger.points[last] if last >= 0 else None
    last_completion_constraint = max((i for i, p in enumerate(ledger.points) if p['completion']['funds_blocked']), default=-1)
    completion = next((p for p in ledger.points[last_completion_constraint + 1:] if p['completion']['affordable']), None)
    endpoints = {}
    for key, point in (('first_affordable', first), ('last_funds_constraint', last_point),
                       ('lasting_breakpoint', tail), ('catalogue_completion', completion)):
        if point:
            endpoints[key] = {**point, 'state': json.loads(point['_save'])}
            endpoints[key].pop('_save')
    for point in ledger.points:
        point.pop('_save')
    return dict(case=case, result=result, flows={k: dict(v) for k, v in ledger.flows.items()},
                decisions=ledger.points, events=ledger.events, endpoints=endpoints)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--hero', choices=('Commander', 'Warrior', 'Scout', 'Wizard'), default='Commander')
    parser.add_argument('--report', type=Path, default=ROOT / 'docs/evidence/resource-breakpoints.json')
    args = parser.parse_args()
    sources = [*sorted((ROOT / 'eador').glob('*.py')), Path(__file__).resolve(),
               *(ROOT / 'tools' / name for name in ('audit_eador_difficulty.py', 'audit_eador_economy.py',
                 'eador_campaign.py', 'stress_eador_control.py'))]
    fingerprints = lambda: {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    before = fingerprints()
    rows = []
    for theme in THEMES:
        for mode in DIFFICULTIES:
            for plan in PLANS:
                row = measured((args.seed, args.hero, theme, plan, mode, 'direct'))
                rows.append(row)
                point = row['endpoints'].get('lasting_breakpoint')
                print(theme, mode, plan, row['result']['status'], row['result']['turns'],
                      'breakpoint', point['turn'] if point else None, flush=True)
    assert before == fingerprints()
    groups = defaultdict(list)
    for row in rows:
        groups[row['case'][2]].append(row)
        groups[row['case'][4]].append(row)
        groups[row['case'][3]].append(row)
    summary = {}
    for group, items in groups.items():
        flows = defaultdict(Counter)
        for row in items:
            for source, amounts in row['flows'].items():
                flows[source].update(amounts)
        points = [r['endpoints']['lasting_breakpoint'] for r in items if 'lasting_breakpoint' in r['endpoints']]
        summary[group] = dict(runs=len(items), outcomes=dict(Counter(r['result']['status'] for r in items)),
                              flows={k: dict(v) for k, v in flows.items()},
                              breakpoints=[p['turn'] for p in points],
                              final_gold=[r['result']['gold_left'] for r in items],
                              final_crystals=[r['result']['crystals_left'] for r in items])
    after_breakpoint = defaultdict(Counter)
    for row in rows:
        point = row['endpoints'].get('lasting_breakpoint')
        if point:
            for source in row['flows'].keys() | point['flows'].keys():
                for currency in ('gold', 'crystals'):
                    after_breakpoint[source][currency] += (row['flows'].get(source, {}).get(currency, 0)
                                                           - point['flows'].get(source, {}).get(currency, 0))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    rows_path = args.report.with_suffix('.rows.json.gz')
    rows_path.write_bytes(gzip.compress(json.dumps(rows, separators=(',', ':')).encode(), mtime=0))
    report = dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=before, source_files_changed_during_run=[], seed=args.seed, hero=args.hero,
                  campaigns=len(rows), matched_unobserved_outcomes=True, summary=summary,
                  after_individual_breakpoint={k: dict(v) for k, v in after_breakpoint.items()},
                  scope='Observed unchanged public paid policies. Actual command deltas reconcile both currencies. '
                        'Detached public quotes for unbuilt buildings, absent-role recruitment/replacement with '
                        'prerequisites, needed infusion and local paid approaches. Funds constraints exclude '
                        'other refusals such as actions. The breakpoint is conditional on this actual policy; '
                        'affordable does not mean desirable. No production/counterfactual rules changed.',
                  rows_file=rows_path.name, rows_sha256=hashlib.sha256(rows_path.read_bytes()).hexdigest())
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(args.report)


if __name__ == '__main__':
    main()
