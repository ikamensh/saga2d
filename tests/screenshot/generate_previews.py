#!/usr/bin/env python3
"""Generate low-fidelity UI previews using the MockBackend + PIL.

Unlike the GPU-based screenshot tests (which require pyglet + a display),
this script uses Saga2D's **MockBackend** to record draw calls (rects,
texts, sprites) during a normal game tick, then replays those calls with
PIL's ``ImageDraw`` to produce PNG previews.

The previews are *approximate* — fonts are rendered with Pillow's default
bitmap font (not pyglet's TrueType renderer), and sprites appear as
coloured placeholders — but they are enough to verify layout, positioning,
widget state, and UI structure in a fully headless environment.

Run from the project root::

    python -m tests.screenshot.generate_previews          # previews only
    python -m tests.screenshot.generate_previews --golden  # also populate golden/

Images are saved to ``tests/screenshot/previews/`` (always) and
``tests/screenshot/golden/`` (with ``--golden``).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageDraw, ImageFont

from saga2d import Game, Scene, Theme
from saga2d.save import SaveManager
from saga2d.ui import (
    Anchor,
    Button,
    DataTable,
    Grid,
    Label,
    Layout,
    List,
    Panel,
    ProgressBar,
    Style,
    TabGroup,
    TextBox,
    Tooltip,
)
from saga2d.ui.screens import (
    ChoiceScreen,
    ConfirmDialog,
    MessageScreen,
    SaveLoadScreen,
)

# ---------------------------------------------------------------------------
# Output directories
# ---------------------------------------------------------------------------

_PREVIEWS_DIR = Path(__file__).resolve().parent / "previews"
_GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

# Module-level flag: set to True by main() when --golden is passed.
_write_golden: bool = False


def _ensure_dirs() -> None:
    _PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    if _write_golden:
        _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)


def _save(image: Image.Image, preview_name: str, golden_name: str | None = None) -> None:
    """Save *image* to previews/ and optionally to golden/.

    Args:
        image:        The rendered PIL image.
        preview_name: Filename (without path) for ``previews/``.
        golden_name:  If not None and ``_write_golden`` is True, also save
                      as ``golden/{golden_name}.png``.
    """
    _ensure_dirs()
    image.save(_PREVIEWS_DIR / preview_name)
    label = preview_name
    if golden_name and _write_golden:
        image.save(_GOLDEN_DIR / f"{golden_name}.png")
        label += f" + golden/{golden_name}.png"
    print(f"  \u2713 {label}")


# ---------------------------------------------------------------------------
# Mock-render helper: tick a scene with MockBackend, capture draw calls
# ---------------------------------------------------------------------------


def _render_mock(
    setup_fn: Callable[[Game], None],
    *,
    tick_count: int = 1,
    resolution: tuple[int, int] = (480, 360),
) -> Image.Image:
    """Create a headless MockBackend Game, tick, then paint draw calls to PIL.

    This mirrors ``render_scene()`` from the harness but uses ``backend="mock"``
    instead of ``backend="pyglet"``.

    Returns an RGBA Pillow Image with all rects and texts painted.
    """
    import saga2d.rendering.sprite as _sprite_mod
    import saga2d.util.tween as _tween_mod

    old_game = _sprite_mod._current_game
    old_tween = _tween_mod._tween_manager
    game = None

    try:
        game = Game(
            "Preview",
            resolution=resolution,
            fullscreen=False,
            backend="mock",
        )

        setup_fn(game)

        dt = 1.0 / 60.0
        for _ in range(tick_count):
            game.tick(dt=dt)

        # Now paint the recorded draw calls into a PIL image.
        backend = game._backend
        image = _paint_draw_calls(
            backend,
            resolution[0],
            resolution[1],
        )
        return image
    finally:
        if game is not None:
            game._backend.quit()
        _sprite_mod._current_game = old_game
        _tween_mod._tween_manager = old_tween


# ---------------------------------------------------------------------------
# PIL painting: replay MockBackend draw calls
# ---------------------------------------------------------------------------

# Try to load a small TrueType font for better text rendering.
# Fall back to PIL's built-in bitmap font if unavailable.
_FONT_CACHE: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return a cached PIL font at the given size."""
    if size not in _FONT_CACHE:
        # Try common system paths for a monospace/sans font.
        for candidate in (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSMono.ttf",
            "/System/Library/Fonts/Monaco.ttf",
        ):
            if Path(candidate).exists():
                try:
                    _FONT_CACHE[size] = ImageFont.truetype(candidate, size)
                    return _FONT_CACHE[size]
                except Exception:
                    continue
        # Last resort: PIL default
        _FONT_CACHE[size] = ImageFont.load_default()
    return _FONT_CACHE[size]


def _rgba(color: tuple[int, ...], opacity: float = 1.0) -> tuple[int, int, int, int]:
    """Normalize an RGBA colour tuple, applying opacity."""
    r, g, b = color[0], color[1], color[2]
    a = color[3] if len(color) >= 4 else 255
    a = int(a * opacity)
    return (r, g, b, a)


