"""Either human army uses the same tactical screen with its own orders and resources."""

from eador.app import create_game
from eador.battle import Battle
from eador.model import State
from eador.scene import BattleScene, ShardScene
import pytest

from saga2d import Button, Scene
from tests.eador.test_game_audio import cues
from tools.eador_ui import PlayerInput


def human_battle(team, *, defender_healer=False):
    """Use two untouched campaign armies and the live root's local-team contract."""
    realms = State.new(7, 'Wizard'), State.new(12, 'Wizard')
    if defender_healer:
        realms[1].end_turn()
        realms[1].build('temple')
        realms[1].recruit('healer')
    battle = Battle.create_duel(realms[0].hero, realms[1].hero, 'plains',
                               realms[0].spells, realms[1].spells)
    local = realms[team == 'enemy']
    local.battle, local.battle_province, local.battle_kind = battle, local.hero.pos, 'human'
    root = ShardScene(local)
    root.battle_team, root.live_match = team, True
    return root


def unit(battle, team, source):
    return next(actor for actor in battle.units if actor.team == team and actor.source_id == source)


def test_defender_waits_then_selects_moves_and_casts_with_its_own_mana(tmp_path):
    """Peer-phase input does nothing; the real handoff enables the defender's own hero Bolt."""
    root = human_battle('enemy')
    battle = root.state.battle
    hero = unit(battle, 'enemy', 0)
    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        game.push(root)
        game.tick(0)
        player = PlayerInput(game)
        scene = game.scene
        assert type(scene) is BattleScene and scene.selected == hero.id
        waiting = scene.ui.find(lambda control: isinstance(control, Button)
                                and control.text == 'Waiting for opponent')
        assert waiting is not None and not waiting.enabled
        player.press('f')
        assert any(actor.pos == scene.cursor and actor.team == 'player' for actor in battle.units)
        before = battle.to_dict()
        for key in ('e', 'a', 'g', '1', '2', 't', 'return'):
            player.press(key)
            assert battle.to_dict() == before and game.scene is scene

        # The network supplies an accepted, already-resolved peer trace.
        trace = battle.trace(battle.end_turn)
        scene.begin_playback(trace)
        player.finish_playback()
        assert battle.active_team == 'enemy'
        phase = scene.ui.find(lambda control: isinstance(control, Button) and control.text == 'End phase')
        assert phase is not None and phase.enabled
        assert scene.ui.find(lambda control: isinstance(control, Button)
                             and control.text == 'Auto-play one round') is None

        expected = Battle.from_dict(battle.to_dict())
        militia = unit(battle, 'enemy', 1)
        target = unit(battle, 'player', 3)
        expected.move(militia.id, (1, 0))
        expected.move(hero.id, (1, 1))
        expected.cast('bolt', target.id, caster_id=hero.id)
        player.order('battle.move', militia.id, (1, 0))
        player.order('battle.move', hero.id, (1, 1))
        player.order('battle.cast', 'bolt', target.id, caster_id=hero.id)
        assert battle.to_dict() == expected.to_dict()
        assert battle.mana == before['mana']
        assert battle.enemy_magic.mana == root.state.hero.mana - 4
        assert scene.selected == hero.id
    finally:
        game.close()


def test_paid_defender_acolyte_heals_its_own_hero_then_another_ally_guards(tmp_path):
    """A genuinely funded fifth ally spends its own order and mana, leaving its hero ready."""
    root = human_battle('enemy', defender_healer=True)
    battle = root.state.battle
    attacker, defender = unit(battle, 'player', 0), unit(battle, 'enemy', 0)
    battle.move(unit(battle, 'player', 1).id, (-1, 0))
    battle.move(attacker.id, (-1, -1))
    battle.cast('bolt', defender.id)
    battle.end_turn()
    healer = next(actor for actor in battle.units if actor.team == 'enemy' and actor.can_heal)
    expected = Battle.from_dict(battle.to_dict())
    expected.cast('heal', defender.id, caster_id=healer.id)
    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        game.push(root)
        game.tick(0)
        player = PlayerInput(game)
        assert any('5 allies · 4 foes' in text['text'] for text in game.backend.texts)
        player.order('battle.cast', 'heal', defender.id, caster_id=healer.id)
        assert battle.to_dict() == expected.to_dict()
        assert healer.acted and not defender.acted
        assert defender.hp == defender.max_hp
        expected.guard(defender.id)
        player.order('battle.guard', defender.id)
        assert battle.to_dict() == expected.to_dict()
        player.press('tab')
        assert battle.unit(game.scene.selected).team == 'enemy'
    finally:
        game.close()


