"""Paid, reproducible adventure plans; no battle statistics or positions are edited."""
import pytest

from eador.model import BUILDINGS, State, RuleError
from tests.eador.test_extraction import prepared_crossing
from tools.eador_campaign import finish_battle, march_to, rest


class Journey:
    """Record real orders and verify their exact saved continuation after each one."""
    def __init__(self, state):
        self.state = State.from_json(state.to_json())
        self.orders = []

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
        getattr(battle, command)(*args, **kwargs)
        if command in ('attack', 'pin'):
            assert (hp[0] - target.hp, hp[1] - attacker.hp) == forecast
        elif command == 'cast':
            assert abs(target.hp - hp) == forecast
        self.orders.append((command, args, kwargs))
        text = self.state.to_json()
        self.state = State.from_json(text)
        assert self.state.to_json() == text

    def guard_remaining(self):
        for unit in self.battle.units:
            if unit.alive and unit.team == 'player' and not unit.acted:
                self.do('guard', unit.id)

    def enemy(self, kind):
        return next(u.id for u in self.battle.units if u.team == 'enemy' and u.kind == kind)


def crossing_route(state, approach):
    state.explore(approach=approach)
    play = Journey(state)
    pikeman, brigand = play.enemy('pikeman'), play.enemy('brigand')
    if approach == 'guided':
        play.do('move', 1, (2, 0)); play.do('attack', 1, brigand)
        play.do('move', 4, (2, 1)); play.do('attack', 4, brigand)
        play.do('move', 3, (0, 0)); play.do('pin', 3, pikeman)
        play.do('move', 0, (1, 2))
        if play.battle.unit(brigand).alive:
            play.do('attack', 0, brigand)
        play.do('move', 5, (0, 1))
        if len(state.hero.army) == 6:
            play.do('move', 6, (-1, 1))
        play.do('move', 2, (-1, 2))
        play.guard_remaining(); play.do('end_turn')
        play.do('cast', 'heal', 3, caster_id=5)
        if len(state.hero.army) == 6:
            play.do('attack', 6, pikeman); play.do('move', 6, (0, -1))
        play.do('move', 4, (3, 0)); play.do('move', 0, (2, 1))
    else:
        ranger = next(u.id for u in play.battle.units if u.team == 'player' and u.kind == 'ranger')
        healer = next((u.id for u in play.battle.units if u.team == 'player' and u.can_heal), None)
        play.do('move', 1, (1, 0))
        if play.battle.unit(brigand) in play.battle.targets(ranger):
            play.do('attack', ranger, brigand); play.do('move', ranger, (-1, 1))
        else:
            play.do('move', ranger, (-1, 1)); play.do('attack', ranger, brigand)
        play.do('move', 3, (0, 0)); play.do('attack', 3, brigand)
        play.do('attack', 1, brigand)
        play.do('move', 4, (0, 1)); play.do('move', 0, (-1, 0))
        play.do('move', 2, (-1, 2))
        if healer is not None:
            play.do('move', healer, (-2, 0))
        play.guard_remaining(); play.do('end_turn')
        if state.hero.hero_class in ('Commander', 'Warrior'):
            assert play.battle.unit(0).pinned
        play.do('move', 1, (3, 0)); play.do('move', 3, (0, -1)); play.do('pin', 3, pikeman)
        play.do('move', 4, (2, 1)); play.do('move', 0, (0, 0))
        if play.battle.unit(0).hp < play.battle.unit(0).max_hp:
            play.do('cast', 'heal', 0, caster_id=healer)
        play.guard_remaining(); play.do('end_turn')
        play.do('move', 1, (3, -1)); play.do('move', 4, (3, 0)); play.do('move', 0, (2, 0))
    play.do('swap', 4, 0)
    assert not play.battle.unit(0).acted and play.battle.outcome is None
    play.do('evacuate')
    return play


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
    direct = crossing_route(State.from_json(baseline), 'direct')
    guided = crossing_route(State.from_json(baseline), 'guided')
    assert (direct.battle.round, guided.battle.round) == (3, 2)
    assert direct.state.gold == guided.state.gold + 20
    assert direct.state.battle_adventure.gold == guided.state.battle_adventure.gold == 50
    assert any(command == 'cast' for command, *_ in guided.orders)
    assert any(command == 'swap' for command, *_ in guided.orders)
    assert_one_reward(direct); assert_one_reward(guided)


