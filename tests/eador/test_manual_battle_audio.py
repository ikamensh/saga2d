"""Accepted player orders finish their recorded sounds without delaying battle rules."""

from eador.app import create_game
from eador.battle import Battle
from eador.model import State
from eador.scene import BattleScene, ShardScene, TitleScene
from tests.eador.test_game_audio import cues
from tools.eador_ui import PlayerInput
import pytest


def test_manual_arrow_plays_one_contact_after_release_without_delaying_rules(tmp_path):
    """A real shot has release and contact; redraws and loading never replay the contact."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(TitleScene(hero_class='Wizard'))
        player = PlayerInput(game, finish_actions=False)
        player.press('return'); player.press('x')
        battle = player.state.battle
        archer = next(unit for unit in battle.units if unit.team == 'player' and unit.can_pin)
        player.order('battle.move', archer.id, (-1, 0))
        target = battle.targets(archer.id)[0]
        expected = State.from_json(player.state.to_json())
        expected.battle.attack(archer.id, target.id)
        game.backend.sounds_played.clear()
        player.order('battle.attack', archer.id, target.id)
        assert type(game.scene) is BattleScene
        assert player.state.to_json() == expected.to_json()
        assert cues(game) == ['attack_arrow']
        game.tick(.2)
        assert cues(game) == ['attack_arrow']
        game.tick(.2)
        assert cues(game) == ['attack_arrow', 'attack_hit']
        game.scene.refresh(); game.tick(1.5)
        assert cues(game) == ['attack_arrow', 'attack_hit']
        assert player.state.to_json() == expected.to_json()
        player.reload(expected.to_json())
        game.tick(1.5)
        assert cues(game).count('attack_hit') == 1
    finally:
        game.close()


@pytest.mark.parametrize('kind,building', [('hero', None), ('adept', 'mage_tower'), ('healer', 'temple')])
@pytest.mark.parametrize('playback', [False, True])
def test_ranged_magic_uses_one_magic_contact_and_no_bowstring(tmp_path, kind, building, playback):
    """A fresh Wizard or paid specialist uses its real ranged weapon in both presentations."""
    from eador.battle_playback_scene import BattlePlaybackScene
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(TitleScene(hero_class='Wizard' if kind == 'hero' else 'Commander', difficulty='accessible'))
        player = PlayerInput(game, finish_actions=False)
        player.press('return')
        player.press('e')  # One real income turn funds the more expensive Tower + Adept pair.
        if building:
            player.order('build', building)
            player.order('recruit', kind)
        player.press('x')
        player.press('e'); player.press('space')  # Let the defenders close through the opening terrain.
        battle = player.state.battle
        actor = next(unit for unit in battle.units if unit.team == 'player' and unit.kind == kind)
        destinations = [(pos, enemy) for pos in sorted(battle.reachable(actor.id) | {actor.pos})
                        for enemy in battle.units if enemy.team == 'enemy' and enemy.alive
                        and battle.grid.distance(pos, enemy.pos) == 2 and battle.has_sight(pos, enemy.pos)]
        assert destinations, 'The fresh army must have a legal two-hex firing position.'
        pos, target = destinations[0]
        if pos != actor.pos:
            player.order('battle.move', actor.id, pos)
        expected = State.from_json(player.state.to_json())
        trace = expected.battle.trace(lambda: expected.battle.attack(actor.id, target.id))
        assert [event.kind for event in trace.events] == ['attack']
        game.backend.sounds_played.clear()
        player.order('battle.attack', actor.id, target.id)
        assert player.state.to_json() == expected.to_json()
        if playback:
            game.push(BattlePlaybackScene(game.scene, trace))
        assert cues(game) == []  # The available magic cue is a complete contact, not a bow release.
        game.tick(.41)
        assert cues(game) == ['bolt']
        game.scene.refresh(); game.tick(0)
        assert cues(game) == ['bolt']
        assert player.state.to_json() == expected.to_json()
    finally:
        game.close()


@pytest.mark.parametrize('kind,enemy,stance,kinds', [
    ('swordsman', 'brigand', None, ['attack', 'retaliation']),
    ('swordsman', 'pikeman', 'brace', ['brace', 'attack']),
    ('archer', 'brigand', None, ['attack', 'retaliation']),
])
def test_manual_attack_plays_every_actual_reaction_contact(tmp_path, kind, enemy, stance, kinds):
    """An authored adjacent arena exposes real Brace/retaliation rules through player clicks."""
    from tests.eador.test_guard import encounter
    state = State.new(); state.explore()
    state.battle = encounter(kind, enemy)
    state.battle.unit(1000).stance = stance
    expected = Battle.from_dict(state.battle.to_dict())
    trace = expected.trace(lambda: expected.attack(0, 1000))
    assert [event.kind for event in trace.events] == kinds
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(0)
        player = PlayerInput(game, finish_actions=False)
        game.backend.sounds_played.clear()
        player.order('battle.attack', 0, 1000)
        assert state.battle.to_dict() == expected.to_dict()
        game.tick(1.5)  # A long frame must drain both actual contacts, not just the latest event.
        assert cues(game) == (['attack_arrow'] if kind == 'archer' else []) + ['attack_hit'] * 2
        game.scene.refresh(); game.tick(1.5)
        assert cues(game).count('attack_hit') == 2
        assert state.battle.to_dict() == expected.to_dict()
    finally:
        game.close()


@pytest.mark.parametrize('next_order,contacts', [('guard', 1), ('end_turn', 1), ('reload', 0), ('retreat', 0)])
def test_pending_contact_finishes_before_next_order_and_cannot_outlive_loaded_or_retreating_scene(
        tmp_path, next_order, contacts):
    """Fast input keeps real rules live; replacing or leaving the scene creates no delayed ghost hit."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(TitleScene(hero_class='Wizard'))
        player = PlayerInput(game, finish_actions=False)
        player.press('return'); player.press('x')
        battle = player.state.battle
        archer = next(unit for unit in battle.units if unit.team == 'player' and unit.can_pin)
        player.order('battle.move', archer.id, (-1, 0))
        target = battle.targets(archer.id)[0]
        game.backend.sounds_played.clear()
        player.order('battle.attack', archer.id, target.id)
        assert cues(game) == ['attack_arrow']
        expected = State.from_json(player.state.to_json())
        if next_order == 'guard':
            expected.battle.guard(0)
            player.order('battle.guard', 0)
            assert cues(game) == ['attack_arrow', 'attack_hit', 'guard']
        elif next_order == 'end_turn':
            expected.battle.end_turn()
            player.press('e')
            assert cues(game)[:3] == ['attack_arrow', 'attack_hit', 'end_turn']
            player.press('space')
        elif next_order == 'reload':
            player.reload(expected.to_json())
        else:
            expected.retreat()
            player.press('t')
            assert cues(game) == ['attack_arrow', 'defeat']
        assert player.state.to_json() == expected.to_json()
        game.tick(1.5)
        assert cues(game).count('attack_hit') == contacts
        assert player.state.to_json() == expected.to_json()
    finally:
        game.close()


