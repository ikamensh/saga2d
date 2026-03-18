"""Library Consumer Harness — verifies saga2d can be used as a consumer would.

Covers:
  US1 — Install: import saga2d succeeds, all 63 symbols accessible
  US2 — Import: all 63 public API symbols importable by name
  US3 — Game init: Game(mock), push Scene, tick
  US5 — Teardown: game._teardown() cleans up state

Run: python -m tests.harness.consumer_harness [-v]
"""

from __future__ import annotations

import sys

# Canonical list of the 63 public API symbols (from saga2d/__init__.py __all__)
EXPECTED_SYMBOLS = [
    "HUD",
    "Action",
    "Anchor",
    "AnimationDef",
    "AssetManager",
    "AssetNotFoundError",
    "AudioManager",
    "Button",
    "Camera",
    "ChoiceScreen",
    "ColorSwap",
    "Component",
    "ConfirmDialog",
    "CursorManager",
    "DataTable",
    "Delay",
    "Do",
    "DragManager",
    "Ease",
    "Event",
    "FadeIn",
    "FadeOut",
    "Game",
    "Grid",
    "ImageBox",
    "InputEvent",
    "InputManager",
    "KeyEvent",
    "Label",
    "Layout",
    "List",
    "MessageScreen",
    "MouseEvent",
    "MoveTo",
    "Panel",
    "Parallel",
    "ParticleEmitter",
    "PlayAnim",
    "ProgressBar",
    "Remove",
    "RenderLayer",
    "Repeat",
    "SaveError",
    "SaveLoadScreen",
    "SaveManager",
    "Scene",
    "Sequence",
    "Sprite",
    "SpriteAnchor",
    "StateMachine",
    "Style",
    "TabGroup",
    "TextBox",
    "Theme",
    "TimerHandle",
    "Tooltip",
    "WindowEvent",
    "compute_anchor_position",
    "compute_content_size",
    "compute_flow_layout",
    "get_palette",
    "register_palette",
    "tween",
]


def run_harness(verbose: bool = False) -> bool:
    """Run the consumer harness. Returns True on success, False on failure."""
    ok = True

    # ── US1 + US2: Import all 63 public API symbols ──
    try:
        import saga2d

        # Verify __all__ matches our expectation
        actual = sorted(saga2d.__all__)
        expected = sorted(EXPECTED_SYMBOLS)
        if actual != expected:
            extra = set(actual) - set(expected)
            missing_from_expected = set(expected) - set(actual)
            if verbose:
                if extra:
                    print(f"  Extra symbols in __all__: {extra}")
                if missing_from_expected:
                    print(f"  Missing from __all__: {missing_from_expected}")
            ok = False

        # Verify every symbol in __all__ is actually accessible
        missing = [s for s in saga2d.__all__ if not hasattr(saga2d, s)]
        if missing:
            if verbose:
                print(f"  Missing symbols (not importable): {missing}")
            ok = False

        # Verify star-import equivalent works
        ns: dict = {}
        exec(f"from saga2d import {', '.join(saga2d.__all__)}", ns)

        count = len(saga2d.__all__)
        if verbose:
            print(f"  US1/US2: Imported {count} public API symbols — OK")
    except Exception as e:
        if verbose:
            print(f"  US1/US2: Import failed — {e}")
        return False

    # ── US3: Game(mock), push Scene, tick ──
    try:
        game = saga2d.Game(
            "ConsumerHarness", resolution=(800, 600), backend="mock"
        )
    except Exception as e:
        if verbose:
            print(f"  US3: Game init failed — {e}")
        return False

    try:
        scene = saga2d.Scene()
        game.push(scene)
        game.tick(0.016)

        # Verify scene is on stack
        top = game._scene_stack.top()
        if top is not scene:
            if verbose:
                print("  US3: Scene not on stack after push")
            ok = False
        elif verbose:
            print("  US3: Game(mock), push(Scene), tick(0.016) — OK")
    except Exception as e:
        if verbose:
            print(f"  US3: tick failed — {e}")
        ok = False

    # ── US5: Teardown ──
    try:
        game._teardown()

        # Verify cleanup — _current_game lives on saga2d.rendering.sprite module
        from saga2d.rendering import sprite as _sprite_mod

        if _sprite_mod._current_game is not None:
            if verbose:
                print("  US5: _current_game not None after teardown")
            ok = False
        elif verbose:
            print("  US5: _teardown() cleans up — OK")
    except Exception as e:
        if verbose:
            print(f"  US5: teardown failed — {e}")
        ok = False

    return ok


def main() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    success = run_harness(verbose=verbose)
    status = "PASS" if success else "FAIL"
    if verbose:
        print(f"Consumer harness: {status}")
    else:
        print(f"Consumer harness: {status}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
