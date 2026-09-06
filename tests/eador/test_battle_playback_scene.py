"""Ordered enemy feedback is a read-only view of already-saved authoritative rules."""
from eador.app import create_game
from eador.model import State
from eador.scene import BattleScene, ShardScene
from tools.eador_ui import PlayerInput
from tests.eador.test_battle_trace import relief_before_rally
import pytest


def test_playback_hit_sound_matches_damage_and_does_not_repeat_on_refresh(tmp_path):
    """A real ranged attack releases first; its one impact accompanies the visible HP change."""
    from eador.battle_playback_scene import BattlePlaybackScene
    from tests.eador.test_game_audio import cues
    state = State.new(hero_class='Wizard')
    state.explore()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(1 / 60)
        player = PlayerInput(game, finish_actions=False)
        archer = next(unit for unit in state.battle.units if unit.team == 'player' and unit.can_pin)
        player.order('battle.move', archer.id, (-1, 0))
        target = state.battle.targets(archer.id)[0]
        trace = state.battle.trace(lambda: state.battle.attack(archer.id, target.id))
        resolved = state.to_json()
        game.backend.sounds_played.clear()
        view = BattlePlaybackScene(game.scene, trace)
        game.push(view)
        assert cues(game) == ['attack_arrow']
        assert view.battle.unit(target.id).hp == trace.before.unit(target.id).hp
        game.tick(view.playback.duration * .49)
        assert 'attack_hit' not in cues(game)
        game.tick(view.playback.duration * .02)
        assert view.battle.unit(target.id).hp == trace.events[0].after.unit(target.id).hp
        assert cues(game).count('attack_hit') == 1
        view.refresh(); game.tick(0)
        assert cues(game).count('attack_hit') == 1
        assert state.to_json() == resolved
    finally:
        game.close()


