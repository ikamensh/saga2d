"""A linked campaign is played through the same public shard and transition commands."""
import pytest

from eador.model import HERO_CLASSES, State
from tools.eador_linked_campaign import lose_shard


def test_linked_start_saves_its_contract_while_standalone_stays_standalone():
    """The title can distinguish a real campaign from an unchanged standalone shard."""
    state = State.new_campaign(7, 'Wizard')
    assert state.campaign.stage == 1 and state.campaign.phase == 'playing'
    assert state.campaign.contract == 'westwatch' and state.theme == 'frontier'
    assert state.hero_level_cap == 3 and state.troop_level_cap == 3
    state.explore()
    state.battle.auto_turn()
    assert State.from_json(state.to_json()).to_json() == state.to_json()
    single = State.new(7)
    assert single.campaign is None and single.hero_level_cap is None


def test_a_real_shard_victory_caps_advancement_and_opens_persistent_choices():
    """A finished shard offers two distinct challenges after its last earned choice."""
    from tools.eador_campaign import play_campaign
    state = play_campaign(State.new_campaign(7))
    assert state.status == 'victory'
    assert state.hero.level <= state.hero_level_cap == 3
    assert all(t.level <= 3 for t in state.hero.army)
    assert state.campaign.phase == 'departure'
    assert {offer.contract for offer in state.campaign.offers} == {'rootward', 'foundries'}
    assert {offer.theme for offer in state.campaign.offers} == {'elderwild', 'ruins'}
    assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_departure_carries_choices_and_two_veterans_but_rebuilds_the_local_realm():
    """A transition is atomic, bounded and resumes identically after saving its offer."""
    import pytest
    from copy import deepcopy
    from eador.model import RuleError
    from tools.eador_campaign import play_campaign
    state = play_campaign(State.new_campaign(7))
    old_hero = deepcopy(state.hero)
    selected = tuple(t.id for t in state.hero.army[:2])
    relics = tuple(state.inventory[:2])
    offer = next(offer for offer in state.campaign.offers if offer.contract == 'rootward')
    restored = State.from_json(state.to_json())
    for campaign in (state, restored):
        before = campaign.to_json()
        with pytest.raises(RuleError):
            campaign.advance(offer.id, troop_ids=(selected[0], selected[0]), relic_ids=relics)
        assert campaign.to_json() == before
        campaign.advance(offer.id, troop_ids=selected, relic_ids=relics)
        assert campaign.campaign.stage == 2 and campaign.campaign.phase == 'playing'
        assert campaign.campaign.contract == 'rootward' and campaign.theme == 'elderwild'
        assert campaign.hero.skill_ranks == old_hero.skill_ranks
        assert {t.id for t in campaign.hero.army} & set(selected) == set(selected)
        assert len(campaign.hero.army) == 3 and campaign.hero.pos == (-2, 0)
        assert 100 <= campaign.gold <= 140 and 4 <= campaign.crystals <= 6
        assert not campaign.buildings and campaign.turn == 1
        assert campaign.inventory == list(relics)
        assert campaign.hero.hp == campaign.hero.max_hp and campaign.hero.mana == campaign.hero.max_mana
        assert all(t.hp == t.max_hp for t in campaign.hero.army)
        before = campaign.to_json()
        with pytest.raises(RuleError):
            campaign.advance(offer.id)
        assert campaign.to_json() == before
    assert state.to_json() == restored.to_json()


def test_damaged_linked_metadata_is_rejected_before_it_can_change_the_live_game():
    """Corrupt phases, limits and nested checkpoints fail as save errors, not later crashes."""
    import json
    import pytest
    from eador.model import SaveFormatError
    state = State.new_campaign(7)
    for change in (lambda c: c.update(contract=[]), lambda c: c.update(contract='future'),
                   lambda c: c.update(stage=2), lambda c: c.update(phase='departure'),
                   lambda c: c.update(recovery_used='yes'),
                   lambda c: c['entry'].update(campaign={}),
                   lambda c: c.update(completed=[{}]), lambda c: c.update(offers=[{}])):
        data = json.loads(state.to_json())
        change(data['campaign'])
        with pytest.raises(SaveFormatError):
            State.from_json(json.dumps(data))
    assert state.campaign.phase == 'playing' and state.campaign.stage == 1


