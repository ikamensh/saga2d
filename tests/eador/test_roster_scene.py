"""Control recruits disclose both currencies and execute their saved capabilities."""
from dataclasses import replace

import pytest

from eador.app import create_game
from eador.model import State
from eador.scene import ShardScene
from tools.eador_ui import PlayerInput


@pytest.mark.parametrize('kind,number', [('sapper', '3'), ('adept', '4'), ('skyrider', '5')])
def test_recruit_buttons_require_crystals_and_deduct_both_displayed_costs(tmp_path, kind, number):
    """Gold alone cannot activate a special recruit's button or number shortcut."""
    for crystals in (0, 8):
        # Isolate affordability with a valid funded save; paid campaign routes
        # separately exercise earning the buildings and these resources.
        state = replace(State.new(7), gold=200, crystals=crystals,
                        buildings={'market', 'mage_tower', 'temple'})
        game = create_game(backend='mock', save_dir=tmp_path / str(crystals))
        player = PlayerInput(game)
        try:
            game.push(ShardScene(state))
            player.press('r'); player.press('right')
            before = state.to_json()
            crystal_cost = state.recruit_crystal_cost(kind)
            assert any(f'{crystal_cost} crystal' in item['text'] for item in game.backend.texts)
            player.press(number)
            if crystals == 0:
                assert state.to_json() == before
            else:
                assert state.hero.army[-1].kind == kind
                assert state.gold == 200 - state.recruit_cost(kind)
                assert state.crystals == crystals - crystal_cost
                player.press('escape')
                player.reload(state.to_json())
        finally:
            game._teardown()


@pytest.mark.parametrize('scenario', ['smoke', 'rally', 'repulse', 'watch'])
def test_paid_control_orders_have_exact_previews_and_saved_finite_effects(tmp_path, scenario):
    """The native input journey buys the army, aims/cancels the order and checks its complete saved effect."""
    from tools.verify_eador_control import verify
    report = verify(tmp_path, backend='mock', scenario=scenario)
    assert report['exact_save_reloads'] >= 1
