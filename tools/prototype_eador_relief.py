"""THROWAWAY: does enemy Rally create a distinct paid hold decision?

Run: PYTHONPATH=. python tools/prototype_eador_relief.py --output /tmp/relief.json.gz
Inspect manually: add --interactive western (or forward/scout). JSON orders use
ordinary Battle method names/arguments; 'end' guards unused units and ends turn.
This constructs a detached initial battlefield, never a registered site/reward.
"""
from collections import Counter
from dataclasses import asdict, replace
from functools import partial
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import platform
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eador.battle import Battle, BattleObjective
from eador.content import RELICS
from eador.model import HERO_CLASSES, State
from eador.worldgen import FRONTIER_SITES, generate
from tools.audit_eador_aerie import Purchases
from tools.cpu_budget import CpuBudget
from tools.eador_control_campaign import prepare_control_watch

MARSH = {(-1,-2), (1,-3), (-2,-1), (-1,-1), (-1,0), (-1,1), (-1,2)}
SEAL = (0,-2)
TERRAIN = {(q,r): 'marsh' if (q,r) in MARSH else 'plains'
           for q in range(-3,4) for r in range(-3,4) if abs(q+r) <= 3}
WESTERN = ((-3,0), (-2,0), (-3,1), (-2,-1), (-1,-2), (-2,1), (-3,2))
FORWARD = ((-1,-1), (0,-1), (-2,-1), (0,-2), (-1,-2), (-2,0), (-1,0))
ENEMIES = ('skyrider', 'militia', 'archer', 'guard')
ENEMY_POSITIONS = ((3,0), (3,-1), (1,2), (2,1))


def prepare(hero='Commander', *, budget=None):
    budget = CpuBudget(25) if budget is None else budget
    state = Purchases(State.new(7, hero))
    prepare_control_watch(state, kinds=('pikeman','warden','adept') if hero == 'Commander' else ('pikeman','archer'),
                          budget=budget)
    return state


def create(paid, approach):
    """Only initial authored geometry differs; paid soldier/hero data is unchanged."""
    original = Battle.create(paid.hero, list(ENEMIES), 'plains', paid.spells)
    positions = dict(zip([u.id for u in original.units if u.team == 'player'],
                         WESTERN if approach == 'western' else FORWARD))
    positions.update(zip([u.id for u in original.units if u.team == 'enemy'], ENEMY_POSITIONS))
    return replace(original, units=[replace(u, pos=positions[u.id]) for u in original.units],
                   terrain=dict(TERRAIN), objective=BattleObjective('hold', SEAL, 0, 2, 4))


class Orders:
    def __init__(self, battle, *, budget=None):
        self.budget = CpuBudget(25) if budget is None else budget
        self.battle = battle
        self.initial = battle.to_dict()
        self.orders, self.snapshots, self.forecasts = [], [], []

    def enemy(self, kind):
        return next(u.id for u in self.battle.units if u.team == 'enemy' and u.kind == kind)

    def do(self, command, *args):
        self.budget.checkpoint()
        b = self.battle
        if command in ('attack', 'pin'):
            attacker, target = (b.unit(ident) for ident in args)
            before = target.hp, attacker.hp
            forecast = (b.preview if command == 'attack' else b.pin_preview)(*args)
        elif command == 'cast':
            target = b.unit(args[1]); before = target.hp
            forecast = b.spell_preview(*args)
        elif command == 'repulse':
            target = b.unit(args[1]); forecast = b.repulse_preview(*args)
        getattr(b, command)(*args)
        if command in ('attack', 'pin'):
            assert (before[0]-target.hp, before[1]-attacker.hp) == forecast
            self.forecasts.append(dict(order=len(self.orders), kind=command, values=forecast))
        elif command == 'cast':
            assert abs(target.hp-before) == forecast
            self.forecasts.append(dict(order=len(self.orders), kind=command, values=forecast))
        elif command == 'repulse':
            assert target.pos == forecast
            self.forecasts.append(dict(order=len(self.orders), kind=command, values=forecast))
        self.orders.append((command,args))
        snapshot = json.loads(json.dumps(b.to_dict()))
        self.battle = Battle.from_dict(snapshot)
        assert json.loads(json.dumps(self.battle.to_dict())) == snapshot
        self.snapshots.append(snapshot)

    def end(self):
        for unit in self.battle.units:
            if unit.alive and unit.team == 'player' and not unit.acted:
                self.do('guard', unit.id)
        self.do('end_turn')

    def report(self):
        b = self.battle
        return dict(initial=self.initial, orders=self.orders, snapshots=self.snapshots, forecasts=self.forecasts,
                    outcome=b.outcome_reason, round=b.round, progress=b.objective.progress,
                    mana_spent=self.initial['mana']-b.mana,
                    missing_hp=sum(u.max_hp-u.hp for u in b.units if u.team == 'player'),
                    dead=[u.id for u in b.units if u.team == 'player' and not u.alive],
                    survivors=[dict(id=u.id,kind=u.kind,hp=u.hp,max_hp=u.max_hp) for u in b.units if u.team=='player'],
                    living_enemies=[u.kind for u in b.units if u.team == 'enemy' and u.alive])


