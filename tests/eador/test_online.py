"""Shardbound co-op rooms on the dedicated server: shared rules, checkpoints and restarts."""
import json

import pytest
from websockets.sync.client import connect

from eador.model import State
from eador.multiplayer import ONLINE, ShardboundMatch
from saga2d.server import Room
from saga2d.server.storage import RoomStore
from saga2d.testing.online import command, handshake, receive, running_server, server_fixture

GAME = 'shardbound-v1'
SPEC = 'eador.multiplayer:ONLINE'
server_url = server_fixture(SPEC)


def test_shardbound_coop_runs_campaign_and_battle_rules_for_both_partners(server_url):
    """A partner develops the realm and the other enters tactical combat on the same server state."""
    from eador.model import State
    with connect(server_url, proxy=None) as host, connect(server_url, proxy=None) as guest:
        room = handshake(host, game='shardbound-v1', options={'seed': 7})
        receive(host)
        handshake(guest, 'join', game='shardbound-v1', room=room['room'])
        receive(host)
        receive(guest)
        command(guest, {'action': 'build', 'target': 'state', 'args': ['barracks']})
        assert 'barracks' in State.from_json(receive(host)['state']['campaign']).buildings
        receive(guest)
        command(host, {'action': 'explore', 'target': 'state', 'args': []})
        battle = State.from_json(receive(guest)['state']['campaign']).battle
        assert battle is not None
        receive(host)
        unit = next(unit for unit in battle.units if unit.team == 'player')
        command(guest, {'action': 'guard', 'target': 'battle', 'args': [unit.id]})
        changed = receive(host)
        assert State.from_json(changed['state']['campaign']).battle.unit(unit.id).acted
        assert receive(guest)['state'] == changed['state']



def test_rooms_and_private_seats_survive_server_restart(tmp_path):
    """Trusted checkpoints restore private seats and a partly played battle after process loss."""
    with running_server(SPEC, arguments=('--state-dir', tmp_path)) as (url, process):
        with connect(url, proxy=None) as host, connect(url, proxy=None) as guest:
            seat0 = handshake(host, game=GAME)
            receive(host)
            seat1 = handshake(guest, 'join', game=GAME, room=seat0['room'])
            receive(host)
            receive(guest)
            command(host, {'action': 'build', 'target': 'state', 'args': ['barracks']})
            receive(guest)
            command(guest, {'action': 'explore', 'target': 'state', 'args': []})
            receive(guest)
            command(host, {'action': 'guard', 'target': 'battle', 'args': [0]})
            before = receive(guest)
            assert State.from_json(before['state']['campaign']).battle.unit(0).acted
            # Acknowledged orders survive even an abrupt power/process loss.
            process.kill()
            process.wait(timeout=5)
    with running_server(SPEC, arguments=('--state-dir', tmp_path)) as (url, process):
        with connect(url, proxy=None) as host, connect(url, proxy=None) as guest:
            returned = handshake(host, 'resume', game=GAME, room=seat0['room'], resume_token=seat0['resume_token'])
            assert returned['player'] == 0
            assert not receive(host)['ready']
            handshake(guest, 'resume', game=GAME, room=seat0['room'], resume_token=seat1['resume_token'])
            resumed = receive(guest)
            assert resumed['ready']
            assert resumed['state'] == before['state']
            assert resumed['revision'] > before['revision']
            expected = State.from_json(before['state']['campaign'])
            troop = next(unit for unit in expected.battle.units if unit.team == 'player' and not unit.acted)
            expected.battle.guard(troop.id)
            command(guest, {'action': 'guard', 'target': 'battle', 'args': [troop.id]})
            assert receive(guest)['state']['campaign'] == expected.to_json()


def test_trusted_checkpoint_keeps_existing_json_and_the_next_real_order():
    """The realm resumes exact paid state using its unchanged checkpoint format."""
    spec = ONLINE[GAME]
    match = spec.create({})
    match.apply(0, {'target': 'state', 'action': 'build', 'args': ['barracks']})
    before = json.loads(json.dumps(match.snapshot(0)))
    checkpoint = json.loads(json.dumps(spec.checkpoint(match)))
    assert checkpoint == before
    resumed = spec.restore(checkpoint)
    assert resumed.snapshot(0) == match.snapshot(0)
    following = {'target': 'state', 'action': 'recruit', 'args': ['swordsman']}
    match.apply(1, following)
    resumed.apply(1, following)
    assert json.loads(json.dumps(resumed.snapshot(0))) != before
    assert resumed.snapshot(0) == match.snapshot(0)
    assert resumed.snapshot(1) == match.snapshot(1)


def test_room_storage_retains_campaign_hidden_from_player_snapshots(tmp_path):
    """A filtered view cannot erase an actual paid realm or its unfinished battle on restart."""
    class FilteredCampaign(ShardboundMatch):
        def snapshot(self, player):
            return {'status': self.state.status}

    match = FilteredCampaign()
    match.apply(0, {'target': 'state', 'action': 'build', 'args': ['barracks']})
    match.apply(1, {'target': 'state', 'action': 'explore', 'args': []})
    expected = ShardboundMatch.snapshot(match, 0)
    store = RoomStore(tmp_path)
    try:
        store.save(Room(GAME, match, 'private-campaign'), 900, ONLINE[GAME].checkpoint(match))
    finally:
        store.close()

    reopened = RoomStore(tmp_path)
    try:
        saved, = reopened.load()
    finally:
        reopened.close()
    assert saved['state'] == expected
    resumed = ONLINE[saved['game']].restore(saved['state'])
    unit = next(unit for unit in resumed.state.battle.units if unit.team == 'player')
    guard = {'target': 'battle', 'action': 'guard', 'args': [unit.id]}
    match.apply(1, guard)
    resumed.apply(1, guard)
    assert resumed.state.battle.unit(unit.id).acted
    assert resumed.snapshot(0) == ShardboundMatch.snapshot(match, 0)
