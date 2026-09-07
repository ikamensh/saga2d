"""A stopped game resumes every saved phase through a new process's title controls."""


def test_each_saved_phase_loads_from_disk_and_accepts_its_next_public_order(tmp_path):
    """Fresh-process UI loads preserve full state, then continue earned phases exactly."""
    from tools.verify_eador_restarts import verify

    report = verify(tmp_path, backend='mock')
    assert report['writer_pid'] != report['resume_pid']
    assert report['source_unchanged'] and report['fresh_process']
    cases = {case['name']: case for case in report['cases']}
    assert {name: case['loaded_scenes'][-1] for name, case in cases.items()} == {
        'campaign': 'ShardScene', 'battle': 'BattleScene',
        'skill': 'ChoiceScene', 'relic': 'ChoiceScene', 'result': 'ResultScene',
        'departure': 'CampaignScene', 'recovery': 'CampaignScene',
        'completed': 'CampaignScene', 'capital-loss': 'ResultScene',
    }
    assert {case['load_control'] for case in cases.values()} == {'F9', 'F6 / 2'}
    assert all(case['exact_load'] and case['exact_continuation'] and case['manual_bytes_unchanged']
               for case in cases.values())
    assert cases['campaign']['after']['turn'] == cases['campaign']['before']['turn'] + 1
    hero = next(unit for unit in cases['battle']['after']['battle']['units'] if unit['id'] == 0)
    assert hero['acted']
    assert [choice['kind'] for choice in cases['skill']['after']['choices']] == ['relic']
    assert not cases['relic']['after']['choices']
    assert 'veil_censer' in cases['relic']['after']['inventory']
    assert cases['result']['after']['battle'] is None and cases['result']['after']['choices']
    assert cases['departure']['after']['campaign']['stage'] == 2
    assert cases['recovery']['after']['campaign']['recovery_used']
    for name in ('departure', 'recovery'):
        assert cases[name]['after']['campaign']['phase'] == 'playing'
    for name in ('completed', 'capital-loss'):
        assert cases[name]['new_game_started']
        assert cases[name]['after'] == cases[name]['before']
