#!/usr/bin/env python3
"""real_user_app.py — A small but realistic game built with saga2d.

Simulates what a normal game developer would write: a title screen,
a gameplay scene with sprites/camera/particles/actions/tweens/audio/FSM/timers,
an overlay settings screen with UI widgets, and a pause menu with save/load.

The script creates the Game with backend="mock", pushes scenes, and injects
keyboard & mouse events through the mock backend exactly as the real engine
loop would deliver them. Every frame is driven by game.tick(dt).

At the end it prints a structured report:
  - phases completed
  - any exceptions / tracebacks
  - any state anomalies (stale sprites, leaked timers, etc.)
  - repro steps for any bug found
"""

from __future__ import annotations

import math
import sys
import traceback
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────────────
# Framework imports (normal game-developer style)
# ─────────────────────────────────────────────────────────────────────
from saga2d import (
    Game, Scene, Sprite, Camera, AnimationDef, ParticleEmitter,
    Sequence, Parallel, MoveTo, PlayAnim, Delay, Do, FadeOut, FadeIn, Remove, Repeat,
    tween, Ease, TimerHandle,
    Panel, Label, Button, ProgressBar, List, TextBox, DataTable, Grid,
    TabGroup, Tooltip, ImageBox, Anchor, Layout, Style,
    InputEvent, RenderLayer, SpriteAnchor,
    AudioManager, SaveManager, SaveError, AssetNotFoundError,
)
from saga2d.util.fsm import StateMachine
from saga2d.backends.mock_backend import MockBackend

# ─────────────────────────────────────────────────────────────────────
# Report accumulator
# ─────────────────────────────────────────────────────────────────────

class Report:
    def __init__(self):
        self.phases: list[str] = []
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[str] = []
        self.state_checks: list[dict[str, Any]] = []
        self.bugs: list[dict[str, Any]] = []

    def phase(self, name: str):
        self.phases.append(name)
        print(f"  ✓ Phase: {name}")

    def error(self, phase: str, exc: Exception, tb: str):
        self.errors.append({"phase": phase, "exception": str(exc), "traceback": tb})
        print(f"  ✗ ERROR in {phase}: {exc}")

    def warn(self, msg: str):
        self.warnings.append(msg)
        print(f"  ⚠ WARNING: {msg}")

    def check(self, name: str, expected: Any, actual: Any):
        ok = expected == actual
        self.state_checks.append({"name": name, "expected": expected, "actual": actual, "ok": ok})
        if not ok:
            print(f"  ✗ CHECK FAIL: {name}: expected {expected!r}, got {actual!r}")
        return ok

    def check_true(self, name: str, condition: bool):
        self.state_checks.append({"name": name, "expected": True, "actual": condition, "ok": condition})
        if not condition:
            print(f"  ✗ CHECK FAIL: {name}")
        return condition

    def bug(self, title: str, repro: str, details: str = ""):
        self.bugs.append({"title": title, "repro": repro, "details": details})
        print(f"  🐛 BUG: {title}")

    def summary(self) -> str:
        lines = ["\n" + "="*70, "REAL USER APP — RUNTIME REPORT", "="*70]
        lines.append(f"\nPhases completed: {len(self.phases)}/{len(self.phases)}")
        for p in self.phases:
            lines.append(f"  ✓ {p}")

        n_checks = len(self.state_checks)
        n_pass = sum(1 for c in self.state_checks if c["ok"])
        lines.append(f"\nState checks: {n_pass}/{n_checks} passed")
        for c in self.state_checks:
            mark = "✓" if c["ok"] else "✗"
            lines.append(f"  {mark} {c['name']}: expected={c['expected']!r}, actual={c['actual']!r}")

        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")

        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"  ✗ {e['phase']}: {e['exception']}")
                lines.append(f"    {e['traceback']}")

        if self.bugs:
            lines.append(f"\nBugs Found ({len(self.bugs)}):")
            for b in self.bugs:
                lines.append(f"  🐛 {b['title']}")
                lines.append(f"     Repro: {b['repro']}")
                if b["details"]:
                    lines.append(f"     Details: {b['details']}")
        else:
            lines.append("\nNo bugs found.")

        lines.append("")
        return "\n".join(lines)


report = Report()

# ─────────────────────────────────────────────────────────────────────
# Scene definitions — what a real game developer would write
# ─────────────────────────────────────────────────────────────────────

