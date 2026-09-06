#!/usr/bin/env python3
"""NON-PRODUCTION camp-service counterfactuals on retained public campaign states.

Only the proposed service edits a cloned, validated save payload. All purchases,
waiting, travel and subsequent combat use the actual game commands. These are
prototype outcomes; neither service is implemented in the shipped game.
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
from eador.model import RuleError, State
from tools.eador_campaign import CampaignMetrics, finish_battle


def prototype_service(state, kind):
    if state.status != 'playing' or state.battle or state.choice:
        raise RuleError('Use a camp service while playing between battles and choices.')
    if state.provinces[state.hero.pos].owner != 'player' or (state.encircled and state.hero.pos == (-2, 0)):
        raise RuleError('Use a supplied friendly camp.')
    if not state.actions_left:
        raise RuleError('The proposed service costs one campaign action.')
    building, price = ('mage_tower', 3) if kind == 'infusion' else ('temple', 4)
    if building not in state.buildings or state.crystals < price:
        raise RuleError('The proposed service needs its building and crystals.')
    before = state.to_json()
    payload = json.loads(before)
    hero = payload['hero']
    gains = {}
    if kind == 'infusion':
        gains['mana'] = min(8, hero['max_mana'] - hero['mana'])
        hero['mana'] += gains['mana']
    elif kind == 'treatment':
        units = [(0, hero), *((u['id'], u) for u in hero['army'])]
        budget = 24
        for uid, unit in sorted(units, key=lambda entry: (entry[1]['hp'] - entry[1]['max_hp'], entry[0])):
            gain = min(12, budget, unit['max_hp'] - unit['hp'])
            if gain:
                unit['hp'] += gain
                gains[str(uid)] = gain
                budget -= gain
    else:
        raise ValueError('Unknown prototype service')
    if not sum(gains.values()):
        raise RuleError('The proposed service would restore nothing.')
    payload['crystals'] -= price
    payload['actions_left'] -= 1
    result = State.from_json(json.dumps(payload))
    assert state.to_json() == before, 'Prototype mutated its input state'
    return result, dict(kind=kind, crystals=price, actions=1, gains=gains)


def snapshot(state):
    return dict(turn=state.turn, status=state.status, position=state.hero.pos,
                gold=state.gold, crystals=state.crystals, actions=state.actions_left,
                hero_hp=state.hero.hp, hero_max_hp=state.hero.max_hp,
                mana=state.hero.mana, max_mana=state.hero.max_mana,
                army=[dict(id=u.id, kind=u.kind, hp=u.hp, max_hp=u.max_hp) for u in state.hero.army],
                central_owner=state.provinces[(0, 0)].owner,
                capital_owner=state.provinces[(2, 0)].owner,
                rival_position=state.rival.pos, rival_target=state.rival.target,
                rival_intent=state.rival.intent, rival_countdown=state.rival.turns_until_action)


def exercise(payload, variant, *, pursuit=False):
    state = State.from_json(json.dumps(payload))
    before = snapshot(state)
    operations, service = [], None
    if variant.startswith('tower_'):
        state.build('mage_tower')
        operations.append(dict(command='build', target='mage_tower'))
    if 'infusion' in variant or 'treatment' in variant:
        kind = 'infusion' if 'infusion' in variant else 'treatment'
        state, service = prototype_service(state, kind)
        operations.append(dict(command='PROTOTYPE ' + kind, **service))
    after_preparation = snapshot(state)
    if 'rest_reserve' in variant:
        while state.hero.mana < state.hero.max_mana - 4:
            state.end_turn()
            operations.append(dict(command='end_turn'))
            assert not state.battle, 'Concrete rest example unexpectedly entered defense'
    elif 'rest_once' in variant or not state.actions_left:
        state.end_turn()
        operations.append(dict(command='end_turn'))
        assert not state.battle, 'Concrete rest example unexpectedly entered defense'
    before_battle = snapshot(state)
    target = state.rival.pos if pursuit else (2, 0)
    state.travel(target)
    operations.append(dict(command='travel', target=target, battle_kind=state.battle_kind))
    assert state.battle is not None
    battle_kind = state.battle_kind
    metrics = CampaignMetrics()
    finish_battle(state, metrics)
    operations.append(dict(command='explicit automatic battle and reward resolution'))
    after = snapshot(state)
    assert State.from_json(state.to_json()).to_json() == state.to_json()
    return dict(variant=variant, rules_id=state.rules_id, before=before,
                after_preparation=after_preparation, before_battle=before_battle,
                after=after, operations=operations, metrics=asdict(metrics),
                battle_kind=battle_kind, final_save_sha256=hashlib.sha256(state.to_json().encode()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--examples', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    examples = json.loads(args.examples.read_text())
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), Path(__file__), ROOT / 'tools/eador_campaign.py'])
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    runs = {}
    variants = {'pre_assault_mana': ('assault_now', 'rest_once', 'rest_reserve', 'infusion', 'treatment'),
                'pursuit_last_action': ('intercept_now', 'rest_once', 'tower_intercept',
                                        'tower_rest_once', 'tower_infusion', 'treatment')}
    for name, choices in variants.items():
        runs[name] = []
        for variant in choices:
            result = exercise(examples[name]['state'], variant, pursuit=name == 'pursuit_last_action')
            assert result == exercise(examples[name]['state'], variant, pursuit=name == 'pursuit_last_action')
            runs[name].append(result)
    # Confirm the quoted scarcity example through a public rejected purchase.
    full = State.from_json(json.dumps(examples['late_full_roster']['state']))
    before = full.to_json()
    try:
        full.recruit('pikeman')
    except RuleError as error:
        rejection = str(error)
    else:
        raise AssertionError('The retained full army unexpectedly accepted a recruit')
    assert full.to_json() == before
    report = dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, examples_file=args.examples.name,
                  examples_sha256=hashlib.sha256(args.examples.read_bytes()).hexdigest(),
                  policy='NON-PRODUCTION saved-payload services; one action; subsequent real commands and explicit auto combat. '
                         'Fixed local branches, not a tuned campaign policy or new service API.',
                  runs=runs, full_army_purchase_rejection=rejection,
                  source_files_changed=[str(p.relative_to(ROOT)) for p in sources
                                        if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))]])
    assert not report['source_files_changed']
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