@pytest.mark.parametrize('player_hp,enemy,enemy_hp,stance,kind,result', [
    (None, 'brigand', 1, None, 'attack', 'victory'),
    (1, 'pikeman', None, 'brace', 'brace', 'defeat'),
])
def test_terminal_direct_order_contacts_once_before_result_without_inventing_a_lethal_brace_attack(
        tmp_path, player_hp, enemy, enemy_hp, stance, kind, result):
    """A lethal hit or pre-hit spear flushes the one real contact before the terminal result cue."""
    from eador.scene import ResultScene
    from tests.eador.test_guard import encounter
    state = State.new(); state.explore()
    state.battle = encounter('swordsman', enemy, player_hp=player_hp, enemy_hp=enemy_hp)
    state.battle.unit(1000).stance = stance
    expected = Battle.from_dict(state.battle.to_dict())
    trace = expected.trace(lambda: expected.attack(0, 1000))
    assert [event.kind for event in trace.events] == [kind, 'result']
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(0)
        player = PlayerInput(game, finish_actions=False)
        game.backend.sounds_played.clear()
        player.order('battle.attack', 0, 1000)
        assert type(game.scene) is ResultScene
        assert state.battle.to_dict() == expected.to_dict()
        assert cues(game) == ['attack_hit', result]
        game.tick(1.5)
        assert cues(game) == ['attack_hit', result]
    finally:
        game.close()
