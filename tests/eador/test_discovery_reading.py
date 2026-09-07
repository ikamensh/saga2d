"""The native discovery reader also exercises ordinary mock input and exact saves."""


def test_saved_sources_are_readable_before_conquest_and_after_reload(tmp_path):
    """Fresh moved sites and untouched historical sources remain locatable without spending."""
    from tools.verify_eador_discoveries import verify

    receipt = verify(tmp_path, backend='mock')
    fresh = [case for case in receipt['cases'] if case['origin'] == 'fresh_title']
    assert [(case['theme'], case['seed']) for case in fresh] == [('frontier', 5), ('frontier', 12), ('ruins', 7)]
    assert all(case['source']['position'] != case['source']['baseline_position'] for case in fresh)
    assert all(case['source']['owner'] == 'neutral' and case['readings'] == [100, 125] for case in fresh)
    historical = [case for case in receipt['cases'] if case['origin'] == 'fixed_save']
    assert len(historical) == 2 and any(case['source']['cleared'] for case in historical)
    assert all(case['initial'] == case['final'] for case in receipt['cases'])
    assert len(receipt['captures']) == 8 and receipt['exact_reloads'] == 5
    assert len(receipt['readings']) == 8
    assert all(reading['site_location'] and reading['relic_location'] for reading in receipt['readings'])
    assert receipt['source_unchanged'] and receipt['preparation_commands'] == 0
