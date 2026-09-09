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
from tools.eador_sources import source_name
from eador.model import BUILDINGS, RuleError, State, UNITS
from saga2d.testing.cpu_budget import CpuBudget

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
    def __init__(self, state, *, budget=None):
        self.state = state
        self.budget = budget
        self.events, self.retired, self.fights = [], [], []
        self.gold_spent = self.crystals_spent = self.replacement_actions = 0

    def do(self, command, *args, **kwargs):
        if self.budget:
            self.budget.checkpoint()
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


def prepare(plan, *, budget=None):
    state, _ = input_state()
    play = Orders(state, budget=budget)
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
        if play.budget:
            play.budget.checkpoint()
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


def run(plan, tactics='auto', *, wait_after_intercept=False, budget=None):
    play = prepare(plan, budget=budget)
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


def paid_retry(payload, *, budget=None):
    """One bounded conventional recovery from the staged conversion's real loss.

    Buy affordable Swordsmen, rest to the existing six-HP/four-mana reserve, and
    retry the adjacent capital. No site rewards, injected funds or free troops.
    """
    play = Orders(State.from_json(json.dumps(payload)), budget=budget)
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



class EarnedWindow:
    """Observe an unchanged paid policy, retaining the first useful turn-five/seven camp."""
    def __init__(self, state):
        self.state, self.saved = state, None

    def __getattr__(self, name):
        from tools.audit_eador_resource_breakpoints import COMMANDS
        target = getattr(self.state, name)
        if name not in COMMANDS:
            return target
        def observed(*args, **kwargs):
            result = target(*args, **kwargs)
            state = self.state
            if (self.saved is None and 5 <= state.turn <= 7 and state.status == 'playing'
                    and not state.battle and not state.choice and state.actions_left
                    and state.provinces[state.hero.pos].owner == 'player'
                    and len(state.hero.army) == state.hero.max_army
                    and state.gold >= state.recruit_cost('sapper')
                    and state.crystals >= state.recruit_crystal_cost('sapper')):
                self.saved = state.to_json()
            return result
        return observed


class InvestmentOrders(Orders):
    """Existing public replay/quote recorder, with real defense during funding waits."""
    def rest(self, *, defend=True):
        # Match the established policy's defense responsibility, but recheck the
        # actual expedition position instead of marching to a stale destination.
        if defend:
            for _ in range(24):
                state = self.state
                if (state.status != 'playing' or not state.rival.army
                        or state.grid.distance(state.rival.pos, (-2, 0)) > 2):
                    break
                if not state.actions_left:
                    self.rest(defend=False)
                    continue
                assert self.do('travel', state.grid.path(state.hero.pos, state.rival.pos)[1])
                if self.state.battle and fight(self, 'auto') == 'enemy':
                    break
            else:
                raise AssertionError('Public live-position interception exceeded its bound')
        if self.state.status == 'playing':
            assert self.do('end_turn')
            if self.state.battle:
                fight(self, 'auto')

    def march(self, destination):
        for _ in range(24):
            state = self.state
            if state.status != 'playing' or state.hero.pos == destination:
                return
            if not state.actions_left:
                self.rest(defend=False)
                continue
            assert self.do('travel', state.grid.path(state.hero.pos, destination)[1])
            if self.state.battle and fight(self, 'auto') == 'enemy':
                return
        raise AssertionError('Authored investment route exceeded its public movement bound')


def role_cost(state, roles):
    buildings = {UNITS[kind].building for kind in roles} - state.buildings
    return (sum(BUILDINGS[kind].cost for kind in buildings) + sum(state.recruit_cost(kind) for kind in roles),
            sum(BUILDINGS[kind].crystals for kind in buildings) + sum(state.recruit_crystal_cost(kind) for kind in roles))


