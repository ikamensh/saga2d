from eador.model import State
from tools.eador_screen_campaign import prepare_screen, screen_western_route
from tests.eador.test_extraction_journeys import Journey
from tests.eador.test_pack_hunt import assert_one_rout_reward


def test_paid_western_screen_relocates_under_smoke_and_wins_with_saved_orders():
    state = prepare_screen()
    assert state.actions_left > 0
    assert state.hero.hp == state.hero.max_hp and all(t.hp == t.max_hp for t in state.hero.army)
    assert state.provinces[state.hero.pos].site_kind == 'smuggler_screen'
    assert [troop.kind for troop in state.hero.army] == ['militia', 'militia', 'archer', 'warden', 'ranger']
    before = State.from_json(state.to_json())
    play = screen_western_route(state, orders_type=Journey)
    assert play.battle.outcome_reason == 'rout' and play.battle.round == 4
    assert all(u.alive for u in play.battle.units if u.team == 'player')
    assert sum(u.max_hp - u.hp for u in play.battle.units if u.team == 'player') == 62
    assert play.battle.mana == before.hero.mana
    assert play.state.gold == before.gold and play.state.crystals == before.crystals
    assert_one_rout_reward(play)


def test_saved_old_grove_and_caravan_keep_their_exact_active_battle_continuations():
    from pathlib import Path
    from tools.eador_campaign import finish_battle

    fixtures = Path(__file__).parent / 'fixtures'
    for kind in ('grove', 'caravan'):
        state = State.from_json((fixtures / f'v12_elderwild_{kind}_battle.json').read_text())
        assert state.provinces[(0, -1)].site_kind == kind
        assert all(province.site_kind != 'smuggler_screen' for province in state.provinces.values())
        finish_battle(state)
        expected = State.from_json((fixtures / f'v12_elderwild_{kind}_result.json').read_text())
        assert state.to_json() == expected.to_json()


class ScreenJourney(Journey):
    def __init__(self, state):
        super().__init__(state)
        self.clouds_after_first_phase = []
        self.sapper_before_first_phase = None
        self.rallied_after_shooting = False

    def do(self, command, *args, **kwargs):
        first_phase = command == 'end_turn' and self.battle.round == 1
        if first_phase:
            sapper = next(u for u in self.battle.units if u.kind == 'sapper')
            self.sapper_before_first_phase = sapper.alive, 'smoke' in sapper.spent_abilities
        if command == 'rally':
            ranger = self.battle.unit(args[1])
            assert ranger.pinned and ranger.acted and not ranger.moved
            assert (2, -3) not in self.battle.reachable(ranger.id)
            self.rallied_after_shooting = True
        super().do(command, *args, **kwargs)
        if first_phase:
            self.clouds_after_first_phase = [c.pos for c in self.battle.smoke_clouds]
        if command == 'rally':
            ranger = self.battle.unit(args[1])
            assert not ranger.pinned and ranger.acted and not ranger.moved
            assert (2, -3) in self.battle.reachable(ranger.id)


def test_same_paid_party_uses_distinct_orders_for_the_two_free_assemblies():
    from tools.eador_screen_campaign import screen_northern_route

    prepared = prepare_screen()
    original = prepared.to_json()
    west = screen_western_route(State.from_json(original), orders_type=ScreenJourney)
    north = screen_northern_route(State.from_json(original), orders_type=ScreenJourney)
    assert west.clouds_after_first_phase == [(-2, 1)]
    assert north.clouds_after_first_phase == [(0, -2)]
    assert not west.rallied_after_shooting and north.rallied_after_shooting
    assert (west.battle.round, north.battle.round) == (4, 5)
    assert west.battle.mana == prepared.hero.mana
    assert north.battle.mana == prepared.hero.mana - 2 * north.battle.spell_cost('heal')
    assert west.state.gold == north.state.gold and west.state.crystals == north.state.crystals
    assert [(u.kind, u.hp) for u in west.battle.units if u.team == 'enemy'] == [(u.kind, u.hp) for u in north.battle.units if u.team == 'enemy']
    assert_one_rout_reward(west); assert_one_rout_reward(north)


def test_scout_party_can_deny_smoke_before_its_charge_without_a_special_relic():
    from tools.eador_screen_campaign import screen_scout_route

    state = prepare_screen('Scout')
    starting_mana = state.hero.mana
    assert len(state.hero.army) == 5 and state.hero.relic == 'moonstone'
    assert [t.kind for t in state.hero.army] == ['militia', 'militia', 'archer', 'warden', 'ranger']
    play = screen_scout_route(state, orders_type=ScreenJourney)
    assert play.battle.round == 5 and play.battle.mana == starting_mana - 2 * play.battle.spell_cost('heal')
    assert play.sapper_before_first_phase == (False, False)
    assert all(u.alive for u in play.battle.units if u.team == 'player')
    assert not play.clouds_after_first_phase
    assert not any('screens' in message for message in play.battle.log)
    assert_one_rout_reward(play)