@pytest.mark.parametrize('still', [False, True])
def test_direct_shot_has_bounded_feedback_and_keeps_orders_and_saves_live(tmp_path, still):
    """An actual player shot is visible without delaying orders; reduced motion stays fixed."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        from eador.scene import TitleScene
        game.push(TitleScene(hero_class='Wizard'))
        player = PlayerInput(game, finish_actions=False)
        if still:
            for key in ('o', 'd', 'down', 'down', 'right', 'return'):
                player.press(key)
        player.press('return'); player.press('x')
        battle = player.state.battle
        archer = next(unit for unit in battle.units if unit.team == 'player' and unit.can_pin)
        player.order('battle.move', archer.id, (-1, 0))
        target = battle.targets(archer.id)[0]
        expected = State.from_json(player.state.to_json())
        expected.battle.attack(archer.id, target.id)
        player.order('battle.attack', archer.id, target.id)
        assert type(game.scene) is BattleScene
        assert player.state.to_json() == expected.to_json()
        early = list(game.backend.lines)
        game.tick(.12)
        assert (early == game.backend.lines) == still
        game.tick(1.5)
        assert early != game.backend.lines, 'The shot must have a visible transient effect'
        assert player.state.to_json() == expected.to_json()
        # A new ordinary command and save/load need no playback completion control.
        player.order('battle.guard', 0)
        expected.battle.guard(0)
        assert type(game.scene) is BattleScene
        player.reload(expected.to_json())
    finally:
        game.close()


def test_shot_transients_leave_persistent_health_on_top(tmp_path):
    """Actual shot effects stay below readable damage and health throughout contact and drift."""
    from eador.style import GOLD, INK, RED
    state = State.new(hero_class='Wizard'); state.explore()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(1 / 60)
        player = PlayerInput(game, finish_actions=False)
        archer = next(unit for unit in state.battle.units if unit.team == 'player' and unit.can_pin)
        player.order('battle.move', archer.id, (-1, 0))
        target = state.battle.targets(archer.id)[0]
        player.order('battle.attack', archer.id, target.id)
        resolved = state.to_json()
        cx, cy = game.scene.grid.center(archer.pos)
        top = cy + game.scene.grid.size * .23
        plaque = next(shape for shape in game.backend.polygons if shape['color'] == INK
                      and abs(min(x for x, y in shape['points']) + max(x for x, y in shape['points']) - cx * 2) < .01
                      and abs(min(y for x, y in shape['points']) - top) < .01)
        hp = next(text for text in game.backend.texts if text['text'] == str(archer.hp)
                  and abs(text['x'] - cx) < .01 and abs(text['y'] - top) < .01)
        ring = [line for line in game.backend.lines if line['color'] == (*GOLD[:3], 180)]
        assert ring, 'The successful shot must retain its ground focus marker'
        assert all(line['order'] < plaque['order'] and line['order'] < hp['order'] for line in ring)
        damage = next(text for text in game.backend.texts if text['text'].startswith('-') and text['text'][1:].isdigit())
        neighbor = next(unit for unit in state.battle.units if unit.team == 'enemy' and unit.kind == 'brigand')
        nx, ny = game.scene.grid.center(neighbor.pos)
        neighbor_hp = next(text for text in game.backend.texts if text['text'] == str(neighbor.hp)
                           and abs(text['x'] - nx) < .01 and abs(text['y'] - (ny + game.scene.grid.size * .23)) < .01)
        assert damage['order'] < neighbor_hp['order']
        game.tick(.33)  # The real shot has reached its target; its impact ring is now visible.
        impact = [line for line in game.backend.lines
                  if line['color'][:3] == RED[:3] and line['color'][3] < 255]
        assert impact, 'The contact frame must retain a visible impact'
        damage = next(text for text in game.backend.texts if text['text'].startswith('-') and text['text'][1:].isdigit())
        tx, ty = game.scene.grid.center(target.pos)
        target_hp = next(text for text in game.backend.texts if text['text'] == str(target.hp)
                         and abs(text['x'] - tx) < .01 and abs(text['y'] - (ty + game.scene.grid.size * .23)) < .01)
        assert all(line['order'] < damage['order'] < target_hp['order'] for line in impact)
        def bounds(shape):
            return (min(x for x, y in shape['points']), min(y for x, y in shape['points']),
                    max(x for x, y in shape['points']), max(y for x, y in shape['points']))
        neighbor_box = next(bounds(shape) for shape in game.backend.polygons if shape['color'] == INK
                            and abs(bounds(shape)[0] + bounds(shape)[2] - nx * 2) < .01
                            and abs(bounds(shape)[1] - (ny + game.scene.grid.size * .23)) < .01)
        corners = game.scene.grid.corners(target.pos)
        left, top, right = min(x for x, y in corners), min(y for x, y in corners), max(x for x, y in corners)
        _, target_y = game.scene.grid.center(target.pos)
        for dt in (0, .4, .5):
            game.tick(dt)
            damage = next(text for text in game.backend.texts if text['text'].startswith('-') and text['text'][1:].isdigit())
            pill = next(bounds(shape) for shape in game.backend.polygons if shape['color'] == INK
                        and bounds(shape)[0] < damage['x'] < bounds(shape)[2]
                        and bounds(shape)[1] <= damage['y'] < bounds(shape)[3])
            assert left <= pill[0] < pill[2] <= right and top <= pill[1] < pill[3] <= target_y
            assert pill[2] - pill[0] < (right - left) * .75
            assert pill[2] <= neighbor_box[0] or pill[0] >= neighbor_box[2] or pill[3] <= neighbor_box[1] or pill[1] >= neighbor_box[3]
        assert state.to_json() == resolved
    finally:
        game.close()


@pytest.mark.parametrize('ability', ['swap', 'smoke', 'heal'])
def test_paid_ability_feedback_draws_from_the_resolved_trace(tmp_path, ability):
    """Purchased roles show their distinct actual effects while save/load remains authoritative."""
    from tools.eador_observatory_campaign import prepare_observatory
    state = prepare_observatory()
    state.explore(approach='clear' if ability == 'heal' else 'covered')
    battle = state.battle
    if ability == 'heal':
        for ident, pos in ((1, (1, -1)), (0, (0, 0)), (3, (0, -1))):
            battle.move(ident, pos)
        guard = next(unit for unit in battle.units if unit.team == 'enemy' and unit.kind == 'guard')
        battle.attack(0, guard.id)  # Earn the wound through the defender's real reaction.
        for ident, pos in ((4, (-1, 0)), (5, (-1, 1)), (6, (-2, 1))):
            battle.move(ident, pos)
        command, args, options = 'cast', ('heal', 0), {'caster_id': 6}
        assert 0 < battle.unit(0).hp < battle.unit(0).max_hp
    elif ability == 'swap':
        warden = next(unit for unit in battle.units if unit.team == 'player' and unit.can_swap)
        command, args, options = 'swap', (warden.id, battle.swap_targets(warden.id)[0].id), {}
    else:
        sapper = next(unit for unit in battle.units if unit.team == 'player' and unit.can_smoke)
        command, args, options = 'smoke', (sapper.id, min(battle.smoke_targets(sapper.id))), {}
    expected = State.from_json(state.to_json())
    getattr(expected.battle, command)(*args, **options)
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(1 / 60)
        player = PlayerInput(game, finish_actions=False)
        player.order('battle.' + command, *args, **options)
        assert type(game.scene) is BattleScene and state.to_json() == expected.to_json()
        early = list(game.backend.lines), list(game.backend.circles)
        game.tick(.2)
        assert early != (game.backend.lines, game.backend.circles)
        game.tick(1.5)
        assert early != (game.backend.lines, game.backend.circles)
        assert state.to_json() == expected.to_json()
        player.reload(expected.to_json())
    finally:
        game.close()


def test_native_effects_capture_path_uses_real_orders_and_exact_saves(tmp_path):
    """The native sampler's complete input route is executable against the shipped scene stack."""
    from tools.verify_eador_effects import verify
    report = verify(tmp_path, backend='mock')
    assert [case['name'] for case in report['cases']] == ['arrow', 'bolt', 'melee', 'heal', 'swap', 'smoke']
    assert report['exact_save_reloads'] == 6
    assert all(len(case['captures']) == 3 and case['orders'] for case in report['cases'])
    assert report['briefings'] and report['cpu_percent_requested'] == 25


