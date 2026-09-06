"""Themed shards change strategic routes while preserving a fair, portable opening."""
import pytest

from eador.model import HERO_CLASSES, State
from eador.worldgen import NORTH_ROAD, SOUTH_ROAD, THEMES


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
    assert checkpoint.site_kind == 'barrow'
    flanks = [[state.provinces[pos] for pos in road[1:-1]] for road in (NORTH_ROAD, SOUTH_ROAD)]
    weaker = min(flanks, key=lambda provinces: sum(sum(p.guard_hp) for p in provinces))
    assert sum(sum(p.guard_hp) for p in weaker) < sum(sum(p.guard_hp) for p in max(flanks, key=lambda ps: sum(sum(p.guard_hp) for p in ps)))
    assert checkpoint.income > max(p.income for p in weaker)
    assert any(p.site_kind == 'caravan' for p in weaker)
    assert any(p.site_kind == 'tower' for p in weaker)
    assert any('pikeman' in p.guards for p in state.provinces.values() if p.owner == 'rival')


def test_theme_identity_and_active_hold_survive_save_migration_without_world_generation():
    """A legacy world keeps all its recorded terrain, rewards and ongoing hold orders."""
    import json
    from pathlib import Path
    legacy = (Path(__file__).parent / 'fixtures/v5_watch_battle.json').read_text()
    before = json.loads(legacy)
    state = State.from_json(legacy)
    assert state.theme == 'frontier'
    current = json.loads(state.to_json())
    assert current['schema_version'] == 10
    assert current['provinces'] == before['provinces']
    for unit in before['battle']['units']:
        unit.update(abilities=[], pinned=False, pin_cooldown=0, cargo_penalty=0)
    before['battle']['objective']['exits'] = []
    assert current['battle'] == before['battle']
    while not state.battle.outcome:
        state.battle.auto_turn()
    state.resolve_battle()
    assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_new_themes_keep_their_identity_through_active_battles_and_reject_unknown_ids():
    """Theme selection is durable campaign data and invalid IDs fail at the public boundary."""
    import json
    import pytest
    from eador.model import RuleError, SaveFormatError
    from eador.worldgen import THEMES
    for theme in THEMES:
        state = State.new(7, theme=theme)
        state.explore()
        saved = state.to_json()
        restored = State.from_json(saved)
        assert restored.theme == theme
        assert restored.to_json() == saved
        bad = json.loads(saved)
        bad['theme'] = 'unreleased'
        with pytest.raises(SaveFormatError, match='theme'):
            State.from_json(json.dumps(bad))
    for bad in ('unreleased', None, ['frontier']):
        with pytest.raises(RuleError, match='Choose'):
            State.new(theme=bad)


def test_every_theme_places_one_optional_watch_away_from_the_home_shrine():
    """The timed encounter is an authored flank adventure, never a surprise opening fight."""
    from eador.worldgen import THEMES
    for theme in THEMES:
        state = State.new(7, theme=theme)
        watches = [p for p in state.provinces.values() if p.site_kind == 'border_watch']
        assert len(watches) == 1
        watch = watches[0]
        assert watch.owner == 'neutral' and watch.pos[0] == 0 and abs(watch.pos[1]) == 2
        assert state.grid.path(state.hero.pos, watch.pos)
        assert state.provinces[state.hero.pos].site_kind == 'shrine'


def test_a_hundred_seeds_per_theme_keep_connected_capitals_variety_and_valid_content():
    """Random placement cannot erase routes, break saved rosters or strand the opening."""
    from eador.content import SITES
    from eador.model import UNITS
    from eador.worldgen import THEMES
    for theme in THEMES:
        worlds, flank_sides = set(), set()
        for seed in range(100):
            state = State.new(seed, theme=theme)
            assert len(state.provinces) == 19
            assert set(state.grid.reachable(state.hero.pos, 19)) == state.grid.cells
            assert state.grid.path(state.hero.pos, (2, 0))
            assert state.provinces[(2, 0)].owner == 'rival'
            for province in state.provinces.values():
                assert len(province.guards) <= 7 and len(province.site_guards) <= 7
                assert province.guard_hp == [UNITS[kind].hp for kind in province.guards]
                assert province.site_guard_hp == [UNITS[kind].hp for kind in province.site_guards]
                assert province.site_kind is None or province.site_kind in SITES
            saved = state.to_json()
            assert State.from_json(saved).to_json() == saved
            worlds.add(tuple((p.terrain, p.income, tuple(p.guards), p.site_kind)
                             for p in state.provinces.values()))
            if theme != 'frontier':
                flank_sides.add(next(p.pos[1] for p in state.provinces.values()
                                     if p.name in ('Old Causeway', 'Salvager’s Track')))
        assert len(worlds) > 90
        if theme != 'frontier':
            assert flank_sides == {-1, 1}


def test_all_heroes_can_win_opening_adventures_and_each_adjacent_conquest_in_every_theme():
    """A sensible first purchase leaves every opening direction viable, across 100 seeds."""
    from eador.model import HERO_CLASSES
    from eador.worldgen import THEMES
    from tools.eador_campaign import finish_battle
    for theme in THEMES:
        for seed in range(100):
            for hero_class in HERO_CLASSES:
                for target in (None, (-2, 1), (-1, -1), (-1, 0)):
                    state = State.new(seed, hero_class, theme=theme)
                    state.build('barracks')
                    state.recruit('swordsman')
                    state.explore() if target is None else state.travel(target)
                    finish_battle(state)
                    if target is None:
                        assert state.provinces[(-2, 0)].explored
                    else:
                        assert state.hero.pos == target
                    assert state.status == 'playing'


@pytest.mark.parametrize('theme', THEMES)
@pytest.mark.parametrize('hero_class', HERO_CLASSES)
@pytest.mark.parametrize('route', [None, NORTH_ROAD, SOUTH_ROAD], ids=['direct', 'north', 'south'])
def test_each_theme_and_hero_can_finish_by_exploring_either_flank_or_the_direct_road(theme, hero_class, route):
    """The route audit uses the same public campaign commands as this executable journey."""
    from tools.eador_campaign import CampaignMetrics, play_campaign
    metrics = CampaignMetrics()
    state = play_campaign(State.new(7, hero_class, theme=theme), route, metrics)
    assert state.status == 'victory' and state.theme == theme
    assert state.hero.level > 1 and state.inventory
    assert metrics.end_turns == state.turn - 1
    assert metrics.battles > 0 and metrics.recruitment_gold > 0
    assert metrics.battle_hp_attrition > 0 and metrics.hp_recovered > 0
