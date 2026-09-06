"""Independent playback review through Game input and real saved campaign states."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import pytest
from eador.app import create_game
from eador.model import State
from eador.scene import BattleScene, ResultScene, ShardScene, TitleScene, SaveScene
from eador.battle_playback_scene import BattlePlaybackScene
from tools.eador_ui import PlayerInput
from tests.eador.test_battle_trace import relief_before_rally
from tests.eador.test_battle_playback_scene import last_hold_phase

def setup(state, tmp_path):
    game = create_game(backend='mock', save_dir=tmp_path)
    game.push(ShardScene(state)); game.tick(0)
    return game, PlayerInput(game, finish_actions=False)

def batch(game, *keys):
    for key in keys:
        game.backend.inject_key(key)
        game.backend.inject_key(key, type='key_release')
    game.tick(0)

@pytest.mark.parametrize('command', ['e', 'a'])
def test_all_ordinary_keys_and_hex_clicks_remain_read_only(command, tmp_path):
    state = relief_before_rally()
    expected = State.from_json(state.to_json())
    getattr(expected.battle, 'end_turn' if command == 'e' else 'auto_turn')()
    game, player = setup(state, tmp_path)
    try:
        batch(game, command)
        assert isinstance(game.scene, BattlePlaybackScene)
        visual = game.scene
        authoritative = expected.to_json()
        for key in ('e', 'a', 'g', 't', '1', '2', 'p', 's', 'q', 'd', 'r', 'f', 'tab',
                    'left', 'right', 'up', 'down', 'pageup', 'pagedown', 'o', 'v', 'h', 'b', 'x', 'j'):
            batch(game, key)
            assert game.scene is visual and player.state.to_json() == authoritative, key
        for pos in state.battle.terrain:
            x, y = visual.grid.center(pos)
            game.backend.inject_click(round(x), round(y))
            game.backend.inject_release(round(x), round(y))
            game.tick(0)
            assert game.scene is visual and player.state.to_json() == authoritative, pos
        batch(game, 'space', 'e', 'return', 'a', 't')
        assert type(game.scene) in (BattleScene, ResultScene)
        assert player.state.to_json() == authoritative
    finally:
        game._teardown(); game.backend.quit()


def test_loading_older_state_discards_finished_rules_and_cannot_later_post_a_ghost_result(tmp_path):
    state = last_hold_phase()
    before = state.to_json()
    expected = State.from_json(before); expected.battle.end_turn()
    game, player = setup(state, tmp_path)
    try:
        player.press('f5')
        player.press('e')
        visual = game.scene
        assert isinstance(visual, BattlePlaybackScene) and player.state.battle.outcome == 'player'
        player.press('c')
        clock = visual.playback.elapsed, visual.playback.index
        game.tick(30)
        assert (visual.playback.elapsed, visual.playback.index) == clock
        player.press('escape'); player.press('f9')
        assert type(game.scene) is BattleScene and player.state.to_json() == before
        assert not any(isinstance(s, BattlePlaybackScene) for s in game.scenes)
        game.tick(30)
        assert type(game.scene) is BattleScene and player.state.to_json() == before
        batch(game, 'e', 'space', 'return')
        assert isinstance(game.scene, BattlePlaybackScene)
        assert player.state.to_json() == expected.to_json()
        batch(game, 'space', 'space', 'return', 'e')
        assert type(game.scene) is ResultScene
        assert player.state.to_json() == expected.to_json() and not player.state.provinces[player.state.hero.pos].explored
        expected.resolve_battle()
        batch(game, 'return', 'return', 'e', 'space')
        assert player.state.to_json() == expected.to_json()
        assert len([s for s in game.scenes if isinstance(s, (BattleScene, ResultScene))]) == 0
    finally:
        game._teardown(); game.backend.quit()


def test_save_and_title_during_playback_keeps_resolved_state_and_cancels_visual_lifetime(tmp_path):
    state = last_hold_phase()
    game, player = setup(state, tmp_path)
    try:
        player.press('e')
        visual = game.scene
        assert isinstance(visual, BattlePlaybackScene)
        resolved = player.state.to_json()
        player.press('f1'); player.press('s')
        assert isinstance(game.scene, SaveScene) and game.scene.return_to_title
        clock = visual.playback.elapsed, visual.playback.index
        game.tick(30)
        assert (visual.playback.elapsed, visual.playback.index) == clock
        player.press('1')
        assert isinstance(game.scene, TitleScene)
        game.tick(30)
        assert isinstance(game.scene, TitleScene)
        player.press('f9')
        assert type(game.scene) is ResultScene and player.state.to_json() == resolved
        assert not any(isinstance(s, BattlePlaybackScene) for s in game.scenes)
        expected = State.from_json(resolved); expected.resolve_battle()
        batch(game, 'return', 'return')
        assert player.state.to_json() == expected.to_json()
    finally:
        game._teardown(); game.backend.quit()


@pytest.mark.parametrize('fixture', ['v4_brace_battle', 'v10_pinned_crossing', 'v12_pre_relief_grove_battle'])
def test_saved_old_battles_play_naturally_without_saving_visual_frames(fixture, tmp_path):
    saved = (ROOT / 'tests/eador/fixtures' / f'{fixture}.json').read_text()
    state = State.from_json(saved)
    game, player = setup(state, tmp_path)
    try:
        expected = State.from_json(saved)
        for _ in range(80):
            if expected.battle.outcome: break
            expected.battle.auto_turn()
            player.press('a')
            resolved = expected.to_json()
            assert player.state.to_json() == resolved
            for tick in range(50):
                if not isinstance(game.scene, BattlePlaybackScene): break
                game.tick(.2)
                assert player.state.to_json() == resolved
            else: raise AssertionError('Unbounded playback')
            assert type(game.scene) in (BattleScene, ResultScene)
        assert type(game.scene) is ResultScene and expected.battle.outcome
    finally:
        game._teardown(); game.backend.quit()
