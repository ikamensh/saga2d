"""Stage 5 asset/resource edge-case probes — runtime verification.

Each probe exercises a specific edge case with actual runtime interaction,
records the outcome, and asserts expected behavior. Runs headlessly.

Run from repo root::

    uv run python scripts/stage5_asset_probe.py
"""

from __future__ import annotations

import json
import math
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

# Results accumulator
results: list[tuple[str, str, str]] = []  # (id, description, outcome)
bugs: list[tuple[str, str, str]] = []  # (id, description, details)


def probe(pid: str, desc: str):
    """Decorator that wraps a probe function with try/except and result tracking."""
    def wrapper(fn):
        def run():
            try:
                fn()
                results.append((pid, desc, "PASS"))
            except AssertionError as e:
                results.append((pid, desc, f"BUG: {e}"))
                bugs.append((pid, desc, str(e)))
            except Exception as e:
                results.append((pid, desc, f"ERROR: {type(e).__name__}: {e}"))
                bugs.append((pid, desc, f"{type(e).__name__}: {e}"))
        return run
    return wrapper


# ── Helpers ──────────────────────────────────────────────────────────────

def make_game(asset_root: Path):
    """Create a fresh Game with mock backend."""
    from saga2d import Game
    return Game("ProbeTest", backend="mock", resolution=(800, 600), asset_path=asset_root)


def make_asset_dir(root: Path, subdirs=("images/sprites",)):
    """Create temp asset directory structure."""
    for sub in subdirs:
        (root / sub).mkdir(parents=True, exist_ok=True)


def teardown(game):
    """Safely teardown game."""
    try:
        game._teardown()
    except Exception:
        pass


# ── Probe functions ──────────────────────────────────────────────────────

# --- Asset loading: missing files ---

@probe("A1", "Sprite with nonexistent image raises AssetNotFoundError")
def probe_a1():
    from saga2d import Game, Sprite
    from saga2d.assets import AssetNotFoundError
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    game = make_game(root)
    try:
        try:
            s = Sprite("sprites/nonexistent", position=(0, 0))
            assert False, "Should have raised AssetNotFoundError"
        except AssetNotFoundError as e:
            assert "nonexistent" in str(e), f"Error message unhelpful: {e}"
            assert "not found" in str(e).lower(), f"Error lacks 'not found': {e}"
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A2", "Sprite with empty string image name raises AssetNotFoundError")
def probe_a2():
    from saga2d import Game, Sprite
    from saga2d.assets import AssetNotFoundError
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    game = make_game(root)
    try:
        try:
            s = Sprite("", position=(0, 0))
            assert False, "Should have raised AssetNotFoundError"
        except AssetNotFoundError:
            pass  # Expected
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A3", "AssetManager.sound() with missing sound raises AssetNotFoundError")
def probe_a3():
    from saga2d.assets import AssetNotFoundError
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root, ("sounds",))
    game = make_game(root)
    try:
        try:
            game.assets.sound("missing_sfx")
            assert False, "Should have raised AssetNotFoundError"
        except AssetNotFoundError as e:
            assert ".wav" in str(e), f"Error should list tried .wav: {e}"
            assert ".ogg" in str(e), f"Error should list tried .ogg: {e}"
            assert ".mp3" in str(e), f"Error should list tried .mp3: {e}"
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A4", "AssetManager.music() with missing music raises AssetNotFoundError")
def probe_a4():
    from saga2d.assets import AssetNotFoundError
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root, ("music",))
    game = make_game(root)
    try:
        try:
            game.assets.music("missing_track")
            assert False, "Should have raised AssetNotFoundError"
        except AssetNotFoundError as e:
            assert ".ogg" in str(e), f"Error should list tried .ogg: {e}"
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A5", "AssetManager.frames() with no matching frames raises AssetNotFoundError")
def probe_a5():
    from saga2d.assets import AssetNotFoundError
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    game = make_game(root)
    try:
        try:
            game.assets.frames("sprites/nonexistent_walk")
            assert False, "Should have raised AssetNotFoundError"
        except AssetNotFoundError as e:
            assert "nonexistent_walk" in str(e)
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A6", "AudioManager.play_sound(optional=True) silences missing asset")
def probe_a6():
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root, ("sounds",))
    game = make_game(root)
    try:
        result = game.audio.play_sound("missing_sfx", optional=True)
        assert result is None, f"Expected None, got {result}"
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A7", "AudioManager.play_music(optional=True) silences missing asset")
def probe_a7():
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root, ("music",))
    game = make_game(root)
    try:
        result = game.audio.play_music("missing_track", optional=True)
        assert result is None, f"Expected None, got {result}"
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A8", "AudioManager.crossfade_music() with missing target raises AssetNotFoundError")
def probe_a8():
    from saga2d.assets import AssetNotFoundError
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root, ("music",))
    (root / "music" / "track_a.ogg").write_bytes(b"ogg")
    game = make_game(root)
    try:
        game.audio.play_music("track_a")
        try:
            game.audio.crossfade_music("nonexistent_track")
            assert False, "Should have raised AssetNotFoundError"
        except AssetNotFoundError:
            pass  # Expected — no optional flag on crossfade
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A9", "AssetManager.image() caching: same name returns same handle")
def probe_a9():
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    (root / "images" / "sprites" / "hero.png").write_bytes(b"png")
    game = make_game(root)
    try:
        h1 = game.assets.image("sprites/hero")
        h2 = game.assets.image("sprites/hero")
        assert h1 == h2, f"Cached handles differ: {h1} vs {h2}"
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A10", "AssetManager.sound() caching: same name returns same handle")
def probe_a10():
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root, ("sounds",))
    (root / "sounds" / "click.wav").write_bytes(b"wav")
    game = make_game(root)
    try:
        h1 = game.assets.sound("click")
        h2 = game.assets.sound("click")
        assert h1 == h2, f"Cached handles differ: {h1} vs {h2}"
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