def _paint_draw_calls(
    backend: Any,
    width: int,
    height: int,
) -> Image.Image:
    """Replay ``rects``, ``texts``, and ``sprites`` onto a PIL Image."""

    # Start with the clear colour or a dark default.
    clear = getattr(backend, "clear_color", None)
    if clear and len(clear) >= 3:
        bg = (clear[0], clear[1], clear[2], 255)
    else:
        bg = (20, 20, 30, 255)

    image = Image.new("RGBA", (width, height), bg)

    # We composite each draw call onto a temporary layer so alpha blending
    # works correctly.

    # --- 1) Sprites (persistent, drawn first = background layer) ----------
    # Sort by layer order (lower draws first, behind higher).
    sorted_sprites = sorted(
        backend.sprites.values(),
        key=lambda s: s.get("layer", 0),
    )
    for sp in sorted_sprites:
        if not sp.get("visible", True):
            continue
        opacity = sp.get("opacity", 255)
        if opacity <= 0:
            continue
        sx, sy = int(sp["x"]), int(sp["y"])
        # Mock sprites don't have real image data — draw a grey placeholder.
        img_handle = sp.get("image", "")
        sw, sh = backend.get_image_size(img_handle)
        if sx + sw < 0 or sy + sh < 0 or sx > width or sy > height:
            continue  # off-screen
        tint = sp.get("tint", (1.0, 1.0, 1.0))
        # Compute a sprite colour from tint.
        r = int(100 * tint[0])
        g = int(100 * tint[1])
        b = int(120 * tint[2])
        a = int(opacity * 0.5)  # semi-transparent placeholder
        color = (r, g, b, a)
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle(
            [sx, sy, sx + sw - 1, sy + sh - 1],
            fill=color,
            outline=(min(r + 40, 255), min(g + 40, 255), min(b + 40, 255), a),
        )
        image = Image.alpha_composite(image, layer)

    # --- 2) Rects (UI overlays — panels, buttons, progress bars, etc.) ----
    for rect in backend.rects:
        rx, ry = int(rect["x"]), int(rect["y"])
        rw, rh = int(rect["width"]), int(rect["height"])
        if rw <= 0 or rh <= 0:
            continue
        color = _rgba(rect["color"], rect.get("opacity", 1.0))
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle(
            [rx, ry, rx + rw - 1, ry + rh - 1],
            fill=color,
        )
        image = Image.alpha_composite(image, layer)

    # --- 3) Draw-image calls (ImageBox widgets, etc.) ---------------------
    for img_call in backend.images:
        ix, iy = int(img_call["x"]), int(img_call["y"])
        iw, ih = int(img_call["width"]), int(img_call["height"])
        if iw <= 0 or ih <= 0:
            continue
        opacity = img_call.get("opacity", 1.0)
        a = int(255 * opacity)
        color = (80, 80, 100, a)
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        draw.rectangle(
            [ix, iy, ix + iw - 1, iy + ih - 1],
            fill=color,
            outline=(120, 120, 140, a),
        )
        image = Image.alpha_composite(image, layer)

    # --- 4) Texts (labels, button text, etc.) — drawn last (on top). -----
    for txt in backend.texts:
        text = txt["text"]
        if not text:
            continue
        tx, ty = int(txt["x"]), int(txt["y"])
        font_size = int(txt["font_size"])
        color = _rgba(txt["color"])
        font = _get_font(font_size)

        # Adjust for anchor_x / anchor_y.
        anchor_x = txt.get("anchor_x", "left")
        anchor_y = txt.get("anchor_y", "baseline")

        # Measure text for anchor adjustments.
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if anchor_x == "center":
            tx -= text_w // 2
        elif anchor_x == "right":
            tx -= text_w

        if anchor_y == "center":
            ty -= text_h // 2
        elif anchor_y == "bottom":
            ty -= text_h
        # "baseline" / "top" — no adjustment needed for our purposes.

        # Draw text directly on the image (text doesn't need alpha compositing
        # per-call since it's typically opaque and drawn on top).
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((tx, ty), text, fill=color, font=font)
        image = Image.alpha_composite(image, layer)

    return image


# ======================================================================
# Preview scene definitions (gallery-style, always generated)
# ======================================================================

_RES_MENU = (480, 360)
_RES_GALLERY = (640, 480)
_RES_TD = (960, 540)


# ---------------------------------------------------------------------------
# 1. Main Menu (from test_ui_screenshots)
# ---------------------------------------------------------------------------

def preview_main_menu() -> None:
    """Centered panel with title + 3 buttons."""

    class MenuScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=8,
            )
            panel.add(Label("Main Menu", style=Style(font_size=28)))
            panel.add(Button("New Game"))
            panel.add(Button("Load Game"))
            panel.add(Button("Quit"))
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(MenuScene())

    image = _render_mock(setup, tick_count=1, resolution=_RES_MENU)
    _save(image, "main_menu.png", golden_name="ui_main_menu")


# ---------------------------------------------------------------------------
# 2. Widget Gallery: Panel + Button states
# ---------------------------------------------------------------------------

def preview_button_states() -> None:
    """Four buttons: normal, hovered, pressed, disabled."""

    class BtnScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=10,
                style=Style(padding=20),
            )
            panel.add(Label(
                "Button States",
                style=Style(font_size=28, text_color=(255, 220, 100, 255)),
            ))

            row = Panel(
                layout=Layout.HORIZONTAL,
                spacing=12,
                style=Style(padding=0, background_color=(0, 0, 0, 0)),
            )

            btn_normal = Button("Normal", style=Style(font_size=18, padding=10))

            btn_hover = Button("Hovered", style=Style(font_size=18, padding=10))
            btn_hover._state = "hovered"

            btn_pressed = Button("Pressed", style=Style(font_size=18, padding=10))
            btn_pressed._state = "pressed"

            btn_disabled = Button("Disabled", style=Style(font_size=18, padding=10))
            btn_disabled.enabled = False

            row.add(btn_normal)
            row.add(btn_hover)
            row.add(btn_pressed)
            row.add(btn_disabled)

            panel.add(row)
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(BtnScene())

    image = _render_mock(setup, tick_count=1, resolution=_RES_GALLERY)
    _save(image, "button_states.png")


# ---------------------------------------------------------------------------
# 3. Widget Gallery: ProgressBar (0%, 50%, 100%)
# ---------------------------------------------------------------------------

