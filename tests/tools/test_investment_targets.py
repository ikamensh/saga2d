"""Paid comparisons must reach their actual named encounter after rival interruptions."""
import gzip
import json

from tools.prototype_eador_early_conversion import ROOT, authored_branch


def test_defensive_recovery_returns_to_the_named_expedition_before_entering():
    """A rival detour cannot relabel a different site's battle as the paid target."""
    pilot = ROOT / 'docs/evidence/earned-specialist-investment-e5a13ce/authored-commander-pilot.json.gz'
    report = json.loads(gzip.decompress(pilot.read_bytes()))
    row = next(row for row in report['rows'] if row['case'][2] == 'ruins')
    branch = authored_branch(json.dumps(row['input']), 'sapper', target_kind='sealed_vault')
    assert branch['target_fight'] is not None
    initial = branch['fights'][branch['target_fight']]['initial']
    assert tuple(initial['battle_province']) == tuple(branch['target'])