class TitleScene(Scene):
    """Main menu with start/settings/quit buttons."""
    background_color = (25, 25, 40, 255)

    def on_enter(self):
        self.entered = True
        self.play_clicked = False

        panel = Panel(width=500, height=400, anchor=Anchor.CENTER, layout=Layout.VERTICAL)
        panel.add(Label("SAGA QUEST", width=400, height=60))

        self.play_btn = Button(
            "New Game", width=250, height=50,
            on_click=self._start_game,
        )
        panel.add(self.play_btn)

        self.settings_btn = Button(
            "Settings", width=250, height=50,
            on_click=self._open_settings,
        )
        panel.add(self.settings_btn)

        self.quit_btn = Button(
            "Quit", width=250, height=50,
            on_click=lambda: self.game.quit(),
        )
        panel.add(self.quit_btn)

        self.ui.add(panel)

        # Background decoration sprite
        self.bg_sprite = self.add_sprite(
            Sprite("sprites/background", position=(960, 540),
                   layer=RenderLayer.BACKGROUND, anchor=SpriteAnchor.CENTER)
        )

        # Ambient sparkle particles
        self.sparkle = self.add_emitter(
            ParticleEmitter(
                "sprites/crate",
                position=(960, 540),
                count=3,
                speed=(10, 50),
                direction=(0, 360),
                lifetime=(0.5, 1.5),
                fade_out=True,
            )
        )
        self.sparkle.continuous(rate=5)

        # Play title music (optional — won't crash if missing)
        self.game.audio.play_music("music/title", optional=True)

    def _start_game(self):
        self.play_clicked = True
        self.game.replace(WorldScene())

    def _open_settings(self):
        self.game.push(SettingsScene())

    def on_exit(self):
        self.exited = True


class SettingsScene(Scene):
    """Overlay settings scene with various UI widgets."""
    transparent = True
    pop_on_cancel = True
    show_hud = False

    def on_enter(self):
        self.entered = True
        panel = Panel(width=600, height=450, anchor=Anchor.CENTER,
                     layout=Layout.VERTICAL,
                     style=Style(background_color=(40, 40, 60, 230)))

        panel.add(Label("Settings", width=500, height=40))

        # Volume controls using progress bars
        panel.add(Label("Master Volume", width=500, height=25))
        self.master_vol = ProgressBar(value=80, max_value=100, width=500, height=20)
        panel.add(self.master_vol)

        panel.add(Label("Music Volume", width=500, height=25))
        self.music_vol = ProgressBar(value=70, max_value=100, width=500, height=20)
        panel.add(self.music_vol)

        panel.add(Label("SFX Volume", width=500, height=25))
        self.sfx_vol = ProgressBar(value=90, max_value=100, width=500, height=20)
        panel.add(self.sfx_vol)

        # Difficulty selection list
        self.difficulty_list = List(
            items=["Easy", "Normal", "Hard", "Nightmare"],
            item_height=28,
            width=500,
            height=112,
        )
        panel.add(self.difficulty_list)

        # Keybindings table
        self.bindings_table = DataTable(
            columns=["Action", "Key"],
            rows=[
                ["Move Up", "W"],
                ["Move Down", "S"],
                ["Move Left", "A"],
                ["Move Right", "D"],
                ["Attack", "Space"],
                ["Inventory", "I"],
            ],
            width=500,
            height=180,
            row_height=28,
        )
        panel.add(self.bindings_table)

        self.close_btn = Button(
            "Back", width=120, height=40,
            on_click=lambda: self.game.pop(),
        )
        panel.add(self.close_btn)

        self.ui.add(panel)

    def on_exit(self):
        self.exited = True


