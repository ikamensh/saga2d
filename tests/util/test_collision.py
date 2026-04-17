"""Properties of :mod:`saga2d.util.collision`.

iter-44 ships :class:`Rect` and :func:`aabb_overlap` as the first
collision helpers in saga2d. The properties below are the algebraic
invariants of AABB overlap:

*   **Reflexivity**: ``a.overlaps(a) == True`` for any positive Rect.
*   **Symmetry**: ``aabb_overlap(a, b) == aabb_overlap(b, a)``.
*   **Zero-size rects** don't overlap anything (including themselves).
*   **Touching-but-not-overlapping** boundary case:
    ``(0, 0, 10, 10)`` and ``(10, 0, 10, 10)`` — the right edge of the
    first exactly meets the left edge of the second. saga2d picks the
    strict-inequality convention, so this is *not* an overlap. We
    document this choice.
*   **Centre-distance formula**: overlap on axis iff
    ``|dx| * 2 < (w1 + w2)``.
*   **Tuple vs Rect interop**: the helper accepts either without
    coercion.
*   **Property: contains_point**: a Rect's centre is always inside it.
*   **Sprite.aabb**: anchored bounding box tracks the sprite as it moves.
"""

from __future__ import annotations

import pytest

from saga2d import Game, Rect, Scene, Sprite, aabb_overlap


# ---------------------------------------------------------------------------
# Rect unit properties
# ---------------------------------------------------------------------------


def test_rect_is_frozen_and_hashable() -> None:
    r = Rect(0, 0, 10, 10)
    with pytest.raises(Exception):  # dataclass(frozen=True) blocks mutation.
        r.cx = 5  # type: ignore[misc]
    # Hashable → usable as dict key / set member.
    assert hash(r) == hash(Rect(0, 0, 10, 10))


def test_rect_overlap_is_reflexive_for_positive_rect() -> None:
    r = Rect(100, 50, 40, 40)
    assert r.overlaps(r) is True


def test_rect_overlap_is_symmetric() -> None:
    a = Rect(0, 0, 10, 10)
    b = Rect(5, 5, 10, 10)
    assert a.overlaps(b) == b.overlaps(a) == True


def test_rect_non_overlap_is_symmetric() -> None:
    a = Rect(0, 0, 10, 10)
    b = Rect(100, 100, 10, 10)
    assert a.overlaps(b) == b.overlaps(a) == False


def test_rect_contains_its_own_centre() -> None:
    r = Rect(50, 30, 20, 10)
    assert r.contains_point(50, 30) is True


def test_rect_contains_point_boundary() -> None:
    r = Rect(0, 0, 10, 10)  # spans x=-5..5, y=-5..5
    assert r.contains_point(-5, -5) is True   # corner
    assert r.contains_point(5, 5) is True
    assert r.contains_point(5.1, 0) is False  # just outside


def test_rect_overlaps_accepts_tuple() -> None:
    r = Rect(0, 0, 10, 10)
    assert r.overlaps((5, 0, 10, 10)) is True
    assert r.overlaps((50, 0, 10, 10)) is False


# ---------------------------------------------------------------------------
# aabb_overlap free function
# ---------------------------------------------------------------------------


def test_aabb_overlap_symmetry() -> None:
    """Property: overlap is symmetric for any pair of AABBs."""
    import random
    rng = random.Random(0)
    for _ in range(50):
        a = (rng.uniform(-100, 100), rng.uniform(-100, 100),
             rng.uniform(1, 50), rng.uniform(1, 50))
        b = (rng.uniform(-100, 100), rng.uniform(-100, 100),
             rng.uniform(1, 50), rng.uniform(1, 50))
        assert aabb_overlap(a, b) == aabb_overlap(b, a)


def test_aabb_overlap_interior_is_overlap() -> None:
    """A rect fully inside another overlaps it."""
    outer = (0, 0, 100, 100)
    inner = (20, 20, 10, 10)
    assert aabb_overlap(outer, inner) is True
    assert aabb_overlap(inner, outer) is True


def test_aabb_overlap_disjoint_is_not_overlap() -> None:
    assert aabb_overlap((0, 0, 10, 10), (100, 100, 10, 10)) is False


