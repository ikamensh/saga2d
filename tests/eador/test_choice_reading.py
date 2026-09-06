"""Earned decisions reflow without changing their saved consequences."""

import json

import pytest
from saga2d import Label

from eador.app import create_game
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import ChoiceScene, ShardScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def first_reward():
    """Win the starting shrine through public tactics, leaving its reward undecided."""
    state = State.new(7, 'Wizard')
    state.explore()
    for _ in range(80):
        if state.battle.outcome:
            break
        state.battle.auto_turn()
    assert state.battle.outcome == 'player'
    state.resolve_battle()
    assert state.choice.context == 'moonstone'
    return state


def test_choice_reading_preview_restart_and_numbered_reward(tmp_path):
    """Reading overlays do not choose; a restarted 125% reward keeps complete text and its real effects."""
    state = first_reward()
    before = state.to_json()
    saves = tmp_path / 'saves'
    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        assert isinstance(game.scene, ChoiceScene)
        for key in ('t', 'right', 'escape'):
            player.press(key)
        assert reading_scale(game) == 100
        assert not (tmp_path / 'settings.json').exists()
        for key in ('t', 'right', 'return', 'c', 'escape'):
            player.press(key)
        assert isinstance(game.scene, ChoiceScene)
        assert reading_scale(game) == 125
        assert state.to_json() == before
        check_reading_layout(game.scene)
        labels = [item.text for item in game.scene.ui.find_all(lambda item: isinstance(item, Label))]
        for option in state.choice.options:
            assert option.name in labels and option.description in labels
        assert any(row['text'] == 'Keep Moonstone' and row['font_size'] == 21 for row in game.backend.texts)
        player.reload(before)
        assert isinstance(game.scene, ChoiceScene)
    finally:
        game._teardown()

    restarted = create_game(backend='mock', save_dir=saves)
    try:
        restarted.push(ShardScene(State.from_json(before)))
        player = PlayerInput(restarted)
        restarted.tick(1 / 60)
        assert reading_scale(restarted) == 125
        check_reading_layout(restarted.scene)
        expected = State.from_json(before)
        expected.choose(expected.choice.options[1].id)
        player.press('2')
        assert player.state.to_json() == expected.to_json()
        assert 'moonstone' not in player.state.inventory
        player.press('2')
        assert player.state.to_json() == expected.to_json()
    finally:
        restarted._teardown()


def test_all_earned_choices_keep_whole_options_and_actual_effects(tmp_path):
    """Every relic, duplicate and hero discipline reads at both sizes, and each visible option has its saved effect."""
    from tools.verify_eador_choices import verify

    verify(tmp_path, backend='mock')


@pytest.mark.parametrize('damaged_bytes', [b'damaged manual save', json.dumps({'version': 'X' * 5000}).encode()],
                         ids=['broken-json', 'huge-invalid-version'])
def test_choice_save_and_load_errors_are_immediately_readable(tmp_path, damaged_bytes):
    """A damaged manual file cannot erase or obscure a real pending decision, even after overlay return."""
    saves = tmp_path / 'saves'
    saves.mkdir()
    damaged = saves / 'save_1.json'
    damaged.write_bytes(damaged_bytes)
    (tmp_path / 'settings.json').write_text('{"codex_text_scale": 125}')
    state = first_reward()
    before = state.to_json()
    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        for key in ('f5', 'f9'):
            player.press(key)
            assert isinstance(game.scene, ChoiceScene) and game.scene.message
            assert any(game.scene.message == item.text
                       for item in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
            check_reading_layout(game.scene)
            assert state.to_json() == before and damaged.read_bytes() == damaged_bytes
            player.press('c')
            player.press('escape')
            assert any(game.scene.message == item.text
                       for item in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
    finally:
        game._teardown()


def test_queued_choice_reports_checkpoint_failure_without_repeating_first_option(tmp_path):
    """A learned skill can reveal its earned relic while preserving damaged autosaves and the complete warning."""
    from eador.persistence import AUTO_SLOTS
    from tools.verify_eador_choices import prepared_choices

    for _, snapshot in prepared_choices():
        expected = State.from_json(snapshot)
        expected.choose(expected.choice.options[0].id)
        if expected.choice:
            break
    else:
        raise AssertionError('The earned routes must produce a queued decision')
    state = State.from_json(snapshot)
    assert state.choice != expected.choice
    saves = tmp_path / 'saves'
    saves.mkdir()
    for slot in AUTO_SLOTS:
        (saves / f'save_{slot}.json').write_bytes(b'damaged autosave')
    (tmp_path / 'settings.json').write_text('{"codex_text_scale": 125}')
    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        player.press('1')
        assert isinstance(game.scene, ChoiceScene) and state.to_json() == expected.to_json()
        assert 'All autosave slots are damaged' in game.scene.message
        assert any(game.scene.message == item.text
                   for item in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
        check_reading_layout(game.scene)
        for key in ('t', 'left', 'escape', 'c', 'escape'):
            player.press(key)
        assert state.to_json() == expected.to_json()
        assert all((saves / f'save_{slot}.json').read_bytes() == b'damaged autosave' for slot in AUTO_SLOTS)
    finally:
        game._teardown()


def test_final_choice_save_failure_acknowledges_the_applied_decision_once(tmp_path):
    """An unsaved final reward stays readable; overlays and old number keys cannot grant it twice."""
    from saga2d import Button
    from eador.persistence import AUTO_SLOTS

    saves = tmp_path / 'saves'
    saves.mkdir()
    for slot in AUTO_SLOTS:
        (saves / f'save_{slot}.json').write_bytes(b'damaged autosave')
    (tmp_path / 'settings.json').write_text('{"codex_text_scale": 125}')
    state = first_reward()
    expected = State.from_json(state.to_json())
    expected.choose('sell')
    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        player.press('2')
        assert isinstance(game.scene, ChoiceScene)
        assert state.to_json() == expected.to_json() and state.choice is None
        assert any('All autosave slots are damaged' in item.text
                   for item in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
        assert not game.scene.ui.find(lambda item: isinstance(item, Button) and item.text.startswith('Choose '))
        check_reading_layout(game.scene)
        for key in ('1', '2', 't', 'left', 'escape', 'c', 'escape', 'f6', 'escape', 'f9'):
            player.press(key)
        assert isinstance(game.scene, ChoiceScene) and state.to_json() == expected.to_json()
        assert 'empty' in game.scene.message.lower()
        player.press('f5')
        assert isinstance(game.scene, ChoiceScene)
        assert game.scene.saves.load().to_json() == expected.to_json()
        assert any('Saved to Manual 1' in item.text
                   for item in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
        player.press('return')
        assert isinstance(game.scene, ShardScene)
        player.press('f9')
        assert isinstance(game.scene, ShardScene) and player.state.to_json() == expected.to_json()
        assert all((saves / f'save_{slot}.json').read_bytes() == b'damaged autosave' for slot in AUTO_SLOTS)
    finally:
        game._teardown()
