"""The split-party rescue is playable with purchased formations and visible orders."""
import pytest


def test_paid_commander_reunites_the_split_party_and_claims_its_saved_reward_once(tmp_path):
    """Enter the advertised assembly, use the Ranger and Warden, and evacuate with enemies still alive."""
    from tools.verify_eador_explorer import verify

    report = verify(tmp_path, backend='mock')
    assert report['outcome_reason'] == 'escape'
    assert report['troops_lost'] == 0 and report['building_gold'] > 0 and report['recruitment_gold'] > 0
    assert report['fee_gold'] == report['fee_crystals'] == 0
    assert any(command == 'swap' for command, *_ in report['orders'])


@pytest.mark.parametrize('plan,party_size', [('commander-south', 6), ('warrior-acolyte', 6), ('scout-alone', 5)])
def test_alternative_assemblies_and_parties_can_reunite_without_losing_troops(tmp_path, plan, party_size):
    """The southern assembly, ordinary healer escort and smaller unescorted Scout have actual control paths."""
    from tools.verify_eador_explorer import verify

    report = verify(tmp_path, backend='mock', plan=plan)
    assert report['outcome_reason'] == 'escape' and report['troops_lost'] == 0
    assert len(report['survivors']) == party_size
    assert all(unit['hp'] > 0 for unit in report['survivors'])
