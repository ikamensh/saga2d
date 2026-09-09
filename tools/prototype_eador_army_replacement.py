#!/usr/bin/env python3
"""NON-PRODUCTION: does retiring a veteran buy a useful late-game role choice?

One proposed replacement changes only a cloned save: pay the ordinary incoming
recruit price and one action, retire a named troop permanently, and insert a
fresh recruit in that formation slot. There is no refund, reserve or XP transfer.
All subsequent orders and saved battle continuations use the actual game API.
This is retained experiment code, not an available player command.

Run: uv run python tools/prototype_eador_army_replacement.py
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eador.model import BUILDINGS, RECRUITABLE, RuleError, State, UNITS
from tools.eador_sources import source_name
from tools.audit_eador_difficulty import DifficultyTrial
from saga2d.testing.cpu_budget import CpuBudget


def prototype_replace(state, outgoing_id, kind):
    """Return a validated counterfactual; never modify the supplied real state."""
    if state.status != 'playing' or state.battle or state.choice:
        raise RuleError('Replace between battles and pending decisions.')
    if state.provinces[state.hero.pos].owner != 'player':
        raise RuleError('Replace in a friendly camp.')
    if not state.actions_left:
        raise RuleError('Replacement costs one action.')
    if kind not in RECRUITABLE:
        raise RuleError('Choose a recruitable troop.')
    spec = UNITS[kind]
    if spec.building and spec.building not in state.buildings:
        raise RuleError('Build the normal recruitment prerequisite.')
    index = next((i for i, troop in enumerate(state.hero.army) if troop.id == outgoing_id), None)
    if index is None:
        raise RuleError('Choose a living troop to retire.')
    gold, crystals = state.recruit_cost(kind), state.recruit_crystal_cost(kind)
    if state.gold < gold or state.crystals < crystals:
        raise RuleError('Pay the ordinary incoming recruitment cost.')
    before = state.to_json()
    data = json.loads(before)
    outgoing = data['hero']['army'][index]
    incoming = dict(id=data['next_troop_id'], kind=kind, hp=spec.hp,
                    max_hp=spec.hp, level=1, xp=0)
    data['hero']['army'][index] = incoming
    data['next_troop_id'] += 1
    data['gold'] -= gold
    data['crystals'] -= crystals
    data['actions_left'] -= 1
    result = State.from_json(json.dumps(data))
    assert state.to_json() == before
    return result, dict(gold=gold, crystals=crystals, actions=1,
                        formation_index=index, retired=outgoing, incoming=incoming)


def snapshot(state):
    return dict(turn=state.turn, status=state.status, position=state.hero.pos,
                gold=state.gold, crystals=state.crystals, actions=state.actions_left,
                income=state.income, upkeep=state.upkeep,
                hero_hp=state.hero.hp, hero_max_hp=state.hero.max_hp,
                mana=state.hero.mana, max_mana=state.hero.max_mana,
                army=[asdict(troop) for troop in state.hero.army],
                central_owner=state.provinces[(0, 0)].owner,
                capital_owner=state.provinces[(2, 0)].owner,
                rival=asdict(state.rival))


def exercise(payload, kind=None, *, rest=False, pursuit=False, reload_rounds=True, budget=None):
    budget = CpuBudget(25) if budget is None else budget
    state = State.from_json(json.dumps(payload))
    operations = [dict(command='load retained paid state', state=snapshot(state))]
    replacement = None
    if kind:
        state, replacement = prototype_replace(state, 1, kind)
        state = State.from_json(state.to_json())
        operations.append(dict(command='PROTOTYPE replace', quote=replacement, state=snapshot(state)))
    if rest or not state.actions_left:
        budget.checkpoint()
        state.end_turn()
        assert state.battle is None, 'The disclosed local waiting branch changed.'
        operations.append(dict(command='end_turn', state=snapshot(state)))
    target = state.rival.pos if pursuit else (2, 0)
    budget.checkpoint()
    state.travel(target)
    assert state.battle is not None
    operations.append(dict(command='travel', target=target, state=snapshot(state)))
    battle_kind = state.battle_kind
    initial_battle = state.battle.to_dict()
    initial_ids = {troop.id for troop in state.hero.army}
    rounds = []
    for _ in range(80):
        budget.checkpoint()
        battle = state.battle
        if battle.outcome:
            break
        start_round, start_log = battle.round, len(battle.log)
        battle.auto_turn()
        rounds.append(dict(round=start_round, commands='explicit auto_turn',
                           log=battle.log[start_log:],
                           units=[asdict(unit) for unit in battle.units], mana=battle.mana))
        if reload_rounds:
            encoded = state.to_json()
            state = State.from_json(encoded)
            assert state.to_json() == encoded
    assert state.battle.outcome
    final_battle = state.battle.to_dict()
    dead_ids = [unit.id for unit in state.battle.units
                if unit.team == 'player' and unit.id != 0 and unit.hp == 0]
    state.resolve_battle()
    while state.choice:
        budget.checkpoint()
        state.choose(state.choice.options[0].id)
    assert initial_ids - {troop.id for troop in state.hero.army} == set(dead_ids)
    encoded = state.to_json()
    assert State.from_json(encoded).to_json() == encoded
    budget.checkpoint()
    return dict(replacement=replacement, rest_requested=rest,
                operations=operations, battle_kind=battle_kind,
                initial_battle=initial_battle, rounds=rounds, final_battle=final_battle,
                dead_in_battle=dead_ids, retired_ids=[1] if kind else [],
                surviving_army_wounds=sum(t.max_hp - t.hp for t in state.hero.army),
                final=snapshot(state), final_save_sha256=hashlib.sha256(encoded.encode()).hexdigest())


class GoldLedger(State):
    """Observe public command cash flows; the normal game's result must match."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ledger = []

    def record(self, label, command, *args):
        before, turn = self.gold, self.turn
        result = command(*args)
        if before != self.gold:
            self.ledger.append(dict(turn=turn, command=label, delta=self.gold - before, gold=self.gold))
        return result

    def build(self, kind):
        return self.record('build.' + kind, super().build, kind)

    def recruit(self, kind):
        return self.record('recruit.' + kind, super().recruit, kind)

    def end_turn(self):
        return self.record('net_income_after_upkeep', super().end_turn)

    def resolve_battle(self):
        return self.record('battle.' + self.battle_kind, super().resolve_battle)

    def choose(self, option):
        return self.record('choice.' + self.choice.kind, super().choose, option)


