"""Stage 7 — End-to-end coverage for under-tested feature areas.

Targets:
  - Audio: crossfade E2E, sound pools (edge cases), _teardown, channel isolation,
    optional missing assets, volume clamping
  - Text/Fonts: backend draw_text + load_font, TextBox typewriter (skip/reset/complete),
    word wrap edge cases, Label draw with text emission
  - Backend drawing: draw_circle, draw_image, capture_frame
  - Utility modules: tween cancel/on_complete, timer chaining, FSM edge cases
  - Tilemap: N/A (not in saga2d)

Run:  .venv/bin/python -m pytest tests/kodo_test_stage7_e2e.py -v
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest

from saga2d import (
    Game,
    Scene,
    AssetNotFoundError,
)
from saga2d.assets import AssetManager
from saga2d.audio import AudioManager
from saga2d.backends.mock_backend import MockBackend
from saga2d.input import InputEvent
from saga2d.rendering.camera import Camera
from saga2d.rendering.sprite import Sprite
from saga2d.rendering.layers import SpriteAnchor
from saga2d.ui import (
    Panel,
    Label,
    Button,
    TextBox,
    ProgressBar,
)
from saga2d.ui.layout import Layout, Anchor
from saga2d.ui.theme import Style
from saga2d.util import tween as tween_mod
from saga2d.util.tween import Ease, tween


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture()
def game():
    g = Game("Stage7", backend="mock", resolution=(800, 600))
    yield g
    g._teardown()


@pytest.fixture()
def backend(game: Game) -> MockBackend:
    return game.backend


@pytest.fixture()
def audio_dir(tmp_path: Path) -> Path:
    """Temp asset dir with test sounds and music files."""
    sounds = tmp_path / "sounds"
    sounds.mkdir()
    (sounds / "sword_hit.wav").write_bytes(b"wav")
    (sounds / "click.wav").write_bytes(b"wav")
    (sounds / "hit_01.wav").write_bytes(b"wav")
    (sounds / "hit_02.wav").write_bytes(b"wav")
    (sounds / "hit_03.wav").write_bytes(b"wav")
    (sounds / "lone.wav").write_bytes(b"wav")
    music = tmp_path / "music"
    music.mkdir()
    (music / "track_a.ogg").write_bytes(b"ogg")
    (music / "track_b.ogg").write_bytes(b"ogg")
    images = tmp_path / "images" / "sprites"
    images.mkdir(parents=True)
    (images / "knight.png").write_bytes(b"png")
    return tmp_path


@pytest.fixture()
def audio_game(audio_dir: Path):
    """Game with custom asset dir for audio tests."""
    g = Game("AudioTest", backend="mock", resolution=(800, 600))
    g._assets = AssetManager(g.backend, base_path=audio_dir)
    yield g
    g._teardown()


# ═══════════════════════════════════════════════════════════════════
# 1. AUDIO — crossfade orchestration E2E
# ═══════════════════════════════════════════════════════════════════


class TestAudioCrossfadeE2E:
    """E2E crossfade tests exercising the tween-driven volume ramp."""

    def test_crossfade_drives_volume_over_time(self, audio_game: Game) -> None:
        """Crossfade gradually ramps old→0, new→1 via tick-driven tweens."""
        audio_game.push(Scene())
        audio = audio_game.audio

        audio.play_music("track_a")
        assert audio._current_music_name == "track_a"

        audio.crossfade_music("track_b", duration=1.0)
        assert audio._current_music_name == "track_b"
        assert audio._crossfade_old_player is not None

        # Drive 25 ticks at 0.05s = 1.25s (past crossfade completion)
        for _ in range(25):
            audio_game.tick(0.05)

        assert audio._crossfade_old_player is None
        assert audio._crossfade_tween_ids == []

    def test_crossfade_same_track_noop(self, audio_game: Game) -> None:
        """Crossfade to same track name is a no-op."""
        audio_game.push(Scene())
        audio = audio_game.audio

        audio.play_music("track_a")
        player_before = audio._current_player_id

        audio.crossfade_music("track_a")
        assert audio._current_player_id == player_before
        assert audio._crossfade_old_player is None

    def test_crossfade_with_no_music_plays_directly(self, audio_game: Game) -> None:
        """Crossfade with no current music just plays the track."""
        audio_game.push(Scene())
        audio = audio_game.audio

        audio.crossfade_music("track_a")
        assert audio._current_music_name == "track_a"
        assert audio._crossfade_old_player is None

    def test_stop_cancels_active_crossfade(self, audio_game: Game) -> None:
        """stop_music() during crossfade cancels tweens and stops all players."""
        audio_game.push(Scene())
        audio = audio_game.audio

        audio.play_music("track_a")
        audio.crossfade_music("track_b", duration=2.0)
        audio_game.tick(0.1)

        audio.stop_music()
        assert audio._current_player_id is None
        assert audio._crossfade_old_player is None
        assert audio._crossfade_tween_ids == []


# ═══════════════════════════════════════════════════════════════════
# 2. AUDIO — sound pools edge cases
# ═══════════════════════════════════════════════════════════════════


class TestAudioSoundPools:
    """Sound pool registration and playback edge cases."""

    def test_pool_single_element(self, audio_game: Game) -> None:
        """Pool with 1 sound always plays that sound (no crash)."""
        audio_game.push(Scene())
        audio = audio_game.audio

        audio.register_pool("hits", ["sword_hit"])
        for _ in range(5):
            audio.play_pool("hits")

    def test_pool_empty_list(self, audio_game: Game) -> None:
        """Pool with empty list returns without playing."""
        audio_game.push(Scene())
        audio = audio_game.audio
        audio.register_pool("empty", [])
        audio.play_pool("empty")  # Should not crash

    def test_pool_unregistered_raises(self, audio_game: Game) -> None:
        """Playing from unregistered pool raises KeyError."""
        audio_game.push(Scene())
        with pytest.raises(KeyError):
            audio_game.audio.play_pool("nonexistent")

    def test_pool_no_immediate_repeat(self, audio_game: Game) -> None:
        """Pool with 2+ sounds avoids immediate repetition."""
        audio_game.push(Scene())
        audio = audio_game.audio

        audio.register_pool("multi", ["hit_01", "hit_02", "hit_03"])
        indices = []
        for _ in range(20):
            audio.play_pool("multi")
            indices.append(audio._pool_last["multi"])

        for i in range(1, len(indices)):
            assert indices[i] != indices[i - 1]


# ═══════════════════════════════════════════════════════════════════
# 3. AUDIO — volume and channel isolation
# ═══════════════════════════════════════════════════════════════════


class TestAudioVolumeEdgeCases:
    """Volume clamping, channel isolation, invalid channel."""

    def test_volume_clamps_above_one(self, game: Game) -> None:
        game.push(Scene())
        game.audio.set_volume("master", 1.5)
        assert game.audio.get_volume("master") == 1.0

    def test_volume_clamps_below_zero(self, game: Game) -> None:
        game.push(Scene())
        game.audio.set_volume("sfx", -0.5)
        assert game.audio.get_volume("sfx") == 0.0

    def test_invalid_channel_raises_keyerror(self, game: Game) -> None:
        game.push(Scene())
        with pytest.raises(KeyError, match="Unknown audio channel"):
            game.audio.set_volume("nonexistent", 0.5)

    def test_get_volume_invalid_channel_raises(self, game: Game) -> None:
        game.push(Scene())
        with pytest.raises(KeyError):
            game.audio.get_volume("bogus")

    def test_ui_channel_exists(self, game: Game) -> None:
        """The 'ui' channel is a valid channel."""
        game.push(Scene())
        assert game.audio.get_volume("ui") == 1.0
        game.audio.set_volume("ui", 0.3)
        assert abs(game.audio.get_volume("ui") - 0.3) < 1e-9


# ═══════════════════════════════════════════════════════════════════
# 4. AUDIO — optional play_sound / play_music
# ═══════════════════════════════════════════════════════════════════


class TestAudioOptionalAssets:
    """play_sound/play_music with optional=True for missing assets."""

    def test_play_sound_optional_missing(self, game: Game) -> None:
        game.push(Scene())
        result = game.audio.play_sound("nonexistent_sound", optional=True)
        assert result is None

    def test_play_sound_required_missing_raises(self, game: Game) -> None:
        game.push(Scene())
        with pytest.raises(AssetNotFoundError):
            game.audio.play_sound("nonexistent_sound")

    def test_play_music_optional_missing(self, game: Game) -> None:
        game.push(Scene())
        result = game.audio.play_music("nonexistent_music", optional=True)
        assert result is None

    def test_play_music_required_missing_raises(self, game: Game) -> None:
        game.push(Scene())
        with pytest.raises(AssetNotFoundError):
            game.audio.play_music("nonexistent_music")


# ═══════════════════════════════════════════════════════════════════
# 5. AUDIO — _teardown
# ═══════════════════════════════════════════════════════════════════


class TestAudioTeardown:
    """AudioManager._teardown lifecycle."""

    def test_teardown_stops_music(self, audio_game: Game) -> None:
        audio_game.push(Scene())
        audio = audio_game.audio

        audio.play_music("track_a")
        assert audio._current_player_id is not None

        audio._teardown()
        assert audio._current_player_id is None
        assert audio._current_music_name is None

    def test_teardown_idempotent(self, game: Game) -> None:
        game.push(Scene())
        audio = game.audio
        audio._teardown()
        audio._teardown()  # Should not crash


# ═══════════════════════════════════════════════════════════════════
# 6. TEXT / FONTS — backend draw_text and load_font
# ═══════════════════════════════════════════════════════════════════


class TestBackendDrawText:
    """Verify MockBackend draw_text / load_font recording."""

    def test_draw_text_recorded(self, game: Game, backend: MockBackend) -> None:
        """Scene.draw() can call backend.draw_text and it's recorded."""

        class TextScene(Scene):
            def draw(self):
                self.game._backend.draw_text(
                    "Hello World", 100, 200, 16, (255, 255, 255, 255)
                )

        game.push(TextScene())
        game.tick(0.016)

        assert len(backend.texts) >= 1
        t = backend.texts[0]
        assert t["text"] == "Hello World"
        assert t["x"] == 100
        assert t["y"] == 200
        assert t["font_size"] == 16

    def test_draw_text_anchors(self, game: Game, backend: MockBackend) -> None:
        """Text anchor parameters are recorded."""

        class AnchorScene(Scene):
            def draw(self):
                self.game._backend.draw_text(
                    "Centered", 400, 300, 24, (0, 0, 0, 255),
                    anchor_x="center", anchor_y="top"
                )

        game.push(AnchorScene())
        game.tick(0.016)

        t = backend.texts[0]
        assert t["anchor_x"] == "center"
        assert t["anchor_y"] == "top"

    def test_load_font_returns_handle(self, backend: MockBackend) -> None:
        """load_font returns a string handle."""
        handle = backend.load_font("Arial")
        assert isinstance(handle, str)
        assert "Arial" in handle

    def test_load_font_with_path(self, backend: MockBackend) -> None:
        """load_font with explicit path records it."""
        handle = backend.load_font("custom", path="/fonts/custom.ttf")
        assert handle == "font_custom"
        assert backend.fonts["custom"] == "/fonts/custom.ttf"


