"""Balance audit entry points honor CPU limits without changing paid outcomes."""
import json
import gzip
import pytest


@pytest.mark.parametrize('audit', ['economy', 'difficulty', 'crystal_demand'])
def test_audit_cli_yields_and_preserves_the_paid_campaign(tmp_path, monkeypatch, audit):
    """A selected real campaign gets the default allowance, including its repeat check."""
    from importlib import import_module
    main = import_module('tools.audit_eador_' + audit).main

    samples = {'cpu': 0.0, 'wall': 0.0, 'sleeps': []}

    def process_time():
        samples['cpu'] += .06
        samples['wall'] += .06
        return samples['cpu']

    def sleep(seconds):
        samples['sleeps'].append(seconds)
        samples['wall'] += seconds

    monkeypatch.setattr('tools.cpu_budget.time.process_time', process_time)
    monkeypatch.setattr('tools.cpu_budget.time.monotonic', lambda: samples['wall'])
    monkeypatch.setattr('tools.cpu_budget.time.sleep', sleep)
    report = tmp_path / (audit + '.json')
    args = ['--seeds', '1', '--heroes', 'Commander', '--themes', 'ruins',
            '--plans', 'economy']
    if audit == 'economy':
        args += ['--output', str(report)]
    else:
        args += ['--routes', 'direct', '--modes', 'standard', '--report', str(report)]

    def rows():
        data = json.loads(report.read_text())
        if audit == 'economy':
            return data['runs']
        return json.loads(gzip.decompress((report.parent / data['rows_file']).read_bytes()))

    main(args)
    paced = json.loads(report.read_text())
    expected = rows()
    assert paced['cpu_percent'] == 25
    assert samples['sleeps'], 'The standalone audit bypassed the CPU allowance'
    samples['sleeps'].clear()
    main([*args, '--cpu-percent', '100'])
    assert not samples['sleeps']
    assert rows() == expected
