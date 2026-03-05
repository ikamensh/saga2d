"""Simple tactical AI for enemy units.

:class:`BattleAI` evaluates one AI-controlled unit at a time and returns
a decision tuple describing the best action:

- ``("attack", target)`` — target is already in attack range.
- ``("move_attack", (col, row), target)`` — move to cell, then attack.
- ``("move", (col, row))`` — move toward the nearest enemy; no attack possible.
- ``("wait",)`` — no reachable enemies, no useful moves.

Usage::

    ai = BattleAI()
    decision = ai.compute_turn(grid, skeleton, player_units)

    if decision[0] == "attack":
        target = decision[1]
        ...
    elif decision[0] == "move_attack":
        cell, target = decision[1], decision[2]
        ...
    elif decision[0] == "move":
        cell = decision[1]
        ...
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from examples.battle_vignette.battle_grid import SquareGrid
    from examples.battle_vignette.battle_unit import BaseUnit

# Decision type aliases for readability.
#   ("attack", target)
#   ("move_attack", (col, row), target)
#   ("move", (col, row))
#   ("wait",)
type Decision = (
    tuple[str, BaseUnit]
    | tuple[str, tuple[int, int], BaseUnit]
    | tuple[str, tuple[int, int]]
    | tuple[str]
)


# ======================================================================
# BFS distance helper
# ======================================================================

def _bfs_distance(
    grid: SquareGrid,
    start_col: int,
    start_row: int,
    goal_col: int,
    goal_row: int,
) -> int:
    """Return the shortest orthogonal distance between two cells.

    Uses BFS over the grid, treating occupied cells as passable (we only
    care about distance, not reachability).  Returns ``-1`` if no path
    exists (shouldn't happen on an open grid, but defensive).
    """
    if start_col == goal_col and start_row == goal_row:
        return 0

    visited: set[tuple[int, int]] = {(start_col, start_row)}
    queue: deque[tuple[int, int, int]] = deque()
    queue.append((start_col, start_row, 0))

    while queue:
        c, r, dist = queue.popleft()
        for nc, nr in grid.neighbors(c, r):
            if (nc, nr) in visited:
                continue
            if nc == goal_col and nr == goal_row:
                return dist + 1
            visited.add((nc, nr))
            queue.append((nc, nr, dist + 1))

    return -1  # unreachable


def _chebyshev(c1: int, r1: int, c2: int, r2: int) -> int:
    """Chebyshev (king-move) distance between two cells."""
    return max(abs(c1 - c2), abs(r1 - r2))


# ======================================================================
# BattleAI
# ======================================================================

class BattleAI:
    """Greedy tactical AI for a single unit.

    Strategy:

    1. **Attack in place** — if any enemy is already within attack range,
       pick the one with the lowest HP.
    2. **Move + attack** — otherwise, move to the reachable cell that
       places an enemy within attack range, preferring lowest-HP targets.
    3. **Move closer** — if no move allows attacking, advance toward the
       nearest enemy (by BFS distance from the destination cell).
    4. **Wait** — if no enemies remain or no moves are useful.
    """

    def compute_turn(
        self,
        grid: SquareGrid,
        ai_unit: BaseUnit,
        player_units: list[BaseUnit],
    ) -> Decision:
        """Evaluate the best action for *ai_unit* this turn.

        Parameters:
            grid:          The shared :class:`SquareGrid`.
            ai_unit:       The AI-controlled unit taking its turn.
            player_units:  All opposing units (dead units are filtered out).

        Returns:
            A decision tuple — see module docstring for the four forms.
        """
        # Filter to living enemies only.
        enemies = [u for u in player_units if u.alive]
        if not enemies:
            return ("wait",)

        # ------------------------------------------------------------------
        # 1. Can we attack from the current position?
        # ------------------------------------------------------------------
        targets_in_range = self._targets_in_range(grid, ai_unit, enemies)
        if targets_in_range:
            target = min(targets_in_range, key=lambda u: u.hp)
            return ("attack", target)

        # ------------------------------------------------------------------
        # 2. Can we move to a cell that allows attacking?
        # ------------------------------------------------------------------
        move_cells = grid.movement_range(ai_unit.col, ai_unit.row, ai_unit.mov)
        # Remove the current cell — staying still was handled above.
        candidate_cells = move_cells - {(ai_unit.col, ai_unit.row)}

        best_move_attack: tuple[tuple[int, int], BaseUnit] | None = None
        best_ma_hp = float("inf")

        for mc, mr in candidate_cells:
            # Which enemies would be in attack range from this cell?
            atk_cells = grid.attack_range(mc, mr, ai_unit.rng)
            for enemy in enemies:
                if (enemy.col, enemy.row) in atk_cells:
                    if enemy.hp < best_ma_hp:
                        best_ma_hp = enemy.hp
                        best_move_attack = ((mc, mr), enemy)

        if best_move_attack is not None:
            cell, target = best_move_attack
            return ("move_attack", cell, target)

        # ------------------------------------------------------------------
        # 3. Move toward the nearest enemy.
        # ------------------------------------------------------------------
        best_cell = self._best_advance_cell(grid, ai_unit, enemies, candidate_cells)
        if best_cell is not None:
            return ("move", best_cell)

        # ------------------------------------------------------------------
        # 4. No useful action — wait.
        # ------------------------------------------------------------------
        return ("wait",)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _targets_in_range(
        grid: SquareGrid,
        ai_unit: BaseUnit,
        enemies: list[BaseUnit],
    ) -> list[BaseUnit]:
        """Return enemies within Chebyshev attack range of *ai_unit*."""
        atk_cells = grid.attack_range(ai_unit.col, ai_unit.row, ai_unit.rng)
        return [e for e in enemies if (e.col, e.row) in atk_cells]

    @staticmethod
    def _best_advance_cell(
        grid: SquareGrid,
        ai_unit: BaseUnit,
        enemies: list[BaseUnit],
        candidate_cells: set[tuple[int, int]],
    ) -> tuple[int, int] | None:
        """Pick the move cell that minimises BFS distance to the nearest enemy.

        Ties are broken by Chebyshev distance (prefer cells that are also
        diagonally closer), then by grid position for determinism.
        """
        if not candidate_cells:
            return None

        # Find the nearest enemy by BFS from the AI unit's current position.
        nearest_enemy: BaseUnit | None = None
        nearest_dist = float("inf")
        for enemy in enemies:
            d = _bfs_distance(grid, ai_unit.col, ai_unit.row, enemy.col, enemy.row)
            if d >= 0 and d < nearest_dist:
                nearest_dist = d
                nearest_enemy = enemy

        if nearest_enemy is None:
            return None

        # Evaluate each candidate cell: how close does it get to the target?
        best: tuple[int, int] | None = None
        best_bfs = float("inf")
        best_cheb = float("inf")

        for mc, mr in candidate_cells:
            d = _bfs_distance(grid, mc, mr, nearest_enemy.col, nearest_enemy.row)
            if d < 0:
                continue
            cheb = _chebyshev(mc, mr, nearest_enemy.col, nearest_enemy.row)
            # Primary: BFS distance.  Secondary: Chebyshev.  Tertiary: grid order.
            if (d, cheb, (mr, mc)) < (best_bfs, best_cheb, (best[1], best[0]) if best else (float("inf"), float("inf"))):
                best_bfs = d
                best_cheb = cheb
                best = (mc, mr)

        return best
