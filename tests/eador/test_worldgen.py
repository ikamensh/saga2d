"""Themed shards change strategic routes while preserving a fair, portable opening."""
from eador.model import State


def test_elderwild_offers_a_richer_dry_detour_through_a_wolf_and_goblin_shard():
    """The extra travel buys stronger income and merchant loot instead of just a new palette."""
    state = State.new(7, theme='elderwild')
    assert state.provinces[(-2, 0)].site_kind == 'shrine'
    assert not state.provinces[(-2, 0)].guards
    assert sum(p.terrain in ('forest', 'marsh') for p in state.provinces.values()) > len(state.provinces) // 2
    road = {p.pos for p in state.provinces.values() if not p.capital and p.income >= 10}
    path = state.grid.path((-2, 0), (2, 0), blocked=state.grid.cells - road - {(-2, 0), (2, 0)})
    assert len(path) > len(state.grid.path((-2, 0), (2, 0)))
    assert path
    assert all(state.provinces[pos].terrain == 'plains' for pos in path[1:-1])
    assert any(state.provinces[pos].site_kind == 'caravan' for pos in path[1:-1])
    assert state.provinces[(0, 0)].income < min(state.provinces[pos].income for pos in road)
    assert state.provinces[(0, 0)].guards.count('wolf') > 1
    restored = State.from_json(state.to_json())
    assert restored.provinces == state.provinces


def test_an_elderwild_campaign_can_win_by_developing_and_defending_a_realm():
    """New guarding parties remain beatable through the ordinary campaign commands."""
    from tools.eador_campaign import play_campaign
    state = play_campaign(State.new(7, theme='elderwild'))
    assert state.status == 'victory'
    assert state.hero.level > 1
    assert any(province.explored for province in state.provinces.values())


def test_ruins_trade_a_valuable_pike_checkpoint_for_a_weaker_flank():
    """Both paths are playable, but the short road asks for Brace counters and pays more income."""
    from eador.worldgen import NORTH_ROAD, SOUTH_ROAD
    state = State.new(7, theme='ruins')
    checkpoint = state.provinces[(0, 0)]
    assert {'pikeman', 'archer'} <= set(checkpoint.guards)
    assert checkpoint.site_kind == 'tower'
    flanks = [[state.provinces[pos] for pos in road[1:-1]] for road in (NORTH_ROAD, SOUTH_ROAD)]
    weaker = min(flanks, key=lambda provinces: sum(sum(p.guard_hp) for p in provinces))
    assert sum(sum(p.guard_hp) for p in weaker) < sum(sum(p.guard_hp) for p in max(flanks, key=lambda ps: sum(sum(p.guard_hp) for p in ps)))
    assert checkpoint.income > max(p.income for p in weaker)
    assert any(p.site_kind == 'caravan' for p in weaker)
    assert any('pikeman' in p.guards for p in state.provinces.values() if p.owner == 'rival')