def prepare_adventure(hero_class, theme, *, support='healer'):
    """Pay for a Warden and support through western conquest, then recover at the site."""
    state = State.new(7, hero_class, theme=theme)
    state.build('barracks'); state.recruit('warden')
    state.explore(); finish_battle(state)
    for pos in ((-1, -1), (-1, 0)):
        march_to(state, pos); rest(state)
    building = 'temple' if support == 'healer' else 'archery'
    for _ in range(48):
        assert state.status == 'playing'
        if building not in state.buildings and state.gold >= BUILDINGS[building].cost:
            state.build(building)
        if building in state.buildings and state.gold >= state.recruit_cost(support):
            state.recruit(support)
            break
        rest(state)
    else:
        raise AssertionError('Could not fund support')
    destination = (0, 2) if theme == 'frontier' else (-1, -1)
    for _ in range(48):
        march_to(state, destination)
        if state.actions_left and all(t.hp == t.max_hp for t in state.hero.army) and state.hero.hp == state.hero.max_hp:
            return state
        rest(state)
    raise AssertionError('Could not reach the adventure recovered')


@pytest.mark.parametrize('hero_class', ['Commander', 'Warrior', 'Scout', 'Wizard'])
def test_all_heroes_can_take_the_paid_southern_extraction_route(hero_class):
    state = prepare_adventure(hero_class, 'frontier')
    # This six-body army uses its Warden and Acolyte; Commander need not fill its extra slot.
    play = crossing_route(state, 'guided')
    assert play.battle.round == 2
    assert_one_reward(play)


@pytest.mark.parametrize('hero_class', ['Commander', 'Warrior', 'Scout', 'Wizard'])
def test_all_heroes_can_keep_the_fee_and_cross_with_mobile_fire(hero_class):
    state = prepare_adventure(hero_class, 'frontier', support='ranger')
    play = crossing_route(state, 'direct')
    assert play.battle.round == 3
    assert_one_reward(play)


def cache_route(state, approach):
    state.explore(approach=approach)
    play = Journey(state)
    wolf = next(u.id for u in play.battle.units if u.team == 'enemy' and u.pos == (-3, 0))
    play.do('move', 3, (-3, 2)); play.do('attack', 3, wolf)
    play.do('move', 4, (-2, 0)); play.do('attack', 4, wolf)
    if play.battle.unit(wolf).alive:
        play.do('move', 5, (-1, -1)); play.do('attack', 5, wolf)
    if (-3, 1) in play.battle.reachable(0):
        play.do('move', 0, (-3, 1))
    else:
        play.do('move', 0, (-2, 1))
        play.guard_remaining(); play.do('end_turn')
        if play.battle.unit(0).hp < play.battle.unit(0).max_hp:
            play.do('cast', 'heal', 0, caster_id=5)
        play.do('move', 4, (-3, 1)); play.do('swap', 4, 0)
    play.do('evacuate')
    return play


@pytest.mark.parametrize('hero_class', ['Commander', 'Warrior', 'Scout', 'Wizard'])
def test_full_cache_trades_an_enemy_phase_for_gold_while_pathfinder_mitigates_it(hero_class):
    baseline = prepare_adventure(hero_class, 'elderwild').to_json()
    light = cache_route(State.from_json(baseline), 'light')
    full = cache_route(State.from_json(baseline), 'full')
    assert light.state.hero == full.state.hero  # The carry penalty never edits the persistent hero.
    assert full.battle.unit(0).effective_move_range == light.battle.unit(0).effective_move_range - 1
    assert full.state.battle_adventure.gold == light.state.battle_adventure.gold + 40
    assert light.battle.round == 1
    assert full.battle.round == (1 if hero_class == 'Scout' else 2)
    if hero_class != 'Scout':
        assert sum(u.hp for u in full.battle.units if u.team == 'player') < sum(u.hp for u in light.battle.units if u.team == 'player')
        assert any(command == 'swap' for command, *_ in full.orders)
    assert_one_reward(light); assert_one_reward(full)
