"""3-battle campaign mode for the tactical battle demo.

Run from the project root::

    python examples/battle_vignette/campaign.py

Campaign progression:
    Battle 1 (Easy):   4 warriors vs 3 skeletons
    Battle 2 (Medium): 4 warriors vs 5 skeletons
    Battle 3 (Hard):   4 warriors vs 6 skeletons (boosted: 30 ATK, 8 DEF)

Between battles an interstitial screen shows "Battle X Complete!" and waits
for Enter.  After all three victories the player sees "Campaign Victory!".
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup (same as battle_demo.py)
# ---------------------------------------------------------------------------
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from saga2d import (  # noqa: E402
    Anchor,
    AssetManager,
    Game,
    InputEvent,
    Label,
    Layout,
    Panel,
    Scene,
    Style,
)

from examples.battle_vignette.battle_demo import (  # noqa: E402
    BattleScene,
    SCREEN_W,
    SCREEN_H,
)
from examples.battle_vignette.battle_unit import (  # noqa: E402
    SkeletonUnit,
    WarriorUnit,
)


# ======================================================================
# Battle configuration
# ======================================================================

class BattleConfig:
    """Describes one battle's unit layout."""

    def __init__(
        self,
        num_warriors: int,
        num_skeletons: int,
        skeleton_atk: int | None = None,
        skeleton_def: int | None = None,
    ) -> None:
        self.num_warriors = num_warriors
        self.num_skeletons = num_skeletons
        # None means use default stats
        self.skeleton_atk = skeleton_atk
        self.skeleton_def = skeleton_def


CAMPAIGN_BATTLES: list[BattleConfig] = [
    BattleConfig(num_warriors=4, num_skeletons=3),                             # Easy
    BattleConfig(num_warriors=4, num_skeletons=5),                             # Medium
    BattleConfig(num_warriors=4, num_skeletons=6, skeleton_atk=30, skeleton_def=8),  # Hard
]


# ======================================================================
# CampaignBattleScene — BattleScene with configurable unit counts/stats
# ======================================================================

class CampaignBattleScene(BattleScene):
    """A BattleScene whose unit spawning is driven by a :class:`BattleConfig`.

    After victory the scene notifies the campaign manager via *on_victory*
    instead of showing the default restart/quit overlay.
    """

    def __init__(
        self,
        config: BattleConfig,
        battle_number: int,
        on_victory: Any = None,
        on_defeat: Any = None,
    ) -> None:
        super().__init__()
        self._config = config
        self._battle_number = battle_number
        self._on_victory = on_victory
        self._on_defeat = on_defeat

    # ------------------------------------------------------------------
    # Override unit spawning
    # ------------------------------------------------------------------

    def _spawn_units(self) -> None:
        """Spawn warriors and skeletons according to the battle config."""
        cfg = self._config

        # Warrior positions — left column, centred vertically
        warrior_rows = _centered_rows(cfg.num_warriors, total_rows=6)
        for row in warrior_rows:
            w = WarriorUnit.spawn(self, col=1, row=row, grid=self.grid, team="friendly")
            self.warriors.append(w)
            self.all_units.append(w)

        # Skeleton positions — right column, centred vertically
        skeleton_rows = _centered_rows(cfg.num_skeletons, total_rows=6)
        for row in skeleton_rows:
            s = SkeletonUnit.spawn(self, col=6, row=row, grid=self.grid, team="enemy")
            # Apply stat overrides if present
            if cfg.skeleton_atk is not None:
                s.atk = cfg.skeleton_atk
            if cfg.skeleton_def is not None:
                s.def_ = cfg.skeleton_def
            self.skeletons.append(s)
            self.all_units.append(s)

    # ------------------------------------------------------------------
    # Override obstacle placement to respect dynamic unit positions
    # ------------------------------------------------------------------

    def _place_obstacles(self) -> None:
        """Place obstacles, reserving positions for the configured unit counts."""
        import random
        rng = random.Random(42 + self._battle_number)

        cfg = self._config
        warrior_rows = _centered_rows(cfg.num_warriors, total_rows=6)
        skeleton_rows = _centered_rows(cfg.num_skeletons, total_rows=6)
        reserved = {(1, r) for r in warrior_rows} | {(6, r) for r in skeleton_rows}

        from examples.battle_vignette.battle_demo import GRID_ROWS

        candidates = []
        for col in range(2, 6):
            for row in range(GRID_ROWS):
                if (col, row) not in reserved:
                    candidates.append((col, row))

        num_obstacles = rng.randint(3, 5)
        num_obstacles = min(num_obstacles, len(candidates))
        obstacle_positions = rng.sample(candidates, num_obstacles)

        for col, row in obstacle_positions:
            self.grid.place_obstacle(col, row)

    # ------------------------------------------------------------------
    # Override game-over handling to route through campaign
    # ------------------------------------------------------------------

    def _show_game_over(self, text: str) -> None:
        """Override to route victory/defeat through campaign callbacks."""
        self._game_over_title.text = text
        self._game_over_panel.visible = True
        self._turn_label.text = text

        # Update subtitle for campaign context
        if hasattr(self, "_game_over_result") and self._game_over_result == "victory":
            self._game_over_sub.text = "Press Enter to continue"
        else:
            self._game_over_sub.text = "Press Enter to retry  |  Escape to quit"

    def handle_input(self, event: InputEvent) -> bool:
        """Override game-over input to route through campaign."""
        from examples.battle_vignette.battle_demo import S_GAME_OVER

        if self.fsm.state == S_GAME_OVER:
            if event.action == "confirm":
                if hasattr(self, "_game_over_result") and self._game_over_result == "victory":
                    if self._on_victory:
                        self._on_victory()
                else:
                    if self._on_defeat:
                        self._on_defeat()
                return True
            if event.action == "cancel":
                self.game.pop()
                return True
            return True
        return super().handle_input(event)