def test_quick_heal_replaces_the_previous_damage_number_at_its_hex(tmp_path):
    """A fast legal Heal shows the new recovery amount without overprinting the earlier wound."""
    from tools.eador_observatory_campaign import prepare_observatory
    state = prepare_observatory(); state.explore(approach='clear')
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(1 / 60)
        player = PlayerInput(game, finish_actions=False)
        for ident, pos in ((1, (1, -1)), (0, (0, 0)), (3, (0, -1))):
            player.order('battle.move', ident, pos)
        guard = next(unit for unit in state.battle.units if unit.team == 'enemy' and unit.kind == 'guard')
        player.order('battle.attack', 0, guard.id)
        for ident, pos in ((4, (-1, 0)), (5, (-1, 1)), (6, (-2, 1))):
            player.order('battle.move', ident, pos)
        expected = State.from_json(state.to_json())
        hp = expected.battle.unit(0).hp
        expected.battle.cast('heal', 0, caster_id=6)
        restored = expected.battle.unit(0).hp - hp
        player.order('battle.cast', 'heal', 0, caster_id=6)
        cx, _ = game.scene.grid.center(state.battle.unit(0).pos)
        numbers = [text['text'] for text in game.backend.texts if text['text'].startswith(('+', '-'))
                   and text['text'][1:].isdigit() and abs(text['x'] - cx) < .01]
        assert numbers == [f'+{restored}']
        assert state.to_json() == expected.to_json()
    finally:
        game.close()


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
