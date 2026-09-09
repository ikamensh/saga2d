"""Shardbound co-op orders cross a LAN socket; both seats share one realm."""
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


def test_shardbound_partners_share_campaign_and_tactical_orders():
    """Both seats can develop one realm, enter battle and act on the same army."""
    from eador.multiplayer import ShardboundMatch
    from eador.model import State
    match = ShardboundMatch(seed=7)
    host = MatchHost('shardbound-v1', match.apply, match.snapshot, address=('127.0.0.1', 0), token='test')
    client = MatchClient('shardbound-v1', host.address, token='test')
    def order(action, *args, target='state', **kwargs):
        return {'action': action, 'target': target, 'args': list(args), 'kwargs': kwargs}
    try:
        converge(host, client, lambda: client.ready)
        client.submit(order('build', 'barracks'))
        converge(host, client, lambda: 'barracks' in State.from_json(client.state['campaign']).buildings)
        host.submit(order('explore'))
        converge(host, client, lambda: State.from_json(client.state['campaign']).battle is not None)
        unit_id = next(u.id for u in match.state.battle.units if u.team == 'player')
        client.submit(order('guard', unit_id, target='battle'))
        converge(host, client, lambda: match.state.battle.unit(unit_id).acted)
        before = match.state.to_json()
        enemy_id = next(u.id for u in match.state.battle.units if u.team == 'enemy')
        with pytest.raises(CommandError):
            match.apply(1, order('guard', enemy_id, target='battle'))
        assert match.state.to_json() == before
        host.submit(order('end_turn', target='battle'))
        converge(host, client, lambda: client.state['campaign'] == match.state.to_json())
    finally:
        client.close()
        host.close()


def test_shardbound_offline_save_controls_preserve_the_live_match(tmp_path):
    """The battle's save browser cannot replace co-op with a local campaign."""
    from eador.diagnostics import DiagnosticScene
    from eador.app import create_game
    from eador.model import State
    from eador.multiplayer import ShardboundMatch, NetworkShardScene
    from eador.persistence import CampaignSaves
    from eador.scene import BattleScene, SaveScene, HelpScene, TitleScene
    match = ShardboundMatch()
    host = MatchHost('co-op', match.apply, match.snapshot, address=('127.0.0.1', 0), token='test')
    client = MatchClient('co-op', host.address, token='test')
    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        saves = CampaignSaves(game.save_manager)
        saves.save(State.new(99), 1)
        converge(host, client, lambda: client.ready)
        host.submit({'target': 'state', 'action': 'explore', 'args': []})
        converge(host, client, lambda: client.revision == host.revision)
        root = NetworkShardScene(client)
        game.push(root)
        game.tick(.03)
        assert isinstance(game.scene, BattleScene)
        assert not game.scene.load_game()
        assert game.scene.root is root
        for mode in ('load', 'save'):
            game.push(SaveScene(root, mode=mode))
            assert isinstance(game.scene, DiagnosticScene)
            assert 'live' in game.scene.message.lower()
            assert saves.load(1).seed == 99
            assert client.ready
            game.backend.inject_key('escape')
            game.tick(.03)
            assert isinstance(game.scene, BattleScene)
            assert game.scene.root is root
        help_scene = HelpScene(root)
        game.push(help_scene)
        help_scene.title()
        assert isinstance(game.scene, TitleScene)
        assert client.closed
    finally:
        game.close()
        client.close()
        host.close()


def test_shardbound_guest_can_depart_to_the_next_campaign_shard(tmp_path):
    """A completed shard's retinue flow sends one atomic transition to the host."""
    from eador.app import create_game
    from eador.campaign_scene import CampaignScene
    from eador.multiplayer import ShardboundMatch, NetworkShardScene
    from tools.eador_linked_campaign import play_stage
    match = ShardboundMatch(campaign=True)
    match.state = play_stage(match.state)
    assert match.state.campaign.phase == 'departure'
    host = MatchHost('co-op', match.apply, match.snapshot, address=('127.0.0.1', 0), token='test')
    client = MatchClient('co-op', host.address, token='test')
    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        converge(host, client, lambda: client.ready)
        game.push(NetworkShardScene(client))
        game.tick(.03)
        assert isinstance(game.scene, CampaignScene)
        game.scene.choose_offer(match.state.campaign.offers[0].id)
        game.scene.depart()
        assert match.state.campaign.stage == 1
        converge(host, client, lambda: match.state.campaign.stage == 2)
        converge(host, client, lambda: client.revision == host.revision)
        game.tick(.03)
        assert isinstance(game.scene, NetworkShardScene)
        assert game.scene.state.to_json() == match.state.to_json()
        assert client.ready
    finally:
        game.close()
        client.close()
        host.close()



def test_guest_controls_reach_host_and_accepted_state_returns_to_the_scene(tmp_path):
    """The real shard scene submits orders without mutating the guest state ahead of the host."""
    from eador.app import create_game
    from eador.multiplayer import ShardboundMatch, NetworkShardScene
    from eador.scene import BattleScene
    match = ShardboundMatch(7)
    host = MatchHost('eador', match.apply, match.snapshot, address=('127.0.0.1', 0), token='test')
    client = MatchClient('eador', host.address, token='test')
    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        converge(host, client, lambda: client.ready)
        scene = NetworkShardScene(client)
        game.push(scene)
        game.tick(1/30)
        game.backend.inject_key('x')
        game.tick(1/30)
        assert match.state.battle is None
        converge(host, client, lambda: match.state.battle is not None)
        converge(host, client, lambda: client.revision == host.revision)
        game.tick(1/30)
        assert isinstance(game.scene, BattleScene)
        game.backend.inject_key('g')
        game.tick(1/30)
        converge(host, client, lambda: match.state.battle.unit(0).acted)
        converge(host, client, lambda: client.revision == host.revision)
        game.tick(1/30)
        assert isinstance(game.scene, BattleScene)
        assert game.scene.battle.unit(0).acted
    finally:
        game.close()
        client.close()
        host.close()


def test_title_opens_a_usable_host_join_form(tmp_path):
    """Co-op is reachable from the title and address entry uses ordinary input."""
    from eador.app import create_game
    from eador.scene import TitleScene
    game = create_game(backend='mock', save_dir=tmp_path)
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
