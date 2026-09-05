"""Paced real-Pyglet reliability soak; freezes source before importing the game.

    uv run python tools/soak_eador.py --seconds 60 --input-interval .05
    uv run python tools/soak_eador.py --seconds 7200 --output dist/soak/candidate

Progress is durable in progress.json. SIGINT/SIGTERM stop the run, close the
window, release caffeinate, and write a cancelled report. This is an automated
repeated journey, not a human playtest or a complete-campaign balance test.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import resource
import shutil
import signal
import statistics
import struct
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback


ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    staged = path.with_suffix(".tmp")
    staged.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staged.replace(path)


def hashes(folder):
    return {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(folder.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def freeze(output, revision):
    """The worker imports only copied game/framework source, even during later edits."""
    output.mkdir(parents=True, exist_ok=False)
    source = output / "source"
    source.mkdir()
    commit = subprocess.check_output(["git", "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}"],
                                     cwd=ROOT, text=True).strip()
    archive = subprocess.check_output(["git", "archive", commit, "eador", "saga2d", "pyproject.toml", "uv.lock"], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as files:
        files.extractall(source, filter="data")
    (source / "tools").mkdir()
    shutil.copyfile(__file__, source / "tools" / "soak_eador.py")
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": commit,
        "source_origin": "git archive; working game/framework edits are excluded; harness is copied and independently hashed",
        "game_framework_last_change": subprocess.check_output(["git", "log", "-1", "--format=%H", commit, "--", "eador", "saga2d"], cwd=ROOT, text=True).strip(),
        "working_tree_status": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).splitlines(),
        "source_sha256": hashes(source),
        "python": sys.version, "python_executable": sys.executable,
        "packages": {name: metadata.version(name) for name in ("numpy", "Pillow", "pyglet")},
    }
    write_json(output / "manifest.json", manifest)
    return source


def rss_bytes():
    # ps reports current resident memory in KiB; ru_maxrss is only a high-water mark.
    return int(subprocess.check_output(["ps", "-o", "rss=", "-p", str(os.getpid())], text=True)) * 1024


def percentiles(values):
    if not values:
        return {}
    ordered = sorted(values)
    result = {}
    for name, fraction in (("p50_ms", .5), ("p95_ms", .95), ("p99_ms", .99)):
        position = (len(ordered) - 1) * fraction
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        result[name] = ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
    return {**result, "max_ms": ordered[-1], "samples": len(ordered)}


def cancel_run(signum, _frame):
    raise KeyboardInterrupt(signal.Signals(signum).name)


class Journey:
    """Yield one real input per step; assertions run after its rendered frame."""

    def __init__(self, game):
        from eador.scene import BattleScene, ChoiceScene, ShardScene

        self.game = game
        self.BattleScene, self.ChoiceScene, self.ShardScene = BattleScene, ChoiceScene, ShardScene
        self.counts = Counter()
        self.history = deque(maxlen=30)
        self.cycles = 0
        self.steps = self.repeat()

    @property
    def state(self):
        return next(scene.state for scene in self.game.scenes if isinstance(scene, self.ShardScene))

    def choices(self):
        if isinstance(self.game.scene, self.ChoiceScene):
            yield "key", "F5"
            saved = self.state.to_json()
            yield "key", "_1"
            yield "key", "F9"
            assert self.state.to_json() == saved, "pending-choice quickload changed state"
            self.counts["choice_save_load"] += 1
        while isinstance(self.game.scene, self.ChoiceScene):
            kind = self.state.choice.kind
            option = "_2" if kind == "skill" and self.cycles % 2 else "_1"
            yield "key", option
            self.counts[kind + "_choices"] += 1

    def battle(self):
        assert isinstance(self.game.scene, self.BattleScene)
        yield "key", "F5"
        saved = self.state.to_json()
        yield "key", "A"
        yield "key", "F9"
        assert self.state.to_json() == saved, "battle quickload changed state"
        self.counts["battle_save_load"] += 1
        scene, battle = self.game.scene, self.state.battle
        hero = battle.unit(0)
        yield "click", scene.grid.center(hero.pos)
        reachable = battle.reachable(0) - {hero.pos}
        if reachable:
            enemy = next(unit for unit in battle.units if unit.team == "enemy" and unit.alive)
            destination = min(reachable, key=lambda cell: (battle.grid.distance(cell, enemy.pos), cell))
            yield "click", scene.grid.center(destination)
            assert hero.pos == destination, "mouse move did not reach its hex"
            self.counts["manual_moves"] += 1
        targets = battle.targets(0)
        if targets:
            yield "click", scene.grid.center(targets[0].pos)
            assert hero.acted, "mouse attack was not applied"
            self.counts["manual_attacks"] += 1
        for _ in range(81):
            if self.state.battle.outcome is not None:
                break
            yield "key", "A"
            self.counts["auto_rounds"] += 1
        assert self.state.battle.outcome == "player", "prepared opening encounter was not won"
        yield "key", "E"
        self.counts["battles_resolved"] += 1
        yield from self.choices()

    def repeat(self):
        from eador.scene import HeroScene, SaveScene, TitleScene

        while True:
            # Bounded restarts reuse the same Game/window/render caches for the entire soak.
            seed = 7 + self.cycles % 8
            yield "restart", seed
            self.counts[f"seed_{seed}"] += 1
            for _ in range(self.cycles % 4):
                yield "key", "TAB"
            yield "key", "ENTER"
            self.counts["hero_" + self.state.hero.hero_class] += 1
            yield "key", "B"
            yield "key", "_1"
            yield "key", "ESCAPE"
            yield "key", "R"
            yield "key", "_2"
            yield "key", "ESCAPE"
            assert "barracks" in self.state.buildings and self.state.hero.army[-1].kind == "swordsman"
            yield "key", "X"
            yield from self.battle()
            assert self.state.inventory, "site reward did not reach inventory"
            yield "key", "H"
            assert isinstance(self.game.scene, HeroScene)
            yield "button", "Equip"
            assert self.state.hero.relic is not None
            yield "key", "ESCAPE"
            yield "key", "E"
            yield "click", self.game.scene.grid.center((-1, 0))
            yield "key", "ENTER"
            yield from self.battle()
            assert self.state.hero.pos == (-1, 0)
            yield "key", "F6"
            assert isinstance(self.game.scene, SaveScene)
            yield "key", "TAB"
            saved = self.state.to_json()
            yield "key", "_2"
            yield "key", "TAB"
            yield "key", "_2"
            assert self.state.to_json() == saved, "manual-slot load changed state"
            self.counts["browser_save_load"] += 1
            yield "key", "F1"
            yield "button", "Save & title"
            assert isinstance(self.game.scene, SaveScene)
            yield "key", "_3"
            assert isinstance(self.game.scene, TitleScene)
            self.cycles += 1

    def step(self):
        from pyglet.window import key, mouse
        from saga2d import Button
        from eador.scene import TitleScene

        kind, value = next(self.steps)
        self.counts[kind] += 1
        self.history.append((type(self.game.scene).__name__, kind, value))
        window = self.game.backend.window
        if kind == "restart":
            self.game.clear_and_push(TitleScene(value))
        elif kind == "key":
            symbol = getattr(key, value)
            window.dispatch_event("on_key_press", symbol, 0)
            window.dispatch_event("on_key_release", symbol, 0)
        else:
            if kind == "button":
                control = self.game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == value and item.enabled)
                assert control is not None, f"no enabled button: {value}"
                x, y, width, height = control.bounds
                value = (x + width / 2, y + height / 2)
            x, y = value
            scale = min(window.width / self.game.width, window.height / self.game.height)
            px = (window.width - self.game.width * scale) / 2 + x * scale
            py = (window.height - self.game.height * scale) / 2 + (self.game.height - y) * scale
            window.dispatch_event("on_mouse_motion", round(px), round(py), 0, 0)
            window.dispatch_event("on_mouse_press", round(px), round(py), mouse.LEFT, 0)
            window.dispatch_event("on_mouse_release", round(px), round(py), mouse.LEFT, 0)


def soak(args):
    os.environ["SAGA2D_HEADLESS"] = "1"
    os.environ["SAGA2D_SILENT"] = "1"
    sys.path.insert(0, str(ROOT))
    from saga2d import Game
    from eador.model import State
    from eador.scene import ShardScene, TitleScene

    output = args.output
    manifest = json.loads((output / "manifest.json").read_text())
    started = time.monotonic()
    samples, frame_window, scenes = [], [], Counter()
    report = {"status": "starting", "pid": os.getpid(), "requested_seconds": args.seconds,
              "source_commit": manifest["source_commit"], "source_manifest": "manifest.json",
              "game_framework_last_change": manifest["game_framework_last_change"],
              "started_utc": datetime.now(timezone.utc).isoformat(), "fps_cap": 60,
              "input_interval_seconds": args.input_interval, "resolution": [1280, 800],
              "platform": platform.platform(), "architecture": platform.machine(),
              "latency_measurement": "Game.tick only: input dispatch, updates and real rendering; excludes pacing, driver setup, screenshots and report I/O",
              "latency_file": "latency-ms.f64", "latency_byte_order": sys.byteorder,
              "scope": "Repeated prepared opening journeys; 8 seeds, 4 hero classes, one persistent hidden Pyglet window; silent audio driver. Not full campaigns or human playtesting."}
    for name in ("hw.model", "machdep.cpu.brand_string", "hw.memsize"):
        report[name] = subprocess.check_output(["sysctl", "-n", name], text=True).strip()
    awake = subprocess.Popen(["/usr/bin/caffeinate", "-dims", "-w", str(os.getpid())])
    game = None
    journey = None
    frames = 0
    write_json(output / "progress.json", report)

    def progress(status="running"):
        elapsed = time.monotonic() - started
        sample = {"elapsed_seconds": elapsed, "rss_bytes": rss_bytes(), "frames": frames,
                  "window_latency": percentiles(frame_window)}
        samples.append(sample)
        frame_window.clear()
        report.update(status=status, elapsed_seconds=elapsed, frames=frames, rss_samples=samples,
                      scene_frames=dict(scenes), completed_journeys=journey.cycles if journey else 0,
                      actions=dict(journey.counts) if journey else {}, last_actions=list(journey.history) if journey else [])
        write_json(output / "progress.json", report)
        with (output / "minutes.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({**sample, "status": status, "journeys": report["completed_journeys"]}) + "\n")
        print(f"{status}: {elapsed:.1f}s, {frames} frames, {report['completed_journeys']} journeys, "
              f"RSS {sample['rss_bytes'] / 1048576:.1f} MiB, p95 {sample['window_latency'].get('p95_ms', 0):.2f} ms", flush=True)

    try:
        with tempfile.TemporaryDirectory(prefix="shardbound-soak-saves-") as saves, (output / "latency-ms.f64").open("wb") as timing:
            report["temporary_save_directory"] = saves
            game = Game("Shardbound real-backend soak", resolution=(1280, 800), visible=False, save_dir=Path(saves) / "saves",
                        asset_path=ROOT / "eador" / "assets")
            # Pyglet's Cocoa event loop installs its own SIGTERM handler at startup.
            signal.signal(signal.SIGTERM, cancel_run)
            signal.signal(signal.SIGINT, cancel_run)
            from pyglet.gl import gl_info
            report.update(backend=type(game.backend).__name__, gl_vendor=gl_info.get_vendor(),
                          gl_renderer=gl_info.get_renderer(), gl_version=gl_info.get_version_string(),
                          window_pixels=[game.backend.window.width, game.backend.window.height])
            game.push(TitleScene(7))
            journey = Journey(game)
            started = time.monotonic()  # Duration excludes source freezing and window startup.
            progress()
            next_frame = started
            next_input = started
            next_minute = started + 60
            next_capture = started + 600
            captured = set()
            while time.monotonic() - started < args.seconds:
                remaining = next_frame - time.monotonic()
                if remaining > 0:
                    time.sleep(remaining)
                now = time.monotonic()
                if now >= next_input:
                    journey.step()
                    next_input = now + args.input_interval
                before = time.perf_counter()
                game.tick(1 / 60)
                latency = (time.perf_counter() - before) * 1000
                timing.write(struct.pack("d", latency))
                frame_window.append(latency)
                frames += 1
                assert game.running and game.scene is not None and len(game.scenes) <= 4
                name = type(game.scene).__name__
                scenes[name] += 1
                now = time.monotonic()
                if name not in captured or now >= next_capture:
                    stamp = int(now - started)
                    game.backend.capture_frame().save(output / f"{stamp:05d}-{name}.png")
                    captured.add(name)
                    if now >= next_capture:
                        next_capture = now + 600
                if now >= next_minute:
                    shard = next((scene for scene in game.scenes if isinstance(scene, ShardScene)), None)
                    if shard:
                        serialized = shard.state.to_json()
                        assert State.from_json(serialized).to_json() == serialized
                    timing.flush()
                    progress()
                    next_minute = now + 60
                # Never catch up missed frames in an unpaced burst.
                next_frame = max(next_frame + 1 / 60, time.monotonic())
            game.backend.capture_frame().save(output / "final.png")
            progress("completed")
    except BaseException as error:
        report["error"] = traceback.format_exc()
        progress("cancelled" if isinstance(error, KeyboardInterrupt) else "failed")
        raise
    finally:
        try:
            if game is not None:
                try:
                    game._teardown()
                finally:
                    game.backend.quit()
        finally:
            awake.terminate()
            awake.wait(timeout=5)
            report["cleanup"] = {"window_closed": game is None or game.backend.window is None,
                                 "awake_helper_exited": awake.poll() is not None,
                                 "temporary_saves_removed": not Path(report["temporary_save_directory"]).exists()
                                 if "temporary_save_directory" in report else True}
            report["two_hour_duration_satisfied"] = report.get("elapsed_seconds", 0) >= 7200 and report["status"] == "completed"
            regular = samples[1:]  # Exclude the pre-render baseline from comparison windows.
            first, last = regular[:5], regular[-5:]
            if regular:
                first_mean = statistics.mean(sample["rss_bytes"] for sample in first)
                last_mean = statistics.mean(sample["rss_bytes"] for sample in last)
                report["memory"] = {"first_window_samples": len(first), "last_window_samples": len(last),
                                    "comparison_windows_disjoint": len(regular) >= 10,
                                    "first_window_elapsed_seconds": [sample["elapsed_seconds"] for sample in first],
                                    "last_window_elapsed_seconds": [sample["elapsed_seconds"] for sample in last],
                                    "first_window_mean_bytes": first_mean, "last_window_mean_bytes": last_mean,
                                    "growth_bytes": last_mean - first_mean,
                                    "growth_percent": (last_mean / first_mean - 1) * 100,
                                    "peak_sampled_rss_bytes": max(sample["rss_bytes"] for sample in samples),
                                    "process_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
            latency_path = output / "latency-ms.f64"
            if latency_path.exists():
                from array import array
                values = array("d")
                with latency_path.open("rb") as stream:
                    values.fromfile(stream, latency_path.stat().st_size // values.itemsize)
                report["latency"] = percentiles(values)
            report["finished_utc"] = datetime.now(timezone.utc).isoformat()
            report["source_snapshot_unchanged"] = hashes(ROOT) == manifest["source_sha256"]
            report["loaded_game_modules"] = {name: module.__file__ for name, module in sys.modules.items()
                                             if name.split(".")[0] in ("eador", "saga2d") and getattr(module, "__file__", None)}
            report["all_game_modules_from_snapshot"] = all(Path(path).resolve().is_relative_to(ROOT)
                                                            for path in report["loaded_game_modules"].values())
            write_json(output / "report.json", report)
            write_json(output / "progress.json", report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=7200)
    parser.add_argument("--input-interval", type=float, default=.25)
    parser.add_argument("--revision", default="HEAD", help="Committed game/framework revision to freeze (default HEAD)")
    parser.add_argument("--output", type=Path, default=Path("dist/soak") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not (math.isfinite(args.seconds) and args.seconds > 0 and math.isfinite(args.input_interval) and args.input_interval >= 1 / 60):
        parser.error("seconds must be positive and input-interval must be at least 1/60 second")
    if platform.system() != "Darwin":
        parser.error("This harness is currently verified only on macOS (RSS units and caffeinate).")
    args.output = args.output.resolve()
    if not args.worker:
        source = freeze(args.output, args.revision)
        os.execv(sys.executable, [sys.executable, str(source / "tools" / "soak_eador.py"), "--worker",
                                "--output", str(args.output), "--seconds", str(args.seconds),
                                "--input-interval", str(args.input_interval)])
    signal.signal(signal.SIGTERM, cancel_run)
    soak(args)


if __name__ == "__main__":
    main()
