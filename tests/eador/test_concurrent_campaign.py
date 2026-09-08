"""Two realms develop independently and settle one authoritative campaign day."""
import json

import pytest

from saga2d import CommandError
from tools.cpu_budget import CpuBudget


def order(match, seat, action, *args, **kwargs):
    """Send the same day/realm revision envelope a network client supplies."""
    message = {'day': match.day, 'realm_revision': match.realms[seat].revision,
               'action': action, 'args': list(args), 'kwargs': kwargs}
    match.apply(seat, message)
    return message


def win_battle(match, seat, budget):
    """Play ordinary optional auto-turn orders; never inject a battle result."""
    for _ in range(80):
        if match.realms[seat].battle.outcome:
            break
        order(match, seat, 'battle.auto_turn')
        budget.checkpoint()
    assert match.realms[seat].battle.outcome == 'player'
    order(match, seat, 'resolve_battle')


def approaching_armies(budget):
    """Earn neighboring approaches with paid troops and ordinary conquest commands."""
    from eador.concurrent_campaign import ConcurrentCampaign

    match = ConcurrentCampaign.new(7, heroes=('Warrior', 'Warrior'))
    for seat, destination in ((0, (-1, 0)), (1, (1, 0))):
        order(match, seat, 'build', 'barracks')
        order(match, seat, 'recruit', 'swordsman')
        order(match, seat, 'travel', list(destination))
        win_battle(match, seat, budget)
    return match


def test_two_realms_develop_independently_then_settle_one_shared_day():
    """Ready grants nothing until both realms finish, and a duplicate cannot settle again."""
    from eador.concurrent_campaign import ConcurrentCampaign

    match = ConcurrentCampaign.new(7, heroes=('Commander', 'Wizard'))
    other = match.snapshot(1)['realm']
    order(match, 0, 'build', 'barracks')
    order(match, 0, 'recruit', 'swordsman')
    assert match.snapshot(1)['realm'] == other
    assert match.realms[0].gold == 10
    assert match.realms[1].gold == 100
    assert match.realms[0].hero.pos != match.realms[1].hero.pos
    assert {p.owner for p in match.provinces.values() if p.capital} == {'realm:0', 'realm:1'}

    before = [(r.gold, r.crystals, r.actions_left) for r in match.realms]
    order(match, 0, 'ready')
    assert match.day == 1
    assert before == [(r.gold, r.crystals, r.actions_left) for r in match.realms]
    with pytest.raises(CommandError, match='ready'):
        order(match, 0, 'build', 'market')
    order(match, 1, 'build', 'temple')
    quote = [match.income(seat) for seat in (0, 1)]
    before = [(r.gold, r.crystals, r.upkeep) for r in match.realms]
    ready = order(match, 1, 'ready')
    assert match.day == 2 and not any(r.ready for r in match.realms)
    assert [(r.gold, r.crystals) for r in match.realms] == [
        (gold + income.gold - upkeep, crystals + income.crystals)
        for (gold, crystals, upkeep), income in zip(before, quote)]
    settled = match.checkpoint()
    with pytest.raises(CommandError, match='day'):
        match.apply(1, ready)
    assert match.checkpoint() == settled

    resumed = ConcurrentCampaign.restore(json.loads(json.dumps(settled)))
    for room in (match, resumed):
        order(room, 0, 'ready')
        order(room, 1, 'ready')
    assert resumed.checkpoint() == match.checkpoint()