def _scout_disables_sapper():
    """Stop the actual Scout route before its first enemy phase."""
    from tools.eador_screen_campaign import screen_scout_opening

    state = prepare_screen('Scout'); state.explore(approach='northern')
    play = Journey(state)
    screen_scout_opening(play)
    return play


def test_retreat_keeps_dead_sapper_and_wounded_guards_when_changing_assembly():
    from tools.eador_campaign import march_to, rest
    from saga2d.testing.cpu_budget import CpuBudget

    play = _scout_disables_sapper()
    destination = play.state.hero.pos
    play.guard_remaining(); play.do('end_turn')
    state = play.state
    gold, xp, crystals = state.gold, state.hero.xp, state.crystals
    surviving = [(u.kind, u.hp) for u in play.battle.units if u.team == 'enemy' and u.alive]
    assert surviving == [('archer', 20), ('archer', 4), ('warden', 34), ('guard', 38)]
    state.retreat()
    assert state.gold == gold - 20 and state.crystals == crystals and state.hero.xp == xp
    assert not state.provinces[state.hero.pos].explored and state.choice is None
    state = State.from_json(state.to_json())
    budget = CpuBudget(25)
    for _ in range(8):
        rest(state, budget=budget)
        march_to(state, destination, budget=budget)
        if state.hero.pos == destination and state.actions_left:
            break
    assert state.hero.pos == destination and state.actions_left
    state.explore(approach='western')
    assert [(u.kind, u.hp) for u in state.battle.units if u.team == 'enemy'] == surviving
    assert not any(u.can_smoke for u in state.battle.units if u.team == 'enemy')
    assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_real_defeat_keeps_casualties_and_cannot_reward_the_sapper_kill_until_a_paid_retry_wins():
    from tools.eador_campaign import rest, march_to
    from saga2d.testing.cpu_budget import CpuBudget

    play = _scout_disables_sapper()
    pos = play.state.hero.pos
    budget = CpuBudget(25)
    for _ in range(80):
        if play.battle.outcome:
            break
        play.guard_remaining(); play.do('end_turn')
        budget.checkpoint()
    assert play.battle.outcome_reason == 'hero_death' and play.battle.round == 53
    state = play.state
    xp, gold = state.hero.xp, state.gold
    dead_ids = {u.id for u in play.battle.units if u.team == 'player' and not u.alive and u.id != 0}
    assert dead_ids == {1, 2, 3, 4, 5}
    state.resolve_battle()
    assert state.gold == gold - 20 and state.hero.xp == xp
    assert state.choice is None and not state.provinces[pos].explored
    assert state.provinces[pos].site_guards == ['archer']
    assert state.provinces[pos].site_guard_hp == [20]
    state = State.from_json(state.to_json())
    spent = 0
    for _ in range(32):
        if len(state.hero.army) < state.hero.max_army and state.gold >= state.recruit_cost('swordsman'):
            before = state.gold; state.recruit('swordsman'); spent += before - state.gold
        march_to(state, pos, budget=budget)
        if state.actions_left and len(state.hero.army) >= 4 and state.hero.hp == state.hero.max_hp and all(t.hp == t.max_hp for t in state.hero.army):
            break
        rest(state, budget=budget)
    assert state.status == 'playing' and spent == 180
    assert not dead_ids.intersection(t.id for t in state.hero.army)
    state.explore(approach='western')
    assert [(u.kind, u.hp) for u in state.battle.units if u.team == 'enemy'] == [('archer', 20)]
    play = Journey(state)
    while not play.battle.outcome:
        play.do('auto_turn')
        budget.checkpoint()
    assert_one_rout_reward(play)


def test_a_hundred_seeds_preserve_required_sources_and_the_twelve_relic_union():
    from eador.content import RELICS

    for seed in range(100):
        states = {theme: State.new(seed, theme=theme) for theme in ('frontier', 'elderwild', 'ruins')}
        wild = states['elderwild']
        screen, = [p for p in wild.provinces.values() if p.site_kind == 'smuggler_screen']
        assert screen.pos[0] == 0
        assert {'supply_cache', 'pack_hunt'} <= {p.site_kind for p in wild.provinces.values()}
        assert any(p.site_relic == 'oak_standard' for p in wild.provinces.values())
        for state in states.values():
            assert state.provinces[(-2, 0)].site_kind == 'shrine'
            assert {'den', 'explorer_camp', 'border_watch'} <= {p.site_kind for p in state.provinces.values()}
        frontier, ruins = states['frontier'], states['ruins']
        crossing, = [p for p in frontier.provinces.values() if p.site_kind == 'courier_crossing']
        assert crossing.site_relic == screen.site_relic == 'veil_censer'
        assert {'stranded_explorer', 'muster_yard'} <= {p.site_kind for p in frontier.provinces.values()}
        assert {'sealed_vault', 'broken_observatory'} <= {p.site_kind for p in ruins.provinces.values()}
        assert {p.site_relic for state in states.values() for p in state.provinces.values() if p.site_relic} == set(RELICS)