def second_shard(contract='rootward', hero_class='Commander', seed=7):
    from tools.eador_campaign import play_campaign
    state = play_campaign(State.new_campaign(seed, hero_class))
    state.advance(contract, troop_ids=tuple(t.id for t in state.hero.army[:2]), relic_ids=tuple(state.inventory[:2]))
    return state


def test_middle_contracts_block_an_early_assault_then_reward_actual_objective_completion():
    """A new stage changes what must be controlled; its gate cannot spend an illegal order."""
    import pytest
    from eador.model import RuleError
    from tools.eador_campaign import finish_battle, march_to, play_campaign, rest
    for contract in ('rootward', 'foundries'):
        state = second_shard(contract)
        with pytest.raises(RuleError, match='Border Watch|foundries'):
            play_campaign(state)
        saved = state.to_json()
        with pytest.raises(RuleError):
            state.travel((2, 0))
        assert state.to_json() == saved
        objectives = ([p.pos for p in state.provinces.values() if p.site_kind == 'border_watch']
                      if contract == 'rootward' else [(0, -1), (0, 1)])
        for pos in objectives:
            march_to(state, pos)
            if contract == 'rootward':
                if not state.actions_left:
                    rest(state, defend=False)
                state.explore()
                finish_battle(state)
        assert state.assault_blocked_reason is None
        march_to(state, (2, 0))
        assert state.status == 'victory' and state.campaign.phase == 'departure'
        assert {offer.contract for offer in state.campaign.offers} == {'throne', 'gate'}
        assert all(offer.theme != state.theme for offer in state.campaign.offers)
        State.from_json(state.to_json())



def test_recovery_keeps_new_knowledge_and_survivors_in_the_exact_world_then_a_second_loss_ends():
    """Recovery is a single expedition, not a reroll or resurrection of fallen troops."""
    import json
    import pytest
    from eador.model import RuleError
    from tools.eador_campaign import play_campaign
    state = second_shard()
    old_ranks = dict(state.hero.skill_ranks)
    with pytest.raises(RuleError, match='Border Watch'):
        play_campaign(state)
    assert state.hero.skill_ranks != old_ranks
    ranks = dict(state.hero.skill_ranks)
    entry = json.loads(state.to_json())['campaign']['entry']
    lose_shard(state)
    assert state.campaign.phase == 'recovery'
    survivors = tuple(t.id for t in state.hero.army[:2])
    state = State.from_json(state.to_json())
    state.recover(troop_ids=survivors, relic_ids=tuple(state.inventory[:2]))
    assert state.campaign.stage == 2 and state.campaign.recovery_used
    assert state.hero.skill_ranks == ranks and state.campaign.phase == 'playing'
    assert set(survivors) <= {t.id for t in state.hero.army}
    assert json.loads(state.to_json())['provinces'] == entry['provinces']
    assert len(state.hero.army) == 3 and state.gold == 60 and not state.buildings
    assert State.from_json(state.to_json()).to_json() == state.to_json()
    lose_shard(state)
    assert state.campaign.phase == 'lost'
    with pytest.raises(RuleError):
        state.recover()
    assert State.from_json(state.to_json()).campaign.phase == 'lost'


def test_a_three_shard_campaign_reaches_both_final_contracts_and_a_saved_ending():
    """Each finale has an explicit contract and completes three distinct recorded themes."""
    from tools.eador_linked_campaign import play_linked
    for middle in ('rootward', 'foundries'):
        for finale in ('throne', 'gate'):
            state = play_linked(7, 'Commander', middle, finale)
            assert state.status == 'victory' and state.campaign.phase == 'completed'
            assert state.campaign.stage == 3 and state.campaign.contract == finale
            assert len(state.campaign.completed) == 3
            assert {record.theme for record in state.campaign.completed} == {'frontier', 'elderwild', 'ruins'}
            assert state.campaign.offers == ()
            assert State.from_json(state.to_json()).to_json() == state.to_json()


