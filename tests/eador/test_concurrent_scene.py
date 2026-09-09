"""Two real socket seats retain their own UI while the shared shard changes."""
import time
from contextlib import contextmanager
import pytest

from eador.app import create_game
from eador.concurrent_campaign import ConcurrentCampaign
from eador.concurrent_scene import ConcurrentShardScene
from saga2d import MatchClient, MatchHost
from saga2d.testing.cpu_budget import CpuBudget
from tools.eador_ui import PlayerInput


@contextmanager
def players(tmp_path, match=None, *, seat=0):
    match = match or ConcurrentCampaign.new(7, heroes=('Warrior', 'Warrior'))
    host = MatchHost('shardbound-pvp-v1', match.apply, match.snapshot,
                     address=('127.0.0.1', 0), token='scene-test')
    client = MatchClient('shardbound-pvp-v1', host.address, token=host.token)
    game = create_game(backend='mock', save_dir=tmp_path / str(seat))
    sessions = (host, client)
    budget = CpuBudget(25)

    def settle(until):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            host.poll()
            client.poll()
            game.tick(1 / 30)
            assert not client.error, client.error
            if until() and all(session.state == match.snapshot(index) for index, session in enumerate(sessions)):
                return
            budget.checkpoint()
            time.sleep(.005)
        raise AssertionError('Player views did not converge.')

    try:
        settle(lambda: client.ready)
        root = ConcurrentShardScene(sessions[seat])
        game.push(root)
        settle(lambda: root in game.scenes)
        yield match, game, root, PlayerInput(game), sessions[1 - seat], settle
    finally:
        game.close()
        client.close()
        host.close()


@pytest.mark.parametrize('seat', (0, 1))
def test_purchase_updates_only_its_realm_and_preserves_peer_help(tmp_path, seat):
    """A public purchase crosses the socket without dismissing the other player's reading."""
    with players(tmp_path, seat=seat) as (match, game, root, inputs, peer, settle):
        inputs.press('b')
        inputs.press('1')
        settle(lambda: bool(root.state.buildings))
        assert root.state.buildings == match.realms[seat].buildings
        assert match.realms[1 - seat].buildings == set()
        assert root.state.provinces[root.state.hero.pos].owner == 'player'
        capital = root.state.provinces[root.state.capital].name.upper()
        assert any(row['text'] == capital + ' / STRONGHOLD' for row in game.backend.texts)
        inputs.press('escape')
        inputs.press('f1')
        help_screen = game.scene
        own_revision = root.state.revision
        peer.submit({'day': peer.state['day'], 'realm_revision': peer.state['realm']['revision'],
                     'action': 'build', 'args': ['barracks'], 'kwargs': {}})
        settle(lambda: bool(match.realms[1 - seat].buildings))
        assert root.state.revision == own_revision
        assert game.scene is help_screen
        inputs.press('escape')
        assert game.scene is root


@pytest.mark.parametrize('seat', (0, 1))
def test_independent_pve_retains_battle_and_help_during_peer_orders(tmp_path, seat):
    """Both realms enter actual sites; a peer guard cannot rebuild the local tactical UI."""
    from eador.scene import BattleScene
    with players(tmp_path, seat=seat) as (match, game, root, inputs, peer, settle):
        inputs.press('x')
        settle(lambda: isinstance(game.scene, BattleScene))
        tactical = game.scene
        own_battle = root.state.battle.to_dict()
        peer.submit({'day': peer.state['day'], 'realm_revision': peer.state['realm']['revision'],
                     'action': 'explore', 'args': [], 'kwargs': {}})
        settle(lambda: root.state.opponent['in_battle'])
        assert game.scene is tactical and root.state.battle.to_dict() == own_battle
        inputs.press('f1')
        help_screen = game.scene
        peer.submit({'day': peer.state['day'], 'realm_revision': peer.state['realm']['revision'],
                     'action': 'battle.guard', 'args': [0], 'kwargs': {}})
        settle(lambda: match.realms[1 - seat].battle.unit(0).stance == 'guard')
        assert game.scene is help_screen
        assert root.state.battle.to_dict() == own_battle


@pytest.mark.parametrize('seat', (0, 1))
def test_ready_waits_for_peer_then_settles_the_day_once(tmp_path, seat):
    """Each player's Ready UI joins the same barrier; a waiting key cannot collect again."""
    with players(tmp_path, seat=seat) as (match, game, root, inputs, peer, settle):
        gold = root.state.gold
        earnings = root.state.production.gold - root.state.upkeep
        inputs.press('e')
        settle(lambda: root.state.ready)
        assert root.state.day == 1 and root.state.gold == gold
        inputs.press('e')
        assert match.day == 1
        peer.submit({'day': peer.state['day'], 'realm_revision': peer.state['realm']['revision'],
                     'action': 'ready', 'args': [], 'kwargs': {}})
        settle(lambda: root.state.day == 2)
        assert not root.state.ready and root.state.gold == gold + earnings
        assert all(realm.actions_left == 2 for realm in match.realms)


def test_paid_map_challenge_can_withdraw_without_rebuilding_the_incumbent(tmp_path):
    """The visible wait action spends exactly one order; withdrawing keeps the incumbent PvE."""
    from tests.eador.test_concurrent_campaign import approaching_armies, order
    match = approaching_armies(CpuBudget(25))
    order(match, 0, 'travel', [0, 0])
    incumbent = match.realms[0].battle.to_dict()
    with players(tmp_path, match, seat=1) as (_, game, root, inputs, peer, settle):
        inputs.click(*root.grid.center((0, 0)))
        actions = root.state.actions_left
        inputs.button('Wait and attack')
        settle(lambda: root.state.waiting)
        assert root.state.actions_left == actions - 1
        assert match.realms[0].battle.to_dict() == incumbent
        inputs.button('Withdraw challenge')
        settle(lambda: not root.state.waiting)
        assert root.state.actions_left == actions - 1
        assert match.realms[0].battle.to_dict() == incumbent


