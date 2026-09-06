"""Pin changes movement choices without disabling attacks, Guard or saved continuation."""
from eador.battle import Battle
from eador.model import RuleError
import pytest


def test_pin_slows_the_next_enemy_turn_then_reopens_after_one_skipped_turn():
    """An Archer trades damage for distance; the following turn still allows a normal order."""
    battle = Battle.clash([('archer', 20)], [('swordsman', 34)], 'plains')
    battle.move(0, (0, 0))
    target = battle.unit(1000)
    assert battle.unit(0).can_pin
    assert battle.pin_targets(0) == [target]
    assert battle.pin_preview(0, 1000) == (2, 0)
    battle.pin(0, 1000)
    assert target.hp == 32 and target.pinned and target.effective_move_range == 1
    assert battle.unit(0).acted
    battle = Battle.from_dict(battle.to_dict())
    battle.end_turn()
    assert battle.grid.distance(battle.unit(1000).pos, (3, -1)) == 1
    assert not battle.unit(1000).pinned
    assert battle.unit(0).pin_cooldown == 1 and battle.pin_targets(0) == []
    saved = battle.to_dict()
    with pytest.raises(RuleError):
        battle.pin(0, 1000)
    assert battle.to_dict() == saved
    battle.guard(0)
    battle = Battle.from_dict(battle.to_dict())
    battle.end_turn()
    assert battle.unit(0).pin_cooldown == 0
    assert battle.pin_targets(0) == [battle.unit(1000)]


def test_loading_a_v6_archer_battle_preserves_its_exact_automatic_continuation():
    """New controls do not retroactively give an old active army a different AI plan."""
    from pathlib import Path
    import json
    from eador.model import State

    fixture = Path(__file__).parent / 'fixtures'
    original = json.loads((fixture / 'v6_archer_battle.json').read_text())
    state = State.from_json(json.dumps(original))
    assert json.loads(state.to_json())['schema_version'] == 11
    assert json.loads(state.to_json())['provinces'] == original['provinces']
    assert json.loads(state.to_json())['inventory'] == original['inventory']
    assert not any(unit.can_pin for unit in state.battle.units)
    while state.battle.outcome is None:
        state.battle.auto_turn()
    actual = json.loads(json.dumps(state.battle.to_dict()))
    assert actual['objective'].pop('exits') == []
    assert actual.pop('sight_rules') == 'open'
    assert actual.pop('smoke_clouds') == []
    for unit in actual['units']:
        assert unit.pop('cargo_penalty') == 0
        assert unit.pop('spent_abilities') == []
        for field in ('abilities', 'pinned', 'pin_cooldown'):
            unit.pop(field)
    assert actual == json.loads((fixture / 'v6_archer_battle_result.json').read_text())


@pytest.mark.parametrize('theme', ['frontier', 'elderwild', 'ruins'])
def test_new_shards_offer_all_three_tactical_relic_sources_away_from_home(theme):
    """Boots remain discoverable while the Watch and Den gain their new capabilities."""
    from eador.model import State
    for seed in range(20):
        state = State.new(seed, theme=theme)
        sources = {p.site_kind: p.site_relic for p in state.provinces.values() if p.site_kind}
        assert sources['border_watch'] == 'watch_bell'
        assert sources['den'] == 'storm_quiver'
        assert sources['explorer_camp'] == 'wayfarer_boots'
        assert state.provinces[(-2, 0)].site_kind == 'shrine'
        assert all(state.grid.path(state.hero.pos, p.pos) for p in state.provinces.values()
                   if p.site_relic in ('watch_bell', 'storm_quiver', 'wayfarer_boots'))


def pin_duel(*, enemy='swordsman', hp=34, attack=8, stance=None):
    """A small public battle fixture makes adjacent counterattacks and HP limits explicit."""
    from eador.battle import BattleUnit
    units = [BattleUnit(0, 'player', 'archer', (0, 0), 20, 20, attack, 1, 3, 3, abilities=('pin',)),
             BattleUnit(1000, 'enemy', enemy, (1, 0), hp, hp, 11, 4, 3, 1, stance=stance)]
    return Battle(units, {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3}, 0, set(), hero_id=None)


@pytest.mark.parametrize('hp,attack,expected', [(34, 9, (3, 10)), (3, 11, (3, 0))])
def test_pin_rounds_damage_up_before_clamping_to_health_and_previews_real_reactions(hp, attack, expected):
    """Pin can finish a wounded target and uses the ordinary adjacent ranged retaliation."""
    battle = pin_duel(hp=hp, attack=attack)
    before = battle.to_dict()
    assert battle.pin_preview(0, 1000) == expected and battle.to_dict() == before
    battle.pin(0, 1000)
    assert (hp - battle.unit(1000).hp, 20 - battle.unit(0).hp) == expected
    assert battle.unit(1000).pinned == battle.unit(1000).alive


def test_pin_is_a_ranged_counter_to_brace_without_consuming_its_waiting_reaction():
    """Even adjacent, the special shot does not trigger a spear or spend its reserved reaction."""
    battle = pin_duel(enemy='pikeman', hp=28, stance='brace')
    assert battle.pin_preview(0, 1000) == (2, 0)
    battle.pin(0, 1000)
    assert battle.unit(1000).stance == 'brace' and not battle.unit(1000).retaliated
    assert battle.unit(0).hp == 20


def test_a_second_shooter_cannot_stack_or_extend_pin_but_can_attack():
    """Control uses one next-turn window; additional archers must choose another action."""
    from eador.battle import BattleUnit
    battle = pin_duel()
    battle.units.append(BattleUnit(1, 'player', 'archer', (-1, 0), 20, 20, 8, 1, 3, 3, abilities=('pin',)))
    battle.pin(0, 1000)
    before = battle.to_dict()
    assert battle.pin_targets(1) == []
    with pytest.raises(RuleError):
        battle.pin(1, 1000)
    assert battle.to_dict() == before
    battle.attack(1, 1000)
    assert battle.unit(1).acted and battle.unit(1000).pinned


