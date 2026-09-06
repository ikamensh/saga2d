"""An optional Causeway preserves older sources and earned tactical consequences."""
from pathlib import Path

from eador.model import State
from tools.eador_campaign import finish_battle


def test_actual_pre_causeway_shrine_keeps_its_complete_saved_continuation():
    """New worlds may change this site; a real loaded Shrine battle and all rewards remain exact."""
    fixtures = Path(__file__).parent / 'fixtures'
    before = (fixtures / 'v12_pre_causeway_shrine_battle.json').read_text()
    state = State.from_json(before)
    assert state.to_json() == before
    assert state.provinces[(0, 1)].site_kind == 'shrine'
    finish_battle(state)
    assert state.to_json() == (fixtures / 'v12_pre_causeway_shrine_result.json').read_text()
