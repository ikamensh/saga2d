"""Completed matches through the local high-score store, including fresh sessions."""

from tribes import mapgen
from tribes.model import World
from tribes.scores import HighScores


def test_completed_match_survives_reopening_without_duplicate_scores(tmp_path) -> None:
    """Revisiting results or loading a save records one best result for the same run."""
    world = mapgen.generate(seed=7, size=11, tribe_count=2)
    world.winner = 0
    world.round = 15
    board = HighScores(tmp_path)
    assert board.record(world, tribe=0, seed=7, run_id="one-match") == 1
    first = board.load()
    assert len(first) == 1
    assert first[0].score == sum(world.score_breakdown(0, final=True).values())

    reopened = HighScores(tmp_path)
    assert reopened.record(World.from_dict(world.to_dict()), tribe=0, seed=7, run_id="one-match") == 1
    assert reopened.load() == first
    world.round = 16  # a worse alternate finish must not replace the best
    reopened.record(world, tribe=0, seed=7, run_id="one-match")
    assert reopened.load() == first


def test_boards_keep_ten_best_per_configuration_and_reject_unfinished_games(tmp_path) -> None:
    """A larger map cannot evict small-map records; unfinished and low scores cannot enter."""
    import pytest
    from tribes.model import RuleError

    board = HighScores(tmp_path)
    world = mapgen.generate(seed=7, size=11, tribe_count=2)
    with pytest.raises(RuleError, match="not over"):
        board.record(world, tribe=0, seed=7, run_id="unfinished")
    assert board.load() == []
    world.winner = 0
    for i in range(12):
        world.round = 20 - i
        board.record(world, tribe=0, seed=i, run_id=f"small-{i}")
    large = mapgen.generate(seed=8, size=18, tribe_count=4)
    large.winner = 1  # losses still get an honest score and outcome
    board.record(large, tribe=0, seed=8, run_id="large")
    entries = HighScores(tmp_path).load()
    small = [e for e in entries if e.size == 11]
    assert len(small) == 10
    assert [e.score for e in small] == sorted((e.score for e in small), reverse=True)
    assert small[0].run_id == "small-11"
    assert len(entries) == 11
    assert next(e for e in entries if e.run_id == "large").victory is False
    world.round = 30
    assert board.record(world, tribe=0, seed=20, run_id="below-cutoff") is None


def test_damaged_or_unknown_score_files_are_reported_and_never_overwritten(tmp_path) -> None:
    """Corruption must be visible; recording a new win must preserve the broken file."""
    import pytest
    from saga2d import SaveError, SaveManager

    world = mapgen.generate(seed=7, size=11, tribe_count=2)
    world.winner = 0
    path = tmp_path / "high_scores" / "save_1.json"
    saves = SaveManager(path.parent)
    saves.save(1, {"version": 99, "entries": []}, "TribesHighScores")
    for content in (path.read_text(), "{broken"):
        path.write_text(content)
        with pytest.raises(SaveError):
            HighScores(tmp_path).load()
        with pytest.raises(SaveError):
            HighScores(tmp_path).record(world, tribe=0, seed=7, run_id="new-win")
        assert path.read_text() == content
