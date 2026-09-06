"""Adventure choices disclose their costs before entering an explicitly commanded escape."""
import pytest

from eador.app import create_game
from eador.encounter_scene import EncounterScene
from eador.encounters import ENCOUNTERS
from eador.scene import BattleScene, ShardScene
from tools.eador_extraction_campaign import prepare_adventure
from tools.eador_ui import PlayerInput


@pytest.mark.parametrize('theme', ['frontier', 'elderwild'])
def test_second_adventure_approach_is_reviewable_cancelable_and_saved_exactly(tmp_path, theme):
    """A guide fee or cargo burden applies only after accepting the visible second choice."""
    state = prepare_adventure(theme=theme)
    approach = state.adventure_approaches()[1]
    definition = ENCOUNTERS[approach.encounter]
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    player = PlayerInput(game)
    try:
        game.push(ShardScene(state))
        before, gold, crystals, actions = state.to_json(), state.gold, state.crystals, state.actions_left
        player.press('x')
        assert isinstance(game.scene, EncounterScene)
        player.press('2')
        assert game.scene.definition == definition and state.to_json() == before
        player.press('escape')
        assert isinstance(game.scene, ShardScene) and state.to_json() == before
        for key in ('x', '2', 'return'):
            player.press(key)
        assert isinstance(game.scene, BattleScene)
        assert state.gold == gold - approach.gold_cost and state.actions_left == actions - 1
        assert state.crystals == crystals - approach.crystals_cost
        assert state.battle_adventure.approach == approach.id
        assert state.battle.objective.exits == definition.exits
        assert state.battle.unit(0).pos == definition.player_positions[0]
        assert state.battle.unit(0).cargo_penalty == approach.cargo_penalty
        player.reload(state.to_json())
    finally:
        game._teardown()


@pytest.mark.parametrize('theme,approach', [('frontier', 'direct'), ('frontier', 'guided'),
                                          ('elderwild', 'light'), ('elderwild', 'full')])
def test_paid_manual_extraction_routes_work_through_visible_player_orders(tmp_path, theme, approach):
    """Both choices at both sites reach an explicit, saved escape with living defenders."""
    from tools.verify_eador_extraction import verify
    report = verify(tmp_path, backend='mock', theme=theme, approach=approach)
    assert report['exact_save_reloads'] >= 2


def test_spending_the_carriers_order_on_an_exit_disables_evacuation_until_reload(tmp_path):
    """The hero must explicitly leave with an unspent order; a saved ready carrier can do so."""
    from tools.eador_extraction_campaign import AdventureOrders, crossing_route
    from eador.scene import ResultScene

    class StopBeforeEscape(AdventureOrders):
        def do(self, command, *args, **kwargs):
            if command != 'evacuate':
                super().do(command, *args, **kwargs)

    state = crossing_route(prepare_adventure(), 'guided', orders_type=StopBeforeEscape).state
    assert state.battle.outcome is None and state.battle.evacuation_blocked_reason is None
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    player = PlayerInput(game)
    try:
        game.push(ShardScene(state))
        for key in ('f5', 'g'):
            player.press(key)
        before = player.state.to_json()
        player.press('v')
        assert player.state.to_json() == before and player.state.battle.outcome is None
        assert any('already acted' in text['text'] for text in game.backend.texts)
        for key in ('f9', 'v'):
            player.press(key)
        assert isinstance(game.scene, ResultScene) and player.state.battle.outcome_reason == 'escape'
    finally:
        game._teardown()