def preview_progress_bars() -> None:
    """Three progress bars at different fill levels."""

    class BarScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=12,
                style=Style(padding=20),
            )
            panel.add(Label(
                "Progress Bars",
                style=Style(font_size=28, text_color=(255, 220, 100, 255)),
            ))

            for pct in (0, 50, 100):
                row = Panel(
                    layout=Layout.HORIZONTAL,
                    spacing=10,
                    style=Style(padding=0, background_color=(0, 0, 0, 0)),
                )
                row.add(Label(f"{pct:>3d}%", style=Style(font_size=18)))
                row.add(ProgressBar(
                    value=pct, max_value=100,
                    width=350, height=28,
                ))
                panel.add(row)

            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(BarScene())

    image = _render_mock(setup, tick_count=1, resolution=_RES_GALLERY)
    _save(image, "progress_bars.png")


# ---------------------------------------------------------------------------
# 4. Widget Gallery: List with selection
# ---------------------------------------------------------------------------

def preview_list() -> None:
    """List widget with 6 items, item 3 selected."""

    class ListScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=10,
                style=Style(padding=20),
            )
            panel.add(Label(
                "List Widget",
                style=Style(font_size=28, text_color=(255, 220, 100, 255)),
            ))

            lst = List(
                [
                    "Slot 1 - Elven Forest",
                    "Slot 2 - Dwarven Mines",
                    "Slot 3 - Dragon Keep",
                    "Slot 4 - Haunted Marsh",
                    "Slot 5 - Crystal Caves",
                    "Slot 6 - Shadow Tower",
                ],
                width=320,
                item_height=30,
            )
            lst.selected_index = 2
            panel.add(lst)
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(ListScene())

    image = _render_mock(setup, tick_count=1, resolution=_RES_GALLERY)
    _save(image, "list_widget.png")


# ---------------------------------------------------------------------------
# 5. Widget Gallery: Grid with selection
# ---------------------------------------------------------------------------

def preview_grid() -> None:
    """3x3 Grid with labels in cells, cell (1,1) selected."""

    class GridScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=10,
                style=Style(padding=20),
            )
            panel.add(Label(
                "Grid Widget",
                style=Style(font_size=28, text_color=(255, 220, 100, 255)),
            ))

            grid = Grid(
                3, 3,
                cell_size=(64, 64),
                spacing=4,
                style=Style(padding=6),
            )
            grid.set_cell(0, 0, Label("Sw", style=Style(font_size=14)))
            grid.set_cell(1, 0, Label("Sh", style=Style(font_size=14)))
            grid.set_cell(2, 0, Label("Bw", style=Style(font_size=14)))
            grid.set_cell(0, 1, Label("Hp", style=Style(font_size=14)))
            grid.set_cell(1, 1, Label("Mp", style=Style(font_size=14)))
            grid.selected = (1, 1)
            panel.add(grid)
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(GridScene())

    image = _render_mock(setup, tick_count=1, resolution=_RES_GALLERY)
    _save(image, "grid_widget.png")


# ---------------------------------------------------------------------------
# 6. Widget Gallery: TextBox
# ---------------------------------------------------------------------------

def preview_textbox() -> None:
    """TextBox with wrapped multi-line text."""

    class TextScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=10,
                style=Style(padding=20),
            )
            panel.add(Label(
                "TextBox Widget",
                style=Style(font_size=28, text_color=(255, 220, 100, 255)),
            ))

            panel.add(TextBox(
                "The ancient fortress loomed ahead, its crumbling towers "
                "silhouetted against the crimson sky. Our party pressed "
                "forward through the overgrown courtyard, weapons drawn.",
                width=400,
                style=Style(font_size=16),
            ))
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(TextScene())

    image = _render_mock(setup, tick_count=1, resolution=_RES_GALLERY)
    _save(image, "textbox_widget.png")


# ---------------------------------------------------------------------------
# 7. Widget Gallery: TabGroup
# ---------------------------------------------------------------------------

def preview_tabgroup() -> None:
    """TabGroup with 3 tabs, Stats tab active."""

    class TabScene(Scene):
        def on_enter(self) -> None:
            stats_panel = Panel(
                layout=Layout.VERTICAL, spacing=6,
                width=300, height=120, style=Style(padding=10),
            )
            stats_panel.add(Label("STR: 18", style=Style(font_size=16)))
            stats_panel.add(Label("DEX: 14", style=Style(font_size=16)))
            stats_panel.add(Label("INT: 12", style=Style(font_size=16)))

            skills_panel = Panel(
                layout=Layout.VERTICAL, spacing=6,
                width=300, height=120, style=Style(padding=10),
            )
            skills_panel.add(Label("Fireball Lv.3", style=Style(font_size=16)))

            items_panel = Panel(
                layout=Layout.VERTICAL, spacing=6,
                width=300, height=120, style=Style(padding=10),
            )
            items_panel.add(Label("Potion x5", style=Style(font_size=16)))

            tabs = TabGroup(
                {"Stats": stats_panel, "Skills": skills_panel, "Items": items_panel},
                width=320, height=160, anchor=Anchor.CENTER,
            )
            self.ui.add(tabs)

    def setup(game: Game) -> None:
        game.push(TabScene())

    image = _render_mock(setup, tick_count=1, resolution=_RES_GALLERY)
    _save(image, "tabgroup_widget.png")


# ---------------------------------------------------------------------------
# 8. Widget Gallery: DataTable
# ---------------------------------------------------------------------------