def forward_opening(p, *, finish_support=True):
    for ident,pos in ((1,(3,-2)), (0,(0,-1)), (3,(1,-1)), (4,SEAL), (6,(1,0)), (2,(-1,-2))):
        p.do('move',ident,pos)
    p.do('pin',3,p.enemy('skyrider')); p.do('cast','bolt',p.enemy('militia'))
    p.do('attack',1,p.enemy('militia'))
    if finish_support:
        p.do('attack',6,p.enemy('militia'))
    p.end()


def forward(p, *, heal=False):
    forward_opening(p)
    p.do('attack',1,p.enemy('skyrider')); p.do('attack',3,p.enemy('skyrider'))
    if heal:
        p.do('cast','heal',1)
    p.end()
    return p


def western(p, *, heal=False, repulse=True):
    # Let Brace receive the flyer; this assembly cannot intercept its support on turn one.
    for ident,pos in ((1,(0,-1)), (0,(-1,0)), (2,(-2,0)), (3,(-1,-1)),
                      (4,SEAL), (5,(-1,1)), (6,(-2,1))):
        p.do('move',ident,pos)
    p.end()
    p.do('move',3,(-1,-2)); p.do('move',0,(-1,-1))
    p.do('cast','bolt',p.enemy('skyrider')); p.do('attack',4,p.enemy('skyrider'))
    p.do('attack',1,p.enemy('militia')); p.do('move',5,(0,1)); p.do('attack',5,p.enemy('militia'))
    p.do('move',6,(-1,0)); p.do('attack',6,p.enemy('militia')); p.do('attack',3,p.enemy('guard'))
    p.end()
    # The injured Pike leaves the seal; the Adept occupies it and pushes its contester away.
    p.do('move',0,(-2,-1)); p.do('cast','bolt',p.enemy('archer'))
    p.do('move',3,(1,-3)); p.do('move',4,(0,-3)); p.do('move',6,SEAL)
    if repulse:
        p.do('repulse',6,p.enemy('guard')); p.do('move',1,(1,-2)); p.do('move',5,(0,-1))
    p.end()
    if heal:
        p.do('cast','heal',4)
    p.end()
    return p


def scout(p, *, veteran_pin=False):
    # The veteran withstands the Guard while the fresh Archer Pins from the protected lane.
    for ident,pos in ((1,(3,-2)), (0,(0,-1)), (3,(1,0)), (4,SEAL), (5,(1,-1)), (2,(-1,-2))):
        p.do('move',ident,pos)
    p.do('pin',3 if veteran_pin else 5,p.enemy('skyrider'))
    for ident in (0,1,5 if veteran_pin else 3):
        p.do('attack',ident,p.enemy('militia'))
    p.end()
    if veteran_pin:
        return p
    p.do('move',5,(1,-3)); p.do('move',1,(1,-2))
    for ident in (0,5,3):
        p.do('attack',ident,p.enemy('skyrider'))
    p.end()
    return p


