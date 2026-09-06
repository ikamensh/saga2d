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
    assert state.to_json() == (fixtures / 'v11_crossing_relic_result.json').read_text().strip()


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