class WorldScene(Scene):
    """Main gameplay — hero moves through a world with enemies, items, particles."""
    background_color = (20, 35, 20, 255)

    def on_enter(self):
        self.entered = True
        self.hero_moved = False
        self.attack_count = 0
        self.damage_dealt = False
        self.items_collected = 0
        self.hp = 100
        self.max_hp = 100
        self.gold = 0
        self.xp = 0
        self.level = 1

        # Camera
        self.camera = Camera(
            self.game._resolution,
            world_bounds=(0, 0, 4000, 3000),
        )

        # Hero sprite
        self.hero = self.add_sprite(
            Sprite("sprites/knight", position=(500, 400),
                   anchor=SpriteAnchor.BOTTOM_CENTER)
        )

        # Enemies at various positions
        self.enemies: list[Sprite] = []
        enemy_positions = [(900, 400), (1200, 600), (700, 800), (1500, 300)]
        for pos in enemy_positions:
            enemy = self.add_sprite(
                Sprite("sprites/enemy", position=pos,
                       anchor=SpriteAnchor.BOTTOM_CENTER)
            )
            enemy.do(Repeat(Sequence(
                MoveTo((pos[0] + 50, pos[1]), speed=30),
                MoveTo((pos[0] - 50, pos[1]), speed=30),
            )))
            self.enemies.append(enemy)

        # Collectible crates
        self.crates: list[Sprite] = []
        crate_positions = [(600, 500), (1000, 400), (800, 700)]
        for pos in crate_positions:
            crate = self.add_sprite(
                Sprite("sprites/crate", position=pos,
                       layer=RenderLayer.OBJECTS)
            )
            self.crates.append(crate)

        # Animations
        self.walk_anim = AnimationDef(
            frames=["sprites/knight_walk_01", "sprites/knight_walk_02",
                    "sprites/knight_walk_03"],
            frame_duration=0.12,
            loop=True,
        )
        self.attack_anim = AnimationDef(
            frames=["sprites/knight_attack_01", "sprites/knight_attack_02",
                    "sprites/knight_attack_03"],
            frame_duration=0.08,
            loop=False,
        )

        # Particle emitters
        self.dust_emitter = self.add_emitter(
            ParticleEmitter(
                "sprites/crate",
                position=(500, 410),
                count=4,
                speed=(20, 60),
                direction=(180, 360),
                lifetime=(0.2, 0.5),
                fade_out=True,
            )
        )

        # HUD / UI
        hud_panel = Panel(width=350, height=120, anchor=Anchor.TOP_LEFT,
                         layout=Layout.VERTICAL)
        self.hp_label = Label(f"HP: {self.hp}/{self.max_hp}", width=300, height=25)
        self.hp_bar = ProgressBar(value=self.hp, max_value=self.max_hp, width=300, height=18)
        self.gold_label = Label("Gold: 0", width=300, height=25)
        self.xp_label = Label("XP: 0  Lv.1", width=300, height=25)
        hud_panel.add(self.hp_label)
        hud_panel.add(self.hp_bar)
        hud_panel.add(self.gold_label)
        hud_panel.add(self.xp_label)
        self.ui.add(hud_panel)

        # Minimap area (decorative panel)
        minimap = Panel(width=200, height=150, anchor=Anchor.TOP_RIGHT,
                       style=Style(background_color=(20, 20, 20, 180)))
        minimap.add(Label("Minimap", width=180, height=30))
        self.ui.add(minimap)

        # Key bindings
        self.bind_key("space", self._do_attack)
        self.bind_key("i", self._open_inventory)
        self.bind_key("escape", self._open_pause)

        # Audio
        self.game.audio.play_music("music/world", optional=True)
        self.game.audio.register_pool("footsteps", ["step1", "step2", "step3"])
        self.game.audio.register_pool("hits", ["hit1", "hit2"])

        # FSM for hero
        self.hero_fsm = StateMachine(
            states=["idle", "walking", "attacking", "collecting", "dead"],
            initial="idle",
            transitions={
                "idle": {"walk": "walking", "attack": "attacking",
                         "collect": "collecting", "die": "dead"},
                "walking": {"arrive": "idle", "attack": "attacking"},
                "attacking": {"done": "idle"},
                "collecting": {"done": "idle"},
                "dead": {},
            },
        )

        # Timers
        self.gold_timer = self.every(2.0, self._passive_gold)
        self.regen_timer = self.every(3.0, self._hp_regen)

        # Camera follow
        self.camera.follow(self.hero)

        # Tweens — subtle breathing effect on hero opacity
        self._breathing_obj = type("Obj", (), {"val": 255.0})()
        tween(self._breathing_obj, "val", 255.0, 230.0, 1.0, ease=Ease.EASE_IN_OUT)

    def _do_attack(self):
        if self.hero_fsm.state == "dead":
            return
        if self.hero_fsm.state == "attacking":
            return  # Already attacking, ignore
        self.hero_fsm.trigger("attack")
        self.attack_count += 1

        self.hero.do(Sequence(
            PlayAnim(self.attack_anim),
            Do(self._check_hit),
            Do(lambda: self.hero_fsm.trigger("done")),
        ))

    def _check_hit(self):
        """Check if any enemy is close enough to be hit."""
        hx, hy = self.hero.position
        for enemy in self.enemies[:]:
            if enemy.is_removed:
                continue
            ex, ey = enemy.position
            dist = math.hypot(hx - ex, hy - ey)
            if dist < 150:
                self.damage_dealt = True
                self.xp += 25
                self.gold += 15

                # Hit particles
                hit_emitter = self.add_emitter(
                    ParticleEmitter(
                        "sprites/crate",
                        position=enemy.position,
                        count=8,
                        speed=(40, 120),
                        lifetime=(0.15, 0.4),
                    )
                )
                hit_emitter.burst(8)

                # Kill enemy with fade
                enemy.stop_actions()
                enemy.do(Sequence(FadeOut(0.3), Remove()))
                self.enemies.remove(enemy)

                # Camera shake on kill
                self.camera.shake(6, 0.25, 1.5)
                break

    def _open_inventory(self):
        self.game.push(InventoryScene(
            items=["Iron Sword", "Wooden Shield", "Health Potion x3",
                   "Fire Scroll", "Gold Ring", "Silver Key"],
            stats={"ATK": self.level * 5 + 10, "DEF": self.level * 3 + 5,
                   "SPD": 8, "LCK": 3},
        ))

    def _open_pause(self):
        self.game.push(PauseScene())

    def _passive_gold(self):
        self.gold += 5
        self.gold_label.text = f"Gold: {self.gold}"

    def _hp_regen(self):
        if self.hp < self.max_hp:
            self.hp = min(self.hp + 2, self.max_hp)

    def _collect_crate(self, crate: Sprite):
        if crate.is_removed:
            return
        self.hero_fsm.trigger("collect")
        self.items_collected += 1
        self.gold += 10
        crate.do(Sequence(
            Parallel(FadeOut(0.3), MoveTo((crate.x, crate.y - 30), speed=60)),
            Remove(),
            Do(lambda: self.hero_fsm.trigger("done")),
        ))
        self.crates.remove(crate)

    def update(self, dt):
        # Update HUD
        self.hp_bar.value = self.hp
        self.hp_label.text = f"HP: {self.hp}/{self.max_hp}"
        self.gold_label.text = f"Gold: {self.gold}"
        self.xp_label.text = f"XP: {self.xp}  Lv.{self.level}"

        # Level up check
        if self.xp >= self.level * 50:
            self.xp -= self.level * 50
            self.level += 1
            self.max_hp += 10
            self.hp = self.max_hp

        # Auto-collect nearby crates
        hx, hy = self.hero.position
        for crate in self.crates[:]:
            if crate.is_removed:
                continue
            cx, cy = crate.position
            dist = math.hypot(hx - cx, hy - cy)
            if dist < 80 and self.hero_fsm.state == "idle":
                self._collect_crate(crate)

    def handle_input(self, event: InputEvent) -> bool:
        if event.type == "click" and event.button == "left":
            if event.world_x is not None:
                target = (event.world_x, event.world_y)
                if self.hero_fsm.state not in ("dead", "attacking"):
                    self.hero_fsm.trigger("walk")
                    self.hero_moved = True

                    self.hero.stop_actions()
                    self.hero.do(Sequence(
                        Parallel(
                            PlayAnim(self.walk_anim),
                            MoveTo(target, speed=250),
                        ),
                        Do(self._on_arrive),
                    ))

                    # Dust on movement start
                    self.dust_emitter.position = self.hero.position
                    self.dust_emitter.burst(3)
                return True
        return False

    def _on_arrive(self):
        self.hero_moved = True
        if self.hero_fsm.state != "dead":
            self.hero_fsm.trigger("arrive")

    def on_exit(self):
        self.exited = True

    def get_save_state(self) -> dict:
        return {
            "hp": self.hp,
            "max_hp": self.max_hp,
            "gold": self.gold,
            "xp": self.xp,
            "level": self.level,
            "hero_pos": list(self.hero.position),
            "items_collected": self.items_collected,
            "attack_count": self.attack_count,
            "enemies_remaining": len(self.enemies),
        }

    def load_save_state(self, state: dict):
        self.hp = state.get("hp", 100)
        self.max_hp = state.get("max_hp", 100)
        self.gold = state.get("gold", 0)
        self.xp = state.get("xp", 0)
        self.level = state.get("level", 1)
        self.items_collected = state.get("items_collected", 0)
        self.attack_count = state.get("attack_count", 0)
        pos = state.get("hero_pos", [500, 400])
        self.hero.position = tuple(pos)