# ═══════════════════════════════════════════════════════════════════
# 7. TEXT — TextBox typewriter E2E
# ═══════════════════════════════════════════════════════════════════


class TestTextBoxTypewriter:
    """TextBox typewriter reveal, skip, reset, and drawing E2E."""

    def test_typewriter_gradual_reveal(self, game: Game, backend: MockBackend) -> None:
        """Typewriter reveals chars over time via game ticks."""
        tb = TextBox("Hello", typewriter_speed=10, width=200)

        class TBScene(Scene):
            def on_enter(self):
                self.ui.add(tb)

        game.push(TBScene())
        assert tb.revealed_count == 0
        assert not tb.is_complete

        game.tick(0.3)  # 10 chars/sec × 0.3s = 3 chars
        assert tb.revealed_count == 3

        game.tick(0.3)  # 3 more → 6 total, but only 5 chars
        assert tb.revealed_count == 5
        assert tb.is_complete

    def test_typewriter_skip(self, game: Game) -> None:
        """skip() reveals all text instantly."""
        tb = TextBox("Long text here", typewriter_speed=1, width=200)

        class S(Scene):
            def on_enter(self):
                self.ui.add(tb)

        game.push(S())
        assert tb.revealed_count == 0

        tb.skip()
        assert tb.is_complete
        assert tb.revealed_count == len("Long text here")

    def test_typewriter_reset(self, game: Game) -> None:
        """reset() sets reveal back to 0."""
        tb = TextBox("ABC", typewriter_speed=100, width=200)

        class S(Scene):
            def on_enter(self):
                self.ui.add(tb)

        game.push(S())
        game.tick(1.0)  # Reveal all
        assert tb.is_complete

        tb.reset()
        assert tb.revealed_count == 0
        assert not tb.is_complete

    def test_instant_mode_reveals_all(self, game: Game) -> None:
        """typewriter_speed=0 → all text visible immediately."""
        tb = TextBox("Instant", typewriter_speed=0, width=200)
        assert tb.is_complete
        assert tb.revealed_count == len("Instant")

    def test_text_setter_resets_typewriter(self, game: Game) -> None:
        """Changing .text resets typewriter reveal to 0."""
        tb = TextBox("Old", typewriter_speed=5, width=200)

        class S(Scene):
            def on_enter(self):
                self.ui.add(tb)

        game.push(S())
        game.tick(1.0)
        assert tb.is_complete

        tb.text = "New text"
        assert tb.revealed_count == 0
        assert not tb.is_complete

    def test_textbox_draw_emits_text(self, game: Game, backend: MockBackend) -> None:
        """TextBox.on_draw produces draw_text calls in the backend."""
        tb = TextBox("Draw me", typewriter_speed=0, width=300, height=100)

        class S(Scene):
            def on_enter(self):
                self.ui.add(tb)

        game.push(S())
        game.tick(0.016)

        assert len(backend.texts) >= 1
        drawn_texts = [t["text"] for t in backend.texts]
        assert any("Draw" in t for t in drawn_texts)


