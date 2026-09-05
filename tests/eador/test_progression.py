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
    from eador.battle import Battle
    control = State.from_json(reloaded.to_json())
    control.equip(None)
    if kind == 'caravan':
        assert reloaded.recruit_cost('swordsman') < control.recruit_cost('swordsman')
    elif kind == 'grove':
        reloaded.end_turn()
        control.end_turn()
        assert sum(t.hp for t in reloaded.hero.army) > sum(t.hp for t in control.hero.army)
    else:
        powered = Battle.create(reloaded.hero, ['guard'], 'forest', reloaded.spells, seed=4)
        ordinary = Battle.create(control.hero, ['guard'], 'forest', control.spells, seed=4)
        if kind in ('shrine', 'tower'):
            spell = 'heal' if kind == 'shrine' else 'bolt'
            assert powered.spell_power[spell] > ordinary.spell_power[spell]
        elif kind == 'den':
            assert ordinary.reachable(0) < powered.reachable(0)
        else:
            for battle in (powered, ordinary):
                for _ in range(2):
                    battle.end_turn()
                enemy = next(unit for unit in battle.units if unit.team == 'enemy')
                battle.move(0, min(battle.reachable(0), key=lambda pos: battle.grid.distance(pos, enemy.pos)))
            enemy_id = next(unit.id for unit in ordinary.units if unit.team == 'enemy')
            assert ordinary.preview(0, enemy_id)[1] > 0
            assert powered.preview(0, enemy_id)[1] == 0


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


def advancement(hero_class):
    """Earn an ordinary second-level choice through two easy encounters."""
    state = State.new(hero_class=hero_class)
    state.build('barracks')
    state.recruit('swordsman')
    state.explore()
    win(state)
    choose_all(state)
    state.end_turn()
    state.travel((-1, 0))
    win(state)
    assert state.choice and state.choice.kind == 'skill'
    return state


def test_commanders_choose_between_affordable_reinforcements_and_safe_attacks():
    """A development choice changes either the economy or a real damage preview."""
    from eador.battle import Battle

    state = advancement('Commander')
    tactician = State.from_json(state.to_json())
    state.choose('quartermaster')
    tactician.choose('tactician')
    assert state.recruit_cost('swordsman') < tactician.recruit_cost('swordsman')
    ordinary = Battle.create(state.hero, ['guard'], 'plains', state.spells)
    trained = Battle.create(tactician.hero, ['guard'], 'plains', tactician.spells)
    for battle in (ordinary, trained):
        battle.end_turn()
        troop = next(unit for unit in battle.units if unit.team == 'player' and unit.kind == 'swordsman')
        enemy = next(unit for unit in battle.units if unit.team == 'enemy')
        destination = min(battle.reachable(troop.id), key=lambda pos: battle.grid.distance(pos, enemy.pos))
        battle.move(troop.id, destination)
    attacker = next(unit.id for unit in ordinary.units if unit.kind == 'swordsman')
    enemy = next(unit.id for unit in ordinary.units if unit.team == 'enemy')
    assert ordinary.preview(attacker, enemy)[1] > 0
    assert trained.preview(attacker, enemy)[1] == 0
    trained.attack(attacker, enemy)
    assert trained.unit(attacker).safe_attacks == 0


def test_scout_paths_change_terrain_routes_or_allow_a_fighting_withdrawal():
    """Skirmishers attack and then move; Pathfinders move the whole army through woods."""
    from eador.battle import Battle

    state = advancement('Scout')
    skirmisher = State.from_json(state.to_json())
    state.choose('pathfinder')
    skirmisher.choose('skirmisher')
    woods = Battle.create(state.hero, ['guard'], 'forest', state.spells, seed=4)
    skirmish = Battle.create(skirmisher.hero, ['guard'], 'forest', skirmisher.spells, seed=4)
    militia = next(unit.id for unit in woods.units if unit.kind == 'militia')
    assert skirmish.reachable(militia) < woods.reachable(militia)
    for battle in (woods, skirmish):
        for _ in range(10):
            if battle.targets(0):
                break
            battle.end_turn()
        target = battle.targets(0)[0]
        battle.attack(0, target.id)
    assert not woods.reachable(0)
    assert skirmish.reachable(0)
    skirmish.move(0, min(skirmish.reachable(0)))
    assert not skirmish.reachable(0)


def test_warriors_choose_safe_duels_or_faster_recovery():
    """Vigor improves recovery from actual wounds; Duelist prevents a real counterstrike."""
    from eador.battle import Battle

    state = advancement('Warrior')
    vigorous = State.from_json(state.to_json())
    state.choose('duelist')
    vigorous.choose('vigor')
    for campaign in (state, vigorous):
        campaign.end_turn()
        campaign.explore()
        battle = campaign.battle
        enemy = next(unit for unit in battle.units if unit.team == 'enemy')
        battle.move(0, min(battle.reachable(0), key=lambda pos: battle.grid.distance(pos, enemy.pos)))
        while battle.unit(0).hp > battle.unit(0).max_hp - 14 and not battle.outcome:
            battle.end_turn()
        assert battle.unit(0).hp > 0
        campaign.retreat()
    assert state.hero.hp == vigorous.hero.hp
    state.end_turn()
    vigorous.end_turn()
    assert vigorous.hero.hp > state.hero.hp
    ordinary = Battle.create(vigorous.hero, ['guard'], 'plains', vigorous.spells)
    duel = Battle.create(state.hero, ['guard'], 'plains', state.spells)
    for battle in (ordinary, duel):
        battle.end_turn()
        enemy = next(unit for unit in battle.units if unit.team == 'enemy')
        battle.move(0, min(battle.reachable(0), key=lambda pos: battle.grid.distance(pos, enemy.pos)))
    enemy_id = next(unit.id for unit in ordinary.units if unit.team == 'enemy')
    assert ordinary.preview(0, enemy_id)[1] > 0
    assert duel.preview(0, enemy_id)[1] == 0


def test_pending_choices_and_active_battles_validate_their_campaign_context():
    """A save cannot award unearned ranks or swap identities inside a running battle."""
    import json
    from eador.model import SaveFormatError

    pending = advancement('Commander')
    data = json.loads(pending.to_json())
    data['choices'].append(data['choices'][0])
    with pytest.raises(SaveFormatError, match='earned'):
        State.from_json(json.dumps(data))
    pending.choose('tactician')
    pending.end_turn()
    pending.explore()
    for mutation in (
        lambda data: data['battle']['units'][1].update(kind='guard'),
        lambda data: data['battle']['units'][1].update(pos=data['battle']['units'][0]['pos']),
        lambda data: data['battle']['units'][0].update(max_hp=999),
        lambda data: data['battle']['spell_costs'].update(bolt=0),
    ):
        data = json.loads(pending.to_json())
        mutation(data)
        with pytest.raises(SaveFormatError):
            State.from_json(json.dumps(data))


def test_new_shards_reject_invalid_seeds_instead_of_creating_unloadable_saves():
    """Every accepted seed produces a save that the game can read back."""
    with pytest.raises(RuleError, match='integer'):
        State.new(seed=7.5)
    state = State.new(seed=-(2**80))
    assert State.from_json(state.to_json()).to_json() == state.to_json()
