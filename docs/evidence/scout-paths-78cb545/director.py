"""Apply explicitly supplied public commands to one retained, never-rewound journey."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path('/tmp/saga2d-scout-paths-78cb545')
sys.path.insert(0, str(ROOT))
from eador.model import State
from tools.audit_eador_army_plans import SavedCommands
from tools.cpu_budget import CpuBudget

PLAN = sys.argv[1]
assert PLAN in ('pathfinder', 'skirmisher')
PATH = Path('/tmp/shardbound-scout-' + PLAN + '-78cb545.json.gz')


def write(data):
    pending = PATH.with_suffix('.pending')
    pending.write_bytes(gzip.compress(json.dumps(data, separators=(',', ':')).encode(), mtime=0))
    pending.replace(PATH)


def inspect(state, request):
    hero = state.hero
    out = dict(turn=state.turn, actions=state.actions_left, gold=state.gold,
               crystals=state.crystals, status=state.status, position=hero.pos,
               hero=dict(hp=hero.hp, max_hp=hero.max_hp, xp=hero.xp, mana=hero.mana,
                         max_mana=hero.max_mana, level=hero.level, skills=hero.skill_ranks,
                         relic=hero.relic),
               roster=[vars(t) for t in hero.army], buildings=sorted(state.buildings),
               inventory=state.inventory, log=state.log[-5:])
    if state.campaign:
        c = state.campaign
        out['campaign'] = dict(stage=c.stage, contract=c.contract, phase=c.phase,
                               offers=c.offers, recovery_used=c.recovery_used)
    out['rival'] = dict(vars(state.rival))
    out['rival']['army'] = [vars(t) for t in state.rival.army]
    if state.choice:
        out['choice'] = dict(kind=state.choice.kind,
                             options=[vars(option) for option in state.choice.options])
    battle = state.battle
    if battle:
        out['battle'] = dict(round=battle.round, mana=battle.mana,
                             kind=state.battle_kind, province=state.battle_province,
                             objective=vars(battle.objective), outcome=battle.outcome,
                             reason=battle.outcome_reason, log=battle.log[-12:], units=[])
        for unit in battle.units:
            row = dict(id=unit.id, kind=unit.kind, team=unit.team, pos=unit.pos,
                       hp=unit.hp, max_hp=unit.max_hp, attack=unit.attack,
                       defense=unit.defense, range=unit.attack_range,
                       moved=unit.moved, acted=unit.acted, stance=unit.stance,
                       retaliated=unit.retaliated, pinned=unit.pinned,
                       spent=unit.spent_abilities)
            if unit.alive and unit.team == 'player' and not unit.acted and not battle.outcome:
                row['attacks'] = [(target.id, battle.preview(unit.id, target.id))
                                  for target in battle.targets(unit.id)]
                row['pins'] = [(target.id, battle.pin_preview(unit.id, target.id))
                               for target in battle.pin_targets(unit.id)]
                row['repulse'] = [(target.id, battle.repulse_preview(unit.id, target.id))
                                  for target in battle.repulse_targets(unit.id)]
                spells = battle.spells if unit.id == 0 else ('heal',) if unit.can_heal else ()
                row['spells'] = {spell: dict(cost=battle.spell_cost(spell),
                                  targets=[(target.id, battle.spell_preview(spell, target.id, caster_id=unit.id))
                                           for target in battle.spell_targets(spell, caster_id=unit.id)])
                                  for spell in spells if battle.mana >= battle.spell_cost(spell)}
            if unit.id in request.get('moves', []):
                row['reachable'] = sorted(battle.reachable(unit.id))
            out['battle']['units'].append(row)
        if request.get('terrain'):
            out['battle']['terrain'] = [(pos, kind) for pos, kind in battle.terrain.items() if kind != 'plains']
    if request.get('world'):
        out['provinces'] = [dict(pos=p.pos, owner=p.owner, name=p.name, terrain=p.terrain,
                                 guards=list(zip(p.guards, p.guard_hp)), site=p.site_kind,
                                 explored=p.explored, income=p.income, crystals=p.crystals)
                            for p in state.provinces.values()]
    return out


request = json.load(sys.stdin)
if not PATH.exists():
    source = ROOT / 'docs/evidence/shardbound-army-plans-cd351a9/mobile.json.gz'
    blob = source.read_bytes()
    assert hashlib.sha256(blob).hexdigest() == '1962ca77a5cbad06de2d81a5591e18d35e5502429dbe0d55b8b07a36bde00d5c'
    history = json.loads(gzip.decompress(blob))
    initial = history['commands'][14]['before']
    assert State.from_json(initial).to_json() == initial
    data = dict(source=dict(path=str(source.relative_to(ROOT)), journal_sha256=hashlib.sha256(blob).hexdigest(),
                            journal_source=history['source_commit'], command_index=14,
                            initial_sha256=hashlib.sha256(initial.encode()).hexdigest()),
                execution_source=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted([*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'),
                                                ROOT/'tools/audit_eador_army_plans.py', ROOT/'tools/cpu_budget.py'])},
                plan=PLAN, policy='One of two prescribed Scout advancements, chosen through public skill rewards. Root-directed commands with explicit rationales. Historical opening used autoplay; '
                       'no autoplay or decision-search branches in this continuation. No resources or state fields injected.',
                initial_state=initial, final_state=initial, commands=[])
    write(data)
else:
    data = json.loads(gzip.decompress(PATH.read_bytes()))
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == sha for p, sha in data['source_sha256'].items())
played = SavedCommands(State.from_json(data['final_state']), CpuBudget(25))
if request.get('observation'):
    data.setdefault('observations', []).append(dict(after_commands=len(data['commands']), text=request['observation']))
    write(data)
for supplied in request.get('orders', []):
    command, args = supplied['command'], supplied.get('args', [])
    assert command != 'battle.auto_turn', 'This journey requires explicitly directed orders.'
    assert supplied['reason'].strip()
    if command == 'choose' and played.state.choice and played.state.choice.kind == 'skill':
        assert args == [PLAN], 'Both earned skill choices must follow the declared plan.'
    if command == 'travel':
        args = [tuple(args[0])]
    elif command in ('battle.move', 'battle.smoke'):
        args = [args[0], tuple(args[1])]
    forecast = None
    if command in ('battle.attack', 'battle.pin'):
        preview = played.battle.pin_preview if command == 'battle.pin' else played.battle.preview
        forecast = list(preview(*args))
        if 'expected' in supplied:
            assert forecast == supplied['expected'], (command, args, forecast, supplied['expected'])
    played.order(command, *args, **supplied.get('kwargs', {}))
    row = played.commands[-1]
    row['reason'] = supplied['reason']
    if forecast is not None:
        row['forecast'] = forecast
    data['commands'].append(row)
    data['final_state'] = row['after']
    write(data)
before = played.state.to_json()
view = inspect(played.state, request)
assert played.state.to_json() == before, 'Inspection must be read-only'
print(f"Commands {len(data['commands'])}; turn {view['turn']}, actions {view['actions']}, "
      f"gold {view['gold']}, crystals {view['crystals']}, position {view['position']}, status {view['status']}")
if 'battle' in view:
    b = view['battle']
    print('BATTLE', b['kind'], b['province'], 'ROUND', b['round'], 'MANA', b['mana'], 'OUTCOME', b['outcome'])
    for u in b['units']:
        print(u['id'], u['kind'], u['pos'], f"{u['hp']}/{u['max_hp']}",
              'moved' if u['moved'] else '', 'acted' if u['acted'] else '',
              'reacted' if u['retaliated'] else '', 'PINNED' if u['pinned'] else '', u['stance'] or '',
              'A', u.get('attacks', []), 'P', u.get('pins', []), 'R', u.get('repulse', []),
              'S', u.get('spells', {}))
        if 'reachable' in u:
            print('  MOVE', u['reachable'])
    print('LOG', b['log'])
    if 'terrain' in b:
        print('TERRAIN', b['terrain'])
else:
    print(json.dumps(view, default=str))
