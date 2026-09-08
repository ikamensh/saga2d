"""Two realms develop independently and settle one authoritative campaign day."""
import json

import pytest

from saga2d import CommandError
from tools.cpu_budget import CpuBudget


def order(match, seat, action, *args, **kwargs):
    """Send the same day/realm revision envelope a network client supplies."""
    message = {'day': match.day, 'realm_revision': match.realms[seat].revision,
               'action': action, 'args': list(args), 'kwargs': kwargs}
    match.apply(seat, message)
    return message


def win_battle(match, seat, budget):
    """Play ordinary optional auto-turn orders; never inject a battle result."""
    for _ in range(80):
        if match.realms[seat].battle.outcome:
            break
        order(match, seat, 'battle.auto_turn')
        budget.checkpoint()
    assert match.realms[seat].battle.outcome == 'player'
    order(match, seat, 'resolve_battle')


def test_two_realms_develop_independently_then_settle_one_shared_day():
    """Ready grants nothing until both realms finish, and a duplicate cannot settle again."""
    from eador.concurrent_campaign import ConcurrentCampaign

    match = ConcurrentCampaign.new(7, heroes=('Commander', 'Wizard'))
    other = match.snapshot(1)['realm']
    order(match, 0, 'build', 'barracks')
    order(match, 0, 'recruit', 'swordsman')
    assert match.snapshot(1)['realm'] == other
    assert match.realms[0].gold == 10
    assert match.realms[1].gold == 100
    assert match.realms[0].hero.pos != match.realms[1].hero.pos
    assert {p.owner for p in match.provinces.values() if p.capital} == {'realm:0', 'realm:1'}

    before = [(r.gold, r.crystals, r.actions_left) for r in match.realms]
    order(match, 0, 'ready')
    assert match.day == 1
    assert before == [(r.gold, r.crystals, r.actions_left) for r in match.realms]
    with pytest.raises(CommandError, match='ready'):
        order(match, 0, 'build', 'market')
    order(match, 1, 'build', 'temple')
    quote = [match.income(seat) for seat in (0, 1)]
    before = [(r.gold, r.crystals, r.upkeep) for r in match.realms]
    ready = order(match, 1, 'ready')
    assert match.day == 2 and not any(r.ready for r in match.realms)
    assert [(r.gold, r.crystals) for r in match.realms] == [
        (gold + income.gold - upkeep, crystals + income.crystals)
        for (gold, crystals, upkeep), income in zip(before, quote)]
    settled = match.checkpoint()
    with pytest.raises(CommandError, match='day'):
        match.apply(1, ready)
    assert match.checkpoint() == settled

    resumed = ConcurrentCampaign.restore(json.loads(json.dumps(settled)))
    for room in (match, resumed):
        order(room, 0, 'ready')
        order(room, 1, 'ready')
    assert resumed.checkpoint() == match.checkpoint()


def test_two_active_pve_battles_keep_their_own_orders_and_survive_a_checkpoint():
    """Both players fight locally; a peer's turn cannot alter or stale the other battle."""
    from eador.concurrent_campaign import ConcurrentCampaign

    match = ConcurrentCampaign.new(7, heroes=('Warrior', 'Wizard'))
    order(match, 0, 'explore')
    first = match.snapshot(0)['realm']
    order(match, 1, 'explore')
    assert match.snapshot(0)['realm'] == first
    assert match.claims == {realm.capital: realm.seat for realm in match.realms}
    assert all(realm.battle is not None for realm in match.realms)
    pending = {'day': match.day, 'realm_revision': match.realms[1].revision,
               'action': 'battle.guard', 'args': [0], 'kwargs': {}}
    other = match.snapshot(1)['realm']
    order(match, 0, 'battle.guard', 0)
    order(match, 0, 'battle.end_turn')
    assert match.snapshot(1)['realm'] == other and match.day == 1
    match.apply(1, pending)
    assert match.realms[1].battle.unit(0).stance == 'guard'

    saved = match.checkpoint()
    with pytest.raises(CommandError, match='battle'):
        order(match, 0, 'ready')
    enemy = next(unit.id for unit in match.realms[1].battle.units if unit.team == 'enemy')
    with pytest.raises(CommandError):
        order(match, 1, 'battle.guard', enemy)
    assert match.checkpoint() == saved

    resumed = ConcurrentCampaign.restore(json.loads(json.dumps(saved)))
    for room in (match, resumed):
        order(room, 1, 'battle.end_turn')
        order(room, 0, 'retreat')
        assert room.realms[1].battle is not None
        assert room.claims == {room.realms[1].capital: 1}
        order(room, 1, 'retreat')
        assert not room.claims and room.day == 1
        assert not any(province.explored for province in room.provinces.values())
    assert resumed.checkpoint() == match.checkpoint()


