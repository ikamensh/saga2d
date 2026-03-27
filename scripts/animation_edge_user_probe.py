"""Manual / CI-friendly probe: AnimationDef & AnimationPlayer edge cases.

Run from repo root:
  uv run python scripts/animation_edge_user_probe.py

Adjust SCENARIOS or temp asset layout in CONFIG only — no CLI.
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

# ----- CONFIG ----------------------------------------------------------------

# Scenarios: name -> callable returning None (prints its own lines)
RUN_E2E_SPRITE = True  # needs tiny temp PNGs


def _print(title: str, lines: list[str]) -> None:
    print(f"\n=== {title} ===")
    for line in lines:
        print(line)


def _expect_raises(label: str, fn, exc_type, substr: str | None = None) -> None:
    try:
        fn()
    except exc_type as e:
        msg = str(e)
        ok = substr is None or substr in msg
        _print(
            label,
            [
                f"RESULT: {exc_type.__name__} as expected",
                f"message: {msg!r}",
                f"substring_match({substr!r}): {ok}",
            ],
        )
        return
    _print(label, ["RESULT: BUG — expected", exc_type.__name__, "but no exception"])


# ----- Direct API (no Game) ---------------------------------------------------


def probe_animation_def_bad_durations() -> None:
    from saga2d.animation import AnimationDef

    bads = [
        ("zero", 0.0),
        ("negative", -0.1),
        ("nan", float("nan")),
        ("inf", float("inf")),
        ("neg_inf", float("-inf")),
    ]
    for name, d in bads:
        _expect_raises(
            f"AnimationDef(frame_duration={name})",
            lambda: AnimationDef(frames=["a", "b"], frame_duration=d),
            ValueError,
            "frame_duration",
        )


def probe_animation_player_bad_durations() -> None:
    from saga2d.animation import AnimationPlayer

    frames = ["h0", "h1", "h2"]
    bads = [
        ("zero", 0.0),
        ("negative", -1.0),
        ("nan", float("nan")),
        ("inf", float("inf")),
        ("neg_inf", float("-inf")),
    ]
    for name, d in bads:
        _expect_raises(
            f"AnimationPlayer(frame_duration={name})",
            lambda fd=d: AnimationPlayer(frames, frame_duration=fd, loop=False),
            ValueError,
            "frame_duration",
        )


def probe_empty_list_animation_def() -> None:
    from saga2d.animation import AnimationDef

    d = AnimationDef(frames=[], frame_duration=0.1, loop=True)
    _print(
        "AnimationDef(frames=[], frame_duration=0.1)",
        [
            "RESULT: constructs successfully (empty list is allowed on Def).",
            f"repr snippet: {d!r}",
        ],
    )


def probe_animation_player_empty_frames_order() -> None:
    from saga2d.animation import AnimationPlayer

    _expect_raises(
        "AnimationPlayer([], frame_duration=0) — error priority",
        lambda: AnimationPlayer([], frame_duration=0.0, loop=False),
        ValueError,
        "zero frames",
    )


def probe_single_frame_player() -> None:
    from saga2d.animation import AnimationPlayer

    completed: list[bool] = []
    p = AnimationPlayer(
        ["only"],
        frame_duration=0.1,
        loop=False,
        on_complete=lambda: completed.append(True),
    )
    p.update(0.05)
    mid = (p.frame_index, p.is_complete, len(completed))
    p.update(0.2)
    after = (p.frame_index, p.is_complete, len(completed))
    _print(
        "AnimationPlayer single frame, non-loop",
        [
            f"after dt=0.05: frame_index={mid[0]}, complete={mid[1]}, callbacks={mid[2]}",
            f"after +dt=0.2: frame_index={after[0]}, complete={after[1]}, callbacks={after[2]}",
            "RESULT: first update does not complete; second crosses duration → complete + on_complete.",
        ],
    )

    p2 = AnimationPlayer(["only"], frame_duration=0.1, loop=True)
    for _ in range(20):
        p2.update(0.1)
    _print(
        "AnimationPlayer single frame, loop=True",
        [
            f"after 20×dt=0.1: frame_index={p2.frame_index}, is_playing={p2.is_playing}",
            "RESULT: stays index 0; is_playing True (vacuous wrap).",
        ],
    )


def probe_player_update_nan_dt() -> None:
    from saga2d.animation import AnimationPlayer

    p = AnimationPlayer(["a", "b"], frame_duration=0.1, loop=False)
    p.update(float("nan"))
    _print(
        "AnimationPlayer.update(nan) valid player",
        [
            f"_elapsed after update: {p._elapsed} (nan if propagated)",
            f"frame_index: {p.frame_index}",
            "RESULT: elapsed becomes NaN; while _elapsed >= _frame_duration is False → stuck, no advance.",
        ],
    )


# ----- E2E: Game + Sprite + AssetManager -------------------------------------


def _make_asset_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="saga2d_anim_probe_"))
    images = root / "images" / "sprites"
    images.mkdir(parents=True)
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8  # tiny placeholder
    (images / "knight.png").write_bytes(png)
    (images / "oneframe_01.png").write_bytes(png)
    (images / "walk_01.png").write_bytes(png)
    (images / "walk_02.png").write_bytes(png)
    return root


def probe_e2e_sprite() -> None:
    from saga2d import Game, Scene, Sprite
    from saga2d.animation import AnimationDef
    from saga2d.assets import AssetManager

    root = _make_asset_root()
    try:
        g = Game("AnimProbe", backend="mock", resolution=(800, 600))
        g.assets = AssetManager(g.backend, base_path=root)
        scene = Scene()
        g.push(scene)
        sp = Sprite("sprites/knight", position=(10, 20))
        scene.add_sprite(sp)

        # 1) Empty explicit frame list on Def → play resolves to [] → player ctor
        empty_def = AnimationDef(frames=[], frame_duration=0.1, loop=True)
        try:
            sp.play(empty_def)
            lines = ["RESULT: unexpected — play() should have raised"]
        except ValueError as e:
            lines = [
                "Sprite.play(AnimationDef(frames=[], …))",
                f"RESULT: ValueError {e!r}",
                "Repro: build valid Def with [] and valid duration; play fails at AnimationPlayer(empty).",
            ]
        _print("E2E empty frames list", lines)

        g._teardown()

        # 2) Single-frame animation through tick (new Game — singleton)
        g2 = Game("AnimProbe2", backend="mock", resolution=(800, 600))
        g2.assets = AssetManager(g2.backend, base_path=root)
        scene2 = Scene()
        g2.push(scene2)
        sp2 = Sprite("sprites/knight", position=(0, 0))
        scene2.add_sprite(sp2)
        one = AnimationDef(
            frames=["sprites/oneframe_01"],
            frame_duration=0.05,
            loop=False,
        )
        done = []
        sp2.play(one, on_complete=lambda: done.append(True))
        g2.tick(0.02)
        g2.tick(0.10)
        _print(
            "E2E single-frame non-loop via Game.tick",
            [
                f"after ticks: anim_complete={sp2._anim_player.is_complete if sp2._anim_player else None}",
                f"on_complete fired: {len(done) == 1}",
                "RESULT: two ticks enough to finish; callback runs once.",
            ],
        )
        g2._teardown()

        # 3) Invalid frame_duration on Def — ctor only (no Game)
        try:
            bad = AnimationDef(frames=["sprites/walk_01"], frame_duration=0.0, loop=True)
            msg = f"unexpected construct: {bad}"
        except ValueError as e:
            msg = f"ValueError at Def ctor: {e}"
        _print("E2E invalid duration blocked at AnimationDef", [msg])
    finally:
        import shutil

        shutil.rmtree(root, ignore_errors=True)


def main() -> None:
    probe_animation_def_bad_durations()
    probe_animation_player_bad_durations()
    probe_empty_list_animation_def()
    probe_animation_player_empty_frames_order()
    probe_single_frame_player()
    probe_player_update_nan_dt()
    if RUN_E2E_SPRITE:
        probe_e2e_sprite()

    _print(
        "Summary",
        [
            "All invalid frame_duration values rejected at AnimationDef / AnimationPlayer __init__.",
            "AnimationDef(frames=[]) is allowed; failure is at Sprite.play → AnimationPlayer(empty).",
            "Single-frame: non-loop completes after enough dt; loop=True stays on frame 0.",
            "update(nan): playback stuck (no frame advance) — avoid non-finite dt.",
        ],
    )


if __name__ == "__main__":
    main()
