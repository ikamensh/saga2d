"""The standalone smoke validates installed assets without relying on the working directory."""

from pathlib import Path
import runpy
import shutil

import pytest


ENTRY = Path(__file__).resolve().parents[2] / 'packaging/entry.py'


def test_smoke_decodes_a_relocated_shipping_catalogue_and_rejects_changed_bytes(tmp_path):
    """All shipped WAVs decode from a module-relative asset root and match their provenance."""
    decode = runpy.run_path(str(ENTRY))['decode_audio_catalogue']
    assets = tmp_path / 'installed/eador/assets'
    shutil.copytree(ENTRY.parent.parent / 'eador/assets', assets)
    files = decode(assets)
    assert len(files) == 14
    assert {record['sample_rate'] for record in files.values()} == {44100}
    assert {record['channels'] for name, record in files.items() if name.startswith('sounds/')} == {1}
    assert {record['channels'] for name, record in files.items() if name.startswith('music/')} == {2}
    assert {files[f'music/{name}.wav']['seconds'] for name in ('battle', 'campaign')} == {32, 48}
    cue = assets / 'sounds/confirm.wav'
    cue.write_bytes(cue.read_bytes()[:-2])
    with pytest.raises(RuntimeError, match='Audio asset differs.*confirm'):
        decode(assets)