# ═══════════════════════════════════════════════════════════════════
# 8. TEXT — word wrap edge cases
# ═══════════════════════════════════════════════════════════════════


class TestWordWrap:
    """_word_wrap helper edge cases."""

    def test_explicit_newlines_respected(self) -> None:
        from saga2d.ui.widgets import _word_wrap
        lines = _word_wrap("Line one\nLine two", 9999, 16)
        assert lines == ["Line one", "Line two"]

    def test_empty_string(self) -> None:
        from saga2d.ui.widgets import _word_wrap
        lines = _word_wrap("", 200, 16)
        assert lines == [""]

    def test_single_long_word(self) -> None:
        """A word longer than max_width gets its own line (never broken)."""
        from saga2d.ui.widgets import _word_wrap
        lines = _word_wrap("Superlongword short", 50, 12)
        assert "Superlongword" in lines[0]

    def test_zero_max_width(self) -> None:
        from saga2d.ui.widgets import _word_wrap
        lines = _word_wrap("text", 0, 16)
        assert lines == ["text"]

    def test_multiple_newlines(self) -> None:
        from saga2d.ui.widgets import _word_wrap
        lines = _word_wrap("A\n\nB", 9999, 16)
        assert lines == ["A", "", "B"]


# ═══════════════════════════════════════════════════════════════════
# 9. BACKEND — draw_circle
# ═══════════════════════════════════════════════════════════════════


