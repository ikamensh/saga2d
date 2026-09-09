"""Tribes rooms on the dedicated server: turns, option limits, checkpoints and restarts."""
import json
import os

import pytest
from websockets.sync.client import connect

from saga2d.testing.online import command, handshake, receive, running_server, server_fixture
from tribes.multiplayer import ONLINE

GAME = 'tribes-v1'
SPEC = 'tribes.multiplayer:ONLINE'
server_url = server_fixture(SPEC)


def test_tribes_room_enforces_turns_and_publishes_authoritative_state(server_url):
    """Internet peers share a server-owned match and cannot take another faction's turn."""
    with connect(server_url, proxy=None) as host, connect(server_url, proxy=None) as guest:
        welcome = handshake(host, game=GAME, options={'seed': 7, 'size': 11})
        waiting = receive(host)
        assert waiting['player'] == 0 and not waiting['ready']
        joined = handshake(guest, 'join', game=GAME, room=welcome['room'])
        assert joined['player'] == 1
        assert joined['resume_token'] != welcome['resume_token']
        ready = receive(host, predicate=lambda message: message['ready'])
        assert receive(guest)['state'] == ready['state']
        command(guest, {'action': 'end_turn'})
        assert 'not your turn' in receive(guest, 'error')['error']
        command(host, {'action': 'end_turn'}, ready['revision'])
        changed = receive(guest)
        assert changed['state']['world']['current'] == 1
        assert changed['revision'] > ready['revision']
        assert receive(host)['state'] == changed['state']



@pytest.mark.parametrize('options, fragment', [
    ({'size': 100000}, 'size'),
    ({'size': True}, 'size'),
    ({'undeclared': 'field'}, 'option'),
])
def test_oversized_or_undeclared_options_cannot_allocate_a_world(server_url, options, fragment):
    with connect(server_url, proxy=None) as bad:
        bad.send(json.dumps({'type': 'create', 'protocol': 1, 'game': GAME, 'options': options}))
        assert fragment in receive(bad, 'reject')['error'].lower()
    with connect(server_url, proxy=None) as good:
        handshake(good, game=GAME, options={'size': 11})
        assert receive(good)['state']['world']['current'] == 0


def test_rooms_and_private_seats_survive_server_restart(tmp_path):
    """Acknowledged turn orders survive even an abrupt process loss."""
    with running_server(SPEC, arguments=('--state-dir', tmp_path)) as (url, process):
        with connect(url, proxy=None) as host, connect(url, proxy=None) as guest:
            seat0 = handshake(host, game=GAME)
            receive(host)
            seat1 = handshake(guest, 'join', game=GAME, room=seat0['room'])
            receive(host)
            receive(guest)
            command(host, {'action': 'end_turn'})
            before = receive(guest)
            process.kill()
            process.wait(timeout=5)
    if os.name != 'nt':  # Windows has no POSIX mode bits to check.
        assert (tmp_path / 'rooms.sqlite3').stat().st_mode & 0o777 == 0o600
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


def test_trusted_checkpoint_keeps_existing_json_and_the_next_real_order():
    """The match resumes exact turn state using its unchanged checkpoint format."""
    spec = ONLINE[GAME]
    match = spec.create({'size': 11})
    match.apply(0, {'action': 'end_turn'})
    before = json.loads(json.dumps(match.snapshot(0)))
    checkpoint = json.loads(json.dumps(spec.checkpoint(match)))
    assert checkpoint == before
    resumed = spec.restore(checkpoint)
    assert resumed.snapshot(0) == match.snapshot(0)
    assert resumed.snapshot(1) == match.snapshot(1)
    match.apply(1, {'action': 'end_turn'})
    resumed.apply(1, {'action': 'end_turn'})
    assert json.loads(json.dumps(resumed.snapshot(0))) != before
    assert resumed.snapshot(0) == match.snapshot(0)
