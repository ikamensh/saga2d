"""A paid role change retires a veteran explicitly without weakening normal recruitment."""
from dataclasses import FrozenInstanceError, asdict
import json
from pathlib import Path

import pytest

from eador.model import RuleError, State, UNITS
from tools.eador_campaign import finish_battle


def earned_army(name='late_full_roster'):
    path = Path(__file__).parents[2] / 'docs/evidence/crystal-service-comparison.examples.json'
    return State.from_json(json.dumps(json.loads(path.read_text())[name]['state']))


def test_full_paid_army_can_quote_and_replace_a_veteran_in_its_saved_formation_slot():
    """Exact prices buy a fresh identity; frozen quotes expose permanent rank/XP loss."""
    state = earned_army()
    before = state.to_json()
    with pytest.raises(RuleError, match='Your army is full'):
        state.recruit('warden')
    quote = state.replacement_preview(1, 'warden')
    assert state.to_json() == before
    assert asdict(quote.outgoing) == asdict(state.hero.army[0])
    assert quote.outgoing.level > 1 and quote.outgoing.xp > 0
    assert quote.incoming.kind == 'warden'
    assert (quote.incoming.id, quote.incoming.level, quote.incoming.xp) == (state.next_troop_id, 1, 0)
    assert quote.incoming.hp == quote.incoming.max_hp == UNITS['warden'].hp
    assert (quote.gold, quote.crystals) == (state.recruit_cost('warden'), state.recruit_crystal_cost('warden'))
    assert quote.actions == 1 and quote.blocked_reason is None
    for record, attribute in ((quote, 'gold'), (quote.outgoing, 'xp'), (quote.incoming, 'hp')):
        with pytest.raises(FrozenInstanceError):
            setattr(record, attribute, 0)
    old_army = [asdict(troop) for troop in state.hero.army]
    old_gold, old_crystals, old_actions, old_upkeep = state.gold, state.crystals, state.actions_left, state.upkeep
    restored = State.from_json(before)
    for current in (state, restored):
        current.replace_troop(1, 'warden')
        assert [asdict(t) for t in current.hero.army] == [asdict(quote.incoming), *old_army[1:]]
        assert (current.gold, current.crystals, current.actions_left) == (
            old_gold - quote.gold, old_crystals - quote.crystals, old_actions - quote.actions)
        assert current.upkeep == quote.upkeep_after and quote.upkeep_before == old_upkeep
        assert current.next_troop_id == quote.incoming.id + 1
    assert state.to_json() == restored.to_json()
    assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_replacement_earns_a_saved_manual_extraction_and_heal_in_the_same_assault():
    """A fresh Warden moves a real wounded veteran into Heal range, without injected battle state."""
    state = earned_army()
    state.build('archery'); state.build('mage_tower')
    quote = state.replacement_preview(1, 'warden')
    frozen_quote = asdict(quote)
    state.replace_troop(1, 'warden')
    state = State.from_json(state.to_json())
    state.travel((2, 0))
    wid = quote.incoming.id
    for _ in range(12):
        battle = state.battle
        wounded = [target for target in battle.swap_targets(wid)
                   if target.hp * 2 < target.max_hp and target not in battle.spell_targets('heal')]
        if wounded:
            break
        assert battle.outcome is None and battle.unit(wid).alive
        battle.auto_turn()
    else:
        raise AssertionError('The paid assault did not expose the wounded flank.')
    target_id = min(wounded, key=lambda troop: (troop.hp, troop.id)).id
    saved = State.from_json(state.to_json())
    for current in (state, saved):
        battle = current.battle
        target, warden = battle.unit(target_id), battle.unit(wid)
        target_pos, warden_pos, hp = target.pos, warden.pos, target.hp
        battle.swap(wid, target_id)
        assert (target.pos, warden.pos) == (warden_pos, target_pos)
        assert warden.acted and warden.moved and target.moved
        assert target in battle.spell_targets('heal')
        gain = battle.spell_preview('heal', target_id)
        battle.cast('heal', target_id)
        assert target.hp == hp + gain and gain > 0
        finish_battle(current)
        assert current.status == 'victory'
        assert any(t.id == target_id for t in current.hero.army)
    assert state.to_json() == saved.to_json()
    assert asdict(quote) == frozen_quote


def assert_refused(state, kind, reason, *, outgoing_id=None):
    outgoing_id = state.hero.army[0].id if outgoing_id is None else outgoing_id
    before = state.to_json()
    quote = state.replacement_preview(outgoing_id, kind)
    assert reason in quote.blocked_reason
    assert state.to_json() == before
    with pytest.raises(RuleError, match=reason):
        state.replace_troop(outgoing_id, kind)
    assert state.to_json() == before


def test_missing_prerequisite_and_both_currencies_refuse_the_entire_replacement():
    state = State.new()
    assert_refused(state, 'warden', 'Build Barracks')
    state.build('mage_tower')
    quote = state.replacement_preview(1, 'adept')
    assert state.gold < quote.gold and state.crystals >= quote.crystals
    assert_refused(state, 'adept', 'Not enough gold or crystals')
    state = State.new(7, 'Scout')
    state.build('mage_tower'); state.explore(); finish_battle(state)
    state.infuse()
    quote = state.replacement_preview(1, 'adept')
    assert state.gold >= quote.gold and state.crystals < quote.crystals and state.actions_left
    assert_refused(state, 'adept', 'Not enough gold or crystals')


