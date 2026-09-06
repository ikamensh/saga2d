"""Active relics are earned, occupy one slot, and reuse existing tactical orders."""
from pathlib import Path

from eador.model import State
from tools.eador_campaign import finish_battle
from tools.eador_relic_campaign import prepare_censer_watch


def test_an_earned_censer_grants_one_saved_smoke_charge_in_a_later_watch():
    state = prepare_censer_watch()
    assert state.hero.relic == 'veil_censer' and 'veil_censer' in state.inventory
    hero = state.battle.unit(0)
    assert hero.abilities == ('smoke',)
    before = state.to_json()
    cloud = state.battle.smoke_preview(0, hero.pos)
    assert state.to_json() == before
    state.battle.smoke(0, hero.pos)
    assert hero.acted and hero.moved and hero.spent_abilities == ('smoke',)
    loaded = State.from_json(state.to_json())
    assert loaded.to_json() == state.to_json()
    assert loaded.battle.smoke_clouds == [cloud] and loaded.battle.smoke_targets(0) == set()
    loaded.battle.end_turn()
    assert loaded.battle.smoke_clouds == [] and loaded.battle.unit(0).spent_abilities == ('smoke',)


def test_existing_active_crossing_keeps_its_reward_and_exact_continuation():
    fixtures = Path(__file__).parent / 'fixtures'
    state = State.from_json((fixtures / 'v11_crossing_relic_battle.json').read_text())
    assert state.battle_adventure.relic == 'merchant_seal'
    assert state.provinces[(0, 2)].site_relic == 'merchant_seal'
    assert not state.battle.unit(0).abilities
    finish_battle(state)
    import json
    actual = json.loads(state.to_json())
    expected = json.loads((fixtures / 'v11_crossing_relic_result.json').read_text())
    assert actual.pop('rules_id') == 'standard-1'
    actual.pop('schema_version'); expected.pop('schema_version')
    assert actual == expected


def test_censer_uses_one_equipped_slot_and_cannot_change_power_during_combat():
    import json
    import pytest
    from eador.model import RuleError, SaveFormatError
    state = prepare_censer_watch()
    before = state.to_json()
    with pytest.raises(RuleError):
        state.equip('moonstone')
    assert state.to_json() == before
    for relic, abilities, spent in (('moonstone', ['smoke'], []),
                                    ('veil_censer', ['smoke', 'swap'], []),
                                    ('veil_censer', [], ['smoke'])):
        data = json.loads(before)
        data['hero']['relic'] = relic
        hero = next(u for u in data['battle']['units'] if u['id'] == 0)
        hero['abilities'], hero['spent_abilities'] = abilities, spent
        with pytest.raises(SaveFormatError):
            State.from_json(json.dumps(data))
    assert state.to_json() == before


def test_new_relic_sources_and_old_equipment_remain_discoverable_across_themes():
    from eador.content import RELICS
    assert len(RELICS) == 12
    for seed in range(100):
        for theme, sources, old_relic in (
            ('frontier', {(0, 2): ('courier_crossing', 'veil_censer'), (-1, 1): ('muster_yard', 'vanguard_drum')}, 'merchant_seal'),
            ('elderwild', {(-1, -1): ('supply_cache', 'porter_rune')}, 'oak_standard'),
            ('ruins', {(-1, 1): ('sealed_vault', 'mirror_badge')}, 'iron_crown'),
        ):
            state = State.new(seed, theme=theme)
            for pos, identity in sources.items():
                site = state.provinces[pos]
                assert (site.site_kind, site.site_relic) == identity
            assert any(site.site_relic == old_relic for site in state.provinces.values())
            assert state.provinces[(-2, 0)].site_kind == 'shrine'
            assert state.provinces[(-2, 2)].site_kind == 'den'
            assert state.provinces[(-1, 2)].site_kind == 'explorer_camp'
            assert any(site.site_kind == 'border_watch' for site in state.provinces.values())
            assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_earned_censer_screen_and_guard_both_hold_with_defenders_alive():
    from tools.eador_extraction_campaign import AdventureOrders
    from tools.eador_relic_campaign import censer_watch_route

    class SavedOrders(AdventureOrders):
        def do(self, command, *args, **kwargs):
            if command == 'smoke':
                # The same earned hero can choose a bad screen that blocks its Acolyte.
                before = self.state.to_json()
                bad = State.from_json(before)
                assert bad.battle.unit(1) in bad.battle.spell_targets('heal', caster_id=5)
                bad.battle.smoke(0, (0, 0))
                assert bad.battle.unit(1) not in bad.battle.spell_targets('heal', caster_id=5)
                assert State.from_json(bad.to_json()).to_json() == bad.to_json()
                assert self.state.to_json() == before
            super().do(command, *args, **kwargs)
            saved = self.state.to_json()
            self.state = State.from_json(saved)
            assert self.state.to_json() == saved

    baseline = prepare_censer_watch(ranger=True).to_json()
    screened = censer_watch_route(State.from_json(baseline), orders_type=SavedOrders)
    guarded = censer_watch_route(State.from_json(baseline), smoke=False, orders_type=SavedOrders)
    assert screened.after_screen_hp > guarded.after_screen_hp
    for play in (screened, guarded):
        assert play.battle.outcome_reason == 'hold' and play.battle.round == 3
        assert all(u.alive for u in play.battle.units if u.team == 'player')
        assert any(u.alive for u in play.battle.units if u.team == 'enemy')
        play.state.resolve_battle()
        assert play.state.provinces[(0, -2)].explored


