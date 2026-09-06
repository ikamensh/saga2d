"""Ordered enemy feedback is a read-only view of already-saved authoritative rules."""
from eador.app import create_game
from eador.model import State
from eador.scene import BattleScene, ShardScene
from tools.eador_ui import PlayerInput
from tests.eador.test_battle_trace import relief_before_rally


def test_enemy_playback_is_read_only_and_visible_finish_restores_ordinary_controls(tmp_path):
    """Repeated battle keys cannot execute extra turns while an enemy chain is being shown."""
    from eador.battle_playback_scene import BattlePlaybackScene
    state = relief_before_rally()
    expected = State.from_json(state.to_json()); expected.battle.end_turn()
    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        game.push(ShardScene(state)); game.tick(1/60)
        player = PlayerInput(game, finish_actions=False); player.press('e')
        assert isinstance(game.scene, BattlePlaybackScene)
        assert game.scene.battle.log == [], 'The first visual frame must not reveal later attacks'
        assert any(item['text'] == 'Space' for item in game.backend.texts), 'Finish must show its real key'
        resolved = expected.to_json()
        assert player.state.to_json() == resolved
        for key in ('e', 'a', 'g', 't', '1', '2'):
            player.press(key)
        player.click(*game.scene.grid.center((0, 0)))
        assert player.state.to_json() == resolved
        for key in ('space', 'a', 't'):
            game.backend.inject_key(key)
        game.tick(1/60)
        assert type(game.scene) is BattleScene and player.state.to_json() == resolved
    finally:
        game._teardown()


def test_playback_transition_discards_queued_orders_and_loading_uses_the_resolved_save(tmp_path):
    """The existing scene boundary owns input safety; no intermediate visual state is persisted."""
    from eador.battle_playback_scene import BattlePlaybackScene
    state = relief_before_rally()
    expected = State.from_json(state.to_json()); expected.battle.end_turn()
    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        game.push(ShardScene(state)); game.tick(1/60)
        for key in ('e', 'e', 't'):
            game.backend.inject_key(key)
        game.tick(1/60)
        assert isinstance(game.scene, BattlePlaybackScene)
        assert state.to_json() == expected.to_json()
        player = PlayerInput(game, finish_actions=False)
        player.reload(expected.to_json())
        assert type(game.scene) is BattleScene
        assert player.state.to_json() == expected.to_json()
    finally:
        game._teardown()


def test_settings_and_history_pause_playback_without_changing_the_resolved_save(tmp_path):
    """Covered playback has no independent timer, and read-only overlays cannot replay a command."""
    from eador.battle_playback_scene import BattlePlaybackScene
    state = relief_before_rally()
    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        game.push(ShardScene(state)); game.tick(1/60)
        player = PlayerInput(game, finish_actions=False); player.press('e')
        view = game.scene
        resolved = state.to_json()
        player.press('f2')
        elapsed = view.playback.elapsed
        game.tick(3)
        assert view.playback.elapsed == elapsed
        player.press('escape')
        assert game.scene is view
        player.press('l')
        game.tick(3)
        assert state.to_json() == resolved
        player.press('escape')
        assert isinstance(game.scene, BattlePlaybackScene)
        player.button('Finish playback')
        assert type(game.scene) is BattleScene and state.to_json() == resolved
    finally:
        game._teardown()


def last_hold_phase():
    """Keep the public before-state of the real passive army's final scoring phase."""
    from tools.eador_extraction_campaign import AdventureOrders
    from tools.eador_relief_campaign import prepare_relief, relief_passive_route
    snapshots = []
    class Orders(AdventureOrders):
        def do(self, command, *args, **kwargs):
            if command == 'end_turn':
                snapshots.append(self.state.to_json())
            return super().do(command, *args, **kwargs)
    relief_passive_route(prepare_relief(), orders_type=Orders)
    return State.from_json(snapshots[-1])


def test_terminal_playback_finishes_with_one_result_and_one_earned_cue(tmp_path):
    """Winning rules are saved immediately; their result appears after the bounded viewing period."""
    from eador.battle_playback_scene import BattlePlaybackScene
    from eador.scene import ResultScene
    from tests.eador.test_game_audio import cues
    state = last_hold_phase()
    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        game.push(ShardScene(state)); game.tick(1/60)
        player = PlayerInput(game, finish_actions=False); player.press('e')
        assert isinstance(game.scene, BattlePlaybackScene) and state.battle.outcome_reason == 'hold'
        resolved = state.to_json()
        assert 'victory' not in cues(game)
        for _ in range(510):
            game.tick(1/60)
        assert isinstance(game.scene, ResultScene) and state.to_json() == resolved
        assert cues(game).count('victory') == 1
        player.reload(resolved)
        assert isinstance(game.scene, ResultScene) and cues(game).count('victory') == 1
        player.press('e')
        assert player.state.battle is None and player.state.provinces[player.state.hero.pos].explored
    finally:
        game._teardown()