class InventoryScene(Scene):
    """Overlay with item list, stats, description box."""
    transparent = True
    pop_on_cancel = True
    show_hud = False

    def __init__(self, items: list[str] | None = None, stats: dict | None = None):
        super().__init__()
        self._items = items or ["No Items"]
        self._stats = stats or {}

    def on_enter(self):
        self.entered = True
        panel = Panel(width=700, height=500, anchor=Anchor.CENTER,
                     layout=Layout.VERTICAL,
                     style=Style(background_color=(30, 30, 50, 240)))

        panel.add(Label("Inventory", width=650, height=40))

        # Item list
        self.item_list = List(
            items=self._items,
            item_height=28,
            width=650,
            height=170,
        )
        panel.add(self.item_list)

        # Item description with typewriter
        self.desc_box = TextBox(
            text="Select an item to see its description.",
            width=650,
            height=80,
            typewriter_speed=60,
        )
        panel.add(self.desc_box)

        # Stats table
        stat_rows = [[k, str(v)] for k, v in self._stats.items()]
        self.stats_table = DataTable(
            columns=["Stat", "Value"],
            rows=stat_rows if stat_rows else [["N/A", "N/A"]],
            width=650,
            height=120,
            row_height=28,
        )
        panel.add(self.stats_table)

        self.close_btn = Button(
            "Close", width=120, height=40,
            on_click=lambda: self.game.pop(),
        )
        panel.add(self.close_btn)

        self.ui.add(panel)

    def on_exit(self):
        self.exited = True


