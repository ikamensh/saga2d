"""Authored rout choices disclose their actual objective before accepting a fee."""
import pytest

from eador.app import create_game
from eador.encounter_scene import EncounterScene
from eador.scene import BattleScene, ShardScene
from tools.eador_campaign import march_to, rest
from tools.eador_extraction_campaign import prepare_adventure
from tools.eador_ui import PlayerInput


@pytest.mark.parametrize('number', ['1', '2'])
def test_pack_approach_briefing_and_codex_describe_rout_without_a_seal_or_deadline(tmp_path, number):
    """Review/cancel is free; accepting records the visible fee and an untimed rout."""
    state = prepare_adventure(theme='elderwild')
    march_to(state, (-1, 1))
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
        assert 'Rout the defenders' in text and 'No round limit' in text
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
        assert 'No round limit' in text and 'Evacuate' not in text
    finally:
        game._teardown()
