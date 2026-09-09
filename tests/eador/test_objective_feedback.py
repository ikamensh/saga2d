"""Recorded seal progress becomes feedback without participating in battle rules."""

from functools import lru_cache
import gzip
import json
from pathlib import Path
import pytest

from eador.app import create_game
from eador.battle_playback_scene import BattlePlaybackScene
from eador.model import State
from eador.preferences import DEFAULTS
from eador.scene import BattleScene, ShardScene
from eador.style import TEAL
from saga2d import Settings
from tests.eador.test_game_audio import cues
from saga2d.testing.cpu_budget import CpuBudget
from tools.eador_ui import PlayerInput


@lru_cache(maxsize=1)
def recorded_seal_states():
    """Use retained earned saves; the historical party preparation included autoplay."""
    path = Path(__file__).resolve().parents[2] / 'docs/evidence/relief-c6093de/model-orders.json.gz'
    with gzip.open(path, 'rt') as stream:
        snapshots = json.load(stream)['plans']['standard/7/Commander/passive']['snapshots']
    return tuple(json.dumps(snapshots[index]) for index in (13, 14, 21))


def watch_progress(game, value):
    """Observe at most the existing eight-second playback, cooperatively paced."""
    budget = CpuBudget()
    for _ in range(170):
        if game.scene.battle.objective.progress == value:
            return
        assert isinstance(game.scene, BattlePlaybackScene)
        game.tick(.05)
        budget.checkpoint()
    raise AssertionError('Seal progress was not presented within the playback bound.')


@pytest.mark.parametrize('still', [False, True])
def test_earned_seal_gain_is_announced_once_through_input_refresh_skip_and_load(tmp_path, still):
    """A real scoring enemy phase emits one progress cue and keeps every resolved save exact."""
    state = State.from_json(recorded_seal_states()[0])
    expected = State.from_json(state.to_json())
    expected.battle.end_turn()
    assert expected.battle.objective.progress == 1 and expected.battle.outcome is None
    prefs = Settings(tmp_path / 'settings.json', DEFAULTS)
    prefs['reduced_motion'] = still
    prefs.save()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(0)
        player = PlayerInput(game, finish_actions=False)
        player.press('e')
        assert type(game.scene) is BattlePlaybackScene
        assert player.state.to_json() == expected.to_json()
        watch_progress(game, 1)
        assert cues(game).count('seal_gain') == 1
        def seal_ring():
            return [(line['x1'], line['y1'], line['x2'], line['y2']) for line in game.backend.lines
                    if line['color'][:3] == TEAL[:3] and line['width'] == 3.5]
        ring = seal_ring()
        assert len(ring) == 16, 'The scoring seal needs a complete ring below its occupying unit.'
        cx, cy = game.scene.grid.center(game.scene.battle.objective.target)
        holder = next(unit for unit in game.scene.battle.units if unit.alive
                      and unit.pos == game.scene.battle.objective.target)
        health = next(text for text in game.backend.texts if text['text'] == str(holder.hp)
                      and abs(text['x'] - cx) < .01 and abs(text['y'] - cy - game.scene.grid.size * .23) < .01)
        assert all(line['order'] < health['order'] for line in game.backend.lines
                   if line['color'][:3] == TEAL[:3] and line['width'] == 3.5)
        game.tick(.04)
        assert (seal_ring() == ring) == still
        game.scene.refresh(); game.tick(0)
        assert cues(game).count('seal_gain') == 1
        player.press('space'); game.tick(1.5)
        assert type(game.scene) is BattleScene
        assert player.state.to_json() == expected.to_json()
        player.reload(expected.to_json()); game.tick(1.5)
        assert cues(game).count('seal_gain') == 1
        assert player.state.to_json() == expected.to_json()
    finally:
        game.close()


def test_leaving_earned_seal_announces_loss_once_and_unchanged_zero_stays_silent(tmp_path):
    """Open the paid enclosure and move its real holder away; only the resulting lost progress sounds."""
    state = State.from_json(recorded_seal_states()[1])
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(0)
        player = PlayerInput(game, finish_actions=False)
        for ident, destination in ((5, (-2, -1)), (2, (-1, -1))):
            assert destination in player.state.battle.reachable(ident)
            player.order('battle.move', ident, destination)
        expected = State.from_json(player.state.to_json())
        expected.battle.end_turn()
        assert expected.battle.objective.progress == 0 and expected.battle.outcome is None
        player.press('e')
        watch_progress(game, 0)
        assert cues(game).count('seal_loss') == 1 and 'seal_gain' not in cues(game)
        game.scene.refresh(); game.tick(0)
        player.press('space')
        player.reload(expected.to_json())
        expected.battle.end_turn()
        assert expected.battle.objective.progress == 0 and expected.battle.outcome is None
        player.press('e')
        budget = CpuBudget()
        for _ in range(90):
            if type(game.scene) is BattleScene:
                break
            game.tick(.1); budget.checkpoint()
        assert type(game.scene) is BattleScene
        assert cues(game).count('seal_loss') == 1 and 'seal_gain' not in cues(game)
        assert player.state.to_json() == expected.to_json()
    finally:
        game.close()


@pytest.mark.parametrize('transition', ['skip', 'reload', 'terminal'])
def test_unseen_or_terminal_progress_never_adds_a_late_nonterminal_sting(tmp_path, transition):
    """Skipping/loading cancels the viewing period; a completed seal keeps its existing victory cue."""
    from eador.scene import ResultScene
    state = State.from_json(recorded_seal_states()[2 if transition == 'terminal' else 0])
    expected = State.from_json(state.to_json())
    expected.battle.end_turn()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(0)
        player = PlayerInput(game, finish_actions=False)
        player.press('e')
        if transition == 'reload':
            player.reload(expected.to_json())
        elif transition == 'skip':
            player.press('space')
        else:
            budget = CpuBudget()
            for _ in range(90):
                if type(game.scene) is ResultScene:
                    break
                game.tick(.1); budget.checkpoint()
            assert type(game.scene) is ResultScene
            assert expected.battle.outcome_reason == 'hold'
            assert cues(game).count('victory') == 1
        game.tick(1.5)
        assert not {'seal_gain', 'seal_loss'}.intersection(cues(game))
        assert player.state.to_json() == expected.to_json()
    finally:
        game.close()
