#!/usr/bin/env python3
"""Measure the explicit seed-seven extraction plans; not an optimal-play benchmark."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.model import HERO_CLASSES, RuleError, State
from tools.eador_extraction_campaign import prepare_adventure, prepared_crossing, crossing_route, cache_route


class PaidState:
    """Measure actual purchases through the same public preparation commands."""
    def __init__(self, state):
        self.state = state
        self.building_gold = self.recruitment_gold = 0

    def __getattr__(self, name):
        return getattr(self.state, name)

    def build(self, name):
        before = self.gold
        self.state.build(name)
        self.building_gold += before - self.gold

    def recruit(self, name):
        before = self.gold
        self.state.recruit(name)
        self.recruitment_gold += before - self.gold


def measure(prepared, approach, route, name):
    state = State.from_json(prepared.to_json())
    before = {'campaign_turn': state.turn, 'gold': state.gold, 'hero_class': state.hero.hero_class,
              'building_gold': prepared.building_gold, 'recruitment_gold': prepared.recruitment_gold,
              'army': [troop.kind for troop in state.hero.army], 'hero_skills': dict(state.hero.skill_ranks)}
    play = route(state, approach)
    state, battle = play.state, play.battle
    assert battle.outcome_reason == 'escape'
    assert all(unit.alive for unit in battle.units if unit.team == 'player')
    assert any(unit.alive for unit in battle.units if unit.team == 'enemy')
    assert State.from_json(state.to_json()).to_json() == state.to_json()
    reward = state.battle_adventure
    result = {'plan': name, 'approach': approach, **before, 'rounds': battle.round,
              'entry_gold': before['gold'] - state.gold, 'reward_gold': reward.gold,
              'reward_crystals': reward.crystals, 'mana_spent': state.hero.mana - battle.mana,
              'remaining_hp_deficit': sum(u.max_hp - u.hp for u in battle.units if u.team == 'player'),
              'enemies_surviving': sum(u.alive for u in battle.units if u.team == 'enemy'),
              'order_count': len(play.orders), 'orders': play.orders}
    gold, crystals = state.gold, state.crystals
    state.resolve_battle()
    assert state.gold == gold + reward.gold and state.crystals == crystals + reward.crystals
    while state.choice:
        state.choose(state.choice.options[0].id)
    saved = state.to_json()
    try:
        state.explore()
    except RuleError:
        pass
    else:
        raise AssertionError('Completed extraction rewarded twice')
    assert saved == state.to_json()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'),
                      ROOT / 'tools/eador_campaign.py', ROOT / 'tools/eador_roles_campaign.py',
                      ROOT / 'tools/eador_extraction_campaign.py', Path(__file__).resolve()])
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines()
    started = time.perf_counter()
    rows = []
    paired = prepared_crossing(PaidState(State.new(7)))
    for approach in ('direct', 'guided'):
        rows.append(measure(paired, approach, crossing_route, 'same seven-body Crossing army'))
    for hero in HERO_CLASSES:
        for approach, support in (('direct', 'ranger'), ('guided', 'healer')):
            state = prepare_adventure(hero, 'frontier', support=support, state=PaidState(State.new(7, hero)))
            rows.append(measure(state, approach, crossing_route, 'six-body Crossing route'))
        prepared = prepare_adventure(hero, 'elderwild', state=PaidState(State.new(7, hero, theme='elderwild')))
        for approach in ('light', 'full'):
            rows.append(measure(prepared, approach, cache_route, 'same six-body Cache army'))
    changed = [str(p.relative_to(ROOT)) for p in sources if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))]]
    assert not changed
    report = {'revision': revision, 'dirty_at_start': dirty,
              'source_sha256': hashes, 'source_files_changed': changed, 'seed': 7,
              'python': platform.python_version(), 'platform': platform.platform(),
              'elapsed_seconds': time.perf_counter() - started, 'completed_manual_escapes': len(rows), 'journeys': rows}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(f'Passed {len(rows)} paid manual escapes; source unchanged. Report: {args.report}')


if __name__ == '__main__':
    main()
