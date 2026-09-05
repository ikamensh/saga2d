"""Adventure decisions have persistent, observable consequences."""
import pytest

from eador.model import RuleError, State


def win(state):
    while not state.battle.outcome:
        state.battle.auto_turn()
    assert state.battle.outcome == 'player'
    state.resolve_battle()


def choose_all(state):
    while state.choice:
        state.choose(state.choice.options[0].id)


def test_an_explored_site_offers_a_relic_or_money_and_survives_a_save():
    """The same earned reward cannot be claimed twice or skipped by ending a turn."""
    state = State.new()
    state.explore()
    win(state)
    assert state.choice.kind == 'relic'
    before = state.to_json()
    with pytest.raises(RuleError, match='choice'):
        state.end_turn()
    assert state.to_json() == before
    restored = State.from_json(before)
    restored.choose(restored.choice.options[0].id)
    assert restored.inventory
    restored.equip(restored.inventory[0])
    assert restored.hero.relic == restored.inventory[0]
    assert 'heal' in restored.spells
    with pytest.raises(RuleError):
        restored.choose('take')
    assert State.from_json(restored.to_json()).to_json() == restored.to_json()


def test_wizard_can_master_one_path_instead_of_automatically_learning_both():
    """A saved level decision changes real spell expenditure and keeps a distinct build."""
    from eador.battle import Battle

    state = State.new(hero_class='Wizard')
    for destination in [(-2, 0), (-1, 0)]:
        if destination != state.hero.pos:
            state.travel(destination)
            win(state)
            if state.choice and state.choice.kind == 'skill':
                break
        else:
            state.explore()
            win(state)
            choose_all(state)
    assert state.choice.kind == 'skill'
    alternative = State.from_json(state.to_json())
    state.choose('channeling')
    alternative.choose('restoration')
    battle = Battle.create(state.hero, ['guard'], 'plains', state.spells)
    other = Battle.create(alternative.hero, ['guard'], 'plains', alternative.spells)
    assert battle.spell_cost('bolt') < other.spell_cost('bolt')
    assert other.spell_cost('heal') < battle.spell_cost('heal')
    enemy = next(unit for unit in battle.units if unit.team == 'enemy')
    battle.move(0, min(battle.reachable(0), key=lambda pos: battle.grid.distance(pos, enemy.pos)))
    mana = battle.mana
    battle.cast('bolt', enemy.id)
    assert mana - battle.mana == battle.spell_cost('bolt')
    assert state.hero.skills == {'channeling'}


def test_preversioned_campaign_and_active_battle_migrate_without_new_rewards():
    """Fixtures from the shipped prototype retain their progress and existing site rules."""
    import json
    from pathlib import Path

    for filename in ('v1_campaign.json', 'v1_battle.json'):
        text = (Path(__file__).parent / 'fixtures' / filename).read_text()
        old = json.loads(text)
        restored = State.from_json(text)
        assert restored.gold == old['gold']
        assert restored.hero.hp == old['hero']['hp']
        assert restored.hero.skills == set() and restored.choice is None
        assert restored.provinces[restored.hero.pos].site_gold == 55
        assert restored.provinces[restored.hero.pos].site_relic is None
        assert json.loads(restored.to_json())['schema_version'] == 2
        if restored.battle:
            assert restored.battle.to_dict()['units'][0]['hp'] == old['battle']['units'][0]['hp']
            win(restored)
            assert restored.choice is None
        assert State.from_json(restored.to_json()).to_json() == restored.to_json()


@pytest.mark.parametrize('damage', [
    lambda data: data.update(schema_version=99),
    lambda data: data.update(status=[]),
    lambda data: data.pop('hero'),
    lambda data: data['hero'].update(hero_class='Unknown'),
    lambda data: data['hero'].update(hp=-1),
    lambda data: data['hero'].update(pos=[99, 99]),
    lambda data: data['hero'].update(skill_ranks={'channeling': 1}),
    lambda data: data['hero'].update(relic='moonstone'),
    lambda data: data['hero']['army'][0].update(kind='unknown'),
    lambda data: data['hero']['army'][1].update(id=data['hero']['army'][0]['id']),
    lambda data: data['provinces'][0].update(site_kind='unknown'),
    lambda data: data['provinces'][0].update(guards=['unknown']),
    lambda data: data.update(buildings=['unknown']),
    lambda data: data.update(inventory=['unknown']),
])
def test_invalid_or_newer_saves_raise_a_useful_game_error(damage):
    """Corrupt or incompatible payloads never leak dictionary errors or mutate a live game."""
    import json
    from eador.model import SaveFormatError

    state = State.new()
    before = state.to_json()
    data = json.loads(before)
    damage(data)
    with pytest.raises(SaveFormatError):
        State.from_json(json.dumps(data))
    assert state.to_json() == before
    for malformed in ('{', 'null', '[]'):
        with pytest.raises(SaveFormatError):
            State.from_json(malformed)


@pytest.mark.parametrize('kind', ['shrine', 'tower', 'barrow', 'den', 'caravan', 'grove'])
def test_each_site_pattern_is_reachable_playable_and_awards_its_own_reward(kind):
    """Every authored site is generated and completed using ordinary campaign commands."""
    from eador.content import SITES

    state = next(State.new(seed, 'Wizard') for seed in range(100)
                 if State.new(seed, 'Wizard').provinces[(-2, 1)].site_kind == kind)
    state.build('barracks')
    state.recruit('swordsman')
    state.travel((-2, 1))
    win(state)
    choose_all(state)
    state.end_turn()
    province = state.provinces[state.hero.pos]
    gold, crystals = state.gold, state.crystals
    state.explore()
    assert tuple(unit.kind for unit in state.battle.units if unit.team == 'enemy') == SITES[kind].guards
    reloaded = State.from_json(state.to_json())
    win(reloaded)
    assert reloaded.gold - gold == province.site_gold
    assert reloaded.crystals - crystals == province.site_crystals
    while reloaded.choice and reloaded.choice.kind == 'skill':
        reloaded.choose(reloaded.choice.options[0].id)
    assert reloaded.choice.context == SITES[kind].relic
    reloaded.choose('take')
    reloaded.equip(SITES[kind].relic)
    assert reloaded.hero.relic in reloaded.inventory


def test_rank_mastery_remains_an_option_at_later_levels():
    """Choosing the same path twice produces rank two instead of forcing the other skill."""
    state = State.new(hero_class='Wizard')
    state.build('barracks')
    state.recruit('swordsman')
    for destination in [(-2, 0), (-1, 0), (0, 0)]:
        if destination != state.hero.pos:
            state.travel(destination)
            win(state)
        while state.choice:
            state.choose('channeling' if state.choice.kind == 'skill' else state.choice.options[0].id)
        state.end_turn()
        state.explore()
        win(state)
        while state.choice:
            state.choose('channeling' if state.choice.kind == 'skill' else state.choice.options[0].id)
        state.end_turn()
    assert state.hero.skill_ranks['channeling'] >= 2
    assert 'restoration' not in state.hero.skills
    assert State.from_json(state.to_json()).hero.skill_ranks == state.hero.skill_ranks
