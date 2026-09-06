"""Immediate tactical casualties are visible before the player spends an order."""
import gzip
import json
from pathlib import Path
import pytest

from eador.__main__ import create_session
from eador.model import State
from eador.persistence import CampaignSaves
from tools.eador_ui import PlayerInput


def earned_save(plan, command):
    journal = Path(__file__).parents[2] / f'docs/evidence/shardbound-army-plans-cd351a9/{plan}.json.gz'
    return json.loads(gzip.decompress(journal.read_bytes()))['commands'][command]['before']


def test_earned_adept_casualty_is_explained_before_confirming_the_attack(tmp_path):
    """Inspecting a lethal attack and switching to another ally must leave the saved army untouched."""
    initial = earned_save('control', 80)
    game, title = create_session(['--data-dir', str(tmp_path)], backend='mock')
    player = PlayerInput(game)
    try:
        CampaignSaves(game.save_manager).save(State.from_json(initial))
        game.push(title)
        player.press('f9')
        player.click(*game.scene.grid.center(player.state.battle.unit(6).pos))
        player.press('f')
        shown = ' '.join(item['text'] for item in game.backend.texts)
        assert 'Rune Adept falls.' in shown
        assert 'Tab selects another unit.' in shown
        assert player.state.to_json() == initial
        player.click(*game.scene.grid.center(player.state.battle.unit(8).pos))
        player.press('f')
        assert 'Rune Adept falls.' not in ' '.join(item['text'] for item in game.backend.texts)
        assert player.state.to_json() == initial
        for unit in player.state.battle.units:
            if unit.team == 'player' and unit.alive and unit.id != 6:
                player.click(*game.scene.grid.center(unit.pos))
                player.press('g')
        player.click(*game.scene.grid.center(player.state.battle.unit(6).pos))
        player.press('f')
        shown = ' '.join(item['text'] for item in game.backend.texts)
        assert 'Rune Adept falls. Choose another order.' in shown
    finally:
        game._teardown()
        game.backend.quit()


@pytest.mark.parametrize('pin', [False, True])
def test_lethal_attack_or_pin_explains_the_kill_and_matches_the_actual_order(tmp_path, pin):
    """A killed defender has no next-turn movement; the preview stays true after resizing and reloading."""
    initial = earned_save('mobile', 26)
    game, title = create_session(['--data-dir', str(tmp_path)], backend='mock')
    player = PlayerInput(game)
    try:
        CampaignSaves(game.save_manager).save(State.from_json(initial))
        game.push(title)
        player.press('f9')
        target = player.state.battle.unit(1007)
        player.click(*game.scene.grid.center(player.state.battle.unit(3).pos))
        if pin:
            player.press('p')
        for _ in player.state.battle.units:
            player.press('f')
            if game.scene.cursor == target.pos:
                break
        player.press('f2'); player.press('right'); player.press('return')
        shown = ' '.join(item['text'] for item in game.backend.texts)
        assert f'{target.name} defeated.' in shown
        assert 'Next turn: Move' not in shown
        assert player.state.to_json() == initial
        player.press('return')
        assert player.state.battle.unit(1007).hp == 0
        player.reload(player.state.to_json())
    finally:
        game._teardown()
        game.backend.quit()
