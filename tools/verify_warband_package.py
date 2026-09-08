"""Verify an extracted Warband archive and Windows install/launch/uninstall.

    uv run python tools/verify_warband_package.py dist/warband --native

Uses the production RoomServer over real loopback WebSockets. The application
process runs outside the checkout with an isolated profile and no Python on
PATH. A native rendering receipt is separate from mandatory socket acceptance.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_warband import sha256, write_json


@contextmanager
def local_server():
    """Run the actual room handler and simulation on an OS-assigned loopback port."""
    from online_server import MAX_MESSAGE, RoomServer
    from websockets.asyncio.server import serve
    ready, errors = queue.Queue(), queue.Queue()

    async def run():
        rooms = RoomServer(max_rooms=4, max_connections=8, room_ttl=30)
        stopped = asyncio.Event()
        async with serve(rooms.handle, "127.0.0.1", 0, process_request=rooms.health, origins=[None], max_size=MAX_MESSAGE,
                         compression=None, close_timeout=2) as server:
            task = asyncio.create_task(rooms.maintain())
            ready.put((asyncio.get_running_loop(), stopped, f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/play"))
            try:
                await stopped.wait()
            finally:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    def worker():
        try:
            asyncio.run(run())
        except Exception as exc:
            errors.put(exc)
            ready.put(None)

    thread = threading.Thread(target=worker, name="warband-package-authority", daemon=True)
    thread.start()
    started = ready.get(timeout=15)
    if started is None:
        raise errors.get()
    loop, stopped, endpoint = started
    try:
        yield endpoint
    finally:
        if thread.is_alive():
            loop.call_soon_threadsafe(stopped.set)
            thread.join(10)
        if thread.is_alive():
            raise RuntimeError("Package verification server did not stop")
        if not errors.empty():
            raise errors.get()


def isolated_environment(profile: Path, original=None) -> dict:
    """Keep OS/DLL configuration while excluding user Python and game overrides."""
    env = dict(os.environ if original is None else original)
    for name in ("PYTHONPATH", "PYTHONHOME", "SAGA2D_SERVER_URL", "SAGA2D_HEADLESS"):
        env.pop(name, None)
    env.update(HOME=str(profile), USERPROFILE=str(profile), SAGA2D_SILENT="1")
    if os.name == "nt":
        system_root = next(value for name, value in env.items() if name.upper() == "SYSTEMROOT")
        env["PATH"] = str(Path(system_root) / "System32") + os.pathsep + system_root
        env["APPDATA"], env["LOCALAPPDATA"] = str(profile / "Roaming"), str(profile / "Local")
    else:
        env["PATH"] = "/usr/bin:/bin"
    return env


def executable_smoke(executable: Path, endpoint: str, report: Path, manifest: dict, *, native=False) -> dict:
    with tempfile.TemporaryDirectory(prefix="warband-clean-profile-") as directory:
        profile = Path(directory)
        env = isolated_environment(profile)
        option = "--package-native-smoke" if native else "--package-smoke"
        target = report.with_suffix(".png") if native else report
        process = subprocess.run([str(executable), option, str(target), "--endpoint", endpoint], cwd=profile,
                                 env=env, capture_output=True, text=True, timeout=300 if native else 90)
        report.with_suffix(".log").write_text(process.stdout + process.stderr, encoding="utf-8")
        if not report.is_file():
            raise RuntimeError(f"The shipped executable produced no receipt: exit {process.returncode}; {process.stderr}")
        result = json.loads(report.read_text(encoding="utf-8"))
        if native and process.returncode and result.get("error_type") in {"NoSuchConfigException", "ContextException", "NoSuchDisplayException"}:
            result["status"] = "runner_has_no_supported_graphics_context"
            write_json(report, result)
            return result
        if process.returncode or not result["passed"]:
            raise RuntimeError(f"Packaged check failed: {result}")
        assert result["source_commit"] == manifest["source_commit"] and result["version"] == manifest["version"], result
        return result


def verify(output: Path, *, native=False) -> dict:
    output = output.resolve()
    manifest = json.loads((output / "build-manifest.json").read_text(encoding="utf-8"))
    for item in manifest["artifacts"]:
        path = output / item["file"]
        assert path.stat().st_size == item["bytes"] and sha256(path) == item["sha256"], path
    archive = next(output / item["file"] for item in manifest["artifacts"] if item["file"].endswith(".zip"))
    installers = [output / item["file"] for item in manifest["artifacts"] if item["file"].endswith("-setup.exe")]
    evidence = output / "verification"
    evidence.mkdir(exist_ok=True)
    report = {"source_commit": manifest["source_commit"], "version": manifest["version"], "scope": "Loopback authority; isolated profile on the named CI host"}
    with tempfile.TemporaryDirectory(prefix="warband-extracted-") as directory, local_server() as endpoint:
        extracted = Path(directory)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(extracted)
        executable = extracted / "Warband" / ("Warband.exe" if os.name == "nt" else "Warband")
        if os.name != "nt":
            executable.chmod(executable.stat().st_mode | 0o111)
        report["portable"] = executable_smoke(executable, endpoint, evidence / "portable.json", manifest)
        if installers:
            if os.name != "nt":
                raise RuntimeError("Installer verification requires Windows")
            installed = extracted / "Installed Warband"
            group = f"Warband verification {manifest['version']}"
            shortcut = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs" / group / "Warband.lnk"
            try:
                subprocess.run([str(installers[0]), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-",
                                f"/DIR={installed}", f"/GROUP={group}", f"/LOG={evidence / 'install.log'}"], check=True, timeout=120)
                assert shortcut.is_file(), shortcut
                executable = installed / "Warband.exe"
                report["installed"] = executable_smoke(executable, endpoint, evidence / "installed.json", manifest)
                if native:
                    report["native"] = executable_smoke(executable, endpoint, evidence / "native.json", manifest, native=True)
            finally:
                uninstaller = installed / "unins000.exe"
                if uninstaller.is_file():
                    subprocess.run([str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                                    f"/LOG={evidence / 'uninstall.log'}"], check=True, timeout=120)
            assert not executable.exists() and not shortcut.exists(), "Uninstall left the application or Start menu shortcut"
            report["install_shortcut_uninstall"] = True
        elif native:
            report["native"] = executable_smoke(executable, endpoint, evidence / "native.json", manifest, native=True)
    report["passed"] = True
    write_json(output / "verification.json", report)
    print(json.dumps(report, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--native", action="store_true")
    args = parser.parse_args()
    verify(args.output, native=args.native)
