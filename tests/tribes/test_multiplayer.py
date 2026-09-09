"""Tribes orders cross a LAN socket; rules and ownership stay in the game."""
import time

import pytest

from saga2d import CommandError, Game, MatchClient, MatchHost, MatchMenu


def converge(host, client, until):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        host.poll()
        client.poll()
        if until():
            return
        time.sleep(.001)
    raise AssertionError('match did not converge')


def test_tribes_guest_takes_its_turn_and_cannot_order_the_host_army():
    """Both human seats survive serialization and only the active faction can act."""
    from tribes.multiplayer import TribesMatch
    from tribes.model import World
    match = TribesMatch(seed=7)
    host = MatchHost('tribes-v1', match.apply, match.snapshot, address=('127.0.0.1', 0), token='test')
    client = MatchClient('tribes-v1', host.address, token='test')
    try:
        converge(host, client, lambda: client.ready)
        assert all(t.human for t in World.from_dict(client.state['world']).tribes)
        client.submit({'action': 'end_turn'})
        converge(host, client, lambda: bool(client.error))
        assert match.world.current == 0
        host.submit({'action': 'end_turn'})
        converge(host, client, lambda: client.state['world']['current'] == 1)
        ours = match.world.tribe_units(0)[0]
        with pytest.raises(CommandError):
            match.apply(1, {'action': 'hold', 'unit': ours.id})
        guest = match.world.tribe_units(1)[0]
        client.submit({'action': 'hold', 'unit': guest.id})
        converge(host, client, lambda: match.world.units[guest.id].done)
        client.submit({'action': 'end_turn'})
        converge(host, client, lambda: client.state['world']['current'] == 0)
        assert World.from_dict(client.state['world']).to_dict() == match.world.to_dict()
    finally:
        client.close()
        host.close()


def test_tribes_online_results_do_not_enter_the_offline_high_score_board(tmp_path):
    """Two-human finishes show their scores without ranking against solo AI matches."""
    from saga2d import Game
    from tribes.multiplayer import TribesMatch, NetworkMapScene
    from tribes.scene import GameOverScene
    from tribes.scores import HighScores
    from tribes.style import build_theme
    match = TribesMatch()
    while match.world.winner is None:
        match.apply(match.world.current, {'action': 'end_turn'})
    host = MatchHost('tribes', match.apply, match.snapshot, address=('127.0.0.1', 0), token='test')
    client = MatchClient('tribes', host.address, token='test')
    game = Game('online result', backend='mock', theme=build_theme(), save_dir=tmp_path)
    try:
        converge(host, client, lambda: client.ready)
        game.push(NetworkMapScene(client))
        game.tick(.03)
        assert isinstance(game.scene, GameOverScene)
        assert game.scene.map_scene.human == 1
        assert HighScores(game.data_dir).load() == []
        assert any(t['text'] == 'Multiplayer match · 2 human tribes' for t in game.backend.texts)
        game.scene.back_to_title()
        assert client.closed
    finally:
        game.close()
        client.close()
        host.close()



def test_guest_controls_reach_host_and_accepted_state_returns_to_the_scene(tmp_path):
    """The real map scene submits orders without mutating the guest world ahead of the host."""
    from tribes.multiplayer import TribesMatch, NetworkMapScene
    from tribes.style import build_theme
    match = TribesMatch(7)
    host = MatchHost('tribes', match.apply, match.snapshot, address=('127.0.0.1', 0), token='test')
    client = MatchClient('tribes', host.address, token='test')
    game = Game('network test', backend='mock', theme=build_theme(), save_dir=tmp_path)
    try:
        converge(host, client, lambda: client.ready)
        scene = NetworkMapScene(client)
        game.push(scene)
        game.tick(1/30)
        host.submit({'action': 'end_turn'})
        converge(host, client, lambda: client.state['world']['current'] == 1)
        game.tick(1/30)
        game.backend.inject_key('tab')
        game.tick(1/30)
        unit_id = scene.selected.id
        game.backend.inject_key('h')
        game.tick(1/30)
        assert not match.world.units[unit_id].done
        converge(host, client, lambda: match.world.units[unit_id].done)
        converge(host, client, lambda: client.revision == host.revision)
        game.tick(1/30)
        assert scene.world.units[unit_id].done
    finally:
        game.close()
        client.close()
        host.close()


def test_title_opens_a_usable_host_join_form(tmp_path):
    """Multiplayer is reachable from the title and address entry uses ordinary input."""
    from tribes.style import build_theme
    from tribes.title import TitleScene
    game = Game('title', backend='mock', theme=build_theme(), save_dir=tmp_path)
    try:
        game.push(TitleScene())
        game.backend.inject_key('m')
        game.tick(1/30)
        assert isinstance(game.scene, MatchMenu)
        assert game.scene.mode == 'online'
        lan = next(button for button in game.scene.ui.walk() if getattr(button, 'text', None) == 'LAN')
        x, y, w, h = lan.bounds
        game.backend.inject_click(x + w / 2, y + h / 2)
        game.tick(1/30)
        assert game.scene.mode == 'lan'
        for key in ['1', '9', '2', 'period', '1', '6', '8', 'period', '1', 'period', '9']:
            game.backend.inject_key(key)
            game.tick(1/30)
        assert game.scene.fields[0] == '192.168.1.9'
        game.backend.inject_key('tab')
        game.tick(1/30)
        game.backend.inject_key('8')
        game.tick(1/30)
        assert game.scene.fields[1] == '8'
    finally:
        game.close()
