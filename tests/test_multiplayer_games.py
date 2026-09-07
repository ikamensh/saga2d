"""Game commands cross actual sockets; rules and ownership stay game-specific."""
import time
import pytest
from saga2d import MatchClient, MatchHost, CommandError


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


def test_warband_guest_orders_and_host_simulation_stay_in_sync():
    """Guest units move on the authoritative clock; forged ownership is rejected atomically."""
    from warband.multiplayer import WarbandMatch
    from warband.model import World
    match = WarbandMatch(seed=3)
    host = MatchHost('warband-v1', match.apply, match.snapshot, address=('127.0.0.1', 0), token='test')
    client = MatchClient('warband-v1', host.address, token='test')
    try:
        converge(host, client, lambda: client.ready)
        guest = match.world.player_units(1)[0]
        original = guest.pos
        ours = match.world.player_units(0)[0]
        with pytest.raises(CommandError):
            match.apply(1, {'action': 'move', 'args': [[guest.id, ours.id], [15., 15.]], 'kwargs': {}})
        assert not guest.orders
        client.submit({'action': 'move', 'args': [[guest.id], [original[0]-2, original[1]]], 'kwargs': {}})
        converge(host, client, lambda: bool(match.world.units[guest.id].orders))
        for _ in range(40):
            match.step()
        host.publish()
        converge(host, client, lambda: client.state['world']['tick'] == match.world.tick)
        assert match.world.units[guest.id].pos != original
        restored = World.from_dict(client.state['world'])
        assert all(p.human for p in restored.players)
        assert restored.to_dict() == match.world.to_dict()
    finally:
        client.close()
        host.close()


@pytest.mark.parametrize('audio_schema', ['current', 'basic', 'partial'])
def test_warband_fatal_impact_keeps_its_material_across_the_socket(tmp_path, audio_schema):
    """Guests hear fatal impacts, with explicit basic audio only for the old schema."""
    from saga2d import Game
    from warband.model import World
    from warband.multiplayer import WarbandMatch, NetworkGameScene
    from warband.rules import BuildingType, Terrain, UnitType
    from warband.style import build_theme

    match = WarbandMatch(3)
    match.world = World(32, 24, [[Terrain.GRASS] * 32 for _ in range(24)], 2)
    for player in match.world.players:
        player.human = True
    match.world.place_building(0, BuildingType.TOWN_HALL, (3, 3))
    match.world.place_building(1, BuildingType.TOWN_HALL, (25, 18))
    attacker = match.world.spawn_unit(1, UnitType.FOOTMAN, (10.5, 10.5))
    victim = match.world.place_building(0, BuildingType.TOWER, (11, 10), done=False)
    victim.hp = 1
    armor = match.world.armor_of(victim)
    match.world.update_vision()
    impact_fields = ('source_type', 'target_type', 'target_armor', 'target_complete')
    omitted_fields = {'current': (), 'basic': impact_fields, 'partial': ('target_type',)}[audio_schema]

    def snapshot(player):
        state = match.snapshot(player)
        for _, event in state['events']:
            for field in omitted_fields:
                del event[field]
        return state

    host = MatchHost('warband-v1', match.apply, snapshot, address=('127.0.0.1', 0), token='test')
    client = MatchClient('warband-v1', host.address, token='test')
    game = Game('network battle audio', backend='mock', theme=build_theme(), save_dir=tmp_path)
    try:
        converge(host, client, lambda: client.ready)
        scene = NetworkGameScene(client, settings={'tutorial': False})
        game.push(scene)
        scene.camera.center_on(11.5 * 32, 10.5 * 32)
        game.tick(1 / 30)
        scene.order('attack', [attacker.id], victim.id)
        converge(host, client, lambda: bool(match.world.units[attacker.id].orders))
        for _ in range(4):
            match.step()
            if match.world.entity(victim.id) is None:
                break
        assert match.world.entity(victim.id) is None
        host.publish()
        converge(host, client, lambda: client.revision == host.revision)
        hit = next(event for _, event in client.state['events']
                   if event['kind'] == 'hit' and event['other'] == victim.id)
        if audio_schema == 'current':
            assert {key: hit[key] for key in impact_fields} == {
                'source_type': 'footman', 'target_type': 'tower', 'target_armor': armor, 'target_complete': False,
            }
            assert armor > 0
        elif audio_schema == 'basic':
            assert not set(impact_fields).intersection(hit)
        else:
            with pytest.raises(ValueError, match='incomplete battle audio metadata'):
                game.tick(1 / 30)
            assert 'impact' not in scene.recent_sounds
            return
        game.tick(1 / 30)
        assert scene.world.entity(victim.id) is None
        assert ('sword_wood' if audio_schema == 'current' else 'impact') in scene.recent_sounds
        assert 'sword_stone' not in scene.recent_sounds
        if audio_schema == 'basic':
            assert scene.status == 'Server uses basic battle audio; update the server for weapon and material sounds.'
            # Later impacts must leave newer player feedback visible.
            next_victim = match.world.place_building(0, BuildingType.TOWER, (11, 10), done=False)
            next_victim.hp = 1
            scene.say('Holding the line.')
            scene.order('attack', [attacker.id], next_victim.id)
            converge(host, client, lambda: bool(match.world.units[attacker.id].orders)
                     and match.world.units[attacker.id].orders[0].target == next_victim.id)
            for _ in range(30):
                match.step()
                if match.world.entity(next_victim.id) is None:
                    break
            assert match.world.entity(next_victim.id) is None
            host.publish()
            converge(host, client, lambda: client.revision == host.revision)
            game.tick(1 / 30)
            assert scene.world.entity(next_victim.id) is None
            assert scene.status == 'Holding the line.'
    finally:
        game.close()
        client.close()
        host.close()


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


