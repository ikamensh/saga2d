"""One paced, local-only native input check of the independent counter demo."""
import hashlib
import json
import os
from pathlib import Path
import resource
import select
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import time

ROOT = Path('/Users/ikamen/ai-workspace/experiments/by_kodo/saga2d')
OUTPUT = Path('/tmp/saga2d-counter-native-final')
sys.path.insert(0, str(ROOT))
os.environ['SAGA2D_SILENT'] = '1'

from saga2d import Button, Game, MatchLobby
from saga2d.online import OnlineClient
from tools.cpu_budget import CpuBudget
from tools.demo_match_room import CounterScene, GAME_ID, Help, make_menu
from tools.native_frames import tick


def fingerprints():
    paths = [ROOT / 'tools/demo_match_room.py', ROOT / 'tools/native_frames.py',
             ROOT / 'tools/cpu_budget.py', *sorted((ROOT / 'saga2d').rglob('*.py'))]
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    budget = CpuBudget(25)
    started, cpu_started = time.monotonic(), time.process_time()
    child_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    report = {'scope': 'One hidden native menu/lobby/counter/help journey; second seat is an explicit loopback OnlineClient. No reference games, hosted service, audio listening or multiplayer release claim.',
              'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'source_sha256': fingerprints(), 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'cpu_percent_requested': 25, 'native_fps_limit': 30,
              'timing_scope': 'This verifier body after Python imports, including local server startup and complete cleanup.',
              'inputs': [], 'captures': [], 'frames': 0}
    server = subprocess.Popen([sys.executable, 'tools/demo_match_room.py', '--serve', '--port', '0'],
                              cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                              env={**os.environ, 'PYTHONUNBUFFERED': '1'})
    game = guest = None
    previous_endpoint = os.environ.get('SAGA2D_SERVER_URL')
    try:
        readable, _, _ = select.select([server.stdout, server.stderr], [], [], 5)
        assert server.stdout in readable, 'Counter server startup timed out or failed'
        line = server.stdout.readline().strip()
        assert line.startswith('LISTENING ws://127.0.0.1:'), line
        endpoint = line.removeprefix('LISTENING ')
        report.update(endpoint=endpoint, server_pid=server.pid)
        os.environ['SAGA2D_SERVER_URL'] = endpoint
        with TemporaryDirectory(prefix='saga2d-counter-native-') as directory:
            game = Game('Independent counter room', visible=False, resolution=(960, 720),
                        save_dir=Path(directory) / 'saves')
            from pyglet.window import key, mouse

            def frame():
                if game.scenes:
                    tick(game)
                    report['frames'] += 1
                else:
                    time.sleep(1 / 30)
                if guest is not None:
                    guest.poll()
                budget.checkpoint()

            def wait(until):
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    frame()
                    if until():
                        return
                raise AssertionError('Counter room did not reach the expected state')

            def click(label):
                control = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == label)
                assert control is not None and control.enabled, label
                x, y, width, height = control.bounds
                assert 0 <= x < x + width <= game.width and 0 <= y < y + height <= game.height
                window = game.backend.window
                scale = min(window.width / game.width, window.height / game.height)
                px = (window.width - game.width * scale) / 2 + (x + width / 2) * scale
                py = (window.height - game.height * scale) / 2 + (game.height - y - height / 2) * scale
                report['inputs'].append({'scene': type(game.scene).__name__, 'click': label})
                window.dispatch_event('on_mouse_press', round(px), round(py), mouse.LEFT, 0)
                window.dispatch_event('on_mouse_release', round(px), round(py), mouse.LEFT, 0)
                frame()

            def press(name):
                report['inputs'].append({'scene': type(game.scene).__name__, 'key': name})
                symbol = getattr(key, name.upper())
                game.backend.window.dispatch_event('on_key_press', symbol, 0)
                game.backend.window.dispatch_event('on_key_release', symbol, 0)
                frame()

            def capture(name):
                for _ in range(3):
                    frame()
                path = OUTPUT / f'{name}.png'
                game.backend.capture_frame().save(path)
                report['captures'].append({'file': path.name, 'scene': type(game.scene).__name__,
                                           'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})

            try:
                game.push(make_menu())
                frame()
                capture('menu')
                click('Create room')
                assert isinstance(game.scene, MatchLobby)
                lobby = game.scene
                wait(lambda: lobby.session.state is not None)
                assert lobby.session.room == 'counter' and not lobby.session.ready
                capture('lobby')
                guest = OnlineClient(GAME_ID, endpoint=endpoint, room=lobby.session.room)
                wait(lambda: isinstance(game.scene, CounterScene) and guest.ready)
                room = game.scene
                assert game.scenes == [room] and room.session is lobby.session
                assert room.session.player == 0 and guest.player == 1
                click('Add one')
                wait(lambda: room.session.state['counts'] == guest.state['counts'] == [1, 0])
                capture('counter')
                click('Help')
                assert isinstance(game.scene, Help) and not room.session.closed
                guest.submit({'action': 'add'})
                report['inputs'].append({'scene': 'remote peer', 'command': {'action': 'add'}})
                wait(lambda: room.session.state['counts'] == guest.state['counts'] == [1, 1])
                capture('help-peer-updated')
                press('escape')
                assert game.scene is room and room.session.ready
                press('space')
                wait(lambda: room.session.state['counts'] == guest.state['counts'] == [2, 1])
                capture('counter-returned')
                report.update(final_host=room.session.state, final_guest=guest.state,
                              overlay_polling_verified=True, lobby_ownership_transferred=True)
            finally:
                game.close()
            report['game_window_closed'] = game.backend.window is None
            report['owning_session_closed'] = room.session.closed
            assert report['game_window_closed'] and report['owning_session_closed']
            wait(lambda: not guest.ready)
            report['peer_observed_disconnect'] = True
    finally:
        if game is not None:
            game.close()
        if guest is not None:
            guest.close()
        server.terminate()
        try:
            _, errors = server.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            _, errors = server.communicate(timeout=5)
        (OUTPUT / 'server-stderr.txt').write_text(errors)
        report['server_returncode'] = server.returncode
        if previous_endpoint is None:
            os.environ.pop('SAGA2D_SERVER_URL', None)
        else:
            os.environ['SAGA2D_SERVER_URL'] = previous_endpoint
    deadline = time.monotonic() + 3
    while any(thread.name == 'saga2d-online' for thread in threading.enumerate()) and time.monotonic() < deadline:
        time.sleep(1 / 30)
    assert not any(thread.name == 'saga2d-online' for thread in threading.enumerate())
    assert 'Traceback (most recent call last)' not in errors, errors
    assert report['source_sha256'] == fingerprints(), 'Counter/framework sources changed during native verification'
    child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    report.update(wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu_started,
                  child_cpu_seconds=(child_after.ru_utime + child_after.ru_stime - child_before.ru_utime - child_before.ru_stime),
                  online_workers_closed=True, sources_unchanged=True)
    (OUTPUT / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({field: report[field] for field in ('frames', 'wall_seconds', 'cpu_seconds', 'child_cpu_seconds',
                                                       'final_host', 'final_guest', 'server_returncode', 'online_workers_closed')}))


if __name__ == '__main__':
    main()