# ======================================================================
# Interstitial Scene — "Battle X Complete!"
# ======================================================================

class InterstitialScene(Scene):
    """Brief screen shown between campaign battles."""

    transparent = False
    background_color = (15, 18, 30, 255)

    def __init__(self, title: str, subtitle: str, on_continue: Any = None) -> None:
        super().__init__()
        self._title_text = title
        self._subtitle_text = subtitle
        self._on_continue = on_continue

    def on_enter(self) -> None:
        self.ui.add(Panel(
            layout=Layout.VERTICAL,
            spacing=30,
            anchor=Anchor.CENTER,
            style=Style(
                background_color=(20, 20, 30, 220),
                padding=80,
            ),
            children=[
                Label(
                    self._title_text,
                    font_size=72,
                    font="Arial",
                    text_color=(255, 220, 80, 255),
                ),
                Label(
                    self._subtitle_text,
                    font_size=28,
                    font="Arial",
                    text_color=(200, 200, 200, 255),
                ),
            ],
        ))

    def handle_input(self, event: InputEvent) -> bool:
        if event.action == "confirm":
            if self._on_continue:
                self._on_continue()
            return True
        if event.action == "cancel":
            self.game.pop()
            return True
        return False


# ======================================================================
# CampaignScene — manages the 3-battle sequence
# ======================================================================

class CampaignScene(Scene):
    """Orchestrates a 3-battle campaign.

    This scene acts as the campaign "root".  It pushes battle scenes and
    interstitials on top of itself, using callbacks to advance through
    the sequence.
    """

    background_color = (15, 18, 30, 255)

    def on_enter(self) -> None:
        self._current_battle = 0
        self._start_battle(0)

    def _start_battle(self, index: int) -> None:
        """Push the battle scene for campaign battle *index*."""
        self._current_battle = index
        config = CAMPAIGN_BATTLES[index]
        battle = CampaignBattleScene(
            config=config,
            battle_number=index + 1,
            on_victory=lambda: self._on_battle_won(index),
            on_defeat=lambda: self._on_battle_lost(index),
        )
        self.game.push(battle)

    def _on_battle_won(self, index: int) -> None:
        """Called when battle *index* is won."""
        # Pop the battle scene
        self.game.pop()

        if index < len(CAMPAIGN_BATTLES) - 1:
            # Show interstitial, then start next battle
            battle_num = index + 1
            interstitial = InterstitialScene(
                title=f"Battle {battle_num} Complete!",
                subtitle="Press Enter to continue",
                on_continue=lambda: self._advance_to_next(index + 1),
            )
            self.game.push(interstitial)
        else:
            # All battles won — show victory screen
            victory = InterstitialScene(
                title="Campaign Victory!",
                subtitle="All battles won!  Press Enter or Escape to quit",
                on_continue=lambda: self.game.quit(),
            )
            self.game.push(victory)

    def _advance_to_next(self, next_index: int) -> None:
        """Pop the interstitial and start the next battle."""
        self.game.pop()  # pop interstitial
        self._start_battle(next_index)

    def _on_battle_lost(self, index: int) -> None:
        """Called when battle *index* is lost — retry the same battle."""
        self.game.pop()  # pop the failed battle
        self._start_battle(index)


