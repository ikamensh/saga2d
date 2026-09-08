"""Real socket orders remain watchable after readers defer campaign reconciliation."""
import pytest

from eador.concurrent_campaign import ConcurrentCampaign
from eador.scene import BattleScene
from tests.eador.test_combat_journal import shared_match
from tests.eador.test_concurrent_scene import players


@pytest.fixture(scope='module')
def earned_duel():
    """One public, paid conquest preparation; each test restores its own authority."""
    return shared_match().checkpoint()


def send(peer, action, *args):
    peer.submit({'day': peer.state['day'], 'realm_revision': peer.state['realm']['revision'],
                 'action': action, 'args': list(args), 'kwargs': {}})


def test_help_retains_peer_orders_then_plays_them_once_before_accepting_input(tmp_path, earned_duel):
    """Coalesced guard/phase updates survive Help and animate from the defender's perspective."""
    from eador.concurrent_playback import RecordedCombatPlayback
    from eador.model import RuleError
    match = ConcurrentCampaign.restore(earned_duel)
    with players(tmp_path, match, seat=0) as (_, game, root, inputs, peer, settle):
        initial = root.state.battle.to_dict()
        inputs.press('f1')
        reader = game.scene
        hero = match.encounter.battle.hero_id
        send(peer, 'battle.guard', hero)
        settle(lambda: match.encounter.battle.unit(hero).stance == 'guard')
        send(peer, 'battle.end_turn')
        settle(lambda: match.encounter.battle.active_team == 'enemy')
        assert game.scene is reader and root.state.battle.to_dict() == initial
        accepted = match.checkpoint()
        inputs.press('escape')
        settle(lambda: isinstance(game.scene, RecordedCombatPlayback))
        playback = game.scene
        assert playback.team == 'enemy' and not playback.accepts_orders
        assert any('Watching resolved actions.' in row['text'] for row in game.backend.texts)
        assert playback.playback.trace.before.active_team == 'player'
        assert playback.playback.trace.after.active_team == 'enemy'
        assert any(event.kind == 'guard' for event in playback.playback.trace.events)
        with pytest.raises(RuleError, match='Wait'):
            root.order('end_turn', target='battle')
        inputs.press('space')
        settle(lambda: type(game.scene) is BattleScene and
               root.state.battle.to_dict() == match.encounter.battle.to_dict())
        assert game.scene.accepts_orders and match.checkpoint() == accepted
        for _ in range(4):
            game.tick(1 / 30)
        assert type(game.scene) is BattleScene and match.checkpoint() == accepted


def test_terminal_peer_history_survives_settlement_and_returns_to_the_earned_choice_once(tmp_path, earned_duel):
    """A defender retreats during Help; playback reads historical facts and then the current reward."""
    from eador.concurrent_playback import RecordedCombatPlayback
    from eador.diagnostics import DiagnosticScene
    from eador.scene import ChoiceScene
    from tests.eador.test_combat_journal import order
    match = ConcurrentCampaign.restore(earned_duel)
    order(match, 1, 'battle.end_turn')
    with players(tmp_path, match, seat=1) as (_, game, root, inputs, peer, settle):
        inputs.press('f1')
        reader = game.scene
        send(peer, 'battle.guard', match.encounter.battle.enemy_magic.hero_id)
        settle(lambda: match.encounter.battle.unit(match.encounter.battle.enemy_magic.hero_id).stance == 'guard')
        send(peer, 'retreat')
        settle(lambda: match.encounter is None)
        assert game.scene is reader and root.state.battle is not None
        accepted = match.checkpoint()
        inputs.press('escape')
        settle(lambda: isinstance(game.scene, RecordedCombatPlayback))
        historical = game.scene
        assert historical.playback.trace.after.outcome == 'player'
        assert historical.team == 'player'
        inputs.button('Battle log')
        assert isinstance(game.scene, DiagnosticScene) and game.scene.title == 'Recorded battle log'
        inputs.press('escape')
        assert game.scene is historical
        inputs.press('f6')
        assert isinstance(game.scene, DiagnosticScene) and game.scene.title == 'Live room'
        inputs.press('escape')
        inputs.press('space')
        settle(lambda: isinstance(game.scene, ChoiceScene))
        assert root.state.battle is None and match.checkpoint() == accepted
        assert not any(isinstance(scene, BattleScene) for scene in game.scenes)
        inputs.press('1')
        settle(lambda: game.scene is root)
        settled = match.checkpoint()
        inputs.press('return')
        assert game.scenes == [root] and match.checkpoint() == settled