@pytest.mark.parametrize('outgoing_id,kind', [(0, 'militia'), (9999, 'militia'), (1, 'guard'), (1, 'unknown')])
def test_invalid_selection_refuses_both_quote_and_command_without_charging(outgoing_id, kind):
    state = State.new()
    before = state.to_json()
    for command in (state.replacement_preview, state.replace_troop):
        with pytest.raises(RuleError):
            command(outgoing_id, kind)
        assert state.to_json() == before


def test_repeated_same_role_orders_lose_identity_and_actions_without_refund():
    state = State.new()
    gold, crystals, outgoing = state.gold, state.crystals, state.hero.army[0].id
    retired, total = [], 0
    for _ in range(state.actions_left):
        quote = state.replacement_preview(outgoing, 'militia')
        state.replace_troop(outgoing, 'militia')
        retired.append(outgoing)
        outgoing = quote.incoming.id
        total += quote.gold
        assert state.hero.army[0].id == outgoing
        assert not set(retired).intersection(t.id for t in state.hero.army)
    assert state.gold == gold - total and state.crystals == crystals
    assert_refused(state, 'militia', 'No campaign actions remain')
    before = state.to_json()
    with pytest.raises(RuleError, match='living troop'):
        state.replace_troop(retired[0], 'militia')
    assert state.to_json() == before
    # Ordinary recruitment retains its zero-action behavior when a slot exists.
    old_len, gold, price = len(state.hero.army), state.gold, state.recruit_cost('militia')
    state.recruit('militia')
    assert state.actions_left == 0 and state.gold == gold - price
    assert len(state.hero.army) == old_len + 1


def test_a_new_order_rechecks_readiness_and_allocates_a_fresh_id_after_an_old_quote():
    state = State.new()
    quote = state.replacement_preview(1, 'militia')
    state.recruit('militia')
    new_quote = state.replacement_preview(1, 'militia')
    assert new_quote.incoming.id > quote.incoming.id
    state.replace_troop(1, 'militia')
    assert asdict(state.hero.army[0]) == asdict(new_quote.incoming)
    state.explore()
    assert_refused(state, 'militia', 'Finish or retreat')
    while state.battle.outcome is None:
        state.battle.auto_turn()
    state.resolve_battle()
    assert state.choice is not None
    assert_refused(state, 'militia', 'pending choice')
    while state.choice:
        state.choose(state.choice.options[0].id)
    # A formerly affordable quote is not a promise to sell after other purchases.
    poor = State.new(); poor.build('barracks')
    assert poor.replacement_preview(1, 'warden').blocked_reason is None
    poor.recruit('militia')
    assert_refused(poor, 'warden', 'Not enough gold or crystals')


def test_replacement_spends_the_last_interception_action_and_keeps_the_rival_consequence():
    immediate = earned_army('pursuit_last_action')
    delayed = State.from_json(immediate.to_json())
    immediate.travel(immediate.rival.pos)
    quote = delayed.replacement_preview(1, 'warden')
    delayed.replace_troop(1, 'warden')
    assert delayed.actions_left == 0
    delayed = State.from_json(delayed.to_json())
    delayed.end_turn()
    assert delayed.provinces[(0, 0)].owner == 'rival'
    delayed.travel(delayed.rival.pos)
    for state in (immediate, delayed):
        finish_battle(state)
        assert state.provinces[(0, 0)].owner == 'player' and state.rival.defeats > 0
    assert delayed.turn == immediate.turn + 1
    assert delayed.gold < immediate.gold + immediate.income
    assert any(t.id == quote.incoming.id for t in delayed.hero.army)
    assert all(t.id != quote.outgoing.id for t in delayed.hero.army)


def test_normal_recruitment_refusal_order_and_blockade_eligibility_remain_unchanged():
    """A valid full/poor snapshot makes each pre-existing refusal observable."""
    data = json.loads(earned_army().to_json())
    data['gold'] = 0
    state = State.from_json(json.dumps(data))
    before = state.to_json()
    for kind, reason in [('guard', 'cannot be recruited'), ('adept', 'Build Mage Tower'),
                         ('warden', 'Your army is full')]:
        with pytest.raises(RuleError, match=reason):
            state.recruit(kind)
        assert state.to_json() == before
    data = json.loads(State.new().to_json())
    neighbors = State.new().grid.neighbors((-2, 0))
    for province in data['provinces']:
        if tuple(province['pos']) in neighbors:
            province['owner'] = 'rival'
    state = State.from_json(json.dumps(data))
    assert state.encircled
    state.recruit('militia')
    assert state.replacement_preview(1, 'militia').blocked_reason is None
    state.replace_troop(1, 'militia')
    assert state.encircled


def test_real_old_camp_save_can_replace_without_regenerating_its_world_or_bumping_schema():
    cases = json.loads((Path(__file__).parent / 'fixtures/v11_difficulty_cases.json').read_text())
    original = next(case['before'] for case in cases if case['name'] == 'rival_order')
    state = State.from_json(json.dumps(original))
    migrated = json.loads(state.to_json())
    assert {k: v for k, v in migrated.items() if k not in ('schema_version', 'rules_id')} == {
        k: v for k, v in original.items() if k != 'schema_version'}
    state.replace_troop(state.hero.army[0].id, 'militia')
    replaced = json.loads(state.to_json())
    assert replaced['schema_version'] == migrated['schema_version']
    assert replaced['provinces'] == original['provinces']
    assert replaced['rival'] == original['rival']
    assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_a_completed_shard_cannot_pay_for_retirement():
    state = earned_army()
    state.travel((2, 0)); finish_battle(state)
    assert state.status == 'victory'
    assert_refused(state, 'militia', 'campaign has ended')