def test_two_active_pve_battles_keep_their_own_orders_and_survive_a_checkpoint():
    """Both players fight locally; a peer's turn cannot alter or stale the other battle."""
    from eador.concurrent_campaign import ConcurrentCampaign

    match = ConcurrentCampaign.new(7, heroes=('Warrior', 'Wizard'))
    order(match, 0, 'explore')
    first = match.snapshot(0)['realm']
    order(match, 1, 'explore')
    assert match.snapshot(0)['realm'] == first
    assert match.claims == {realm.capital: realm.seat for realm in match.realms}
    assert all(realm.battle is not None for realm in match.realms)
    pending = {'day': match.day, 'realm_revision': match.realms[1].revision,
               'action': 'battle.guard', 'args': [0], 'kwargs': {}}
    other = match.snapshot(1)['realm']
    order(match, 0, 'battle.guard', 0)
    order(match, 0, 'battle.end_turn')
    assert match.snapshot(1)['realm'] == other and match.day == 1
    match.apply(1, pending)
    assert match.realms[1].battle.unit(0).stance == 'guard'

    saved = match.checkpoint()
    with pytest.raises(CommandError, match='battle'):
        order(match, 0, 'ready')
    enemy = next(unit.id for unit in match.realms[1].battle.units if unit.team == 'enemy')
    with pytest.raises(CommandError):
        order(match, 1, 'battle.guard', enemy)
    assert match.checkpoint() == saved

    resumed = ConcurrentCampaign.restore(json.loads(json.dumps(saved)))
    for room in (match, resumed):
        order(room, 1, 'battle.end_turn')
        order(room, 0, 'retreat')
        assert room.realms[1].battle is not None
        assert room.claims == {room.realms[1].capital: 1}
        order(room, 1, 'retreat')
        assert not room.claims and room.day == 1
        assert not any(province.explored for province in room.provinces.values())
    assert resumed.checkpoint() == match.checkpoint()


def test_contested_arrival_spends_nothing_and_retry_inherits_the_real_guard_wounds():
    """One shared encounter pays once, and pending earned choices hold the day barrier."""
    from eador.concurrent_campaign import ConcurrentCampaign

    budget = CpuBudget(25)
    match = approaching_armies(budget)
    order(match, 0, 'travel', [0, 0])
    claimed = match.checkpoint()
    with pytest.raises(CommandError, match='claimed'):
        order(match, 1, 'travel', [0, 0])
    assert match.checkpoint() == claimed
    order(match, 0, 'battle.auto_turn')
    battle = match.realms[0].battle
    assert battle.outcome is None
    survivors = [(unit.kind, unit.hp) for unit in battle.units if unit.team == 'enemy' and unit.alive]
    original = match.provinces[(0, 0)]
    assert survivors != list(zip(original.guards, original.guard_hp))
    order(match, 0, 'retreat')
    assert not match.claims
    saved = match.checkpoint()
    match = ConcurrentCampaign.restore(saved)
    order(match, 1, 'travel', [0, 0])
    assert [(u.kind, u.hp) for u in match.realms[1].battle.units if u.team == 'enemy'] == survivors
    order(match, 0, 'ready')
    waiting = match.snapshot(0)['realm']
    gold = match.realms[1].gold
    win_battle(match, 1, budget)
    assert match.provinces[(0, 0)].owner == 'realm:1' and not match.claims
    assert match.realms[1].gold == gold + 25
    assert match.realms[1].choice.kind == 'skill'
    assert match.snapshot(0)['realm'] == waiting and match.day == 1
    won = match.checkpoint()
    with pytest.raises(CommandError, match='finished'):
        order(match, 1, 'resolve_battle')
    with pytest.raises(CommandError, match='choice'):
        order(match, 1, 'ready')
    assert match.checkpoint() == won
    resumed = ConcurrentCampaign.restore(won)
    for room in (match, resumed):
        order(room, 1, 'choose', room.realms[1].choice.options[0].id)
        order(room, 1, 'ready')
        assert room.day == 2 and not any(realm.ready for realm in room.realms)
    assert resumed.checkpoint() == match.checkpoint()


@pytest.mark.parametrize('corruption', ['missing', 'orphan', 'wrong_owner', 'ready_battle'])
def test_checkpoint_rejects_encounter_claims_that_cannot_resume(corruption):
    """A saved claim must belong to its active battle; otherwise the map can lock permanently."""
    from eador.concurrent_campaign import ConcurrentCampaign
    from eador.model import SaveFormatError

    match = ConcurrentCampaign.new(7)
    order(match, 0, 'explore')
    saved = match.checkpoint()
    if corruption == 'missing':
        saved['claims'] = []
    elif corruption == 'orphan':
        saved['claims'].append({'pos': [0, 0], 'seat': 1})
    elif corruption == 'wrong_owner':
        saved['claims'][0]['seat'] = 1
    else:
        saved['realms'][0]['ready'] = True
    with pytest.raises(SaveFormatError, match='encounter'):
        ConcurrentCampaign.restore(saved)


