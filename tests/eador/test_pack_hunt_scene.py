"""Authored rout choices disclose their actual objective before accepting a fee."""
import pytest

from eador.app import create_game
from eador.encounter_scene import EncounterScene
from eador.scene import BattleScene, ShardScene
from tools.eador_campaign import march_to, rest, site_position
from tools.eador_extraction_campaign import prepare_adventure
from tools.eador_ui import PlayerInput


@pytest.mark.parametrize('number', ['1', '2'])
def test_pack_approach_briefing_and_codex_describe_rout_and_global_exhaustion(tmp_path, number):
    """No mission deadline or seal applies; the battle's global exhaustion limit still does."""
    state = prepare_adventure(theme='elderwild')
    march_to(state, site_position(state, 'pack_hunt'))
    if not state.actions_left:
        rest(state)
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    player = PlayerInput(game)
    try:
        game.push(ShardScene(state))
        before = state.to_json()
        gold, crystals, actions = state.gold, state.crystals, state.actions_left
        player.press('x'); player.press(number)
        assert isinstance(game.scene, EncounterScene)
        text = ' '.join(item['text'] for item in game.backend.texts)
        assert 'Rout the defenders' in text and '80 rounds' in text
        assert 'Secure the seal' not in text and '◎ Seal' not in text
        approach = game.scene.approach
        assert state.to_json() == before
        player.press('escape')
        assert state.to_json() == before
        player.press('x'); player.press(number); player.press('return')
        assert isinstance(game.scene, BattleScene)
        assert any('ROUT THE DEFENDERS' in item['text'] for item in game.backend.texts)
        assert state.gold == gold - approach.gold_cost and state.crystals == crystals - approach.crystals_cost
        assert state.actions_left == actions - 1
        assert state.battle.objective.kind == 'rout' and state.battle.objective.deadline is None
        assert state.battle_adventure.approach == approach.id
        player.reload(state.to_json())
        player.press('c'); player.press('5')
        while not any('Current attempt' in item['text'] for item in game.backend.texts):
            player.button('Next')
        text = ' '.join(item['text'] for item in game.backend.texts)
        assert '80 rounds' in text and 'Evacuate' not in text
    finally:
        game._teardown()