@pytest.mark.parametrize('name', ['tribes', 'warband', 'eador'])
def test_guest_controls_reach_host_and_accepted_state_returns_to_the_scene(name, tmp_path):
    """Real game scenes submit orders without mutating the guest world ahead of the host."""
    from saga2d import Game
    if name == 'tribes':
        from tribes.multiplayer import TribesMatch, NetworkMapScene
        from tribes.style import build_theme
        match, scene_type = TribesMatch(7), NetworkMapScene
    elif name == 'warband':
        from warband.multiplayer import WarbandMatch, NetworkGameScene
        from warband.style import build_theme
        match, scene_type = WarbandMatch(3), NetworkGameScene
    else:
        from eador.multiplayer import ShardboundMatch, NetworkShardScene
        from eador.style import build_theme
        match, scene_type = ShardboundMatch(7), NetworkShardScene
    host = MatchHost(name, match.apply, match.snapshot, address=('127.0.0.1', 0), token='test')
    client = MatchClient(name, host.address, token='test')
    game = None
    try:
        converge(host, client, lambda: client.ready)
        if name == 'eador':
            from eador.app import create_game
            game = create_game(backend='mock', save_dir=tmp_path)
        else:
            game = Game('network test', backend='mock', theme=build_theme(), save_dir=tmp_path)
        scene = scene_type(client)
        game.push(scene)
        game.tick(1/30)
        if name == 'tribes':
            host.submit({'action': 'end_turn'})
            converge(host, client, lambda: client.state['world']['current'] == 1)
            game.tick(1/30)
            game.backend.inject_key('tab')
            game.tick(1/30)
            unit_id = scene.selected.id
            game.backend.inject_key('h')
            game.tick(1/30)
            assert not match.world.units[unit_id].done
            wanted = lambda: match.world.units[unit_id].done
        elif name == 'warband':
            unit = scene.world.player_units(1)[0]
            scene.select([unit.id])
            scene.command_move((unit.x-2, unit.y))
            assert not match.world.units[unit.id].orders
            wanted = lambda: bool(match.world.units[unit.id].orders)
        else:
            from eador.scene import BattleScene
            game.backend.inject_key('x')
            game.tick(1/30)
            assert match.state.battle is None
            wanted = lambda: match.state.battle is not None
        converge(host, client, wanted)
        converge(host, client, lambda: client.revision == host.revision)
        game.tick(1/30)
        if name == 'tribes':
            assert scene.world.units[unit_id].done
        elif name == 'warband':
            assert scene.world.units[unit.id].orders
        else:
            assert isinstance(game.scene, BattleScene)
            game.backend.inject_key('g')
            game.tick(1/30)
            converge(host, client, lambda: match.state.battle.unit(0).acted)
            converge(host, client, lambda: client.revision == host.revision)
            game.tick(1/30)
            assert isinstance(game.scene, BattleScene)
            assert game.scene.battle.unit(0).acted
    finally:
        if game:
            game.close()
        client.close()
        host.close()