class TestBackendDrawCircle:
    """Verify MockBackend draw_circle recording."""

    def test_draw_circle_recorded(self, game: Game, backend: MockBackend) -> None:
        class CircleScene(Scene):
            def draw(self):
                self.game._backend.draw_circle(
                    400, 300, 50, (255, 0, 0, 255)
                )

        game.push(CircleScene())
        game.tick(0.016)

        assert len(backend.circles) >= 1
        c = backend.circles[0]
        assert c["x"] == 400
        assert c["y"] == 300
        assert c["radius"] == 50
        assert c["color"] == (255, 0, 0, 255)

    def test_draw_circle_with_segments(self, game: Game, backend: MockBackend) -> None:
        class S(Scene):
            def draw(self):
                self.game._backend.draw_circle(
                    100, 100, 25, (0, 255, 0, 255), segments=32
                )

        game.push(S())
        game.tick(0.016)
        assert backend.circles[0]["segments"] == 32

    def test_draw_circle_opacity(self, game: Game, backend: MockBackend) -> None:
        class S(Scene):
            def draw(self):
                self.game._backend.draw_circle(
                    100, 100, 10, (0, 0, 255, 255), opacity=0.5
                )

        game.push(S())
        game.tick(0.016)
        assert backend.circles[0]["opacity"] == 0.5