def final_battle(finale='gate', hero_class='Commander', seed=7, *, ranged=False):
    """Prepare a final assault by playing two shards and developing the third normally."""
    from tools.eador_campaign import finish_battle, march_to, provision_army, rest
    from tools.eador_linked_campaign import play_stage, travel_selection
    state = State.new_campaign(seed, hero_class)
    for contract in ('rootward', finale):
        state = play_stage(state)
        assert state.status == 'victory'
        state.advance(contract, **travel_selection(state))
    if ranged:
        state.build('archery')
        state.recruit('archer')
        state.recruit('archer')
    else:
        state.build('barracks')
        state.recruit('swordsman')

    def provision():
        if not ranged:
            provision_army(state)
            return
        from eador.model import BUILDINGS
        for kind in ('temple', 'mage_tower'):
            spec = BUILDINGS[kind]
            if kind not in state.buildings and state.gold >= spec.cost and state.crystals >= spec.crystals:
                state.build(kind)
        while len(state.hero.army) < state.hero.max_army and state.gold >= state.recruit_cost('archer'):
            state.recruit('archer')
    for destination in ((-2, 0), (-1, 0), (0, 0), (1, 0)):
        march_to(state, destination)
        if not state.actions_left:
            rest(state)
            march_to(state, destination)
        state.explore()
        finish_battle(state)
        rest(state)
        provision()
    for _ in range(24):
        provision()
        march_to(state, (1, 0))
        if max([state.hero.max_hp - state.hero.hp] + [t.max_hp - t.hp for t in state.hero.army]) > 6:
            rest(state)
            continue
        if not state.actions_left:
            rest(state, defend=False)
            continue
        state.travel((2, 0))
        if state.battle_kind == 'conquest':
            return state
        finish_battle(state)
        rest(state)
    raise AssertionError('The final garrison was never reached.')


def test_final_seal_has_a_distinct_saved_battlefield_and_enforceable_deadline():
    """The ritual contract uses actual hold rules at the capital, with a real failure outcome."""
    from tools.eador_campaign import finish_battle
    state = final_battle()
    battle = state.battle
    assert battle.objective.kind == 'hold' and battle.objective.deadline == 8
    assert battle.objective.target != (0, 0)  # Its layout is separate from the Border Watch.
    assert len([u for u in battle.units if u.team == 'enemy']) == 7
    saved = State.from_json(state.to_json())
    finish_battle(state)
    finish_battle(saved)
    assert state.to_json() == saved.to_json()
    assert state.campaign.phase == 'completed'


def test_manual_final_control_wins_with_surviving_defenders_and_deadline_failure_stays_recoverable():
    """A commanded screen outperforms rout; guarding deployment alone cannot stall the ritual."""
    state = final_battle()
    stalled = State.from_json(state.to_json())
    battle = state.battle
    by_pos = {unit.pos: unit.id for unit in battle.units if unit.team == 'player'}
    placements = (((-2, 0), (-1, 0)), ((-2, -1), (0, -1)), ((-2, 1), (0, 0)),
                  ((-3, 2), (-1, 1)), ((-3, 0), (-1, -1)), ((-3, 1), (-2, 0)), ((-3, 3), (-2, 1)))
    for source, destination in placements:
        battle.move(by_pos[source], destination)
    for turn in range(2):
        for unit in state.battle.units:
            if unit.team == 'player' and unit.alive and not unit.acted:
                state.battle.guard(unit.id)
        state.battle.end_turn()
        state = State.from_json(state.to_json())
    assert state.battle.outcome_reason == 'hold' and state.battle.round == 2
    assert all(unit.alive for unit in state.battle.units)
    state.resolve_battle()
    while state.choice:
        state.choose(state.choice.options[0].id)
    assert state.campaign.phase == 'completed'
    while stalled.battle.outcome is None:
        for unit in stalled.battle.units:
            if unit.team == 'player' and unit.alive and not unit.acted:
                stalled.battle.guard(unit.id)
        stalled.battle.end_turn()
    assert stalled.battle.outcome_reason == 'deadline' and stalled.battle.round == 8
    stalled = State.from_json(stalled.to_json())
    stalled.resolve_battle()
    assert stalled.status == 'playing' and stalled.campaign.phase == 'playing'
    assert stalled.provinces[(2, 0)].owner == 'rival'


