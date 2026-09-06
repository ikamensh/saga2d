"""The standalone smoke validates installed assets without relying on the working directory."""

from pathlib import Path
import gzip
import hashlib
import json
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


def test_packaged_forecast_check_reads_an_external_earned_save_without_spending_an_order(tmp_path, monkeypatch):
    """The package diagnostic loads through Title, reads both forecasts, and preserves exact progress."""
    check = runpy.run_path(str(ENTRY))['verify_forecast_save']
    journal = ENTRY.parent.parent / 'docs/evidence/shardbound-army-plans-cd351a9/control.json.gz'
    initial = json.loads(gzip.decompress(journal.read_bytes()))['commands'][80]['before']
    supplied = tmp_path / 'earned-control.json'
    supplied.write_text(initial + '\n', encoding='utf-8')
    original = supplied.read_bytes()
    outside = tmp_path / 'outside-repository'
    outside.mkdir()
    monkeypatch.chdir(outside)

    report = check(supplied, outside / 'smoke.png', backend='mock')

    assert 'Rune Adept falls.' in ' '.join(report['forecast_100'])
    assert 'Tab selects another unit.' in ' '.join(report['forecast_125'])
    assert 'Rune Adept falls.' not in ' '.join(report['safe_forecast'])
    assert report['reading_percent'] == 125
    assert report['state_sha256'] == hashlib.sha256(initial.encode()).hexdigest()
    assert report['input_sha256'] == hashlib.sha256(original).hexdigest()
    assert report['state_unchanged'] and report['exact_save_reloads'] == 1
    assert report['input_activations'] > 0
    assert supplied.read_bytes() == original
    assert not Path(report['isolated_data_directory']).exists()