# --- Asset loading: corrupt files (mock backend behavior) ---

@probe("A11", "Sprite with corrupt PNG file (mock backend accepts it - no content validation)")
def probe_a11():
    """Mock backend doesn't read file contents, so corrupt files don't error."""
    from saga2d import Sprite
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    (root / "images" / "sprites" / "corrupt.png").write_bytes(b"\x00\x01BAD")
    game = make_game(root)
    try:
        s = Sprite("sprites/corrupt", position=(100, 100))
        assert not s.is_removed, "Sprite should be created (mock doesn't validate content)"
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A12", "Zero-byte image file (mock backend accepts it)")
def probe_a12():
    from saga2d import Sprite
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    (root / "images" / "sprites" / "empty.png").write_bytes(b"")
    game = make_game(root)
    try:
        s = Sprite("sprites/empty", position=(100, 100))
        assert not s.is_removed
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


# --- ColorSwap edge cases ---

@probe("A13", "ColorSwap with unregistered palette raises KeyError")
def probe_a13():
    from saga2d import Sprite
    from saga2d.rendering.color_swap import get_palette
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    (root / "images" / "sprites" / "knight.png").write_bytes(b"png")
    game = make_game(root)
    try:
        try:
            get_palette("nonexistent_team")
            assert False, "Should have raised KeyError"
        except KeyError as e:
            assert "nonexistent_team" in str(e)
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A14", "Sprite with unregistered team_palette raises KeyError")
def probe_a14():
    from saga2d import Sprite
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    (root / "images" / "sprites" / "knight.png").write_bytes(b"png")
    game = make_game(root)
    try:
        try:
            s = Sprite("sprites/knight", team_palette="blue_team")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass  # Expected
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A15", "ColorSwap source/target length mismatch raises ValueError")
def probe_a15():
    from saga2d.rendering.color_swap import ColorSwap
    try:
        swap = ColorSwap(
            source_colors=[(255, 0, 0), (0, 255, 0)],
            target_colors=[(0, 0, 255)],  # mismatched length
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected


# --- CursorManager edge cases ---

@probe("A16", "CursorManager.register() with missing image raises AssetNotFoundError")
def probe_a16():
    from saga2d.assets import AssetNotFoundError
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root, ("images/ui",))
    game = make_game(root)
    try:
        try:
            game.cursor.register("attack", "ui/nonexistent_cursor")
            assert False, "Should have raised AssetNotFoundError"
        except AssetNotFoundError:
            pass  # Expected
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A17", "CursorManager.set() with unregistered cursor raises KeyError")
def probe_a17():
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    game = make_game(root)
    try:
        try:
            game.cursor.set("nonexistent")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass  # Expected
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