# ======================================================================
# Campaign Title Scene
# ======================================================================

class CampaignTitleScene(Scene):
    """Title screen for the campaign mode."""

    background_color = (15, 18, 30, 255)

    def on_enter(self) -> None:
        self.ui.add(Panel(
            layout=Layout.VERTICAL,
            spacing=20,
            anchor=Anchor.CENTER,
            style=Style(
                background_color=(20, 20, 30, 220),
                padding=60,
            ),
            children=[
                Label(
                    "TACTICAL CAMPAIGN",
                    font_size=80,
                    font="Arial",
                    text_color=(255, 220, 80, 255),
                ),
                Label(
                    "3 Battles  --  Warriors vs Skeletons",
                    font_size=32,
                    font="Arial",
                    text_color=(180, 170, 140, 255),
                ),
                Label(
                    "",
                    font_size=16,
                    font="Arial",
                    text_color=(0, 0, 0, 0),
                ),
                Label(
                    "Battle 1:  4 warriors vs 3 skeletons (easy)",
                    font_size=22,
                    font="Arial",
                    text_color=(160, 180, 160, 255),
                ),
                Label(
                    "Battle 2:  4 warriors vs 5 skeletons (medium)",
                    font_size=22,
                    font="Arial",
                    text_color=(180, 180, 140, 255),
                ),
                Label(
                    "Battle 3:  4 warriors vs 6 boosted skeletons (hard)",
                    font_size=22,
                    font="Arial",
                    text_color=(200, 140, 140, 255),
                ),
                Label(
                    "",
                    font_size=16,
                    font="Arial",
                    text_color=(0, 0, 0, 0),
                ),
                Label(
                    "Press ENTER to begin campaign",
                    font_size=28,
                    font="Arial",
                    text_color=(200, 200, 200, 255),
                ),
                Label(
                    "ESC to quit",
                    font_size=20,
                    font="Arial",
                    text_color=(120, 120, 130, 255),
                ),
            ],
        ))

    def handle_input(self, event: InputEvent) -> bool:
        if event.action == "confirm":
            self.game.push(CampaignScene())
            return True
        if event.action == "cancel":
            self.game.quit()
            return True
        return False


# ======================================================================
# Helpers
# ======================================================================

def _centered_rows(count: int, total_rows: int = 6) -> list[int]:
    """Return *count* row indices centred within 0..total_rows-1.

    Examples:
        _centered_rows(3, 6) -> [1, 2, 3]     (centred in 0-5)
        _centered_rows(4, 6) -> [1, 2, 3, 4]
        _centered_rows(5, 6) -> [0, 1, 2, 3, 4]
        _centered_rows(6, 6) -> [0, 1, 2, 3, 4, 5]
    """
    start = (total_rows - count) // 2
    return list(range(start, start + count))


# ======================================================================
# Main
# ======================================================================

def main() -> None:
    asset_path = Path(__file__).resolve().parent / "assets"

    game = Game(
        "Tactical Campaign",
        resolution=(SCREEN_W, SCREEN_H),
        fullscreen=False,
        backend="pyglet",
    )
    game.assets = AssetManager(
        game.backend,
        base_path=asset_path,
    )

    game.run(CampaignTitleScene())


if __name__ == "__main__":
    main()