def preview_datatable() -> None:
    """DataTable with header, alternating rows, and selection."""

    class TableScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=10,
                style=Style(padding=20),
            )
            panel.add(Label(
                "DataTable Widget",
                style=Style(font_size=28, text_color=(255, 220, 100, 255)),
            ))

            dt = DataTable(
                ["Unit", "Class", "Level"],
                [
                    ["Arthas", "Paladin", "10"],
                    ["Jaina", "Mage", "12"],
                    ["Thrall", "Shaman", "15"],
                    ["Sylvanas", "Ranger", "18"],
                    ["Uther", "Cleric", "9"],
                ],
                width=360,
            )
            dt.selected_row = 1
            panel.add(dt)
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(TableScene())

    image = _render_mock(setup, tick_count=1, resolution=_RES_GALLERY)
    _save(image, "datatable_widget.png")


# ---------------------------------------------------------------------------
# 9. Widget Gallery: Tooltip
# ---------------------------------------------------------------------------

def preview_tooltip() -> None:
    """Tooltip past its delay, visible on screen."""

    class TipScene(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label(
                "Hover over items for details",
                anchor=Anchor.TOP,
                margin=20,
                style=Style(font_size=16),
            ))
            self._tooltip = Tooltip(
                "Sword of Flames (+12 ATK)",
                delay=0.3,
                style=Style(font_size=14),
            )
            self.ui.add(self._tooltip)
            self._tooltip.show(150, 180)

    def setup(game: Game) -> None:
        game.push(TipScene())
        # Advance past the 0.3s delay.
        for _ in range(30):
            game.tick(dt=1.0 / 60.0)

    image = _render_mock(setup, tick_count=1, resolution=_RES_GALLERY)
    _save(image, "tooltip_widget.png")


# ---------------------------------------------------------------------------
# 10. Battle Demo: Title Scene
# ---------------------------------------------------------------------------

def preview_battle_title() -> None:
    """Battle Vignette title screen (if importable)."""
    _demo_dir = Path(__file__).resolve().parents[2] / "examples" / "battle_vignette"
    _asset_dir = _demo_dir / "assets"
    added = False
    if str(_demo_dir) not in sys.path:
        sys.path.insert(0, str(_demo_dir))
        added = True
    try:
        from battle_demo import TitleScene as BattleTitleScene  # type: ignore[import-not-found]
    except ImportError:
        print("  \u2298 battle_title.png (battle_demo not importable)")
        return
    finally:
        if added:
            sys.path.remove(str(_demo_dir))

    def setup(game: Game) -> None:
        # BattleTitleScene creates decorative Sprites that need asset files.
        game._asset_path = _asset_dir
        game.push(BattleTitleScene())

    image = _render_mock(setup, tick_count=1, resolution=(1920, 1080))
    # Scale down for easier viewing.
    image = image.resize((640, 360), Image.LANCZOS)
    _save(image, "battle_title.png")


# ---------------------------------------------------------------------------
# 11. Tower Defense: Title Scene
# ---------------------------------------------------------------------------

def preview_td_title() -> None:
    """Tower Defense title screen (if importable)."""
    _demo_dir = Path(__file__).resolve().parents[2] / "examples" / "tower_defense"
    added = False
    if str(_demo_dir) not in sys.path:
        sys.path.insert(0, str(_demo_dir))
        added = True
    try:
        import main as td_main  # type: ignore[import-not-found]
    except ImportError:
        print("  \u2298 td_title.png (tower_defense not importable)")
        return
    finally:
        if added:
            sys.path.remove(str(_demo_dir))

    def setup(game: Game) -> None:
        game.theme = Theme(
            font="serif",
            font_size=24,
            text_color=(220, 220, 230, 255),
            panel_background_color=(30, 35, 50, 220),
            panel_padding=16,
            button_background_color=(50, 55, 80, 255),
            button_hover_color=(70, 80, 120, 255),
            button_press_color=(35, 40, 60, 255),
            button_text_color=(220, 220, 230, 255),
            button_padding=14,
            button_font_size=26,
            button_min_width=220,
        )
        game.push(td_main.TitleScene())

    image = _render_mock(setup, tick_count=1, resolution=_RES_TD)
    _save(image, "td_title.png")


# ---------------------------------------------------------------------------
# 12. Tower Defense: GameScene (initial map)
# ---------------------------------------------------------------------------

def preview_td_game() -> None:
    """Tower Defense game scene — initial map with slots and HUD."""
    _demo_dir = Path(__file__).resolve().parents[2] / "examples" / "tower_defense"
    _asset_dir = _demo_dir / "assets"
    added = False
    if str(_demo_dir) not in sys.path:
        sys.path.insert(0, str(_demo_dir))
        added = True
    try:
        import main as td_main  # type: ignore[import-not-found]
    except ImportError:
        print("  \u2298 td_game_initial.png (tower_defense not importable)")
        return
    finally:
        if added:
            sys.path.remove(str(_demo_dir))

    def setup(game: Game) -> None:
        game._asset_path = _asset_dir
        game.theme = Theme(
            font="serif",
            font_size=24,
            text_color=(220, 220, 230, 255),
            panel_background_color=(30, 35, 50, 220),
            panel_padding=16,
            button_background_color=(50, 55, 80, 255),
            button_hover_color=(70, 80, 120, 255),
            button_press_color=(35, 40, 60, 255),
            button_text_color=(220, 220, 230, 255),
            button_padding=14,
            button_font_size=26,
            button_min_width=220,
        )
        game.push(td_main.GameScene())

    image = _render_mock(setup, tick_count=1, resolution=_RES_TD)
    _save(image, "td_game_initial.png")


# ======================================================================
# Golden generators — exact scene setups matching screenshot tests
# ======================================================================
# These replicate the EXACT scene construction from each test file so the
# golden PNGs have identical layout/content.  Only generated when
# ``--golden`` is passed.

