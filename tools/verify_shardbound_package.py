"""Verify a built Shardbound archive, its online client and the Windows installer.

    uv run python tools/verify_shardbound_package.py dist/shardbound --public-server wss://games.tachyon-ai.eu/play

The extracted application runs the frozen smoke journey outside the checkout with
an isolated profile, then the online diagnostic against a loopback room server.
On Windows the installer is installed silently, checked the same way (plus the
public server when requested) and uninstalled. ``--mesa-dir`` supplies a
test-only software GL driver for CI hosts; it never touches shipping files.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_eador import check_shipped_audio, clean_environment, extract_archive, run_smoke, sha256, write_json  # noqa: E402
from saga2d.packaging.verify import local_server, mesa_test_context  # noqa: E402


def online_check(executable: Path, endpoint: str, report: Path, env: dict, manifest: dict) -> dict:
    subprocess.run([str(executable), "--online-smoke", str(report), "--endpoint", endpoint],
                   cwd=executable.parent, env=env, check=True, timeout=120)
    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["passed"] and result["source_commit"] == manifest["source_commit"], result
    assert result["version"] == manifest["version"] and result["executable_sha256"] == sha256(executable), result
    return result


def graphics_environment(profile: Path, graphics: dict) -> dict:
    env = clean_environment({"HOME": str(profile), "USERPROFILE": str(profile), "SAGA2D_SILENT": "1"})
    if os.name == "nt":
        env["APPDATA"], env["LOCALAPPDATA"] = str(profile / "Roaming"), str(profile / "Local")
    if graphics:
        env.update(GALLIUM_DRIVER="llvmpipe", LP_NUM_THREADS="2")
    return env


def application_checks(executable: Path, folder: Path, evidence: Path, name: str, manifest: dict, *,
                       loopback: str, public_server: str | None, mesa_dir: Path | None) -> dict:
    context = mesa_test_context(executable, mesa_dir) if mesa_dir is not None else nullcontext({})
    with tempfile.TemporaryDirectory(prefix="shardbound-clean-profile-") as directory, context as graphics:
        env = graphics_environment(Path(directory), graphics)
        report = run_smoke(executable, folder, evidence / f"{name}-smoke.png", env)
        check_shipped_audio(report, manifest["package_data"])
        result = {"smoke": {key: report[key] for key in ("frozen", "native_input_journey", "shard_controls_verified",
                                                         "audio_catalogue_decoded_and_played")},
                  "smoke_images": sorted(p.name for p in evidence.glob(f"{name}-smoke*.png")),
                  "loopback": online_check(executable, loopback, evidence / f"{name}-loopback.json", env, manifest)["online"]}
        if graphics:
            result["graphics_test_context"] = graphics
        if public_server is not None:
            result["public_server"] = {"endpoint": public_server, **online_check(
                executable, public_server, evidence / f"{name}-public-server.json", env, manifest)["online"]}
        return result


def verify(output: Path, *, public_server: str | None = None, mesa_dir: Path | None = None) -> dict:
    if public_server is not None and not public_server.startswith("wss://"):
        raise ValueError("Public-server acceptance requires an explicit wss:// TLS endpoint")
    output = output.resolve()
    manifest = json.loads((output / "build-manifest.json").read_text(encoding="utf-8"))
    if manifest["product"] != "Shardbound":
        raise ValueError(f"{output} does not hold a Shardbound build")
    for item in manifest["artifacts"]:
        path = output / item["file"]
        assert path.stat().st_size == item["bytes"] and sha256(path) == item["sha256"], path
    archive = next(output / item["file"] for item in manifest["artifacts"] if item["file"].endswith(".zip"))
    installers = [output / item["file"] for item in manifest["artifacts"] if item["file"].endswith("-setup.exe")]
    if public_server is not None and not installers:
        raise ValueError("Public-server acceptance requires the Windows installer artifact")
    evidence = output / "verification"
    evidence.mkdir(exist_ok=True)
    report = {"source_commit": manifest["source_commit"], "version": manifest["version"],
              "scope": "Isolated profile on the named host; loopback authority plus the requested public endpoint"}
    macos = sys.platform == "darwin"
    with tempfile.TemporaryDirectory(prefix="shardbound-extracted-") as directory, local_server("eador.multiplayer:ONLINE") as loopback:
        extracted = Path(directory)
        executable = extract_archive(archive, extracted, macos)
        report["portable"] = application_checks(executable, extracted, evidence, "portable", manifest,
                                                loopback=loopback, public_server=None, mesa_dir=mesa_dir)
        if installers:
            if os.name != "nt":
                raise RuntimeError("Installer verification requires Windows")
            installed = extracted / "Installed Shardbound"
            shortcut = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Shardbound/Shardbound.lnk"
            if shortcut.exists():
                raise RuntimeError("Run installer verification in a Windows account without an existing Shardbound installation")
            try:
                subprocess.run([str(installers[0]), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-",
                                f"/DIR={installed}", f"/LOG={evidence / 'install.log'}"], check=True, timeout=180)
                assert shortcut.is_file(), shortcut
                executable = installed / "Shardbound.exe"
                report["installed"] = application_checks(executable, installed, evidence, "installed", manifest,
                                                         loopback=loopback, public_server=public_server, mesa_dir=mesa_dir)
            finally:
                uninstaller = installed / "unins000.exe"
                if uninstaller.is_file():
                    subprocess.run([str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                                    f"/LOG={evidence / 'uninstall.log'}"], check=True, timeout=180)
            assert not executable.exists() and not shortcut.exists(), "Uninstall left the application or Start menu shortcut"
            report["install_shortcut_uninstall"] = True
    report["passed"] = True
    write_json(output / "verification.json", report)
    print(json.dumps(report, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--public-server", help="Also require the installed executable to pass its online check over this wss:// endpoint")
    parser.add_argument("--mesa-dir", type=Path, help="Test-only x64 Mesa WGL DLLs for CI hosts without a graphics driver")
    args = parser.parse_args()
    verify(args.output, public_server=args.public_server, mesa_dir=args.mesa_dir)
