#!/usr/bin/env python3
"""NON-PRODUCTION: buy existing control roles at an earned early budget window.

Every purchase, retirement, turn and tactic is a shipped public command. No rules,
resources, battle geometry or army data are replaced. The input is the retained
turn-six Standard Frontier decision from the resource-attribution audit.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eador.model import BUILDINGS, RuleError, State, UNITS

ROLES = ((4, 'sapper'), (5, 'adept'), (6, 'skyrider'))


def input_state():
    path = ROOT / 'docs/evidence/resource-breakpoints.rows.json.gz'
    rows = json.loads(gzip.decompress(path.read_bytes()))
    row = next(r for r in rows if r['case'] == [0, 'Commander', 'frontier', 'economy', 'standard', 'direct'])
    state = State.from_json(json.dumps(row['endpoints']['lasting_breakpoint']['state']))
    assert (state.turn, state.gold, state.crystals, state.actions_left, state.hero.pos) == (6, 144, 21, 1, (1, 0))
    return state, path


def snapshot(state):
    return dict(turn=state.turn, gold=state.gold, crystals=state.crystals, actions=state.actions_left,
                hero_hp=state.hero.hp, hero_max_hp=state.hero.max_hp, mana=state.hero.mana,
                max_mana=state.hero.max_mana, army=[asdict(t) for t in state.hero.army],
                rival=asdict(state.rival), income=state.income, upkeep=state.upkeep,
                shortfall=state.upkeep_shortfall, owned=sorted(p.pos for p in state.provinces.values() if p.owner == 'player'))


class Orders:
    def __init__(self, state):
        self.state = state
        self.events, self.retired, self.fights = [], [], []
        self.gold_spent = self.crystals_spent = self.replacement_actions = 0

    def do(self, command, *args, **kwargs):
        before = self.state.to_json()
        gold, crystals = self.state.gold, self.state.crystals
        quote = (self.state.replacement_preview(*args) if command == 'replace_troop' else None)
        try:
            getattr(self.state, command)(*args, **kwargs)
        except RuleError as error:
            assert self.state.to_json() == before
            self.events.append(dict(command=command, args=args, rejected=str(error)))
            return False
        if command in ('build', 'replace_troop', 'recruit', 'infuse'):
            self.gold_spent += gold - self.state.gold
            self.crystals_spent += crystals - self.state.crystals
        if quote:
            self.retired.append(asdict(quote))
            self.replacement_actions += quote.actions
        self.events.append(dict(command=command, args=args, after=snapshot(self.state)))
        encoded = self.state.to_json()
        self.state = State.from_json(encoded)
        assert self.state.to_json() == encoded
        return True

    def rest(self):
        assert self.do('end_turn')
        assert self.state.status == 'playing' and self.state.battle is None, 'Preparation encountered an actual interruption'

    def tower(self):
        assert self.do('build', 'mage_tower')

    def replace(self, uid, kind):
        assert self.do('replace_troop', uid, kind)


def prepare(plan):
    state, _ = input_state()
    play = Orders(state)
    single_role = plan.removesuffix('_militia')
    if plan.startswith('tower') or single_role == 'adept':
        play.tower()
    if plan.endswith('rest1'):
        play.rest()
    elif plan.endswith('rest3'):
        for _ in range(3):
            play.rest()
    if single_role in ('sapper', 'adept', 'skyrider'):
        play.replace(1 if plan.endswith('_militia') else next(uid for uid, kind in ROLES if kind == single_role), single_role)
        play.rest()
    elif plan in ('full_staged', 'full_staged_tanks'):
        roles = ROLES if plan == 'full_staged' else ((1, 'sapper'), (3, 'adept'), (6, 'skyrider'))
        for uid, kind in roles:
            for _ in range(12):
                building = UNITS[kind].building
                if building not in play.state.buildings:
                    spec = BUILDINGS[building]
                    if play.state.gold >= spec.cost and play.state.crystals >= spec.crystals:
                        assert play.do('build', building)
                if play.do('replace_troop', uid, kind):
                    break
                play.rest()
            else:
                raise AssertionError('The staged conversion was not affordable in the bounded window')
    elif plan == 'full_fund_first':
        while play.state.gold < 223:
            play.rest()
        play.tower()
        for uid, kind in ROLES:
            if not play.state.actions_left:
                play.rest()
            play.replace(uid, kind)
    return play


def hero_heal_first(battle):
    """Disclosed manual hero orders, then ordinary automatic troop orders.

    Preserve mana for useful healing; otherwise attack in melee or approach the
    nearest foe using reachable cover. This is a small tactical control, not an
    optimal solver or a mutation of the available spell set.
    """
    hero = battle.unit(0)
    commands = []
    if not hero.alive or hero.acted or battle.outcome:
        return commands
    def do(command, *args):
        getattr(battle, command)(*args)
        commands.append((command, args))
    injured = [u for u in battle.spell_targets('heal') if battle.spell_preview('heal', u.id) >= 8]
    if injured:
        target = min(injured, key=lambda u: (u.hp / u.max_hp, u.id))
        do('cast', 'heal', target.id)
        return commands
    targets = battle.targets(0)
    if not targets:
        enemies = [u for u in battle.units if u.team == 'enemy' and u.alive]
        def score(pos):
            distance = min(battle.grid.distance(pos, u.pos) for u in enemies)
            return (distance > 1, max(0, distance - 1), battle.terrain[pos] not in ('forest', 'hills'), pos)
        destination = min(battle.reachable(0) | {hero.pos}, key=score)
        if destination != hero.pos:
            do('move', 0, destination)
        targets = battle.targets(0)
    if targets:
        do('attack', 0, min(targets, key=lambda u: (u.hp, u.id)).id)
    else:
        do('guard', 0)
    return commands


def fight(play, tactics):
    state = play.state
    initial = state.to_json()
    kind = state.battle_kind
    orders = []
    for _ in range(80):
        if state.battle.outcome:
            break
        before = state.to_json()
        if tactics == 'heal_first':
            commands = hero_heal_first(state.battle)
        else:
            commands = []
        if not state.battle.outcome:
            state.battle.auto_turn()
            commands.append(('auto_turn', ()))
        clone = State.from_json(before)
        for command, args in commands:
            getattr(clone.battle, command)(*args)
        assert clone.to_json() == state.to_json(), 'Saved public tactical orders continued differently'
        orders.extend(commands)
        state = State.from_json(state.to_json())
    battle = state.battle
    assert battle.outcome
    tactical_result = battle.to_dict()
    state.resolve_battle()
    while state.choice:
        state.choose(state.choice.options[0].id)
    play.state = State.from_json(state.to_json())
    play.fights.append(dict(kind=kind, initial=json.loads(initial), orders=orders,
                            result=tactical_result, after=snapshot(play.state)))
    return battle.outcome


def run(plan, tactics='auto', *, wait_after_intercept=False):
    play = prepare(plan)
    ready = snapshot(play.state)
    for _ in range(4):
        if play.state.status != 'playing':
            break
        if not play.state.actions_left:
            play.rest()
        assert play.do('travel', (2, 0))
        if play.state.battle:
            kind = play.state.battle_kind
            if fight(play, tactics) == 'enemy':
                break
            if kind == 'intercept' and wait_after_intercept:
                play.rest()
    ending = play.state.to_json()
    safety = []
    if play.state.status == 'playing':
        # An explicit no-purchase continuation, not a guarantee of future safety.
        for _ in range(3):
            assert play.do('end_turn')
            safety.append(snapshot(play.state))
            if play.state.battle or play.state.status != 'playing':
                break
    lost = [u['id'] for f in play.fights for u in f['result']['units'] if u['team'] == 'player' and u['id'] != 0 and u['hp'] == 0]
    return dict(plan=plan, tactics=tactics, wait_after_intercept=wait_after_intercept,
                ready=ready, gold_spent=play.gold_spent, crystals_spent=play.crystals_spent,
                replacement_actions=play.replacement_actions, retired=play.retired,
                events=play.events, fights=play.fights, ending=json.loads(ending),
                combat_deaths=lost, later_no_purchase_turns=safety,
                result='victory' if json.loads(ending)['status'] == 'victory' else 'failed_assault')


def paid_retry(payload):
    """One bounded conventional recovery from the staged conversion's real loss.

    Buy affordable Swordsmen, rest to the existing six-HP/four-mana reserve, and
    retry the adjacent capital. No site rewards, injected funds or free troops.
    """
    play = Orders(State.from_json(json.dumps(payload)))
    start = play.state.turn
    for _ in range(32):
        state = play.state
        if state.status != 'playing' or state.turn > start + 12:
            break
        while len(play.state.hero.army) < play.state.hero.max_army and play.state.gold >= play.state.recruit_cost('swordsman'):
            assert play.do('recruit', 'swordsman')
        state = play.state
        missing = max([state.hero.max_hp - state.hero.hp] + [t.max_hp - t.hp for t in state.hero.army])
        if state.actions_left and missing <= 6 and state.hero.mana >= state.hero.max_mana - 4:
            assert play.do('travel', (2, 0))
            if play.state.battle and fight(play, 'auto') == 'enemy':
                break
        if play.state.status == 'playing':
            assert play.do('end_turn')
            if play.state.battle and fight(play, 'auto') == 'enemy':
                break
    return dict(additional_gold_spent=play.gold_spent, additional_crystals_spent=play.crystals_spent,
                events=play.events, fights=play.fights, final=json.loads(play.state.to_json()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT / 'docs/evidence/early-conversion-prototype.json.gz')
    args = parser.parse_args()
    state, input_path = input_state()
    sources = [*sorted((ROOT / 'eador').glob('*.py')), Path(__file__).resolve()]
    fingerprints = lambda: {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    before = fingerprints()
    cases = [(plan, 'auto', False) for plan in ('keep_now', 'keep_rest1', 'tower_now', 'tower_rest1',
             'sapper', 'adept', 'skyrider', 'full_staged', 'keep_rest3', 'tower_rest3', 'full_fund_first')]
    cases.append(('tower_rest3', 'auto', True))
    # Do not make conversion look weak only by throwing away every Swordsman.
    cases += [(plan, 'auto', False) for plan in ('sapper_militia', 'adept_militia', 'skyrider_militia', 'full_staged_tanks')]
    cases += [(plan, 'heal_first', False) for plan in ('keep_rest1', 'adept', 'full_staged', 'tower_rest3')]
    rows = []
    for plan, tactics, delayed in cases:
        row = run(plan, tactics, wait_after_intercept=delayed)
        assert row == run(plan, tactics, wait_after_intercept=delayed)
        rows.append(row)
        print(plan, tactics, delayed, 'ready', row['ready']['turn'], 'result', row['result'],
              row['ending']['turn'], 'deaths', len(row['combat_deaths']), flush=True)
    staged = next(row for row in rows if row['plan'] == 'full_staged' and row['tactics'] == 'auto')
    retry = paid_retry(staged['ending'])
    assert retry == paid_retry(staged['ending'])
    print('staged paid retry', retry['final']['status'], retry['final']['turn'], retry['additional_gold_spent'])
    assert before == fingerprints()
    report = dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=before, source_files_changed_during_run=[],
                  input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(), input=json.loads(state.to_json()),
                  scope='No production rules changed. All ordinary commands from an actual paid turn-six save. '
                        'Same capital objective and initial finite rival. Waiting changes rival and the seeded '
                        'battlefield; retained-party same-clock controls are explicit. Auto outcomes are not '
                        'proof of manual optimality. Every branch repeats and every tactical phase replays '
                        'from its actual saved start. Failed assault is not a lost campaign.', runs=rows,
                  staged_paid_retry=retry)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes(gzip.compress(json.dumps(report, separators=(',', ':')).encode(), mtime=0))
    print(args.report)


if __name__ == '__main__':
    main()