def test_aabb_overlap_touching_edges_is_not_overlap() -> None:
    """Rects whose edges exactly touch are NOT considered overlapping.

    saga2d uses the strict-inequality convention
    (``abs(dx) * 2 < w1 + w2``) so a row of non-overlapping tiles
    placed edge-to-edge doesn't register spurious collisions.
    """
    # (0,0,10,10) spans x=-5..5; (10,0,10,10) spans x=5..15. Touch at x=5.
    assert aabb_overlap((0, 0, 10, 10), (10, 0, 10, 10)) is False


def test_aabb_overlap_strict_treats_touching_edges_as_overlap() -> None:
    """iter-46 opt-in: ``strict=True`` flips touching-edges from
    non-overlap to overlap. Useful for bullet-vs-player "first
    contact tags as hit" semantics.
    """
    a = (0, 0, 10, 10)
    b = (10, 0, 10, 10)  # right edge of a touches left edge of b
    assert aabb_overlap(a, b) is False          # default: strict inequality
    assert aabb_overlap(a, b, strict=True) is True   # opt-in: touch tags


def test_aabb_overlap_strict_still_rejects_disjoint() -> None:
    """strict=True flips only the boundary case — fully disjoint
    rects still report non-overlap."""
    assert aabb_overlap((0, 0, 10, 10), (100, 100, 10, 10), strict=True) is False


def test_aabb_overlap_accepts_mixed_rect_and_tuple() -> None:
    r = Rect(0, 0, 10, 10)
    assert aabb_overlap(r, (5, 0, 10, 10)) is True
    assert aabb_overlap((5, 0, 10, 10), r) is True


def test_aabb_overlap_translation_invariant() -> None:
    """Property: translating both rects by the same vector doesn't
    change whether they overlap."""
    a = (0, 0, 10, 10)
    b = (4, 0, 10, 10)
    assert aabb_overlap(a, b) is True
    shifted = lambda rect, dx, dy: (rect[0] + dx, rect[1] + dy, rect[2], rect[3])
    assert aabb_overlap(shifted(a, 500, -300), shifted(b, 500, -300)) is True


# ---------------------------------------------------------------------------
# Sprite.aabb integration — the common-case helper for games
# ---------------------------------------------------------------------------


@pytest.fixture
def game():
    g = Game("collision-test", resolution=(400, 400),
             fullscreen=False, backend="mock", visible=False)
    yield g
    g._teardown()


def test_sprite_aabb_updates_with_position(game: Game) -> None:
    """Moving a sprite moves its AABB. The aabb property should NOT
    cache — every call returns a fresh Rect from the current position."""
    class S(Scene):
        background_color = (0, 0, 0, 255)

        def on_enter(self) -> None:
            self.sprite = self.add_sprite(Sprite(
                "player_token", position=(100, 100),
            ))

    scene = S()
    game._scene_stack.push(scene)
    game.tick(dt=1/60)
    aabb1 = scene.sprite.aabb
    scene.sprite.position = (200, 150)
    game.tick(dt=1/60)
    aabb2 = scene.sprite.aabb
    assert aabb1.cx != aabb2.cx
    assert aabb1.cy != aabb2.cy


def test_sprite_aabb_detects_overlap_with_another_sprite(game: Game) -> None:
    """Two sprites at nearly-identical positions overlap."""
    class S(Scene):
        background_color = (0, 0, 0, 255)

        def on_enter(self) -> None:
            self.a = self.add_sprite(Sprite(
                "player_token", position=(100, 100),
            ))
            self.b = self.add_sprite(Sprite(
                "player_token", position=(100, 100),
            ))

    scene = S()
    game._scene_stack.push(scene)
    game.tick(dt=1/60)
    assert aabb_overlap(scene.a.aabb, scene.b.aabb) is True


def test_sprite_aabb_matches_image_size(game: Game) -> None:
    """The AABB's width/height equal the underlying image dimensions."""
    class S(Scene):
        background_color = (0, 0, 0, 255)

        def on_enter(self) -> None:
            self.sprite = self.add_sprite(Sprite(
                "player_token", position=(100, 100),
            ))

    scene = S()
    game._scene_stack.push(scene)
    game.tick(dt=1/60)
    img_w, img_h = scene.sprite.size
    assert scene.sprite.aabb.w == img_w
    assert scene.sprite.aabb.h == img_h
