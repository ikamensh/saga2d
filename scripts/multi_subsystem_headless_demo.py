"""Headless multi-subsystem demo — mock backend only (no GUI window).

Wires input translation/rebinding, cursor, custom theme, layout widgets,
drag-and-drop, and built-in screens (message / choice / confirm / settings)
in one workflow. Run from repo root::

    uv run python scripts/multi_subsystem_headless_demo.py

Exit code 0 = all checks passed; 1 = a recorded breakage (printed with repro).
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

from saga2d import (
    Anchor,
    Button,
    ChoiceScreen,
    ConfirmDialog,
    Game,
    Label,
    Layout,
    List,
    MessageScreen,
    Panel,
    Scene,
    Style,
    Theme,
)
from saga2d.backends.base import KeyEvent, MouseEvent
from saga2d.ui.component import Component
from saga2d.ui.screens import _SettingsScene
from saga2d.ui.widgets import List as ListWidget

# --- inputs (edit here) ---
RESOLUTION = (800, 600)
DT = 1.0 / 60.0
# ---


class _FixedBox(Component):
    """Pinned layout rect (same pattern as tests/ui/test_drag_drop.py)."""

    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        w: int = 64,
        h: int = 64,
        draggable: bool = False,
        drag_data=None,
        drop_accept=None,
        on_drop=None,
    ) -> None:
        super().__init__(
            width=w,
            height=h,
            draggable=draggable,
            drag_data=drag_data,
            drop_accept=drop_accept,
            on_drop=on_drop,
        )
        self._fx = x
        self._fy = y

    def compute_layout(self, x: int, y: int, w: int, h: int) -> None:
        self._computed_x = self._fx
        self._computed_y = self._fy
        self._computed_w = self._width or 64
        self._computed_h = self._height or 64
        self._layout_children()
        self._layout_dirty = False


def _find_list_widget(root: Component) -> ListWidget | None:
    if isinstance(root, ListWidget):
        return root
    for ch in root._children:
        found = _find_list_widget(ch)
        if found is not None:
            return found
    return None


def _find_buttons(component: Component, out: list) -> None:
    from saga2d.ui.components import Button as Btn

    if isinstance(component, Btn):
        out.append(component)
    for ch in component._children:
        _find_buttons(ch, out)


def _click_center(game: Game, widget: Component) -> None:
    cx = widget._computed_x + widget._computed_w // 2
    cy = widget._computed_y + widget._computed_h // 2
    game.backend.inject_click(cx, cy)


def _prepare_assets(root: Path) -> None:
    (root / "images" / "ui").mkdir(parents=True)
    img = Image.new("RGBA", (8, 8), (200, 100, 50, 255))
    img.save(root / "images" / "ui" / "pointer.png", format="PNG")
    (root / "sounds").mkdir(parents=True)
    (root / "sounds" / "ui_blip.wav").write_bytes(b"")
    (root / "music").mkdir(parents=True)
    (root / "music" / "hub.ogg").write_bytes(b"")


class HubScene(Scene):
    background_color = (35, 40, 55, 255)

    def on_enter(self) -> None:
        self.msg_seen = False
        self.choice_idx: int | None = None
        self.confirm_yes = False
        self.list_last_select: int | None = None

        g = self.game
        g.cursor.register("hand", "ui/pointer", hotspot=(0, 0))
        g.cursor.set("hand")
        g.cursor.set_visible(True)

        g.audio.play_music("hub", loop=True)
        g.audio.play_sound("ui_blip", channel="ui")

        panel = Panel(
            width=400,
            anchor=Anchor.CENTER,
            layout=Layout.VERTICAL,
            spacing=10,
            style=Style(padding=16, background_color=(50, 55, 70, 240)),
        )
        panel.add(Label("Multi-subsystem headless hub", width=360, height=28))
        side = Panel(layout=Layout.HORIZONTAL, spacing=12)
        side.add(
            List(
                items=["Lane A", "Lane B"],
                width=120,
                height=72,
                item_height=32,
                on_select=lambda i: setattr(self, "list_last_select", int(i)),
            )
        )
        side.add(Label("Pick a lane (list)", width=140, height=72))
        panel.add(side)

        self.btn_msg = Button(
            "Open message",
            width=280,
            height=34,
            on_click=lambda: g.push(
                MessageScreen(
                    "Demo message.",
                    on_dismiss=lambda: setattr(self, "msg_seen", True),
                )
            ),
        )
        self.btn_choice = Button(
            "Choice screen",
            width=280,
            height=34,
            on_click=lambda: g.push(
                ChoiceScreen(
                    "Choose:",
                    ["One", "Two", "Three"],
                    on_choice=lambda i: setattr(self, "choice_idx", i),
                )
            ),
        )
        self.btn_confirm = Button(
            "Confirm dialog",
            width=280,
            height=34,
            on_click=lambda: g.push(
                ConfirmDialog(
                    "Proceed?",
                    on_confirm=lambda: setattr(self, "confirm_yes", True),
                )
            ),
        )
        self.btn_settings = Button(
            "Settings (rebind)",
            width=280,
            height=34,
            on_click=lambda: g.push_settings(),
        )
        for b in (
            self.btn_msg,
            self.btn_choice,
            self.btn_confirm,
            self.btn_settings,
        ):
            panel.add(b)
        self.ui.add(panel)

        dropped: list[object] = []

        src = _FixedBox(
            x=60,
            y=500,
            w=56,
            h=56,
            draggable=True,
            drag_data="token",
        )
        tgt = _FixedBox(
            x=320,
            y=500,
            w=72,
            h=56,
            drop_accept=lambda d: d == "token",
            on_drop=lambda _c, d: dropped.append(d),
        )
        self._drop_record = dropped
        self.ui.add(src)
        self.ui.add(tgt)
        self.ui._ensure_layout()

def _expect(findings: list[str], cond: bool, msg: str) -> None:
    if not cond:
        findings.append(msg)


def main() -> int:
    findings: list[str] = []
    root = Path(tempfile.mkdtemp(prefix="saga2d_multi_demo_"))
    game: Game | None = None
    try:
        _prepare_assets(root)

        custom = Theme(
            button_background_color=(70, 75, 95, 255),
            button_hover_color=(90, 95, 120, 255),
            drop_accept_color=(0, 190, 90, 100),
            drop_reject_color=(190, 40, 40, 100),
        )
        game = Game(
            "MultiDemo",
            backend="mock",
            resolution=RESOLUTION,
            asset_path=root,
        )
        game.theme = custom
        be = game.backend

        hub = HubScene()
        game.push(hub)
        game.tick(DT)

        _expect(
            findings,
            be.cursor_image is not None,
            "Cursor: expected backend.cursor_image after register/set 'hand'. "
            "Repro: run script; inspect MockBackend.cursor_image after HubScene.on_enter.",
        )

        _expect(
            findings,
            be.music_playing is not None,
            "Audio: expected music_playing set after play_music('hub'). "
            "Repro: run script; check backend.music_playing.",
        )
        _expect(
            findings,
            len(be.sounds_played) >= 1,
            "Audio: expected ≥1 mock play_sound after play_sound('ui_blip'). "
            "Repro: inspect backend.sounds_played.",
        )

        # --- List widget: click second row ---
        lst = _find_list_widget(hub.ui)
        _expect(findings, lst is not None, "Internal: List widget not found in hub UI.")
        if lst is not None:
            hub.ui._ensure_layout()
            ix = lst._computed_x + lst._computed_w // 2
            iy = lst._computed_y + int(1.5 * lst._item_height)
            be.inject_click(ix, iy)
            game.tick(DT)
            _expect(
                findings,
                hub.list_last_select == 1,
                f"List: expected on_select index 1 after click; got {hub.list_last_select!r}. "
                f"Repro: inject_click({ix}, {iy}) after layout.",
            )

        # --- Drag-and-drop ---
        be.inject_click(88, 528)
        game.tick(DT)
        _expect(
            findings,
            hub.ui.drag_manager.is_dragging,
            "DnD: drag did not start after inject_click on source. "
            "Repro: inject_click(88, 528); tick once.",
        )
        be.inject_mouse_move(356, 528)
        game.tick(DT)
        be.inject_event(MouseEvent(type="release", x=356, y=528, button="left"))
        game.tick(DT)
        _expect(
            findings,
            hub._drop_record == ["token"],
            f"DnD: expected drop ['token']; got {hub._drop_record!r}. "
            "Repro: click (88,528) → move (356,528) → release.",
        )

        # --- MessageScreen ---
        _click_center(game, hub.btn_msg)
        game.tick(DT)
        _expect(
            findings,
            isinstance(game._scene_stack.top(), MessageScreen),
            "Message: Choice/Message push failed — top scene is not MessageScreen. "
            "Repro: click center of 'Open message' button; tick.",
        )
        be.inject_key("h")
        game.tick(DT)
        _expect(
            findings,
            hub.msg_seen is True,
            "Message: on_dismiss / pop did not run. "
            "Repro: with MessageScreen on stack, inject_key('h'); tick.",
        )
        _expect(
            findings,
            game._scene_stack.top() is hub,
            "Message: stack did not return to HubScene after dismiss.",
        )

        # --- ChoiceScreen: key "2" → index 1 ---
        _click_center(game, hub.btn_choice)
        game.tick(DT)
        be.inject_key("2")
        game.tick(DT)
        _expect(
            findings,
            hub.choice_idx == 1,
            f"Choice: expected index 1 from key '2'; got {hub.choice_idx!r}.",
        )

        # --- ConfirmDialog: Enter ---
        _click_center(game, hub.btn_confirm)
        game.tick(DT)
        be.inject_key("return")
        game.tick(DT)
        _expect(findings, hub.confirm_yes is True, "Confirm: on_confirm not fired for Return.")

        # --- Settings: rebind confirm to space, close, verify translation ---
        _click_center(game, hub.btn_settings)
        game.tick(DT)
        top = game._scene_stack.top()
        _expect(
            findings,
            isinstance(top, _SettingsScene),
            "Settings: push_settings did not leave _SettingsScene on top.",
        )
        buttons: list = []
        _find_buttons(top._ui, buttons)
        binding_buttons = [b for b in buttons if b._text.startswith("[") and b._text.endswith("]")]
        confirm_btn = next((b for b in binding_buttons if b._text == "[RETURN]"), None)
        _expect(
            findings,
            confirm_btn is not None,
            "Settings: could not find [RETURN] binding button for 'confirm'.",
        )
        if confirm_btn is not None:
            confirm_btn._on_click()
            game.tick(DT)
            be.inject_key("space")
            game.tick(DT)
            bindings = game.input.get_bindings()
            _expect(
                findings,
                bindings.get("confirm") == "space",
                f"Settings: rebind failed; bindings['confirm']={bindings.get('confirm')!r}.",
            )
        be.inject_key("escape")
        game.tick(DT)
        _expect(
            findings,
            game._scene_stack.top() is hub,
            "Settings: Escape did not pop settings.",
        )

        mapped = game.input.translate([KeyEvent(type="key_press", key="space")])
        _expect(
            findings,
            len(mapped) == 1 and mapped[0].action == "confirm",
            f"Input: after rebind, space should map to action 'confirm'; got {mapped!r}. "
            "Note: List.on_event consumes confirm before Scene.handle_input — "
            "use translate() to assert bindings.",
        )

        game._teardown()
    except Exception as exc:
        findings.append(
            f"Exception: {type(exc).__name__}: {exc} "
            "(repro: uv run python scripts/multi_subsystem_headless_demo.py)"
        )
        if game is not None:
            try:
                game._teardown()
            except Exception:
                pass
        print("FAIL — multi_subsystem_headless_demo")
        for line in findings:
            print(" -", line)
        return 1
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if findings:
        print("FAIL — multi_subsystem_headless_demo")
        for line in findings:
            print(" -", line)
        return 1
    print("PASS — multi_subsystem_headless_demo (all subsystems exercised)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
