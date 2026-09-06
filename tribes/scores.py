"""Local match records, kept separately from quick saves and preferences."""

from dataclasses import asdict, dataclass
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from saga2d import SaveError, SaveManager
from tribes.model import World
from tribes.rules import MAX_ROUNDS


@dataclass(frozen=True)
class ScoreEntry:
    run_id: str
    tribe: str
    score: int
    rounds: int
    size: int
    tribes: int
    seed: int
    victory: bool
    completed_at: str

    def __post_init__(self) -> None:
        for name in ("score", "rounds", "size", "tribes", "seed"):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"High-score {name} must be an integer")
        if self.score < 0 or not 1 <= self.rounds <= MAX_ROUNDS or self.size < 1 or self.tribes < 2:
            raise ValueError("Invalid high-score match values")
        for name in ("run_id", "tribe", "completed_at"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"High-score {name} must be nonempty text")
        if type(self.victory) is not bool:
            raise ValueError("High-score victory must be a boolean")
        datetime.fromisoformat(self.completed_at)


class HighScores:
    """One best finish per run; the ten highest scores per map size / tribe count.

    Equal scores prefer fewer rounds, then the earlier recorded finish. The
    framework supplies atomic file replacement and a previous-file backup.
    """

    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "high_scores" / "save_1.json"
        self.saves = SaveManager(self.path.parent)

    def load(self) -> list[ScoreEntry]:
        saved = self.saves.load(1)
        if saved is None:
            return []
        try:
            state = saved["state"]
            if type(state["version"]) is not int or state["version"] != 1:
                raise ValueError("Unsupported high-score version; expected 1")
            if not isinstance(state["entries"], list):
                raise ValueError("High-score entries must be a list")
            entries = [ScoreEntry(**entry) for entry in state["entries"]]
            if len({e.run_id for e in entries}) != len(entries):
                raise ValueError("Duplicate high-score run IDs")
            return sorted(entries, key=self._order)
        except (KeyError, TypeError, ValueError) as error:
            raise SaveError(f"Cannot read high scores at {self.path}: {error}") from error

    def record(self, world: World, *, tribe: int, seed: int, run_id: str) -> int | None:
        points = world.score_breakdown(tribe, final=True)
        entry = ScoreEntry(run_id, world.tribes[tribe].name, sum(points.values()), min(world.round, MAX_ROUNDS),
                           world.size, len(world.tribes), seed, world.winner == tribe,
                           datetime.now(timezone.utc).isoformat())
        entries = self.load()
        original = entries
        previous = next((e for e in entries if e.run_id == run_id), None)
        if previous is None or self._order(entry) < self._order(previous):
            entries = [e for e in entries if e.run_id != run_id] + [entry]
            entries.sort(key=self._order)
            counts: Counter[tuple[int, int]] = Counter()
            kept = []
            for candidate in entries:
                board = (candidate.size, candidate.tribes)
                counts[board] += 1
                if counts[board] <= 10:
                    kept.append(candidate)
            entries = kept
            if entries != original:
                self.saves.save(1, {"version": 1, "entries": [asdict(e) for e in entries]}, "TribesHighScores")
        table = [e for e in entries if (e.size, e.tribes) == (entry.size, entry.tribes)]
        return next((i for i, e in enumerate(table, 1) if e.run_id == run_id), None)

    @staticmethod
    def _order(entry: ScoreEntry) -> tuple:
        return (-entry.score, entry.rounds, entry.completed_at, entry.run_id)
