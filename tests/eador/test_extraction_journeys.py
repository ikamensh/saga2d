"""Paid, reproducible adventure plans; no battle statistics or positions are edited."""
import pytest

from eador.model import State, RuleError
from tools.eador_extraction_campaign import AdventureOrders, prepared_crossing, prepare_adventure, crossing_route, cache_route


class Journey(AdventureOrders):
    """Record real orders and verify their exact saved continuation after each one."""
    def __init__(self, state):
        super().__init__(State.from_json(state.to_json()))

    @property
    def battle(self):
        return self.state.battle

    def do(self, command, *args, **kwargs):
        battle = self.battle
        forecast = None
        if command in ('attack', 'pin'):
            attacker, target = (battle.unit(uid) for uid in args)
            hp = target.hp, attacker.hp
            forecast = getattr(battle, 'preview' if command == 'attack' else 'pin_preview')(*args)
        elif command == 'cast':
            target = battle.unit(args[1]); hp = target.hp
            forecast = battle.spell_preview(*args, **kwargs)
        super().do(command, *args, **kwargs)
        if command in ('attack', 'pin'):
            assert (hp[0] - target.hp, hp[1] - attacker.hp) == forecast
        elif command == 'cast':
            assert abs(target.hp - hp) == forecast
        text = self.state.to_json()
        self.state = State.from_json(text)
        assert self.state.to_json() == text



def assert_one_reward(play):
    state, battle = play.state, play.battle
    assert battle.outcome_reason == 'escape' and any(u.alive and u.team == 'enemy' for u in battle.units)
    assert all(u.alive for u in battle.units if u.team == 'player')
    gold, crystals, reward, pos = state.gold, state.crystals, state.battle_adventure, state.hero.pos
    state.resolve_battle()
    assert state.gold == gold + reward.gold and state.crystals == crystals + reward.crystals
    assert state.provinces[pos].explored and state.battle_adventure is None
    state = State.from_json(state.to_json())
    while state.choice:
        state.choose(state.choice.options[0].id)
        state = State.from_json(state.to_json())
    before = state.to_json()
    with pytest.raises(RuleError):
        state.explore()
    with pytest.raises(RuleError):
        state.resolve_battle()
    assert state.to_json() == before


def test_paid_guide_saves_a_turn_against_the_same_guards_and_rewards_only_once():
    """The free route crosses a slowing shot; the bought flank reaches extraction sooner."""
    baseline = prepared_crossing().to_json()
    direct = crossing_route(State.from_json(baseline), 'direct', orders_type=Journey)
    guided = crossing_route(State.from_json(baseline), 'guided', orders_type=Journey)
    assert (direct.battle.round, guided.battle.round) == (3, 2)
    assert direct.state.gold == guided.state.gold + 20
    assert direct.state.battle_adventure.gold == guided.state.battle_adventure.gold == 50
    assert any(command == 'cast' for command, *_ in guided.orders)
    assert any(command == 'swap' for command, *_ in guided.orders)
    assert_one_reward(direct); assert_one_reward(guided)



@pytest.mark.parametrize('hero_class', ['Commander', 'Warrior', 'Scout', 'Wizard'])
def test_all_heroes_can_take_the_paid_southern_extraction_route(hero_class):
    state = prepare_adventure(hero_class, 'frontier')
    # This six-body army uses its Warden and Acolyte; Commander need not fill its extra slot.
    play = crossing_route(state, 'guided', orders_type=Journey)
    assert play.battle.round == 2
    assert_one_reward(play)


@pytest.mark.parametrize('hero_class', ['Commander', 'Warrior', 'Scout', 'Wizard'])
def test_all_heroes_can_keep_the_fee_and_cross_with_mobile_fire(hero_class):
    state = prepare_adventure(hero_class, 'frontier', support='ranger')
    play = crossing_route(state, 'direct', orders_type=Journey)
    assert play.battle.round == 3
    assert_one_reward(play)



@pytest.mark.parametrize('hero_class', ['Commander', 'Warrior', 'Scout', 'Wizard'])
def test_full_cache_trades_an_enemy_phase_for_gold_while_pathfinder_mitigates_it(hero_class):
    baseline = prepare_adventure(hero_class, 'elderwild').to_json()
    light = cache_route(State.from_json(baseline), 'light', orders_type=Journey)
    full = cache_route(State.from_json(baseline), 'full', orders_type=Journey)
    assert light.state.hero == full.state.hero  # The carry penalty never edits the persistent hero.
    assert full.battle.unit(0).effective_move_range == light.battle.unit(0).effective_move_range - 1
    assert full.state.battle_adventure.gold == light.state.battle_adventure.gold + 40
    assert light.battle.round == 1
    assert full.battle.round == (1 if hero_class == 'Scout' else 2)
    if hero_class != 'Scout':
        assert sum(u.hp for u in full.battle.units if u.team == 'player') < sum(u.hp for u in light.battle.units if u.team == 'player')
        assert any(command == 'swap' for command, *_ in full.orders)
    assert_one_reward(light); assert_one_reward(full)