def test_loading_during_a_terminal_playback_skips_visuals_without_replaying_the_reward(tmp_path):
    """The quicksave contains the won but unresolved encounter, not an intermediate visual frame."""
    from eador.battle_playback_scene import BattlePlaybackScene
    from eador.scene import ResultScene
    state = last_hold_phase()
    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        game.push(ShardScene(state)); game.tick(1/60)
        player = PlayerInput(game, finish_actions=False); player.press('e')
        assert isinstance(game.scene, BattlePlaybackScene)
        expected = state.to_json()
        player.reload(expected)
        assert type(game.scene) is ResultScene and player.state.to_json() == expected
        assert not player.state.provinces[player.state.hero.pos].explored
    finally:
        game._teardown()


def test_visual_movement_and_reduced_motion_use_the_same_resolved_command():
    """Normal feedback crosses legal path points; reduced motion uses stationary event poses."""
    from eador.battle_playback_scene import BattlePlayback
    from saga2d import HexGrid
    state = relief_before_rally()
    trace = state.battle.trace(state.battle.end_turn)
    resolved = state.to_json()
    player = BattlePlayback(state.battle, trace)
    assert player.view.log == []  # Even before its first tick, no future actions appear.
    index = next(i for i, event in enumerate(trace.events) if event.kind == 'move')
    player.advance(player.duration * (index + .25))
    actor = player.view.unit(player.event.actor_id)
    grid = HexGrid(player.view.terrain)
    assert player.position(actor, grid, still=True) == grid.center(player.event.before.unit(actor.id).pos)
    assert player.position(actor, grid) != player.position(actor, grid, still=True)
    player.advance(player.MAX_SECONDS)
    assert player.done and state.to_json() == resolved


def test_failed_autosave_and_manual_recovery_during_playback_preserve_the_one_resolved_turn(tmp_path):
    """A real file failure remains visible and recoverable; finishing cannot execute the turn again."""
    from saga2d import Label
    from eador.battle_playback_scene import BattlePlaybackScene
    from eador.persistence import AUTO_SLOTS
    from eador.scene import SaveScene
    state = relief_before_rally()
    expected = State.from_json(state.to_json()); expected.battle.end_turn()
    saves = tmp_path / 'saves'; saves.mkdir()
    for slot in AUTO_SLOTS:
        (saves / f'save_{slot}.json').write_bytes(b'damaged autosave')
    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(state)); game.tick(1/60)
        player = PlayerInput(game, finish_actions=False); player.press('e')
        assert isinstance(game.scene, BattlePlaybackScene)
        assert state.to_json() == expected.to_json() and 'Autosave failed' in game.scene.message
        assert any('All autosave slots are damaged' in c.text
                   for c in game.scene.ui.walk() if isinstance(c, Label))
        player.press('f6')
        assert isinstance(game.scene, SaveScene)
        player.press('tab'); assert game.scene.mode == 'save'
        player.press('1')
        assert (saves / 'save_1.json').is_file()
        player.press('escape')
        assert isinstance(game.scene, BattlePlaybackScene)
        player.press('f9')
        assert type(game.scene) is BattleScene and player.state.to_json() == expected.to_json()
        assert all((saves / f'save_{slot}.json').read_bytes() == b'damaged autosave' for slot in AUTO_SLOTS)
    finally:
        game._teardown()


def test_the_earned_native_equivalent_chain_preserves_each_frame_and_the_hold_result(tmp_path):
    """The development capture follows actual paid preparation and input, not injected animation fixtures."""
    from tools.verify_eador_battle_feedback import verify
    report = verify(tmp_path, backend='mock', scenario='hold', still=True, scale=125)
    assert any(item['event'] == 'objective' for item in report['observed'])
    assert report['exact_save_reloads'] >= 3


def test_manual_save_acknowledgement_survives_finishing_playback(tmp_path):
    """A successful save in the modal must not reveal an obsolete failure after Finish."""
    from eador.persistence import AUTO_SLOTS
    state = relief_before_rally()
    for slot in AUTO_SLOTS:
        (tmp_path / f'save_{slot}.json').write_bytes(b'damaged autosave')
    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        game.push(ShardScene(state)); game.tick(1/60)
        player = PlayerInput(game, finish_actions=False); player.press('e')
        assert 'Autosave failed' in game.scene.message
        before = state.to_json(); player.press('f5')
        assert 'Saved to Manual 1' in game.scene.message
        player.press('space')
        assert type(game.scene) is BattleScene and state.to_json() == before
        assert 'Saved to Manual 1' in game.scene.message
        assert game.scene.saves.load(1).to_json() == before
    finally:
        game._teardown()
