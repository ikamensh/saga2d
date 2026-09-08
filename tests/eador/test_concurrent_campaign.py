"""Two realms develop independently and settle one authoritative campaign day."""
import json

import pytest

from saga2d import CommandError


def order(match, seat, action, *args, **kwargs):
    """Send the same day/realm revision envelope a network client supplies."""
    message = {'day': match.day, 'realm_revision': match.realms[seat].revision,
               'action': action, 'args': list(args), 'kwargs': kwargs}
    match.apply(seat, message)
    return message


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