# ---------------------------------------------------------------------------
# test_ui_screenshots.py goldens
# ---------------------------------------------------------------------------

def golden_ui_main_menu() -> None:
    """Exact scene from test_ui_main_menu (480x360)."""

    class MenuScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=8,
            )
            panel.add(Label("Main Menu", style=Style(font_size=28)))
            panel.add(Button("New Game"))
            panel.add(Button("Load Game"))
            panel.add(Button("Quit"))
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(MenuScene())

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_ui_main_menu.png", golden_name="ui_main_menu")


def golden_ui_horizontal_buttons() -> None:
    """Exact scene from test_ui_horizontal_buttons (480x360)."""

    class HBarScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.BOTTOM,
                layout=Layout.HORIZONTAL,
                spacing=12,
                margin=10,
            )
            panel.add(Button("Attack"))
            panel.add(Button("Defend"))
            panel.add(Button("Magic"))
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(HBarScene())

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_ui_horizontal_buttons.png", golden_name="ui_horizontal_buttons")


def golden_ui_styled_label() -> None:
    """Exact scene from test_ui_styled_label (480x360)."""

    class LabelScene(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label(
                "GAME OVER",
                anchor=Anchor.CENTER,
                style=Style(
                    font_size=40,
                    text_color=(255, 60, 60, 255),
                ),
            ))

    def setup(game: Game) -> None:
        game.push(LabelScene())

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_ui_styled_label.png", golden_name="ui_styled_label")


def golden_ui_nested_panels() -> None:
    """Exact scene from test_ui_nested_panels (480x360)."""

    class NestedScene(Scene):
        def on_enter(self) -> None:
            inner_style = Style(
                background_color=(80, 80, 100, 220),
                padding=10,
            )

            top_row = Panel(
                layout=Layout.HORIZONTAL, spacing=20,
                style=inner_style,
            )
            top_row.add(Label("HP: 100", style=Style(font_size=18)))
            top_row.add(Label("MP: 50", style=Style(font_size=18)))

            bottom_row = Panel(
                layout=Layout.HORIZONTAL, spacing=20,
                style=inner_style,
            )
            bottom_row.add(Label("ATK: 25", style=Style(font_size=18)))
            bottom_row.add(Label("DEF: 18", style=Style(font_size=18)))

            outer = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=8,
                style=Style(
                    background_color=(30, 30, 45, 240),
                    padding=14,
                ),
            )
            outer.add(top_row)
            outer.add(bottom_row)
            self.ui.add(outer)

    def setup(game: Game) -> None:
        game.push(NestedScene())

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_ui_nested_panels.png", golden_name="ui_nested_panels")


# ---------------------------------------------------------------------------
# test_widget_screenshots.py goldens
# ---------------------------------------------------------------------------

def golden_widget_progress_bar() -> None:
    """Exact scene from test_progress_bar (480x360)."""

    class BarScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=8,
            )
            panel.add(Label("Health", style=Style(font_size=20)))
            panel.add(ProgressBar(
                value=75,
                max_value=100,
                width=300,
                height=28,
            ))
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(BarScene())

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_widget_progress_bar.png", golden_name="widget_progress_bar")


def golden_widget_textbox_instant() -> None:
    """Exact scene from test_textbox_instant (480x360)."""

    class TextScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=6,
                style=Style(padding=12),
            )
            panel.add(Label("Journal Entry", style=Style(font_size=22)))
            panel.add(TextBox(
                "The ancient fortress loomed ahead, its crumbling towers "
                "silhouetted against the crimson sky. Our party pressed "
                "forward through the overgrown courtyard, weapons drawn.",
                width=350,
                style=Style(font_size=16),
            ))
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(TextScene())

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_widget_textbox_instant.png", golden_name="widget_textbox_instant")


def golden_widget_list_with_selection() -> None:
    """Exact scene from test_list_with_selection (480x360)."""

    class ListScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=8,
            )
            panel.add(Label("Save Files", style=Style(font_size=20)))
            lst = List(
                ["Slot 1 - Castle", "Slot 2 - Forest", "Slot 3 - Dungeon",
                 "Slot 4 - Village", "Slot 5 - Empty"],
                width=280,
                item_height=28,
            )
            lst.selected_index = 2
            panel.add(lst)
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(ListScene())

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_widget_list_with_selection.png", golden_name="widget_list_with_selection")


def golden_widget_grid_with_cells() -> None:
    """Exact scene from test_grid_with_cells (480x360)."""

    class GridScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=8,
            )
            panel.add(Label("Inventory", style=Style(font_size=20)))
            grid = Grid(
                3, 3,
                cell_size=(64, 64),
                spacing=4,
                style=Style(padding=6),
            )
            grid.set_cell(0, 0, Label("Sw", style=Style(font_size=14)))
            grid.set_cell(1, 0, Label("Sh", style=Style(font_size=14)))
            grid.set_cell(2, 0, Label("Bw", style=Style(font_size=14)))
            grid.set_cell(0, 1, Label("Hp", style=Style(font_size=14)))
            grid.set_cell(1, 1, Label("Mp", style=Style(font_size=14)))
            grid.selected = (1, 1)
            panel.add(grid)
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(GridScene())

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_widget_grid_with_cells.png", golden_name="widget_grid_with_cells")


def golden_widget_tooltip_visible() -> None:
    """Exact scene from test_tooltip_visible (480x360)."""

    class TipScene(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label(
                "Hover over items for details",
                anchor=Anchor.TOP,
                margin=20,
                style=Style(font_size=16),
            ))
            self._tooltip = Tooltip(
                "Sword of Flames (+12 ATK)",
                delay=0.3,
                style=Style(font_size=14),
            )
            self.ui.add(self._tooltip)
            self._tooltip.show(150, 180)

    def setup(game: Game) -> None:
        game.push(TipScene())
        # Advance past the 0.3 s delay (30 ticks * 1/60 = 0.5 s > 0.3 s).
        for _ in range(30):
            game.tick(dt=1.0 / 60.0)

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_widget_tooltip_visible.png", golden_name="widget_tooltip_visible")


