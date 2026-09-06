"""One paid linked campaign with a persistent army plan and exact saved continuations.

These are disclosed development policies, not an opponent, an optimal strategy,
or manual-play acceptance. Tactical rounds use the visible autoplay command.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from functools import partial
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.model import BUILDINGS, State, UNITS
from tools.audit_eador_economy import Trial
from tools.cpu_budget import CpuBudget


@dataclass(frozen=True)
class ArmyPlan:
    hero: str
    # Purchase priority is also the desired multiset. Repeated kinds are real slots.
    roster: tuple[str, ...]
    skills: tuple[str, ...]
    retinue: tuple[str, ...]
    equipment: tuple[str, ...]


PLANS = {
    'sustain': ArmyPlan('Commander',
        ('swordsman', 'healer', 'pikeman', 'swordsman', 'archer', 'militia'),
        ('quartermaster', 'tactician', 'quartermaster', 'quartermaster'),
        ('swordsman', 'healer'), ('moonstone', 'iron_crown', 'oak_standard')),
    'mobile': ArmyPlan('Scout',
        ('warden', 'ranger', 'ranger', 'archer', 'militia'),
        ('pathfinder', 'skirmisher', 'pathfinder', 'skirmisher'),
        ('warden', 'ranger'), ('iron_crown', 'moonstone', 'wayfarer_boots')),
    'control': ArmyPlan('Wizard',
        ('sapper', 'healer', 'adept', 'skyrider', 'militia'),
        ('channeling', 'restoration', 'channeling', 'channeling'),
        ('skyrider', 'adept'), ('ember_lens', 'moonstone', 'oak_standard')),
}


class SavedCommands:
    """Record ordinary commands; the following command runs on their saved result."""

    def __init__(self, state, budget):
        self.state, self.budget, self.commands = state, budget, []

    def __getattr__(self, name):
        if name in ('build', 'recruit', 'replace_troop', 'travel', 'explore', 'end_turn',
                    'choose', 'equip', 'resolve_battle', 'retreat', 'advance', 'recover'):
            return partial(self.order, name)
        return getattr(self.state, name)

    def order(self, command, *args, **kwargs):
        self.budget.checkpoint()
        before = self.state.to_json()
        gold, crystals = self.gold, self.crystals
        target = self.state.battle if command.startswith('battle.') else self.state
        result = getattr(target, command.removeprefix('battle.'))(*args, **kwargs)
        after = self.state.to_json()
        restored = State.from_json(after)
        assert restored.to_json() == after, f'{command} did not save exactly'
        self.commands.append(dict(command=command, args=args, kwargs=kwargs,
                                  gold_spent=gold - self.gold, crystals_spent=crystals - self.crystals,
                                  before=before, after=after))
        self.state = restored
        return result


class ArmyTrial(Trial):
    """Reuse the finite rival-aware itinerary; own only purchases and battle decisions."""

    def __init__(self, state, plan, *, route, budget):
        super().__init__(state.seed, state.hero.hero_class, state.theme, plan,
                         state=state, route=route, budget=budget)
        self.spec = PLANS[plan]
        self.battles = []

    def equipment(self):
        state = self.state
        owned = [relic for relic in self.spec.equipment if relic in state.inventory]
        chosen = owned[0] if owned else next(iter(state.inventory), None)
        if state.hero.relic != chosen:
            state.equip(chosen)

    def invest(self):
        state = self.state
        if state.status != 'playing' or state.provinces[state.hero.pos].owner != 'player':
            return
        if 'merchant_seal' in state.inventory and state.hero.relic != 'merchant_seal':
            state.equip('merchant_seal')
        desired, prefix = Counter(self.spec.roster), Counter()
        for kind in self.spec.roster:
            prefix[kind] += 1
            if Counter(t.kind for t in state.hero.army)[kind] >= prefix[kind]:
                continue
            building = UNITS[kind].building
            if building and building not in state.buildings:
                spec = BUILDINGS[building]
                if state.gold < spec.cost or state.crystals < spec.crystals:
                    break
                self.buy('build', building)
            if state.gold < state.recruit_cost(kind) or state.crystals < state.recruit_crystal_cost(kind):
                break
            if len(state.hero.army) < state.hero.max_army:
                self.buy('recruit', kind)
                continue
            counts = Counter(t.kind for t in state.hero.army)
            surplus = [troop for troop in state.hero.army if counts[troop.kind] > desired[troop.kind]]
            assert surplus, 'A full incomplete roster has no replaceable surplus'
            outgoing = min(surplus, key=lambda t: (t.level, t.xp, t.hp, t.id))
            quote = state.replacement_preview(outgoing.id, kind)
            if quote.blocked_reason:
                break
            state.replace_troop(outgoing.id, kind)
            self.metrics.recruitment_gold += quote.gold
            self.bought['replace.' + kind] += 1
            self.investments.append((state.turn, 'replace_troop', kind, quote.gold, quote.crystals))
        self.equipment()

    def battle(self):
        state = self.state
        before = state.to_json()
        initial = state.battle
        hp = {u.id: u.hp for u in initial.units if u.team == 'player'}
        mana, gold = initial.mana, state.gold
        roster = [asdict(troop) for troop in state.hero.army]
        for _ in range(80):
            if state.battle.outcome:
                break
            state.order('battle.auto_turn')
        battle = state.battle
        assert battle.outcome is not None, 'Tactical autoplay exceeded its 80-round bound'
        self.metrics.battles += 1
        self.metrics.lost_troops += sum(u.id != 0 and u.hp == 0 for u in battle.units if u.team == 'player')
        self.metrics.battle_hp_attrition += sum(max(0, value - battle.unit(uid).hp) for uid, value in hp.items())
        self.metrics.mana_spent += mana - battle.mana
        self.metrics.defeats += battle.outcome == 'enemy'
        self.battles.append(dict(encounter=state.battle_encounter, kind=state.battle_kind,
                                 turn=state.turn, roster=roster, before=before,
                                 resolved=state.to_json(), outcome=battle.outcome,
                                 reason=battle.outcome_reason, rounds=battle.round,
                                 commands='Explicit tactical autoplay; no manual orders.'))
        state.resolve_battle()
        self.retreat_gold += max(0, gold - state.gold)
        while state.choice:
            if state.choice.kind == 'skill':
                skill = self.spec.skills[sum(state.hero.skill_ranks.values())]
                assert skill in {option.id for option in state.choice.options}
                state.choose(skill)
            else:
                # Keep a newly discovered relic; distill duplicates into actual crystals.
                state.choose(state.choice.options[0].id)
        self.equipment()


def retinue(state, plan):
    """Choose role-preserving veterans, then return their IDs in UI roster order."""
    selected = []
    for kind in PLANS[plan].retinue:
        candidates = [troop for troop in state.hero.army if troop.kind == kind and troop.id not in selected]
        if candidates:
            selected.append(max(candidates, key=lambda t: (t.level, t.xp, t.hp, t.id)).id)
    for troop in sorted(state.hero.army, key=lambda t: (t.level, t.xp, t.hp, t.id), reverse=True):
        if len(selected) == 2:
            break
        if troop.id not in selected:
            selected.append(troop.id)
    preferred = ('merchant_seal', *PLANS[plan].equipment)
    relics = list(dict.fromkeys(relic for relic in (*preferred, *state.inventory) if relic in state.inventory))[:2]
    return dict(troop_ids=tuple(t.id for t in state.hero.army if t.id in selected),
                relic_ids=tuple(relic for relic in state.inventory if relic in relics))


def journey(plan='sustain', *, seed=7, difficulty='standard', middle='foundries',
            finale='throne', cpu_percent=25):
    """Run one paid three-shard attempt, using the one recovery if a capital actually falls."""
    budget = CpuBudget(cpu_percent)
    spec = PLANS[plan]
    state = SavedCommands(State.new_campaign(seed, spec.hero, difficulty=difficulty), budget)
    initial, stages = state.to_json(), []
    for destination in (middle, finale, None):
        while True:
            contract = state.campaign.contract
            if contract == 'foundries':
                route = ((-2, 0), (-1, 0), (0, -1), (0, 1), (1, 0), (2, 0))
            elif contract == 'rootward':
                watch = next(p.pos for p in state.provinces.values() if p.site_kind == 'border_watch')
                route = ((-2, 0), (-1, 0), (0, 0), watch, (1, 0), (2, 0))
            else:
                route = tuple(state.grid.path(state.hero.pos, (2, 0)))
            trial = ArmyTrial(state, plan, route=route, budget=budget)
            summary = trial.run()
            stages.append(dict(stage=state.campaign.stage, contract=contract,
                               attempt=2 if state.campaign.recovery_used else 1,
                               summary=summary, battles=trial.battles, state=state.to_json()))
            if state.campaign.phase != 'recovery':
                break
            state.recover(**retinue(state, plan))
        if state.status != 'victory' or destination is None:
            break
        state.advance(destination, **retinue(state, plan))
    return dict(plan=plan, specification=asdict(spec), seed=seed, difficulty=difficulty,
                cpu_percent=cpu_percent, middle=middle, finale=finale,
                policy='Paid persistent roster; exact save continuation after every command; tactical autoplay.',
                initial_state=initial, stages=stages, commands=state.commands,
                final_state=state.to_json(), phase=state.campaign.phase,
                status=state.status, recovery_used=state.campaign.recovery_used)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', choices=PLANS, default='sustain')
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--difficulty', choices=('accessible', 'standard', 'challenge'), default='standard')
    parser.add_argument('--middle', choices=('foundries', 'rootward'), default='foundries')
    parser.add_argument('--finale', choices=('throne', 'gate'), default='throne')
    parser.add_argument('--cpu-percent', type=float, default=25)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    paths = [*ROOT.glob('eador/**/*.py'), ROOT / 'tools/audit_eador_army_plans.py',
             ROOT / 'tools/audit_eador_economy.py', ROOT / 'tools/cpu_budget.py']
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    report = journey(args.plan, seed=args.seed, difficulty=args.difficulty, middle=args.middle,
                     finale=args.finale, cpu_percent=args.cpu_percent)
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == value for path, value in hashes.items())
    report.update(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, source_unchanged=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(args.output, 'wt') as stream:
        json.dump(report, stream, indent=2)
    print(f"{args.plan}: {report['phase']}, {len(report['stages'])} shard attempts, "
          f"{len(report['commands'])} exact saved commands; {args.output}", flush=True)


if __name__ == '__main__':
    main()
