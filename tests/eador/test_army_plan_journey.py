"""A paid army remains a build through earned shard transitions and saved continuation."""
from collections import Counter

from eador.model import State
from tools.audit_eador_army_plans import journey


def test_commander_completes_linked_campaign_with_paid_sustain_roster():
    """Exercise the real campaign, purchases and saves rather than injecting a finished party."""
    report = journey('sustain')
    final = State.from_json(report['final_state'])
    assert final.campaign.phase == 'completed'
    assert [record.stage for record in final.campaign.completed] == [1, 2, 3]
    target = Counter(('swordsman', 'swordsman', 'pikeman', 'healer', 'archer', 'militia'))
    assert any(Counter(unit['kind'] for unit in battle['roster']) == target
               for stage in report['stages'] for battle in stage['battles'])
    purchases = [entry for entry in report['commands'] if entry['command'] in ('recruit', 'replace_troop')]
    assert purchases and all(entry['gold_spent'] > 0 for entry in purchases)
    assert any(entry['command'] == 'replace_troop' for entry in purchases)
    previous = report['initial_state']
    for entry in report['commands']:
        assert entry['before'] == previous
        restored = State.from_json(entry['after'])
        assert restored.to_json() == entry['after']
        previous = entry['after']
    assert previous == report['final_state']