@pytest.mark.parametrize('hero_class', ('Warrior', 'Scout', 'Wizard'))
def test_six_body_armies_hold_the_final_seal_with_pin_rotation_and_healing(hero_class):
    """A smaller army can deny the flank with real recruit choices rather than needing Commander capacity."""
    state = final_battle(hero_class=hero_class, ranged=True)
    battle = state.battle
    by_pos = {u.pos: u.id for u in battle.units if u.team == 'player'}
    assert len(by_pos) == 6
    for source, destination in (((-2, 0), (-1, 0)), ((-2, -1), (0, -1)), ((-2, 1), (0, 0)),
                                ((-3, 2), (-1, 1)), ((-3, 0), (-1, -1)), ((-3, 1), (-2, 0))):
        battle.move(by_pos[source], destination)
    for unit in battle.units:
        if unit.team == 'player':
            battle.guard(unit.id)
    battle.end_turn()
    assert battle.objective.progress == 1
    state = State.from_json(state.to_json())
    battle = state.battle
    battle.move(by_pos[(-3, 1)], (-2, 1))
    for archer_start, flank in (((-2, 1), (-2, 2)), ((-3, 2), (-1, 2))):
        defender = next(u for u in battle.units if u.team == 'enemy' and u.pos == flank)
        battle.pin(by_pos[archer_start], defender.id)
    battle.cast('heal', by_pos[(-3, 2)])
    for unit in battle.units:
        if unit.team == 'player' and not unit.acted:
            battle.guard(unit.id)
    battle.end_turn()
    assert battle.outcome_reason == 'hold' and battle.round == 2
    assert all(u.alive for u in battle.units)
    state = State.from_json(state.to_json())
    state.resolve_battle()
    while state.choice:
        state.choose(state.choice.options[0].id)
    assert state.campaign.phase == 'completed'


def test_an_actual_v7_standalone_battle_continues_exactly_after_the_v8_migration():
    """New linked metadata does not opt an older game into a campaign or change Pin combat."""
    import json
    from pathlib import Path
    fixtures = Path(__file__).parent / 'fixtures'
    before = json.loads((fixtures / 'v7_campaign_battle.json').read_text())
    state = State.from_json(json.dumps(before))
    assert state.campaign is None
    assert json.loads(state.to_json())['provinces'] == before['provinces']
    while state.battle.outcome is None:
        state.battle.auto_turn()
    state.resolve_battle()
    while state.choice:
        state.choose(state.choice.options[0].id)
    actual = json.loads(state.to_json())
    actual.pop('campaign')
    assert actual.pop('battle_adventure') is None
    actual['schema_version'] = 7
    assert actual == json.loads((fixtures / 'v7_campaign_battle_result.json').read_text())


@pytest.mark.parametrize('hero_class', HERO_CLASSES)
@pytest.mark.parametrize('contract', ['rootward', 'foundries'])
def test_a_recovery_expedition_can_complete_its_contract_and_the_final_shard(hero_class, contract):
    """The smaller recovery treasury still permits a winning public strategy."""
    from tools.eador_linked_campaign import play_stage, travel_selection
    state = second_shard(contract, hero_class)
    lose_shard(state)
    lost_turns, casualties = state.turn, state.campaign.casualties
    state.recover(**travel_selection(state))
    assert state.campaign.casualties == casualties
    state = play_stage(state)
    assert state.status == 'victory'
    assert state.campaign.completed[-1].turns >= lost_turns + state.turn
    state.advance('gate', **travel_selection(state))
    state = play_stage(state)
    assert state.campaign.phase == 'completed' and state.campaign.recovery_used