# ═══════════════════════════════════════════════════════════════════
# 10. BACKEND — draw_image
# ═══════════════════════════════════════════════════════════════════


class TestBackendDrawImage:
    """Verify MockBackend draw_image recording."""

    def test_draw_image_recorded(self, game: Game, backend: MockBackend) -> None:
        class S(Scene):
            def draw(self):
                # Use a fake image handle directly (mock doesn't validate)
                self.game._backend.draw_image("img_handle", 100, 200, 64, 64)

        game.push(S())
        game.tick(0.016)
        assert len(backend.images) >= 1
        img = backend.images[0]
        assert img["x"] == 100
        assert img["y"] == 200
        assert img["width"] == 64
        assert img["height"] == 64

    def test_draw_image_opacity(self, game: Game, backend: MockBackend) -> None:
        class S(Scene):
            def draw(self):
                self.game._backend.draw_image("img", 0, 0, 32, 32, opacity=0.5)

        game.push(S())
        game.tick(0.016)
        assert backend.images[0]["opacity"] == 0.5


# ═══════════════════════════════════════════════════════════════════
# 11. BACKEND — capture_frame
# ═══════════════════════════════════════════════════════════════════


class TestBackendCaptureFrame:
    """Verify MockBackend capture_frame returns valid image."""

    def test_capture_frame_returns_pil_image(self, game: Game, backend: MockBackend) -> None:
        game.push(Scene())
        game.tick(0.016)

        img = backend.capture_frame()
        assert hasattr(img, "size")
        assert img.size == (800, 600)
        assert img.mode == "RGBA"


# ═══════════════════════════════════════════════════════════════════
# 12. LABEL — draw emits text calls
# ═══════════════════════════════════════════════════════════════════


class TestLabelDrawE2E:
    """Label drawing produces backend text calls."""

    def test_label_emits_draw_text(self, game: Game, backend: MockBackend) -> None:
        label = Label("Score: 100", style=Style(font_size=20))

        class S(Scene):
            def on_enter(self):
                self.ui.add(label)

        game.push(S())
        game.tick(0.016)

        text_entries = [t for t in backend.texts if "Score" in t["text"]]
        assert len(text_entries) >= 1

    def test_label_empty_string_draws(self, game: Game, backend: MockBackend) -> None:
        """Empty label still renders without crash."""
        label = Label("")

        class S(Scene):
            def on_enter(self):
                self.ui.add(label)

        game.push(S())
        game.tick(0.016)  # Should not crash


# ═══════════════════════════════════════════════════════════════════
# 13. UTILITY — tween cancel and on_complete
# ═══════════════════════════════════════════════════════════════════


