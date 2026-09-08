"""Directed campaign conflict input: paid waiting, ordinary human turns and return to the map.

The earned opening uses disclosed public PvE autoplay. Seat 1 then uses shipped
controls against a real socket host; this is not independent human play.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d import Button, Label, MatchClient, MatchHost
from eador.app import create_game
from eador.concurrent_campaign import ConcurrentCampaign
from eador.concurrent_scene import ConcurrentShardScene
from eador.concurrent_playback import RecordedCombatPlayback
from eador.preferences import reading_scale
from eador.scene import BattleScene, ChoiceScene
from tools.cpu_budget import CpuBudget
from tools.verify_eador_shard_look import PacedInput


def verify(output, *, backend='pyglet'):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    budget = CpuBudget(25)
    started, cpu_started = time.monotonic(), time.process_time()
    paths = sorted((ROOT / 'eador').glob('*.py')) + sorted((ROOT / 'saga2d').rglob('*.py'))
    paths += [Path(__file__).resolve(), ROOT / 'tools/verify_eador_shard_look.py',
              ROOT / 'tools/eador_ui.py', ROOT / 'tools/cpu_budget.py']
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    match = ConcurrentCampaign.new(7, heroes=('Warrior', 'Warrior'))
    report = dict(backend=backend, local_seat=1, peer_seat=0, completed=False,
                  source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_dirty_paths=subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
                  source_sha256=hashes, initial_checkpoint=match.checkpoint(), commands=[],
                  inputs=[], captures=[], exact_ui_orders=[],
                  scope='Paid public PvE autoplay preparation, then directed seat-1 input against a loopback peer. '
                        'No independent human, hosted-server restart, full campaign or release-readiness claim.')
    host = client = game = player = root = None
    source = 'public model preparation (includes PvE autoplay)'

    def envelope(seat, action, *args):
        return {'day': match.day, 'realm_revision': match.realms[seat].revision,
                'action': action, 'args': list(args), 'kwargs': {}}

    def apply(seat, command):
        match.apply(seat, command)
        report['commands'].append(dict(seat=seat, source=source, command=command,
                                       checkpoint=match.checkpoint()))
        budget.checkpoint()

    def finish_pve(seat, send):
        for _ in range(80):
            if match.realms[seat].battle.outcome:
                break
            send('battle.auto_turn')
        assert match.realms[seat].battle.outcome == 'player', 'The paid preparation did not win.'
        send('resolve_battle')

    def settle(until, *, applied=True):
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            host.poll()
            client.poll()
            player._tick()
            assert not host.error and not client.error, (host.error, client.error)
            if (until() and host.state == match.snapshot(0) and client.state == match.snapshot(1)
                    and (not applied or root is None or root._revision == client.revision)):
                return
            time.sleep(.005)
        raise AssertionError('Conflict UI and both socket views did not converge.')

    def peer_order(action, *args, applied=True):
        nonlocal source
        source = 'seat-0 socket host public order'
        revision = match.realms[0].revision
        host.submit(envelope(0, action, *args))
        settle(lambda: match.realms[0].revision > revision, applied=applied)

    def control(text, *, enabled=True):
        button = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == text)
        assert button is not None and button.enabled == enabled, text
        x, y, width, height = button.bounds
        assert 0 <= x < x + width <= game.width and 0 <= y < y + height <= game.height
        return button

    def capture(name):
        before = match.checkpoint()
        player.pointer(10, 100)
        player.capture(name, settle=False)
        assert match.checkpoint() == before, 'Inspection changed the authority.'
        report['captures'].append(dict(name=name, scene=type(game.scene).__name__,
                                       after_command=len(report['commands']), percent=reading_scale(game),
                                       png=player.native, checkpoint_unchanged=True))

    def ui_order(action, args, activate, until):
        nonlocal source
        source = 'seat-1 native input' if player.native else 'seat-1 mock input'
        command = envelope(1, action, *args)
        expected = ConcurrentCampaign.restore(match.checkpoint())
        expected.apply(1, command)
        previous = len(report['commands'])
        activate()
        settle(until)
        assert len(report['commands']) == previous + 1
        assert report['commands'][-1]['command'] == command
        assert match.checkpoint() == expected.checkpoint(), action
        report['exact_ui_orders'].append(action)

    try:
        for seat, destination in ((0, [-1, 0]), (1, [1, 0])):
            def prepare(action, *args):
                apply(seat, envelope(seat, action, *args))
            prepare('build', 'barracks')
            prepare('recruit', 'swordsman')
            assert match.realms[seat].gold == 10
            prepare('travel', destination)
            finish_pve(seat, prepare)
        apply(0, envelope(0, 'travel', [0, 0]))
        report['preparation_commands'] = len(report['commands'])
        report['native_entry_checkpoint'] = match.checkpoint()

        host = MatchHost('shardbound-pvp-v1', apply, match.snapshot,
                         address=('127.0.0.1', 0), token='conflict-verification')
        client = MatchClient('shardbound-pvp-v1', host.address, token=host.token)
        game = create_game('Shardbound campaign conflict verification', backend=backend, visible=False,
                           save_dir=output / 'saves')
        game.set_window_size((1280, 720))
        player = PacedInput(game, budget, native=backend == 'pyglet', output=output)
        settle(lambda: client.ready)
        root = ConcurrentShardScene(client)
        game.push(root)
        player._tick()
        for key in ('f2', 'right', 'return'):
            player.press(key)
        assert reading_scale(game) == 125
        before = match.checkpoint()
        player.click(*root.grid.center((0, 0)))
        assert root.selected == (0, 0) and root.contested and match.checkpoint() == before
        assert 'one travel action' in control('Wait and attack').tooltip
        capture('01-wait-and-attack-125')
        incumbent = match.snapshot(0)['realm']
        actions, gold = match.realms[1].actions_left, match.realms[1].gold
        ui_order('challenge', ([0, 0],), lambda: player.button('Wait and attack'),
                 lambda: root.state.waiting)
        assert match.snapshot(0)['realm'] == incumbent
        assert (match.realms[1].actions_left, match.realms[1].gold) == (actions - 1, gold)
        assert match.realms[1].hero.pos == (1, 0)
        control('Withdraw challenge')
        capture('02-paid-waiting-125')

        finish_pve(0, peer_order)
        assert match.realms[0].choice.kind == 'skill' and not match.claims
        assert root.state.opponent['choosing'] and not root.state.opponent['in_battle']
        assert root.state.waiting and game.scene is root
        assert game.scene.ui.find(lambda item: isinstance(item, Label) and item.text == 'Choosing a reward')
        assert set(client.state['opponent']) == {'seat', 'capital', 'hero_pos', 'ready', 'in_battle', 'choosing'}
        capture('03-peer-earned-choice-125')
        while match.realms[0].choice:
            peer_order('choose', match.realms[0].choice.options[0].id)
        settle(lambda: type(game.scene) is BattleScene)
        assert root.battle_team == 'player' and match.encounter.battle.active_team == 'player'
        assert all(realm.battle is None for realm in match.realms)
        control('End phase')
        capture('04-shared-attacker-phase-125')

        hero_id = match.encounter.battle.hero_id
        ui_order('battle.guard', (hero_id,), lambda: player.order('battle.guard', hero_id),
                 lambda: type(game.scene) is BattleScene and root.state.battle.unit(hero_id).stance == 'guard')
        ui_order('battle.end_turn', (), lambda: player.button('End phase'),
                 lambda: type(game.scene) is BattleScene and root.state.battle.active_team == 'enemy')
        control('Waiting for opponent', enabled=False)
        assert not game.scene.accepts_orders
        capture('05-defender-phase-waiting-125')
        before = match.checkpoint()
        player.press('e')
        assert match.checkpoint() == before
        player.press('f1')
        reader = game.scene
        hero_id = match.encounter.battle.enemy_magic.hero_id
        destination = sorted(match.encounter.battle.reachable(hero_id))[0]
        peer_order('battle.move', hero_id, list(destination), applied=False)
        peer_order('battle.guard', hero_id, applied=False)
        gold = [realm.gold for realm in match.realms]
        peer_order('retreat', applied=False)
        accepted = match.checkpoint()
        assert game.scene is reader and root.state.battle is not None
        capture('06-help-retains-peer-move-guard-retreat-125')
        player.press('escape')
        settle(lambda: isinstance(game.scene, RecordedCombatPlayback), applied=False)
        historical = game.scene
        assert historical.team == 'player' and not historical.accepts_orders
        assert historical.playback.trace.after.outcome_reason == 'retreat'
        assert any(event.kind == 'move' for event in historical.playback.trace.events)
        settle(lambda: historical.playback.event.kind == 'move' and historical.playback.fraction >= .3,
               applied=False)
        capture('07-peer-move-playback-125')
        player.button('Battle log')
        assert game.scene.title == 'Recorded battle log'
        capture('08-historical-log-125')
        player.press('escape')
        assert game.scene is historical
        player.press('f6')
        assert game.scene.title == 'Live room'
        capture('09-historical-live-save-125')
        player.press('escape')
        player.press('space')
        settle(lambda: isinstance(game.scene, ChoiceScene) and root.state.battle is None)
        assert match.checkpoint() == accepted
        assert match.encounter is None and not match.claims
        assert match.provinces[(0, 0)].owner == 'realm:1' and match.realms[1].hero.pos == (0, 0)
        assert match.realms[0].hero.pos == match.realms[0].capital
        assert [realm.gold for realm in match.realms] == [max(0, gold[0] - 20), gold[1]]
        assert match.day == 1 and match.winner is None
        assert root.state.choice.kind == 'skill' and root.state.hero.level == 2
        capture('10-attacker-earned-choice-125')
        choice = root.state.choice.options[0].id
        ui_order('choose', (choice,), lambda: player.press('1'),
                 lambda: game.scene is root and root.state.choice is None)
        assert game.scenes == [root]
        capture('11-returned-map-125')
        before = match.checkpoint()
        match = ConcurrentCampaign.restore(before)
        host.snapshot = match.snapshot
        host.publish()
        settle(lambda: 'room restarted' in root.message)
        assert match.checkpoint() == before
        capture('12-restored-authority-notice-125')
        report['completed'] = True
    finally:
        try:
            if game is not None:
                game.close()
        finally:
            try:
                if client is not None:
                    client.close()
            finally:
                if host is not None:
                    host.close()
        report.update(final_checkpoint=match.checkpoint(), inputs=player.events if player else [],
                      autoplay_commands=sum(entry['command']['action'] == 'battle.auto_turn'
                                            for entry in report['commands']),
                      source_unchanged=all(hashlib.sha256(path.read_bytes()).hexdigest() ==
                                           hashes[str(path.relative_to(ROOT))] for path in paths),
                      game_closed=game is not None and not game.scenes and not game.running,
                      sockets_closed=host is not None and client is not None and host.closed and client.closed,
                      wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu_started,
                      cpu_allowance_percent=25, native_fps_cap=30)
        (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    assert report['game_closed'] and report['sockets_closed'] and report['source_unchanged']
    assert (game.backend.window is None) if backend == 'pyglet' else (not game.backend.is_running)
    print(json.dumps({key: report[key] for key in ('completed', 'captures', 'exact_ui_orders',
                                                 'wall_seconds', 'cpu_seconds', 'game_closed', 'sockets_closed')}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    args = parser.parse_args()
    verify(args.output, backend=args.backend)