# --- ParticleEmitter deferred validation ---

@probe("A18", "ParticleEmitter with nonexistent image — no error at construction, error at spawn")
def probe_a18():
    from saga2d import Scene, Sprite
    from saga2d.assets import AssetNotFoundError
    from saga2d.rendering.particles import ParticleEmitter
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    game = make_game(root)
    try:
        # Construction should succeed (no image validation at init)
        emitter = ParticleEmitter("sprites/nonexistent_particle",
                                   position=(100, 100),
                                   speed=(10, 50),
                                   direction=(0, 360),
                                   lifetime=(0.5, 1.0))
        # burst() should fail because Sprite creation will fail
        try:
            emitter.burst(5)
            assert False, "Should have raised AssetNotFoundError on spawn"
        except AssetNotFoundError:
            pass  # Expected — deferred validation
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


# --- SaveManager edge cases ---

@probe("S1", "SaveManager.load() empty slot returns None")
def probe_s1():
    from saga2d.save import SaveManager
    root = Path(tempfile.mkdtemp())
    mgr = SaveManager(root / "saves")
    try:
        result = mgr.load(1)
        assert result is None, f"Expected None, got {result}"
    finally:
        shutil.rmtree(root, ignore_errors=True)


@probe("S2", "SaveManager.save() creates directory and writes file")
def probe_s2():
    from saga2d.save import SaveManager
    root = Path(tempfile.mkdtemp())
    save_dir = root / "nonexistent" / "saves"
    mgr = SaveManager(save_dir)
    try:
        mgr.save(1, {"hp": 100}, "TestScene")
        assert save_dir.exists(), "Save dir not created"
        data = mgr.load(1)
        assert data is not None
        assert data["state"]["hp"] == 100
    finally:
        shutil.rmtree(root, ignore_errors=True)


@probe("S3", "SaveManager.load() corrupt JSON raises SaveError")
def probe_s3():
    from saga2d.save import SaveError, SaveManager
    root = Path(tempfile.mkdtemp())
    save_dir = root / "saves"
    save_dir.mkdir(parents=True)
    (save_dir / "save_1.json").write_text("{bad json", encoding="utf-8")
    mgr = SaveManager(save_dir)
    try:
        try:
            mgr.load(1)
            assert False, "Should have raised SaveError"
        except SaveError as e:
            assert "slot 1" in str(e).lower() or "slot 1" in str(e)
            assert "delete" in str(e).lower(), f"Missing recovery hint: {e}"
    finally:
        shutil.rmtree(root, ignore_errors=True)


@probe("S4", "SaveManager.load() non-dict JSON (array) raises SaveError")
def probe_s4():
    from saga2d.save import SaveError, SaveManager
    root = Path(tempfile.mkdtemp())
    save_dir = root / "saves"
    save_dir.mkdir(parents=True)
    (save_dir / "save_1.json").write_text("[1, 2, 3]", encoding="utf-8")
    mgr = SaveManager(save_dir)
    try:
        try:
            mgr.load(1)
            assert False, "Should have raised SaveError"
        except SaveError as e:
            assert "expected JSON object" in str(e).lower() or "expected json object" in str(e).lower()
    finally:
        shutil.rmtree(root, ignore_errors=True)


@probe("S5", "SaveManager.load() binary garbage raises SaveError")
def probe_s5():
    from saga2d.save import SaveError, SaveManager
    root = Path(tempfile.mkdtemp())
    save_dir = root / "saves"
    save_dir.mkdir(parents=True)
    (save_dir / "save_1.json").write_bytes(b"\x80\x81\x82\xff\xfe")
    mgr = SaveManager(save_dir)
    try:
        try:
            mgr.load(1)
            assert False, "Should have raised SaveError"
        except SaveError:
            pass  # Expected — UnicodeDecodeError wrapped
    finally:
        shutil.rmtree(root, ignore_errors=True)


