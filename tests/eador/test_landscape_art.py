"""The shipped art builder produces stable, aligned transparent tile assets."""
import json

from PIL import Image

from tools.build_eador_art import build_assets, verify_assets


def test_terrain_assets_are_reproducible_and_manifest_checked(tmp_path):
    manifest = build_assets(tmp_path, terrains=('forest',), variants=(0,),
                            modes=('province', 'ground'))
    assert set(manifest['files']) == {
        'images/terrain/province-forest-0.png',
        'images/terrain/ground-forest-0.png',
    }
    assert verify_assets(tmp_path) == 2
    before = {name: (tmp_path / name).read_bytes() for name in manifest['files']}
    for name in before:
        with Image.open(tmp_path / name) as tile:
            assert tile.mode == 'RGBA'
            assert tile.size == (320, 352)
            assert tile.getpixel((160, 160))[3] == 255
            assert tile.getpixel((160, 320))[3] > 0  # visible relief
            assert all(tile.getpixel(p)[3] == 0 for p in
                       ((0, 0), (319, 0), (0, 351), (319, 351)))
    build_assets(tmp_path, terrains=('forest',), variants=(0,),
                 modes=('province', 'ground'))
    assert before == {name: (tmp_path / name).read_bytes() for name in before}
    assert before['images/terrain/province-forest-0.png'] != before['images/terrain/ground-forest-0.png']
    saved = json.loads((tmp_path / 'terrain-art-manifest.json').read_text())
    assert saved == manifest
    damaged = tmp_path / next(iter(before))
    damaged.write_bytes(b'not the generated tile')
    import pytest
    with pytest.raises(ValueError, match='SHA256'):
        verify_assets(tmp_path)