def test_both_earned_relic_branches_hold_the_gate_and_preserve_every_order_on_reload():
    from dataclasses import asdict
    import pytest
    from eador.model import RuleError
    from tools.eador_extraction_campaign import AdventureOrders
    from tools.eador_relic_campaign import porter_gate_route, mirror_gate_route

    class SavedOrders(AdventureOrders):
        def do(self, command, *args, **kwargs):
            before = self.state.to_json()
            target_before = asdict(self.battle.unit(args[1])) if command in ('repulse', 'swap') else None
            actor_pos = self.battle.unit(args[0]).pos if target_before else None
            forecast = self.battle.repulse_preview(*args) if command == 'repulse' else None
            if command == 'repulse':
                # Controlled counter-fixtures use the earned hero and its exact charge.
                # They isolate anchoring and occupancy; these two enemy states are not
                # claimed as additional naturally played encounters.
                for counter in ('guard', 'occupied'):
                    clone = State.from_json(before)
                    if counter == 'guard':
                        clone.battle.unit(args[1]).stance = 'guard'
                    else:
                        blocker = next(u for u in clone.battle.units if u.team == 'enemy' and u.id != args[1])
                        blocker.pos = forecast
                    clone = State.from_json(clone.to_json())
                    denied = clone.to_json()
                    with pytest.raises(RuleError):
                        clone.battle.repulse(*args)
                    assert clone.to_json() == denied
            assert self.state.to_json() == before
            super().do(command, *args, **kwargs)
            if command == 'repulse':
                assert asdict(self.battle.unit(args[1])) == {**target_before, 'pos': forecast}
                assert self.battle.unit(args[1]).alive
            elif command == 'swap':
                assert asdict(self.battle.unit(args[1])) == {**target_before, 'pos': actor_pos, 'moved': True}
            saved = self.state.to_json()
            self.state = State.from_json(saved)
            assert self.state.to_json() == saved

    for route, relic, theme, rounds in ((porter_gate_route, 'porter_rune', 'ruins', 5),
                                        (mirror_gate_route, 'mirror_badge', 'elderwild', 2)):
        play = route(orders_type=SavedOrders)
        state = play.state
        assert state.campaign.stage == 3 and state.theme == theme and state.hero.relic == relic
        assert play.battle.outcome_reason == 'hold' and play.battle.round == rounds
        assert all(u.alive for u in play.battle.units if u.team == 'player')
        assert any(u.alive for u in play.battle.units if u.team == 'enemy')
        finish_battle(state)
        assert state.campaign.phase == 'completed'
        assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_earned_drum_clears_a_real_watch_pin_without_refreshing_a_spent_ranger():
    from dataclasses import asdict
    from tools.eador_extraction_campaign import AdventureOrders
    from tools.eador_relic_campaign import drum_watch_route

    class SavedOrders(AdventureOrders):
        def do(self, command, *args, **kwargs):
            if command == 'rally':
                before = self.state.to_json()
                target = asdict(self.battle.unit(args[1]))
                forecast = self.battle.rally_preview(*args)
                assert self.state.to_json() == before and (0, -1) in forecast.reachable
                spent = State.from_json(before)
                spent.battle.guard(args[1])
                spent_before = asdict(spent.battle.unit(args[1]))
                spent.battle.rally(*args)
                assert asdict(spent.battle.unit(args[1])) == {**spent_before, 'pinned': False}
                assert not spent.battle.reachable(args[1]) and not spent.battle.targets(args[1])
            super().do(command, *args, **kwargs)
            if command == 'rally':
                assert asdict(self.battle.unit(args[1])) == {**target, 'pinned': False}
            saved = self.state.to_json()
            self.state = State.from_json(saved)
            assert self.state.to_json() == saved

    play = drum_watch_route(orders_type=SavedOrders)
    assert play.state.hero.relic == 'vanguard_drum'
    assert play.battle.unit(5).pos == (0, -1) and play.battle.unit(5).acted
    assert any('Archer pins Ranger' in entry for entry in play.battle.log)
    restored = State.from_json(play.state.to_json())
    finish_battle(play.state); finish_battle(restored)
    assert play.state.to_json() == restored.to_json()
    assert play.state.provinces[(0, -2)].explored


def test_earned_mirror_extends_arrival_but_cannot_evacuate_with_a_spent_hero_order():
    """The actual Badge can deliver its hero to an exit, but arrival costs that phase's action."""
    import pytest
    from eador.model import RuleError
    from tools.eador_relic_campaign import prepare_relic_gate, _recover_at
    state = prepare_relic_gate('mirror_badge')
    state.retreat()
    _recover_at(state, (-1, -1))
    state.explore(approach='light')
    battle = state.battle
    ids = {u.pos: u.id for u in battle.units if u.team == 'player'}
    wolf = next(u.id for u in battle.units if u.team == 'enemy' and u.pos == (-3, 0))
    battle.move(ids[(-1, 1)], (-3, 1)); battle.attack(ids[(-1, 1)], wolf)
    battle.move(ids[(-1, 0)], (-2, 0)); battle.attack(ids[(-1, 0)], wolf)
    battle.move(0, (-2, 1)); battle.swap(0, ids[(-1, 1)])
    assert battle.unit(0).pos in battle.objective.exits
    assert not any(u.alive and u.team == 'enemy' and battle.grid.distance(u.pos, battle.unit(0).pos) <= 1 for u in battle.units)
    before = state.to_json()
    with pytest.raises(RuleError, match='unspent action'):
        battle.evacuate()
    assert state.to_json() == before
    state = State.from_json(before)
    state.battle.end_turn(); state.battle.evacuate()
    assert state.battle.outcome_reason == 'escape' and state.battle.round == 2
    assert any(u.alive for u in state.battle.units if u.team == 'enemy')
