"""Reading verifiers yield during real preparation before beginning their UI matrices."""

import pytest

from saga2d.testing.cpu_budget import CpuBudget


class YieldObserved(Exception):
    """Stop at the clock boundary instead of running a full campaign matrix."""


@pytest.fixture
def clock(monkeypatch):
    """Fake only CPU/wall time; the real preparation stops at its first cooperative yield."""
    samples = {'cpu': 0.0, 'wall': 0.0, 'sleeps': [], 'stop': True}

    def process_time():
        samples['cpu'] += .06
        samples['wall'] += .06
        return samples['cpu']

    def sleep(seconds):
        samples['sleeps'].append(seconds)
        samples['wall'] += seconds
        if samples['stop']:
            raise YieldObserved

    monkeypatch.setattr('saga2d.testing.cpu_budget.time.process_time', process_time)
    monkeypatch.setattr('saga2d.testing.cpu_budget.time.monotonic', lambda: samples['wall'])
    monkeypatch.setattr('saga2d.testing.cpu_budget.time.sleep', sleep)
    return samples


def test_campaign_preparation_respects_the_supplied_allowance(clock):
    """Paid campaign preparation must use the caller's 50% allowance instead of running unpaced."""
    from tools.verify_eador_campaign_reading import prepared_transitions

    with pytest.raises(YieldObserved):
        prepared_transitions(budget=CpuBudget(50))
    assert clock['sleeps'] == pytest.approx([.06])


def test_briefing_preparation_respects_the_supplied_allowance(clock):
    """The authored-adventure matrix must yield within its first real paid preparation."""
    from tools.verify_eador_guidance import prepared_briefings

    with pytest.raises(YieldObserved):
        prepared_briefings(budget=CpuBudget(50))
    assert clock['sleeps'] == pytest.approx([.06])


@pytest.mark.parametrize('recovery', [False, True])
def test_checkpoint_preparation_respects_the_supplied_allowance(clock, tmp_path, recovery):
    """Both checkpoint remedies must yield while earning their input state, before creating a window."""
    from tools.verify_eador_checkpoint import verify

    with pytest.raises(YieldObserved):
        verify(tmp_path, backend='mock', recovery=recovery, budget=CpuBudget(50))
    assert clock['sleeps'] == pytest.approx([.06])


@pytest.mark.parametrize('name', ['campaign', 'briefing'])
def test_complete_preparation_defaults_to_yielding_without_changing_saved_results(clock, name):
    """Every real paid/legacy snapshot matches explicit unpaced preparation; only the clock is replaced."""
    from eador.model import State
    from tools.verify_eador_campaign_reading import prepared_transitions
    from tools.verify_eador_guidance import prepared_briefings

    prepare = prepared_transitions if name == 'campaign' else prepared_briefings
    clock['stop'] = False
    prepared_transitions.cache_clear()
    try:
        expected = prepare(budget=CpuBudget(100))
        assert not clock['sleeps']
        actual = prepare()
        assert clock['sleeps'], 'Default preparation must yield without an explicit budget'
        assert actual == expected
        for _, snapshot, *_ in actual:
            state = State.from_json(snapshot)
            assert State.from_json(state.to_json()).to_json() == state.to_json()
    finally:
        prepared_transitions.cache_clear()


def test_campaign_verifier_forwards_its_allowance_and_closes_on_interruption(clock, tmp_path, monkeypatch):
    """The actual mock session closes when paced preparation is interrupted at the clock boundary."""
    from saga2d.backends.mock_backend import MockBackend
    from tools.verify_eador_campaign_reading import verify

    backends = []

    class ObservedBackend(MockBackend):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            backends.append(self)

    monkeypatch.setattr('saga2d.backends.mock_backend.MockBackend', ObservedBackend)
    with pytest.raises(YieldObserved):
        verify(tmp_path, backend='mock', budget=CpuBudget(50))
    assert clock['sleeps'] == pytest.approx([.06])
    assert len(backends) == 1 and not backends[0].is_running


def test_briefing_matrix_forwards_its_allowance_to_paid_preparation(clock, tmp_path):
    """A supplied matrix allowance reaches model work before any authored UI cases run."""
    from eador.app import create_game
    from tools.verify_eador_guidance import verify_briefing_matrix

    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        with pytest.raises(YieldObserved):
            verify_briefing_matrix(game, budget=CpuBudget(50))
        assert clock['sleeps'] == pytest.approx([.06])
    finally:
        game.close()


@pytest.mark.parametrize('name', ['campaign_reading', 'guidance', 'checkpoint'])
def test_reading_verifier_cli_rejects_invalid_allowance_before_starting(name, capsys):
    """Invalid CLI allowances fail before any preparation, file output or native session starts."""
    from importlib import import_module

    main = import_module('tools.verify_eador_' + name).main
    with pytest.raises(SystemExit) as error:
        main(['--cpu-percent', '0'])
    assert error.value.code == 2
    assert 'CPU percent must be greater than 0 and at most 100' in capsys.readouterr().err