def golden_widget_tabgroup() -> None:
    """Exact scene from test_tabgroup (480x360)."""

    class TabScene(Scene):
        def on_enter(self) -> None:
            stats_panel = Panel(
                layout=Layout.VERTICAL,
                spacing=6,
                width=300,
                height=120,
                style=Style(padding=10),
            )
            stats_panel.add(Label("STR: 18", style=Style(font_size=16)))
            stats_panel.add(Label("DEX: 14", style=Style(font_size=16)))
            stats_panel.add(Label("INT: 12", style=Style(font_size=16)))

            skills_panel = Panel(
                layout=Layout.VERTICAL,
                spacing=6,
                width=300,
                height=120,
                style=Style(padding=10),
            )
            skills_panel.add(Label("Fireball Lv.3", style=Style(font_size=16)))
            skills_panel.add(Label("Heal Lv.2", style=Style(font_size=16)))

            items_panel = Panel(
                layout=Layout.VERTICAL,
                spacing=6,
                width=300,
                height=120,
                style=Style(padding=10),
            )
            items_panel.add(Label("Potion x5", style=Style(font_size=16)))
            items_panel.add(Label("Elixir x2", style=Style(font_size=16)))

            tabs = TabGroup(
                {"Stats": stats_panel, "Skills": skills_panel, "Items": items_panel},
                width=320,
                height=160,
                anchor=Anchor.CENTER,
            )
            self.ui.add(tabs)

    def setup(game: Game) -> None:
        game.push(TabScene())

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_widget_tabgroup.png", golden_name="widget_tabgroup")


def golden_widget_datatable() -> None:
    """Exact scene from test_datatable (480x360)."""

    class TableScene(Scene):
        def on_enter(self) -> None:
            dt = DataTable(
                ["Unit", "Class", "Level"],
                [
                    ["Arthas", "Paladin", "10"],
                    ["Jaina", "Mage", "12"],
                    ["Thrall", "Shaman", "15"],
                    ["Sylvanas", "Ranger", "18"],
                    ["Uther", "Cleric", "9"],
                ],
                width=360,
                anchor=Anchor.CENTER,
            )
            dt.selected_row = 1
            self.ui.add(dt)

    def setup(game: Game) -> None:
        game.push(TableScene())

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_widget_datatable.png", golden_name="widget_datatable")


def golden_widget_combined_dialog() -> None:
    """Exact scene from test_combined_dialog (480x360)."""

    class DialogScene(Scene):
        def on_enter(self) -> None:
            dialog = Panel(
                anchor=Anchor.BOTTOM,
                margin=10,
                layout=Layout.VERTICAL,
                spacing=8,
                width=460,
                style=Style(
                    background_color=(25, 25, 40, 240),
                    padding=12,
                ),
            )

            top_row = Panel(
                layout=Layout.HORIZONTAL,
                spacing=10,
                style=Style(padding=0, background_color=(0, 0, 0, 0)),
            )

            portrait_panel = Panel(
                width=64,
                height=64,
                style=Style(
                    background_color=(80, 60, 100, 255),
                    padding=4,
                ),
            )
            portrait_panel.add(Label("NPC", style=Style(font_size=14)))
            top_row.add(portrait_panel)

            text = TextBox(
                "Greetings, adventurer! I have a quest for you. "
                "The goblins in the eastern caves have stolen our "
                "sacred relic. Will you retrieve it for us?",
                typewriter_speed=100,
                width=350,
                style=Style(font_size=15),
            )
            text.skip()
            top_row.add(text)

            dialog.add(top_row)

            button_row = Panel(
                layout=Layout.HORIZONTAL,
                spacing=12,
                style=Style(padding=0, background_color=(0, 0, 0, 0)),
            )
            button_row.add(Button(
                "Accept",
                style=Style(font_size=16, padding=8),
            ))
            button_row.add(Button(
                "Decline",
                style=Style(font_size=16, padding=8),
            ))
            dialog.add(button_row)

            self.ui.add(dialog)

    def setup(game: Game) -> None:
        game.push(DialogScene())

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_widget_combined_dialog.png", golden_name="widget_combined_dialog")


# ---------------------------------------------------------------------------
# test_stage13_screenshots.py goldens
# ---------------------------------------------------------------------------

def golden_stage13_message_screen() -> None:
    """Exact scene from test_message_screen (480x360)."""

    class BaseScene(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label(
                "Game World",
                anchor=Anchor.TOP,
                margin=20,
                style=Style(font_size=20),
            ))

    def setup(game: Game) -> None:
        game.push(BaseScene())
        game.push(MessageScreen("You found a legendary sword!"))

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_stage13_message_screen.png", golden_name="stage13_message_screen")


def golden_stage13_choice_screen() -> None:
    """Exact scene from test_choice_screen (480x360)."""

    class BaseScene(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label(
                "Character Creation",
                anchor=Anchor.TOP,
                margin=20,
                style=Style(font_size=20),
            ))

    def setup(game: Game) -> None:
        game.push(BaseScene())
        game.push(ChoiceScreen(
            "Choose your class:",
            ["Warrior", "Mage", "Rogue"],
        ))

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_stage13_choice_screen.png", golden_name="stage13_choice_screen")


