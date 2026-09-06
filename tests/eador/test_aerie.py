from eador.model import State
from tools.eador_aerie_campaign import prepare_aerie, aerie_western_route
from tests.eador.test_extraction_journeys import Journey
from tests.eador.test_pack_hunt import assert_one_rout_reward


def test_paid_control_party_wins_a_saved_aerie_rout_using_a_delayed_sortie():
    state = prepare_aerie()
    assert state.hero.pos == (0, 0)
    assert state.provinces[(0, 0)].site_kind == 'aerie_raid'
    assert [t.kind for t in state.hero.army] == ['militia', 'militia', 'archer', 'pikeman', 'adept', 'skyrider']
    play = aerie_western_route(state, orders_type=Journey)
    assert play.battle.outcome_reason == 'rout'
    assert all(u.alive for u in play.battle.units if u.team == 'player')
    assert any(command == 'repulse' for command, *_ in play.orders)
    assert_one_rout_reward(play)


def test_same_paid_party_uses_landing_control_or_preemptive_fire_in_two_free_assemblies():
    from tools.eador_aerie_campaign import aerie_northern_route

    original = prepare_aerie().to_json()
    west = aerie_western_route(State.from_json(original), orders_type=Journey)
    north = aerie_northern_route(State.from_json(original), orders_type=Journey)
    assert (west.battle.round, north.battle.round) == (4, 3)
    assert (sum(u.max_hp - u.hp for u in west.battle.units if u.team == 'player'),
            sum(u.max_hp - u.hp for u in north.battle.units if u.team == 'player')) == (53, 34)
    assert west.battle.unit(5).spent_abilities == ('repulse',)
    assert north.battle.unit(5).spent_abilities == ()
    assert west.state.gold == north.state.gold and west.state.crystals == north.state.crystals
    assert (west.battle.mana, north.battle.mana) == (6, 2)
    assert [order[0] for order in north.orders[:4]] == ['attack', 'attack', 'attack', 'cast']
    assert_one_rout_reward(west); assert_one_rout_reward(north)


def test_smaller_scout_party_can_rotate_its_ground_escort_without_flight_or_repulse():
    from tools.eador_aerie_campaign import aerie_scout_route

    state = prepare_aerie('Scout', party='ground')
    assert len(state.hero.army) == 5 and state.hero.level == 2 and state.turn == 5
    assert [t.kind for t in state.hero.army] == ['militia', 'militia', 'archer', 'pikeman', 'warden']
    assert state.buildings == {'market', 'barracks'}
    play = aerie_scout_route(state, orders_type=Journey)
    assert play.battle.round == 5 and play.battle.mana == 8
    assert sum(u.max_hp-u.hp for u in play.battle.units if u.team == 'player') == 27
    assert ('swap', (5, 1), {}) in play.orders
    assert_one_rout_reward(play)


def test_aerie_sources_preserve_every_fixed_site_and_all_twelve_relics_for_a_hundred_seeds():
    from eador.content import RELICS
    from eador.worldgen import generate

    fixed = {
        'frontier': {(0, 2): 'courier_crossing', (-1, 1): 'muster_yard', (0, -1): 'stranded_explorer'},
        'elderwild': {(-1, -1): 'supply_cache', (-1, 1): 'pack_hunt', (0, -1): 'smuggler_screen'},
        'ruins': {(-1, 1): 'sealed_vault', (-1, 0): 'broken_observatory', (0, 0): 'aerie_raid', (1, 0): 'barrow'},
    }
    for seed in range(100):
        rewards = set()
        for theme, sites in fixed.items():
            world = generate(seed, theme)
            for pos, kind in {(-2, 0): 'shrine', (-2, 2): 'den', (-1, 2): 'explorer_camp', **sites}.items():
                assert world[pos].site_kind == kind
            assert any(p.site_kind == 'border_watch' for p in world.values())
            assert world[(-2, 1)].site_kind != 'aerie_raid'
            if theme == 'ruins':
                assert world[(0, 0)].site_relic == 'watch_bell'
                assert world[(0, 0)].site_guards == ['skyrider', 'skyrider', 'archer', 'pikeman']
            rewards.update(p.site_relic for p in world.values() if p.site_relic)
        assert rewards == set(RELICS)


def test_actual_prior_barrow_keeps_its_world_battle_and_exact_reward_continuation():
    from pathlib import Path
    from tools.eador_campaign import finish_battle

    fixtures = Path(__file__).parent / 'fixtures'
    text = (fixtures / 'v12_pre_aerie_barrow_battle.json').read_text()
    state = State.from_json(text)
    assert state.to_json() == text
    assert state.provinces[(0, 0)].site_kind == 'barrow'
    assert all(p.site_kind != 'aerie_raid' for p in state.provinces.values())
    finish_battle(state)
    assert state.to_json() == (fixtures / 'v12_pre_aerie_barrow_result.json').read_text()


def test_failed_sortie_and_defense_preserve_finite_losses_across_a_paid_changed_assembly_retry():
    from tools.eador_aerie_campaign import aerie_failed_sortie, aerie_retry_route

    play = aerie_failed_sortie(prepare_aerie(), orders_type=Journey)
    state = play.state
    assert play.battle.outcome_reason == 'hero_death' and play.battle.round == 56
    gold, crystals, xp = state.gold, state.crystals, state.hero.xp
    state.resolve_battle()
    assert (state.gold, state.crystals, state.hero.xp) == (gold - 20, crystals, xp)
    assert not state.provinces[(0, 0)].explored and not state.choice
    assert [t.kind for t in state.hero.army] == ['pikeman']
    assert state.provinces[(0, 0)].site_guards == ['archer']
    assert state.provinces[(0, 0)].site_guard_hp == [12]
    state = State.from_json(state.to_json())
    gold, crystals = state.gold, state.crystals
    state.recruit('skyrider')
    assert (state.gold, state.crystals) == (gold - 60, crystals - 3)
    retry = aerie_retry_route(State.from_json(state.to_json()), orders_type=Journey)
    assert retry.battle.round == 1
    assert retry.state.battle_adventure.approach == 'northern'
    assert [(u.kind, u.max_hp) for u in retry.battle.units if u.team == 'enemy'] == [('archer', 20)]
    assert_one_rout_reward(retry)


def test_production_forecasts_match_reaction_and_flight_crosses_an_otherwise_blocked_landing():
    from tools.audit_eador_aerie import RecordedOrders, without_flight_reachable

    state = prepare_aerie(); state.explore(approach='western')
    rear = [u.id for u in state.battle.units if u.team == 'enemy' and u.kind == 'skyrider'][1]
    assert (-2, 3) in state.battle.reachable(rear)
    assert (-2, 3) not in without_flight_reachable(state.battle, rear)
    play = aerie_western_route(prepare_aerie(), orders_type=RecordedOrders)
    assert play.flight_landings == [{'unit': 6, 'source': (-1, 1), 'destination': (2, 0)}]
    assert len(play.snapshots) == len(play.orders)
    assert play.battle.outcome_reason == 'rout'
