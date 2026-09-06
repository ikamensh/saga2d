"""Paid linked journeys preserve earned builds through loss, recovery and departure."""
import pytest

from eador.content import SKILLS
from eador.model import State
from tools.audit_eador_disciplines import journey


@pytest.mark.parametrize('skill', SKILLS)
def test_each_preferred_discipline_earns_mastery_and_survives_a_complete_recovered_campaign(skill):
    """Both paths of every hero work through actual commands, without inserting ranks or XP."""
    result = journey(skill, recovery=True)
    assert result['phase'] == 'completed'
    assert [record['stage'] for record in result['records']] == [1, 2, 3]
    choices = [decision for decision in result['decisions'] if decision['kind'] == 'skill']
    assert len(choices) == 4
    for decision in choices:
        before = State.from_json(decision['before'])
        after = State.from_json(decision['after'])
        selected = decision['selected']
        if skill in decision['offered']:
            assert selected == skill
        else:
            assert selected != skill
        assert after.hero.skill_ranks.get(selected, 0) == before.hero.skill_ranks.get(selected, 0) + 1
        assert after.hero.level == before.hero.level
    checkpoints = {entry['phase']: State.from_json(entry['state']) for entry in result['checkpoints']}
    assert checkpoints['stage-1-departure'].hero.skill_ranks == {skill: 2}
    for phase in ('stage-2-arrived', 'capital-lost', 'recovered'):
        assert checkpoints[phase].hero.skill_ranks == {skill: 2}
    assert checkpoints['recovered'].campaign.recovery_used
    assert checkpoints['stage-2-departure'].hero.skill_ranks == {skill: 3}
    assert checkpoints['stage-3-arrived'].hero.skill_ranks == {skill: 3}
    assert State.from_json(result['final_state']).hero.skill_ranks[skill] == 3
