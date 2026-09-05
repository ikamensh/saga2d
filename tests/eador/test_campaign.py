"""A linked campaign is played through the same public shard and transition commands."""
from eador.model import State


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
