"""Shared combat can be watched without replaying private battles or realm settlement."""
from copy import deepcopy
import json

import pytest

from saga2d import CommandError
from eador.concurrent_campaign import ConcurrentCampaign
from eador.combat_journal import MAX_BYTES, MAX_RECORDS, replay_combat
from saga2d.testing.cpu_budget import CpuBudget


def order(match, seat, action, *args, **kwargs):
    match.apply(seat, {'day': match.day, 'realm_revision': match.realms[seat].revision,
                       'action': action, 'args': list(args), 'kwargs': kwargs})


def shared_match():
    """Buy both armies and earn the center's conquest/skill before a seat-1 challenge starts combat."""
    match, budget = ConcurrentCampaign.new(7, heroes=('Warrior', 'Warrior')), CpuBudget(25)

    def win(seat):
        for _ in range(80):
            if match.realms[seat].battle.outcome:
                break
            order(match, seat, 'battle.auto_turn')
            budget.checkpoint()
        assert match.realms[seat].battle.outcome == 'player'
        order(match, seat, 'resolve_battle')

    for seat, pos in ((0, [-1, 0]), (1, [1, 0])):
        order(match, seat, 'build', 'barracks')
        order(match, seat, 'recruit', 'swordsman')
        order(match, seat, 'travel', pos)
        win(seat)
    order(match, 0, 'travel', [0, 0])
    order(match, 1, 'challenge', [0, 0])
    win(0)
    order(match, 0, 'choose', match.realms[0].choice.options[0].id)
    assert match.encounter.battle is not None
    return match


def test_paid_armies_publish_only_accepted_shared_orders_that_replay_to_the_exact_battle():
    """Both seats receive one combat history; replay preserves every saved battle fact and the live authority."""
    match = shared_match()
    assert match.snapshot(0)['presentation']['records'] == []
    initial = json.loads(json.dumps(match.encounter.battle.to_dict()))
    order(match, 1, 'battle.guard', match.encounter.battle.hero_id)
    order(match, 1, 'battle.end_turn')
    order(match, 0, 'battle.guard', match.encounter.battle.enemy_magic.hero_id)
    first, peer = match.snapshot(0)['presentation'], match.snapshot(1)['presentation']
    assert first == peer and first['head'] == 3
    assert [record['seq'] for record in first['records']] == [1, 2, 3]
    assert [record['command']['action'] for record in first['records']] == ['guard', 'end_turn', 'guard']
    assert first['records'][0]['before'] == initial
    saved = match.checkpoint()
    result = replay_combat(first['records'])
    assert result.battle.to_dict() == match.encounter.battle.to_dict()
    assert result.attacker == 1 and result.destination == (0, 0)
    assert result.trace.before.active_team == 'player' and result.trace.after.active_team == 'enemy'
    assert len(result.trace.events) >= 3
    assert match.checkpoint() == saved


def test_rejected_orders_and_changed_snapshot_copies_do_not_change_shared_history():
    """Unauthenticated turns and malformed commands cannot leak into the accepted replay stream."""
    match = shared_match()
    hero = match.encounter.battle.hero_id
    order(match, 1, 'battle.guard', hero)
    saved, presentation = match.checkpoint(), match.snapshot(1)['presentation']
    for seat, action, args, kwargs in ((0, 'battle.end_turn', (), {}),
                                       (1, 'battle.move', (hero, [999, 999]), {}),
                                       (1, 'battle.guard', (hero,), {'unknown': True})):
        with pytest.raises(CommandError):
            order(match, seat, action, *args, **kwargs)
        assert match.checkpoint() == saved and match.snapshot(0)['presentation'] == presentation
    visible = match.snapshot(1)['presentation']
    visible['records'][0]['before']['units'][0]['hp'] = 0
    visible['records'][0]['command']['args'][0] = 999
    assert match.snapshot(0)['presentation'] == presentation
    assert set(presentation['records'][0]) == {
        'seq', 'battle_id', 'attacker', 'destination', 'before', 'command', 'after_sha256'}