@pytest.mark.parametrize('hero_class', HERO_CLASSES)
@pytest.mark.parametrize('middle', ['rootward', 'foundries'])
@pytest.mark.parametrize('finale', ['throne', 'gate'])
def test_each_hero_can_finish_each_linked_contract_path(hero_class, middle, finale):
    """No class or offered path depends on the Commander-only manual seal formation."""
    from tools.eador_linked_campaign import play_linked
    state = play_linked(17, hero_class, middle, finale)
    assert state.campaign.phase == 'completed' and state.status == 'victory'
    assert state.hero.level <= 5 and all(t.level <= 3 for t in state.hero.army)


def test_losing_a_foundry_relocks_the_assault_until_a_real_recapture():
    """The broad-front contract remains contested by the finite rival after the first capture."""
    from tools.eador_campaign import finish_battle, march_to, play_campaign, rest
    from eador.model import RuleError
    state = second_shard('foundries')
    with pytest.raises(RuleError, match='foundries'):
        play_campaign(state)
    for pos in ((0, -1), (0, 1)):
        march_to(state, pos)
    assert state.assault_blocked_reason is None
    march_to(state, (1, 0))
    for _ in range(80):
        if state.assault_blocked_reason:
            break
        state.end_turn()
        if state.battle:
            finish_battle(state)
    assert state.status == 'playing' and state.assault_blocked_reason
    targets = [pos for pos in ((0, -1), (0, 1)) if state.provinces[pos].owner != 'player']
    assert targets
    for pos in targets:
        march_to(state, pos)
    assert state.assault_blocked_reason is None
    assert State.from_json(state.to_json()).to_json() == state.to_json()


@pytest.mark.parametrize('map_name', ['current', 'entry'])
def test_a_required_watch_cannot_be_deleted_from_the_current_or_recovery_world(map_name):
    """A damaged save must not load an adventure whose required seal no longer exists."""
    import json
    from eador.model import SaveFormatError
    state = second_shard('rootward')
    data = json.loads(state.to_json())
    provinces = data['provinces'] if map_name == 'current' else data['campaign']['entry']['provinces']
    watch = next(p for p in provinces if p['site_kind'] == 'border_watch')
    watch.update(site=None, site_kind=None, site_relic=None, site_guards=[], site_guard_hp=[], site_gold=0, site_crystals=0)
    with pytest.raises(SaveFormatError, match='Watch'):
        State.from_json(json.dumps(data))


def test_authored_encounters_can_be_queried_before_spending_a_travel_order():
    """The UI can brief a site or final ritual using the same definition as the coming battle."""
    state = State.new_campaign(7)
    watch = next(p.pos for p in state.provinces.values() if p.site_kind == 'border_watch')
    saved = state.to_json()
    assert state.encounter_at(watch, kind='site') == 'border_watch'
    assert state.encounter_at(watch) is None
    assert state.to_json() == saved
    final = final_battle()
    assert final.encounter_at((2, 0)) == final.battle_encounter == 'last_gate'
    assert final.encounter_at((2, 0), kind='site') is None


@pytest.mark.parametrize('change', [dict(kind='rout', target=None, progress=0, required=0, deadline=None),
                                    dict(deadline=80), dict(required=1), dict(target=[0, 0])])
def test_a_saved_final_ritual_cannot_silently_change_the_offered_contract(change):
    """Current saves keep the exact ritual promised by the selected challenge."""
    import json
    from eador.model import SaveFormatError
    state = final_battle()
    data = json.loads(state.to_json())
    data['battle']['objective'].update(change)
    with pytest.raises(SaveFormatError, match='ritual'):
        State.from_json(json.dumps(data))