def investment_observation(payload, *, budget=None):
    budget = CpuBudget(25) if budget is None else budget
    full = State.from_json(json.dumps(payload))
    before = full.to_json()
    try:
        full.recruit('pikeman')
    except RuleError as error:
        rejection = str(error)
    else:
        raise AssertionError('The full army unexpectedly recruited a troop.')
    assert full.to_json() == before
    missing = []
    for kind in BUILDINGS:
        budget.checkpoint()
        if kind not in full.buildings:
            missing.append(dict(kind=kind, gold=BUILDINGS[kind].cost, crystals=BUILDINGS[kind].crystals))
            full.build(kind)
    quotes = {kind: dict(gold=full.recruit_cost(kind), crystals=full.recruit_crystal_cost(kind))
              for kind in ('pikeman', 'warden', 'ranger', 'sapper', 'adept', 'skyrider')}
    after_building = snapshot(full)
    full.end_turn()
    after_waiting = snapshot(full)
    case = (0, 'Commander', 'frontier', 'economy', 'standard', 'direct')
    trial = DifficultyTrial(*case, budget=budget)
    trial.state = GoldLedger.from_json(trial.state.to_json())
    start_gold = trial.state.gold
    result = trial.run()
    assert result == DifficultyTrial(*case, budget=budget).run(), 'Observing gold changed the paid policy.'
    totals = Counter()
    for event in trial.state.ledger:
        totals[event['command'].split('.')[0]] += event['delta']
    assert start_gold + sum(totals.values()) == trial.state.gold
    budget.checkpoint()
    return dict(full_army_rejection=rejection, missing_buildings_bought=missing,
                after_buildings=after_building, after_one_wait=after_waiting, role_quotes=quotes,
                ledger_case=case, ledger_start_gold=start_gold, ledger=trial.state.ledger,
                ledger_totals=dict(totals), ledger_result=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--examples', type=Path, default=ROOT / 'docs/evidence/crystal-service-comparison.examples.json')
    parser.add_argument('--report', type=Path, default=ROOT / 'docs/evidence/army-replacement-prototype.json.gz')
    parser.add_argument('--cpu-percent', type=float, default=25,
                        help='CPU allowance as a percent of one core (default 25; 100 for explicit stress)')
    args = parser.parse_args()
    try:
        budget = CpuBudget(args.cpu_percent)
    except ValueError as error:
        parser.error(str(error))
    examples = json.loads(args.examples.read_text())
    complete_camp = State.from_json(json.dumps(examples['late_full_roster']['state']))
    for building in ('archery', 'mage_tower'):
        budget.checkpoint()
        complete_camp.build(building)
    examples['late_all_buildings'] = dict(state=json.loads(complete_camp.to_json()))
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), Path(__file__),
                      *[ROOT / 'tools' / name for name in ('audit_eador_difficulty.py', 'audit_eador_economy.py',
                                                         'stress_eador_control.py', 'eador_campaign.py')]])
    hashes = {source_name(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    runs = {}
    for name, variants in {
        'late_all_buildings': ((None, False), (None, True), ('pikeman', False),
                              ('warden', False), ('skyrider', False), ('militia', False)),
        'late_full_roster': ((None, False), (None, True), ('pikeman', False), ('warden', False),
                             ('pikeman', True), ('warden', True), ('skyrider', False), ('skyrider', True),
                             ('militia', False), ('militia', True)),
        'pursuit_last_action': ((None, False), (None, True), ('warden', False)),
    }.items():
        runs[name] = []
        for kind, rest in variants:
            options = dict(rest=rest, pursuit=name == 'pursuit_last_action', budget=budget)
            run = exercise(examples[name]['state'], kind, **options)
            # Real saves after every tactical round continue exactly like no reloads.
            assert run == exercise(examples[name]['state'], kind, reload_rounds=False, **options)
            runs[name].append(run)
            final = run['final']
            print(f'{name}: {kind or "keep"}, rest={rest}: turn {final["turn"]}, '
                  f'{len(run["dead_in_battle"])} battle deaths + {len(run["retired_ids"])} retired, '
                  f'{final["gold"]}g/{final["crystals"]}c, hero {final["hero_hp"]}HP, '
                  f'{run["surviving_army_wounds"]} army wounds')
        # Replacement does not reroll the imminent battlefield or defending party.
        baseline = runs[name][0]['initial_battle']
        for run in runs[name]:
            if run['operations'][-1]['state']['turn'] == runs[name][0]['operations'][-1]['state']['turn']:
                actual = run['initial_battle']
                assert actual['terrain'] == baseline['terrain']
                assert actual['objective'] == baseline['objective']
                enemy = lambda data: [{key: value for key, value in unit.items() if key != 'id'}
                                      for unit in data['units'] if unit['team'] == 'enemy']
                assert enemy(actual) == enemy(baseline)
    report = dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  cpu_percent=budget.percent,
                  source_sha256=hashes, examples_sha256=hashlib.sha256(args.examples.read_bytes()).hexdigest(),
                  policy='NON-PRODUCTION normal-price, one-action replacement of troop 1 in its original formation slot; '
                         'fresh rank/XP/ID, no refund or reserve. Subsequent real orders and explicit auto battle. '
                         'Every-round saved continuation compared exactly to an uninterrupted duplicate.',
                  derived_input=dict(source='late_full_roster', commands=[['build', 'archery'], ['build', 'mage_tower']],
                                     state=examples['late_all_buildings']['state']),
                  investment=investment_observation(examples['late_full_roster']['state'], budget=budget), runs=runs)
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == hashes[str(p.relative_to(ROOT))] for p in sources)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(report, indent=2, sort_keys=True) + '\n').encode()
    args.report.write_bytes(gzip.compress(encoded, mtime=0) if args.report.suffix == '.gz' else encoded)
    budget.checkpoint()


if __name__ == '__main__':
    main()