@probe("S6", "SaveManager.load() zero-byte file raises SaveError")
def probe_s6():
    from saga2d.save import SaveError, SaveManager
    root = Path(tempfile.mkdtemp())
    save_dir = root / "saves"
    save_dir.mkdir(parents=True)
    (save_dir / "save_1.json").write_text("", encoding="utf-8")
    mgr = SaveManager(save_dir)
    try:
        try:
            mgr.load(1)
            assert False, "Should have raised SaveError"
        except SaveError:
            pass  # Expected — json.JSONDecodeError wrapped
    finally:
        shutil.rmtree(root, ignore_errors=True)


@probe("S7", "SaveManager.save() with non-serializable state raises SaveError")
def probe_s7():
    from saga2d.save import SaveError, SaveManager
    root = Path(tempfile.mkdtemp())
    mgr = SaveManager(root / "saves")
    try:
        try:
            mgr.save(1, {"callback": lambda: None}, "TestScene")
            assert False, "Should have raised SaveError"
        except SaveError as e:
            assert "slot 1" in str(e)
    finally:
        shutil.rmtree(root, ignore_errors=True)


@probe("S8", "SaveManager slot validation: slot=0, slot=-1, slot=float")
def probe_s8():
    from saga2d.save import SaveManager
    root = Path(tempfile.mkdtemp())
    mgr = SaveManager(root / "saves")
    try:
        # slot < 1
        try:
            mgr.load(0)
            assert False, "slot=0 should raise ValueError"
        except ValueError:
            pass
        try:
            mgr.load(-1)
            assert False, "slot=-1 should raise ValueError"
        except ValueError:
            pass
        # slot not int
        try:
            mgr.load(1.5)
            assert False, "slot=float should raise TypeError"
        except TypeError:
            pass
        try:
            mgr.load("1")
            assert False, "slot=str should raise TypeError"
        except TypeError:
            pass
    finally:
        shutil.rmtree(root, ignore_errors=True)


@probe("S9", "SaveManager.delete() on nonexistent slot is silent no-op")
def probe_s9():
    from saga2d.save import SaveManager
    root = Path(tempfile.mkdtemp())
    mgr = SaveManager(root / "saves")
    try:
        mgr.delete(99)  # Should not raise
    finally:
        shutil.rmtree(root, ignore_errors=True)


@probe("S10", "SaveManager.delete() on existing slot removes file")
def probe_s10():
    from saga2d.save import SaveManager
    root = Path(tempfile.mkdtemp())
    save_dir = root / "saves"
    mgr = SaveManager(save_dir)
    try:
        mgr.save(1, {"x": 1}, "T")
        assert mgr.load(1) is not None
        mgr.delete(1)
        assert mgr.load(1) is None, "Slot not deleted"
    finally:
        shutil.rmtree(root, ignore_errors=True)


@probe("S11", "SaveManager.list_slots() with mix of valid, empty, and corrupt")
def probe_s11():
    from saga2d.save import SaveError, SaveManager
    root = Path(tempfile.mkdtemp())
    save_dir = root / "saves"
    mgr = SaveManager(save_dir)
    try:
        mgr.save(1, {"level": 1}, "Scene1")
        # Slot 2 = empty (no file)
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_3.json").write_text("NOT JSON", encoding="utf-8")
        # list_slots should fail on slot 3 (corrupt)
        try:
            mgr.list_slots(count=3)
            assert False, "Should have raised SaveError for corrupt slot 3"
        except SaveError:
            pass  # Expected
    finally:
        shutil.rmtree(root, ignore_errors=True)


# --- Audio channel edge cases ---