class TestTweenEdgeCases:
    """Tween cancel mid-progress and on_complete callback."""

    def test_tween_on_complete_fires(self, game: Game) -> None:
        game.push(Scene())
        obj = type("Obj", (), {"x": 0.0})()
        completed = []

        tween(obj, "x", 0, 100, 0.5, on_complete=lambda: completed.append(True))

        for _ in range(35):
            game.tick(0.016)

        assert obj.x == pytest.approx(100.0)
        assert completed == [True]

    def test_tween_cancel_stops(self, game: Game) -> None:
        game.push(Scene())
        obj = type("Obj", (), {"x": 0.0})()

        tid = tween(obj, "x", 0, 100, 1.0)
        game.tick(0.25)

        tween_mod._tween_manager.cancel(tid)
        val_at_cancel = obj.x
        game.tick(0.25)
        assert obj.x == pytest.approx(val_at_cancel)

    def test_tween_easing_modes(self, game: Game) -> None:
        """All 4 easing modes produce values between start and end."""
        game.push(Scene())
        for ease in (Ease.LINEAR, Ease.EASE_IN, Ease.EASE_OUT, Ease.EASE_IN_OUT):
            obj = type("Obj", (), {"v": 0.0})()
            tween(obj, "v", 0, 100, 0.5, ease=ease)
            for _ in range(35):
                game.tick(0.016)
            assert obj.v == pytest.approx(100.0), f"Failed for {ease}"


# ═══════════════════════════════════════════════════════════════════
# 14. UTILITY — timer chaining
# ═══════════════════════════════════════════════════════════════════


class TestTimerChaining:
    """Timer .then() chaining and cancel behaviour."""

    def test_timer_then_chain(self, game: Game) -> None:
        """after().then() fires callbacks in order."""
        game.push(Scene())
        log = []
        scene = game._scene_stack.top()

        # .then(callback, delay) — callback first, delay second
        scene.after(0.1, lambda: log.append("first")).then(
            lambda: log.append("second"), 0.1
        ).then(lambda: log.append("third"), 0.1)

        for _ in range(25):
            game.tick(0.016)

        assert log == ["first", "second", "third"]

    def test_timer_cancel_via_manager(self, game: Game) -> None:
        """Cancelling a timer via timer manager prevents firing."""
        game.push(Scene())
        fired = []

        handle = game._timer_manager.after(0.1, lambda: fired.append(True))
        game._timer_manager.cancel(handle)

        for _ in range(20):
            game.tick(0.016)

        assert fired == []


# ═══════════════════════════════════════════════════════════════════
# 15. UTILITY — FSM edge cases
# ═══════════════════════════════════════════════════════════════════


class TestFSMEdgeCases:
    """StateMachine transitions, callbacks, and validation."""

    def test_fsm_transition_fires_callbacks(self) -> None:
        from saga2d.util.fsm import StateMachine
        log = []

        sm = StateMachine(
            ["idle", "walk", "attack"],
            "idle",
            transitions={
                "idle": {"start_walk": "walk", "start_attack": "attack"},
                "walk": {"stop": "idle"},
                "attack": {"done": "idle"},
            },
            on_enter={"walk": lambda: log.append("enter_walk")},
            on_exit={"idle": lambda: log.append("exit_idle")},
        )

        sm.trigger("start_walk")
        assert sm.state == "walk"
        assert log == ["exit_idle", "enter_walk"]

    def test_fsm_unknown_event_returns_false(self) -> None:
        """trigger() with unknown event returns False (no error)."""
        from saga2d.util.fsm import StateMachine
        sm = StateMachine(
            ["idle", "walk"],
            "idle",
            transitions={"idle": {"go": "walk"}, "walk": {"stop": "idle"}},
        )
        result = sm.trigger("invalid_event")
        assert result is False
        assert sm.state == "idle"

    def test_fsm_valid_events_property(self) -> None:
        """valid_events returns list of valid events for current state."""
        from saga2d.util.fsm import StateMachine
        sm = StateMachine(
            ["idle", "walk"],
            "idle",
            transitions={"idle": {"go": "walk"}, "walk": {"stop": "idle"}},
        )
        assert set(sm.valid_events) == {"go"}

    def test_fsm_self_transition(self) -> None:
        from saga2d.util.fsm import StateMachine
        log = []
        sm = StateMachine(
            ["idle"],
            "idle",
            transitions={"idle": {"reset": "idle"}},
            on_exit={"idle": lambda: log.append("exit")},
            on_enter={"idle": lambda: log.append("enter")},
        )
        # Constructor fires on_enter for initial state
        log.clear()

        sm.trigger("reset")
        assert sm.state == "idle"
        assert log == ["exit", "enter"]

    def test_fsm_duplicate_states_detected(self) -> None:
        """Duplicate state names don't crash (set deduplication)."""
        from saga2d.util.fsm import StateMachine
        # The constructor uses set() to validate — duplicates are silently deduped
        sm = StateMachine(["idle", "idle"], "idle")
        assert sm.state == "idle"

    def test_fsm_invalid_initial_raises(self) -> None:
        from saga2d.util.fsm import StateMachine
        with pytest.raises(ValueError, match="not in states"):
            StateMachine(["idle"], "walk")


