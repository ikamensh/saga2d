"""Current paid audit output must replay exactly through the game's input adapter."""

import gzip
import hashlib
import json
import sys

import pytest


@pytest.fixture
def current_report(tmp_path, monkeypatch):
    from tools.audit_eador_army_decisions import main
    input_report = tmp_path / 'control.json.gz'
    monkeypatch.setattr(sys, 'argv', ['audit_eador_army_decisions.py', '--plan', 'control',
                                    '--output', str(input_report)])
    main()
    return input_report


def test_verifier_replays_one_current_report_through_paid_aftermath(tmp_path, current_report):
    """The CLI's current model report supplies both branches without requiring historical autoplay."""
    from tools.verify_eador_army_decisions import verify

    input_report = current_report
    source = json.loads(gzip.decompress(input_report.read_bytes()))
    report = verify(input_report, tmp_path / 'verified', backend='mock')
    assert report['input_sha256'] == hashlib.sha256(input_report.read_bytes()).hexdigest()
    assert report['input_source_commit'] == source['source_commit']
    assert {row['branch'] for row in report['rows']} == {'manual', 'auto'}
    for row in report['rows']:
        assert row['plan'] == 'control'
        assert row['final'] == source[row['branch']]['replenished']
        assert row['exact_commands'] == len(source[row['branch']]['commands'])
        assert row['reloads'] == row['exact_commands']


def test_verifier_rejects_stale_or_incomplete_reports_before_replay(tmp_path, current_report):
    """Old pricing, framework changes and broken input journals must fail before a game is created."""
    from tools.verify_eador_army_decisions import verify

    original = gzip.decompress(current_report.read_bytes())
    invalid = tmp_path / 'invalid.json.gz'
    output = tmp_path / 'must-not-replay'
    for path in ('eador/model.py', 'saga2d/game.py', 'eador/../../outside.py'):
        source = json.loads(original)
        source['source_sha256'][path] = 'outdated'
        invalid.write_bytes(gzip.compress(json.dumps(source).encode()))
        with pytest.raises(ValueError, match='Input report.*regenerate the audit'):
            verify(invalid, output, backend='mock')
    for omitted in ('plan', 'source', 'auto'):
        source = json.loads(original)
        del source[omitted]
        invalid.write_bytes(gzip.compress(json.dumps(source).encode()))
        with pytest.raises(ValueError, match='Input report must contain'):
            verify(invalid, output, backend='mock')
    source = json.loads(original)
    source['manual']['commands'][1]['before'] = source['manual']['commands'][0]['before']
    invalid.write_bytes(gzip.compress(json.dumps(source).encode()))
    with pytest.raises(ValueError, match='do not form an exact saved chain'):
        verify(invalid, output, backend='mock')
    assert not output.exists()