def test_contested_arrival_spends_nothing_and_retry_inherits_the_real_guard_wounds():
    """One shared encounter pays once, and pending earned choices hold the day barrier."""
    from eador.concurrent_campaign import ConcurrentCampaign

    budget = CpuBudget(25)
    match = ConcurrentCampaign.new(7, heroes=('Warrior', 'Warrior'))
    for seat, destination in ((0, (-1, 0)), (1, (1, 0))):
        order(match, seat, 'build', 'barracks')
        order(match, seat, 'recruit', 'swordsman')
        order(match, seat, 'travel', list(destination))
        win_battle(match, seat, budget)
    order(match, 0, 'travel', [0, 0])
    claimed = match.checkpoint()
    with pytest.raises(CommandError, match='claimed'):
        order(match, 1, 'travel', [0, 0])
    assert match.checkpoint() == claimed
    order(match, 0, 'battle.auto_turn')
    battle = match.realms[0].battle
    assert battle.outcome is None
    survivors = [(unit.kind, unit.hp) for unit in battle.units if unit.team == 'enemy' and unit.alive]
    original = match.provinces[(0, 0)]
    assert survivors != list(zip(original.guards, original.guard_hp))
    order(match, 0, 'retreat')
    assert not match.claims
    saved = match.checkpoint()
    match = ConcurrentCampaign.restore(saved)
    order(match, 1, 'travel', [0, 0])
    assert [(u.kind, u.hp) for u in match.realms[1].battle.units if u.team == 'enemy'] == survivors
    order(match, 0, 'ready')
    waiting = match.snapshot(0)['realm']
    gold = match.realms[1].gold
    win_battle(match, 1, budget)
    assert match.provinces[(0, 0)].owner == 'realm:1' and not match.claims
    assert match.realms[1].gold == gold + 25
    assert match.realms[1].choice.kind == 'skill'
    assert match.snapshot(0)['realm'] == waiting and match.day == 1
    won = match.checkpoint()
    with pytest.raises(CommandError, match='finished'):
        order(match, 1, 'resolve_battle')
    with pytest.raises(CommandError, match='choice'):
        order(match, 1, 'ready')
    assert match.checkpoint() == won
    resumed = ConcurrentCampaign.restore(won)
    for room in (match, resumed):
        order(room, 1, 'choose', room.realms[1].choice.options[0].id)
        order(room, 1, 'ready')
        assert room.day == 2 and not any(realm.ready for realm in room.realms)
    assert resumed.checkpoint() == match.checkpoint()


@pytest.mark.parametrize('corruption', ['missing', 'orphan', 'wrong_owner', 'ready_battle'])
def test_checkpoint_rejects_encounter_claims_that_cannot_resume(corruption):
    """A saved claim must belong to its active battle; otherwise the map can lock permanently."""
    from eador.concurrent_campaign import ConcurrentCampaign
    from eador.model import SaveFormatError

    match = ConcurrentCampaign.new(7)
    order(match, 0, 'explore')
    saved = match.checkpoint()
    if corruption == 'missing':
        saved['claims'] = []
    elif corruption == 'orphan':
        saved['claims'].append({'pos': [0, 0], 'seat': 1})
    elif corruption == 'wrong_owner':
        saved['claims'][0]['seat'] = 1
    else:
        saved['realms'][0]['ready'] = True
    with pytest.raises(SaveFormatError, match='encounter'):
        ConcurrentCampaign.restore(saved)