def test_waiting_attack_reserves_one_action_without_interrupting_the_incumbent():
    """A paid arrival can be withdrawn, but never cancels PvE or refunds a spent order."""
    from eador.concurrent_campaign import ConcurrentCampaign

    budget = CpuBudget(25)
    match = approaching_armies(budget)
    order(match, 0, 'travel', [0, 0])
    incumbent = match.snapshot(0)['realm']
    available = match.realms[1].actions_left
    order(match, 1, 'challenge', [0, 0])
    assert match.snapshot(0)['realm'] == incumbent
    assert match.realms[1].actions_left == available - 1
    assert match.realms[1].hero.pos == (1, 0) and match.claims == {(0, 0): 0}
    pending = match.snapshot(1)['encounter']
    assert pending['attacker'] == 1 and pending['destination'] == [0, 0] and pending['battle'] is None
    saved = match.checkpoint()
    for action, args in (('ready', ()), ('equip', (None,)), ('travel', ([2, 0],))):
        with pytest.raises(CommandError, match='waiting'):
            order(match, 1, action, *args)
        assert match.checkpoint() == saved
    resumed = ConcurrentCampaign.restore(saved)
    for room in (match, resumed):
        order(room, 1, 'withdraw')
        assert room.snapshot(1)['encounter'] is None
        assert room.realms[1].actions_left == available - 1
        assert room.snapshot(0)['realm'] == incumbent and room.claims == {(0, 0): 0}
    assert resumed.checkpoint() == match.checkpoint()


def test_pve_rewards_and_choices_finish_before_a_saved_shared_human_battle():
    """A seat-1 attacker waits through conquest, then only the acting human can issue orders."""
    from eador.concurrent_campaign import ConcurrentCampaign

    budget = CpuBudget(25)
    match = approaching_armies(budget)
    order(match, 0, 'travel', [0, 0])
    prepared = {'day': match.day, 'realm_revision': match.realms[0].revision,
                'action': 'battle.guard', 'args': [0], 'kwargs': {}}
    order(match, 1, 'challenge', [0, 0])
    match.apply(0, prepared)
    gold = match.realms[0].gold
    win_battle(match, 0, budget)
    assert match.realms[0].gold == gold + 25 and match.realms[0].choice.kind == 'skill'
    assert match.encounter.battle is None and not match.claims
    saved = match.checkpoint()
    match = ConcurrentCampaign.restore(json.loads(json.dumps(saved)))
    assert match.checkpoint() == saved
    order(match, 0, 'choose', match.realms[0].choice.options[0].id)
    battle = match.encounter.battle
    assert battle is not None and battle.active_team == 'player'
    assert battle.unit(battle.enemy_magic.hero_id).hp == match.realms[0].hero.hp
    assert match.claims == {(0, 0): 1}
    assert all(realm.battle is None for realm in match.realms)
    assert match.realms[1].actions_left == 0 and match.realms[1].hero.pos == (1, 0)
    rejected = match.checkpoint()
    for action, args in (('battle.end_turn', ()), ('battle.cast', ('heal', battle.hero_id)),
                         ('retreat', ()), ('equip', (None,)), ('ready', ())):
        with pytest.raises(CommandError):
            order(match, 0, action, *args)
        assert match.checkpoint() == rejected
    with pytest.raises(CommandError):
        order(match, 1, 'battle.guard', battle.enemy_magic.hero_id)
    assert match.checkpoint() == rejected
    old = [realm.revision for realm in match.realms]
    order(match, 1, 'battle.guard', battle.hero_id)
    assert [realm.revision for realm in match.realms] == [value + 1 for value in old]
    order(match, 1, 'battle.end_turn')
    assert match.encounter.battle.active_team == 'enemy'
    saved = match.checkpoint()
    restored = ConcurrentCampaign.restore(json.loads(json.dumps(saved)))
    for room in (match, restored):
        gold = [realm.gold for realm in room.realms]
        order(room, 0, 'battle.guard', room.encounter.battle.enemy_magic.hero_id)
        order(room, 0, 'retreat')
        assert room.encounter is None and not room.claims and room.winner is None
        assert room.provinces[(0, 0)].owner == 'realm:1'
        assert room.realms[1].hero.pos == (0, 0) and room.realms[0].hero.pos == room.realms[0].capital
        assert [realm.gold for realm in room.realms] == [max(0, gold[0] - 20), gold[1]]
        assert all(realm.actions_left == 0 for realm in room.realms)
        after = room.checkpoint()
        with pytest.raises(CommandError):
            order(room, 1, 'resolve_battle')
        assert room.checkpoint() == after
    assert restored.checkpoint() == match.checkpoint()


