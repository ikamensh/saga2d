"""Presentation observes resolved rules without becoming part of campaign state."""
from dataclasses import FrozenInstanceError

import pytest

from eador.battle import Battle
from eador.model import RuleError, State
from tools.eador_extraction_campaign import AdventureOrders
from tools.eador_relief_campaign import prepare_relief


def relief_before_rally():
    """Earn the actual party and leave two HP of enemy support before ending the phase."""
    state = prepare_relief()
    state.explore(approach='forward')
    play = AdventureOrders(state)
    for ident, pos in ((1, (3, -2)), (0, (0, -1)), (3, (1, -1)), (4, (0, -2)),
                       (6, (1, 0)), (2, (-1, -2))):
        play.do('move', ident, pos)
    play.do('pin', 3, play.enemy('skyrider'))
    play.do('cast', 'bolt', play.enemy('militia'))
    play.do('attack', 1, play.enemy('militia'))
    play.guard_remaining()
    return state


def test_trace_keeps_rally_flight_brace_and_hits_ordered_without_changing_saved_rules():
    """Visual snapshots explain the enemy chain; the complete campaign and next phase stay exact."""
    state = relief_before_rally()
    plain = State.from_json(state.to_json())
    trace = state.battle.trace(state.battle.end_turn)
    plain.battle.end_turn()
    assert state.to_json() == plain.to_json()
    kinds = [event.kind for event in trace.events]
    rally = next(event for event in trace.events if event.kind == 'rally')
    flyer = state.battle.unit(rally.target_id)
    flight = next(event for event in trace.events if event.kind == 'move' and event.actor_id == flyer.id)
    brace = next(event for event in trace.events if event.kind == 'brace')
    hit = next(event for event in trace.events if event.kind == 'attack' and event.actor_id == flyer.id)
    assert kinds.index('rally') < trace.events.index(flight) < kinds.index('brace') < trace.events.index(hit)
    assert rally.before.unit(flyer.id).pinned and not rally.after.unit(flyer.id).pinned
    assert flight.path[0] == flight.before.unit(flyer.id).pos
    assert flight.path[-1] == flight.after.unit(flyer.id).pos == (1, -2)
    assert brace.after.unit(flyer.id).hp < brace.before.unit(flyer.id).hp
    assert hit.after.unit(hit.target_id).hp < hit.before.unit(hit.target_id).hp
    assert trace.after.unit(flyer.id).hp == flyer.hp
    state.battle.end_turn(); plain.battle.end_turn()
    assert state.to_json() == plain.to_json()
    with pytest.raises(FrozenInstanceError):
        trace.before.unit(0).hp = 0


def test_trace_releases_observation_after_rejection_and_unexpected_exceptions():
    """Errors keep their identity; a later observation has no stale events or save fields."""
    state = State.new()
    state.explore()
    battle = state.battle
    before = state.to_json()
    with pytest.raises(RuleError):
        battle.trace(lambda: battle.move(0, (99, 99)))
    assert state.to_json() == before
    error = RuntimeError('observer command failed')
    def fail():
        raise error
    with pytest.raises(RuntimeError) as caught:
        battle.trace(fail)
    assert caught.value is error and state.to_json() == before
    plain = Battle.from_dict(battle.to_dict())
    trace = battle.trace(battle.end_turn)
    plain.end_turn()
    assert battle.to_dict() == plain.to_dict()
    assert trace.events and all(event.before != event.after for event in trace.events)


def test_a_lethal_brace_has_no_fictitious_attack_and_keeps_the_same_terminal_result():
    """The presentation must show the pre-hit kill rather than inventing a zero-damage strike."""
    from tests.eador.test_guard import encounter
    battle = encounter('pikeman', enemy_hp=5)
    battle.guard(0)
    plain = Battle.from_dict(battle.to_dict())
    trace = battle.trace(battle.end_turn)
    plain.end_turn()
    assert battle.to_dict() == plain.to_dict()
    assert [event.kind for event in trace.events] == ['brace', 'result']
    assert trace.events[0].after.unit(1000).hp == 0
    assert trace.after.outcome == 'player'


@pytest.mark.parametrize('fixture', ['v4_brace_battle', 'v6_archer_battle', 'v10_pinned_crossing',
                                     'v11_crossing_relic_battle', 'v12_pre_relief_grove_battle'])
def test_real_old_battles_have_the_same_complete_saved_continuation_when_observed(fixture):
    """Old capabilities, status expiry and terminal rounds remain identical through observation."""
    from pathlib import Path
    state = State.from_json((Path(__file__).parent / 'fixtures' / f'{fixture}.json').read_text())
    plain = State.from_json(state.to_json())
    while not state.battle.outcome:
        trace = state.battle.trace(state.battle.auto_turn)
        plain.battle.auto_turn()
        assert state.to_json() == plain.to_json()
        if state.battle.objective.kind == 'rout':
            assert all('escape clock' not in event.text.lower() for event in trace.events)
        frame = trace.before
        for event in trace.events:
            assert event.before == frame
            frame = event.after
        assert frame == trace.after
    state.resolve_battle(); plain.resolve_battle()
    assert state.to_json() == plain.to_json()


def test_enemy_pin_expiry_in_a_rout_is_not_described_as_an_escape_clock():
    """A changed status may need a final frame even when there is no special objective."""
    battle = Battle.clash([('archer', 20)], [('guard', 42)], 'plains')
    battle.move(0, (0, 0)); battle.pin(0, 1000)
    trace = battle.trace(battle.end_turn)
    assert not trace.after.unit(1000).pinned
    assert all('escape clock' not in event.text.lower() for event in trace.events)
