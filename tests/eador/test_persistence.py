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


def test_checkpoint_accepts_only_an_exact_current_manual_when_autosaves_fail(tmp_path):
    """A manual checkpoint unblocks a transition only for the complete state actually saved."""
    saves = CampaignSaves(SaveManager(tmp_path))
    state = State.new_campaign(7)
    assert saves.checkpoint(state) in AUTO_SLOTS
    for slot in AUTO_SLOTS:
        (tmp_path / f"save_{slot}.json").write_bytes(b"{broken autosave")
    with pytest.raises(SaveError, match="All autosave slots are damaged"):
        saves.checkpoint(state)
    saves.save(State.new_campaign(8), 1)
    saves.save(state, 2)
    snapshots = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    assert saves.checkpoint(state) == 2
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == snapshots
    state.end_turn()
    with pytest.raises(SaveError, match="All autosave slots are damaged"):
        saves.checkpoint(state)
    saves.save(state, 3)
    assert saves.checkpoint(state) == 3
    assert all((tmp_path / f"save_{slot}.json").read_bytes() == b"{broken autosave" for slot in AUTO_SLOTS)


def test_checkpoint_rejects_matching_backup_and_skips_damaged_manual_slots(tmp_path):
    """A previous version is not permission to leave; a separate current exact save is."""
    saves = CampaignSaves(SaveManager(tmp_path))
    state = State.new_campaign(7)
    saves.save(state, 1)
    saves.save(State.new_campaign(8), 1)
    assert saves.load(1, backup=True).to_json() == state.to_json()
    for slot in (*AUTO_SLOTS, 2):
        (tmp_path / f"save_{slot}.json").write_bytes(b"corrupted current file")
    with pytest.raises(SaveError, match="All autosave slots are damaged"):
        saves.checkpoint(state)
    saves.save(state, 3)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    assert saves.checkpoint(state) == 3
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before


def test_checkpoint_preserves_actual_write_error_until_matching_manual_is_saved(tmp_path):
    """A failed backup write retains its original error and every existing snapshot."""
    saves = CampaignSaves(SaveManager(tmp_path))
    state = State.new_campaign(7)
    for _ in AUTO_SLOTS:
        saves.autosave(state)
    (tmp_path / 'save_10.backup.json').mkdir()
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir() if path.is_file()}
    with pytest.raises(SaveError) as original:
        saves.autosave(state)
    with pytest.raises(SaveError) as refused:
        saves.checkpoint(state)
    assert str(refused.value).startswith("Cannot write save file for slot 10")
    assert isinstance(refused.value.__cause__, OSError)
    assert refused.value.__cause__.errno == original.value.__cause__.errno
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir() if path.is_file()} == before
    saves.save(state, 2)
    assert saves.checkpoint(state) == 2
    assert {name: (tmp_path / name).read_bytes() for name in before} == before
