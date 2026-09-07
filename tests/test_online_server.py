"""Online players cross real WebSockets and the dedicated process owns game rules."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time

import pytest
from websockets.sync.client import connect


@contextmanager
def running_server(*arguments):
    """Run the production entry point on an OS-assigned local port."""
    process = subprocess.Popen(
        [sys.executable, '-m', 'online_server', '--port', '0', *map(str, arguments)],
        cwd=Path(__file__).resolve().parents[1], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
        env={**os.environ, 'PYTHONUNBUFFERED': '1'},
    )
    try:
        readable, _, _ = select.select([process.stdout, process.stderr], [], [], 15)
        assert process.stdout in readable, process.stderr.readline() if readable else 'server startup timed out'
        endpoint = process.stdout.readline().strip()
        assert endpoint.startswith('LISTENING ws://'), endpoint
        yield endpoint.removeprefix('LISTENING '), process
    finally:
        process.terminate()
        try:
            _, errors = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            _, errors = process.communicate(timeout=5)
        assert 'Traceback (most recent call last)' not in errors, errors


@pytest.fixture
def server_url():
    """The same production process used by the framework client's socket tests."""
    with running_server() as (url, process):
        yield url


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


@pytest.mark.parametrize('game', ['tribes-v1', 'warband-v1', 'shardbound-v1'])
def test_rooms_and_private_seats_survive_server_restart(tmp_path, game):
    """Trusted checkpoints restore private seats and a partly played battle after process loss."""
    with running_server('--state-dir', tmp_path) as (url, process):
        with connect(url, proxy=None) as host, connect(url, proxy=None) as guest:
            seat0 = handshake(host, game=game)
            receive(host)
            seat1 = handshake(guest, 'join', game=game, room=seat0['room'])
            receive(host)
            before = receive(guest)
            if game == 'tribes-v1':
                command(host, {'action': 'end_turn'})
                before = receive(guest)
            elif game == 'shardbound-v1':
                from eador.model import State
                command(host, {'action': 'build', 'target': 'state', 'args': ['barracks']})
                receive(guest)
                command(guest, {'action': 'explore', 'target': 'state', 'args': []})
                receive(guest)
                command(host, {'action': 'guard', 'target': 'battle', 'args': [0]})
                before = receive(guest)
                assert State.from_json(before['state']['campaign']).battle.unit(0).acted
            else:
                before = receive(guest, predicate=lambda state: state['state']['world']['tick'] >= 4)
            if game != 'warband-v1':
                # Acknowledged turn orders survive even an abrupt power/process loss.
                process.kill()
                process.wait(timeout=5)
    assert (tmp_path / 'rooms.sqlite3').stat().st_mode & 0o777 == 0o600
    with running_server('--state-dir', tmp_path) as (url, process):
        with connect(url, proxy=None) as host, connect(url, proxy=None) as guest:
            returned = handshake(host, 'resume', game=game, room=seat0['room'],
                                 resume_token=seat0['resume_token'])
            assert returned['player'] == 0
            waiting = receive(host)
            assert not waiting['ready']
            handshake(guest, 'resume', game=game, room=seat0['room'], resume_token=seat1['resume_token'])
            resumed = receive(guest)
            assert resumed['ready']
            if game == 'warband-v1':
                assert resumed['state']['world']['tick'] >= before['state']['world']['tick']
                assert resumed['state']['world']['tick'] >= 4
            else:
                assert resumed['state'] == before['state']
                assert resumed['revision'] > before['revision']
                if game == 'shardbound-v1':
                    expected = State.from_json(before['state']['campaign'])
                    troop = next(unit for unit in expected.battle.units
                                 if unit.team == 'player' and not unit.acted)
                    expected.battle.guard(troop.id)
                    command(guest, {'action': 'guard', 'target': 'battle', 'args': [troop.id]})
                    assert receive(guest)['state']['campaign'] == expected.to_json()


def test_expired_rooms_do_not_return_after_server_restart(tmp_path):
    """Wall time, rather than process uptime, bounds how long a disconnected seat stays resumable."""
    with running_server('--state-dir', tmp_path, '--room-ttl', '.15') as (url, process):
        with connect(url, proxy=None) as host:
            seat = handshake(host)
            receive(host)
    time.sleep(.2)
    with running_server('--state-dir', tmp_path, '--room-ttl', '.15') as (url, process):
        with connect(url, proxy=None) as returned:
            returned.send(json.dumps({'type': 'resume', 'protocol': 1, 'game': 'tribes-v1',
                                      'room': seat['room'], 'resume_token': seat['resume_token']}))
            assert 'not found' in receive(returned, 'reject')['error']


def test_room_capacity_is_explicit_and_health_remains_available():
    """A full server rejects new rooms while its health endpoint and existing rooms stay usable."""
    from urllib.request import urlopen
    with running_server('--max-rooms', '1') as (url, process):
        with connect(url + '/play', proxy=None) as host:
            handshake(host)
            receive(host)
            with connect(url, proxy=None) as extra:
                extra.send(json.dumps({'type': 'create', 'protocol': 1, 'game': 'tribes-v1'}))
                assert 'full' in receive(extra, 'reject')['error']
            with urlopen(url.replace('ws://', 'http://') + '/healthz', timeout=3) as health:
                assert health.status == 200 and health.read() == b'ok\n'


@pytest.mark.parametrize('trusted', [False, True])
def test_only_configured_loopback_proxy_can_supply_client_ip(trusted):
    """An internet client cannot bypass room quotas by forging a forwarding header."""
    arguments = ['--trusted-proxy'] if trusted else []
    with running_server(*arguments) as (url, process):
        for index in range(5):
            with connect(url, proxy=None, additional_headers={'X-Forwarded-For': f'192.0.2.{index + 1}'}) as host:
                host.send(json.dumps({'type': 'create', 'protocol': 1, 'game': 'tribes-v1',
                                      'options': {'size': 11}}))
                if index == 4 and not trusted:
                    assert 'Too many' in receive(host, 'reject')['error']
                else:
                    receive(host, 'welcome')
                    assert receive(host)['state']
