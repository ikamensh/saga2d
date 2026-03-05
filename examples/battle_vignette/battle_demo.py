"""Playable tactical battle — turn-based combat on an 8x6 grid.

Run from the project root::

    python examples/battle_vignette/battle_demo.py

Controls:
    PLAYER_SELECT  — Left-click a warrior to select it.
    PLAYER_MOVE    — Left-click a blue cell to move, or the warrior's own
                     cell to stay.  Right-click / Escape to cancel selection.
    PLAYER_ATTACK  — Left-click a red-highlighted skeleton to attack, or
                     click elsewhere / press Escape to skip the attack.
    End Turn       — Click the "End Turn" button (or press E) to finish
                     the player phase and start the AI turn.
    Escape         — Cancel current selection / skip attack / quit on title.

The demo places 4 warriors (left) vs 4 skeletons (right) on a procedurally
generated terrain grid.  After all player warriors have acted (or the player
clicks End Turn), the AI moves and attacks with each skeleton sequentially.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from saga2d import (  # noqa: E402
    Anchor,
    AssetManager,
    Button,
    Camera,
    Do,
    Game,
    InputEvent,
    Label,
    Layout,
    MoveTo,
    Parallel,
    Panel,
    PlayAnim,
    RenderLayer,
    Scene,
    Sequence,
    Sprite,
    SpriteAnchor,
    StateMachine,
    Style,
    tween,
)

from examples.battle_vignette.battle_ai import BattleAI  # noqa: E402
from examples.battle_vignette.battle_grid import (  # noqa: E402
    TILE_SIZE,
    SquareGrid,
)
from examples.battle_vignette.battle_unit import (  # noqa: E402
    MOVE_SPEED,
    BaseUnit,
    SkeletonUnit,
    WarriorUnit,
)

# ======================================================================
# Constants
# ======================================================================

SCREEN_W, SCREEN_H = 1920, 1080

# Grid placement — centred on screen with some vertical padding
GRID_COLS, GRID_ROWS = 8, 6
GRID_ORIGIN_X = (SCREEN_W - GRID_COLS * TILE_SIZE) / 2
GRID_ORIGIN_Y = (SCREEN_H - GRID_ROWS * TILE_SIZE) / 2

# FSM states
S_PLAYER_SELECT = "player_select"
S_PLAYER_MOVE = "player_move"
S_PLAYER_ATTACK = "player_attack"
S_UNIT_ACTING = "unit_acting"
S_AI_TURN = "ai_turn"
S_GAME_OVER = "game_over"

# FSM events
E_SELECT = "select"
E_MOVE = "move"
E_ATTACK = "attack"
E_SKIP = "skip"
E_ACTION_START = "action_start"
E_ACTION_DONE = "action_done"
E_END_TURN = "end_turn"
E_AI_START = "ai_start"
E_AI_DONE = "ai_done"
E_WIN = "win"
E_LOSE = "lose"
E_CANCEL = "cancel"


# ======================================================================
# BattleScene
# ======================================================================

class BattleScene(Scene):
    """Playable tactical battle with FSM-driven turn flow."""

    background_color = (50, 60, 40, 255)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        # Core state
        self.warriors: list[WarriorUnit] = []
        self.skeletons: list[SkeletonUnit] = []
        self.all_units: list[BaseUnit] = []
        self.selected_unit: BaseUnit | None = None
        self.acted_this_turn: set[int] = set()  # ids of warriors that acted

        # Highlight cells (recomputed on selection)
        self._move_cells: set[tuple[int, int]] = set()
        self._attack_cells: set[tuple[int, int]] = set()

        # AI
        self._ai = BattleAI()
        self._ai_queue: list[BaseUnit] = []
        self._turn_number = 1

        # Grid
        self.grid = SquareGrid(
            self,
            cols=GRID_COLS,
            rows=GRID_ROWS,
            origin_x=GRID_ORIGIN_X,
            origin_y=GRID_ORIGIN_Y,
            seed=7,
        )

        # Place obstacles before spawning units
        self._place_obstacles()

        self.grid.create_terrain_sprites()

        # Spawn units
        self._spawn_units()

        # Build UI
        self._build_ui()

        # FSM — created last so on_enter callbacks can reference UI
        self.fsm = self._build_fsm()

    def on_exit(self) -> None:
        # Deselect to clean up ring tweens
        self._deselect()

    # ------------------------------------------------------------------
    # Obstacle placement
    # ------------------------------------------------------------------

    def _place_obstacles(self) -> None:
        """Randomly place 3-5 obstacles on the grid.

        Obstacles are rocks that block movement and attacks. They are placed
        in the center columns (3-4) to create tactical chokepoints, avoiding
        unit spawn positions on the edges.
        """
        import random
        rng = random.Random(42)  # Fixed seed for reproducible layout

        # Reserved positions for units
        warrior_positions = {(1, 1), (1, 2), (1, 3), (1, 4)}
        skeleton_positions = {(6, 1), (6, 2), (6, 3), (6, 4)}
        reserved = warrior_positions | skeleton_positions

        # Candidate obstacle positions (center area, avoiding edges)
        candidates = []
        for col in range(2, 6):  # columns 2-5 (center area)
            for row in range(GRID_ROWS):
                if (col, row) not in reserved:
                    candidates.append((col, row))

        # Place 3-5 obstacles randomly
        num_obstacles = rng.randint(3, 5)
        obstacle_positions = rng.sample(candidates, num_obstacles)

        for col, row in obstacle_positions:
            self.grid.place_obstacle(col, row)

    # ------------------------------------------------------------------
    # Unit spawning
    # ------------------------------------------------------------------

    def _spawn_units(self) -> None:
        """Place 4 warriors on the left and 4 skeletons on the right."""
        warrior_positions = [(1, 1), (1, 2), (1, 3), (1, 4)]
        for col, row in warrior_positions:
            w = WarriorUnit.spawn(self, col=col, row=row, grid=self.grid, team="friendly")
            self.warriors.append(w)
            self.all_units.append(w)

        skeleton_positions = [(6, 1), (6, 2), (6, 3), (6, 4)]
        for col, row in skeleton_positions:
            s = SkeletonUnit.spawn(self, col=col, row=row, grid=self.grid, team="enemy")
            self.skeletons.append(s)
            self.all_units.append(s)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Turn indicator — top centre
        self._turn_label = Label(
            "Player Turn",
            font_size=32,
            font="Arial",
            text_color=(255, 255, 255, 255),
            anchor=Anchor.TOP,
            margin=16,
        )
        self.ui.add(self._turn_label)

        # Hint label — below turn indicator
        self._hint_label = Label(
            "Select a warrior",
            font_size=20,
            font="Arial",
            text_color=(200, 200, 200, 200),
            anchor=Anchor.TOP,
            margin=60,
        )
        self.ui.add(self._hint_label)

        # End Turn button — bottom right
        self._end_turn_btn = Button(
            "End Turn",
            on_click=self._on_end_turn_click,
            style=Style(
                font_size=24,
                background_color=(60, 80, 120, 220),
                text_color=(255, 255, 255, 255),
                hover_color=(80, 110, 160, 240),
                press_color=(40, 60, 90, 240),
                padding=16,
            ),
            anchor=Anchor.BOTTOM_RIGHT,
            margin=24,
        )
        self.ui.add(self._end_turn_btn)

        # Game-over overlay (initially hidden)
        self._game_over_title = Label(
            "",
            font_size=72,
            font="Arial",
            text_color=(255, 230, 60, 255),
        )
        self._game_over_sub = Label(
            "Press Enter to restart  |  Escape to quit",
            font_size=24,
            font="Arial",
            text_color=(200, 200, 200, 255),
        )
        self._game_over_panel = Panel(
            layout=Layout.VERTICAL,
            spacing=30,
            anchor=Anchor.CENTER,
            style=Style(
                background_color=(20, 20, 30, 220),
                padding=60,
            ),
            children=[self._game_over_title, self._game_over_sub],
            visible=False,
        )
        self.ui.add(self._game_over_panel)

    # ------------------------------------------------------------------
    # FSM
    # ------------------------------------------------------------------

    def _build_fsm(self) -> StateMachine:
        states = [
            S_PLAYER_SELECT, S_PLAYER_MOVE, S_PLAYER_ATTACK,
            S_UNIT_ACTING, S_AI_TURN, S_GAME_OVER,
        ]
        transitions = {
            S_PLAYER_SELECT: {
                E_SELECT: S_PLAYER_MOVE,
                E_END_TURN: S_AI_TURN,
                E_WIN: S_GAME_OVER,
                E_LOSE: S_GAME_OVER,
            },
            S_PLAYER_MOVE: {
                E_MOVE: S_PLAYER_ATTACK,
                E_CANCEL: S_PLAYER_SELECT,
                E_ACTION_START: S_UNIT_ACTING,
            },
            S_PLAYER_ATTACK: {
                E_ATTACK: S_UNIT_ACTING,
                E_SKIP: S_PLAYER_SELECT,
                E_CANCEL: S_PLAYER_SELECT,
            },
            S_UNIT_ACTING: {
                E_ACTION_DONE: S_PLAYER_SELECT,
                E_MOVE: S_PLAYER_ATTACK,  # move animation finished → attack phase
                E_WIN: S_GAME_OVER,
                E_LOSE: S_GAME_OVER,
                E_AI_DONE: S_PLAYER_SELECT,
            },
            S_AI_TURN: {
                E_AI_START: S_UNIT_ACTING,
                E_AI_DONE: S_PLAYER_SELECT,
                E_WIN: S_GAME_OVER,
                E_LOSE: S_GAME_OVER,
            },
            S_GAME_OVER: {},
        }
        return StateMachine(
            states=states,
            initial=S_PLAYER_SELECT,
            transitions=transitions,
            on_enter={
                S_PLAYER_SELECT: self._enter_player_select,
                S_PLAYER_MOVE: self._enter_player_move,
                S_PLAYER_ATTACK: self._enter_player_attack,
                S_AI_TURN: self._enter_ai_turn,
                S_GAME_OVER: self._enter_game_over,
            },
            on_exit={
                S_PLAYER_MOVE: self._exit_player_move,
                S_PLAYER_ATTACK: self._exit_player_attack,
            },
        )

    # ------------------------------------------------------------------
    # FSM on_enter / on_exit callbacks
    # ------------------------------------------------------------------

    def _enter_player_select(self) -> None:
        self._deselect()
        self._update_turn_label()
        self._hint_label.text = "Select a warrior"
        self._end_turn_btn.visible = True
        self._end_turn_btn.enabled = True

    def _enter_player_move(self) -> None:
        if self.selected_unit is None:
            return
        u = self.selected_unit
        self._move_cells = self.grid.movement_range(u.col, u.row, u.mov)
        self._hint_label.text = "Click a blue cell to move (right-click to cancel)"
        self._end_turn_btn.enabled = False

    def _exit_player_move(self) -> None:
        self._move_cells = set()

    def _enter_player_attack(self) -> None:
        if self.selected_unit is None:
            return
        u = self.selected_unit
        atk_cells = self.grid.attack_range(u.col, u.row, u.rng)
        # Only highlight cells occupied by living enemies
        self._attack_cells = {
            (c, r) for c, r in atk_cells
            if self.grid.unit_at(c, r) is not None
            and self.grid.unit_at(c, r).team == "enemy"
            and self.grid.unit_at(c, r).alive
        }
        if self._attack_cells:
            self._hint_label.text = "Click a red cell to attack (click elsewhere to skip)"
        else:
            self._hint_label.text = "No targets in range — click anywhere to skip"

    def _exit_player_attack(self) -> None:
        self._attack_cells = set()

    def _enter_ai_turn(self) -> None:
        self._deselect()
        self._hint_label.text = "Enemy turn..."
        self._end_turn_btn.enabled = False
        self._turn_label.text = "Enemy Turn"

        # Queue living skeletons
        self._ai_queue = [s for s in self.skeletons if s.alive]
        # Start processing after a short delay for visual clarity
        self.after(0.4, self._process_next_ai)

    def _enter_game_over(self) -> None:
        self._deselect()
        self._hint_label.visible = False
        self._end_turn_btn.visible = False

    # ------------------------------------------------------------------
    # Win / lose checks
    # ------------------------------------------------------------------

    def _check_game_over(self) -> bool:
        """Check for victory or defeat.  Returns True if game ended."""
        if not any(s.alive for s in self.skeletons):
            self._game_over_result = "victory"
            self.fsm.trigger(E_WIN)
            self._show_game_over("VICTORY!")
            return True
        if not any(w.alive for w in self.warriors):
            self._game_over_result = "defeat"
            self.fsm.trigger(E_LOSE)
            self._show_game_over("DEFEAT")
            return True
        return False

    def _show_game_over(self, text: str) -> None:
        self._game_over_title.text = text
        self._game_over_panel.visible = True
        self._turn_label.text = text

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def _select(self, unit: BaseUnit) -> None:
        self._deselect()
        self.selected_unit = unit
        unit.select()

    def _deselect(self) -> None:
        if self.selected_unit is not None:
            self.selected_unit.deselect()
        self.selected_unit = None
        self._move_cells = set()
        self._attack_cells = set()

    def _update_turn_label(self) -> None:
        acted = len(self.acted_this_turn)
        total = sum(1 for w in self.warriors if w.alive)
        self._turn_label.text = f"Player Turn {self._turn_number}  ({acted}/{total} acted)"

    # ------------------------------------------------------------------
    # Player click handling
    # ------------------------------------------------------------------

    def _on_end_turn_click(self) -> None:
        if self.fsm.state in (S_PLAYER_SELECT, S_PLAYER_MOVE, S_PLAYER_ATTACK):
            self._deselect()
            # Force transition to AI turn
            if self.fsm.state == S_PLAYER_MOVE:
                self.fsm.trigger(E_CANCEL)
            elif self.fsm.state == S_PLAYER_ATTACK:
                self.fsm.trigger(E_CANCEL)
            self.fsm.trigger(E_END_TURN)

    def _handle_player_select_click(self, col: int, row: int) -> None:
        """PLAYER_SELECT: click a friendly warrior to select it."""
        unit = self.grid.unit_at(col, row)
        if (
            unit is not None
            and unit.alive
            and unit.team == "friendly"
            and id(unit) not in self.acted_this_turn
        ):
            self._select(unit)
            self.fsm.trigger(E_SELECT)

    def _handle_player_move_click(self, col: int, row: int) -> None:
        """PLAYER_MOVE: click a blue cell to move (or current cell to stay)."""
        if (col, row) not in self._move_cells:
            return
        u = self.selected_unit
        if u is None:
            return

        if (col, row) == (u.col, u.row):
            # Stay in place — skip move, go straight to attack phase
            self.fsm.trigger(E_MOVE)
            return

        # Animate the walk, then snap grid position and transition
        target_x, _ = self.grid.grid_to_world_center(col, row)
        target_y = self.grid.origin_y + (row + 1) * TILE_SIZE

        # Temporarily clear occupancy from old cell
        self.grid.remove_unit(u.col, u.row)

        def on_arrive() -> None:
            u.set_grid_pos(col, row)
            self.fsm.trigger(E_MOVE)

        self.fsm.trigger(E_ACTION_START)
        u.sprite.do(Sequence(
            Parallel(
                PlayAnim(u.anim_walk),
                MoveTo((target_x, target_y), speed=MOVE_SPEED),
            ),
            Do(lambda: u.sprite.play(u.anim_idle)),
            Do(on_arrive),
        ))

    def _handle_player_attack_click(self, col: int, row: int) -> None:
        """PLAYER_ATTACK: click a red cell to attack an enemy."""
        if (col, row) not in self._attack_cells:
            # Clicked outside attack range — skip attack
            self._finish_player_action()
            return

        u = self.selected_unit
        if u is None:
            return

        target = self.grid.unit_at(col, row)
        if target is None or not target.alive:
            self._finish_player_action()
            return

        def on_attack_done() -> None:
            self.acted_this_turn.add(id(u))
            if not self._check_game_over():
                self.fsm.trigger(E_ACTION_DONE)

        action = u.get_attack_action(target, on_complete=on_attack_done)
        self.fsm.trigger(E_ATTACK)
        u.sprite.do(action)

    def _finish_player_action(self) -> None:
        """Mark the current warrior as acted and return to select."""
        if self.selected_unit is not None:
            self.acted_this_turn.add(id(self.selected_unit))
        self.fsm.trigger(E_SKIP)

    # ------------------------------------------------------------------
    # AI turn processing
    # ------------------------------------------------------------------

    def _process_next_ai(self) -> None:
        """Process the next AI unit in the queue."""
        # Skip dead units
        while self._ai_queue and not self._ai_queue[0].alive:
            self._ai_queue.pop(0)

        if not self._ai_queue:
            self._finish_ai_turn()
            return

        ai_unit = self._ai_queue.pop(0)
        decision = self._ai.compute_turn(self.grid, ai_unit, self.warriors)
        kind = decision[0]

        if kind == "wait":
            # Nothing to do — process next
            self.after(0.2, self._process_next_ai)
            return

        if kind == "attack":
            target = decision[1]
            self._ai_execute_attack(ai_unit, target)

        elif kind == "move_attack":
            cell = decision[1]
            target = decision[2]
            self._ai_execute_move_then_attack(ai_unit, cell, target)

        elif kind == "move":
            cell = decision[1]
            self._ai_execute_move(ai_unit, cell)

    def _ai_execute_attack(self, ai_unit: BaseUnit, target: BaseUnit) -> None:
        """AI attacks a target from current position."""
        def on_done() -> None:
            if not self._check_game_over():
                self.after(0.3, self._process_next_ai)

        action = ai_unit.get_attack_action(target, on_complete=on_done)
        ai_unit.sprite.do(action)

    def _ai_execute_move_then_attack(
        self,
        ai_unit: BaseUnit,
        cell: tuple[int, int],
        target: BaseUnit,
    ) -> None:
        """AI moves to cell, then attacks target."""
        col, row = cell
        target_x, _ = self.grid.grid_to_world_center(col, row)
        target_y = self.grid.origin_y + (row + 1) * TILE_SIZE

        self.grid.remove_unit(ai_unit.col, ai_unit.row)

        def on_arrive() -> None:
            ai_unit.set_grid_pos(col, row)
            # Now attack
            if target.alive:
                self._ai_execute_attack(ai_unit, target)
            else:
                if not self._check_game_over():
                    self.after(0.3, self._process_next_ai)

        ai_unit.sprite.do(Sequence(
            Parallel(
                PlayAnim(ai_unit.anim_walk),
                MoveTo((target_x, target_y), speed=MOVE_SPEED),
            ),
            Do(lambda: ai_unit.sprite.play(ai_unit.anim_idle)),
            Do(on_arrive),
        ))

    def _ai_execute_move(self, ai_unit: BaseUnit, cell: tuple[int, int]) -> None:
        """AI moves toward enemies (no attack possible)."""
        col, row = cell
        target_x, _ = self.grid.grid_to_world_center(col, row)
        target_y = self.grid.origin_y + (row + 1) * TILE_SIZE

        self.grid.remove_unit(ai_unit.col, ai_unit.row)

        def on_arrive() -> None:
            ai_unit.set_grid_pos(col, row)
            self.after(0.3, self._process_next_ai)

        ai_unit.sprite.do(Sequence(
            Parallel(
                PlayAnim(ai_unit.anim_walk),
                MoveTo((target_x, target_y), speed=MOVE_SPEED),
            ),
            Do(lambda: ai_unit.sprite.play(ai_unit.anim_idle)),
            Do(on_arrive),
        ))

    def _finish_ai_turn(self) -> None:
        """All AI units have acted — start a new player turn."""
        self._turn_number += 1
        self.acted_this_turn.clear()
        if not self._check_game_over():
            self.fsm.trigger(E_AI_DONE)

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def handle_input(self, event: InputEvent) -> bool:
        state = self.fsm.state

        # Game over — Enter to restart, Escape to quit
        if state == S_GAME_OVER:
            if event.action == "confirm":
                self.game.replace(BattleScene())
                return True
            if event.action == "cancel":
                self.game.pop()
                return True
            return True  # consume all input

        # Escape — cancel selection / skip attack
        if event.action == "cancel":
            if state == S_PLAYER_MOVE:
                self.fsm.trigger(E_CANCEL)
                return True
            if state == S_PLAYER_ATTACK:
                self._finish_player_action()
                return True
            if state == S_PLAYER_SELECT:
                self.game.pop()
                return True
            return False

        # "E" key — end turn shortcut
        if event.type == "key_press" and event.key == "e":
            if state in (S_PLAYER_SELECT, S_PLAYER_MOVE, S_PLAYER_ATTACK):
                self._on_end_turn_click()
                return True

        # Right-click — cancel in move/attack
        if event.type == "click" and event.button == "right":
            if state == S_PLAYER_MOVE:
                self.fsm.trigger(E_CANCEL)
                return True
            if state == S_PLAYER_ATTACK:
                self._finish_player_action()
                return True
            return False

        # Left-click — state-dependent
        if event.type == "click" and event.button == "left":
            # Convert screen coords to grid
            wx = event.world_x if event.world_x is not None else float(event.x)
            wy = event.world_y if event.world_y is not None else float(event.y)
            col, row = self.grid.world_to_grid(wx, wy)

            if col < 0 or row < 0:
                # Clicked outside grid
                if state == S_PLAYER_ATTACK:
                    self._finish_player_action()
                    return True
                return False

            if state == S_PLAYER_SELECT:
                self._handle_player_select_click(col, row)
                return True
            elif state == S_PLAYER_MOVE:
                self._handle_player_move_click(col, row)
                return True
            elif state == S_PLAYER_ATTACK:
                self._handle_player_attack_click(col, row)
                return True

        return False

    # ------------------------------------------------------------------
    # Draw — highlights, health bars, floating damage numbers
    # ------------------------------------------------------------------

    def draw(self) -> None:
        state = self.fsm.state

        # Grid highlights
        move_hl = self._move_cells if state == S_PLAYER_MOVE else None
        atk_hl = self._attack_cells if state == S_PLAYER_ATTACK else None
        self.grid.draw_highlights(self, move_hl, atk_hl)

        # Health bars and floating numbers for all units
        for unit in self.all_units:
            unit.draw_health_bar(self)
            unit.draw_floaters(self)


# ======================================================================
# TitleScene
# ======================================================================

class TitleScene(Scene):
    """Simple title screen — press Enter to start."""

    background_color = (25, 25, 40, 255)

    def on_enter(self) -> None:
        self.ui.add(Label(
            "TACTICAL BATTLE",
            font_size=64,
            font="Arial",
            text_color=(255, 220, 80, 255),
            anchor=Anchor.TOP,
            margin=200,
        ))
        self.ui.add(Label(
            "Press ENTER to start",
            font_size=28,
            font="Arial",
            text_color=(200, 200, 200, 255),
            anchor=Anchor.TOP,
            margin=320,
        ))
        self.ui.add(Label(
            "Press ESC to quit",
            font_size=24,
            font="Arial",
            text_color=(160, 160, 160, 255),
            anchor=Anchor.TOP,
            margin=370,
        ))

    def handle_input(self, event: InputEvent) -> bool:
        if event.action == "confirm":
            self.game.push(BattleScene())
            return True
        if event.action == "cancel":
            self.game.quit()
            return True
        return False


# ======================================================================
# Main
# ======================================================================

def main() -> None:
    asset_path = Path(__file__).resolve().parent / "assets"

    game = Game(
        "Tactical Battle",
        resolution=(SCREEN_W, SCREEN_H),
        fullscreen=False,
        backend="pyglet",
    )
    game.assets = AssetManager(
        game.backend,
        base_path=asset_path,
    )

    game.run(TitleScene())


if __name__ == "__main__":
    main()