@pytest.mark.parametrize('name', ['tribes', 'warband', 'eador'])
def test_title_opens_a_usable_host_join_form(name, tmp_path):
    """Multiplayer is reachable from every title and address entry uses ordinary input."""
    from saga2d import Game, MatchMenu
    if name == 'eador':
        from eador.app import create_game
        from eador.scene import TitleScene
        game = create_game(backend='mock', save_dir=tmp_path)
    else:
        from importlib import import_module
        title = import_module(name + '.title')
        style = import_module(name + '.style')
        TitleScene = title.TitleScene
        game = Game('title', backend='mock', theme=style.build_theme(), save_dir=tmp_path)
    try:
        game.push(TitleScene())
        game.backend.inject_key('m')
        game.tick(1/30)
        assert isinstance(game.scene, MatchMenu)
        assert game.scene.mode == 'online'
        lan = next(button for button in game.scene.ui.walk()
                   if getattr(button, 'text', None) == 'LAN')
        x, y, w, h = lan.bounds
        game.backend.inject_click(x + w / 2, y + h / 2)
        game.tick(1/30)
        assert game.scene.mode == 'lan'
        for key in ['1','9','2','period','1','6','8','period','1','period','9']:
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


def test_warband_invalid_cancel_index_is_rejected_without_changing_the_queue():
    """Malformed remote orders are ordinary rejections and cannot crash the host loop."""
    from warband.multiplayer import WarbandMatch
    from warband.rules import UnitType, BuildingType
    match = WarbandMatch()
    hall = match.world.player_buildings(1, BuildingType.TOWN_HALL)[0]
    match.world.train(hall.id, UnitType.PEASANT)
    before = match.world.to_dict()
    with pytest.raises(CommandError):
        match.apply(1, {'action': 'cancel_train', 'args': [], 'kwargs': {'building_id': hall.id, 'index': 999}})
    assert match.world.to_dict() == before


def test_warband_selection_facts_are_drawn_above_their_background(tmp_path):
    """Native review found the inherited HUD panel covering its immediate text."""
    from saga2d import Game
    from warband.scene import new_game
    from warband.style import build_theme
    game = Game('selection', backend='mock', theme=build_theme(), save_dir=tmp_path)
    try:
        scene = new_game(3)
        game.push(scene)
        scene.select([scene.world.player_units(scene.human)[0].id])
        game.tick(.03)
        game.tick(.03)
        text = next(t for t in game.backend.texts if t['text'] == 'Peasant')
        covers = [r for r in game.backend.polygons if r['space'] == 'screen' and r['color'][3] > 128
                  and min(x for x,y in r['points']) <= text['x'] < max(x for x,y in r['points'])
                  and min(y for x,y in r['points']) <= text['y'] < max(y for x,y in r['points'])]
        assert covers
        assert all(r['order'] <= text['order'] for r in covers)
    finally:
        game.close()


def test_shardbound_offline_save_controls_preserve_the_live_match(tmp_path):
    """The battle's save browser cannot replace co-op with a local campaign."""
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
        browser = SaveScene(root, mode='load')
        game.push(browser)
        browser.activate(0)
        assert game.scene is browser
        browser.toggle()
        browser.activate(0)
        assert saves.load(1).seed == 99
        assert client.ready
        game.pop()
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


def test_warband_host_clock_runs_under_its_menu_and_pauses_on_disconnect(tmp_path):
    """The actual host scene owns time independently of the local pause overlay."""
    from saga2d import Game
    from warband.multiplayer import WarbandMatch, NetworkGameScene
    from warband.style import build_theme
    match = WarbandMatch()
    host = MatchHost('warband', match.apply, match.snapshot, address=('127.0.0.1', 0), token='test')
    client = MatchClient('warband', host.address, token='test')
    game = Game('host clock', backend='mock', theme=build_theme(), save_dir=tmp_path)
    try:
        converge(host, client, lambda: client.ready)
        scene = NetworkGameScene(host, match)
        game.push(scene)
        game.backend.inject_key('f10')
        game.tick(.03)
        assert game.scene is not scene
        before = match.world.tick
        deadline = time.monotonic() + 3
        while match.world.tick < before + 4 and time.monotonic() < deadline:
            time.sleep(.01)
            game.tick(.03)
            client.poll()
        assert match.world.tick >= before + 4
        assert scene.world.tick >= before + 2
        client.close()
        game.tick(.03)
        assert not host.ready
        stopped = match.world.tick
        time.sleep(.12)
        game.tick(.03)
        assert match.world.tick == stopped
    finally:
        game.close()
        client.close()
        host.close()