@probe("AU1", "AudioManager.set_volume() unknown channel raises KeyError")
def probe_au1():
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    game = make_game(root)
    try:
        try:
            game.audio.set_volume("nonexistent_channel", 0.5)
            assert False, "Should have raised KeyError"
        except KeyError:
            pass
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("AU2", "AudioManager.play_sound() unknown channel raises KeyError")
def probe_au2():
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root, ("sounds",))
    (root / "sounds" / "click.wav").write_bytes(b"wav")
    game = make_game(root)
    try:
        try:
            game.audio.play_sound("click", channel="nonexistent")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("AU3", "AudioManager.crossfade_music() with NaN duration raises ValueError")
def probe_au3():
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root, ("music",))
    (root / "music" / "a.ogg").write_bytes(b"ogg")
    (root / "music" / "b.ogg").write_bytes(b"ogg")
    game = make_game(root)
    try:
        game.audio.play_music("a")
        try:
            game.audio.crossfade_music("b", duration=float('nan'))
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("AU4", "AudioManager.crossfade_music() with negative duration raises ValueError")
def probe_au4():
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root, ("music",))
    (root / "music" / "a.ogg").write_bytes(b"ogg")
    (root / "music" / "b.ogg").write_bytes(b"ogg")
    game = make_game(root)
    try:
        game.audio.play_music("a")
        try:
            game.audio.crossfade_music("b", duration=-1.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("AU5", "AudioManager.play_pool() with unregistered pool raises KeyError")
def probe_au5():
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    game = make_game(root)
    try:
        try:
            game.audio.play_pool("nonexistent_pool")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


# --- Sprite.image setter with missing asset ---

@probe("A19", "Sprite.image setter with nonexistent name raises AssetNotFoundError")
def probe_a19():
    from saga2d import Sprite
    from saga2d.assets import AssetNotFoundError
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    (root / "images" / "sprites" / "hero.png").write_bytes(b"png")
    game = make_game(root)
    try:
        s = Sprite("sprites/hero", position=(100, 100))
        try:
            s.image = "sprites/nonexistent"
            assert False, "Should have raised AssetNotFoundError"
        except AssetNotFoundError:
            pass
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


# --- AnimationDef with missing frames ---

@probe("A20", "AnimationDef with frame_duration=0 raises ValueError")
def probe_a20():
    from saga2d.animation import AnimationDef
    try:
        AnimationDef(frames=["a", "b"], frame_duration=0.0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


@probe("A21", "AnimationDef with frame_duration<0 raises ValueError")
def probe_a21():
    from saga2d.animation import AnimationDef
    try:
        AnimationDef(frames=["a", "b"], frame_duration=-0.1)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


@probe("A22", "AnimationDef with NaN frame_duration raises ValueError")
def probe_a22():
    from saga2d.animation import AnimationDef
    try:
        AnimationDef(frames=["a", "b"], frame_duration=float('nan'))
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


@probe("A23", "Sprite.play() with missing frame images raises AssetNotFoundError")
def probe_a23():
    from saga2d import Sprite
    from saga2d.animation import AnimationDef
    from saga2d.assets import AssetNotFoundError
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    (root / "images" / "sprites" / "hero.png").write_bytes(b"png")
    game = make_game(root)
    try:
        s = Sprite("sprites/hero", position=(100, 100))
        anim = AnimationDef(frames=["sprites/missing_frame_01", "sprites/missing_frame_02"],
                            frame_duration=0.1)
        try:
            s.play(anim)
            assert False, "Should have raised AssetNotFoundError"
        except AssetNotFoundError:
            pass
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


# --- SaveManager.delete() doesn't wrap PermissionError ---

@probe("S12", "SaveManager.delete() slot validation works")
def probe_s12():
    from saga2d.save import SaveManager
    root = Path(tempfile.mkdtemp())
    mgr = SaveManager(root / "saves")
    try:
        try:
            mgr.delete(0)
            assert False, "slot=0 should raise ValueError"
        except ValueError:
            pass
        try:
            mgr.delete("1")
            assert False, "slot=str should raise TypeError"
        except TypeError:
            pass
    finally:
        shutil.rmtree(root, ignore_errors=True)


# --- Sprite created after teardown ---

@probe("A24", "Sprite creation after Game teardown raises RuntimeError")
def probe_a24():
    from saga2d import Game, Sprite
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    (root / "images" / "sprites" / "hero.png").write_bytes(b"png")
    game = make_game(root)
    game._teardown()
    try:
        try:
            s = Sprite("sprites/hero", position=(0, 0))
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "No active Game" in str(e)
    finally:
        shutil.rmtree(root, ignore_errors=True)


# --- @2x variant selection ---

@probe("A25", "@2x image variant selected when scale_factor >= 1.5")
def probe_a25():
    from saga2d import Game
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    (root / "images" / "sprites" / "hero.png").write_bytes(b"png_base")
    (root / "images" / "sprites" / "hero@2x.png").write_bytes(b"png_2x")
    # Need a game with scale_factor >= 1.5 on the asset manager
    game = Game("ProbeTest", backend="mock", resolution=(800, 600), asset_path=root)
    # Override asset manager scale factor
    from saga2d.assets import AssetManager
    game.assets = AssetManager(game.backend, base_path=root, scale_factor=2.0)
    try:
        h = game.assets.image("sprites/hero")
        # Verify the @2x path was used by checking the loaded images in backend
        loaded = game.backend._loaded_images
        has_2x = any("@2x" in path for path in loaded.keys())
        assert has_2x, f"@2x variant not selected. Loaded: {list(loaded.keys())}"
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


@probe("A26", "Base image used when scale_factor < 1.5 (no @2x)")
def probe_a26():
    from saga2d import Game
    root = Path(tempfile.mkdtemp())
    make_asset_dir(root)
    (root / "images" / "sprites" / "hero.png").write_bytes(b"png_base")
    (root / "images" / "sprites" / "hero@2x.png").write_bytes(b"png_2x")
    game = Game("ProbeTest", backend="mock", resolution=(800, 600), asset_path=root)
    try:
        h = game.assets.image("sprites/hero")
        loaded = game.backend._loaded_images
        has_2x = any("@2x" in path for path in loaded.keys())
        assert not has_2x, f"@2x should not be selected at scale 1.0. Loaded: {list(loaded.keys())}"
    finally:
        teardown(game)
        shutil.rmtree(root, ignore_errors=True)


# --- FSM edge cases (bonus) ---

@probe("F1", "FSM transition to unknown event is silent no-op or raises")
def probe_f1():
    from saga2d.util.fsm import StateMachine
    sm = StateMachine(
        states=["idle", "walking"],
        initial="idle",
        transitions={"idle": {"walk": "walking"}},
    )
    assert sm.state == "idle"
    # Trigger a valid transition
    sm.trigger("walk")
    assert sm.state == "walking", f"Expected 'walking', got {sm.state}"
    # Trigger an unknown event — should not crash
    try:
        sm.trigger("nonexistent_event")
        # If no exception, state should be unchanged
        assert sm.state == "walking", f"State changed on unknown event: {sm.state}"
    except (ValueError, KeyError):
        pass  # Also acceptable — explicit rejection


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    probes = [v for v in globals().values() if callable(v) and hasattr(v, '__wrapped__') is False
              and getattr(v, '__name__', '').startswith('run') is False]

    # Collect all probe_* functions
    probe_fns = []
    for name in sorted(globals()):
        val = globals()[name]
        if name.startswith("probe_") and callable(val):
            probe_fns.append(val)

    print(f"Running {len(probe_fns)} probes...\n")
    for fn in probe_fns:
        fn()

    # Print results
    pass_count = sum(1 for _, _, o in results if o == "PASS")
    bug_count = len(bugs)
    print(f"\n{'='*60}")
    print(f"Stage 5 Asset/Resource Edge-Case Probes")
    print(f"{'='*60}")
    for pid, desc, outcome in results:
        status = "✓" if outcome == "PASS" else "✗"
        print(f"  {status} [{pid}] {desc}: {outcome}")

    print(f"\n{pass_count}/{len(results)} passed, {bug_count} bugs found")

    if bugs:
        print(f"\nBUGS FOUND:")
        for pid, desc, details in bugs:
            print(f"  [{pid}] {desc}")
            print(f"         {details}")
        sys.exit(1)
    else:
        print("\nPASS — all asset/resource edge cases handled correctly")


if __name__ == "__main__":
    main()
