"""Replay the source-specific Screen plans; run from the recorded checkout root."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

from eador.model import State, RuleError
from tools.eador_screen_campaign import prepare_screen, screen_western_route, screen_northern_route, screen_scout_route
from tools.eador_extraction_campaign import AdventureOrders

ROOT = Path.cwd()

class Purchases:
    def __init__(self, state):
        self.state, self.purchases = state, []
    def __getattr__(self, name):
        attribute = getattr(self.state, name)
        if name not in ('build', 'recruit'):
            return attribute
        def purchase(kind):
            before = self.state.gold, self.state.crystals
            result = attribute(kind)
            self.purchases.append(dict(command=name, kind=kind, gold=before[0]-self.state.gold,
                                       crystals=before[1]-self.state.crystals))
            return result
        return purchase

class RecordedOrders(AdventureOrders):
    def __init__(self, state):
        super().__init__(State.from_json(state.to_json()))
        self.trace = []
    def do(self, command, *args, **kwargs):
        battle = self.battle
        forecast = None
        if command in ('attack', 'pin'):
            attacker, target = (battle.unit(uid) for uid in args)
            hp = target.hp, attacker.hp
            forecast = getattr(battle, 'preview' if command == 'attack' else 'pin_preview')(*args)
        elif command == 'cast':
            target = battle.unit(args[1]); hp = target.hp
            forecast = battle.spell_preview(*args, **kwargs)
        super().do(command, *args, **kwargs)
        if command in ('attack', 'pin'):
            assert forecast == (hp[0]-target.hp, hp[1]-attacker.hp)
        elif command == 'cast':
            assert forecast == abs(target.hp-hp)
        saved = self.state.to_json()
        self.state = State.from_json(saved)
        assert self.state.to_json() == saved
        self.trace.append(dict(command=command,args=args,kwargs=kwargs,forecast=forecast,
                               round=self.battle.round,save_sha256=hashlib.sha256(saved.encode()).hexdigest()))

PLANS = {'western': (screen_western_route, {}), 'western_heal': (screen_western_route, {'heal':True}),
         'northern': (screen_northern_route, {}), 'scout': (screen_scout_route, {})}

def run(seed, mode, plan, *, full=False):
    hero = 'Scout' if plan == 'scout' else 'Commander'
    proxy = Purchases(State.new(seed,hero,theme='elderwild',difficulty=mode))
    state = prepare_screen(hero,state=proxy)
    prepared = state.to_json()
    row = dict(seed=seed,mode=mode,rules_id=state.rules_id,plan=plan,hero=hero,turn=state.turn,
               hero_level=state.hero.level,purchases=proxy.purchases,
               party=[dict(id=t.id,kind=t.kind,level=t.level,hp=t.hp) for t in state.hero.army])
    route,options = PLANS[plan]
    try:
        play = route(State.from_json(prepared),orders_type=RecordedOrders,**options)
    except RuleError as error:
        if full:
            raise
        row.update(status='fixed_orders_need_adaptation',error=str(error))
        return row
    battle = play.battle
    row.update(status='rout_win' if battle.outcome_reason=='rout' else 'fixed_orders_unfinished',
               round=battle.round,missing_hp=sum(u.max_hp-u.hp for u in battle.units if u.team=='player'),
               deaths=sum(not u.alive for u in battle.units if u.team=='player'),
               mana_spent=state.hero.mana-battle.mana,orders=len(play.orders),reloads=len(play.trace))
    if full:
        assert row['status']=='rout_win' and row['deaths']==0
        row.update(prepared=json.loads(prepared),terminal=json.loads(play.state.to_json()),trace=play.trace)
    assert state.to_json()==prepared
    return row

paths=sorted([*ROOT.glob('eador/*.py'),*ROOT.glob('saga2d/**/*.py'),ROOT/'tools/eador_screen_campaign.py',
              ROOT/'tools/eador_campaign.py',ROOT/'tools/eador_extraction_campaign.py',ROOT/'tests/eador/test_screen.py',
              ROOT/'tools/eador_save_expectations.py'])
hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
report=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            source_files=hashes,python=platform.python_version(),platform=platform.platform(),
            harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            scope='Saved ordinary model orders; source-specific scripts are not general playing policies. No native UI claim.',
            strict=[run(7,'standard',plan,full=True) for plan in PLANS],
            exploratory=[run(seed,mode,plan) for mode in ('accessible','standard','challenge')
                         for seed in (0,1,2,7,19) for plan in ('western','northern','scout')])
report['source_files_changed']=[name for name,digest in hashes.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
assert not report['source_files_changed']
Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([{k:row[k] for k in ('plan','turn','round','missing_hp','mana_spent','orders')} for row in report['strict']],indent=2))
