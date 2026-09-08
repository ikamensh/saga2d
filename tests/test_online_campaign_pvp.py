"""Hosted concurrent campaigns retain two private realms and ordinary human battles."""
import json
import time

import pytest
from websockets.sync.client import connect

from saga2d import CommandError
from online_server import Room
from online_server.games import create_match, restore_match
from online_server.storage import RoomStore
from tools.cpu_budget import CpuBudget
from tests.test_online_server import command, handshake, receive, running_server


GAME = 'shardbound-pvp-v1'


def realm_order(view, action, *args):
    return {'day': view['day'], 'realm_revision': view['realm']['revision'],
            'action': action, 'args': list(args), 'kwargs': {}}


def assert_restored_view(actual, previous):
    """Authority restart retains every realm/map fact and resets only the ephemeral presentation stream."""
    actual, previous = dict(actual), dict(previous)
    fresh, old = actual.pop('presentation'), previous.pop('presentation')
    assert actual == previous
    assert fresh['epoch'] != old['epoch'] and fresh['head'] == 0 and fresh['records'] == []


def test_private_campaign_checkpoint_preserves_both_realms_and_their_next_commands(tmp_path):
    """The catalog stores complete authority rather than erasing seat 1 through seat 0's view."""
    budget = CpuBudget(25)
    match = create_match(GAME, {'seed': 11, 'theme': 'elderwild', 'difficulty': 'standard',
                               'heroes': ['Warrior', 'Wizard']})
    for seat, building in ((0, 'barracks'), (1, 'temple')):
        match.apply(seat, realm_order(match.snapshot(seat), 'build', building))
        match.apply(seat, realm_order(match.snapshot(seat), 'explore'))
        budget.checkpoint()
    views = [match.snapshot(seat) for seat in (0, 1)]
    assert [view['realm']['hero']['hero_class'] for view in views] == ['Warrior', 'Wizard']
    assert [view['realm']['gold'] for view in views] == [55, 35]
    assert all('realms' not in view and 'gold' not in view['opponent'] for view in views)
    store = RoomStore(tmp_path)
    try:
        store.save(Room(GAME, match, 'two-private-realms'), ttl=900)
    finally:
        store.close()
    store = RoomStore(tmp_path)
    try:
        saved, = store.load()
    finally:
        store.close()
    assert saved['state'] == match.checkpoint()
    assert len(saved['state']['realms']) == 2
    resumed = restore_match(saved['game'], json.loads(json.dumps(saved['state'])))
    for seat in (0, 1):
        assert_restored_view(resumed.snapshot(seat), views[seat])
        following = realm_order(views[seat], 'battle.guard', 0)
        match.apply(seat, following)
        resumed.apply(seat, following)
    assert resumed.checkpoint() == match.checkpoint()


@pytest.mark.parametrize('options, reason', [
    ([], 'object'),
    ({'seed': True}, 'seed'),
    ({'seed': 2**31}, 'seed'),
    ({'heroes': 'Wizard'}, 'heroes'),
    ({'heroes': ['Warrior']}, 'heroes'),
    ({'heroes': ['Warrior', 'Wizard', 'Scout']}, 'heroes'),
    ({'heroes': ['Warrior', {'class': 'Wizard'}]}, 'heroes'),
    ({'heroes': ['Warrior', 'Unknown']}, 'heroes'),
    ({'theme': 'missing'}, 'theme'),
    ({'difficulty': 'missing'}, 'difficulty'),
    ({'hero': 'Wizard'}, 'option'),
    ({'campaign': True}, 'option'),
])
def test_hosted_campaign_options_reject_invalid_or_coop_specific_setup(options, reason):
    """Two-seat setup is bounded and explicit; the distinct game cannot silently become co-op."""
    with pytest.raises(CommandError, match=reason):
        create_match(GAME, options)