def passive(p, *, complete=False):
    positions = ((3,(1,-3)), (1,(1,-2)), (4,(0,-3)), (6,(0,-1)), (2,SEAL),
                 (0,(-1,-2)), (5,(-1,-1))) if complete else (
                     (3,(1,-3)), (2,(-1,-2)), (1,(0,-3)), (0,SEAL))
    for ident,pos in positions:
        p.do('move',ident,pos)
    while not p.battle.outcome:
        p.end()
    return p


def passive_search(parties, *, trials=1000, budget=None):
    """Bounded static-screen countersearch, not an optimal policy or impossibility proof."""
    budget = CpuBudget(25) if budget is None else budget
    rng = random.Random(481)
    results = {}
    for name,party in parties.items():
        for approach in ('forward','western'):
            initial = create(party,approach)
            cells = [pos for pos in initial.terrain if initial.grid.distance(pos,SEAL) <= 1]
            outcomes, wins, wounds, best = Counter(), [], [], None
            for trial in range(trials):
                budget.checkpoint()
                battle = Battle.from_dict(initial.to_dict())
                ids = [u.id for u in battle.units if u.team == 'player']; rng.shuffle(ids)
                moves = []
                for ident in ids:
                    options = [pos for pos in battle.reachable(ident) if pos in cells]
                    if options:
                        pos = rng.choice(options); battle.move(ident,pos); moves.append((ident,pos))
                while not battle.outcome:
                    budget.checkpoint()
                    for unit in battle.units:
                        if unit.alive and unit.team == 'player' and not unit.acted:
                            battle.guard(unit.id)
                    battle.end_turn()
                outcomes[battle.outcome_reason] += 1
                if battle.outcome == 'player':
                    wounds.append(sum(u.max_hp-u.hp for u in battle.units if u.team == 'player'))
                    example = dict(trial=trial,moves=moves,round=battle.round,wounds=wounds[-1],final=battle.to_dict())
                    if len(wins) < 3:
                        wins.append(example)
                    if best is None or example['wounds'] < best['wounds']:
                        best = example
            results[name+'-'+approach] = dict(trials=trials,outcomes=dict(outcomes),
                                              winning_wounds_range=(min(wounds),max(wounds)) if wounds else None,
                                              first_winning_examples=wins,best_sampled_win=best)
    budget.checkpoint()
    return results


def source_audit(*, seed_count=1000, budget=None):
    """Find a duplicate ordinary reward route; inherit the displaced reward unchanged."""
    budget = CpuBudget(25) if budget is None else budget
    fixed = {'frontier': {(0,2):'courier_crossing',(-1,1):'muster_yard',(0,-1):'stranded_explorer'},
             'elderwild': {(-1,-1):'supply_cache',(-1,1):'pack_hunt',(0,-1):'smuggler_screen'},
             'ruins': {(-1,1):'sealed_vault',(-1,0):'broken_observatory',(0,0):'aerie_raid',(1,0):'barrow'}}
    protected = {(-2,0),(-2,1),(-2,2),(-1,2),(-1,1),(0,-1),(0,-2),(0,2),(2,0)}
    selections, counts = [], Counter()
    def reward(province):
        return province.site_gold,province.site_crystals,province.site_relic
    for seed in range(seed_count):
        budget.checkpoint()
        rewards = set()
        for theme,sites in fixed.items():
            world = generate(seed,theme)
            for pos,kind in {(-2,0):'shrine',(-2,2):'den',(-1,2):'explorer_camp',**sites}.items():
                assert world[pos].site_kind == kind
            assert any(p.site_kind == 'border_watch' for p in world.values())
            rewards.update(p.site_relic for p in world.values() if p.site_relic)
            if theme != 'frontier':
                continue
            options = []
            for pos,old in sorted(world.items()):
                if pos in protected or pos[0] < 0 or old.site_kind not in FRONTIER_SITES:
                    continue
                survivors = [p for p in world.values() if p.pos != pos and p.pos[0] <= pos[0]
                             and p.site_kind == old.site_kind and reward(p) == reward(old)
                             and Counter(p.site_guards) <= Counter(old.site_guards)]
                if survivors:
                    options.append((old,min(survivors,key=lambda p:p.pos)))
            assert options, f'No preserved ordinary reward route for seed {seed}'
            old,survivor = options[0]
            counts[str(old.pos)] += 1
            selections.append(dict(seed=seed,proposed_source=asdict(old),unchanged_ordinary_route=asdict(survivor)))
        assert rewards == set(RELICS)
    budget.checkpoint()
    return dict(seeds_per_theme=seed_count,protected_sources=True,three_theme_relic_union=sorted(RELICS),
                selected_positions=dict(counts),selections=selections,placement_changed=False,
                reward_policy='Inherit site_gold, site_crystals and site_relic exactly; preserve selected ordinary duplicate.')


