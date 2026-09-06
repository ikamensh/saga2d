"""A paid observatory approach is a saved, finite hold adventure."""
from eador.model import State


def test_purchased_observatory_army_holds_the_cleared_lane_and_survives_every_saved_order():
    """A real earned army secures the hill before the deadline while enemies remain alive."""
    from tools.eador_observatory_campaign import prepare_observatory, observatory_route
    from tests.eador.test_extraction_journeys import Journey

    state = prepare_observatory()
    crystals = state.crystals
    assert {'barracks', 'market', 'temple'} <= state.buildings
    assert [troop.kind for troop in state.hero.army][-3:] == ['warden', 'sapper', 'healer']
    play = observatory_route(state, 'clear', orders_type=Journey)
    assert state.crystals == crystals - 2
    assert play.battle.outcome_reason == 'hold' and play.battle.outcome == 'player'
    assert play.battle.objective.progress == 2 and play.battle.round <= 8
    assert all(u.alive for u in play.battle.units if u.team == 'player')
    assert any(u.alive for u in play.battle.units if u.team == 'enemy')
    assert State.from_json(play.state.to_json()).to_json() == play.state.to_json()


def test_actual_prior_barrow_save_keeps_its_site_and_complete_continuation():
    """Authored placement affects new worlds only; an old active Barrow stays exact."""
    import json
    from pathlib import Path
    from tools.eador_campaign import finish_battle

    fixtures = Path(__file__).parent / 'fixtures'
    state = State.from_json((fixtures / 'v11_ruins_barrow_battle.json').read_text())
    assert state.provinces[(-1, 0)].site_kind == 'barrow'
    assert not any(p.site_kind == 'broken_observatory' for p in state.provinces.values())
    finish_battle(state)
    assert json.loads(state.to_json()) == json.loads((fixtures / 'v11_ruins_barrow_battle_result.json').read_text())
