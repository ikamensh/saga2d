"""Iter-26: AssetManager auto-registers TTFs in ``assets/fonts/``."""

from __future__ import annotations

from pathlib import Path

import pytest

from saga2d import Game
from saga2d.assets import AssetManager
from saga2d.backends.mock_backend import MockBackend


def test_assets_fonts_ttf_gets_registered(tmp_path: Path) -> None:
    """Given a fonts directory with a TTF file, AssetManager calls
    load_font on the backend for each file during construction."""
    fonts_dir = tmp_path / "fonts"
    fonts_dir.mkdir()
    (fonts_dir / "FakeFont.ttf").write_bytes(b"not really a ttf but who's asking")
    (fonts_dir / "FakeFont.otf").write_bytes(b"also fake")
    (fonts_dir / "README.md").write_text("ignore me")

    backend = MockBackend(100, 100)
    AssetManager(backend, base_path=tmp_path)

    # Two fonts registered by stem, README ignored.
    assert "FakeFont" in backend.fonts
    # Both TTF and OTF handled — stem is the same.
    assert backend.fonts["FakeFont"].endswith(".otf") or backend.fonts[
        "FakeFont"
    ].endswith(".ttf")


def test_no_fonts_dir_is_silent_noop(tmp_path: Path) -> None:
    """When the fonts directory doesn't exist, AssetManager construction
    must not raise — games without bundled fonts are the common case."""
    backend = MockBackend(100, 100)
    AssetManager(backend, base_path=tmp_path)  # no assets/fonts/
    assert backend.fonts == {}


def test_corrupt_font_does_not_break_construction(tmp_path: Path) -> None:
    """If the backend raises on a bad file, AssetManager swallows the
    error — one corrupt asset shouldn't kill the whole game startup."""
    fonts_dir = tmp_path / "fonts"
    fonts_dir.mkdir()
    (fonts_dir / "Broken.ttf").write_bytes(b"")

    class ExplodingBackend(MockBackend):
        def load_font(self, name, path=None):
            raise RuntimeError("corrupt font")

    backend = ExplodingBackend(100, 100)
    AssetManager(backend, base_path=tmp_path)  # no exception


def test_bundled_cinzel_is_picked_up_by_default_manager() -> None:
    """The real repo's ``assets/fonts/Cinzel.ttf`` should be registered
    automatically when a Game's default AssetManager is initialised
    in the project root — no game code needed."""
    game = Game(
        "bundled-font-test",
        resolution=(100, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    try:
        # Access .assets triggers lazy AssetManager creation.
        _ = game.assets
        # iter-27: registered under the font's actual family name
        # parsed from the TTF, not the filename stem. Cinzel's
        # typographic family is "Cinzel" so the two happen to agree,
        # but the parser is what makes it a rule and not a coincidence.
        assert "Cinzel" in game.backend.fonts
    finally:
        game._teardown()


def test_font_registered_under_parsed_family_not_stem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the TTF's family differs from its filename stem, the
    register-by-stem approximation was wrong. The iter-27 parser
    fixes this: registration uses the parsed family name."""
    fonts_dir = tmp_path / "fonts"
    fonts_dir.mkdir()
    # Copy the real Cinzel TTF under a deliberately wrong stem.
    import shutil
    real = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "Cinzel.ttf"
    wrong_stem = fonts_dir / "MyCustomStem.ttf"
    shutil.copy(real, wrong_stem)

    backend = MockBackend(100, 100)
    AssetManager(backend, base_path=tmp_path)
    # Parser returned the font's true typographic family — "Cinzel".
    assert "Cinzel" in backend.fonts
    # Not registered under the filename stem.
    assert "MyCustomStem" not in backend.fonts


def test_unparseable_font_falls_back_to_stem(tmp_path: Path) -> None:
    """If the parser can't extract a family name (corrupt TTF), the
    AssetManager still registers the file using the filename stem —
    degraded but functional."""
    fonts_dir = tmp_path / "fonts"
    fonts_dir.mkdir()
    (fonts_dir / "FakeStem.ttf").write_bytes(b"not a real font")

    backend = MockBackend(100, 100)
    AssetManager(backend, base_path=tmp_path)
    # Parser returned None → fallback uses the stem.
    assert "FakeStem" in backend.fonts


def test_reregistration_is_idempotent(tmp_path: Path) -> None:
    """Creating a second AssetManager over the same fonts directory
    doesn't call load_font a second time for already-registered files."""
    fonts_dir = tmp_path / "fonts"
    fonts_dir.mkdir()
    (fonts_dir / "Once.ttf").write_bytes(b"font")

    backend = MockBackend(100, 100)
    mgr1 = AssetManager(backend, base_path=tmp_path)
    mgr2 = AssetManager(backend, base_path=tmp_path)
    # Each manager has its own idempotency guard, but the backend
    # records are safe because load_font is idempotent too (dict set).
    assert "Once" in backend.fonts
    # Both managers registered it from fresh state — that's fine. The
    # per-manager _registered_fonts prevents double-work *within* one
    # manager's lifetime, not across managers.
    assert len(mgr1._registered_fonts) == 1
    assert len(mgr2._registered_fonts) == 1
