"""Summarize retained saves and receipts; never import or execute the game.

Run from any directory: python path/to/summary.py > path/to/summary.json
The historical anchor is read from the adjacent retained evidence directory.
"""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def sha256(blob):
    return hashlib.sha256(blob).hexdigest()


def wounds(units):
    return [
        dict(id=u['id'], kind=u['kind'], hp=u['hp'], max_hp=u['max_hp'],
             missing_hp=u['max_hp'] - max(0, u['hp']))
        for u in units
    ]


def state_wounds(state):
    hero = state['hero']
    army = wounds(hero['army'])
    return dict(hero=hero['max_hp'] - max(0, hero['hp']),
                army=sum(u['missing_hp'] for u in army), army_units=army)


def snapshot(state):
    return {**{k: state[k] for k in ('turn', 'actions_left', 'gold', 'crystals',
                                    'status', 'hero', 'inventory', 'buildings', 'rival')},
            'campaign_stage': state['campaign']['stage'],
            'campaign_phase': state['campaign']['phase'],
            'completed_shards': state['campaign']['completed'],
            'missing_hp': state_wounds(state)}


def battle_health(battle):
    return dict(mana=battle['mana'],
                units=wounds([u for u in battle['units'] if u['team'] == 'player']))


def summarize(plan):
    blob = (HERE / f'{plan}.json.gz').read_bytes()
    data = json.loads(gzip.decompress(blob))
    native = json.loads((HERE / f'{plan}-native/verification.json').read_text())
    initial, final = (json.loads(data[k]) for k in ('initial_state', 'final_state'))
    source = data['source']
    historical_blob = (HERE.parent / 'shardbound-army-plans-cd351a9/mobile.json.gz').read_bytes()
    historical = json.loads(gzip.decompress(historical_blob))
    assert sha256(historical_blob) == source['journal_sha256']
    assert historical['source_commit'] == source['journal_source']
    assert historical['commands'][source['command_index']]['before'] == data['initial_state']
    assert sha256(data['initial_state'].encode()) == source['initial_sha256']
    assert native['input_sha256'] == sha256(blob)
    assert native['input_source'] == source
    assert native['input_execution_source'] == data['execution_source']
    assert native['source_unchanged'] is True
    assert native['final_state'] == data['final_state']
    assert native['exact_commands'] == native['reloads'] == len(data['commands'])
    shared_source = sorted(p for p in data['source_sha256']
                           if p.startswith(('eador/', 'saga2d/')))
    assert all(data['source_sha256'][p] == native['source_sha256'][p] for p in shared_source)

    battles, rests, spells, transactions, resource_changes, skills = [], [], [], [], [], []
    previous, active = data['initial_state'], None
    for number, row in enumerate(data['commands'], 1):
        assert row['before'] == previous, number
        previous = row['after']
        before, after = json.loads(row['before']), json.loads(row['after'])
        command = row['command']
        gold_delta = after['gold'] - before['gold']
        crystal_delta = after['crystals'] - before['crystals']
        assert row['gold_spent'] == -gold_delta, number
        assert row['crystals_spent'] == -crystal_delta, number
        if gold_delta or crystal_delta:
            resource_changes.append(dict(command_number=number, command=command,
                                         gold_delta=gold_delta, crystals_delta=crystal_delta))
        if gold_delta < 0 or crystal_delta < 0:
            before_army, after_army = before['hero']['army'], after['hero']['army']
            before_ids, after_ids = ({u['id'] for u in army} for army in (before_army, after_army))
            transactions.append(dict(
                command_number=number, command=command, args=row['args'],
                gold_spent=max(0, -gold_delta), crystals_spent=max(0, -crystal_delta),
                actions_spent=before['actions_left'] - after['actions_left'],
                added_troops=[u for u in after_army if u['id'] not in before_ids],
                retired_troops=[u for u in before_army if u['id'] not in after_ids]))
        if before['hero']['skill_ranks'] != after['hero']['skill_ranks']:
            skills.append(dict(command_number=number, command=command, args=row['args'],
                               ranks=after['hero']['skill_ranks']))
        if before['battle'] is None and after['battle'] is not None:
            assert active is None
            province = next(p for p in after['provinces'] if p['pos'] == after['battle_province'])
            active = dict(entry_command=number, entry_turn=after['turn'],
                          province=province['name'], province_pos=province['pos'],
                          kind=after['battle_kind'], adventure=after['battle_adventure'],
                          site=province['site'] if after['battle_kind'] == 'site' else None,
                          objective=after['battle']['objective'],
                          entry=battle_health(after['battle']), enemy_phase_commands=[])
        if command == 'battle.end_turn':
            active['enemy_phase_commands'].append(number)
        if command == 'battle.cast':
            old_battle, new_battle = before['battle'], after['battle']
            spells.append(dict(
                command_number=number, args=row['args'], kwargs=row['kwargs'],
                mana_spent=old_battle['mana'] - new_battle['mana'],
                hp_changes=[dict(id=new['id'], kind=new['kind'], hp_delta=new['hp'] - old['hp'])
                            for old, new in zip(old_battle['units'], new_battle['units'])
                            if new['hp'] != old['hp']]))
        if command == 'resolve_battle':
            battle = before['battle']
            assert active is not None and battle['outcome'] is not None
            dead = [u for u in battle['units'] if u['hp'] <= 0]
            active.update(
                resolve_command=number, final_round=battle['round'],
                outcome=battle['outcome'], outcome_reason=battle['outcome_reason'],
                final_objective=battle['objective'], before_reward=battle_health(battle),
                after_reward_missing_hp=state_wounds(after),
                after_reward_mana=after['hero']['mana'],
                casualties=[dict(id=u['id'], kind=u['kind']) for u in dead if u['team'] == 'player'],
                enemies_killed=[dict(id=u['id'], kind=u['kind']) for u in dead if u['team'] == 'enemy'],
                surviving_enemies=wounds([u for u in battle['units'] if u['team'] == 'enemy' and u['hp'] > 0]),
                reward_gold=gold_delta, reward_crystals=crystal_delta)
            battles.append(active)
            active = None
        if command == 'end_turn':
            rests.append(dict(command_number=number, reason=row['reason'],
                              before=snapshot(before), after=snapshot(after)))
    assert previous == data['final_state'] and active is None
    commands = Counter(row['command'] for row in data['commands'])
    gold_spent = sum(t['gold_spent'] for t in transactions)
    crystals_spent = sum(t['crystals_spent'] for t in transactions)
    gold_received = sum(max(0, r['gold_delta']) for r in resource_changes)
    crystals_received = sum(max(0, r['crystals_delta']) for r in resource_changes)
    assert initial['gold'] + gold_received - gold_spent == final['gold']
    assert initial['crystals'] + crystals_received - crystals_spent == final['crystals']
    resource_totals_by_command = {
        command: {key: sum(r[key] for r in resource_changes if r['command'] == command)
                  for key in ('gold_delta', 'crystals_delta')}
        for command in sorted({r['command'] for r in resource_changes})
    }
    return dict(
        journal=f'{plan}.json.gz', journal_sha256=sha256(blob), source=source,
        execution_source=data['execution_source'], command_chain_verified=True,
        game_framework_hashes_matching_native=len(shared_source),
        commands=len(data['commands']), command_counts=dict(sorted(commands.items())),
        skill_choices=skills, entry=snapshot(initial), final=snapshot(final),
        totals=dict(battle_attempts=len(battles), wins=sum(b['outcome'] == 'player' for b in battles),
                    casualties=sum(len(b['casualties']) for b in battles),
                    final_round_sum=sum(b['final_round'] for b in battles),
                    enemy_phases=commands['battle.end_turn'], spells=len(spells),
                    mana_spent=sum(s['mana_spent'] for s in spells), rests=len(rests),
                    gold_spent=gold_spent, crystals_spent=crystals_spent,
                    gold_received=gold_received, crystals_received=crystals_received,
                    paid_command_actions=sum(t['actions_spent'] for t in transactions)),
        battles=battles, spells=spells, rests=rests, transactions=transactions,
        resource_changes=resource_changes, resource_totals_by_command=resource_totals_by_command,
        observations=data['observations'],
        native=dict(report=f'{plan}-native/verification.json',
                    source_commit=native['source_commit'], source_unchanged=native['source_unchanged'],
                    backend=native['backend'], requested_cpu_percent=native['cpu_percent'],
                    commands=native['exact_commands'], reloads=native['reloads'],
                    inputs=len(native['inputs']), listed_milestone_captures=len(native['captures']),
                    wall_seconds=native['elapsed_seconds'], cpu_seconds=native['cpu_seconds'],
                    cpu_wall_percent=100 * native['cpu_seconds'] / native['elapsed_seconds'],
                    scope=native['scope']))


def main():
    plans = ('pathfinder', 'skirmisher')
    branches = {plan: summarize(plan) for plan in plans}
    journals = [json.loads(gzip.decompress((HERE / f'{plan}.json.gz').read_bytes())) for plan in plans]
    assert journals[0]['initial_state'] == journals[1]['initial_state']
    a, b = (d['source_sha256'] for d in journals)
    differences = [p for p in sorted(a.keys() | b.keys()) if a.get(p) != b.get(p)]
    print(json.dumps(dict(
        method='Read-only JSON aggregation; no game imports, command replay or simulation.',
        command_numbers='One-based within each continuation; historical anchor index is zero-based.',
        wounds='Missing HP at the named snapshot, not cumulative damage; promotion, Heal and rests can change it.',
        rounds='Sum of final saved battle rounds; enemy phases count explicit battle.end_turn commands.',
        matched_initial_state=True, execution_manifest_differences=differences,
        branches=branches), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