def authored_branch(encoded, plan, *, target_kind, wait_until=None, budget=None):
    """Compare actual preparations before the same named encounter and finite rival.

    The disclosed retirement policy preserves a ranged/core troop where possible,
    then releases the lowest-rank/XP melee duplicate. It never edits resources or
    troops. New funding attempts stop after twelve elapsed turns; a defensive
    detour may itself advance several turns. A killed outgoing veteran
    is a combat loss and may leave a normal recruitment slot instead.
    """
    play = InvestmentOrders(State.from_json(encoded), budget=budget)
    state = play.state
    start_turn = state.turn
    roles = {'keep': (), 'sapper': ('sapper',), 'adept': ('adept',),
             'skyrider': ('skyrider',), 'pair': ('sapper', 'adept'),
             'staged': ('sapper', 'adept', 'skyrider'),
             'fund_first': ('sapper', 'adept', 'skyrider')}[plan]
    initial_quote = dict(zip(('gold', 'crystals'), role_cost(state, roles)))
    bound = start_turn + 12
    stopped = None
    if plan == 'fund_first':
        while play.state.status == 'playing' and play.state.turn <= bound:
            gold, crystals = role_cost(play.state, roles)
            if play.state.gold >= gold and play.state.crystals >= crystals:
                break
            play.rest()
    purchased_ids = set()
    for kind in roles:
        while play.state.status == 'playing' and play.state.turn <= bound:
            state = play.state
            building = UNITS[kind].building
            if building not in state.buildings:
                spec = BUILDINGS[building]
                if state.gold >= spec.cost and state.crystals >= spec.crystals:
                    assert play.do('build', building)
            state = play.state
            candidates = [troop for troop in state.hero.army if troop.id not in purchased_ids]
            if len(state.hero.army) < state.hero.max_army:
                command, args = 'recruit', (kind,)
            elif candidates:
                outgoing = min(candidates, key=lambda troop: (troop.kind not in ('militia', 'swordsman'),
                                                               troop.level, troop.xp, troop.id))
                command, args = 'replace_troop', (outgoing.id, kind)
            else:
                stopped = 'No original troop remains to retire.'
                break
            incoming = state.next_troop_id
            if play.do(command, *args):
                purchased_ids.add(incoming)
                break
            play.rest()
        else:
            stopped = 'funding_bound' if play.state.status == 'playing' else play.state.status
        if stopped:
            break
    while (wait_until is not None and play.state.status == 'playing'
           and play.state.turn < wait_until):
        play.rest()
    ready = snapshot(play.state)
    target = next(pos for pos, province in play.state.provinces.items() if province.site_kind == target_kind)
    target_fight = None
    if not stopped and play.state.status == 'playing':
        for _ in range(24):
            play.march(target)
            if play.state.status != 'playing' or play.state.hero.pos != target:
                break
            if not play.state.actions_left:
                play.rest()
                continue  # Defensive recovery can move the hero away from this site.
            if play.do('explore'):
                assert play.state.battle_province == target
                assert play.state.provinces[play.state.battle_province].site_kind == target_kind
                target_fight = len(play.fights)
                fight(play, 'auto')
            break
        else:
            stopped = 'objective_preparation_bound'
    endpoint = play.state.to_json()
    # Observe two ordinary post-objective turns too. Their actual defensive
    # battles, ownership changes and income are distinct from the objective cost.
    for _ in range(2):
        if play.state.status == 'playing':
            play.rest()
    return dict(plan=plan, wait_until=wait_until, initial_quote=initial_quote, ready=ready,
                stopped=stopped, target=target, target_kind=target_kind, target_fight=target_fight,
                gold_spent=play.gold_spent, crystals_spent=play.crystals_spent,
                replacement_actions=play.replacement_actions, retired=play.retired,
                events=play.events, fights=play.fights, endpoint=json.loads(endpoint),
                aftermath=json.loads(play.state.to_json()))