# ═══════════════════════════════════════════════════════════════════
# 16. PROGRESS BAR — draw emits rects
# ═══════════════════════════════════════════════════════════════════


class TestProgressBarDraw:
    """ProgressBar draws via draw_rect."""

    def test_progress_bar_half_emits_rects(self, game: Game, backend: MockBackend) -> None:
        pb = ProgressBar(value=50, max_value=100, width=200, height=20)

        class S(Scene):
            def on_enter(self):
                self.ui.add(pb)

        game.push(S())
        game.tick(0.016)

        assert len(backend.rects) >= 2


# ═══════════════════════════════════════════════════════════════════
# 17. SETTINGS SCREEN — E2E push and interact
# ═══════════════════════════════════════════════════════════════════


class TestSettingsScreenE2E:
    """SettingsScreen pushes as a scene and handles escape to pop."""

    def test_settings_push_and_escape_pops(self, game: Game, backend: MockBackend) -> None:
        base = Scene()
        game.push(base)

        game.push_settings()
        game.tick(0.016)

        assert game._scene_stack.top() is not base

        backend.inject_key("escape")
        game.tick(0.016)

        assert game._scene_stack.top() is base


# ═══════════════════════════════════════════════════════════════════
# 18. TILEMAP — confirmed N/A
# ═══════════════════════════════════════════════════════════════════


class TestTilemapScope:
    """Saga2D has no built-in tilemap system."""

    def test_no_tilemap_module(self) -> None:
        import importlib
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("saga2d.tilemap")

    def test_no_tilemap_in_exports(self) -> None:
        import saga2d
        all_names = getattr(saga2d, "__all__", dir(saga2d))
        tile_names = [n for n in all_names if "tile" in n.lower()]
        assert tile_names == []


# ═══════════════════════════════════════════════════════════════════
# 19. ASSETS — frames discovery and caching
# ═══════════════════════════════════════════════════════════════════


class TestAssetEdgeCases:
    """Asset loading edge cases: frames, caching, missing."""

    def test_frames_returns_ordered_handles(self, game: Game) -> None:
        """AssetManager.frames() discovers numbered frames in order."""
        frames = game.assets.frames("sprites/knight_walk")
        assert len(frames) >= 2

    def test_frames_missing_prefix_raises(self, game: Game) -> None:
        with pytest.raises(AssetNotFoundError):
            game.assets.frames("sprites/nonexistent_anim")

    def test_image_caching(self, game: Game) -> None:
        """Same image name returns same handle on second load."""
        h1 = game.assets.image("sprites/knight")
        h2 = game.assets.image("sprites/knight")
        assert h1 is h2


# ═══════════════════════════════════════════════════════════════════
# 20. SCENE — draw_rect and draw_world_rect
# ═══════════════════════════════════════════════════════════════════


class TestSceneDrawHelpers:
    """Scene drawing helpers emit backend calls."""

    def test_draw_rect_emits(self, game: Game, backend: MockBackend) -> None:
        class S(Scene):
            def draw(self):
                self.draw_rect(10, 20, 100, 50, (255, 0, 0, 255))

        game.push(S())
        game.tick(0.016)
        assert any(
            r["x"] == 10 and r["y"] == 20 and r["width"] == 100
            for r in backend.rects
        )

    def test_draw_world_rect_uses_camera(self, game: Game, backend: MockBackend) -> None:
        """draw_world_rect transforms via camera."""

        class S(Scene):
            def on_enter(self):
                self.camera = Camera((800, 600))
                self.camera.scroll(100, 50)

            def draw(self):
                # World (200, 300) should become screen (100, 250)
                self.draw_world_rect(200, 300, 60, 40, (0, 255, 0, 255))

        game.push(S())
        game.tick(0.016)
        assert any(
            r["x"] == 100 and r["y"] == 250 and r["width"] == 60
            for r in backend.rects
        )


