#!/usr/bin/env python3
"""NON-PRODUCTION: exchange one of two retinue slots for a paid departure chest.

One hypothesis only: pay 100 current gold, receive 100 extra arrival gold. The
ordinary capped treasury carryover is calculated AFTER payment. No production
command, frozen profile, save field or recovery grant is modified.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from functools import partial
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eador.model import BUILDINGS, RuleError, State
from tools.audit_eador_economy import Trial
from tools.cpu_budget import CpuBudget
from tools.eador_campaign import finish_battle
from tools.eador_control_campaign import prepare_control_watch, watch_control_route
from tools.eador_extraction_campaign import AdventureOrders
from tools.eador_linked_campaign import lose_shard, play_stage, travel_selection

PRICE = GRANT = 100


def depart(state, offer_id, *, troop_ids=(), relic_ids=(), chest=False):
    """Atomic detached candidate; quote includes complete actual retinue consequences.

    The resulting ordinary v12 state contains the spent grant as cash, with no
    cargo token to redeem or refund. This is tooling evidence, not a supported
    production cargo-save interface. The original departure is never mutated.
    """
    before = state.to_json()
    if type(chest) is not bool:
        raise RuleError('Choose zero or one chest.')
    if chest and (state.campaign is None or state.campaign.phase != 'departure' or state.battle or state.choice):
        raise RuleError('A chest travels only on a completed shard departure, never on recovery.')
    if chest and (not isinstance(troop_ids, (tuple, list)) or len(troop_ids) > 1):
        raise RuleError('The chest takes one of the two troop slots.')
    if chest and state.gold < PRICE:
        raise RuleError('The chest costs 100 current gold.')
    candidate = State.from_json(before)
    ordinary_funding = state.expedition_funding()
    if chest:
        candidate.gold -= PRICE
    # Existing advance validates departure phase, offered contract, living IDs,
    # duplicates and relic ownership, and builds the candidate world atomically.
    candidate.advance(offer_id, troop_ids=troop_ids, relic_ids=relic_ids)
    if chest:
        candidate.gold += GRANT
    assert state.to_json() == before
    assert State.from_json(candidate.to_json()).to_json() == candidate.to_json()
    quote = dict(price=PRICE if chest else 0, grant=GRANT if chest else 0,
                 departure_gold=state.gold, gold_after_payment=state.gold - (PRICE if chest else 0),
                 slots_used=len(troop_ids) + int(chest), ordinary_funding=ordinary_funding,
                 arrival_gold=candidate.gold, arrival_crystals=candidate.crystals,
                 net_extra_arrival_gold=candidate.gold - ordinary_funding[0],
                 carried=[asdict(next(t for t in state.hero.army if t.id == uid)) for uid in troop_ids],
                 garrisoned=[asdict(t) for t in state.hero.army if t.id not in troop_ids],
                 actual_arrival_army=[asdict(t) for t in candidate.hero.army])
    return candidate, quote


class CargoTrial(Trial):
    """Two disclosed investment policies; all following orders are public game calls."""
    def __init__(self, state, policy, *, budget=None):
        budget = CpuBudget(25) if budget is None else budget
        watch = next(p.pos for p in state.provinces.values() if p.site_kind == 'border_watch')
        route = (((-2, 0), (-1, 0), (0, 0), watch, (1, 0), (2, 0))
                 if state.campaign.contract == 'rootward' else
                 ((-2, 0), (-1, 0), (0, -1), (0, 1), (1, 0), (2, 0)))
        super().__init__(state.seed, state.hero.hero_class, state.theme,
                         'economy' if policy == 'economy' else 'spells', state=state, route=route, budget=budget)
        self.policy = policy
        self.fights = []
        # Magic develops one Adept, a Swordsman and Temple, then normal Swordsmen.
        # Carrying an Adept skips its purchase, but still buys the Tower for Bolt.
        self.orders = [('build', 'mage_tower')]
        if not any(t.kind == 'adept' for t in state.hero.army):
            self.orders.append(('recruit', 'adept'))
        self.orders += [('build', 'barracks'), ('recruit', 'swordsman'), ('build', 'temple')]

    def invest(self):
        if self.policy == 'economy':
            return super().invest()
        state = self.state
        if state.status != 'playing':
            return
        while self.plan_step < len(self.orders):
            action, kind = self.orders[self.plan_step]
            if action == 'build':
                spec = BUILDINGS[kind]
                affordable = state.gold >= spec.cost and state.crystals >= spec.crystals
            else:
                if len(state.hero.army) == state.hero.max_army:
                    self.plan_step += 1
                    continue
                affordable = (state.gold >= state.recruit_cost(kind)
                              and state.crystals >= state.recruit_crystal_cost(kind))
            if not affordable:
                return
            self.buy(action, kind)
            self.plan_step += 1
        while len(state.hero.army) < state.hero.max_army and state.gold >= state.recruit_cost('swordsman'):
            self.buy('recruit', 'swordsman')

    def battle(self):
        state = self.state
        clone = State.from_json(state.to_json())
        finish_battle(clone, budget=self.budget)
        battle = state.battle
        record = dict(turn=state.turn, kind=state.battle_kind, province=state.battle_province,
                      encounter=state.battle_encounter, mana_before=battle.mana,
                      army_before=[asdict(t) for t in state.hero.army])
        super().battle()
        assert state.to_json() == clone.to_json(), 'saved tactical continuation differed'
        record.update(rounds=battle.round, outcome=battle.outcome,
                      spent=[dict(id=u.id, kind=u.kind, abilities=u.spent_abilities)
                             for u in battle.units if u.team == 'player' and u.spent_abilities],
                      army_after=[asdict(t) for t in state.hero.army], mana_after=state.hero.mana)
        self.fights.append(record)


def earned_departures(*, budget=None):
    budget = CpuBudget(25) if budget is None else budget
    ordinary = play_stage(State.new_campaign(7, 'Commander'), budget=budget)
    specialists = prepare_control_watch(State.new_campaign(0, 'Commander'), budget=budget)
    purchased_watch = json.loads(specialists.to_json())
    watch_control_route(specialists, orders_type=partial(AdventureOrders, budget=budget))
    finish_battle(specialists, budget=budget)
    specialists = play_stage(specialists, budget=budget)
    assert ordinary.campaign.phase == specialists.campaign.phase == 'departure'
    assert all(next(t for t in ordinary.hero.army if t.id == uid).kind == 'swordsman' for uid in (5, 4))
    adept = next(t for t in specialists.hero.army if t.id == 5)
    assert adept.kind == 'adept' and adept.level == 3
    budget.checkpoint()
    return dict(swords=dict(state=json.loads(ordinary.to_json()), offer='rootward', troops=(5, 4)),
                specialist=dict(state=json.loads(specialists.to_json()), offer='foundries', troops=(1, 5))), purchased_watch


def run_case(case, branch, policy, *, keep_id=None, budget=None):
    budget = CpuBudget(25) if budget is None else budget
    state = State.from_json(json.dumps(case['state']))
    ids = case['troops'] if branch == 'two_veterans' else (case['troops'][0] if keep_id is None else keep_id,)
    arrival, quote = depart(state, case['offer'], troop_ids=ids,
                            relic_ids=travel_selection(state)['relic_ids'], chest=branch == 'chest')
    saved = arrival.to_json()
    trial = CargoTrial(State.from_json(saved), policy, budget=budget)
    result = trial.run()
    budget.checkpoint()
    return dict(branch=branch, policy=policy, keep_id=keep_id, quote=quote, arrival=json.loads(saved),
                result=result, fights=trial.fights, final=json.loads(trial.state.to_json()))


def boundaries(case, *, budget=None):
    budget = CpuBudget(25) if budget is None else budget
    state = State.from_json(json.dumps(case['state']))
    relics = travel_selection(state)['relic_ids']
    failures = []

    def refuse(source, **options):
        budget.checkpoint()
        encoded = source.to_json()
        try:
            depart(source, options.pop('offer_id', case['offer']), relic_ids=relics, **options)
        except RuleError as error:
            assert source.to_json() == encoded
            failures.append(str(error))
        else:
            raise AssertionError('An invalid cargo order was accepted')

    refuse(state, troop_ids=case['troops'], chest=True)
    refuse(state, troop_ids=case['troops'][:1], chest=2)
    refuse(state, troop_ids=(99999,), chest=True)
    refuse(state, troop_ids=(case['troops'][0],) * 2, chest=False)
    refuse(state, troop_ids=(), chest=True, offer_id='not-offered')
    # Malformed/boundary treasury fixtures are clearly separate from earned runs.
    poor_data = json.loads(state.to_json()); poor_data['gold'] = PRICE - 1
    refuse(State.from_json(json.dumps(poor_data)), troop_ids=(), chest=True)
    exact_data = json.loads(state.to_json()); exact_data['gold'] = PRICE
    exact, exact_quote = depart(State.from_json(json.dumps(exact_data)), case['offer'], chest=True)
    assert exact.gold == state.rules.starting_gold + GRANT
    assert exact_quote['net_extra_arrival_gold'] == GRANT - 40
    empty, empty_quote = depart(state, case['offer'], chest=True)
    assert len(empty.hero.army) == 3 and all(t.kind == 'militia' and t.level == 1 for t in empty.hero.army)
    arrival, quote = depart(state, case['offer'], troop_ids=case['troops'][:1], relic_ids=relics, chest=True)
    before_loss = arrival.to_json()
    refuse(arrival, troop_ids=(), chest=True)
    lose_shard(arrival, budget=budget)
    assert arrival.campaign.phase == 'recovery'
    refuse(arrival, troop_ids=(), chest=True)
    lost = arrival.to_json()
    expected_funding = arrival.expedition_funding(recovery=True)
    arrival.recover(**travel_selection(arrival))
    assert (arrival.gold, arrival.crystals) == expected_funding
    assert arrival.campaign.recovery_used and arrival.campaign.phase == 'playing'
    assert State.from_json(arrival.to_json()).to_json() == arrival.to_json()
    refuse(arrival, troop_ids=(), chest=True)
    ordinary, _ = depart(state, case['offer'], troop_ids=case['troops'], relic_ids=relics)
    direct = State.from_json(state.to_json())
    direct.advance(case['offer'], troop_ids=case['troops'], relic_ids=relics)
    assert ordinary.to_json() == direct.to_json()
    budget.checkpoint()
    return dict(rejected=failures, empty_slot_quote=empty_quote, exact_price_quote=exact_quote,
                funded_arrival=json.loads(before_loss), actual_loss=json.loads(lost),
                recovery=json.loads(arrival.to_json()), recovery_funding=expected_funding,
                ordinary_advance_byte_exact=True,
                replay_note='Reloading a pre-departure save can replay the choice, as ordinary advance does; '
                            'an arrived save has no redeemable token and refuses a second departure.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT / 'docs/evidence/departure-cargo-prototype.json')
    parser.add_argument('--cpu-percent', type=float, default=25,
                        help='CPU allowance as a percent of one core (default 25; 100 for explicit stress)')
    args = parser.parse_args()
    try:
        budget = CpuBudget(args.cpu_percent)
    except ValueError as error:
        parser.error(str(error))
    sources = [*sorted((ROOT / 'eador').glob('*.py')), Path(__file__).resolve(),
               *(ROOT / 'tools' / name for name in ('eador_campaign.py', 'eador_linked_campaign.py',
                 'eador_control_campaign.py', 'eador_extraction_campaign.py', 'audit_eador_economy.py', 'cpu_budget.py'))]
    fingerprints = lambda: {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    before = fingerprints()
    cases, watch = earned_departures(budget=budget)
    rows = []
    for name, case in cases.items():
        for policy in ('economy', 'magic'):
            for branch in ('two_veterans', 'one_veteran', 'chest'):
                row = run_case(case, branch, policy, budget=budget)
                assert row == run_case(case, branch, policy, budget=budget)
                row['case'] = name
                rows.append(row)
                result = row['result']
                print(name, policy, branch, result['status'], result['turns'], result['gold_left'],
                      result['metrics']['lost_troops'], result['metrics']['battle_hp_attrition'])
    # A chest must not look worthwhile merely because the player leaves the
    # stronger role behind. Keep that same earned Adept as the competing choice.
    # The original two-veteran baseline keeps its original roster order (1, 5).
    for policy in ('economy', 'magic'):
        for branch in ('one_veteran', 'chest'):
            row = run_case(cases['specialist'], branch, policy, keep_id=5, budget=budget)
            assert row == run_case(cases['specialist'], branch, policy, keep_id=5, budget=budget)
            row['case'] = 'specialist_keep_adept'
            rows.append(row)
            print(row['case'], policy, branch, row['result']['turns'], row['result']['metrics']['lost_troops'])
    checks = boundaries(cases['swords'], budget=budget)
    assert before == fingerprints(), 'Source changed during the measurement'
    report = dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  cpu_percent=budget.percent, source_sha256=before, source_files_changed_during_run=[],
                  scope='NON-PRODUCTION. Two actual earned departures, three retinue choices, two disclosed '
                        'subsequent investment policies, plus keeping the expensive specialist instead. '
                        'Explicit automatic tactics; each fight paired with '
                        'saved continuation and each full branch repeated. No difficulty-balance claim. '
                        'One 100-gold price/100-gold grant hypothesis; no revision.',
                  inputs=cases, paid_control_watch=watch, runs=rows, boundaries=checks,
                  repeated_branches=len(rows), paired_saved_battles_per_pass=sum(len(row['fights']) for row in rows))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    # Compact records keep complete snapshots inspectable without tens of thousands of lines.
    args.report.write_text(json.dumps(report, separators=(',', ':')) + '\n')
    budget.checkpoint()
    print(args.report)


if __name__ == '__main__':
    main()