def test_new_orders_queue_behind_a_frozen_peer_move(tmp_path, earned_duel):
    """A move already on screen is immutable while the opponent guards and passes their phase."""
    from eador.concurrent_playback import RecordedCombatPlayback
    match = ConcurrentCampaign.restore(earned_duel)
    with players(tmp_path, match, seat=0) as (_, game, root, inputs, peer, settle):
        hero = match.encounter.battle.hero_id
        destination = sorted(match.encounter.battle.reachable(hero))[0]
        send(peer, 'battle.move', hero, list(destination))
        settle(lambda: isinstance(game.scene, RecordedCombatPlayback))
        first = game.scene
        trace = first.playback.trace
        assert trace.events[0].kind == 'move' and trace.after.unit(hero).pos == destination
        send(peer, 'battle.guard', hero)
        settle(lambda: match.encounter.battle.unit(hero).stance == 'guard')
        send(peer, 'battle.end_turn')
        settle(lambda: match.encounter.battle.active_team == 'enemy')
        assert game.scene is first and first.playback.trace == trace
        accepted = match.checkpoint()
        inputs.press('space')
        settle(lambda: isinstance(game.scene, RecordedCombatPlayback) and game.scene is not first)
        assert game.scene.playback.trace.before == trace.after
        inputs.press('space')
        settle(lambda: type(game.scene) is BattleScene and root.state.battle.to_dict() == match.encounter.battle.to_dict())
        assert match.checkpoint() == accepted


def test_inbox_baselines_rejoins_and_explicitly_catches_up_after_gaps_overflow_and_restart(earned_duel):
    """Both transport coalescing and long-open readers use bounded history with a visible catch-up reason."""
    import json
    from eador.concurrent_playback import CombatInbox
    from eador.combat_journal import MAX_RECORDS, MAX_BYTES
    from tests.eador.test_combat_journal import order
    from tools.cpu_budget import CpuBudget
    match, budget = ConcurrentCampaign.restore(earned_duel), CpuBudget(25)
    initial = match.snapshot(0)['presentation']
    reader = CombatInbox(initial)
    for _ in range(MAX_RECORDS + 8):
        seat = 1 if match.encounter.battle.active_team == 'player' else 0
        order(match, seat, 'battle.end_turn')
        reader.observe(match.snapshot(0)['presentation'])
        assert len(reader.records) <= MAX_RECORDS
        assert sum(len(json.dumps(record, sort_keys=True, separators=(',', ':')).encode())
                   for record in reader.records) <= MAX_BYTES
        budget.checkpoint()
    assert 'queue filled' in reader.take_notice()
    current = match.snapshot(0)['presentation']
    assert not CombatInbox(current).pending
    coalesced = CombatInbox(initial)
    coalesced.observe(current)
    assert not coalesced.pending and 'missing older' in coalesced.take_notice()
    restored = ConcurrentCampaign.restore(match.checkpoint())
    reader.observe(restored.snapshot(0)['presentation'])
    assert not reader.pending and 'restarted' in reader.take_notice()


def test_restored_authority_notice_appears_after_help_without_a_new_realm_order(tmp_path, earned_duel):
    """Publishing an identical restored checkpoint changes only the journal epoch, yet still explains catch-up."""
    match = ConcurrentCampaign.restore(earned_duel)
    with players(tmp_path, match, seat=0) as (_, game, root, inputs, peer, settle):
        inputs.press('f1')
        reader = game.scene
        restored = ConcurrentCampaign.restore(match.checkpoint())
        # Replace the authority's public callbacks with its restored model, then
        # publish through the real host. No realm fact or command is injected.
        root.session.apply, root.session.snapshot = restored.apply, restored.snapshot
        root.session.publish()
        for _ in range(3):
            game.tick(1 / 30)
        assert game.scene is reader
        inputs.press('escape')
        for _ in range(3):
            game.tick(1 / 30)
        assert 'room restarted' in game.scene.message
        assert root.state.battle.to_dict() == restored.encounter.battle.to_dict()
        assert match.checkpoint() == restored.checkpoint()
