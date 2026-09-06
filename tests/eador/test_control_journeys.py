"""The control roster is purchased and used in real authored objectives."""


def test_a_real_economy_can_buy_all_three_crystal_roles_and_reach_the_watch():
    """The demonstration starts with ordinary resources, purchases every role and preserves the save."""
    from eador.model import State
    from tools.eador_control_campaign import prepare_control_watch
    state = prepare_control_watch()
    assert {troop.kind for troop in state.hero.army} >= {'sapper', 'adept', 'skyrider'}
    assert {'market', 'mage_tower', 'temple'} <= state.buildings
    assert state.battle_encounter == 'border_watch' and not state.provinces[state.hero.pos].explored
    assert state.crystals >= 0 and all(troop.hp == troop.max_hp for troop in state.hero.army)
    assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_paid_smoke_repulse_and_flight_win_hold_with_a_living_archer_and_save_every_order():
    """A planned screen saves health; displacement and flight replace killing the final defender."""
    from eador.model import State
    from tools.eador_control_campaign import prepare_control_watch, watch_control_route
    from tools.eador_extraction_campaign import AdventureOrders

    class SavedOrders(AdventureOrders):
        def do(self, command, *args, **kwargs):
            if command in ('smoke', 'repulse', 'rally'):
                before = self.state.to_json()
                getattr(self.battle, f'{command}_preview')(*args, **kwargs)
                assert self.state.to_json() == before
            super().do(command, *args, **kwargs)
            text = self.state.to_json()
            self.state = State.from_json(text)
            assert self.state.to_json() == text

    baseline = prepare_control_watch().to_json()
    screened = watch_control_route(State.from_json(baseline), orders_type=SavedOrders)
    guarding = watch_control_route(State.from_json(baseline), smoke=False, orders_type=SavedOrders)
    for play in (screened, guarding):
        assert play.battle.outcome_reason == 'hold' and play.battle.round == 3
        assert all(unit.alive for unit in play.battle.units if unit.team == 'player')
        assert any(unit.alive for unit in play.battle.units if unit.team == 'enemy')
    assert sum(u.hp for u in screened.battle.units if u.team == 'player') > sum(
        u.hp for u in guarding.battle.units if u.team == 'player')
    assert {'smoke', 'repulse'} <= {command for command, *_ in screened.orders}
    state = screened.state
    state.resolve_battle()
    assert state.provinces[(0, -2)].explored
    assert State.from_json(state.to_json()).to_json() == state.to_json()