@pytest.mark.parametrize('team,ending', [('player', 'defeat'), ('enemy', 'victory')])
def test_last_human_bolt_finishes_before_the_local_result_callback(tmp_path, team, ending):
    """Three real Bolts defeat the attacker; both perspectives get their own result once."""
    from eador.battle_playback_scene import BattlePlaybackScene
    root = human_battle(team)
    battle = root.state.battle
    attacker, defender = unit(battle, 'player', 0), unit(battle, 'enemy', 0)
    battle.end_turn()
    battle.move(unit(battle, 'enemy', 1).id, (1, 0))
    battle.move(defender.id, (1, 1))
    for _ in range(2):
        battle.cast('bolt', attacker.id, caster_id=defender.id)
        battle.end_turn()
        battle.end_turn()
    expected = Battle.from_dict(battle.to_dict())
    expected.cast('bolt', attacker.id, caster_id=defender.id)
    result = Scene()
    game = create_game(backend='mock', save_dir=tmp_path)
    root.show_battle_result = lambda: game.push(result)
    try:
        game.push(root)
        game.tick(0)
        game.backend.sounds_played.clear()
        if team == 'enemy':
            PlayerInput(game, finish_actions=False).order('battle.cast', 'bolt', attacker.id, caster_id=defender.id)
        else:
            trace = battle.trace(lambda: battle.cast('bolt', attacker.id, caster_id=defender.id))
            game.scene.begin_playback(trace)
            game.tick(0)
        assert isinstance(game.scene, BattlePlaybackScene)
        assert battle.to_dict() == expected.to_dict() and battle.outcome == 'enemy'
        game.tick(3)
        assert game.scene is result
        assert cues(game)[-1] == ending and cues(game).count(ending) == 1
        game.tick(3)
        assert battle.to_dict() == expected.to_dict() and cues(game).count(ending) == 1
    finally:
        game.close()


def test_defender_playback_observes_the_recorded_handoff_and_own_spell_pool(tmp_path):
    """Resolved peer/own traces animate their recorded phase and mana without changing authority."""
    from eador.battle_playback_scene import BattlePlaybackScene
    root = human_battle('enemy')
    battle = root.state.battle
    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        game.push(root)
        game.tick(0)
        scene = game.scene
        handoff = battle.trace(battle.end_turn)
        after_handoff = battle.to_dict()
        scene.begin_playback(handoff)
        game.tick(0)
        assert isinstance(game.scene, BattlePlaybackScene)
        assert game.scene.battle.active_team == handoff.before.active_team
        game.tick(.41)
        assert game.scene.battle.active_team == handoff.after.active_team
        assert battle.to_dict() == after_handoff
        game.tick(.4)
        assert game.scene is scene

        hero = unit(battle, 'enemy', 0)
        battle.move(unit(battle, 'enemy', 1).id, (1, 0))
        battle.move(hero.id, (1, 1))
        shot = battle.trace(lambda: battle.cast('bolt', unit(battle, 'player', 3).id, caster_id=hero.id))
        after_shot = battle.to_dict()
        scene.begin_playback(shot)
        game.tick(0)
        assert game.scene.battle.enemy_magic.mana == shot.before.enemy_mana
        assert any('Your Hero:' in text['text'] for text in game.backend.texts)
        game.tick(.41)
        assert game.scene.battle.enemy_magic.mana == shot.after.enemy_mana
        assert battle.to_dict() == after_shot
        game.tick(.4)
        assert game.scene is scene and battle.to_dict() == after_shot
    finally:
        game.close()
