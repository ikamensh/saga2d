"""The paced reliability journey must exercise the same controls as a player."""
from eador.app import create_game
from eador.battle_playback_scene import BattlePlaybackScene
from eador.scene import TitleScene
from tools.eador_ui import PlayerInput
from tools.soak_eador import Journey


def test_soak_journeys_watch_resolved_turns_and_return_to_title(tmp_path):
    """Four heroes and both reading sizes finish without counting ignored playback keys as orders."""
    game = create_game(backend='mock', save_dir=tmp_path)
    player = PlayerInput(game, finish_actions=False)
    game.push(TitleScene(7)); game.tick(1 / 60)
    journey = Journey(game)
    watched = 0
    try:
        for _ in range(6000):
            kind, value = next(journey.steps)
            if journey.cycles == 4:
                break
            if kind == 'restart':
                game.clear_and_push(TitleScene(value)); game.tick(1 / 60)
            elif kind == 'key':
                if value in ('A', 'E'):
                    assert not isinstance(game.scene, BattlePlaybackScene), 'Soak issued a battle order during playback'
                player.press('return' if value == 'ENTER' else value.removeprefix('_').lower())
            elif kind == 'click':
                player.click(*value)
            elif kind == 'button':
                player.button(value)
            else:
                assert kind == 'wait' and isinstance(game.scene, BattlePlaybackScene)
                saved = player.state.to_json()
                game.tick(.25)
                assert player.state.to_json() == saved, 'Watching changed the already-resolved turn'
                watched += 1
        else:
            raise AssertionError('The paced soak journey did not complete four openings')
        assert isinstance(game.scene, TitleScene)
        assert watched > 0
        assert journey.counts['battles_resolved'] == 8
        assert journey.counts['browser_save_load'] == 4
        assert journey.counts['reading_100'] == journey.counts['reading_125'] == 2
        assert all(journey.counts['hero_' + hero] == 1 for hero in ('Commander', 'Warrior', 'Scout', 'Wizard'))
    finally:
        game._teardown()
