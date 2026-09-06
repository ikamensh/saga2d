#!/usr/bin/env python3
"""NON-PRODUCTION: test limited remittance and finite outposts on earned realm decisions.

No shipped policy, saved rules ID, model command or registry is changed. Runtime
subclasses are explicit experiment adapters; their JSON is evidence, not a new
supported game-save policy. All following turns, purchases and fights use the
existing public campaign commands and tactical rules.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eador.model import State, UNITS
from tools.audit_eador_difficulty import DifficultyTrial
from tools.eador_campaign import finish_battle


class MeasuredState(State):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cash_flow = []

    def build(self, kind):
        super().build(kind)
        self.cash_flow.append(dict(command='build.' + kind, turn=self.turn, gold=self.gold))

    def end_turn(self):
        before = dict(command='end_turn', turn=self.turn, gold_before=self.gold,
                      ordinary_income=State.income.fget(self), income=self.income,
                      upkeep=self.upkeep, provinces=sum(p.owner == 'player' for p in self.provinces.values()),
                      shortfall=self.upkeep_shortfall)
        super().end_turn()
        self.cash_flow.append(dict(before, gold_after=self.gold))


class LimitedRemittance(MeasuredState):
    """Counterfactual R1: capital/Market + richest two provinces full; others quarter."""
    @property
    def income(self):
        home = self.provinces[(-2, 0)]
        central = home.income if home.owner == 'player' and not self.encircled else 0
        market = 8 if 'market' in self.buildings and not self.encircled else 0
        provinces = sorted((p.income for p in self.provinces.values()
                            if p.owner == 'player' and p.pos != (-2, 0)), reverse=True)
        full = central + market + sum(provinces[:2])
        # Round once after both remittance and the unchanged saved mode's percentage.
        return (4 * full + sum(provinces[2:])) * self.rules.gold_percent // 400


class FiniteOutpost(State):
    """Counterfactual O1 charges normal upkeep for finite friendly province guards.

    These solvent one-turn probes do not invent a guard desertion rule. Bankruptcy,
    hero-plus-outpost deployment and force-aware rival planning remain design gaps.
    """
    @property
    def upkeep(self):
        return super().upkeep + sum(UNITS[kind].upkeep for p in self.provinces.values()
                                   if p.owner == 'player' for kind in p.guards)


def snapshot(state):
    return dict(turn=state.turn, gold=state.gold, crystals=state.crystals,
                actions=state.actions_left, income=state.income, upkeep=state.upkeep,
                shortfall=state.upkeep_shortfall, mana=state.hero.mana,
                hero_hp=state.hero.hp, hero_rank=state.hero.level, hero_xp=state.hero.xp,
                army=[asdict(t) for t in state.hero.army],
                rival=asdict(state.rival), heartwood=asdict(state.provinces[(0, 0)]))


def paid_plan(case, cls):
    trial = DifficultyTrial(*case)
    trial.state = cls.from_json(trial.state.to_json())
    result = trial.run()
    return dict(case=case, experiment='ordinary' if cls is MeasuredState else 'remittance-r1',
                result=result, cash_flow=trial.state.cash_flow)


def late_quote(payload, cls):
    """Future cash flow only: never claw back wealth earned in the original save."""
    original = State.from_json(json.dumps(payload))
    before = original.to_json()
    state = cls.from_json(before)
    operations = []
    for kind in ('archery', 'mage_tower'):
        state.build(kind)
        operations.append(dict(command='build', kind=kind, after=snapshot(state)))
    quote = state.replacement_preview(state.hero.army[0].id, 'warden')
    infusion = state.infusion_preview()
    assert quote.blocked_reason is None and infusion.blocked_reason is None
    state.replace_troop(quote.outgoing.id, 'warden')
    state.infuse()
    operations.append(dict(command='replace Warden then infuse', quote=asdict(quote),
                           infusion=asdict(infusion), after=snapshot(state)))
    assert state.actions_left == 0
    state.end_turn()
    operations.append(dict(command='end_turn', after=snapshot(state)))
    assert original.to_json() == before
    return operations


def buy_outpost(state, kinds):
    """Dispatch two paid recruits to the adjacent warned friendly province: one action.

    Prototype-only mutation of a detached validated save. No free troop, health,
    prerequisite, refund or experience is supplied. Existing public battle rules
    resolve the ensuing clash, including lasting casualties on both sides.
    """
    before = state.to_json()
    target = state.rival.target
    assert state.status == 'playing' and state.battle is None and state.choice is None
    assert state.actions_left > 0 and target in state.grid.neighbors(state.hero.pos)
    assert state.provinces[state.hero.pos].owner == state.provinces[target].owner == 'player'
    assert not state.provinces[target].guards and len(kinds) == 2
    assert all(UNITS[k].building in state.buildings for k in kinds)
    gold = sum(state.recruit_cost(k) for k in kinds)
    crystals = sum(state.recruit_crystal_cost(k) for k in kinds)
    assert state.gold >= gold and state.crystals >= crystals
    data = json.loads(before)
    data['gold'] -= gold
    data['crystals'] -= crystals
    data['actions_left'] -= 1
    province = next(p for p in data['provinces'] if tuple(p['pos']) == target)
    province['guards'], province['guard_hp'] = list(kinds), [UNITS[k].hp for k in kinds]
    result = FiniteOutpost.from_json(json.dumps(data))
    assert state.to_json() == before and result.upkeep_shortfall == 0
    return result, dict(target=target, kinds=kinds, gold=gold, crystals=crystals, actions=1,
                        added_upkeep=sum(UNITS[k].upkeep for k in kinds))


def pursuit(payload, policy, *, reload_turns=True):
    state = State.from_json(json.dumps(payload))
    original = state.to_json()
    initial_ids = {t.id for t in state.hero.army}
    operations, quote = [], None
    if policy == 'tower_infuse':
        state.build('mage_tower')
        state.infuse()
        operations.append(dict(command='build Mage Tower then infuse', state=snapshot(state)))
    if policy.startswith('outpost'):
        if policy == 'outpost_bow':
            state.build('archery')
            operations.append(dict(command='build archery', state=snapshot(state)))
        kinds = ('pikeman', 'archer') if policy == 'outpost_bow' else ('pikeman', 'pikeman')
        state, quote = buy_outpost(state, kinds)
        operations.append(dict(command='PROTOTYPE dispatch outpost', quote=quote, state=snapshot(state)))
    if policy == 'intercept':
        state.travel(state.rival.pos)
        finish_battle(state)
        operations.append(dict(command='intercept with explicit auto combat', state=snapshot(state)))
    else:
        state.end_turn()
        assert state.battle is None
        operations.append(dict(command='end_turn: actual rival operation', state=snapshot(state)))
        if reload_turns:
            state = type(state).from_json(state.to_json())
        # Recapture the province / finish the wounded expedition through public orders.
        state.travel(state.rival.pos)
        finish_battle(state)
        operations.append(dict(command='intercept after waiting with explicit auto combat', state=snapshot(state)))
    assert State.from_json(original).to_json() == original
    assert State.from_json(state.to_json()).to_json() == state.to_json()
    return dict(policy=policy, quote=quote, operations=operations,
                lost_hero_troops=sorted(initial_ids - {t.id for t in state.hero.army}),
                final=snapshot(state), final_save_sha256=hashlib.sha256(state.to_json().encode()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT / 'docs/evidence/late-realm-prototype.json')
    args = parser.parse_args()
    example_path = ROOT / 'docs/evidence/crystal-service-comparison.examples.json'
    examples = json.loads(example_path.read_text())
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), Path(__file__).resolve(),
                      *(ROOT / 'tools' / name for name in ('audit_eador_difficulty.py', 'audit_eador_economy.py',
                                                         'stress_eador_control.py', 'eador_campaign.py'))])
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    plans = []
    for seed, hero, theme, mode in ((0, 'Commander', 'frontier', 'standard'),
                                  (0, 'Commander', 'frontier', 'challenge'),
                                  (7, 'Scout', 'elderwild', 'standard')):
        for plan in ('economy', 'sustain', 'spells'):
            case = (seed, hero, theme, plan, mode, 'direct')
            for cls in (MeasuredState, LimitedRemittance):
                row = paid_plan(case, cls)
                assert row == paid_plan(case, cls)
                plans.append(row)
                print(case, row['experiment'], row['result']['status'], row['result']['turns'], row['result']['gold_left'])
    late = {name: late_quote(examples['late_full_roster']['state'], cls)
            for name, cls in (('ordinary', MeasuredState), ('remittance-r1', LimitedRemittance))}
    outposts = []
    for policy in ('intercept', 'rest', 'tower_infuse', 'outpost_pikes', 'outpost_bow'):
        row = pursuit(examples['pursuit_last_action']['state'], policy)
        assert row == pursuit(examples['pursuit_last_action']['state'], policy, reload_turns=False)
        outposts.append(row)
        print(policy, row['final']['gold'], row['final']['mana'], row['lost_hero_troops'])
    report = dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, examples_sha256=hashlib.sha256(example_path.read_bytes()).hexdigest(),
                  caveat='NON-PRODUCTION runtime experiments, not a supported new saved rules profile. '
                         'No production registry, frozen ID, model command, tactical formula or schema changed. '
                         'Nine selected paid plan pairs, not a balance matrix. Outpost bankruptcy and combined '
                         'hero/garrison deployment are intentionally not invented by the prototype.',
                  parameters={'remittance-r1': {'full_outside_provinces': 2, 'further_gold_percent': 25},
                              'outpost-o1': {'fresh_troops': 2, 'actions': 1, 'price_and_upkeep': 'ordinary public costs',
                                             'destination': 'adjacent owned province', 'automatic_healing': False}},
                  plans=plans, late_current_cash=late, pursuit=outposts)
    report['source_files_changed_during_run'] = [str(p.relative_to(ROOT)) for p in sources
                                                if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))]]
    assert not report['source_files_changed_during_run']
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(args.report)


if __name__ == '__main__':
    main()
