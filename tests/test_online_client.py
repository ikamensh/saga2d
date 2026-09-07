"""The scene-facing client works against the real dedicated server process."""
import time

import pytest

from saga2d.online import OnlineClient
from tests.test_online_server import server_url


def pump(*clients, until):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        for client in clients:
            client.poll()
        if until():
            return
        time.sleep(.01)
    raise AssertionError([(client.ready, client.closed, client.error) for client in clients])


def test_both_players_use_remote_authority_and_can_resume_private_seats(server_url):
    """Creation needs no local listener; closing the creator preserves the live room."""
    creator = OnlineClient('tribes-v1', endpoint=server_url, options={'seed': 7, 'size': 11})
    guest = resumed = None
    try:
        pump(creator, until=lambda: bool(creator.room))
        assert not creator.ready and creator.resume_token
        guest = OnlineClient('tribes-v1', endpoint=server_url, room=creator.room)
        pump(creator, guest, until=lambda: creator.ready and guest.ready)
        assert creator.player == 0 and guest.player == 1
        assert creator.state == guest.state
        creator.submit({'action': 'end_turn'}, revision=creator.revision)
        pump(creator, guest, until=lambda: guest.state['world']['current'] == 1)
        room, token = creator.room, creator.resume_token
        creator.close()
        pump(guest, until=lambda: not guest.ready)
        resumed = OnlineClient('tribes-v1', endpoint=server_url, room=room, resume_token=token)
        pump(resumed, guest, until=lambda: resumed.ready and guest.ready)
        assert resumed.player == 0
        assert resumed.state == guest.state
        assert resumed.state['world']['current'] == 1
    finally:
        for client in (creator, guest, resumed):
            if client is not None:
                client.close()


def test_wrong_room_reports_actionable_failure_without_blocking_frames(server_url):
    """A rejected join becomes a visible closed session rather than a waiting lobby."""
    client = OnlineClient('tribes-v1', endpoint=server_url, room='missing')
    try:
        pump(client, until=lambda: client.closed)
        assert not client.ready
        assert 'Room not found' in client.error
    finally:
        client.close()


def test_public_endpoint_requires_tls():
    """Room codes and private seats may cross plaintext only for local development."""
    with pytest.raises(ValueError, match='TLS'):
        OnlineClient('tribes-v1', endpoint='ws://example.com/play')
