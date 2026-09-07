"""Shipping icons are deterministic transparent assets with checked provenance."""
import hashlib
import json

from PIL import Image
import pytest

from tools.build_eador import collect_package_data
from tools.build_eador_icons import build_assets, verify_assets


def test_icon_catalogue_builds_reproducibly_and_survives_package_collection(tmp_path):
    """Every declared icon ships with its exact bytes and rejects later corruption."""
    assets = tmp_path / 'eador/assets'
    manifest = build_assets(assets)
    assert verify_assets(assets) == len(manifest['files'])
    originals = {name: (assets / name).read_bytes() for name in manifest['files']}
    required = ('guide hero codex text_size save load settings gold crystals health mana '
                'attack defense move fly range actions income upkeep level xp build recruit '
                'explore travel end_turn bolt heal guard retreat auto_play log campaign rival').split()
    assert {f'images/icons/{name}.png' for name in required} <= originals.keys()
    for name, data in originals.items():
        with Image.open(assets / name) as icon:
            assert icon.mode == 'RGBA' and icon.size == (96, 96)
            assert icon.getchannel('A').getextrema() == (0, 255)
            assert all(icon.getpixel(point)[3] == 0 for point in
                       ((0, 0), (95, 0), (0, 95), (95, 95)))
        assert hashlib.sha256(data).hexdigest() == manifest['files'][name]['sha256']
    packaged = collect_package_data(tmp_path)
    for name, record in manifest['files'].items():
        assert packaged[f'eador/assets/{name}'] == {
            field: record[field] for field in ('bytes', 'sha256')}
    assert build_assets(assets) == manifest
    assert originals == {name: (assets / name).read_bytes() for name in originals}
    assert json.loads((assets / 'icon-art-manifest.json').read_text()) == manifest
    damaged = assets / next(iter(originals))
    damaged.write_bytes(b'damaged icon')
    with pytest.raises(ValueError, match='SHA256'):
        verify_assets(assets)
