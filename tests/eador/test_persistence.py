"""Campaign save policy exercised against real temporary save files."""

import json

import pytest

from saga2d import SaveError, SaveManager
from eador.model import State
from eador.persistence import AUTO_SLOTS, CampaignSaves


def test_rolling_autosaves_preserve_manual_progress_and_latest_states(tmp_path):
    """Repeated checkpoints retain the latest three turns without touching a manual save."""
    saves = CampaignSaves(SaveManager(tmp_path))
    state = State.new(7)
    saves.save(state, 1)
    manual = (tmp_path / "save_1.json").read_bytes()
    snapshots = []
    for _ in range(6):
        state.end_turn()
        saves.autosave(state)
        snapshots.append(state.to_json())
    assert (tmp_path / "save_1.json").read_bytes() == manual
    assert {saves.load(slot).to_json() for slot in AUTO_SLOTS} == set(snapshots[-3:])
    assert saves.load(1).turn == 1


def test_damaged_campaign_does_not_hide_other_slots_or_destroy_recovery(tmp_path):
    """The game validates its own payload and offers explicit previous-file recovery."""
    manager = SaveManager(tmp_path)
    saves = CampaignSaves(manager)
    state = State.new(7)
    saves.save(state, 1)
    state.end_turn()
    saves.save(state, 1)
    saves.save(state, 2)
    damaged = json.loads(state.to_json())
    damaged["schema_version"] = 1000
    manager.save(1, {"campaign": json.dumps(damaged)}, "ShardScene")
    original = (tmp_path / "save_1.json").read_bytes()

    with pytest.raises(SaveError, match="Cannot open this campaign"):
        saves.load(1)
    with pytest.raises(SaveError, match="Cannot open this campaign"):
        saves.save(state, 1)
    entries = saves.entries()
    assert entries[0].error
    assert entries[0].backup_available
    assert not entries[1].error
    assert saves.load(1, backup=True).to_json() == state.to_json()
    saves.autosave(state)
    assert (tmp_path / "save_1.json").read_bytes() == original


def test_autosaves_preserve_damaged_files_and_report_exhausted_rotation(tmp_path):
    saves = CampaignSaves(SaveManager(tmp_path))
    state = State.new(7)
    for slot in AUTO_SLOTS[:2]:
        (tmp_path / f"save_{slot}.json").write_text("incomplete file")
    assert saves.autosave(state) == AUTO_SLOTS[2]
    state.end_turn()
    assert saves.autosave(state) == AUTO_SLOTS[2]
    for slot in AUTO_SLOTS:
        (tmp_path / f"save_{slot}.json").write_text("incomplete file")
    with pytest.raises(SaveError, match="All autosave slots are damaged"):
        saves.autosave(state)
    assert all((tmp_path / f"save_{slot}.json").read_text() == "incomplete file" for slot in AUTO_SLOTS)
