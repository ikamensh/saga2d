"""Native verification input respects a frame budget without changing simulation time."""
import sys
import time
from types import ModuleType, SimpleNamespace

import pytest

from eador.app import create_game
from eador.model import State
from eador.scene import BattleScene, ShardScene
from saga2d.backends.mock_backend import MockBackend
from tools.eador_ui import PlayerInput


class NativeWindow:
    """The native event interface, translated into a recording backend for this test."""
    width, height = 1280, 800

    def __init__(self, backend):
        self.backend = backend

    def dispatch_event(self, name, *args):
        if name.startswith('on_key_'):
            self.backend.inject_key(args[0], type=name.removeprefix('on_'))
        elif name == 'on_mouse_press':
            self.backend.inject_click(args[0], self.height - args[1])
        else:
            assert name == 'on_mouse_release'
            self.backend.inject_release(args[0], self.height - args[1])


@pytest.mark.parametrize('native', [True, False])
def test_player_input_paces_native_bursts_and_battle_capture(monkeypatch, tmp_path, native):
    """Keys, clicks and every settling frame share the cap; mock tests retain immediate ticks."""
    wall = [0.0]
    sleeps, starts = [], []

    def sleep(seconds):
        assert seconds > 0
        sleeps.append(seconds)
        wall[0] += seconds

    monkeypatch.setattr(time, 'monotonic', lambda: wall[0])
    monkeypatch.setattr(time, 'sleep', sleep)
    window_module = ModuleType('pyglet.window')
    window_module.key = SimpleNamespace(ENTER='return', TAB='tab')
    window_module.mouse = SimpleNamespace(LEFT=1)
    pyglet_module = ModuleType('pyglet')
    pyglet_module.window = window_module
    monkeypatch.setitem(sys.modules, 'pyglet', pyglet_module)
    monkeypatch.setitem(sys.modules, 'pyglet.window', window_module)

    class TimedBackend(MockBackend):
        def begin_frame(self, clear_color=None):
            starts.append(wall[0])
            super().begin_frame(clear_color)

        def end_frame(self):
            wall[0] += .006  # Rendering has a cost which must count toward the frame interval.
            super().end_frame()

    backend = TimedBackend()
    backend.window = NativeWindow(backend)
    game = create_game(backend=backend, save_dir=tmp_path)
    try:
        game.push(ShardScene(State.new(7)))
        player = PlayerInput(game, native=native)
        player.click(*game.scene.grid.center((-1, 0)))
        player.press('return')
        assert isinstance(game.scene, BattleScene)
        before = game.scene.clock
        frame = len(starts)
        player.capture('battle')
        assert len(starts) - frame == 110
        assert game.scene.clock - before == pytest.approx(110 / 60)
        player.press('tab')
        gaps = [right - left for left, right in zip(starts, starts[1:])]
        if native:
            assert min(gaps) == pytest.approx(1 / 30)
            assert max(gaps) == pytest.approx(1 / 30)
            assert len(sleeps) == len(starts) - 1
            # Work after a pause starts fresh, with no accumulated catch-up frames.
            wall[0] += 10
            player.press('tab')
            player.press('tab')
            assert starts[-1] - starts[-2] == pytest.approx(1 / 30)
        else:
            assert not sleeps
            assert gaps == pytest.approx([.006] * len(gaps))
    finally:
        game._teardown()