def test_waiting_arrival_after_conquest_retreat_inherits_actual_neutral_survivors():
    """An incumbent retreat hands over the province encounter, never its invented victory or full-health guards."""
    from eador.concurrent_campaign import ConcurrentCampaign

    budget = CpuBudget(25)
    match = approaching_armies(budget)
    order(match, 0, 'travel', [0, 0])
    order(match, 1, 'challenge', [0, 0])
    order(match, 0, 'battle.auto_turn')
    survivors = [(unit.kind, unit.hp) for unit in match.realms[0].battle.units
                 if unit.team == 'enemy' and unit.alive]
    assert survivors != list(zip(match.provinces[(0, 0)].guards, match.provinces[(0, 0)].guard_hp))
    saved = match.checkpoint()
    restored = ConcurrentCampaign.restore(saved)
    for room in (match, restored):
        gold = room.realms[1].gold
        order(room, 0, 'retreat')
        assert room.encounter is None and room.claims == {(0, 0): 1}
        assert room.realms[1].hero.pos == (1, 0) and room.realms[1].actions_left == 0
        assert room.realms[1].gold == gold and room.provinces[(0, 0)].owner == 'neutral'
        battle = room.realms[1].battle
        assert battle.enemy_magic is None
        assert [(u.kind, u.hp) for u in battle.units if u.team == 'enemy'] == survivors
        order(room, 1, 'retreat')
        assert not room.claims
    assert restored.checkpoint() == match.checkpoint()


def test_ready_reopens_for_defense_and_only_capital_capture_ends_the_shard():
    """Defending grants no extra economy/actions; losing field battles permits retreat, losing the capital ends play."""
    from eador.concurrent_campaign import ConcurrentCampaign

    budget = CpuBudget(25)
    match = approaching_armies(budget)
    order(match, 0, 'travel', [0, 0])
    win_battle(match, 0, budget)
    order(match, 0, 'choose', match.realms[0].choice.options[0].id)
    order(match, 0, 'ready')
    before = match.snapshot(0)['realm']
    order(match, 1, 'travel', [0, 0])
    after = match.snapshot(0)['realm']
    assert before['ready'] and not after['ready'] and match.day == 1
    assert {k: v for k, v in before.items() if k not in ('ready', 'revision', 'log')} == {
        k: v for k, v in after.items() if k not in ('ready', 'revision', 'log')}
    order(match, 1, 'battle.end_turn')
    order(match, 0, 'retreat')
    assert match.winner is None and match.realms[0].hero.pos == (-2, 0)
    while match.realms[1].choice:
        order(match, 1, 'choose', match.realms[1].choice.options[0].id)
    order(match, 0, 'ready')
    order(match, 1, 'ready')
    assert match.day == 2
    order(match, 1, 'travel', [-1, 0])
    order(match, 1, 'travel', [-2, 0])
    order(match, 1, 'battle.end_turn')
    order(match, 0, 'retreat')
    assert match.winner == 1 and [r.status for r in match.realms] == ['defeat', 'victory']
    assert match.provinces[(-2, 0)].owner == 'realm:1' and not match.claims and match.encounter is None
    ended = match.checkpoint()
    assert ConcurrentCampaign.restore(ended).checkpoint() == ended
    for seat in (0, 1):
        with pytest.raises(CommandError, match='ended'):
            order(match, seat, 'ready')
        assert match.checkpoint() == ended