def golden_stage13_confirm_dialog() -> None:
    """Exact scene from test_confirm_dialog (480x360)."""

    class BaseScene(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label(
                "Inventory",
                anchor=Anchor.TOP,
                margin=20,
                style=Style(font_size=20),
            ))

    def setup(game: Game) -> None:
        game.push(BaseScene())
        game.push(ConfirmDialog("Overwrite existing save?"))

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_stage13_confirm_dialog.png", golden_name="stage13_confirm_dialog")


def golden_stage13_save_load_screen() -> None:
    """Exact scene from test_save_load_screen (480x360).

    Creates a temporary directory with pre-populated save slots.
    """
    with tempfile.TemporaryDirectory() as tmp:
        save_dir = Path(tmp) / "saves"
        mgr = SaveManager(save_dir)
        mgr.save(1, {"hero": "Arthas", "level": 10}, "CampaignScene")
        mgr.save(3, {"hero": "Jaina", "level": 15}, "BattleScene")

        class BaseScene(Scene):
            def on_enter(self) -> None:
                self.ui.add(Label(
                    "Main Menu",
                    anchor=Anchor.TOP,
                    margin=20,
                    style=Style(font_size=20),
                ))

        def setup(game: Game) -> None:
            game.push(BaseScene())
            game.push(SaveLoadScreen(
                "load",
                save_manager=mgr,
                slot_count=5,
            ))

        image = _render_mock(setup, tick_count=1, resolution=(480, 360))
        _save(image, "golden_stage13_save_load_screen.png", golden_name="stage13_save_load_screen")


def golden_stage13_hud_bar() -> None:
    """Exact scene from test_hud_bar (480x360)."""

    class GameScene(Scene):
        show_hud = True

        def on_enter(self) -> None:
            self.ui.add(Label(
                "Explore the Dungeon",
                anchor=Anchor.CENTER,
                style=Style(font_size=22, text_color=(180, 180, 180, 255)),
            ))

    def setup(game: Game) -> None:
        game.push(GameScene())

        hp_panel = Panel(
            anchor=Anchor.TOP_LEFT,
            margin=10,
            layout=Layout.HORIZONTAL,
            spacing=6,
        )
        hp_panel.add(Label(
            "HP",
            style=Style(font_size=16, text_color=(255, 80, 80, 255)),
        ))
        hp_panel.add(ProgressBar(
            value=72,
            max_value=100,
            width=120,
            height=18,
            bar_color=(200, 40, 40, 255),
            bg_color=(60, 20, 20, 200),
        ))
        game.hud.add(hp_panel)

        game.hud.add(Label(
            "Gold: 500",
            anchor=Anchor.TOP_RIGHT,
            margin=10,
            style=Style(font_size=16, text_color=(255, 215, 0, 255)),
        ))

    image = _render_mock(setup, tick_count=1, resolution=(480, 360))
    _save(image, "golden_stage13_hud_bar.png", golden_name="stage13_hud_bar")


def golden_stage13_menu_scene() -> None:
    """Exact scene from test_menu_scene (640x480)."""

    class MainMenu(Scene):
        show_hud = False

        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=20,
                style=Style(
                    background_color=(20, 20, 35, 220),
                    padding=40,
                ),
            )
            panel.add(Label(
                "Chronicles of the Realm",
                style=Style(
                    font_size=36,
                    text_color=(220, 200, 140, 255),
                ),
            ))
            panel.add(Button("New Game", style=Style(font_size=20, padding=10)))
            panel.add(Button("Load Game", style=Style(font_size=20, padding=10)))
            panel.add(Button("Settings", style=Style(font_size=20, padding=10)))
            panel.add(Button("Quit", style=Style(font_size=20, padding=10)))
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(MainMenu())

    image = _render_mock(setup, tick_count=1, resolution=(640, 480))
    _save(image, "golden_stage13_menu_scene.png", golden_name="stage13_menu_scene")


# ---------------------------------------------------------------------------
# test_tower_defense_screenshots.py goldens
# ---------------------------------------------------------------------------

def _td_theme() -> Theme:
    """Return the tower defense theme (shared by all TD goldens)."""
    return Theme(
        font="serif",
        font_size=24,
        text_color=(220, 220, 230, 255),
        panel_background_color=(30, 35, 50, 220),
        panel_padding=16,
        button_background_color=(50, 55, 80, 255),
        button_hover_color=(70, 80, 120, 255),
        button_press_color=(35, 40, 60, 255),
        button_text_color=(220, 220, 230, 255),
        button_padding=14,
        button_font_size=26,
        button_min_width=220,
    )


def _load_td_module() -> Any:
    """Import and return the tower defense main module."""
    _demo_dir = Path(__file__).resolve().parents[2] / "examples" / "tower_defense"
    added = False
    if str(_demo_dir) not in sys.path:
        sys.path.insert(0, str(_demo_dir))
        added = True
    try:
        import main as td_main  # type: ignore[import-not-found]
        return td_main
    except ImportError:
        return None
    finally:
        if added and str(_demo_dir) in sys.path:
            sys.path.remove(str(_demo_dir))


def golden_td_title() -> None:
    """Exact scene from test_td_title (960x540)."""
    td_main = _load_td_module()
    if td_main is None:
        print("  \u2298 golden td_title (tower_defense not importable)")
        return

    def setup(game: Game) -> None:
        _demo_dir = Path(__file__).resolve().parents[2] / "examples" / "tower_defense"
        game._asset_path = _demo_dir / "assets"
        game.theme = _td_theme()
        game.push(td_main.TitleScene())

    image = _render_mock(setup, tick_count=1, resolution=(960, 540))
    _save(image, "golden_td_title.png", golden_name="td_title")