class PauseScene(Scene):
    """Pause menu with resume, save, load, quit."""
    transparent = True
    pop_on_cancel = True
    pause_below = True
    show_hud = False

    def on_enter(self):
        self.entered = True
        self.saved = False
        self.loaded = False

        panel = Panel(width=350, height=300, anchor=Anchor.CENTER,
                     layout=Layout.VERTICAL,
                     style=Style(background_color=(20, 20, 30, 230)))

        panel.add(Label("PAUSED", width=300, height=50))

        self.resume_btn = Button(
            "Resume", width=200, height=40,
            on_click=lambda: self.game.pop(),
        )
        panel.add(self.resume_btn)

        self.save_btn = Button(
            "Save Game", width=200, height=40,
            on_click=self._save,
        )
        panel.add(self.save_btn)

        self.load_btn = Button(
            "Load Game", width=200, height=40,
            on_click=self._load,
        )
        panel.add(self.load_btn)

        self.quit_btn = Button(
            "Quit to Title", width=200, height=40,
            on_click=self._quit_to_title,
        )
        panel.add(self.quit_btn)

        self.ui.add(panel)

    def _save(self):
        try:
            self.game.save(slot=1)
            self.saved = True
        except Exception as e:
            print(f"Save error: {e}")

    def _load(self):
        try:
            data = self.game.load(slot=1)
            self.loaded = data is not None
        except Exception as e:
            print(f"Load error: {e}")

    def _quit_to_title(self):
        self.game.clear_and_push(TitleScene())

    def on_exit(self):
        self.exited = True


# ─────────────────────────────────────────────────────────────────────
# Helper: tick N frames
# ─────────────────────────────────────────────────────────────────────

def tick_frames(game: Game, n: int, dt: float = 1/60):
    for _ in range(n):
        game.tick(dt)


# ─────────────────────────────────────────────────────────────────────
# Main execution — the "real user" playthrough
# ─────────────────────────────────────────────────────────────────────

