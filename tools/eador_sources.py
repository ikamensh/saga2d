"""Source files that fingerprint Shardbound evidence: the game, its tools and the installed framework.

The framework packages live outside this repository, so their files are found
through the imported modules and labelled ``saga2d/...`` and ``sagaforge/...``
in every hash table, exactly as they were when they were checked out beside the game.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import saga2d
import sagaforge

ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = {'saga2d': Path(saga2d.__file__).resolve().parent, 'sagaforge': Path(sagaforge.__file__).resolve().parent}


def framework_sources() -> list[Path]:
    """Every framework Python file, sorted, for evidence fingerprints."""
    return [path for package in FRAMEWORK.values() for path in sorted(package.rglob('*.py'))]


def source_name(path: Path | str) -> str:
    """The stable label of a source file: repository-relative, or ``<package>/...`` for the framework."""
    path = Path(path).resolve()
    for name, package in FRAMEWORK.items():
        if path.is_relative_to(package):
            return f'{name}/{path.relative_to(package).as_posix()}'
    return path.relative_to(ROOT).as_posix()


def source_path(name: str) -> Path:
    """The file behind a label produced by ``source_name``."""
    package, _, rest = name.partition('/')
    if package in FRAMEWORK:
        return FRAMEWORK[package] / rest
    return ROOT / name


def fingerprints(paths) -> dict[str, str]:
    return {source_name(path): hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in sorted(paths)}
