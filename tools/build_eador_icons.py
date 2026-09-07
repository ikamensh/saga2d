"""Build/check Shardbound's original precomputed icons at 25% CPU by default.

    uv run python tools/build_eador_icons.py
    uv run python tools/build_eador_icons.py --check

Only the finished PNGs are loaded during play; this generator needs no fonts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, __version__ as pillow_version

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.icon_art import GENERATOR_VERSION, ICONS, SIZE, render_icon  # noqa: E402
from tools.cpu_budget import CpuBudget  # noqa: E402


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_assets(directory: Path, *, budget: CpuBudget | None = None) -> dict:
    """Build the complete shipping catalogue with exact source and PNG hashes."""
    budget = CpuBudget() if budget is None else budget
    folder = directory / 'images/icons'
    folder.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, description in ICONS.items():
        target = folder / f'{name}.png'
        render_icon(name).save(target, format='PNG', optimize=True)
        files[f'images/icons/{name}.png'] = {
            'bytes': target.stat().st_size, 'sha256': _digest(target),
            'description': description,
        }
        budget.checkpoint()
    manifest = {
        'product': 'Shardbound', 'generator_version': GENERATOR_VERSION,
        'canvas': [SIZE, SIZE], 'designed_display_size': 24,
        'provenance': 'Original project-owned geometric illustration. No fonts, Unicode glyphs, external icon packs, images, or Eador assets.',
        'license': 'Repository MIT license; see LICENSE.',
        'runtime': 'Prebuilt transparent PNGs only; icon composition does not run during play.',
        'generator_dependencies': {'pillow': pillow_version},
        'source_sha256': {name: _digest(ROOT / name) for name in
                          ('eador/icon_art.py', 'tools/build_eador_icons.py', 'tools/cpu_budget.py')},
        'files': files,
    }
    (directory / 'icon-art-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    verify_assets(directory, budget=budget)
    return manifest


def verify_assets(directory: Path, *, budget: CpuBudget | None = None) -> int:
    """Check complete icon packaging, transparency geometry and composing sources."""
    budget = CpuBudget() if budget is None else budget
    manifest = json.loads((directory / 'icon-art-manifest.json').read_text())
    expected = {f'images/icons/{name}.png' for name in ICONS}
    actual = {path.relative_to(directory).as_posix() for path in (directory / 'images/icons').glob('*.png')}
    if set(manifest['files']) != expected or actual != expected:
        raise ValueError('Icon catalogue differs from its manifest')
    for name, record in manifest['files'].items():
        target = directory / name
        if _digest(target) != record['sha256'] or target.stat().st_size != record['bytes']:
            raise ValueError(f'SHA256 or size mismatch: {name}')
        with Image.open(target) as icon:
            if icon.mode != 'RGBA' or icon.size != (SIZE, SIZE):
                raise ValueError(f'Invalid icon geometry: {name}')
        budget.checkpoint()
    for name, digest in manifest['source_sha256'].items():
        if _digest(ROOT / name) != digest:
            raise ValueError(f'SHA256 mismatch: {name}')
        budget.checkpoint()
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'eador/assets')
    parser.add_argument('--cpu-percent', type=float, default=25)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    budget = CpuBudget(args.cpu_percent)
    if args.check:
        count = verify_assets(args.out, budget=budget)
        print(f'Verified {count} icon PNGs and their source manifest.', flush=True)
    else:
        manifest = build_assets(args.out, budget=budget)
        print(f'Built and verified {len(manifest["files"])} icons in {args.out}.', flush=True)


if __name__ == '__main__':
    main()
