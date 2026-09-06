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


def test_linked_save_descriptions_distinguish_progress_and_recovery(tmp_path):
    """A player can identify the linked stage and whether defeat still permits recovery."""
    from tools.eador_linked_campaign import play_stage
    from tools.verify_eador_campaign import lose_shard

    saves = CampaignSaves(SaveManager(tmp_path))
    state = State.new_campaign(7)
    saves.save(state)
    detail = saves.entries()[0].detail
    assert 'Stage 1/3' in detail and 'Westwatch' in detail
    state = play_stage(state)
    saves.save(state)
    detail = saves.entries()[0].detail
    assert 'Next challenge' in detail and 'Victory' not in detail
    state.advance('rootward', troop_ids=(), relic_ids=())
    lose_shard(state)
    saves.save(state)
    detail = saves.entries()[0].detail
    assert 'Stage 2/3' in detail and 'Rootward' in detail and 'Recovery available' in detail
    state.abandon_campaign()
    saves.save(state)
    detail = saves.entries()[0].detail
    assert 'Campaign lost' in detail and 'Recovery available' not in detail


def test_linked_descriptions_keep_battle_decisions_and_completed_ending(tmp_path):
    """Linked context supplements actionable battle/reward details and identifies the true ending."""
    from tools.eador_linked_campaign import play_linked

    saves = CampaignSaves(SaveManager(tmp_path))
    state = State.new_campaign(7)
    state.explore()
    saves.save(state)
    detail = saves.entries()[0].detail
    assert 'Stage 1/3' in detail and f'Battle round {state.battle.round}' in detail
    for _ in range(80):
        if state.battle.outcome:
            break
        state.battle.auto_turn()
    state.resolve_battle()
    assert state.choice is not None
    saves.save(state)
    detail = saves.entries()[0].detail
    assert 'Stage 1/3' in detail and 'Decision pending' in detail
    finished = play_linked()
    assert finished.campaign.phase == 'completed'
    saves.save(finished)
    detail = saves.entries()[0].detail
    assert 'Stage 3/3' in detail and finished.campaign.title in detail and 'Campaign completed' in detail


def test_standalone_save_descriptions_include_saved_difficulty_without_campaign_phases(tmp_path):
    """Single-shard saves disclose their mode alongside the hero, turn and world."""
    saves = CampaignSaves(SaveManager(tmp_path))
    state = State.new(7)
    saves.save(state)
    assert saves.entries()[0].detail == 'Standard · Turn 1 · Commander · Shard 7'
    state.explore()
    saves.save(state)
    assert saves.entries()[0].detail == 'Standard · Turn 1 · Commander · Shard 7 · Battle round 1'