def test_enemy_pin_restricts_one_player_turn_while_attack_and_guard_remain_available():
    """A marksman delays a melee approach, then its cooldown lets the player close normally."""
    from eador.battle import BattleUnit
    battle = Battle([BattleUnit(0, 'player', 'swordsman', (0, 0), 34, 34, 11, 4, 3, 1),
                     BattleUnit(1000, 'enemy', 'archer', (3, 0), 20, 20, 8, 1, 3, 3, abilities=('pin',))],
                    {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3}, 0, set(), hero_id=None)
    battle.end_turn()
    assert battle.unit(0).pinned and battle.unit(0).effective_move_range == 1
    assert battle.unit(1000).pin_cooldown == 2
    battle = Battle.from_dict(battle.to_dict())
    assert (1, 0) in battle.reachable(0) and (2, 0) not in battle.reachable(0)
    battle.move(0, (1, 0))
    battle.guard(0)
    battle.end_turn()
    assert not battle.unit(0).pinned and battle.unit(0).effective_move_range == 3
    assert battle.unit(1000).pin_cooldown == 1
    battle.move(0, (2, 0))
    battle.attack(0, 1000)
    assert battle.unit(0).acted


def test_archers_keep_full_damage_when_the_enemy_can_already_reach_an_ally():
    """Slowing an engaged enemy wastes damage and does not protect the nearby frontline."""
    from eador.battle import BattleUnit
    battle = pin_duel()
    battle.unit(1000).pos = (3, 0)
    battle.units.append(BattleUnit(1, 'player', 'militia', (2, 0), 24, 24, 8, 2, 3, 1))
    battle.guard(1)
    battle.auto_turn()
    assert battle.unit(0).pin_cooldown == 0


def test_campaign_saves_pin_status_and_cooldown_at_each_player_phase():
    """The normal Shrine battle can be saved after a shot and both cooldown boundaries."""
    from eador.model import State
    state = State.new(7)
    state.explore()
    archer = next(u for u in state.battle.units if u.team == 'player' and u.can_pin)
    state.battle.move(archer.id, (-1, 0))
    state.battle.pin(archer.id, state.battle.pin_targets(archer.id)[0].id)
    assert archer.pin_cooldown == 2
    for expected in (2, 1, 0):
        saved = state.to_json()
        state = State.from_json(saved)
        assert state.to_json() == saved
        assert state.battle.unit(archer.id).pin_cooldown == expected
        if expected:
            for unit in state.battle.units:
                if unit.team == 'player' and unit.alive and not unit.acted:
                    state.battle.guard(unit.id)
            state.battle.end_turn()


@pytest.mark.parametrize('theme', ['frontier', 'elderwild', 'ruins'])
def test_real_adventures_award_equip_and_activate_both_relic_capabilities(theme):
    """All three sources are obtainable through battles, choices and travel in every theme."""
    from dataclasses import replace
    from eador.model import State
    from tools.eador_campaign import finish_battle, provision_army, rest, march_to

    state = State.new(7, theme=theme)
    state.build('barracks')
    state.recruit('swordsman')
    state.explore()
    finish_battle(state)
    rest(state)
    provision_army(state)
    watch = next(p.pos for p in state.provinces.values() if p.site_kind == 'border_watch')
    for destination in ((-2, 2), (-1, 2), watch):
        march_to(state, destination)
        rest(state)
        provision_army(state)
        march_to(state, destination)
        if not state.actions_left:
            rest(state)
            march_to(state, destination)
        state.explore()
        finish_battle(state)
        if destination != watch:
            rest(state)
            provision_army(state)
    assert {'storm_quiver', 'watch_bell', 'wayfarer_boots'} <= set(state.inventory)
    for relic in ('watch_bell', 'storm_quiver', 'wayfarer_boots'):
        state.equip(relic)
        state = State.from_json(state.to_json())
        # A solo arena isolates the earned hero capability from its campaign army.
        battle = Battle.create(replace(state.hero, army=[]), ['pikeman'], 'plains', state.spells)
        hero = battle.unit(0)
        assert hero.can_brace == (relic == 'watch_bell')
        assert hero.can_pin == (relic == 'storm_quiver')
        assert hero.terrain_walk == (relic == 'wayfarer_boots')
        battle.move(0, (0, 0))
        if hero.can_pin:
            assert hero.attack_range == 1 and battle.pin_targets(0)
            battle.pin(0, battle.pin_targets(0)[0].id)
            assert hero.pin_cooldown == 2
        else:
            battle.guard(0)
            assert hero.stance == ('brace' if hero.can_brace else 'guard')
        restored = Battle.from_dict(battle.to_dict())
        assert restored.to_dict() == battle.to_dict()


@pytest.mark.parametrize('change', [dict(pinned='yes'), dict(pin_cooldown=-1), dict(pin_cooldown=3),
                                      dict(abilities=['root']), dict(abilities=['pin', 'pin'])])
def test_corrupt_saved_pin_data_fails_before_the_next_enemy_turn(change):
    """Statuses and capabilities are an explicit bounded save contract."""
    import json
    from eador.model import State, SaveFormatError
    state = State.new(7)
    state.explore()
    data = json.loads(state.to_json())
    archer = next(u for u in data['battle']['units'] if u['kind'] == 'archer')
    archer.update(change)
    with pytest.raises(SaveFormatError):
        State.from_json(json.dumps(data))