def measure(*, trials=1000, world_seeds=1000, budget=None):
    budget = CpuBudget(25) if budget is None else budget
    orders = partial(Orders, budget=budget)
    dirty = subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).splitlines()
    paths = sorted([*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'),
                    *ROOT.joinpath('tools').glob('eador_*.py'),ROOT/'tools/audit_eador_aerie.py',
                    ROOT/'tools/audit_eador_extraction.py',ROOT/'tools/cpu_budget.py',Path(__file__).resolve()])
    hashes = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    parties = {name:prepare(hero, budget=budget) for name,hero in (('commander','Commander'),('scout','Scout'))}
    for hero in HERO_CLASSES:
        party = Purchases(State.new(7,hero)); prepare_control_watch(party,kinds=(),budget=budget)
        parties['four-body-'+hero.lower()] = party
    originals = {name:p.to_json() for name,p in parties.items()}
    plans = {}
    for name,party,approach,route in (
            ('forward','commander','forward',forward),
            ('forward-heal','commander','forward',lambda p:forward(p,heal=True)),
            ('western','commander','western',western),
            ('western-heal','commander','western',lambda p:western(p,heal=True)),
            ('scout','scout','forward',scout)):
        p = route(orders(create(parties[party],approach)))
        assert p.battle.outcome_reason == 'hold' and all(u.alive for u in p.battle.units if u.team=='player')
        plans[name] = p.report()
    enclosed = passive(orders(create(parties['commander'],'forward')),complete=True)
    assert enclosed.battle.outcome_reason == 'hold' and enclosed.battle.round == 2
    plans['seven-body-passive-counterexample'] = enclosed.report()
    for name,party in parties.items():
        if name.startswith('four-body-'):
            p = passive(orders(create(party,'forward')))
            assert p.battle.outcome == 'enemy'
            plans[name+'-old-enclosure'] = p.report()
    late = orders(create(parties['commander'],'forward')); forward_opening(late,finish_support=False)
    assert late.battle.objective.progress == 0 and late.battle.unit(late.enemy('militia')).hp == 2
    assert any('rallies Skyrider' in text for text in late.battle.log)
    plans['missed-support-first-phase'] = late.report()
    late_recover = orders(Battle.from_dict(late.battle.to_dict()))
    while not late.battle.outcome:
        late.end()
    assert late.battle.outcome_reason == 'deadline'
    plans['missed-support-then-guard'] = late.report()
    wrong = scout(orders(create(parties['scout'],'forward')),veteran_pin=True)
    assert wrong.battle.objective.progress == 0 and wrong.battle.unit(wrong.enemy('militia')).hp == 1
    assert any('rallies Skyrider' in text for text in wrong.battle.log)
    plans['wrong-archer-allocation'] = wrong.report()
    omitted = western(orders(create(parties['commander'],'western')),repulse=False)
    assert omitted.battle.outcome_reason == 'deadline' and not omitted.report()['dead']
    plans['western-repulse-omitted'] = omitted.report()
    automatic = {}
    for name,party,approach in (('forward','commander','forward'),('western','commander','western'),('scout','scout','forward')):
        p = orders(create(parties[party],approach))
        while not p.battle.outcome:
            p.do('auto_turn')
        automatic[name] = p.report()
    while not late_recover.battle.outcome:
        late_recover.do('auto_turn')
    automatic['missed-support-recovery'] = late_recover.report()
    search_parties = {name:parties[name] for name in [*('four-body-'+hero.lower() for hero in HERO_CLASSES),'scout','commander']}
    searches = passive_search(search_parties, trials=trials, budget=budget)
    sources = source_audit(seed_count=world_seeds, budget=budget)
    assert all(p.to_json()==originals[name] for name,p in parties.items())
    changed = [name for name,sha in hashes.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha]
    assert not changed
    return dict(source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source_sha256=hashes,source_files_changed=changed,python=platform.python_version(),
                dirty_at_start=dirty,cpu_percent=budget.percent,
                scope='Detached proposed battle; no site, reward or campaign continuation installed.',
                parties={name:dict(snapshot=json.loads(originals[name]),purchases=p.purchases) for name,p in parties.items()},
                plans=plans,automatic=automatic,passive_search=searches,source_audit=sources)


