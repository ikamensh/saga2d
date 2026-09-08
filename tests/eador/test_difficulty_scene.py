"""Difficulty selection controls new runs while saved realm rules stay authoritative."""
import pytest

from eador.app import create_game
from eador.scene import ShardScene, TitleScene
from tools.eador_ui import PlayerInput


@pytest.mark.parametrize('mode,key', [('accessible', '1'), ('standard', '2'), ('challenge', '3')])
def test_title_keyboard_and_mouse_select_the_actual_standalone_and_linked_rules(tmp_path, mode, key):
    """Visible choices supply grants and warnings to both starting paths without touching saved runs."""
    from eador.difficulty import DIFFICULTIES
    rules = DIFFICULTIES[mode]
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        player = PlayerInput(game)
        game.push(TitleScene(17, theme='ruins', hero_class='Wizard'))
        player.press(key)
        assert rules.description in ' '.join(t['text'] for t in game.backend.texts)
        player.press('return')
        assert isinstance(game.scene, ShardScene)
        state = game.scene.state
        assert state.rules is rules and state.theme == 'ruins' and state.hero.hero_class == 'Wizard'
        assert (state.gold, state.crystals) == (rules.starting_gold, rules.starting_crystals)
        assert state.rival.turns_until_action == rules.opening_delay
        player.press('f5')
        saved = state.to_json()
        player.press('f1'); player.press('s'); player.press('1')
        assert isinstance(game.scene, TitleScene)
        player.button('Standard' if mode != 'standard' else 'Challenge')
        player.press('f9')
        assert game.scene.state.to_json() == saved
        game.clear_and_push(TitleScene(17, hero_class='Wizard'))
        game.tick(1 / 60)
        player.button(rules.title)
        player.press('l')
        assert game.scene.state.rules is rules and game.scene.state.campaign is not None
    finally:
        game._teardown()


def test_paid_wounded_army_sees_its_saved_mode_and_actual_next_rest_before_ending_turn(tmp_path):
    """Hero, map and saves read the same rules; the displayed recovery matches a real paid battle."""
    from tools.eador_campaign import finish_battle
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        player = PlayerInput(game)
        game.push(TitleScene(7, hero_class='Wizard'))
        player.press('1'); player.press('return')
        state = player.state
        state.build('temple'); state.recruit('healer'); state.explore()
        finish_battle(state)
        actual = player.root.state
        before = actual.to_json()
        recovery = actual.recovery_preview()
        assert recovery.hero_hp > 0 or recovery.mana > 0
        player.press('h')
        shown = ' '.join(t['text'] for t in game.backend.texts)
        assert 'Accessible realm' in shown
        assert f'hero +{recovery.hero_hp} HP' in shown
        assert f'up to {recovery.army_hp} HP each' in shown
        assert f'mana +{recovery.mana}' in shown
        assert actual.to_json() == before
        player.press('escape')
        assert 'ACCESSIBLE' in ' '.join(t['text'] for t in game.backend.texts)
        hp, mana = actual.hero.hp, actual.hero.mana
        state.end_turn()
        assert actual.hero.hp == hp + recovery.hero_hp and actual.hero.mana == mana + recovery.mana
        player.press('f5'); player.press('f6')
        assert 'Accessible' in ' '.join(t['text'] for t in game.backend.texts)
    finally:
        game._teardown()


