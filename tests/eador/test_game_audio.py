"""Game events use shipped audio through one manager, with preferences applied before playback."""

from eador.app import create_game
from eador.scene import BattleScene, ChoiceScene, ResultScene, ShardScene, TitleScene
from eador.preferences import DEFAULTS
from eador.sound import CUES
from saga2d import Settings


def press(game, name):
    from tools.eador_ui import PlayerInput
    PlayerInput(game).press(name)


def cues(game):
    names = {game.assets.sound(name): name for name in CUES}
    return [names[record['handle']] for record in game.backend.sounds_played]


def test_music_cues_muting_and_saved_results_follow_player_events(tmp_path):
    """Settings govern first playback; overlays preserve music; loading never replays earned cues."""
    prefs = Settings(tmp_path / 'settings.json', DEFAULTS)
    prefs['master'], prefs['music'], prefs['sfx'] = .5, .4, .3
    prefs.save()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(TitleScene())
        game.tick(1 / 60)
        assert game.audio.music_name == 'campaign'
        assert game.backend.music_volume == .2
        press(game, 'o')
        same_player = game.backend.music_playing
        press(game, 'escape')
        assert game.backend.music_playing == same_player
        press(game, 'return')
        for name in ('b', '1', 'escape', 'r', '2', 'escape', 'x'):
            press(game, name)
        assert isinstance(game.scene, BattleScene) and game.audio.music_name == 'battle'
        assert 'confirm' in cues(game)
        press(game, 'g')
        assert cues(game)[-1] == 'guard'
        assert abs(game.backend.sounds_played[-1]['volume'] - .15) < 1e-8
        count = len(cues(game))
        press(game, 'g')  # The disabled order consumes its shortcut without playing a success cue.
        assert len(cues(game)) == count
        for _ in range(50):
            if isinstance(game.scene, ResultScene):
                break
            press(game, 'a')
        assert isinstance(game.scene, ResultScene)
        assert game.audio.music_name is None and cues(game)[-1] == 'victory'
        press(game, 'f5')
        count = len(cues(game))
        press(game, 'f9')
        assert isinstance(game.scene, ResultScene) and len(cues(game)) == count
        press(game, 'e')
        while isinstance(game.scene, ChoiceScene):
            press(game, '1')
        assert isinstance(game.scene, ShardScene) and game.audio.music_name == 'campaign'
        assert 'reward' in cues(game)
        game.audio.muted = True
        count = len(cues(game))
        press(game, 'e')
        assert len(cues(game)) == count
    finally:
        game._teardown()
    assert not game.backend.sounds_playing and game.backend.music_playing is None


def test_successful_move_hit_and_spells_have_their_own_cues(tmp_path):
    """Actual tactics route their successful effects once; a disabled spent order stays silent."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')

    def click(pos):
        x, y = game.scene.grid.center(pos)
        game.backend.inject_click(round(x), round(y))
        game.backend.inject_release(round(x), round(y))
        game.tick(1 / 60)

    try:
        game.push(TitleScene(hero_class='Wizard'))
        press(game, 'return')
        press(game, 'x')
        battle = game.scene.battle
        archer = next(unit for unit in battle.units if unit.team == 'player' and unit.can_pin)
        click(archer.pos)
        click((-1, 0))
        assert cues(game)[-1] == 'move'
        target = battle.targets(archer.id)[0]
        click(target.pos)
        assert cues(game)[-1] == 'attack_arrow'
        press(game, 'e')
        target = next(unit for unit in battle.units if unit.team == 'enemy' and unit.alive
                      and battle.grid.distance(battle.unit(0).pos, unit.pos) <= 4)
        press(game, '1')
        click(target.pos)
        assert cues(game)[-1] == 'bolt'
        press(game, 'e')
        wounded = next(unit for unit in battle.units if unit.team == 'player' and 0 < unit.hp < unit.max_hp
                       and battle.grid.distance(battle.unit(0).pos, unit.pos) <= 4)
        press(game, '2')
        click(wounded.pos)
        assert cues(game)[-1] == 'heal'
        # The spent caster's disabled Heal shortcut retains state and stays silent.
        before = game.scene.root.state.to_json()
        count = len(cues(game))
        press(game, '2')
        click(wounded.pos)
        assert game.scene.root.state.to_json() == before and len(cues(game)) == count
    finally:
        game._teardown()
