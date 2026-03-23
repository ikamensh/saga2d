"""Executable reproductions for audio crossfade state corruption,
AnimationPlayer frame_duration=0, and List item_height=0.

Stage 12 — Independent investigation with concrete repros.

Each test is self-contained: it sets up the minimum fixture, exercises the
scenario, and asserts on observable state.  Tests are designed to *fail
loudly* if a bug exists and *pass silently* if the fix is in place.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

import pytest

# ==================================================================
# Fixtures
# ==================================================================


@pytest.fixture
def asset_dir(tmp_path: Path) -> Path:
    """Minimal asset directory for audio + animation + widget tests."""
    # Music tracks
    music = tmp_path / "music"
    music.mkdir()
    for name in ("track_a", "track_b", "track_c", "track_d"):
        (music / f"{name}.ogg").write_bytes(b"ogg")

    # Sound effects (for pool tests)
    sounds = tmp_path / "sounds"
    sounds.mkdir()
    for name in ("hit_a", "hit_b", "hit_c"):
        (sounds / f"{name}.wav").write_bytes(b"wav")

    # Images (for animation tests)
    images = tmp_path / "images" / "sprites"
    images.mkdir(parents=True)
    for name in ("frame_01", "frame_02", "frame_03"):
        (images / f"{name}.png").write_bytes(b"png")

    return tmp_path


@pytest.fixture
def game(asset_dir: Path) -> Any:
    """Game with mock backend + custom asset dir.  Yields then tears down."""
    os.environ.setdefault("SAGA2D_HEADLESS", "1")
    from saga2d import Game
    from saga2d.assets import AssetManager

    g = Game("CrossfadeRepro", resolution=(800, 600), backend="mock")
    g.assets = AssetManager(g.backend, base_path=asset_dir)
    yield g
    g._teardown()


@pytest.fixture
def audio_standalone(asset_dir: Path) -> Any:
    """Standalone AudioManager (no Game/tween tickloop).

    Useful for testing pure AudioManager logic without tween updates.
    """
    from saga2d.assets import AssetManager
    from saga2d.audio import AudioManager
    from saga2d.backends.mock_backend import MockBackend

    backend = MockBackend()
    assets = AssetManager(backend, base_path=asset_dir)
    return AudioManager(backend, assets)


# ==================================================================
# SECTION A — Audio Crossfade State Corruption Investigation
# ==================================================================


class TestCrossfadeVolumeChangeMidFade:
    """Gap 7 scenario: channel volume change mid-crossfade.

    When master or music channel volume changes *during* an active crossfade,
    the _CrossfadeProxy uses the AudioManager._volumes dict live.  So
    set_volume("master", 0.5) mid-crossfade should immediately affect the
    effective volume of BOTH the fading-in and fading-out players.

    Potential bug: set_volume() re-applies to _current_player_id only,
    but during crossfade there are TWO players.  The fading-out player
    is _crossfade_old_player, and set_volume() does NOT touch it directly.
    However, the _CrossfadeProxy setter does use _volumes live, so the
    *next* tween tick will apply the new channel volumes.

    Corruption scenario: if set_volume() is called *between* tween ticks,
    the old player keeps stale effective volume until the next tween update.
    This is at most one frame of desync, not a crash.  But let's verify
    the final state is correct.
    """

    def test_master_volume_change_mid_crossfade_final_state(
        self, game: Any
    ) -> None:
        """After crossfade completes with master=0.5, new player volume
        should be master * music * base = 0.5 * 1.0 * 1.0 = 0.5."""
        backend = game.backend
        game.audio.play_music("track_a")

        # Start crossfade A → B over 1 second.
        game.audio.crossfade_music("track_b", duration=1.0)
        new_player = game.audio._current_player_id

        # Advance to ~50% (about 0.5s).
        for _ in range(31):
            game.tick(dt=0.016)

        # Now change master volume mid-crossfade.
        game.audio.set_volume("master", 0.5)

        # Complete the crossfade.
        for _ in range(40):
            game.tick(dt=0.016)

        # Final state: new player at master(0.5) * music(1.0) * base(1.0) = 0.5
        assert backend._music_players[new_player]["volume"] == pytest.approx(
            0.5, abs=0.05
        )
        assert game.audio._current_player_base_volume == pytest.approx(1.0)

    def test_music_channel_change_mid_crossfade_final_state(
        self, game: Any
    ) -> None:
        """After crossfade with music=0.6, new player at 0.6."""
        backend = game.backend
        game.audio.play_music("track_a")
        game.audio.crossfade_music("track_b", duration=1.0)
        new_player = game.audio._current_player_id

        for _ in range(31):
            game.tick(dt=0.016)

        game.audio.set_volume("music", 0.6)

        for _ in range(40):
            game.tick(dt=0.016)

        # master(1.0) * music(0.6) * base(1.0) = 0.6
        assert backend._music_players[new_player]["volume"] == pytest.approx(
            0.6, abs=0.05
        )

    def test_both_channels_change_mid_crossfade(self, game: Any) -> None:
        """master=0.5, music=0.8 mid-crossfade → final = 0.4."""
        backend = game.backend
        game.audio.play_music("track_a")
        game.audio.crossfade_music("track_b", duration=1.0)
        new_player = game.audio._current_player_id

        for _ in range(20):
            game.tick(dt=0.016)

        game.audio.set_volume("master", 0.5)
        game.audio.set_volume("music", 0.8)

        for _ in range(50):
            game.tick(dt=0.016)

        assert backend._music_players[new_player]["volume"] == pytest.approx(
            0.4, abs=0.05
        )

    def test_volume_change_affects_old_player_on_next_tick(
        self, game: Any
    ) -> None:
        """After set_volume mid-crossfade, the NEXT tick should reflect
        new channel volumes on the old (fading-out) player too."""
        backend = game.backend
        game.audio.play_music("track_a")
        old_player = game.audio._current_player_id

        game.audio.crossfade_music("track_b", duration=2.0)

        # Advance 10 frames.
        for _ in range(10):
            game.tick(dt=0.016)

        # Old player should still be alive (fading out).
        assert old_player in backend._music_players

        # Record old player volume before channel change.
        vol_before = backend._music_players[old_player]["volume"]

        # Change master to 0.5.
        game.audio.set_volume("master", 0.5)

        # One more tick — tween proxy should apply new channel volumes.
        game.tick(dt=0.016)

        vol_after = backend._music_players[old_player]["volume"]
        # The old player's effective volume should be roughly halved
        # compared to what it would have been without the volume change.
        # More precisely: it should be less than vol_before (because master dropped
        # AND the fade-out continued).
        assert vol_after < vol_before

    def test_set_volume_between_tween_ticks_no_crash(self, game: Any) -> None:
        """Calling set_volume between ticks should not crash or corrupt state."""
        game.audio.play_music("track_a")
        game.audio.crossfade_music("track_b", duration=1.0)

        # Rapid volume changes between ticks.
        game.audio.set_volume("master", 0.3)
        game.audio.set_volume("music", 0.7)
        game.audio.set_volume("master", 1.0)
        game.audio.set_volume("music", 1.0)

        # Should not crash.
        for _ in range(70):
            game.tick(dt=0.016)

        # State consistent after crossfade completes.
        assert game.audio._crossfade_tween_ids == []
        assert game.audio._crossfade_old_player is None


class TestCrossfadeDurationZero:
    """crossfade_music(duration=0.0) — instant crossfade.

    duration=0 tweens complete on the first update (elapsed >= duration is
    True immediately).  Both old_volume→0 and new_volume→1 should complete,
    old player should be stopped.
    """

    def test_duration_zero_completes_on_first_tick(self, game: Any) -> None:
        backend = game.backend
        game.audio.play_music("track_a")
        old_player = game.audio._current_player_id

        game.audio.crossfade_music("track_b", duration=0.0)
        new_player = game.audio._current_player_id

        # One tick should complete both tweens.
        game.tick(dt=0.016)

        # Old player stopped.
        assert old_player not in backend._music_players
        # New player at full effective volume.
        assert backend._music_players[new_player]["volume"] == pytest.approx(1.0)
        # Crossfade state cleaned up.
        assert game.audio._crossfade_tween_ids == []
        assert game.audio._crossfade_old_player is None
        assert game.audio._current_player_base_volume == pytest.approx(1.0)

    def test_duration_zero_with_channel_volumes(self, game: Any) -> None:
        """duration=0 with master=0.5 → final volume 0.5."""
        backend = game.backend
        game.audio.set_volume("master", 0.5)
        game.audio.play_music("track_a")
        game.audio.crossfade_music("track_b", duration=0.0)
        new_player = game.audio._current_player_id

        game.tick(dt=0.016)

        assert backend._music_players[new_player]["volume"] == pytest.approx(0.5)


class TestCrossfadeMissingAsset:
    """crossfade_music() with a non-existent asset.

    The crossfade calls _cancel_crossfade() first (cancelling any active
    crossfade), then calls self._assets.music(name) which may raise.  We
    need to verify that state is consistent after the error.
    """

    def test_missing_asset_raises_and_preserves_state(self, game: Any) -> None:
        from saga2d.assets import AssetNotFoundError

        game.audio.play_music("track_a")
        player_before = game.audio._current_player_id
        name_before = game.audio._current_music_name

        with pytest.raises(AssetNotFoundError):
            game.audio.crossfade_music("nonexistent_track")

        # State should be unchanged — track_a still playing.
        # BUT: _cancel_crossfade() was called before the error, so any
        # previously active crossfade is cancelled.  Since there was no
        # active crossfade, state should be exactly as before.
        assert game.audio._current_player_id == player_before
        assert game.audio._current_music_name == name_before

    def test_missing_asset_during_active_crossfade(self, game: Any) -> None:
        """If we're mid-crossfade A→B and crossfade to missing track,
        the A→B crossfade is cancelled (old player stopped), and then
        the error occurs.  This leaves us with track_b still playing
        (it was the new current) but the old crossfade state is cleaned up."""
        from saga2d.assets import AssetNotFoundError

        backend = game.backend
        game.audio.play_music("track_a")
        game.audio.crossfade_music("track_b", duration=2.0)

        # track_b is now _current, track_a is _crossfade_old_player.
        player_b = game.audio._current_player_id
        assert game.audio._crossfade_old_player is not None

        with pytest.raises(AssetNotFoundError):
            game.audio.crossfade_music("nonexistent")

        # _cancel_crossfade was called → old player (track_a) stopped,
        # crossfade tween_ids cleared.  But the error occurs before
        # any new state is set, so track_b remains current.
        assert game.audio._current_player_id == player_b
        assert game.audio._current_music_name == "track_b"
        assert game.audio._crossfade_tween_ids == []
        assert game.audio._crossfade_old_player is None


class TestCrossfadeRapidInterruption:
    """Rapid crossfade interruptions — state consistency stress test."""

    def test_four_rapid_crossfades_no_player_leak(self, game: Any) -> None:
        """Each crossfade should stop the previous old player.
        After all crossfades complete, only one player should remain."""
        backend = game.backend
        game.audio.play_music("track_a")
        game.audio.crossfade_music("track_b", duration=0.5)
        game.audio.crossfade_music("track_c", duration=0.5)
        game.audio.crossfade_music("track_d", duration=0.5)

        # Tick to completion.
        for _ in range(40):
            game.tick(dt=0.016)

        # Only one player should remain (track_d).
        active = [
            pid
            for pid, p in backend._music_players.items()
            if p["playing"]
        ]
        assert len(active) == 1
        assert game.audio._current_music_name == "track_d"

    def test_crossfade_then_play_music_cleans_up(self, game: Any) -> None:
        """play_music() during crossfade calls stop_music() which cancels crossfade."""
        backend = game.backend
        game.audio.play_music("track_a")
        game.audio.crossfade_music("track_b", duration=2.0)

        # Now call play_music() — this stops all music first.
        game.audio.play_music("track_c")

        # All previous players stopped. Only track_c player remains.
        assert game.audio._current_music_name == "track_c"
        assert game.audio._crossfade_tween_ids == []
        assert game.audio._crossfade_old_player is None

        # Only one player active.
        active = [p for p in backend._music_players.values() if p["playing"]]
        assert len(active) == 1

    def test_crossfade_then_stop_then_crossfade(self, game: Any) -> None:
        """stop_music() between crossfades should leave clean state."""
        backend = game.backend
        game.audio.play_music("track_a")
        game.audio.crossfade_music("track_b", duration=2.0)
        game.audio.stop_music()

        # All players stopped.
        assert len(backend._music_players) == 0

        # Now crossfade from nothing — should act like play_music.
        game.audio.crossfade_music("track_c", duration=1.0)
        assert game.audio._current_music_name == "track_c"
        assert game.audio._current_player_id is not None


class TestCrossfadeSetVolumeOnlyUpdatesCurrentPlayer:
    """BUG INVESTIGATION: set_volume() during crossfade only re-applies
    to _current_player_id, not to _crossfade_old_player.

    The _CrossfadeProxy's setters use _volumes live, so the NEXT tween
    tick will pick up the new channel volumes.  But set_volume() itself
    calls set_player_volume() only on _current_player_id.

    This means: between set_volume() and the next tick, the old player
    has STALE effective volume.  This is a one-frame desync.

    Let's verify this is indeed the behavior and document it.
    """

    def test_set_volume_immediately_updates_current_not_old(
        self, game: Any
    ) -> None:
        """Verify that set_volume() immediately updates _current_player_id
        but NOT the _crossfade_old_player.  This is the known one-frame
        desync.
        """
        backend = game.backend
        game.audio.play_music("track_a")
        old_player = game.audio._current_player_id

        game.audio.crossfade_music("track_b", duration=2.0)
        new_player = game.audio._current_player_id

        # Advance a few frames.
        for _ in range(5):
            game.tick(dt=0.016)

        # Record old player volume.
        old_vol_before_change = backend._music_players[old_player]["volume"]

        # Change master volume.
        game.audio.set_volume("master", 0.5)

        # IMMEDIATELY after set_volume (no tick):
        # - new_player should have been updated by set_volume's re-apply.
        new_vol_immediate = backend._music_players[new_player]["volume"]
        # - old_player should NOT have been updated (no code path touches it).
        old_vol_immediate = backend._music_players[old_player]["volume"]

        # The new player was just re-applied: master(0.5) * music(1.0) * base
        # (where base is the current tween position).
        # The old player keeps its stale value.
        assert old_vol_immediate == old_vol_before_change  # stale — no update

        # Now tick once — proxy setter fires with new _volumes.
        game.tick(dt=0.016)
        old_vol_after_tick = backend._music_players[old_player]["volume"]
        # After tick, old player should reflect the new master volume.
        # It should be roughly half of what it was (master went from 1.0 to 0.5).
        assert old_vol_after_tick < old_vol_before_change


class TestSoundPoolDuplicateNames:
    """register_pool with duplicate sound names."""

    def test_duplicate_names_no_repeat_logic_still_works(
        self, game: Any
    ) -> None:
        """Pool ["hit_a", "hit_a", "hit_b"] — the no-repeat logic avoids
        the same INDEX, not the same SOUND NAME.  So it CAN play "hit_a"
        twice in a row (indices 0 and 1 both map to "hit_a")."""
        game.audio.register_pool("test_pool", ["hit_a", "hit_a", "hit_b"])

        # Play several times.  Should not crash.
        for _ in range(20):
            game.audio.play_pool("test_pool")

    def test_re_register_pool_resets_last(self, game: Any) -> None:
        """Re-registering a pool resets _pool_last to -1."""
        game.audio.register_pool("p", ["hit_a", "hit_b"])
        game.audio.play_pool("p")
        assert game.audio._pool_last["p"] != -1

        game.audio.register_pool("p", ["hit_c"])
        assert game.audio._pool_last["p"] == -1


class TestCrossfadeCompletionCallback:
    """Verify _finish_crossfade is called exactly once and cleans up."""

    def test_crossfade_finish_stops_old_player(self, game: Any) -> None:
        backend = game.backend
        game.audio.play_music("track_a")
        old_player = game.audio._current_player_id

        game.audio.crossfade_music("track_b", duration=0.5)

        # Tick to completion.
        for _ in range(40):
            game.tick(dt=0.016)

        # Old player removed.
        assert old_player not in backend._music_players
        # Crossfade state clean.
        assert game.audio._crossfade_old_player is None
        assert game.audio._crossfade_tween_ids == []

    def test_crossfade_base_volume_reaches_one(self, game: Any) -> None:
        """_current_player_base_volume should be 1.0 after crossfade completion."""
        game.audio.play_music("track_a")
        game.audio.crossfade_music("track_b", duration=0.5)

        for _ in range(40):
            game.tick(dt=0.016)

        assert game.audio._current_player_base_volume == pytest.approx(1.0)


class TestCrossfadeWithDurationNegative:
    """crossfade_music with negative duration should raise ValueError
    because tween.create() validates duration >= 0."""

    def test_negative_duration_raises(self, game: Any) -> None:
        game.audio.play_music("track_a")
        with pytest.raises(ValueError, match="duration"):
            game.audio.crossfade_music("track_b", duration=-1.0)


# ==================================================================
# SECTION B — AnimationPlayer frame_duration=0 Fix Verification
# ==================================================================


class TestAnimationPlayerFrameDurationZero:
    """Verify that the Stage 9 fix (F21/F22/F23) is in place:
    AnimationDef and AnimationPlayer reject frame_duration <= 0, NaN, Inf.

    Before the fix, frame_duration=0 with loop=True caused an infinite
    loop in update() because `while elapsed >= 0` is always true.
    """

    def test_animationdef_frame_duration_zero_raises(self) -> None:
        from saga2d.animation import AnimationDef

        with pytest.raises(ValueError, match="positive finite"):
            AnimationDef(frames=["a", "b"], frame_duration=0.0)

    def test_animationdef_frame_duration_negative_raises(self) -> None:
        from saga2d.animation import AnimationDef

        with pytest.raises(ValueError, match="positive finite"):
            AnimationDef(frames=["a", "b"], frame_duration=-0.1)

    def test_animationdef_frame_duration_nan_raises(self) -> None:
        from saga2d.animation import AnimationDef

        with pytest.raises(ValueError, match="positive finite"):
            AnimationDef(frames=["a", "b"], frame_duration=float("nan"))

    def test_animationdef_frame_duration_inf_raises(self) -> None:
        from saga2d.animation import AnimationDef

        with pytest.raises(ValueError, match="positive finite"):
            AnimationDef(frames=["a", "b"], frame_duration=float("inf"))

    def test_animationdef_frame_duration_neg_inf_raises(self) -> None:
        from saga2d.animation import AnimationDef

        with pytest.raises(ValueError, match="positive finite"):
            AnimationDef(frames=["a", "b"], frame_duration=float("-inf"))

    def test_animationplayer_frame_duration_zero_raises(self) -> None:
        from saga2d.animation import AnimationPlayer

        with pytest.raises(ValueError, match="positive finite"):
            AnimationPlayer(frames=["handle_a", "handle_b"], frame_duration=0.0, loop=True)

    def test_animationplayer_frame_duration_negative_raises(self) -> None:
        from saga2d.animation import AnimationPlayer

        with pytest.raises(ValueError, match="positive finite"):
            AnimationPlayer(frames=["handle_a"], frame_duration=-1.0, loop=False)

    def test_animationplayer_frame_duration_nan_raises(self) -> None:
        from saga2d.animation import AnimationPlayer

        with pytest.raises(ValueError, match="positive finite"):
            AnimationPlayer(frames=["h"], frame_duration=float("nan"), loop=True)

    def test_animationplayer_normal_still_works(self) -> None:
        """Positive finite frame_duration should work fine."""
        from saga2d.animation import AnimationPlayer

        player = AnimationPlayer(
            frames=["f1", "f2", "f3"], frame_duration=0.1, loop=True
        )
        assert player.is_playing
        # Advance past one frame.
        result = player.update(0.15)
        assert result is not None  # Frame changed.
        assert player.frame_index == 1

    def test_animationplayer_loop_true_does_not_hang(self) -> None:
        """Verify looping animation with valid frame_duration does not hang.
        Pre-fix, frame_duration=0 + loop=True caused infinite loop here."""
        from saga2d.animation import AnimationPlayer

        player = AnimationPlayer(
            frames=["f1", "f2", "f3"], frame_duration=0.05, loop=True
        )
        # Large dt — should wrap around multiple times, not hang.
        result = player.update(1.0)
        assert result is not None
        assert player.is_playing  # Still playing (looping).


# ==================================================================
# SECTION C — List item_height=0 Fix Verification
# ==================================================================


class TestListItemHeightZero:
    """Verify that the Stage 9 fix (F24) is in place:
    List(item_height=0) no longer crashes with ZeroDivisionError on
    click or motion events.

    Before the fix, clicking on a List with item_height=0 hit
    `int(relative_y // self._item_height)` which divided by zero.
    """

    def _make_list(self, item_height: int = 0) -> Any:
        from saga2d.ui.widgets import List

        return List(
            items=["Apple", "Banana", "Cherry"],
            item_height=item_height,
            width=200,
            height=100,
        )

    def _make_click_event(self, x: float, y: float) -> Any:
        """Create a click InputEvent."""
        from saga2d.input import InputEvent

        return InputEvent(type="click", x=int(x), y=int(y), button="left")

    def _make_motion_event(self, x: float, y: float) -> Any:
        from saga2d.input import InputEvent

        return InputEvent(type="motion", x=int(x), y=int(y))

    def _make_scroll_event(self, x: float, y: float, dy: int = 1) -> Any:
        from saga2d.input import InputEvent

        return InputEvent(type="scroll", x=int(x), y=int(y), dy=dy)

    def test_item_height_zero_click_no_crash(self) -> None:
        """Click on List(item_height=0) should return True, not crash."""
        lst = self._make_list(item_height=0)
        # Force computed bounds to include the click position.
        lst._computed_x = 0
        lst._computed_y = 0
        lst._computed_w = 200
        lst._computed_h = 100

        event = self._make_click_event(50, 50)
        result = lst.on_event(event)
        # Should not raise ZeroDivisionError.
        assert result is True

    def test_item_height_zero_motion_no_crash(self) -> None:
        """Motion over List(item_height=0) should return True, not crash."""
        lst = self._make_list(item_height=0)
        lst._computed_x = 0
        lst._computed_y = 0
        lst._computed_w = 200
        lst._computed_h = 100

        event = self._make_motion_event(50, 50)
        result = lst.on_event(event)
        assert result is True

    def test_item_height_zero_visible_count_returns_zero(self) -> None:
        """_visible_count() should return 0 when item_height <= 0."""
        lst = self._make_list(item_height=0)
        lst._computed_h = 100
        assert lst._visible_count() == 0

    def test_item_height_negative_click_no_crash(self) -> None:
        """Negative item_height should also be guarded."""
        lst = self._make_list(item_height=-10)
        lst._computed_x = 0
        lst._computed_y = 0
        lst._computed_w = 200
        lst._computed_h = 100

        event = self._make_click_event(50, 50)
        result = lst.on_event(event)
        assert result is True

    def test_normal_item_height_click_works(self) -> None:
        """Positive item_height should still select correctly."""
        lst = self._make_list(item_height=30)
        lst._computed_x = 0
        lst._computed_y = 0
        lst._computed_w = 200
        lst._computed_h = 100

        event = self._make_click_event(50, 15)  # first row
        lst.on_event(event)
        assert lst.selected_index == 0


# ==================================================================
# SECTION D — Additional Crossfade Edge Cases
# ==================================================================


class TestCrossfadeProxyDirectly:
    """Test _CrossfadeProxy in isolation to verify it reads live volumes."""

    def test_proxy_uses_live_volumes(self, game: Any) -> None:
        """When channel volumes change, proxy setter should use the new values."""
        from saga2d.audio import _CrossfadeProxy

        backend = game.backend

        game.audio.play_music("track_a")
        old_player = game.audio._current_player_id

        # Manually create a proxy like crossfade_music would.
        new_player_id = backend.play_music(
            backend.load_music("music/track_b.ogg"), loop=True, volume=0.0
        )
        proxy = _CrossfadeProxy(game.audio, old_player, new_player_id, 1.0)

        # Set new_volume to 0.5 — effective should be master(1)*music(1)*0.5
        proxy.new_volume = 0.5
        assert backend._music_players[new_player_id]["volume"] == pytest.approx(0.5)

        # Now change master to 0.5.
        game.audio._volumes["master"] = 0.5

        # Set new_volume again — should now be 0.5*1.0*0.6 = 0.3
        proxy.new_volume = 0.6
        assert backend._music_players[new_player_id]["volume"] == pytest.approx(0.3)

    def test_proxy_updates_base_volume(self, game: Any) -> None:
        """Setting new_volume on proxy should update _current_player_base_volume."""
        from saga2d.audio import _CrossfadeProxy

        backend = game.backend
        game.audio.play_music("track_a")
        old_player = game.audio._current_player_id

        new_player_id = backend.play_music(
            backend.load_music("music/track_b.ogg"), loop=True, volume=0.0
        )
        proxy = _CrossfadeProxy(game.audio, old_player, new_player_id, 1.0)

        proxy.new_volume = 0.75
        assert game.audio._current_player_base_volume == 0.75


class TestCrossfadeEdgeStates:
    """Edge cases around crossfade state transitions."""

    def test_cancel_crossfade_when_no_crossfade(self, game: Any) -> None:
        """_cancel_crossfade() when no crossfade active should be safe."""
        game.audio._cancel_crossfade()  # No crash.
        assert game.audio._crossfade_old_player is None
        assert game.audio._crossfade_tween_ids == []

    def test_double_stop_music(self, game: Any) -> None:
        """stop_music() twice in a row should be safe."""
        game.audio.play_music("track_a")
        game.audio.stop_music()
        game.audio.stop_music()  # No crash.
        assert game.audio._current_player_id is None

    def test_crossfade_to_same_name_after_stop_and_play(
        self, game: Any
    ) -> None:
        """After stop → play(track_a), crossfade to track_a is noop."""
        game.audio.play_music("track_a")
        game.audio.stop_music()
        game.audio.play_music("track_a")

        player = game.audio._current_player_id
        game.audio.crossfade_music("track_a")
        # Should be noop — same player.
        assert game.audio._current_player_id == player

    def test_teardown_during_crossfade(self, game: Any) -> None:
        """_teardown() during active crossfade should cleanly stop everything."""
        backend = game.backend
        game.audio.play_music("track_a")
        game.audio.crossfade_music("track_b", duration=2.0)

        game.audio._teardown()

        assert game.audio._current_player_id is None
        assert game.audio._crossfade_old_player is None
        assert game.audio._crossfade_tween_ids == []
        assert len(backend._music_players) == 0
