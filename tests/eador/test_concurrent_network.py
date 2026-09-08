"""Independent realm commands cross real sockets without a global battle lock."""
import json
import time

import pytest

from saga2d import CommandError, MatchClient, MatchHost
from eador.concurrent_campaign import ConcurrentCampaign
from tools.cpu_budget import CpuBudget


def converge(host, client, until):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        host.poll()
        client.poll()
        assert not client.error, client.error
        if until():
            return
        time.sleep(.005)
    raise AssertionError('Concurrent campaign did not converge.')


def command(view, action, *args, **kwargs):
    return {'day': view['day'], 'realm_revision': view['realm']['revision'],
            'action': action, 'args': list(args), 'kwargs': kwargs}


def connect(match):
    host = MatchHost('concurrent-campaign-dev', match.apply, match.snapshot,
                     address=('127.0.0.1', 0), token='concurrent-test')
    client = MatchClient('concurrent-campaign-dev', host.address, token=host.token)
    return host, client


def test_two_socket_players_resume_active_battles_and_wait_for_both_rewards(tmp_path):
    """Peer activity never stales my order; restarting the authority preserves both encounters."""
    budget = CpuBudget(25)
    match = ConcurrentCampaign.new(7, heroes=('Warrior', 'Warrior'))
    host, client = connect(match)
    try:
        converge(host, client, lambda: client.ready)
        peer_order = command(client.state, 'explore')
        host.submit(command(host.state, 'explore'))
        # This packet predates the host's unrelated world update and remains valid.
        client.submit(peer_order)
        converge(host, client, lambda: client.state['realm']['battle'] is not None)
        assert host.state == match.snapshot(0) and client.state == match.snapshot(1)
        assert set(client.state['opponent']) == {'seat', 'capital', 'hero_pos', 'ready', 'in_battle'}
        assert 'realms' not in client.state
        client.submit(command(client.state, 'battle.guard', 0))
        host.submit(command(host.state, 'battle.guard', 0))
        converge(host, client, lambda: client.state['realm']['revision'] == 2)
        assert all(realm.battle.unit(0).stance == 'guard' for realm in match.realms)
        checkpoint = match.checkpoint()
        path = tmp_path / 'authority.json'
        path.write_text(json.dumps(checkpoint))
    finally:
        client.close()
        host.close()

    resumed = ConcurrentCampaign.restore(json.loads(path.read_text()))
    assert resumed.checkpoint() == checkpoint
    host, client = connect(resumed)
    try:
        converge(host, client, lambda: client.ready)
        assert host.state == resumed.snapshot(0) and client.state == resumed.snapshot(1)
        untouched = client.state['realm']

        def submit(session, action, *args):
            view = session.state
            before = view['realm']['revision']
            session.submit(command(view, action, *args))
            converge(host, client, lambda: session.state['realm']['revision'] > before)
            budget.checkpoint()

        for seat, session in enumerate((host, client)):
            submit(session, 'battle.end_turn')
            for _ in range(80):
                if resumed.realms[seat].battle.outcome:
                    break
                submit(session, 'battle.auto_turn')
            assert resumed.realms[seat].battle.outcome == 'player'
            before_reward = resumed.realms[seat].gold
            site = resumed.provinces[resumed.realms[seat].capital]
            submit(session, 'resolve_battle')
            assert resumed.realms[seat].gold == before_reward + site.site_gold
            assert resumed.provinces[site.pos].explored
            saved = resumed.checkpoint()
            with pytest.raises(CommandError, match='finished'):
                resumed.apply(seat, command(session.state, 'resolve_battle'))
            assert resumed.checkpoint() == saved
            assert resumed.realms[seat].choice is not None
            with pytest.raises(CommandError, match='choice'):
                resumed.apply(seat, command(session.state, 'ready'))
            while resumed.realms[seat].choice:
                submit(session, 'choose', resumed.realms[seat].choice.options[0].id)
            submit(session, 'ready')
            if seat == 0:
                assert client.state['realm'] == untouched and resumed.day == 1
                assert resumed.realms[1].battle is not None
        assert resumed.day == 2 and not resumed.claims
        assert all(realm.inventory and not realm.ready for realm in resumed.realms)
        converge(host, client, lambda: client.state['day'] == 2)
        assert host.state == resumed.snapshot(0) and client.state == resumed.snapshot(1)
    finally:
        client.close()
        host.close()
