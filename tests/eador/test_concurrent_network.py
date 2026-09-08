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


def test_paid_wait_becomes_a_shared_human_battle_and_resumes_the_defender_over_sockets(tmp_path):
    """Real conquests lead to one paid challenge, a saved human handoff and retreat cleanup."""
    budget = CpuBudget(25)
    match = ConcurrentCampaign.new(7, heroes=('Warrior', 'Warrior'))
    host, client = connect(match)

    def submit(session, action, *args):
        previous = session.state['realm']['revision']
        session.submit(command(session.state, action, *args))
        converge(host, client, lambda: session.state['realm']['revision'] > previous
                 and host.state == match.snapshot(0) and client.state == match.snapshot(1))
        budget.checkpoint()

    def finish_pve(session):
        for _ in range(80):
            if session.state['realm']['battle']['outcome']:
                break
            submit(session, 'battle.auto_turn')
        assert session.state['realm']['battle']['outcome'] == 'player'
        submit(session, 'resolve_battle')

    try:
        converge(host, client, lambda: client.ready)
        for session, destination in ((host, [-1, 0]), (client, [1, 0])):
            submit(session, 'build', 'barracks')
            submit(session, 'recruit', 'swordsman')
            assert session.state['realm']['gold'] == 10
            submit(session, 'travel', destination)
            finish_pve(session)
        submit(host, 'travel', [0, 0])
        incumbent = host.state['realm']
        actions = client.state['realm']['actions_left']
        funds = client.state['realm']['gold']
        submit(client, 'challenge', [0, 0])
        assert host.state['realm'] == incumbent
        assert client.state['realm']['actions_left'] == actions - 1
        assert client.state['realm']['gold'] == funds
        assert client.state['realm']['hero']['pos'] == [1, 0]
        assert host.state['encounter'] == client.state['encounter']
        assert client.state['encounter']['attacker'] == 1
        assert client.state['encounter']['battle'] is None
        assert match.claims == {(0, 0): 0}

        gold = host.state['realm']['gold']
        finish_pve(host)
        assert host.state['realm']['gold'] == gold + 25
        assert host.state['realm']['choices'][0]['kind'] == 'skill'
        assert client.state['encounter']['battle'] is None
        while host.state['realm']['choices']:
            submit(host, 'choose', host.state['realm']['choices'][0]['options'][0]['id'])
        assert host.state['encounter'] == client.state['encounter']
        shared = client.state['encounter']['battle']
        assert shared['active_team'] == 'player'
        assert host.state['realm']['battle'] is None and client.state['realm']['battle'] is None
        assert match.claims == {(0, 0): 1}
        revisions = [session.state['realm']['revision'] for session in (host, client)]
        submit(client, 'battle.guard', shared['hero_id'])
        assert [session.state['realm']['revision'] for session in (host, client)] == [n + 1 for n in revisions]
        submit(client, 'battle.end_turn')
        assert host.state['encounter'] == client.state['encounter']
        assert host.state['encounter']['battle']['active_team'] == 'enemy'
        checkpoint = match.checkpoint()
        path = tmp_path / 'shared-human-authority.json'
        path.write_text(json.dumps(checkpoint))
    finally:
        client.close()
        host.close()

    match = ConcurrentCampaign.restore(json.loads(path.read_text()))
    assert match.checkpoint() == checkpoint
    host, client = connect(match)
    try:
        converge(host, client, lambda: client.ready)
        assert host.state == match.snapshot(0) and client.state == match.snapshot(1)
        shared = host.state['encounter']['battle']
        assert shared == client.state['encounter']['battle'] and shared['active_team'] == 'enemy'
        submit(host, 'battle.guard', shared['enemy_magic']['hero_id'])
        gold = [session.state['realm']['gold'] for session in (host, client)]
        submit(host, 'retreat')
        assert host.state['encounter'] is None and client.state['encounter'] is None
        assert not match.claims and match.winner is None
        assert match.provinces[(0, 0)].owner == 'realm:1'
        assert host.state['realm']['hero']['pos'] == host.state['realm']['capital']
        assert client.state['realm']['hero']['pos'] == [0, 0]
        assert [session.state['realm']['gold'] for session in (host, client)] == [max(0, gold[0] - 20), gold[1]]
        assert all(session.state['realm']['actions_left'] == 0 for session in (host, client))
        assert match.day == 1
        assert host.state == match.snapshot(0) and client.state == match.snapshot(1)
    finally:
        client.close()
        host.close()