def test_earned_pve_result_and_choices_return_to_the_same_live_realm_once(tmp_path):
    """Joining a won encounter offers its real reward, then removes obsolete overlays together."""
    from tests.eador.test_concurrent_campaign import order
    from eador.concurrent_scene import CampaignOutcome
    from eador.scene import ChoiceScene
    match = ConcurrentCampaign.new(7, heroes=('Warrior', 'Warrior'))
    budget = CpuBudget(25)
    order(match, 0, 'explore')
    for _ in range(80):
        if match.realms[0].battle.outcome:
            break
        order(match, 0, 'battle.auto_turn')
        budget.checkpoint()
    assert match.realms[0].battle.outcome == 'player'
    gold = match.realms[0].gold
    reward = match.provinces[match.realms[0].capital].site_gold
    with players(tmp_path, match) as (_, game, root, inputs, peer, settle):
        assert isinstance(game.scene, CampaignOutcome)
        inputs.press('return')
        settle(lambda: isinstance(game.scene, ChoiceScene))
        assert root.state.gold == gold + reward
        for _ in range(5):
            if root.state.choice is None:
                break
            revision = root.state.revision
            inputs.press('1')
            settle(lambda: root.state.revision > revision)
        assert game.scene is root and game.scenes == [root]
        assert root.state.choice is None and root.state.inventory
        assert root.state.gold == gold + reward
        assert peer.state['realm']['gold'] == 100


def test_live_battle_save_shortcut_describes_room_persistence_without_offline_slots(tmp_path):
    """F6 in a live battle must never offer to serialize its private view as a solo campaign."""
    from eador.diagnostics import DiagnosticScene
    from eador.scene import BattleScene
    with players(tmp_path) as (match, game, root, inputs, peer, settle):
        inputs.press('x')
        settle(lambda: type(game.scene) is BattleScene)
        before = match.checkpoint()
        inputs.press('f6')
        assert isinstance(game.scene, DiagnosticScene) and game.scene.title == 'Live room'
        for key in ('tab', '1', '2'):
            inputs.press(key)
        assert match.checkpoint() == before
        inputs.press('escape')
        assert type(game.scene) is BattleScene


def test_invalid_tactical_click_refuses_without_changing_or_crashing_the_room(tmp_path):
    """Detached animation previews translate expected rule failures like ordinary network orders."""
    from eador.scene import BattleScene
    with players(tmp_path) as (match, game, root, inputs, peer, settle):
        inputs.press('x')
        settle(lambda: type(game.scene) is BattleScene)
        tactical = game.scene
        before = match.checkpoint()
        enemy = next(unit for unit in root.state.battle.units if unit.team == 'enemy')
        inputs.click(*tactical.grid.center(enemy.pos))
        assert game.scene is tactical and tactical.message
        assert match.checkpoint() == before


def test_confirmed_replacement_returns_without_revealing_the_retired_troops_catalog(tmp_path):
    """A paid network replacement removes stale nested quote screens and keeps the live room."""
    with players(tmp_path) as (match, game, root, inputs, peer, settle):
        inputs.press('b')
        inputs.press('1')
        settle(lambda: 'barracks' in root.state.buildings)
        inputs.press('escape')
        inputs.press('r')
        inputs.press('m')
        inputs.press('1')
        for _ in range(game.scene.pages):
            if 'swordsman' in game.scene.visible_items:
                break
            inputs.press('right')
        inputs.press(str(game.scene.visible_items.index('swordsman') + 1))
        quote = root.state.replacement_preview(1, 'swordsman')
        gold, actions = root.state.gold, root.state.actions_left
        inputs.press('return')
        settle(lambda: game.scene is root)
        assert game.scenes == [root] and root.session.ready
        assert root.state.hero.army[0].id == quote.incoming.id
        assert root.state.gold == gold - quote.gold
        assert root.state.actions_left == actions - quote.actions
        assert match.realms[1].hero.army[0].id == 1


def test_accepting_an_earned_pve_loss_opens_the_waiting_human_battle(tmp_path):
    """A result without a reward choice cannot cover the new duel with its obsolete Accept button."""
    from tests.eador.test_concurrent_campaign import approaching_armies, order, win_battle
    from eador.concurrent_scene import CampaignOutcome
    from eador.scene import BattleScene

    budget = CpuBudget(25)
    match = approaching_armies(budget)
    order(match, 0, 'travel', [-2, 0])
    order(match, 1, 'travel', [0, 0])
    win_battle(match, 1, budget)
    while match.realms[1].choice:
        order(match, 1, 'choose', match.realms[1].choice.options[0].id)
    for seat in (0, 1):
        order(match, seat, 'ready')
    order(match, 1, 'travel', [-1, 0])
    order(match, 0, 'explore')
    order(match, 1, 'challenge', [-2, 0])
    for _ in range(80):
        if match.realms[0].battle.outcome:
            break
        order(match, 0, 'battle.end_turn')
        budget.checkpoint()
    assert match.realms[0].battle.outcome == 'enemy'
    assert match.realms[0].choice is None
    with players(tmp_path, match) as (_, game, root, inputs, peer, settle):
        assert isinstance(game.scene, CampaignOutcome)
        inputs.press('return')
        settle(lambda: type(game.scene) is BattleScene)
        assert root.state.battle_kind == 'army' and root.state.battle.outcome is None
        assert game.scene.team == 'enemy' and not game.scene.accepts_orders
        assert game.scenes == [root, game.scene]
