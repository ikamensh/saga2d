"""Campaign save policy, separate from Saga2D's safe file I/O.

The game decides what a snapshot means, which slots are manual, and when
to checkpoint. The framework owns writing, validation of the file envelope,
and retention of the previous file. Failed loads never replace live state.
"""

from dataclasses import dataclass

from saga2d import SaveError, SaveManager

from eador.model import SaveFormatError, State

MANUAL_SLOTS = (1, 2, 3)
AUTO_SLOTS = (10, 11, 12)
_PHASE_LABELS = {"departure": "Next challenge", "recovery": "Recovery available",
                 "lost": "Campaign lost", "completed": "Campaign completed"}


@dataclass(frozen=True)
class SaveEntry:
    slot: int
    label: str
    detail: str
    timestamp: str = ""
    exists: bool = False
    error: str = ""
    backup_available: bool = False
    backup_error: str = ""


class CampaignSaves:
    """Three manual slots and three rolling autosaves in a SaveManager."""

    def __init__(self, manager: SaveManager):
        self.manager = manager

    def save(self, state: State, slot: int = 1) -> None:
        if slot not in MANUAL_SLOTS:
            raise ValueError("Choose a manual save slot: 1, 2 or 3.")
        # The envelope can be valid while its game schema is incompatible.
        # Preserve that file and its last usable backup until recovery is explicit.
        self.load(slot)
        self._write(state, slot)

    def _write(self, state: State, slot: int) -> None:
        self.manager.save(slot, {"campaign": state.to_json()}, "ShardScene")

    def load(self, slot: int = 1, *, backup: bool = False) -> State | None:
        payload = self.manager.load_backup(slot) if backup else self.manager.load(slot)
        return self._decode(payload)

    @staticmethod
    def _decode(payload) -> State | None:
        if payload is None:
            return None
        if payload["scene_class"] != "ShardScene" or not isinstance(payload["state"].get("campaign"), str):
            raise SaveError("This slot does not contain a Shardbound campaign.")
        try:
            return State.from_json(payload["state"]["campaign"])
        except SaveFormatError as error:
            raise SaveError(f"Cannot open this campaign: {error}") from error

    def entries(self, *, autosaves_only: bool = False) -> list[SaveEntry]:
        entries = []
        for slot in AUTO_SLOTS if autosaves_only else MANUAL_SLOTS + AUTO_SLOTS:
            label = f"Manual {slot}" if slot in MANUAL_SLOTS else f"Autosave {slot - AUTO_SLOTS[0] + 1}"
            backup = False
            backup_error = ""
            if not autosaves_only:
                try:
                    backup = self.load(slot, backup=True) is not None
                except SaveError as error:
                    backup_error = str(error)
            try:
                metadata = self.manager.load(slot)
                state = self._decode(metadata)
                if state is None:
                    entries.append(SaveEntry(slot, label, "Empty slot", backup_available=backup,
                                             backup_error=backup_error))
                    continue
                detail = f"{state.rules.title} · Turn {state.turn} · {state.hero.hero_class} · Shard {state.seed}"
                if state.campaign is not None:
                    detail = f"Stage {state.campaign.stage}/3 · {state.campaign.title} · {detail}"
                if state.battle is not None:
                    detail += f" · Battle round {state.battle.round}"
                elif state.choice is not None:
                    detail += " · Decision pending"
                elif state.campaign is not None and state.campaign.phase in _PHASE_LABELS:
                    detail += f" · {_PHASE_LABELS[state.campaign.phase]}"
                elif state.status != "playing":
                    detail += f" · {state.status.title()}"
                entries.append(SaveEntry(slot, label, detail, metadata["timestamp"], True,
                                         backup_available=backup, backup_error=backup_error))
            except SaveError as error:
                entries.append(SaveEntry(slot, label, "Cannot read this save", exists=True,
                                         error=str(error), backup_available=backup, backup_error=backup_error))
        return entries

    def checkpoint(self, state: State) -> int:
        """Return the slot preserving this exact state before a campaign transition.

        Prefer a new rolling autosave. If that fails, an already saved, current
        manual slot may satisfy the checkpoint instead. Only a validated full
        state match counts; stale, unrelated or backup snapshots never do.
        Failed reads stay untouched and cannot hide the original autosave error.
        """
        try:
            return self.autosave(state)
        except SaveError:
            expected = state.to_json()
            for slot in MANUAL_SLOTS:
                try:
                    saved = self.load(slot)
                except SaveError:
                    continue
                if saved is not None and saved.to_json() == expected:
                    return slot
            raise

    def autosave(self, state: State) -> int:
        """Rotate only autosave slots; manual or damaged files stay untouched."""
        entries = [entry for entry in self.entries(autosaves_only=True) if not entry.error]
        if not entries:
            raise SaveError("All autosave slots are damaged. Your manual saves are intact; choose a manual slot.")
        entry = min(entries, key=lambda item: (item.exists, item.timestamp, item.slot))
        self._write(state, entry.slot)
        return entry.slot