def authored_comparison(args, *, budget=None):
    """Broaden the earlier experiment with existing authored targets and paid openings."""
    from tools.audit_eador_difficulty import DifficultyTrial
    from eador.model import HERO_CLASSES
    from eador.worldgen import THEMES
    from eador.difficulty import DIFFICULTIES
    target_by_theme = {'frontier': 'relief_column', 'elderwild': 'supply_cache', 'ruins': 'runebound_causeway'}
    sources = [*sorted((ROOT / 'eador').glob('*.py')), Path(__file__).resolve(),
               *(ROOT / 'tools' / name for name in ('audit_eador_difficulty.py', 'audit_eador_economy.py',
                 'audit_eador_resource_breakpoints.py', 'stress_eador_control.py', 'eador_campaign.py'))]
    fingerprints = lambda: {source_name(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    before = fingerprints()
    rows, skipped = [], []
    for seed in args.seeds:
        for hero in args.heroes or HERO_CLASSES:
            for theme in args.themes or THEMES:
                for mode in args.modes or DIFFICULTIES:
                    case = (seed, hero, theme, 'economy', mode, 'direct')
                    trial = DifficultyTrial(*case, budget=budget)
                    window = EarnedWindow(trial.state)
                    trial.state = window
                    observed = trial.run()
                    assert observed == DifficultyTrial(*case, budget=budget).run(), 'Capturing a camp changed its original paid policy'
                    if window.saved is None:
                        skipped.append(dict(case=case, reason='No full affordable Sapper camp on turns 5–7', baseline=observed))
                        continue
                    state = State.from_json(window.saved)
                    target_kind = 'border_watch' if args.target == 'watch' else target_by_theme[theme]
                    target = next(p for p in state.provinces.values() if p.site_kind == target_kind)
                    if target.explored:
                        skipped.append(dict(case=case, reason='The target is already explored at the earned window', baseline=observed))
                        continue
                    branches = [authored_branch(window.saved, plan, target_kind=target_kind, budget=budget)
                                for plan in ('keep', 'sapper', 'adept', 'skyrider', 'pair', 'staged', 'fund_first')]
                    # Same-clock no-purchase controls include recovery and the real
                    # rival operation. They do not backdate a changed battlefield.
                    dates = sorted({branch['ready']['turn'] for branch in branches} - {state.turn})
                    branches += [authored_branch(window.saved, 'keep', target_kind=target_kind, wait_until=date, budget=budget) for date in dates]
                    if args.repeat:
                        for branch in branches:
                            assert branch == authored_branch(window.saved, branch['plan'], target_kind=target_kind,
                                                             wait_until=branch['wait_until'], budget=budget)
                    rows.append(dict(case=case, baseline=observed, input=json.loads(window.saved), branches=branches))
                    print(case, 'start', state.turn, state.gold, 'branches', len(branches), flush=True)
    assert before == fingerprints(), 'Sources changed during the authored comparison'
    report = dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=before, source_files_changed_during_run=[], repeated=args.repeat,
                  target=args.target, seeds=args.seeds, rows=rows, skipped=skipped,
                  cpu_percent=budget.percent if budget else None,
                  scope='Unchanged Economy/direct earned openings; first affordable full camp at turns 5–7. '
                        'Actual purchases, retirements, waits, optional objective and two aftermath turns. '
                        'Explicit automatic tactics, not manual mastery or a full balance acceptance. '
                        'Every tactical phase replays its public orders from an exact save. '
                        'Same-clock kept-veteran controls; no rules or resources are replaced.')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes(gzip.compress(json.dumps(report, separators=(',', ':')).encode(), mtime=0))
    print(f'{len(rows)} earned windows; {len(skipped)} excluded; {sum(len(row["branches"]) for row in rows)} branches')



def tactical_control(args, *, budget=None):
    """A paid Smoke versus Guard choice, followed by the same automatic policy."""
    original = json.loads(gzip.decompress(args.tactical_control_from.read_bytes()))
    row = next(row for row in original['rows']
               if row['case'] == [0, 'Commander', 'ruins', 'economy', 'standard', 'direct'])
    branch = next(branch for branch in row['branches'] if branch['plan'] == 'sapper')
    encounter = branch['fights'][branch['target_fight']]
    state = State.from_json(json.dumps(encounter['initial']))
    prefix = []
    for _ in range(80):
        if budget:
            budget.checkpoint()
        before = state.to_json()
        battle = state.battle
        trace = battle.trace(battle.auto_turn)
        smoke = next((event for event in trace.events if event.kind == 'smoke'
                      and battle.unit(event.actor_id).team == 'player'), None)
        if smoke:
            clouds = set(smoke.after.smoke) - set(smoke.before.smoke)
            assert len(clouds) == 1
            position = next(iter(clouds))[0]
            break
        prefix.append(('auto_turn', ()))
        if battle.outcome:
            raise AssertionError('The retained earned Sapper never chose Smoke')
    else:
        raise AssertionError('The earned Smoke decision exceeded the battle bound')
    branches = []
    for command in ('smoke', 'guard'):
        play = Orders(State.from_json(before), budget=budget)
        args_order = (smoke.actor_id, position) if command == 'smoke' else (smoke.actor_id,)
        getattr(play.state.battle, command)(*args_order)
        saved = play.state.to_json()
        assert State.from_json(saved).to_json() == saved
        fight(play, 'auto')
        # A second complete public continuation establishes repeatability of the
        # explicit first order too, in addition to fight's per-phase saved replay.
        repeat = Orders(State.from_json(before), budget=budget)
        getattr(repeat.state.battle, command)(*args_order)
        fight(repeat, 'auto')
        assert play.fights == repeat.fights and play.state.to_json() == repeat.state.to_json()
        branches.append(dict(command=command, args=args_order, first_order_state=json.loads(saved),
                             fight=play.fights[-1], final=json.loads(play.state.to_json())))
    assert json.loads(json.dumps(branches[0]['fight']['result'])) == encounter['result'], 'Manual Smoke did not reproduce the original paid result'
    report = dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  input_report_sha256=hashlib.sha256(args.tactical_control_from.read_bytes()).hexdigest(),
                  cpu_percent=budget.percent if budget else None,
                  paid_case=row['case'], campaign_input=row['input'], investment_branch=branch,
                  public_prefix=prefix, before=json.loads(before), branches=branches,
                  original_phase_trace=[asdict(event) for event in trace.events],
                  scope='Two explicit public choices at one actual paid Sapper decision; the same later automatic policy. '
                        'The Smoke line exactly reproduces the measured original result. Guard is a legal order alternative, '
                        'not a mutation removing an ability. No native or optimal-play claim.')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes(gzip.compress(json.dumps(report, separators=(',', ':')).encode(), mtime=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT / 'docs/evidence/early-conversion-prototype.json.gz')
    parser.add_argument('--authored', action='store_true', help='Compare actual affordable turn-five/seven camps across existing authored objectives.')
    parser.add_argument('--seeds', type=int, nargs='+', default=[0])
    parser.add_argument('--heroes', nargs='+', default=['Commander'], choices=('Commander', 'Scout', 'Warrior', 'Wizard'))
    parser.add_argument('--themes', nargs='+', default=['ruins'], choices=('frontier', 'elderwild', 'ruins'))
    parser.add_argument('--modes', nargs='+', default=['standard'], choices=('accessible', 'standard', 'challenge'))
    parser.add_argument('--target', choices=('authored', 'watch'), default='authored')
    parser.add_argument('--repeat', action='store_true', help='Repeat every complete branch as well as every saved tactical phase.')
    parser.add_argument('--tactical-control-from', type=Path, help='Replay the earned Causeway Sapper Smoke/Guard decision from an authored report.')
    parser.add_argument('--cpu-percent', type=float, default=25,
                        help='Cooperative allowance as a percent of one CPU core (default 25).')
    args = parser.parse_args()
    budget = CpuBudget(args.cpu_percent)
    if args.tactical_control_from:
        tactical_control(args, budget=budget)
        return
    if args.authored:
        authored_comparison(args, budget=budget)
        return
    state, input_path = input_state()
    sources = [*sorted((ROOT / 'eador').glob('*.py')), Path(__file__).resolve()]
    fingerprints = lambda: {source_name(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    before = fingerprints()
    cases = [(plan, 'auto', False) for plan in ('keep_now', 'keep_rest1', 'tower_now', 'tower_rest1',
             'sapper', 'adept', 'skyrider', 'full_staged', 'keep_rest3', 'tower_rest3', 'full_fund_first')]
    cases.append(('tower_rest3', 'auto', True))
    # Do not make conversion look weak only by throwing away every Swordsman.
    cases += [(plan, 'auto', False) for plan in ('sapper_militia', 'adept_militia', 'skyrider_militia', 'full_staged_tanks')]
    cases += [(plan, 'heal_first', False) for plan in ('keep_rest1', 'adept', 'full_staged', 'tower_rest3')]
    rows = []
    for plan, tactics, delayed in cases:
        row = run(plan, tactics, wait_after_intercept=delayed, budget=budget)
        assert row == run(plan, tactics, wait_after_intercept=delayed, budget=budget)
        rows.append(row)
        print(plan, tactics, delayed, 'ready', row['ready']['turn'], 'result', row['result'],
              row['ending']['turn'], 'deaths', len(row['combat_deaths']), flush=True)
    staged = next(row for row in rows if row['plan'] == 'full_staged' and row['tactics'] == 'auto')
    retry = paid_retry(staged['ending'], budget=budget)
    assert retry == paid_retry(staged['ending'], budget=budget)
    print('staged paid retry', retry['final']['status'], retry['final']['turn'], retry['additional_gold_spent'])
    assert before == fingerprints()
    report = dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=before, source_files_changed_during_run=[],
                  cpu_percent=budget.percent,
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
