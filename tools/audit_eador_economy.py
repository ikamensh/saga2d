"""Compare three explicit v9 development plans through unmodified public shard commands."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eador.model import BUILDINGS, HERO_CLASSES, State
from eador.worldgen import THEMES
from tools.eador_campaign import CampaignMetrics, finish_battle

PLANS = {
    'economy': (('build', 'market'), ('build', 'barracks'), ('recruit', 'swordsman'), ('build', 'temple')),
    'sustain': (('build', 'temple'), ('recruit', 'healer'), ('build', 'barracks'), ('recruit', 'swordsman')),
    'spells': (('build', 'mage_tower'), ('build', 'barracks'), ('recruit', 'swordsman'), ('build', 'temple')),
}


class Trial:
    """A measured player policy; every mutation calls the shipped State/Battle interface."""
    def __init__(self, seed, hero_class, theme, plan, *, state=None, route=None):
        self.state = State.new(seed, hero_class, theme=theme) if state is None else state
        self.route = route
        self.seed, self.hero_class, self.theme, self.plan = seed, hero_class, theme, plan
        self.metrics = CampaignMetrics()
        self.plan_step = 0
        self.stop_reason = None
        self.bought = Counter()
        self.investments = []
        self.building_crystals = self.upkeep_gold = self.retreat_gold = self.deserters = 0

    def buy(self, action, kind):
        state = self.state
        gold, crystals = state.gold, state.crystals
        getattr(state, action)(kind)
        self.bought[action + '.' + kind] += 1
        self.investments.append((state.turn, action, kind, gold - state.gold, crystals - state.crystals))
        if action == 'build':
            self.metrics.building_gold += gold - state.gold
            self.building_crystals += crystals - state.crystals
        else:
            self.metrics.recruitment_gold += gold - state.gold

    def invest(self):
        state = self.state
        if state.status != 'playing':
            return
        # Each plan commits to its disclosed order instead of changing after a bad seed.
        while self.plan_step < len(PLANS[self.plan]):
            action, kind = PLANS[self.plan][self.plan_step]
            if action == 'build':
                spec = BUILDINGS[kind]
                affordable = state.gold >= spec.cost and state.crystals >= spec.crystals
            else:
                if len(state.hero.army) == state.hero.max_army:
                    self.plan_step += 1
                    continue
                affordable = state.gold >= state.recruit_cost(kind)
            if not affordable:
                return
            self.buy(action, kind)
            self.plan_step += 1
        relic = state.hero.relic
        if 'merchant_seal' in state.inventory:
            state.equip('merchant_seal')
        while len(state.hero.army) < state.hero.max_army:
            kind = 'healer' if self.plan == 'sustain' and not any(t.kind == 'healer' for t in state.hero.army) else 'swordsman'
            if state.gold < state.recruit_cost(kind):
                break
            self.buy('recruit', kind)
        state.equip(relic)

    def battle(self):
        before = self.state.gold
        finish_battle(self.state, self.metrics)
        self.retreat_gold += max(0, before - self.state.gold)

    def rest(self, defend=True):
        state = self.state
        if defend:
            self.intercept()
        if state.status != 'playing' or state.turn >= 60 or self.stop_reason:
            return
        before = {t.id: t.hp for t in state.hero.army}
        hero_hp, mana = state.hero.hp, state.hero.mana
        state.end_turn()
        self.metrics.end_turns += 1
        # End-turn desertion precedes payment; the strategic rival does not kill
        # player troops before the resulting tactical battle is resolved below.
        self.deserters += len(before) - len(state.hero.army)
        self.upkeep_gold += state.upkeep
        self.metrics.hp_recovered += max(0, state.hero.hp - hero_hp) + sum(max(0, t.hp - before[t.id]) for t in state.hero.army)
        self.metrics.mana_recovered += state.hero.mana - mana
        if state.battle:
            self.battle()

    def intercept(self):
        state = self.state
        if state.rival.army and state.grid.distance(state.rival.pos, (-2, 0)) <= 2:
            self.march(state.rival.pos)

    def ready_for_final(self):
        state = self.state
        missing = max([state.hero.max_hp - state.hero.hp] + [t.max_hp - t.hp for t in state.hero.army])
        return missing <= 6 and state.hero.mana >= state.hero.max_mana - 4 and state.actions_left > 0

    def march(self, destination):
        state = self.state
        for _ in range(24):
            if state.hero.pos == destination or state.status != 'playing' or state.turn >= 60 or self.stop_reason:
                return
            if not state.actions_left:
                self.rest(defend=False)
            if state.status != 'playing' or state.turn >= 60 or self.stop_reason:
                return
            state.travel(state.grid.path(state.hero.pos, destination)[1])
            if state.battle:
                self.battle()
        if state.hero.pos != destination and state.status == 'playing' and state.turn < 60:
            self.stop_reason = 'route_bound'

    def run(self):
        state = self.state
        self.invest()
        itinerary = (self.route or state.grid.path(state.hero.pos, (2, 0)))[:-1]
        for province in itinerary:
            if state.status != 'playing' or state.turn >= 60 or self.stop_reason:
                break
            if province != state.hero.pos:
                self.march(province)
                self.rest()
                self.invest()
            self.march(province)
            if state.status != 'playing' or state.turn >= 60 or self.stop_reason:
                break
            if not state.provinces[province].explored:
                if not state.actions_left:
                    self.rest()
                    self.march(province)
                if state.status != 'playing' or state.turn >= 60 or self.stop_reason:
                    break
                state.explore()
                self.battle()
            self.rest()
            self.invest()
        for _ in range(40):
            if state.status != 'playing' or state.turn >= 60 or self.stop_reason:
                break
            self.invest()
            if not self.ready_for_final():
                self.metrics.recovery_turns += 1
                self.rest()
                continue
            state.travel(state.grid.path(state.hero.pos, (2, 0))[1])
            if state.battle:
                self.battle()
            if state.status == 'playing':
                self.rest()
        assert State.from_json(state.to_json()).to_json() == state.to_json()
        assert self.deserters >= 0
        return dict(seed=self.seed, hero=self.hero_class, theme=self.theme, plan=self.plan,
                    status=state.status, stop_reason=state.status if state.status != 'playing' else self.stop_reason or 'policy_bound',
                    turns=state.turn, metrics=asdict(self.metrics),
                    building_crystals=self.building_crystals, upkeep_gold=self.upkeep_gold,
                    retreat_gold=self.retreat_gold, deserters=self.deserters,
                    gold_left=state.gold, crystals_left=state.crystals,
                    purchases=dict(self.bought), investments=self.investments,
                    hero_rank=state.hero.level, skills=state.hero.skill_ranks,
                    roster=[(t.kind, t.level, t.hp) for t in state.hero.army],
                    final_save_sha256=hashlib.sha256(state.to_json().encode()).hexdigest())


def aggregate(runs):
    groups = defaultdict(list)
    for row in runs:
        for group in (row['plan'], row['plan'] + '/' + row['hero'], row['plan'] + '/' + row['theme']):
            groups[group].append(row)
    summary = {}
    for group, rows in groups.items():
        winners = [r for r in rows if r['status'] == 'victory']
        summary[group] = dict(runs=len(rows), outcomes=dict(Counter(r['status'] for r in rows)),
                             mean_turns=round(statistics.mean(r['turns'] for r in rows), 3),
                             mean_winning_turns=round(statistics.mean(r['turns'] for r in winners), 3) if winners else None,
                             mean_casualties=round(statistics.mean(r['metrics']['lost_troops'] for r in rows), 3),
                             mean_mana_spent=round(statistics.mean(r['metrics']['mana_spent'] for r in rows), 3),
                             mean_recruitment_gold=round(statistics.mean(r['metrics']['recruitment_gold'] for r in rows), 3),
                             mean_building_gold=round(statistics.mean(r['metrics']['building_gold'] for r in rows), 3),
                             mean_building_crystals=round(statistics.mean(r['building_crystals'] for r in rows), 3),
                             mean_upkeep=round(statistics.mean(r['upkeep_gold'] for r in rows), 3),
                             mean_gold_left=round(statistics.mean(r['gold_left'] for r in rows), 3),
                             mean_crystals_left=round(statistics.mean(r['crystals_left'] for r in rows), 3))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=100)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error('--seeds must be positive')
    sources = [*sorted((ROOT / 'eador').glob('*.py')), Path(__file__), ROOT / 'tools/eador_campaign.py']
    fingerprints = lambda: {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    before = fingerprints()
    runs = []
    started = time.monotonic()
    for seed in range(args.seeds):
        if seed % 10 == 0:
            print(f'Economy seed {seed}/{args.seeds}', flush=True)
        for theme in THEMES:
            for hero in HERO_CLASSES:
                for plan in PLANS:
                    row = Trial(seed, hero, theme, plan).run()
                    if seed == 0:
                        assert Trial(seed, hero, theme, plan).run() == row, 'repeated public policy differed'
                    runs.append(row)
    after = fingerprints()
    assert before == after, 'source changed during measurement'
    report = dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=before, elapsed_seconds=round(time.monotonic() - started, 2),
                  policy='Matched direct site itinerary; explicit auto tactics; first reward choices; ordered investment plans then refill Swordsmen. '
                         'Sustain retains one paid Acolyte; all use recovered Merchant Seal discounts and restore combat relic. '
                         'Rest when needed; intercept a visible expedition near home. No rule or route tuning by seed. 60-turn/40-assault-step bound.',
                  seeds=args.seeds, campaigns=len(runs), summary=aggregate(runs), runs=runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # One complete trial per line keeps a large audit inspectable without a huge
    # pretty-printed tree. Metadata and grouped comparisons remain indented.
    header = json.dumps({k: v for k, v in report.items() if k != 'runs'}, indent=2)
    args.output.write_text(header[:-2] + ',\n  "runs": [\n' + ',\n'.join('    ' + json.dumps(r) for r in runs) + '\n  ]\n}\n')
    print(json.dumps({key: value for key, value in report['summary'].items() if '/' not in key}, indent=2))
    print(f'{len(runs)} trials retained in {args.output}; {report["elapsed_seconds"]}s', flush=True)


if __name__ == '__main__':
    main()
