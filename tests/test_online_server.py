"""Online players cross real WebSockets and the dedicated process owns game rules."""
import json
import os
from pathlib import Path
import select
import subprocess
import sys

import pytest
from websockets.sync.client import connect


@pytest.fixture
def server_url():
    """Run the production entry point on an OS-assigned local port."""
    process = subprocess.Popen(
        [sys.executable, '-m', 'online_server', '--port', '0'],
        cwd=Path(__file__).resolve().parents[1], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
        env={**os.environ, 'PYTHONUNBUFFERED': '1'},
    )
    try:
        readable, _, _ = select.select([process.stdout, process.stderr], [], [], 15)
        assert process.stdout in readable, process.stderr.readline() if readable else 'server startup timed out'
        endpoint = process.stdout.readline().strip()
        assert endpoint.startswith('LISTENING ws://'), endpoint
        yield endpoint.removeprefix('LISTENING ')
    finally:
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)


def receive(socket, kind='state', predicate=lambda message: True):
    for _ in range(100):
        message = json.loads(socket.recv(timeout=5))
        if message['type'] == kind and predicate(message):
            return message
        if message['type'] in ('error', 'reject'):
            raise AssertionError(message)
    raise AssertionError('expected message never arrived')


def handshake(socket, kind='create', game='tribes-v1', **fields):
    socket.send(json.dumps({'type': kind, 'protocol': 1, 'game': game, **fields}))
    return receive(socket, 'welcome')


def command(socket, data, revision=None):
    socket.send(json.dumps({'type': 'command', 'command': data, 'revision': revision}))


def test_tribes_room_enforces_turns_and_publishes_authoritative_state(server_url):
    """Internet peers share a server-owned match and cannot take another faction's turn."""
    with connect(server_url, proxy=None) as host, connect(server_url, proxy=None) as guest:
        welcome = handshake(host, options={'seed': 7, 'size': 11})
        waiting = receive(host)
        assert waiting['player'] == 0 and not waiting['ready']
        joined = handshake(guest, 'join', room=welcome['room'])
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


@pytest.mark.parametrize('fields, fragment', [
    ({'protocol': 2}, 'protocol'),
    ({'game': 'tribes-v999'}, 'version'),
    ({'options': []}, 'options'),
    ({'options': {'size': 100000}}, 'size'),
    ({'options': {'size': True}}, 'size'),
    ({'options': {'seed': {'surprise': 'object'}}}, 'seed'),
    ({'options': {'undeclared': 'field'}}, 'option'),
])
def test_invalid_handshakes_are_rejected_without_breaking_other_rooms(server_url, fields, fragment):
    """Untrusted options cannot allocate oversized worlds or take down the room server."""
    with connect(server_url, proxy=None) as bad:
        bad.send(json.dumps({'type': 'create', 'protocol': 1, 'game': 'tribes-v1', **fields}))
        assert fragment in receive(bad, 'reject')['error'].lower()
    with connect(server_url, proxy=None) as good:
        handshake(good, options={'size': 11})
        assert receive(good)['state']['world']['current'] == 0


def test_private_seats_resume_without_room_code_takeover(server_url):
    """A shared invitation never grants a claimed seat; its private token can replace a stale socket."""
    from websockets.exceptions import ConnectionClosed
    with connect(server_url, proxy=None) as host, connect(server_url, proxy=None) as guest:
        host_seat = handshake(host, options={'size': 11})
        receive(host)
        guest_seat = handshake(guest, 'join', room=host_seat['room'])
        receive(host)
        ready = receive(guest)
        with connect(server_url, proxy=None) as intruder:
            intruder.send(json.dumps({'type': 'join', 'protocol': 1, 'game': 'tribes-v1',
                                     'room': host_seat['room']}))
            assert 'claimed' in receive(intruder, 'reject')['error']
        with connect(server_url, proxy=None) as returned:
            resumed = handshake(returned, 'resume', room=host_seat['room'],
                                resume_token=guest_seat['resume_token'])
            assert resumed['player'] == 1
            state = receive(returned)
            assert state['ready'] and state['state'] == ready['state']
            assert 'reconnected' in receive(guest, 'reject')['error']
            with pytest.raises(ConnectionClosed):
                guest.recv(timeout=5)
        paused = receive(host, predicate=lambda message: not message['ready'])
        command(host, {'action': 'end_turn'})
        assert 'Waiting' in receive(host, 'error')['error']
        with connect(server_url, proxy=None) as returned:
            handshake(returned, 'resume', room=host_seat['room'], resume_token=guest_seat['resume_token'])
            assert receive(returned)['state'] == paused['state']


def test_rooms_are_isolated_and_stale_orders_do_not_mutate_state(server_url):
    """Knowledge of another room code or an obsolete revision cannot redirect an order."""
    with (connect(server_url, proxy=None) as host, connect(server_url, proxy=None) as guest,
          connect(server_url, proxy=None) as other):
        room = handshake(host, options={'size': 11})
        initial = receive(host)
        handshake(other, options={'size': 11, 'seed': 99})
        untouched = receive(other)
        handshake(guest, 'join', room=room['room'])
        receive(host)
        receive(guest)
        command(host, {'action': 'end_turn'}, initial['revision'])
        assert 'changed' in receive(host, 'error')['error']
        command(host, {'action': 'end_turn'})
        assert receive(guest)['state']['world']['current'] == 1
        command(other, {'action': 'end_turn'})
        assert 'Waiting' in receive(other, 'error')['error']
        assert untouched['state']['world']['current'] == 0


def test_warband_runs_on_the_server_clock_and_pauses_for_a_disconnected_player(server_url):
    """Headless RTS advances without a host scene and both factions' units obey validated orders."""
    from warband.model import World
    with connect(server_url, proxy=None) as host, connect(server_url, proxy=None) as guest:
        room = handshake(host, game='warband-v1', options={'width': 40, 'height': 32})
        assert receive(host)['state']['world']['tick'] == 0
        guest_seat = handshake(guest, 'join', game='warband-v1', room=room['room'])
        receive(host)
        ready = receive(guest)
        world = World.from_dict(ready['state']['world'])
        own, enemy = world.player_units(1)[0], world.player_units(0)[0]
        destination = [own.x - 2, own.y]
        command(guest, {'action': 'move', 'args': [[enemy.id], destination]})
        assert 'own' in receive(guest, 'error')['error']
        command(guest, {'action': 'move', 'args': [[own.id], destination]})
        moved = receive(guest, predicate=lambda message: message['state']['world']['tick'] >= 12)
        assert World.from_dict(moved['state']['world']).units[own.id].pos != own.pos
        guest.close()
        paused = receive(host, predicate=lambda message: not message['ready'])
        with pytest.raises(TimeoutError):
            host.recv(timeout=.15)
        with connect(server_url, proxy=None) as returned:
            handshake(returned, 'resume', game='warband-v1', room=room['room'],
                      resume_token=guest_seat['resume_token'])
            resumed = receive(returned)
            assert resumed['ready']
            assert resumed['state']['world']['tick'] >= paused['state']['world']['tick']


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


@pytest.mark.parametrize('message', ['[]', '{', '{"value":1e999}', '{"value":NaN}'])
def test_malformed_json_is_a_connection_rejection(server_url, message):
    """Invalid JSON cannot escape into rules or crash the room event loop."""
    with connect(server_url, proxy=None) as bad:
        bad.send(message)
        assert receive(bad, 'reject')['error']
    with connect(server_url, proxy=None) as good:
        handshake(good)
        assert receive(good)['state']