@pytest.mark.parametrize('finished', [False, True])
def test_capital_loss_settles_existing_pve_without_erasing_or_inventing_rewards(finished):
    """Finished adventures pay once; unfinished ones retreat with actual survivors when an empty capital falls."""
    from eador.concurrent_campaign import ConcurrentCampaign
    from eador.content import SITES

    budget = CpuBudget(25)
    match = approaching_armies(budget)
    order(match, 1, 'travel', [0, 0])
    win_battle(match, 1, budget)
    order(match, 1, 'choose', match.realms[1].choice.options[0].id)
    order(match, 0, 'ready')
    order(match, 1, 'ready')
    order(match, 0, 'travel', [-1, -1])
    win_battle(match, 0, budget)
    order(match, 0, 'choose', match.realms[0].choice.options[0].id)
    site = match.provinces[(-1, -1)]
    approaches = SITES[site.site_kind].approaches
    order(match, 0, 'explore', approach=approaches[0].id if approaches else None)
    for _ in range(80 if finished else 1):
        if match.realms[0].battle.outcome:
            break
        order(match, 0, 'battle.auto_turn')
        budget.checkpoint()
    battle = match.realms[0].battle
    assert battle.outcome == ('player' if finished else None)
    guards = [(u.kind, u.hp) for u in battle.units if u.team == 'enemy' and u.alive]
    gold, crystals = match.realms[0].gold, match.realms[0].crystals
    saved = match.checkpoint()
    resumed = ConcurrentCampaign.restore(saved)
    for room in (match, resumed):
        order(room, 1, 'travel', [-1, 0])
        order(room, 1, 'travel', [-2, 0])
        assert room.winner == 1 and room.realms[0].battle is None and not room.claims
        assert room.provinces[site.pos].explored is finished
        assert list(zip(room.provinces[site.pos].site_guards, room.provinces[site.pos].site_guard_hp)) == guards
        assert room.realms[0].gold == (gold + site.site_gold if finished else max(0, gold - 20))
        assert room.realms[0].crystals == crystals + (site.site_crystals if finished else 0)
        if finished:
            assert room.realms[0].choice is not None
            while room.realms[0].choice:
                order(room, 0, 'choose', room.realms[0].choice.options[0].id)
        assert ConcurrentCampaign.restore(room.checkpoint()).checkpoint() == room.checkpoint()
    assert resumed.checkpoint() == match.checkpoint()


def test_waiting_attack_on_departed_army_captures_its_origin_without_chasing_it():
    """A conquest elsewhere moves the incumbent; the challenger enters only its reserved destination."""
    from eador.concurrent_campaign import ConcurrentCampaign

    budget = CpuBudget(25)
    match = approaching_armies(budget)
    order(match, 0, 'travel', [0, 0])
    win_battle(match, 0, budget)
    order(match, 0, 'choose', match.realms[0].choice.options[0].id)
    order(match, 0, 'ready')
    order(match, 1, 'ready')
    order(match, 0, 'travel', [0, -1])
    order(match, 1, 'challenge', [0, 0])
    saved = match.checkpoint()
    resumed = ConcurrentCampaign.restore(saved)
    for room in (match, resumed):
        gold = [realm.gold for realm in room.realms]
        win_battle(room, 0, budget)
        assert room.encounter is None and not room.claims
        assert room.realms[0].hero.pos == (0, -1) and room.realms[1].hero.pos == (0, 0)
        assert room.provinces[(0, -1)].owner == 'realm:0' and room.provinces[(0, 0)].owner == 'realm:1'
        assert [realm.gold for realm in room.realms] == [gold[0] + 25, gold[1]]
        assert all(realm.actions_left == 1 for realm in room.realms)
    assert resumed.checkpoint() == match.checkpoint()


@pytest.mark.parametrize('corruption', ['source', 'source_shape', 'combat_id', 'defending_hero',
                                       'turn', 'outcome', 'ended_active', 'private_human'])