def test_hosted_campaign_private_wait_and_human_turn_survive_two_process_restarts(tmp_path):
    """Private tokens recover both realms, an incumbent PvE wait, and the exact defender turn."""
    budget = CpuBudget(25)
    seats, before = None, None

    def submit(seat, action, *args):
        command(sockets[seat], realm_order(views[seat]['state'], action, *args))
        revision = views[seat]['revision']
        views[:] = [receive(socket, predicate=lambda message: message['revision'] > revision)
                    for socket in sockets]
        assert views[0]['revision'] == views[1]['revision']
        assert views[0]['state']['encounter'] == views[1]['state']['encounter']
        budget.checkpoint()
        # Keep scripted traffic within the production per-peer command rate.
        time.sleep(.05)

    def finish_pve(seat):
        for _ in range(80):
            if views[seat]['state']['realm']['battle']['outcome']:
                break
            submit(seat, 'battle.auto_turn')
        assert views[seat]['state']['realm']['battle']['outcome'] == 'player'
        submit(seat, 'resolve_battle')

    for phase in range(3):
        with running_server('--state-dir', tmp_path) as (url, process):
            with connect(url, proxy=None) as host, connect(url, proxy=None) as guest:
                sockets = host, guest
                if phase == 0:
                    first = handshake(host, game=GAME, options={
                        'seed': 7, 'theme': 'frontier', 'difficulty': 'standard',
                        'heroes': ['Warrior', 'Warrior']})
                    receive(host)
                    second = handshake(guest, 'join', game=GAME, room=first['room'])
                    seats = first, second
                    assert first['resume_token'] != second['resume_token']
                else:
                    returned = handshake(host, 'resume', game=GAME, room=seats[0]['room'],
                                         resume_token=seats[0]['resume_token'])
                    waiting = receive(host)
                    assert returned['player'] == 0 and not waiting['ready']
                    assert_restored_view(waiting['state'], before[0])
                    returned = handshake(guest, 'resume', game=GAME, room=seats[1]['room'],
                                         resume_token=seats[1]['resume_token'])
                    assert returned['player'] == 1
                views = [receive(socket, predicate=lambda message: message['ready']) for socket in sockets]
                assert [view['player'] for view in views] == [0, 1]
                assert all('realms' not in view['state'] and 'gold' not in view['state']['opponent']
                           for view in views)
                if before is not None:
                    for view, previous in zip(views, before):
                        assert_restored_view(view['state'], previous)

                if phase == 0:
                    for seat, destination in ((0, [-1, 0]), (1, [1, 0])):
                        submit(seat, 'build', 'barracks')
                        submit(seat, 'recruit', 'swordsman')
                        assert views[seat]['state']['realm']['gold'] == 10
                        submit(seat, 'travel', destination)
                        finish_pve(seat)
                    submit(0, 'travel', [0, 0])
                    incumbent = views[0]['state']['realm']
                    actions = views[1]['state']['realm']['actions_left']
                    submit(1, 'challenge', [0, 0])
                    assert views[0]['state']['realm'] == incumbent
                    assert views[1]['state']['realm']['actions_left'] == actions - 1
                    assert views[0]['state']['realm']['battle'] is not None
                    assert views[1]['state']['encounter']['battle'] is None
                elif phase == 1:
                    finish_pve(0)
                    assert views[0]['state']['realm']['choices'][0]['kind'] == 'skill'
                    assert views[1]['state']['encounter']['battle'] is None
                    submit(0, 'choose', views[0]['state']['realm']['choices'][0]['options'][0]['id'])
                    shared = views[1]['state']['encounter']['battle']
                    assert shared['active_team'] == 'player'
                    submit(1, 'battle.guard', shared['hero_id'])
                    submit(1, 'battle.end_turn')
                    assert views[0]['state']['encounter']['battle']['active_team'] == 'enemy'
                else:
                    shared = views[0]['state']['encounter']['battle']
                    assert shared['active_team'] == 'enemy'
                    submit(0, 'battle.guard', shared['enemy_magic']['hero_id'])
                    gold = [view['state']['realm']['gold'] for view in views]
                    submit(0, 'retreat')
                    assert all(view['state']['encounter'] is None and not view['state']['claims'] for view in views)
                    assert views[0]['state']['realm']['hero']['pos'] == [-2, 0]
                    assert views[1]['state']['realm']['hero']['pos'] == [0, 0]
                    assert [view['state']['realm']['gold'] for view in views] == [max(0, gold[0] - 20), gold[1]]
                    assert all(view['state']['day'] == 1 and view['state']['realm']['actions_left'] == 0 for view in views)
                before = [view['state'] for view in views]
                if phase < 2:
                    # The server already acknowledged the persisted order; no graceful flush.
                    process.kill()
                    process.wait(timeout=5)

        store = RoomStore(tmp_path)
        try:
            saved, = store.load()
        finally:
            store.close()
        assert saved['game'] == GAME and len(saved['state']['realms']) == 2
        resumed = restore_match(GAME, saved['state'])
        for seat in (0, 1):
            assert_restored_view(resumed.snapshot(seat), before[seat])