def test_real_retreat_retains_the_terminal_trace_without_replaying_realm_rewards():
    """The map may already be settled while viewers still watch the shared defender retreat."""
    match = shared_match()
    order(match, 1, 'battle.end_turn')
    before = match.encounter.battle.to_dict()
    order(match, 0, 'retreat')
    assert match.encounter is None and not match.claims
    assert match.realms[1].choice.kind == 'skill'
    saved = match.checkpoint()
    records = match.snapshot(0)['presentation']['records']
    assert records[-1]['command'] == {'action': 'retreat', 'outcome': 'player', 'reason': 'retreat'}
    result = replay_combat(records)
    assert result.battle.outcome == 'player' and result.battle.outcome_reason == 'retreat'
    assert result.battle.to_dict()['units'] == before['units']
    assert result.trace.events[-1].kind == 'result' and result.trace.events[-1].text == 'Army retreats.'
    assert match.checkpoint() == saved


def test_active_checkpoint_starts_a_fresh_presentation_epoch_and_lazily_records_the_next_order():
    """Rejoining establishes current combat as a baseline instead of replaying obsolete authority history."""
    match = shared_match()
    order(match, 1, 'battle.guard', match.encounter.battle.hero_id)
    old = match.snapshot(0)['presentation']
    saved = match.checkpoint()
    assert 'presentation' not in saved and 'combat_journal' not in saved
    restored = ConcurrentCampaign.restore(saved)
    fresh = restored.snapshot(0)['presentation']
    assert fresh['epoch'] != old['epoch'] and fresh['head'] == 0 and fresh['records'] == []
    assert restored.checkpoint() == saved
    order(restored, 1, 'battle.end_turn')
    record, = restored.snapshot(1)['presentation']['records']
    assert record['seq'] == 1 and record['battle_id'] != old['records'][0]['battle_id']
    assert replay_combat([record]).battle.to_dict() == restored.encounter.battle.to_dict()


def test_replay_refuses_campaign_orders_corrupted_results_and_discontinuous_battles():
    """A client can discard incompatible presentation without applying any command to its campaign."""
    match = shared_match()
    order(match, 1, 'battle.guard', match.encounter.battle.hero_id)
    order(match, 1, 'battle.end_turn')
    valid = match.snapshot(0)['presentation']['records']
    variants = [deepcopy(valid) for _ in range(4)]
    variants[0][0]['command'] = {'action': 'build', 'args': ['market'], 'kwargs': {}}
    variants[1][0]['after_sha256'] = '0' * 64
    variants[2][1]['before']['units'][0]['hp'] -= 1
    variants[3][1]['seq'] += 1
    saved = match.checkpoint()
    for records in variants:
        with pytest.raises(CommandError, match='authoritative state'):
            replay_combat(records)
        assert match.checkpoint() == saved


def test_retained_records_are_a_bounded_contiguous_tail_of_real_manual_turns():
    """Slow viewers get a bounded replay tail and an explicit sequence gap, never unlimited battle history."""
    match, budget = shared_match(), CpuBudget(25)
    for index in range(MAX_RECORDS + 6):
        seat = 1 if match.encounter.battle.active_team == 'player' else 0
        order(match, seat, 'battle.end_turn')
        budget.checkpoint()
    view = match.snapshot(0)['presentation']
    records = view['records']
    assert view['head'] == MAX_RECORDS + 6 and 0 < len(records) <= MAX_RECORDS
    assert records[0]['seq'] > 1
    assert [record['seq'] for record in records] == list(range(records[0]['seq'], view['head'] + 1))
    assert sum(len(json.dumps(record, sort_keys=True, separators=(',', ':')).encode())
               for record in records) <= MAX_BYTES
    assert replay_combat(records).battle.to_dict() == match.encounter.battle.to_dict()