def test_checkpoint_rejects_shared_combat_that_cannot_return_both_real_armies(corruption):
    """A corrupted shared battle must not drop troops or apply one army's wounds to the other."""
    from eador.concurrent_campaign import ConcurrentCampaign
    from eador.entities import SaveFormatError

    budget = CpuBudget(25)
    match = approaching_armies(budget)
    order(match, 0, 'travel', [0, 0])
    win_battle(match, 0, budget)
    order(match, 0, 'choose', match.realms[0].choice.options[0].id)
    order(match, 1, 'travel', [0, 0])
    saved = match.checkpoint()
    battle = saved['encounter']['battle']
    if corruption == 'source':
        battle['units'][-1]['source_id'] = 999
    elif corruption == 'source_shape':
        battle['units'][-1]['source_id'] = []
    elif corruption == 'combat_id':
        battle['units'][-1]['id'] = battle['units'][0]['id']
    elif corruption == 'defending_hero':
        battle['enemy_magic']['hero_id'] = battle['hero_id']
    elif corruption == 'turn':
        battle['active_team'] = 'spectator'
    elif corruption == 'outcome':
        battle['outcome'] = 'victory'
    elif corruption == 'ended_active':
        saved['winner'] = 1
    else:
        saved['encounter'] = None
        realm = saved['realms'][1]
        realm.update(battle=battle, battle_kind='conquest', battle_province=[0, 0])
    with pytest.raises(SaveFormatError, match='encounter'):
        ConcurrentCampaign.restore(saved)


def test_checkpoint_rejects_a_waiting_arrival_redirected_away_from_the_busy_army():
    """A corrupt destination cannot turn a paid wait into entry to an unrelated province."""
    from eador.concurrent_campaign import ConcurrentCampaign
    from eador.entities import SaveFormatError

    budget = CpuBudget(25)
    match = approaching_armies(budget)
    order(match, 0, 'travel', [0, 0])
    order(match, 1, 'challenge', [0, 0])
    saved = match.checkpoint()
    assert ConcurrentCampaign.restore(saved).checkpoint() == saved
    unrelated = (1, -1)
    assert unrelated != match.realms[0].hero.pos and unrelated not in match.claims
    saved['encounter']['destination'] = list(unrelated)
    with pytest.raises(SaveFormatError, match='waiting.*encounter'):
        ConcurrentCampaign.restore(saved)


def test_choice_only_wait_at_a_departed_armys_origin_keeps_its_paid_destination():
    """Finishing a conquest can leave a pending skill choice after the incumbent moves away."""
    from eador.concurrent_campaign import ConcurrentCampaign

    budget = CpuBudget(25)
    match = approaching_armies(budget)
    order(match, 1, 'travel', [0, 0])
    win_battle(match, 1, budget)
    order(match, 1, 'choose', match.realms[1].choice.options[0].id)
    order(match, 0, 'ready')
    order(match, 1, 'ready')
    order(match, 0, 'travel', [-1, -1])
    order(match, 1, 'challenge', [-1, 0])
    win_battle(match, 0, budget)
    assert match.realms[0].hero.pos == (-1, -1)
    assert match.realms[0].battle is None and match.realms[0].choice.kind == 'skill'
    assert match.encounter.destination == (-1, 0) and match.encounter.battle is None
    assert not match.claims
    saved = match.checkpoint()
    resumed = ConcurrentCampaign.restore(saved)
    assert resumed.checkpoint() == saved
    for room in (match, resumed):
        remaining = room.realms[1].actions_left
        order(room, 0, 'choose', room.realms[0].choice.options[0].id)
        assert room.encounter is None and not room.claims
        assert room.realms[0].hero.pos == (-1, -1)
        assert room.realms[1].hero.pos == (-1, 0)
        assert room.provinces[(-1, 0)].owner == 'realm:1'
        assert room.realms[1].actions_left == remaining
    assert resumed.checkpoint() == match.checkpoint()


def test_older_private_campaign_checkpoint_upgrades_without_changing_the_next_day():
    """The earlier development schema has no shared encounter, and must retain its exact next commands."""
    from eador.concurrent_campaign import ConcurrentCampaign
    from eador.entities import SaveFormatError

    match = ConcurrentCampaign.new(7)
    saved = match.checkpoint()
    del saved['encounter']
    saved['schema_version'] = 1
    old = json.loads(json.dumps(saved))
    resumed = ConcurrentCampaign.restore(saved)
    assert saved == old and resumed.checkpoint() == match.checkpoint()
    for room in (match, resumed):
        order(room, 0, 'ready')
        order(room, 1, 'ready')
    assert resumed.checkpoint() == match.checkpoint()
    for extra in ({'encounter': None}, {'schema_version': True}):
        with pytest.raises(SaveFormatError):
            ConcurrentCampaign.restore({**old, **extra})
