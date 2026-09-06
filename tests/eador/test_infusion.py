"""Optional paid preparation competes with movement and preserves ordinary rest."""
import json
from pathlib import Path

import pytest

from eador.model import RuleError, State
from tools.eador_campaign import CampaignMetrics, finish_battle


def paid_caster(hero='Wizard'):
    state = State.new(7, hero)
    state.build('mage_tower')
    state.explore()
    finish_battle(state)
    return state


def test_paid_infusion_matches_its_live_quote_and_preserves_saved_continuation():
    """A purchased Tower and won Shrine supply a real caster's missing mana and fee."""
    state = paid_caster()
    before = state.to_json()
    quote = state.infusion_preview()
    assert state.to_json() == before
    assert (quote.crystals, quote.actions, quote.mana, quote.blocked_reason) == (3, 1, 4, None)
    restored = State.from_json(before)
    old_gold, old_crystals, old_actions, old_mana = state.gold, state.crystals, state.actions_left, state.hero.mana
    for current in (state, restored):
        current.infuse()
        assert current.gold == old_gold and current.turn == 1
        assert current.crystals == old_crystals - quote.crystals
        assert current.actions_left == old_actions - quote.actions
        assert current.hero.mana == old_mana + quote.mana
    assert state.to_json() == restored.to_json()
    state.end_turn(); restored.end_turn()
    assert state.to_json() == restored.to_json()


def assert_refused(state, message):
    before = state.to_json()
    quote = state.infusion_preview()
    assert message in quote.blocked_reason
    assert state.to_json() == before
    with pytest.raises(RuleError, match=message):
        state.infuse()
    assert state.to_json() == before


def test_infusion_requires_a_tower_and_refuses_full_mana_without_charging():
    state = State.new(7, 'Wizard')
    assert_refused(state, 'Build a Mage Tower')
    state.build('mage_tower')
    assert_refused(state, 'Mana is already full')


def test_bought_recruit_and_last_action_are_real_opportunity_costs():
    state = paid_caster()
    state.recruit('adept')
    assert_refused(state, 'requires 3 crystals')
    state = paid_caster()
    state.infuse()
    assert_refused(state, 'No campaign actions remain')
    before = state.to_json()
    with pytest.raises(RuleError, match='No campaign actions remain'):
        state.travel((-1, 0))
    assert state.to_json() == before


def test_scout_can_use_her_extra_action_for_infusion_and_a_saved_onward_attack():
    state = paid_caster('Scout')
    hp = (state.hero.hp, [u.hp for u in state.hero.army])
    state.infuse()
    assert (state.hero.hp, [u.hp for u in state.hero.army]) == hp
    restored = State.from_json(state.to_json())
    for current in (state, restored):
        current.travel((-1, 0))
        assert current.battle_kind == 'conquest'
        finish_battle(current)
    assert state.to_json() == restored.to_json()
    assert state.hero.pos == (-1, 0)


def test_battle_and_pending_reward_must_finish_before_infusion():
    state = State.new(7, 'Wizard')
    state.build('mage_tower'); state.explore()
    assert_refused(state, 'Finish or retreat')
    while not state.battle.outcome:
        state.battle.auto_turn()
    state.resolve_battle()
    assert state.choice is not None
    assert_refused(state, 'pending choice')


def test_a_valid_encircled_capital_blocks_infusion_as_well_as_passive_recovery():
    state = paid_caster()
    # A controlled valid ownership fixture isolates this rule; the pressure suite
    # separately earns encirclement and breakouts through complete public campaigns.
    data = json.loads(state.to_json())
    neighbors = state.grid.neighbors(state.hero.pos)
    for province in data['provinces']:
        if tuple(province['pos']) in neighbors:
            province['owner'] = 'rival'
    state = State.from_json(json.dumps(data))
    assert state.encircled and state.recovery_preview().mana == 0
    assert_refused(state, 'Encirclement blocks infusion')


def earned_example(name):
    path = Path(__file__).parents[2] / 'docs/evidence/crystal-service-comparison.examples.json'
    return State.from_json(json.dumps(json.loads(path.read_text())[name]['state']))


def test_earned_pre_assault_infusion_offers_earlier_attack_with_intermediate_attrition():
    """The retained paid Spells route can spend crystals/action, accept losses now, or wait."""
    runs = {}
    for plan in ('immediate', 'infuse', 'rest'):
        state = earned_example('pre_assault_mana')
        if plan == 'infuse':
            quote = state.infusion_preview()
            assert quote.mana == 8 and quote.blocked_reason is None
            state.infuse()
            state = State.from_json(state.to_json())
        elif plan == 'rest':
            while state.hero.mana < state.hero.max_mana - 4:
                state.end_turn()
        state.travel((2, 0))
        metrics = CampaignMetrics()
        finish_battle(state, metrics)
        assert state.status == 'victory'
        runs[plan] = (state.turn, metrics.lost_troops)
    assert runs['immediate'][0] == runs['infuse'][0] < runs['rest'][0]
    assert runs['rest'][1] < runs['infuse'][1] < runs['immediate'][1]
    assert_refused(state, 'campaign has ended')


def test_infusing_before_a_live_interception_spends_the_last_action_and_yields_territory():
    """A useful Tower purchase and a subsequent infusion are different timing decisions."""
    immediate = earned_example('pursuit_last_action')
    immediate.build('mage_tower')
    delayed = State.from_json(immediate.to_json())
    immediate.travel(immediate.rival.pos)
    assert immediate.battle_kind == 'intercept' and immediate.provinces[(0, 0)].owner == 'player'
    delayed.infuse()
    assert delayed.actions_left == 0
    delayed = State.from_json(delayed.to_json())
    delayed.end_turn()
    assert delayed.provinces[(0, 0)].owner == 'rival'
    delayed.travel(delayed.rival.pos)
    for current in (immediate, delayed):
        finish_battle(current)
        assert current.provinces[(0, 0)].owner == 'player'
        assert current.rival.defeats > 0
    assert delayed.turn == immediate.turn + 1
