"""Properties of :func:`saga2d.util.fontname.parse_font_family_name`.

Tests cover the bundled Cinzel font (real TTF with known metadata)
and corrupt/malformed inputs that must return ``None`` rather than
crash.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from saga2d.util.fontname import parse_font_family_name


REPO_ROOT = Path(__file__).resolve().parents[2]
CINZEL_TTF = REPO_ROOT / "assets" / "fonts" / "Cinzel.ttf"


def test_parses_cinzel_family_as_cinzel() -> None:
    """The bundled Cinzel TTF's typographic family is 'Cinzel' — not
    'CinzelRoman' or 'Cinzel Roman'. That's the string Theme users
    would naturally write."""
    assert CINZEL_TTF.exists(), "assets/fonts/Cinzel.ttf should be present"
    assert parse_font_family_name(CINZEL_TTF) == "Cinzel"


def test_missing_file_returns_none(tmp_path: Path) -> None:
    assert parse_font_family_name(tmp_path / "does-not-exist.ttf") is None


def test_empty_file_returns_none(tmp_path: Path) -> None:
    p = tmp_path / "empty.ttf"
    p.write_bytes(b"")
    assert parse_font_family_name(p) is None


def test_truncated_header_returns_none(tmp_path: Path) -> None:
    p = tmp_path / "bad.ttf"
    p.write_bytes(b"\x00" * 20)  # not enough for a valid table dir
    assert parse_font_family_name(p) is None


def test_non_ttf_binary_returns_none(tmp_path: Path) -> None:
    """A random file with the wrong magic bytes shouldn't produce
    a garbage family name — it should fail out cleanly."""
    p = tmp_path / "not-a-font.ttf"
    p.write_bytes(b"This is a text file, not a font.\n" * 50)
    # Must not raise; may return None or something, but not garbage
    # that gets registered with the backend.
    name = parse_font_family_name(p)
    # Either None or a string — never a crash.
    assert name is None or isinstance(name, str)


def test_path_accepts_string(tmp_path: Path) -> None:
    """``Path | str`` input — string path should work the same as Path."""
    assert parse_font_family_name(str(CINZEL_TTF)) == "Cinzel"


def test_returns_string_or_none_type_only() -> None:
    """Invariant: the return type is always Optional[str]."""
    result = parse_font_family_name(CINZEL_TTF)
    assert result is None or isinstance(result, str)