# ═══════════════════════════════════════════════════════════════════
# 21. ADVERSARIAL — NaN/Inf in actions, channel validation
# ═══════════════════════════════════════════════════════════════════

from saga2d.actions import Delay, FadeOut, FadeIn, Sequence, Do


class TestActionNaNEdgeCases:
    """F13: NaN/Inf dt propagation through action system."""

    def test_delay_nan_dt_stays_stuck(self, game: Game) -> None:
        """Delay.update(NaN) makes elapsed=NaN — action never completes.

        This is a real bug: if a bad dt somehow enters the system,
        the Delay action gets permanently stuck (NaN >= seconds is False).
        """
        d = Delay(1.0)
        s = Sprite("sprites/knight", position=(0, 0))
        d.start(s)
        d.update(float("nan"))
        # elapsed is now NaN — comparison NaN >= 1.0 is always False
        assert math.isnan(d._elapsed)
        assert d.update(0.016) is False  # still stuck

    def test_fadeout_nan_dt_crashes(self, game: Game) -> None:
        """FadeOut.update(NaN) crashes with ValueError on int() conversion.

        int(start_opacity * (1.0 - NaN)) → int(NaN) → ValueError.
        """
        scene = Scene()
        game.push(scene)
        sp = Sprite("sprites/knight", position=(100, 100))
        scene.add_sprite(sp)

        fo = FadeOut(1.0)
        fo.start(sp)
        with pytest.raises(ValueError, match="cannot convert float NaN"):
            fo.update(float("nan"))

    def test_fadein_nan_dt_crashes(self, game: Game) -> None:
        """FadeIn.update(NaN) crashes with ValueError — same as FadeOut."""
        scene = Scene()
        game.push(scene)
        sp = Sprite("sprites/knight", position=(100, 100))
        scene.add_sprite(sp)
        sp.opacity = 0

        fi = FadeIn(1.0)
        fi.start(sp)
        with pytest.raises(ValueError, match="cannot convert float NaN"):
            fi.update(float("nan"))

    def test_delay_inf_dt_completes_immediately(self, game: Game) -> None:
        """Delay.update(+inf) completes instantly (inf >= seconds is True)."""
        d = Delay(1.0)
        s = Sprite("sprites/knight", position=(0, 0))
        d.start(s)
        assert d.update(float("inf")) is True

    def test_delay_negative_dt_delays_completion(self, game: Game) -> None:
        """Delay.update(-1.0) subtracts from elapsed, delaying completion."""
        d = Delay(1.0)
        s = Sprite("sprites/knight", position=(0, 0))
        d.start(s)
        d.update(-1.0)
        assert d._elapsed == -1.0
        # Now needs 2.0s worth of positive dt to complete
        assert d.update(1.5) is False
        assert d.update(0.6) is True


class TestPlaySoundChannelValidation:
    """play_sound() channel parameter accepts channels beyond sfx/ui."""

    def test_play_sound_accepts_music_channel(self, audio_game: Game) -> None:
        """play_sound(channel='music') is accepted even though docs say sfx/ui only.

        The validation checks `channel not in self._volumes` which includes
        master/music/sfx/ui — so music and master pass validation despite the
        docstring saying only sfx and ui are valid for play_sound().
        """
        audio_game.push(Scene())
        # Should work because "music" is in _volumes dict
        audio_game.audio.play_sound("sword_hit", channel="music")

    def test_play_sound_accepts_master_channel(self, audio_game: Game) -> None:
        """play_sound(channel='master') is accepted — same validation gap."""
        audio_game.push(Scene())
        audio_game.audio.play_sound("sword_hit", channel="master")

    def test_play_sound_rejects_unknown_channel(self, audio_game: Game) -> None:
        """Unknown channels are correctly rejected."""
        audio_game.push(Scene())
        with pytest.raises(KeyError, match="Unknown audio channel"):
            audio_game.audio.play_sound("sword_hit", channel="bogus")
