"""Minimal TTF / OTF family-name extractor using only the stdlib.

Why not ``fontTools``? It's a heavyweight dependency for one 60-line
function. A saga2d game bundling ``assets/fonts/Cinzel.ttf`` shouldn't
pull in ~2MB of tables, glyph processing, and subsetting code just to
learn the internal family name.

Reads only the ``name`` table, returns the best family string for
each font file — the name :class:`Theme(font="…")` should match.
"""

from __future__ import annotations

import struct
from pathlib import Path

# Name table IDs per the OpenType spec.
# https://learn.microsoft.com/en-us/typography/opentype/spec/name
_NAME_ID_FAMILY = 1
_NAME_ID_FULL = 4
_NAME_ID_TYPOGRAPHIC_FAMILY = 16

# Platform IDs.
_PLATFORM_UNICODE = 0
_PLATFORM_MACINTOSH = 1
_PLATFORM_WINDOWS = 3


def parse_font_family_name(path: Path | str) -> str | None:
    """Return the font's preferred family name, or ``None`` on parse failure.

    Preference order:

    1. Typographic family (name_id=16) — variable fonts often set this
       to the user-facing family (``"Cinzel"``) while name_id=1 carries
       a subfamily-qualified form (``"CinzelRoman"``).
    2. Family (name_id=1) — every legal TTF has it.

    Among records with the same name_id, Windows-Unicode records are
    preferred over Macintosh because Windows stores UTF-16 strings
    cleanly.

    Best-effort: a malformed file, truncated name table, or encoding
    mismatch returns ``None``. Callers fall back to the filename stem.
    """
    try:
        return _parse_family_inner(Path(path))
    except (OSError, struct.error, UnicodeDecodeError):
        return None


def _parse_family_inner(path: Path) -> str | None:
    with path.open("rb") as f:
        # sfnt header: version(4), numTables(2), searchRange(2),
        # entrySelector(2), rangeShift(2).
        header = f.read(12)
        if len(header) < 12:
            return None
        _sfnt, num_tables = struct.unpack(">IH", header[:6])

        # Table directory — numTables entries of 16 bytes each.
        name_offset = None
        name_length = None
        for _ in range(num_tables):
            entry = f.read(16)
            if len(entry) < 16:
                return None
            tag = entry[:4]
            if tag == b"name":
                _, offset, length = struct.unpack(">III", entry[4:16])
                name_offset = offset
                name_length = length
                break
        if name_offset is None:
            return None

        # Read the name table — format(2), count(2), stringOffset(2),
        # then count * 12-byte name records, then the string pool.
        f.seek(name_offset)
        name_header = f.read(6)
        if len(name_header) < 6:
            return None
        _fmt, record_count, string_offset = struct.unpack(">HHH", name_header)
        records_raw = f.read(12 * record_count)
        if len(records_raw) < 12 * record_count:
            return None
        strings_start = name_offset + string_offset

        # Score records: prefer typographic-family (id=16) over family
        # (id=1), and Windows-Unicode over Macintosh.
        best_score = -1
        best_name: str | None = None
        for i in range(record_count):
            pid, eid, _lid, nid, length, offset = struct.unpack(
                ">HHHHHH", records_raw[i * 12 : (i + 1) * 12],
            )
            if nid not in (_NAME_ID_FAMILY, _NAME_ID_TYPOGRAPHIC_FAMILY):
                continue
            score = 0
            if nid == _NAME_ID_TYPOGRAPHIC_FAMILY:
                score += 10
            if pid == _PLATFORM_WINDOWS:
                score += 5
            elif pid == _PLATFORM_UNICODE:
                score += 3
            if score <= best_score:
                continue

            f.seek(strings_start + offset)
            raw = f.read(length)
            if len(raw) < length:
                continue
            try:
                if pid == _PLATFORM_WINDOWS or pid == _PLATFORM_UNICODE:
                    decoded = raw.decode("utf-16-be")
                elif pid == _PLATFORM_MACINTOSH:
                    decoded = raw.decode("mac-roman", errors="strict")
                else:
                    continue
            except UnicodeDecodeError:
                continue
            best_score = score
            best_name = decoded.strip()

        return best_name or None
