"""Reading size extends to complete guidance without changing campaign commands."""

import pytest
from saga2d import Label

from eador.app import create_game
from eador.model import State
from eador.scene import HelpScene, ShardScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def guide_body_size(game):
    return next(record['font_size'] for record in game.backend.texts if record['text'].startswith('Build a barracks'))


def test_guide_shares_reading_preview_cancel_apply_and_restart(tmp_path):
    """The Guide visibly reflows at 125%; Cancel restores 100% and no reading action changes a save."""
    state = State.new(7)
    saved = state.to_json()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        player.press('f1')
        assert isinstance(game.scene, HelpScene) and guide_body_size(game) == 12
        for key in ('o', 'd', 'down', 'down', 'down', 'right', 'escape'):
            player.press(key)
        assert isinstance(game.scene, HelpScene) and guide_body_size(game) == 12
        assert not (tmp_path / 'settings.json').exists()
        for key in ('o', 'd', 'down', 'down', 'down', 'right', 'return'):
            player.press(key)
        assert isinstance(game.scene, HelpScene) and guide_body_size(game) == 15
        check_reading_layout(game.scene)
        assert state.to_json() == saved
        player.press('c')
        assert any(record['font_size'] == 16 and 'Recruit for' in record['text'] for record in game.backend.texts)
        player.press('escape')
        assert isinstance(game.scene, HelpScene)
    finally:
        game._teardown()

    restarted = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        restarted.push(ShardScene(State.from_json(saved)))
        PlayerInput(restarted).press('f1')
        assert guide_body_size(restarted) == 15
        check_reading_layout(restarted.scene)
    finally:
        restarted._teardown()


def test_saved_reading_size_keeps_paid_briefing_choice_cost_and_geometry_reviewable(tmp_path):
    """The old one-key 125% file enlarges all briefing facts; reading never spends its advertised fee."""
    from eador.encounter_scene import EncounterScene
    from eador.scene import BattleScene
    from tools.eador_observatory_campaign import prepare_observatory

    path = tmp_path / 'settings.json'
    previous = b'{"codex_text_scale": 125}'
    path.write_bytes(previous)
    state = prepare_observatory()
    saved, gold, crystals, actions = state.to_json(), state.gold, state.crystals, state.actions_left
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    player = PlayerInput(game)
    try:
        game.push(ShardScene(state))
        player.press('x')
        player.press('2')
        assert isinstance(game.scene, EncounterScene)
        definition, approach = game.scene.definition, game.scene.approach
        assert {record['font_size'] for record in game.backend.texts
                if record['text'].startswith('Hold the marked hex')} == {15}
        check_reading_layout(game.scene)
        for key in ('t', 'left', 'escape'):
            player.press(key)
        assert game.scene.approach == approach and state.to_json() == saved
        check_reading_layout(game.scene)
        assert path.read_bytes() == previous
        player.button('Return to shard')
        assert state.to_json() == saved
        for key in ('x', '2', 'return'):
            player.press(key)
        assert isinstance(game.scene, BattleScene)
        assert state.gold == gold - approach.gold_cost and state.crystals == crystals - approach.crystals_cost
        assert state.actions_left == actions - 1
        assert state.battle.terrain == dict(definition.terrain)
        assert [unit.pos for unit in state.battle.units if unit.team == 'player'] == list(definition.player_positions[:len(state.hero.army) + 1])
        player.reload(state.to_json())
    finally:
        game._teardown()


def test_all_paid_briefings_and_wounded_retries_fit_both_sizes_without_committing(tmp_path):
    """Each actual approach, including blocked fees and the linked Gate, stays fully reviewable."""
    from tools.verify_eador_guidance import verify_briefing_matrix

    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        rows = verify_briefing_matrix(game)
        assert any(row['blocked'] for row in rows)
        assert {row['percent'] for row in rows} == {100, 125}
    finally:
        game._teardown()


@pytest.mark.parametrize('hero,support,isolated', [('Commander', 'ranger', 'Ranger (army slot 5)'),
                                                  ('Warrior', 'healer', 'Acolyte (army slot 5)'),
                                                  ('Scout', None, 'Hero starts alone east')])
def test_explorer_names_the_actual_isolated_party_in_both_approaches(tmp_path, hero, support, isolated):
    """A real purchased party is named from deployment, including a lone hero, without changing its orders."""
    from tools.eador_explorer_campaign import prepare_explorer
    from eador.encounter_scene import EncounterScene

    (tmp_path / 'settings.json').write_text('{"codex_text_scale": 125}')
    state = prepare_explorer(hero, support=support)
    before = state.to_json()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    player = PlayerInput(game)
    try:
        game.push(ShardScene(state))
        player.press('x')
        assert isinstance(game.scene, EncounterScene)
        for key in ('1', '2'):
            player.press(key)
            text = '\n'.join(label.text for label in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
            assert isolated in text
            check_reading_layout(game.scene)
            assert state.to_json() == before
    finally:
        game._teardown()
