"""Public multiplayer entry points use room codes online and retain explicit LAN."""
import time

from saga2d import Game, MatchMenu, Scene
from tests.test_online_server import server_url


def test_online_menu_needs_only_a_room_code_and_reports_missing_input(tmp_path):
    """The default join path asks friends for a code without requiring an IP address."""
    game = Game('online menu', backend='mock', resolution=(1280, 800), save_dir=tmp_path)
    try:
        game.push(MatchMenu('Test multiplayer', 'tribes-v1', None, None))
        game.tick(.03)
        text = '\n'.join(item['text'] for item in game.backend.texts)
        assert 'Online' in text
        assert 'Host address' not in text
        assert 'Room code' in text
        game.backend.inject_key('return')
        game.tick(.03)
        assert 'Enter a room code' in game.scene.message
        for key in ('a', 'b', 'c', '1', '2', '3'):
            game.backend.inject_key(key)
            game.tick(.03)
        text = '\n'.join(item['text'] for item in game.backend.texts)
        assert 'ABC123' in text
    finally:
        game.close()


def test_online_creator_waits_for_partner_and_can_rejoin_after_app_restart(server_url, tmp_path, monkeypatch):
    """Creating a room never starts local authority; a private saved seat survives restart."""
    from saga2d.multiplayer_ui import MatchLobby
    from saga2d.online import OnlineClient

    class RemoteScene(Scene):
        def __init__(self, session, match):
            assert match is None, 'Online creators must use the remote authority'
            self.session = session

        def update(self, dt):
            self.session.poll()

        def on_close(self):
            self.session.close()

    def local_match():
        raise AssertionError('Online room creation must not construct a local match')

    def new_menu():
        return MatchMenu('Tribes online', 'tribes-v1', local_match, RemoteScene,
                         create_options=lambda: {'seed': 41, 'size': 11})

    def click_text(text):
        button = next(b for b in game.scene.ui.walk() if str(getattr(b, 'text', '')).startswith(text))
        x, y, w, h = button.bounds
        game.backend.inject_click(x + w / 2, y + h / 2)
        game.tick(.03)

    def wait(until):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            game.tick(.03)
            if guest is not None:
                guest.poll()
            if until():
                return
            time.sleep(.01)
        raise AssertionError('Online menu did not reach the expected state')

    monkeypatch.setenv('SAGA2D_SERVER_URL', server_url)
    game = Game('online menu', backend='mock', resolution=(1280, 800), save_dir=tmp_path)
    guest = None
    try:
        game.push(new_menu())
        game.tick(.03)
        click_text('Create room')
        assert isinstance(game.scene, MatchLobby)
        wait(lambda: bool(game.scene.session.resume_token))
        lobby = game.scene
        room = lobby.session.room
        assert not lobby.session.ready
        assert any(f'Room code: {room}' in t['text'] for t in game.backend.texts)
        click_text('Cancel')
        assert isinstance(game.scene, MatchMenu)
        assert any('Rejoin last room' in t['text'] for t in game.backend.texts)
        click_text('Rejoin last room')
        wait(lambda: game.scene.session.state is not None)
        guest = OnlineClient('tribes-v1', endpoint=server_url, room=room)
        wait(lambda: isinstance(game.scene, RemoteScene) and guest.ready)
        assert game.scene.session.player == 0
        assert game.scene.session.state['seed'] == 41
        game.scene.session.submit({'action': 'end_turn'}, revision=game.scene.session.revision)
        wait(lambda: guest.state['world']['current'] == 1)
        game.close()
        game = Game('online menu', backend='mock', resolution=(1280, 800), save_dir=tmp_path)
        game.push(new_menu())
        game.tick(.03)
        wait(lambda: not guest.ready)
        click_text('Rejoin last room')
        wait(lambda: isinstance(game.scene, RemoteScene) and guest.ready)
        assert game.scene.session.player == 0
        assert game.scene.session.room == room
        assert game.scene.session.state['world']['current'] == 1
    finally:
        game.close()
        if guest is not None:
            guest.close()