def interactive(variant, *, budget=None):
    budget = CpuBudget(25) if budget is None else budget
    p = Orders(create(prepare('Scout' if variant=='scout' else 'Commander', budget=budget),
                      'western' if variant=='western' else 'forward'), budget=budget)
    while True:
        print('\033[2J\033[H',end='')
        b = p.battle
        print(f'RELIEF PROTOTYPE | round {b.round}/4 | hold {b.objective.progress}/2 at {SEAL} | mana {b.mana} | {b.outcome_reason or "playing"}')
        print(' ID   TEAM    KIND        HEX       HP       ORDER/MOVE   PIN   STANCE')
        for u in b.units:
            print(f'{u.id:4}  {u.team:7} {u.kind:11} {str(u.pos):9} {u.hp:2}/{u.max_hp:<3}  '
                  f'{str(u.acted):5}/{str(u.moved):5}  {str(u.pinned):5} {u.stance or "—"}')
        print('\n'+'\n'.join(b.log[-5:]))
        print('[JSON] ["move", 4, [0,-2]] / ["pin", 3, enemy_id] / ["cast", "bolt", enemy_id]  [end] guard + end  [q] quit')
        command=input('> ')
        if command=='q':return
        if command=='end':p.end()
        else:
            values=json.loads(command)
            if values[0]=='move':values[2]=tuple(values[2])
            p.do(*values)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/relief-prototype.json.gz'))
    parser.add_argument('--interactive',choices=('western','forward','scout'))
    parser.add_argument('--trials',type=int,default=1000,help='Search trials per party and approach (default 1000)')
    parser.add_argument('--world-seeds',type=int,default=1000,help='World seeds per theme (default 1000)')
    parser.add_argument('--cpu-percent',type=float,default=25,
                        help='CPU allowance as a percent of one core (default 25; 100 for explicit stress)')
    args=parser.parse_args(argv)
    if args.trials < 1 or args.world_seeds < 1:
        parser.error('trials and world-seeds must be positive')
    try:
        budget=CpuBudget(args.cpu_percent)
    except ValueError as error:
        parser.error(str(error))
    if args.interactive:interactive(args.interactive,budget=budget)
    else:
        report=measure(trials=args.trials,world_seeds=args.world_seeds,budget=budget)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with gzip.open(args.output,'wt') as handle:json.dump(report,handle,separators=(',',':'))
        for name,result in report['plans'].items():
            print(name,result['outcome'],result['round'],'wounds',result['missing_hp'],'mana',result['mana_spent'],'dead',result['dead'])
        for name,result in report['passive_search'].items():
            print('passive search',name,result['outcomes'])
        print('placement',report['source_audit']['selected_positions']);print(args.output)


if __name__=='__main__':
    main()
