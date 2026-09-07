"""Packaging inputs remain explicit and verifiable before invoking PyInstaller."""

import hashlib
from tools.build_eador import collect_package_data


def test_package_data_collection_hashes_every_shipped_file_deterministically(tmp_path):
    """Game audio/provenance and framework data survive collection; source/cache files do not."""
    payloads = {
        'eador/assets/sounds/confirm.wav': b'cue bytes',
        'eador/assets/music/campaign.wav': b'loop bytes',
        'eador/assets/audio-manifest.json': b'{}',
        'eador/assets/AUDIO-PROVENANCE.md': b'original composition',
        'eador/assets/images/terrain/ground-forest-0.png': b'painted tile bytes',
        'eador/assets/images/shard-atmosphere.png': b'background painting',
        'saga2d/fonts/sample.ttf': b'font bytes',
    }
    for relative, content in reversed(list(payloads.items())):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    for relative in ('eador/sound.py', 'eador/__pycache__/sound.pyc', 'docs/sampler.wav'):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'not package data')
    collected = collect_package_data(tmp_path)
    assert list(collected) == sorted(payloads)
    assert collected == {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                         for name, data in sorted(payloads.items())}
    assert collect_package_data(tmp_path) == collected


def test_snapshot_freezes_spec_assets_and_regeneration_sources_before_build(tmp_path):
    """A build consumes one self-contained snapshot, with exact data hashes independent of cwd."""
    import json
    from tools.build_eador import ROOT, snapshot_sources, validate_audio

    source = tmp_path / 'source'
    data = snapshot_sources(source)
    assert (source / 'shardbound.spec').read_bytes() == (ROOT / 'packaging/shardbound.spec').read_bytes()
    assert (source / 'entry.py').read_bytes() == (ROOT / 'packaging/entry.py').read_bytes()
    assert (source / 'tools/build_eador_audio.py').read_bytes() == (ROOT / 'tools/build_eador_audio.py').read_bytes()
    assert json.loads((source / 'package-data.json').read_text()) == data
    audio = json.loads((source / 'eador/assets/audio-manifest.json').read_text())
    from eador.sound import CUES, TRACKS
    assert set(audio['files']) == ({f'sounds/{cue}.wav' for cue in CUES} |
                                   {f'music/{track}.wav' for track in TRACKS})
    for name, expected in audio['files'].items():
        assert data[f'eador/assets/{name}'] == {key: expected[key] for key in ('bytes', 'sha256')}
    assert 'eador/assets/AUDIO-PROVENANCE.md' in data
    art = json.loads((source / 'eador/assets/terrain-art-manifest.json').read_text())
    for name, expected in art['files'].items():
        assert data[f'eador/assets/{name}'] == {key: expected[key] for key in ('bytes', 'sha256')}
    assert 'eador/assets/images/shard-atmosphere.png' in data
    assert 'eador/assets/VISUAL-PROVENANCE.md' in data
    portraits = json.loads((source / 'eador/assets/hero-portrait-provenance.json').read_text())
    from eador.model import HERO_CLASSES
    assert set(portraits['portraits']) == {name.lower() for name in HERO_CLASSES}
    for portrait in portraits['portraits'].values():
        assert data[f'eador/assets/{portrait["path"]}'] == {
            key: portrait[key] for key in ('bytes', 'sha256')}
    assert not any('sampler' in name for name in data)
    assert validate_audio(source) is None
    assert snapshot_sources(tmp_path / 'second') == data


def test_audio_validation_refuses_corrupt_missing_unrecorded_and_stale_inputs(tmp_path):
    """A successful build must never attach provenance for a different set of bytes."""
    import pytest
    from tools.build_eador import snapshot_sources, validate_audio

    source = tmp_path / 'source'
    snapshot_sources(source)
    cue = source / 'eador/assets/sounds/confirm.wav'
    original = cue.read_bytes()
    cue.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    with pytest.raises(RuntimeError, match='Audio asset differs.*confirm'):
        validate_audio(source)
    cue.unlink()
    with pytest.raises(RuntimeError, match='missing=.*confirm'):
        validate_audio(source)
    cue.write_bytes(original)
    extra = cue.with_name('unrecorded.wav')
    extra.write_bytes(original)
    with pytest.raises(RuntimeError, match='unrecorded=.*unrecorded'):
        validate_audio(source)
    extra.unlink()
    generator = source / 'tools/build_eador_audio.py'
    generator.write_bytes(generator.read_bytes() + b'\n# changed composition build\n')
    with pytest.raises(RuntimeError, match='Audio generator differs.*build_eador_audio'):
        validate_audio(source)
