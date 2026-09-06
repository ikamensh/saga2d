"""The packaged campaign check uses separate game lifetimes and shipped save/input paths."""

from pathlib import Path
import runpy


def test_three_shards_resume_the_exact_saved_departure_and_completed_ending(tmp_path):
    """Each invocation reconstructs from Title quickload, with no live state passed between games."""
    check = runpy.run_path(str(Path(__file__).parents[2] / 'packaging/campaign_check.py'))['run']
    output = tmp_path / 'campaign'
    previous = None
    for phase in range(1, 5):
        report = check(output, phase=phase, backend='mock')
        assert report['input_activations'] > 0
        if previous is not None:
            assert report['loaded_checkpoint'] == previous['checkpoint']
        previous = report
    assert report['campaign_phase'] == 'completed'
    assert len(report['completed_shards']) == 3
    assert report['returned_to_title']


def test_a_lost_capital_resumes_its_saved_recovery_before_finishing_the_campaign(tmp_path):
    """The loss checkpoint survives a fresh Game before the player spends the single recovery."""
    check = runpy.run_path(str(Path(__file__).parents[2] / 'packaging/campaign_check.py'))['run']
    output = tmp_path / 'recovery'
    previous = None
    for phase in range(1, 6):
        report = check(output, phase=phase, recovery=True, backend='mock')
        if previous is not None:
            assert report['loaded_checkpoint'] == previous['checkpoint']
        if phase == 2:
            assert report['campaign_phase'] == 'recovery' and not report['recovery_used']
        if phase >= 3:
            assert report['recovery_used']
        previous = report
    assert report['returned_to_title'] and len(report['completed_shards']) == 3