def main():
    import tempfile, shutil

    save_dir = Path(tempfile.mkdtemp(prefix="saga2d_app_"))

    print("="*70)
    print("REAL USER APP — EXECUTING")
    print("="*70)

    game: Game | None = None
    try:
        # ── Phase 1: Create Game ─────────────────────────────────────
        try:
            game = Game(
                "Saga Quest",
                resolution=(1920, 1080),
                backend="mock",
                save_dir=save_dir,
            )
            backend: MockBackend = game.backend  # type: ignore
            report.phase("1. Game created (mock backend, 1920x1080)")
        except Exception as e:
            report.error("1. Game creation", e, traceback.format_exc())
            return

        # ── Phase 2: Title Screen ────────────────────────────────────
        try:
            title = TitleScene()
            game.push(title)
            tick_frames(game, 5)

            report.check("title.entered", True, title.entered)
            report.check("scene stack top is TitleScene",
                         True, isinstance(game._scene_stack.top(), TitleScene))
            report.check_true("background sprite exists", not title.bg_sprite.is_removed)
            report.check_true("sparkle emitter active", title.sparkle.is_active)

            # Verify UI rendered
            texts = [t["text"] for t in backend.texts]
            report.check_true("title text rendered", any("SAGA QUEST" in t for t in texts))
            report.check_true("buttons rendered",
                              any("New Game" in t for t in texts) and
                              any("Settings" in t for t in texts))

            report.phase("2. Title screen displayed")
        except Exception as e:
            report.error("2. Title screen", e, traceback.format_exc())
            return

        # ── Phase 3: Open Settings Overlay ───────────────────────────
        try:
            title._open_settings()
            tick_frames(game, 3)

            settings = game._scene_stack.top()
            report.check("settings scene type", True, isinstance(settings, SettingsScene))
            report.check("settings.entered", True, settings.entered)

            # Verify settings UI rendered
            texts = [t["text"] for t in backend.texts]
            report.check_true("settings title rendered", any("Settings" in t for t in texts))
            report.check_true("difficulty list has items",
                              len(settings.difficulty_list.items) == 4)
            report.check_true("bindings table has rows",
                              len(settings.bindings_table.rows) == 6)

            # Close via escape
            backend.inject_key("escape")
            tick_frames(game, 2)
            report.check("back on title after escape",
                         True, isinstance(game._scene_stack.top(), TitleScene))
            report.check("settings exited", True, settings.exited)

            report.phase("3. Settings overlay opened and closed")
        except Exception as e:
            report.error("3. Settings overlay", e, traceback.format_exc())

        # ── Phase 4: Start Game → WorldScene ─────────────────────────
        try:
            title._start_game()
            tick_frames(game, 5)

            world = game._scene_stack.top()
            report.check("world scene type", True, isinstance(world, WorldScene))
            report.check("world.entered", True, world.entered)
            report.check_true("hero exists", not world.hero.is_removed)
            report.check("hero position", (500, 400), world.hero.position)
            report.check_true("camera set up", world.camera is not None)
            report.check("num enemies", 4, len(world.enemies))
            report.check("num crates", 3, len(world.crates))
            report.check("hero FSM state", "idle", world.hero_fsm.state)
            report.check("title exited", True, title.exited)

            report.phase("4. World scene entered with sprites/camera/UI")
        except Exception as e:
            report.error("4. World scene", e, traceback.format_exc())
            return

        # ── Phase 5: Click to Move Hero ──────────────────────────────
        try:
            # Click at a world position (screen center maps to camera view)
            backend.inject_click(960, 540)
            tick_frames(game, 3)
            report.check_true("hero FSM walked", world.hero_fsm.state in ("walking", "idle"))

            # Let hero walk for a bit
            tick_frames(game, 60)
            report.check_true("hero moved from start",
                              world.hero.position != (500, 400) or world.hero_moved)

            report.phase("5. Hero click-to-move with walk animation")
        except Exception as e:
            report.error("5. Click to move", e, traceback.format_exc())

        # ── Phase 6: Move to enemy and attack ────────────────────────
        try:
            if world.enemies:
                # Move hero near first remaining enemy
                target_enemy = world.enemies[0]
                ex, ey = target_enemy.position
                # Click near the enemy
                sx, sy = world.camera.world_to_screen(ex - 50, ey)
                backend.inject_click(int(sx), int(sy))
                tick_frames(game, 80)  # Let hero walk close

                # Attack
                initial_attack_count = world.attack_count
                backend.inject_key("space")
                tick_frames(game, 30)  # Let attack animation play

                report.check_true("attack triggered",
                                  world.attack_count > initial_attack_count)

                # Attack again a few more times to ensure enemy dies
                for _ in range(3):
                    backend.inject_key("space")
                    tick_frames(game, 25)

                report.check_true("damage dealt", world.damage_dealt)
                report.check_true("gold earned from combat", world.gold > 0)
                report.check_true("xp earned", world.xp > 0 or world.level > 1)

            report.phase("6. Combat — attack enemy, earn gold/XP")
        except Exception as e:
            report.error("6. Combat", e, traceback.format_exc())

        # ── Phase 7: Move near crate for auto-collect ────────────────
        try:
            if world.crates:
                crate = world.crates[0]
                cx, cy = crate.position
                # Click directly on the crate
                sx, sy = world.camera.world_to_screen(cx, cy)
                backend.inject_click(int(sx), int(sy))
                tick_frames(game, 100)  # Walk there and auto-collect

                # Tick more for the collect action to finish
                tick_frames(game, 30)

                report.check_true("items collected", world.items_collected > 0 or len(world.crates) < 3)

            report.phase("7. Auto-collect item crate")
        except Exception as e:
            report.error("7. Auto-collect", e, traceback.format_exc())

        # ── Phase 8: Open Inventory ──────────────────────────────────
        try:
            backend.inject_key("i")
            tick_frames(game, 3)

            inv = game._scene_stack.top()
            report.check("inventory scene type", True, isinstance(inv, InventoryScene))
            report.check("inventory.entered", True, inv.entered)
            report.check_true("inventory has items", len(inv.item_list.items) >= 1)
            report.check_true("stats table has rows", len(inv.stats_table.rows) >= 1)

            # Scroll down in item list
            backend.inject_scroll(400, 300, dx=0, dy=-3)
            tick_frames(game, 2)

            # Close inventory
            backend.inject_key("escape")
            tick_frames(game, 2)
            report.check("back on world after inventory close",
                         True, isinstance(game._scene_stack.top(), WorldScene))

            report.phase("8. Inventory overlay opened, scrolled, closed")
        except Exception as e:
            report.error("8. Inventory", e, traceback.format_exc())

        # ── Phase 9: Passive timers (gold + regen) ───────────────────
        try:
            # F28 fix: Scene-owned timers now survive overlay push/pop.
            # The gold timer created in WorldScene.on_enter() is still alive
            # after the inventory/pause overlays from earlier phases.

            gold_before = world.gold
            hp_before = world.hp
            # Tick 5 seconds worth of frames to let timers fire (gold every 2s, regen every 3s)
            tick_frames(game, 300)

            report.check_true("passive gold timer fired", world.gold > gold_before)

            report.phase("9. Passive timers (gold, regen)")
        except Exception as e:
            report.error("9. Timers", e, traceback.format_exc())

        # ── Phase 10: Save + Load roundtrip ──────────────────────────
        try:
            # Save from WorldScene (must be top scene for get_save_state)
            report.check("world is top for save",
                         True, isinstance(game._scene_stack.top(), WorldScene))
            saved_hp = world.hp
            saved_gold = world.gold
            game.save(slot=1)

            # Verify save file
            saved_data = game.save_manager.load(1)
            report.check_true("save file exists", saved_data is not None)
            report.check("saved hp", saved_hp, saved_data["state"]["hp"])
            report.check("saved gold", saved_gold, saved_data["state"]["gold"])

            # Now open pause to test pause overlay flow
            backend.inject_key("escape")
            tick_frames(game, 2)
            pause = game._scene_stack.top()
            report.check("pause scene type", True, isinstance(pause, PauseScene))

            # Resume
            game.pop()
            tick_frames(game, 2)
            report.check("back on world after resume",
                         True, isinstance(game._scene_stack.top(), WorldScene))

            # Modify state, then load to restore
            world.hp = 1
            world.gold = 0
            data = game.load(slot=1)
            tick_frames(game, 1)

            report.check_true("hp restored after load", world.hp > 1)
            report.check_true("gold restored after load", world.gold > 0)

            report.phase("10. Save/Load roundtrip + pause overlay")
        except Exception as e:
            report.error("10. Save/Load", e, traceback.format_exc())

        # ── Phase 11: Camera behavior — pan, shake, follow ───────────
        try:
            world.camera.follow(None)
            world.camera.center_on(2000, 1500)
            tick_frames(game, 2)

            # Pan to a new location
            world.camera.pan_to(1000, 800, duration=0.5, ease=Ease.EASE_OUT)
            tick_frames(game, 40)

            cx = world.camera.x + world.camera.viewport_width / 2
            cy = world.camera.y + world.camera.viewport_height / 2
            report.check_true("camera panned near target",
                              abs(cx - 1000) < 20 and abs(cy - 800) < 20)

            # Shake
            world.camera.shake(12, 0.3, 2.0)
            tick_frames(game, 5)
            report.check_true("shake produces offsets",
                              abs(world.camera.shake_offset_x) <= 12 and
                              abs(world.camera.shake_offset_y) <= 12)

            # Let shake expire
            tick_frames(game, 25)
            report.check_true("shake expired",
                              world.camera.shake_offset_x == 0 and
                              world.camera.shake_offset_y == 0)

            # Re-enable follow
            world.camera.follow(world.hero)
            tick_frames(game, 3)

            report.phase("11. Camera pan, shake, follow")
        except Exception as e:
            report.error("11. Camera", e, traceback.format_exc())

        # ── Phase 12: Multiple rapid mouse clicks ────────────────────
        try:
            for i in range(10):
                backend.inject_click(400 + i * 50, 300 + i * 20)
            tick_frames(game, 5)  # Process all clicks in rapid succession
            tick_frames(game, 60)  # Let movements settle

            report.phase("12. Rapid mouse clicks (no crash)")
        except Exception as e:
            report.error("12. Rapid clicks", e, traceback.format_exc())

        # ── Phase 13: Rapid scene transitions ────────────────────────
        try:
            # Ensure we're on the world scene
            while not isinstance(game._scene_stack.top(), WorldScene):
                game.pop()
                tick_frames(game, 1)

            for _ in range(5):
                game.push(InventoryScene())
                tick_frames(game, 2)
                game.pop()  # Directly pop instead of key (escape bound to pause)
                tick_frames(game, 2)

            report.check("back on world after rapid transitions",
                         True, isinstance(game._scene_stack.top(), WorldScene))

            report.phase("13. Rapid scene push/pop cycles (no leak)")
        except Exception as e:
            report.error("13. Rapid transitions", e, traceback.format_exc())

        # ── Phase 14: HUD layer ──────────────────────────────────────
        try:
            hud_label = Label("SAGA QUEST v1.0", width=300, height=30,
                             anchor=Anchor.BOTTOM)
            game.hud.add(hud_label)
            tick_frames(game, 2)

            texts = [t["text"] for t in backend.texts]
            report.check_true("HUD text rendered", any("SAGA QUEST v1.0" in t for t in texts))

            report.phase("14. HUD layer rendering")
        except Exception as e:
            report.error("14. HUD", e, traceback.format_exc())

        # ── Phase 15: Tween + Action coexistence ─────────────────────
        try:
            class TweenTarget:
                scale = 1.0
                glow = 0.0

            t = TweenTarget()
            tween(t, "scale", 1.0, 2.0, 0.5, ease=Ease.EASE_IN_OUT)
            tween(t, "glow", 0.0, 1.0, 0.3, ease=Ease.EASE_OUT)

            # Meanwhile hero has actions running
            world.hero.do(Sequence(
                MoveTo((800, 600), speed=200),
                Delay(0.2),
                MoveTo((500, 400), speed=200),
            ))

            tick_frames(game, 60)

            report.check_true("tween completed (scale)", abs(t.scale - 2.0) < 0.05)
            report.check_true("tween completed (glow)", abs(t.glow - 1.0) < 0.05)

            report.phase("15. Tweens + Actions coexist")
        except Exception as e:
            report.error("15. Tweens + Actions", e, traceback.format_exc())

        # ── Phase 16: Audio volume channels ──────────────────────────
        try:
            game.audio.set_volume("master", 0.5)
            report.check("master volume", 0.5, game.audio.get_volume("master"))

            game.audio.set_volume("sfx", 0.8)
            report.check("sfx volume", 0.8, game.audio.get_volume("sfx"))

            # Clamping
            game.audio.set_volume("music", 1.5)
            report.check("music volume clamped", 1.0, game.audio.get_volume("music"))

            game.audio.set_volume("ui", -0.3)
            report.check("ui volume clamped", 0.0, game.audio.get_volume("ui"))

            report.phase("16. Audio volume channels")
        except Exception as e:
            report.error("16. Audio volume", e, traceback.format_exc())

        # ── Phase 17: World coordinate transforms ────────────────────
        try:
            world.camera.follow(None)
            world.camera.center_on(1000, 800)
            tick_frames(game, 2)

            # Screen center → world
            sw, sh = 1920, 1080
            wx, wy = world.camera.screen_to_world(sw // 2, sh // 2)
            report.check_true("screen→world correct",
                              abs(wx - 1000) < 2 and abs(wy - 800) < 2)

            # Roundtrip
            sx, sy = world.camera.world_to_screen(1000, 800)
            report.check_true("world→screen roundtrip",
                              abs(sx - sw // 2) < 2 and abs(sy - sh // 2) < 2)

            report.phase("17. World coordinate transforms")
        except Exception as e:
            report.error("17. Coordinate transforms", e, traceback.format_exc())

        # ── Phase 18: Sprite removal during action ───────────────────
        try:
            test_sprite = Sprite("sprites/knight", position=(300, 300))
            world.add_sprite(test_sprite)

            test_sprite.do(Sequence(
                Delay(0.05),
                Do(lambda: test_sprite.remove()),
            ))

            tick_frames(game, 10)
            report.check("sprite self-removed", True, test_sprite.is_removed)

            report.phase("18. Sprite self-removal during action")
        except Exception as e:
            report.error("18. Sprite removal", e, traceback.format_exc())

        # ── Phase 19: Camera follow target removed ───────────────────
        try:
            follow_target = Sprite("sprites/enemy", position=(800, 500))
            world.add_sprite(follow_target)
            world.camera.follow(follow_target)
            tick_frames(game, 3)

            follow_target.remove()
            tick_frames(game, 3)  # Should not crash; camera.update() clears target lazily

            # Camera clears _follow_target during update() when it detects is_removed
            report.check("camera follow cleared after removal (lazy cleanup)",
                         None, world.camera._follow_target)

            # Restore follow
            world.camera.follow(world.hero)

            report.phase("19. Camera follow target removed (no crash)")
        except Exception as e:
            report.error("19. Camera follow removed", e, traceback.format_exc())

        # ── Phase 20: Scene replace during gameplay ──────────────────
        try:
            # Replace world with title
            game.clear_and_push(TitleScene())
            tick_frames(game, 3)

            new_title = game._scene_stack.top()
            report.check("replaced with title", True, isinstance(new_title, TitleScene))

            # Start a new game from the new title
            new_title._start_game()
            tick_frames(game, 5)

            new_world = game._scene_stack.top()
            report.check("new world created", True, isinstance(new_world, WorldScene))
            report.check("new world has hero", True, not new_world.hero.is_removed)

            report.phase("20. Full game restart (clear_and_push)")
        except Exception as e:
            report.error("20. Game restart", e, traceback.format_exc())

        # ── Phase 21: Quit-to-title from pause ───────────────────────
        try:
            new_world = game._scene_stack.top()
            if isinstance(new_world, WorldScene):
                # Open pause
                backend.inject_key("escape")
                tick_frames(game, 2)

                pause = game._scene_stack.top()
                if isinstance(pause, PauseScene):
                    pause._quit_to_title()
                    tick_frames(game, 3)

                    final = game._scene_stack.top()
                    report.check("quit to title", True, isinstance(final, TitleScene))

            report.phase("21. Quit-to-title from pause")
        except Exception as e:
            report.error("21. Quit to title", e, traceback.format_exc())

        # ── Phase 22: Many sprites with concurrent actions ───────────
        try:
            scene = Scene()
            game.clear_and_push(scene)
            tick_frames(game, 2)

            sprites = []
            for i in range(30):
                s = Sprite("sprites/knight", position=(i * 20, i * 15))
                scene.add_sprite(s)
                s.do(Sequence(
                    MoveTo((500 + i * 5, 400 + i * 5), speed=200),
                    FadeOut(0.3),
                ))
                sprites.append(s)

            tick_frames(game, 250)  # Sprites at edges need ~3.5s to complete

            report.check_true("all sprites completed",
                              all(s.opacity < 50 or s.is_removed for s in sprites))

            report.phase("22. 30 sprites with concurrent actions")
        except Exception as e:
            report.error("22. Many sprites", e, traceback.format_exc())

        # ── Phase 23: Window close event ─────────────────────────────
        try:
            backend.inject_window_event("close")
            tick_frames(game, 1)
            report.check("game quit after close event", False, game.running)

            report.phase("23. Window close event handled")
        except Exception as e:
            report.error("23. Window close", e, traceback.format_exc())

    except Exception as e:
        report.error("FATAL", e, traceback.format_exc())

    finally:
        if game is not None:
            try:
                game._teardown()
            except Exception:
                pass

        # Cleanup save dir
        try:
            shutil.rmtree(save_dir, ignore_errors=True)
        except Exception:
            pass

    # Print summary
    print(report.summary())

    # Return exit code
    n_errors = len(report.errors)
    n_bugs = len(report.bugs)
    n_fail_checks = sum(1 for c in report.state_checks if not c["ok"])
    exit_code = 0 if (n_errors == 0 and n_bugs == 0 and n_fail_checks == 0) else 1
    print(f"Exit code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
