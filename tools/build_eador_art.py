"""Build/check Shardbound's original, precomputed terrain PNGs.

    uv run python tools/build_eador_art.py
    uv run python tools/build_eador_art.py --check

Generation is offline and cooperatively limited to 25% of one CPU core by
default. --terrain/--mode/--variant can narrow an art iteration's output set.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, __version__ as pillow_version
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
from tools.eador_sources import source_path
sys.path.insert(0,str(ROOT))

from eador.landscape import GENERATOR_VERSION, MODES, SIZE, TERRAINS, VARIANTS, render_tile  # noqa: E402
from saga2d.testing.cpu_budget import CpuBudget  # noqa: E402


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_assets(directory: Path, *, terrains=TERRAINS, modes=MODES,
                 variants=VARIANTS, budget: CpuBudget | None = None) -> dict:
    """Write the requested shipping tiles and an exact-file/source manifest."""
    budget = CpuBudget() if budget is None else budget
    files = {}
    for mode in modes:
        for terrain in terrains:
            for variant in variants:
                relative = f'images/terrain/{mode}-{terrain}-{variant}.png'
                target = directory / relative
                target.parent.mkdir(parents=True,exist_ok=True)
                tile = render_tile(terrain,variant,mode=mode)
                tile.save(target,format='PNG',optimize=True)
                files[relative] = {'sha256':_digest(target),'bytes':target.stat().st_size,
                                   'terrain':terrain,'mode':mode,'variant':variant}
                budget.checkpoint()
    manifest = {
        'product':'Shardbound','generator_version':GENERATOR_VERSION,
        'canvas':list(SIZE),'center':[160,160],'radius':150,'relief':20,
        'variants':list(variants),'terrains':list(terrains),'modes':list(modes),
        'provenance':'Original project-owned procedural illustration: seeded pigment, hand-authored terrain forms and lighting. No external art, photographs, or Eador assets.',
        'license':'Repository MIT license; see LICENSE.',
        'runtime':'Prebuilt PNGs only. The game does not execute the composition module.',
        'generator_dependencies':{'pillow':pillow_version,'numpy':np.__version__},
        'source_sha256':{name:_digest(source_path(name)) for name in
                         ('eador/landscape.py','tools/build_eador_art.py')},
        'files':files,
    }
    (directory/'terrain-art-manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    verify_assets(directory,budget=budget)
    return manifest


def verify_assets(directory: Path, *, budget: CpuBudget | None = None) -> int:
    """Verify all declared PNGs, their alignment, and the composing source bytes."""
    budget = CpuBudget() if budget is None else budget
    manifest = json.loads((directory/'terrain-art-manifest.json').read_text())
    expected = {f'images/terrain/{mode}-{terrain}-{variant}.png'
                for mode in manifest['modes'] for terrain in manifest['terrains']
                for variant in manifest['variants']}
    if set(manifest['files']) != expected:
        raise ValueError('Terrain manifest does not contain every declared tile')
    for name,entry in manifest['files'].items():
        path = directory/name
        if _digest(path) != entry['sha256']:
            raise ValueError(f'SHA256 mismatch: {name}')
        with Image.open(path) as tile:
            if tile.mode != 'RGBA' or tile.size != SIZE:
                raise ValueError(f'Invalid terrain image geometry: {name}')
        budget.checkpoint()
    for name,digest in manifest['source_sha256'].items():
        if _digest(source_path(name)) != digest:
            raise ValueError(f'SHA256 mismatch: {name}')
        budget.checkpoint()
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'eador'/'assets')
    parser.add_argument('--terrain',nargs='+',choices=TERRAINS,default=TERRAINS)
    parser.add_argument('--mode',nargs='+',choices=MODES,default=MODES)
    parser.add_argument('--variant',nargs='+',type=int,choices=VARIANTS,default=VARIANTS)
    parser.add_argument('--cpu-percent',type=float,default=25)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    budget = CpuBudget(args.cpu_percent)
    if args.check:
        count = verify_assets(args.out,budget=budget)
        print(f'Verified {count} terrain PNGs and their source manifest.',flush=True)
    else:
        manifest = build_assets(args.out,terrains=args.terrain,modes=args.mode,
                                variants=args.variant,budget=budget)
        print(f'Built and verified {len(manifest["files"])} terrain PNGs in {args.out}.',flush=True)


if __name__ == '__main__':
    main()
