"""Campaign behavior exercised through the same commands as the game scenes."""
import pytest

from eador.model import RuleError, State


def test_a_seeded_shard_can_build_recruit_and_survive_a_save():
    """A first turn and its progress survive a portable JSON save."""
    state = State.new(seed=7)
    assert len(state.provinces) == 19
    assert state.to_json() == State.new(seed=7).to_json()
    starting_army = len(state.hero.army)
    state.build('barracks')
    state.recruit('swordsman')
    assert len(state.hero.army) == starting_army + 1
    assert state.gold >= 0
    assert State.from_json(state.to_json()).to_json() == state.to_json()
    with pytest.raises(RuleError, match='already'):
        state.build('barracks')


def finish_battle(state):
    """Resolve a real tactical encounter using the ordinary automatic player."""
    for _ in range(80):
        if state.battle.outcome:
            break
        state.battle.auto_turn()
    return state.resolve_battle()


def test_exploration_and_conquest_preserve_wounds_and_reward_advancement():
    """One adventure crosses economy, battles, rewards and campaign recovery."""
    state = State.new()
    state.explore()
    assert state.battle_kind == 'site'
    restored = State.from_json(state.to_json())
    assert restored.to_json() == state.to_json()
    finish_battle(restored)
    assert restored.provinces[restored.hero.pos].explored
    assert restored.hero.xp > 0
    target = next(p for p in restored.grid.neighbors(restored.hero.pos)
                  if restored.provinces[p].owner == 'neutral')
    restored.travel(target)
    finish_battle(restored)
    assert restored.provinces[target].owner == 'player'
    assert restored.hero.pos == target
    assert restored.hero.level > 1
    assert any(t.hp < t.max_hp for t in restored.hero.army)
    before = sum(t.hp for t in restored.hero.army)
    restored.end_turn()
    assert sum(t.hp for t in restored.hero.army) > before
    assert State.from_json(restored.to_json()).to_json() == restored.to_json()


@pytest.mark.parametrize('hero_class', ['Commander', 'Warrior', 'Scout', 'Wizard'])
@pytest.mark.parametrize('seed', range(8))
def test_each_hero_can_complete_a_seeded_campaign_with_public_commands(seed, hero_class):
    """The documented build/recruit/conquer/rest loop reaches the win condition."""
    state = State.new(seed=seed, hero_class=hero_class)
    state.build('barracks')
    state.recruit('swordsman')
    for _ in range(16):
        if state.status != 'playing':
            break
        while state.gold >= 45 and len(state.hero.army) < state.hero.max_army:
            state.recruit('swordsman')
        next_province = state.grid.path(state.hero.pos, (2, 0))[1]
        state.travel(next_province)
        if state.battle:
            finish_battle(state)
        assert len({t.id for t in state.hero.army}) == len(state.hero.army)
        assert all(0 < t.hp <= t.max_hp for t in state.hero.army)
        assert 0 < state.hero.hp <= state.hero.max_hp
        assert 0 <= state.hero.mana <= state.hero.max_mana
        state = State.from_json(state.to_json())
        if state.status == 'playing':
            state.end_turn()
            if state.battle:
                finish_battle(state)
    assert state.status == 'victory'
    with pytest.raises(RuleError, match='ended'):
        state.end_turn()


def test_an_undefended_capital_can_fall_and_retreat_does_not_capture_sites():
    """Leaving the capital and ignoring the rival has a real losing outcome."""
    state = State.new()
    state.explore()
    state.retreat()
    assert not state.provinces[state.hero.pos].explored
    assert state.actions_left == 1
    state.travel((-2, 1))
    finish_battle(state)
    assert state.hero.pos != (-2, 0)
    for _ in range(30):
        if state.status != 'playing':
            break
        state.end_turn()
        if state.battle:
            state.retreat()
    assert state.status == 'defeat'
    assert state.provinces[(-2, 0)].owner == 'rival'
    assert State.from_json(state.to_json()).status == 'defeat'


def test_invalid_campaign_actions_leave_state_unchanged():
    """Rejected UI commands never spend resources or corrupt the save."""
    state = State.new()
    for action in (lambda: state.travel((2, 0)), lambda: state.recruit('guard'),
                   lambda: state.recruit('swordsman'), lambda: state.resolve_battle()):
        before = state.to_json()
        with pytest.raises(RuleError):
            action()
        assert state.to_json() == before


def test_a_hero_at_the_capital_can_fight_off_the_rival():
    """Rival expansion enters tactical defense when the hero intercepts it."""
    state = State.new()
    state.build('barracks')
    state.recruit('swordsman')
    while state.battle is None and state.status == 'playing':
        state.end_turn()
    assert state.battle_kind == 'defense'
    assert state.battle_province == (-2, 0)
    finish_battle(state)
    assert state.status == 'playing'
    assert state.provinces[(-2, 0)].owner == 'player'
