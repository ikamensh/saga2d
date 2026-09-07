"""Apply explicitly supplied public commands to one retained, never-rewound journey."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from eador.model import State
from tools.audit_eador_army_plans import SavedCommands
from tools.cpu_budget import CpuBudget

SEED = int(sys.argv[1])
assert SEED in (5, 12), 'Only the two declared fresh campaigns are supported.'
PATH = Path(__file__).parent / f'route-seed{SEED}.json.gz'
DECLARATION = Path(__file__).parent / 'route-declarations.md'


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
                             reason=battle.outcome_reason, log=battle.log[-12:], units=[],
                             evacuation_blocked=battle.evacuation_blocked_reason)
        for unit in battle.units:
            row = dict(id=unit.id, kind=unit.kind, team=unit.team, pos=unit.pos,
                       hp=unit.hp, max_hp=unit.max_hp, attack=unit.attack,
                       defense=unit.defense, range=unit.attack_range,
                       moved=unit.moved, acted=unit.acted, stance=unit.stance,
                       retaliated=unit.retaliated, pinned=unit.pinned,
                       spent=unit.spent_abilities, movement=unit.move_range,
                       terrain_walk=unit.terrain_walk, skirmisher=unit.skirmisher)
            if unit.alive and unit.team == 'player' and not unit.acted and not battle.outcome:
                row['attacks'] = [(target.id, battle.preview(unit.id, target.id))
                                  for target in battle.targets(unit.id)]
                row['pins'] = [(target.id, battle.pin_preview(unit.id, target.id))
                               for target in battle.pin_targets(unit.id)]
                row['swaps'] = [target.id for target in battle.swap_targets(unit.id)]
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
                                 site_guards=list(zip(p.site_guards, p.site_guard_hp)),
                                 site_relic=p.site_relic, site_gold=p.site_gold,
                                 site_crystals=p.site_crystals,
                                 explored=p.explored, income=p.income, crystals=p.crystals)
                            for p in state.provinces.values()]
    return out


def source_manifest():
    paths = sorted([*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'),
                    ROOT / 'tools/audit_eador_army_plans.py', ROOT / 'tools/cpu_budget.py'])
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


def load_journal(budget):
    manifest = source_manifest()
    director_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if PATH.exists():
        data = json.loads(gzip.decompress(PATH.read_bytes()))
        assert data['source_sha256'] == manifest, 'Authenticated game or command-adapter source changed.'
        assert data['director_sha256'] == director_sha, 'The retained director changed.'
        assert data['source']['seed'] == SEED
        assert not data.get('halted_on_invalid_mutation'), 'A failed command mutated state; this journey is frozen for review.'
        previous = data['initial_state']
        for number, row in enumerate(data['commands'], 1):
            assert row['before'] == previous, f'Broken saved command join at {number}.'
            previous = row['after']
        assert previous == data['final_state']
        return data
    state = State.new_campaign(SEED, 'Commander', difficulty='standard')
    initial = state.to_json()
    assert State.from_json(initial).to_json() == initial
    declaration = DECLARATION.read_text()
    prior_path = Path(__file__).parent / 'zero-order' / f'seed{SEED}.json.gz'
    prior = json.loads(gzip.decompress(prior_path.read_bytes()))
    assert not prior['commands'] and not prior['invalid_attempts']
    assert prior['initial_state'] == initial, 'Fresh origin changed since the declared plan.'
    data = dict(
        source=dict(kind='new_campaign', seed=SEED, hero_class='Commander', difficulty='standard',
                    initial_sha256=hashlib.sha256(initial.encode()).hexdigest()),
        execution_source=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        execution_dirty_files=subprocess.check_output(
            ['git', 'status', '--porcelain', '--untracked-files=all'], cwd=ROOT, text=True).splitlines(),
        source_sha256=manifest, director_sha256=director_sha,
        plan=f'frontier_seed_{SEED}', cpu_percent=25,
        policy='Fresh Commander campaign generated through State.new_campaign. Explicitly agent-directed public commands only; no historical or autoplay opening, no decision-search branches, no injected resources, no rewind or restart.',
        zero_order_predecessor=dict(path=str(prior_path), sha256=hashlib.sha256(prior_path.read_bytes()).hexdigest(), initial_sha256=prior['source']['initial_sha256']),
        declaration=declaration, declaration_sha256=hashlib.sha256(declaration.encode()).hexdigest(),
        initial_state=initial, final_state=initial, commands=[], observations=[], invalid_attempts=[])
    budget.checkpoint()
    write(data)
    return data


ALLOWED_COMMANDS = {
    'build', 'recruit', 'replace_troop', 'travel', 'explore', 'end_turn', 'choose',
    'equip', 'resolve_battle', 'retreat', 'infuse',
    'battle.move', 'battle.attack', 'battle.pin', 'battle.guard',
    'battle.cast', 'battle.swap', 'battle.evacuate', 'battle.smoke',
    'battle.repulse', 'battle.rally', 'battle.end_turn',
}


request = json.load(sys.stdin)
budget = CpuBudget(25)
data = load_journal(budget)
played = SavedCommands(State.from_json(data['final_state']), budget)
if request.get('observation'):
    data['observations'].append(dict(after_commands=len(data['commands']), text=request['observation']))
    write(data)
for supplied in request.get('orders', []):
    before_attempt = played.state.to_json()
    forecast = None
    try:
        command, args = supplied['command'], supplied.get('args', [])
        assert command in ALLOWED_COMMANDS, 'Only explicit public play commands are allowed; no autoplay, restart, recovery or advance.'
        assert supplied['reason'].strip(), 'Every order needs its actual rationale.'
        if command == 'choose' and played.state.choice and played.state.choice.kind == 'skill':
            assert args == ['tactician'], 'The declared Commander policy chooses Tactician.'
        if command == 'travel':
            args = [tuple(args[0])]
        elif command in ('battle.move', 'battle.smoke'):
            args = [args[0], tuple(args[1])]
        if command in ('battle.attack', 'battle.pin'):
            preview = played.battle.pin_preview if command == 'battle.pin' else played.battle.preview
            forecast = list(preview(*args))
            if 'expected' in supplied:
                assert forecast == supplied['expected'], (command, args, forecast, supplied['expected'])
        played.order(command, *args, **supplied.get('kwargs', {}))
    except Exception as error:
        # Keep the rejection and re-raise it. Never silently rewind a partial mutation.
        after_attempt = played.state.to_json()
        unchanged = after_attempt == before_attempt
        data['invalid_attempts'].append(dict(
            after_commands=len(data['commands']), supplied=supplied, forecast=forecast,
            error_type=type(error).__name__, error=str(error), state_unchanged=unchanged,
            before=before_attempt, after=after_attempt))
        data['observations'].append(dict(
            after_commands=len(data['commands']),
            text=f"Rejected {supplied.get('command')}: {type(error).__name__}: {error}. State unchanged: {unchanged}."))
        if not unchanged:
            data['halted_on_invalid_mutation'] = True
            data['failed_state'] = after_attempt
        write(data)
        raise
    row = played.commands[-1]
    row['reason'] = supplied['reason']
    if forecast is not None:
        row['forecast'] = forecast
    data['commands'].append(row)
    data['final_state'] = row['after']
    write(data)
before = played.state.to_json()
view = inspect(played.state, request)
budget.checkpoint()
assert played.state.to_json() == before, 'Inspection must be read-only'
print(f"Commands {len(data['commands'])}; turn {view['turn']}, actions {view['actions']}, "
      f"gold {view['gold']}, crystals {view['crystals']}, position {view['position']}, status {view['status']}")
if 'battle' in view:
    b = view['battle']
    print('BATTLE', b['kind'], b['province'], 'ROUND', b['round'], 'MANA', b['mana'], 'OUTCOME', b['outcome'])
    print('OBJECTIVE', b['objective'], 'REASON', b['reason'], 'EVACUATE', b['evacuation_blocked'])
    for u in b['units']:
        print(u['id'], u['kind'], u['pos'], f"{u['hp']}/{u['max_hp']}",
              'moved' if u['moved'] else '', 'acted' if u['acted'] else '',
              'reacted' if u['retaliated'] else '', 'PINNED' if u['pinned'] else '', u['stance'] or '',
              'A', u.get('attacks', []), 'P', u.get('pins', []), 'R', u.get('repulse', []),
              'S', u.get('spells', {}), 'SWAP', u.get('swaps', []),
              'movement', u['movement'], 'terrain_walk', u['terrain_walk'], 'skirmisher', u['skirmisher'])
        if 'reachable' in u:
            print('  MOVE', u['reachable'])
    print('LOG', b['log'])
    if 'terrain' in b:
        print('TERRAIN', b['terrain'])
else:
    print(json.dumps(view, default=str))
