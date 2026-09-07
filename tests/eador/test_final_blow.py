"""A deciding contact remains visible before its already-earned battle result."""
import gzip
import json

import pytest

from eador.app import create_game
from eador.model import State
from eador.persistence import CampaignSaves
from eador.scene import BattleScene, ResultScene, ShardScene
from tests.eador.test_game_audio import cues
from tools.eador_ui import PlayerInput
from tools.verify_eador_final_blow import SOURCE, earned_last_arrow as recorded_last_arrow


def earned_last_arrow():
    """The retained manual opening reached this final shot without changing any fixture stats."""
    order = recorded_last_arrow()
    state = State.from_json(order['before'])
    assert state.battle.outcome is None
    assert sum(unit.alive for unit in state.battle.units if unit.team == 'enemy') == 1
    return state, tuple(order['args'])


def before_second_round_orders():
    recorded_last_arrow()  # Authenticate the journal before taking its earlier checkpoint.
    report = json.loads(gzip.decompress(SOURCE.read_bytes()))
    return State.from_json(report['orders'][8]['before'])


@pytest.mark.parametrize('still', [False, True])
def test_final_arrow_lands_before_result_while_progress_is_already_saved(tmp_path, still):
    """The last target survives visually until contact; the exact winning save exists immediately."""
    state, (actor, target) = earned_last_arrow()
    before_hp = state.battle.unit(target).hp
    expected = State.from_json(state.to_json())
    expected.battle.attack(actor, target)
    assert expected.battle.outcome == 'player'
    resolved = expected.to_json()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        from eador.preferences import DEFAULTS, apply_preferences
        apply_preferences(game, DEFAULTS | {'reduced_motion': still})
        game.push(ShardScene(state))
        game.tick(1 / 60)
        player = PlayerInput(game, finish_actions=False)
        player.order('battle.attack', actor, target)
        assert isinstance(game.scene, BattleScene), 'The result must not cover the deciding shot'
        assert game.scene.battle.unit(target).hp == before_hp
        assert state.to_json() == resolved
        assert CampaignSaves(game.save_manager).load(10).to_json() == resolved
        assert cues(game).count('attack_arrow') == 1
        assert 'attack_hit' not in cues(game) and 'victory' not in cues(game)
        game.tick(.2)
        assert game.scene.battle.unit(target).hp == before_hp
        game.tick(.25)
        assert game.scene.battle.unit(target).hp == 0
        assert cues(game).count('attack_hit') == 1 and 'victory' not in cues(game)
        for _ in range(120):
            game.tick(1 / 60)
        assert isinstance(game.scene, ResultScene)
        assert cues(game).count('attack_hit') == cues(game).count('victory') == 1
        assert state.to_json() == resolved
    finally:
        game.close()


@pytest.mark.parametrize('interruption', ['help', 'save_browser', 'load'])
def test_deciding_shot_can_be_covered_or_loaded_without_replaying_rewards(tmp_path, interruption):
    """Overlays pause the view; loading the winning save skips it with no ghost impact or fanfare."""
    state, (actor, target) = earned_last_arrow()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        game.tick(1 / 60)
        player = PlayerInput(game, finish_actions=False)
        player.order('battle.attack', actor, target)
        resolved = state.to_json()
        if interruption == 'load':
            player.reload(resolved)
        else:
            view = game.scene
            hp = view.battle.unit(target).hp
            player.press('f1' if interruption == 'help' else 'f6')
            game.tick(3)
            assert view.battle.unit(target).hp == hp
            assert cues(game) == ['attack_arrow']
            player.press('escape')
            assert game.scene is view
        game.tick(3)
        assert isinstance(game.scene, ResultScene)
        expected_cues = ['attack_arrow'] if interruption == 'load' else ['attack_arrow', 'attack_hit', 'victory']
        assert cues(game) == expected_cues
        assert player.state.to_json() == resolved
        player.press('e')
        assert player.state.battle is None and player.state.provinces[player.state.hero.pos].explored
    finally:
        game.close()


@pytest.mark.parametrize('finish', ['skip', 'skip_after_contact', 'coarse_update', 'crossed_contact'])
def test_finishing_the_last_shot_preserves_one_contact_before_one_result(tmp_path, finish):
    """Skipping or a long frame cannot erase the earned hit cue or duplicate the fanfare."""
    state, (actor, target) = earned_last_arrow()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        game.tick(1 / 60)
        player = PlayerInput(game, finish_actions=False)
        player.order('battle.attack', actor, target)
        resolved = state.to_json()
        if finish == 'skip_after_contact':
            game.tick(.45)
        elif finish == 'crossed_contact':
            game.tick(.9)
            assert cues(game) == ['attack_arrow', 'attack_hit']
        if finish.startswith('skip'):
            player.press('space')
        else:
            game.tick(3)
        assert isinstance(game.scene, ResultScene)
        assert cues(game) == ['attack_arrow', 'attack_hit', 'victory']
        game.tick(3)
        assert cues(game) == ['attack_arrow', 'attack_hit', 'victory']
        assert state.to_json() == resolved
    finally:
        game.close()


def test_final_bolt_uses_its_magic_contact_before_victory(tmp_path):
    """Keeping the Wizard's order instead of Healing earns a legal spell finisher in the same opening."""
    state = before_second_round_orders()
    battle = state.battle
    target = next(unit for unit in battle.units if unit.team == 'enemy' and unit.alive)
    militia = next(unit for unit in battle.units if unit.team == 'player' and unit.kind == 'militia')
    destination = min(pos for pos in battle.reachable(militia.id) if battle.grid.distance(pos, target.pos) == 1)
    battle.move(militia.id, destination)
    battle.attack(militia.id, target.id)
    archer = next(unit for unit in battle.units if unit.team == 'player' and unit.can_pin)
    battle.attack(archer.id, target.id)
    expected = State.from_json(state.to_json())
    expected.battle.cast('bolt', target.id)
    assert expected.battle.outcome == 'player'
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        game.tick(1 / 60)
        player = PlayerInput(game, finish_actions=False)
        player.order('battle.cast', 'bolt', target.id)
        assert isinstance(game.scene, BattleScene)
        assert cues(game) == []
        assert state.to_json() == expected.to_json()
        game.tick(.5)
        assert cues(game) == ['bolt']
        game.tick(3)
        assert isinstance(game.scene, ResultScene)
        assert cues(game) == ['bolt', 'victory']
    finally:
        game.close()


def test_final_pin_follows_an_actual_bolt_and_preserves_its_cost(tmp_path):
    """A softer Pin can finish the Brigand only after spending the Wizard's order and mana."""
    state = before_second_round_orders()
    battle = state.battle
    target = next(unit for unit in battle.units if unit.team == 'enemy' and unit.alive)
    archer = next(unit for unit in battle.units if unit.team == 'player' and unit.can_pin)
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        game.tick(1 / 60)
        player = PlayerInput(game, finish_actions=False)
        player.order('battle.cast', 'bolt', target.id)
        assert battle.outcome is None and target.alive
        expected = State.from_json(state.to_json())
        expected.battle.pin(archer.id, target.id)
        assert expected.battle.outcome == 'player'
        player.order('battle.pin', archer.id, target.id)
        assert isinstance(game.scene, BattleScene)
        assert state.to_json() == expected.to_json()
        assert cues(game) == ['bolt', 'attack_arrow']
        game.tick(3)
        assert isinstance(game.scene, ResultScene)
        assert cues(game) == ['bolt', 'attack_arrow', 'attack_hit', 'victory']
    finally:
        game.close()
