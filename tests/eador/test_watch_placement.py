"""The hold encounter has a deliberate reachable location, leaving the opening Shrine intact."""
from eador.model import State


def test_border_watch_is_reachable_on_the_northern_frontier_without_replacing_the_home_shrine():
    state = State.new(7)
    assert state.provinces[(-2, 0)].site_kind == 'shrine'
    watch = state.provinces[(0, -2)]
    assert watch.site_kind == 'border_watch'
    assert watch.owner == 'neutral'
    assert state.grid.path(state.hero.pos, watch.pos)
    assert len(watch.site_guards) == len(watch.site_guard_hp)