def golden_td_game_initial() -> None:
    """Exact scene from test_td_game_initial (960x540)."""
    td_main = _load_td_module()
    if td_main is None:
        print("  \u2298 golden td_game_initial (tower_defense not importable)")
        return

    def setup(game: Game) -> None:
        _demo_dir = Path(__file__).resolve().parents[2] / "examples" / "tower_defense"
        game._asset_path = _demo_dir / "assets"
        game.theme = _td_theme()
        game.push(td_main.GameScene())

    image = _render_mock(setup, tick_count=1, resolution=(960, 540))
    _save(image, "golden_td_game_initial.png", golden_name="td_game_initial")


def golden_td_game_tower_placed() -> None:
    """Exact scene from test_td_game_tower_placed (960x540)."""
    td_main = _load_td_module()
    if td_main is None:
        print("  \u2298 golden td_game_tower_placed (tower_defense not importable)")
        return

    def setup(game: Game) -> None:
        _demo_dir = Path(__file__).resolve().parents[2] / "examples" / "tower_defense"
        game._asset_path = _demo_dir / "assets"
        game.theme = _td_theme()
        scene = td_main.GameScene()
        game.push(scene)

        # Tick once so the scene is fully initialised.
        game.tick(dt=1.0 / 60.0)

        # Enter placement mode for the Basic tower (cost 50).
        scene._placing_tower_def = td_main.TOWER_DEFS[0]

        # Place at the first tower slot (col=4, row=4).
        slot_col, slot_row = td_main.TOWER_SLOTS[0]
        world_x = slot_col * td_main.TILE_SIZE + td_main.TILE_SIZE / 2
        world_y = slot_row * td_main.TILE_SIZE + td_main.TILE_SIZE / 2
        placed = scene._try_place_tower(world_x, world_y)
        assert placed, "Tower placement at slot (4, 4) should succeed"

    image = _render_mock(setup, tick_count=1, resolution=(960, 540))
    _save(image, "golden_td_game_tower_placed.png", golden_name="td_game_tower_placed")


# ======================================================================
# Main
# ======================================================================

_PREVIEWS: list[tuple[str, Callable[[], None]]] = [
    ("Main Menu", preview_main_menu),
    ("Button States", preview_button_states),
    ("Progress Bars", preview_progress_bars),
    ("List Widget", preview_list),
    ("Grid Widget", preview_grid),
    ("TextBox Widget", preview_textbox),
    ("TabGroup Widget", preview_tabgroup),
    ("DataTable Widget", preview_datatable),
    ("Tooltip Widget", preview_tooltip),
    ("Battle Title", preview_battle_title),
    ("TD Title", preview_td_title),
    ("TD Game Initial", preview_td_game),
]

_GOLDENS: list[tuple[str, Callable[[], None]]] = [
    # test_ui_screenshots.py
    ("ui_main_menu", golden_ui_main_menu),
    ("ui_horizontal_buttons", golden_ui_horizontal_buttons),
    ("ui_styled_label", golden_ui_styled_label),
    ("ui_nested_panels", golden_ui_nested_panels),
    # test_widget_screenshots.py
    ("widget_progress_bar", golden_widget_progress_bar),
    ("widget_textbox_instant", golden_widget_textbox_instant),
    ("widget_list_with_selection", golden_widget_list_with_selection),
    ("widget_grid_with_cells", golden_widget_grid_with_cells),
    ("widget_tooltip_visible", golden_widget_tooltip_visible),
    ("widget_tabgroup", golden_widget_tabgroup),
    ("widget_datatable", golden_widget_datatable),
    ("widget_combined_dialog", golden_widget_combined_dialog),
    # test_stage13_screenshots.py
    ("stage13_message_screen", golden_stage13_message_screen),
    ("stage13_choice_screen", golden_stage13_choice_screen),
    ("stage13_confirm_dialog", golden_stage13_confirm_dialog),
    ("stage13_save_load_screen", golden_stage13_save_load_screen),
    ("stage13_hud_bar", golden_stage13_hud_bar),
    ("stage13_menu_scene", golden_stage13_menu_scene),
    # test_tower_defense_screenshots.py
    ("td_title", golden_td_title),
    ("td_game_initial", golden_td_game_initial),
    ("td_game_tower_placed", golden_td_game_tower_placed),
]


def main() -> None:
    global _write_golden  # noqa: PLW0603

    if "--golden" in sys.argv:
        _write_golden = True

    _ensure_dirs()

    out = _PREVIEWS_DIR
    print(f"Generating UI previews (MockBackend + PIL) \u2192 {out}/")
    if _write_golden:
        print(f"Also populating golden directory \u2192 {_GOLDEN_DIR}/")
    print()

    failed: list[str] = []

    # --- Always generate gallery-style previews ---
    print("=== Gallery previews ===")
    for name, func in _PREVIEWS:
        try:
            func()
        except Exception as exc:
            import traceback

            print(f"  \u2717 {name}: {exc}")
            traceback.print_exc()
            failed.append(name)

    # --- Generate golden-targeted scenes when requested ---
    if _write_golden:
        print()
        print("=== Golden screenshots ===")
        for name, func in _GOLDENS:
            try:
                func()
            except Exception as exc:
                import traceback

                print(f"  \u2717 golden {name}: {exc}")
                traceback.print_exc()
                failed.append(f"golden:{name}")

    print()
    total = len(_PREVIEWS) + (len(_GOLDENS) if _write_golden else 0)
    ok = total - len(failed)
    print(f"Done: {ok}/{total} images generated.")
    if _write_golden:
        print(f"  Previews: {out}/")
        print(f"  Goldens:  {_GOLDEN_DIR}/")
    else:
        print(f"  Output: {out}/")
        print("  (pass --golden to also populate tests/screenshot/golden/)")
    if failed:
        print(f"Failed: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