@pytest.mark.parametrize('mode', ['accessible', 'standard', 'challenge'])
def test_linked_briefs_show_the_actual_funding_and_warning_then_launch_saved_rules(tmp_path, mode):
    """Load public-play departure/recovery states; visible retinue choices deliver their advertised funds."""
    from eador.model import State
    from tools.eador_linked_campaign import lose_shard, play_stage, travel_selection
    state = play_stage(State.new_campaign(7, difficulty=mode))
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        player = PlayerInput(game)
        game.push(ShardScene(State.from_json(state.to_json())))
        game.tick(1 / 60)
        shown = ' '.join(t['text'] for t in game.backend.texts)
        assert state.rules.title.upper() in shown
        assert f'first operation in {state.rules.arrival_delay} turns' in shown
        player.press('1')
        gold, crystals = state.expedition_funding()
        assert f'{gold} gold · {crystals} crystals' in ' '.join(t['text'] for t in game.backend.texts)
        player.choose_retinue(travel_selection(player.root.state))
        player.press('return')
        assert (player.root.state.gold, player.root.state.crystals) == (gold, crystals)
        assert player.root.state.rules is state.rules
        player.press('j')
        assert f'{state.rules.recovery_gold} gold and {state.rules.recovery_crystals} crystals' in ' '.join(t['text'] for t in game.backend.texts)
        lost = lose_shard(State.from_json(player.root.state.to_json()))
        game.clear_and_push(ShardScene(lost))
        game.tick(1 / 60)
        gold, crystals = lost.expedition_funding(recovery=True)
        assert f'{gold} gold · {crystals} crystals' in ' '.join(t['text'] for t in game.backend.texts)
        player.choose_retinue(travel_selection(lost))
        player.press('return')
        assert (player.root.state.gold, player.root.state.crystals) == (gold, crystals)
        assert player.root.state.rules is state.rules and player.root.state.campaign.recovery_used
    finally:
        game._teardown()


def test_challenge_explains_base_production_and_its_live_finite_rival_window(tmp_path):
    """A real Marketplace purchase exposes the reduced aggregate yield before the bill is paid."""
    from tools.verify_eador_shard_reading import check_metric

    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        player = PlayerInput(game)
        game.push(TitleScene(7))
        player.press('3'); player.press('return')
        player.state.build('market')
        state = player.root.state
        shown = ' '.join(t['text'] for t in game.backend.texts)
        assert 'Realm gold yield: 80% of base production' in shown
        check_metric(player.root, 'income', f'{state.provinces[state.hero.pos].income} base', 'Income')
        check_metric(player.root, 'income', f'+{state.income}', 'Income')
        player.press('v')
        shown = ' '.join(t['text'] for t in game.backend.texts)
        assert 'THE DUSKSPIRE EXPEDITION · CHALLENGE' in shown
        assert f'first paid replacement waits {state.rules.replacement_delay} turns' in shown
        before = state.gold
        earnings = state.income - state.upkeep
        player.press('escape'); player.press('e')
        assert state.gold == before + earnings
    finally:
        game._teardown()


@pytest.mark.parametrize('mode,recovery', [('accessible', True), ('challenge', False)])
def test_complete_visible_linked_run_preserves_selected_difficulty_through_departures(tmp_path, mode, recovery):
    """Replay the full input verifier, including Accessible's funded recovery and both saved departures."""
    from tools.verify_eador_campaign import verify
    report = verify(tmp_path, backend='mock', difficulty=mode, recovery=recovery)
    assert report['difficulty'] == mode and len(report['records']) == 3


def test_native_opening_driver_funds_its_support_purchase_in_every_mode(tmp_path):
    """Starting grants differ; the real-input verifier must earn its Acolyte before testing rest/restart."""
    from tools.verify_eador_difficulty import verify
    report = verify(tmp_path, backend='mock')
    assert {row['mode'] for row in report['modes']} == {'accessible', 'standard', 'challenge'}
    assert all(row['fresh_game_restarts'] == 1 for row in report['modes'])


def test_recorded_challenge_keeps_its_original_rest_and_linked_funding_through_current_controls(tmp_path):
    """Load actual earlier saves after starting today's Challenge; visible commands preserve exact continuation."""
    from tools.verify_eador_difficulty import verify_recorded_challenge

    reports = verify_recorded_challenge(tmp_path, backend='mock')
    assert {row['case'] for row in reports} == {'rest', 'advance', 'recover'}
    assert all(row['rules_id'] == 'challenge-1' and row['exact_save_reloads'] == 1 for row in reports)
