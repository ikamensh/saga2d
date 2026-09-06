"""Build a standalone Shardbound development artifact and verify the archive.

Run from the repository root:
uv run --locked --isolated --python 3.13.2 --with-requirements packaging/requirements.txt python tools/build_eador.py
"""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import sysconfig
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
TOOL_VERSIONS = {"pyinstaller": "6.22.2", "pyinstaller-hooks-contrib": "2026.7"}
RUNTIME_PACKAGES = ("numpy", "Pillow", "pyglet")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(command, **kwargs):
    subprocess.run([str(arg) for arg in command], check=True, **kwargs)


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def collect_package_data(source: Path) -> dict:
    """Return the exact, ordered non-Python package files the artifact will ship."""
    return {path.relative_to(source).as_posix():
            {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for package in ("eador", "saga2d")
            for path in sorted((source / package).rglob("*"))
            if path.is_file() and path.suffix not in (".py", ".pyc")
            and "__pycache__" not in path.parts}


def validate_audio(source: Path) -> None:
    """Reject missing, unrecorded or stale shipping WAVs and their generator inputs."""
    assets = source / "eador" / "assets"
    manifest = json.loads((assets / "audio-manifest.json").read_text(encoding="utf-8"))
    actual = {path.relative_to(assets).as_posix() for path in assets.rglob("*.wav")}
    expected = set(manifest["files"])
    if actual != expected:
        raise RuntimeError(f"Audio catalogue differs from manifest: missing={sorted(expected - actual)}, "
                           f"unrecorded={sorted(actual - expected)}")
    for name, record in manifest["files"].items():
        path = assets / name
        if path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
            raise RuntimeError(f"Audio asset differs from manifest: {name}; rebuild audio before packaging")
    for name, expected_hash in manifest["source_sha256"].items():
        if sha256(source / name) != expected_hash:
            raise RuntimeError(f"Audio generator differs from manifest: {name}; rebuild audio before packaging")


def snapshot_sources(source: Path) -> dict:
    """Freeze application, build recipe and verified package-data inputs before PyInstaller runs."""
    if source.exists():
        shutil.rmtree(source)
    source.mkdir(parents=True)
    for package in ("saga2d", "eador"):
        shutil.copytree(ROOT / package, source / package,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("entry.py", "campaign_check.py", "shardbound.spec"):
        shutil.copyfile(ROOT / "packaging" / name, source / name)
    (source / "tools").mkdir()
    (source / "tools" / "__init__.py").write_text('"""Frozen public-input verification helpers."""\n')
    for name in ("build_eador.py", "build_eador_audio.py", "eador_ui.py",
                 "eador_campaign.py", "eador_linked_campaign.py"):
        shutil.copyfile(ROOT / "tools" / name, source / "tools" / name)
    validate_audio(source)
    data = collect_package_data(source)
    write_json(source / "package-data.json", data)
    return data


def copy_licenses(destination: Path) -> None:
    for name in (*RUNTIME_PACKAGES, "pyinstaller"):
        distribution = metadata.distribution(name)
        licenses = [path for path in distribution.files
                    if any(part.lower().startswith(("license", "copying", "copyright"))
                           for part in path.parts)]
        if not licenses:
            raise RuntimeError(f"No installed license files found for {name}")
        for relative in licenses:
            target = destination / name / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(distribution.locate_file(relative), target)
    python_license = Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"
    if not python_license.exists():
        python_license = Path(sys.base_prefix) / "LICENSE.txt"
    shutil.copyfile(python_license, destination / "CPython-LICENSE.txt")


def snapshot(source: Path) -> dict:
    data = snapshot_sources(source)
    release = source / "release"
    release.mkdir()
    for origin, name in [(ROOT / "LICENSE", "LICENSE"),
                         (ROOT / "eador" / "README.md", "player-guide.md"),
                         (ROOT / "packaging" / "credits.md", "credits.md"),
                         (ROOT / "packaging" / "requirements.txt", "build-tools.txt"),
                         (ROOT / "uv.lock", "runtime-uv.lock")]:
        shutil.copyfile(origin, release / name)
    copy_licenses(release / "licenses")
    source_hashes = {str(path.relative_to(source)): sha256(path)
                     for path in sorted(source.rglob("*")) if path.is_file()}
    info = {
        "product": "Shardbound", "version": "0.1.0-development",
        "release_ready": False,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "working_tree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)),
        "platform": platform.platform(), "architecture": platform.machine(),
        "python": platform.python_version(),
        "packages": {name: metadata.version(name) for name in (*RUNTIME_PACKAGES, *TOOL_VERSIONS)},
        "source_sha256": source_hashes,
        "package_data": data,
        "spec_sha256": sha256(source / "shardbound.spec"),
        "validation_scope": "Local host only; no clean account, Windows, signing or notarization claim.",
    }
    write_json(release / "build-info.json", info)
    return info


def inventory(folder: Path) -> dict:
    contents = {}
    for path in sorted(folder.rglob("*")):
        name = str(path.relative_to(folder))
        if path.is_symlink():
            contents[name] = {"symlink": os.readlink(path)}
        elif path.is_file():
            contents[name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    return contents


def verify_campaign_processes(executable: Path, folder: Path, env: dict, output: Path, *, recovery=False) -> dict:
    """Run actual app lifetimes; load departures and the ending through Title F9."""
    phases = []
    for phase in range(1, 6 if recovery else 5):
        command = [executable, '--campaign-check', output, '--phase', phase]
        if recovery:
            command.append('--recovery')
        run(command, cwd=folder, env=env, timeout=180)
        report = json.loads((output / f'phase-{phase}.json').read_text())
        if not report['frozen'] or Path(report['executable']).resolve() != executable.resolve():
            raise RuntimeError('Campaign check did not run the extracted executable.')
        if not Path(report['asset_path']).resolve().is_relative_to(folder.resolve()):
            raise RuntimeError('Campaign check loaded assets from outside the archive.')
        if phases and report['loaded_checkpoint'] != phases[-1]['checkpoint']:
            raise RuntimeError('Campaign process restart changed the saved State.')
        phases.append(report)
    if not phases[-1]['returned_to_title'] or len(phases[-1]['completed_shards']) != 3:
        raise RuntimeError('Packaged linked campaign did not complete and return to title.')
    return dict(recovery=recovery, processes=len(phases), process_ids=[p['process_id'] for p in phases],
                input_activations=sum(p['input_activations'] for p in phases),
                exact_save_reloads=sum(p['exact_save_reloads'] for p in phases),
                exact_process_restarts=len(phases) - 1, completed_shards=phases[-1]['completed_shards'],
                reports=[f'phase-{p["phase"]}.json' for p in phases])


def smoke_archive(archive: Path, output: Path, macos: bool, package_data: dict, *, campaign=False) -> dict:
    with TemporaryDirectory(prefix="shardbound-outside-repo-") as temporary:
        folder = Path(temporary)
        if macos:
            run(["/usr/bin/ditto", "-x", "-k", archive, folder])
            executable = folder / "Shardbound.app" / "Contents" / "MacOS" / "Shardbound"
        else:
            shutil.unpack_archive(archive, folder)
            executable = folder / "Shardbound" / "Shardbound.exe"
        env = {key: value for key, value in os.environ.items()
               if key not in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")}
        env["PATH"] = os.defpath
        env["PYTHONNOUSERSITE"] = "1"
        image = output / "packaged-smoke.png"
        run([executable, "--smoke-image", image], cwd=folder, env=env, timeout=90)
        report = json.loads(image.with_suffix(".json").read_text())
        if not all(report[key] for key in ("frozen", "save_load_roundtrip", "codex_and_rival_rendered",
                                          "battle_save_load_roundtrip", "guard_save_load_roundtrip",
                                          "settings_apply_cancel_restart", "audio_catalogue_decoded_and_played",
                                          "audio_live_mix_and_cleanup", "native_input_journey")):
            raise RuntimeError(f"Packaged smoke verification failed: {report}")
        if Path(report["executable"]).resolve() != executable.resolve():
            raise RuntimeError("Smoke verification did not run the extracted executable")
        if not Path(report["asset_path"]).resolve().is_relative_to(folder.resolve()):
            raise RuntimeError("Smoke verification loaded audio from outside the extracted archive")
        expected_audio = {name.removeprefix("eador/assets/"): record for name, record in package_data.items()
                          if name.startswith("eador/assets/") and name.endswith(".wav")}
        actual_audio = {name: {key: record[key] for key in ("bytes", "sha256")}
                        for name, record in report["audio_files"].items()}
        if actual_audio != expected_audio:
            raise RuntimeError("Packaged audio bytes differ from the build source snapshot")
        if campaign:
            campaign_output = output / 'campaign-verification'
            if campaign_output.exists():
                shutil.rmtree(campaign_output)
            report['linked_campaigns'] = {
                name: verify_campaign_processes(executable, folder, env, campaign_output / name, recovery=recovery)
                for name, recovery in (('direct', False), ('recovery', True))}
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-smoke", action="store_true", help="build only; artifact remains unverified")
    parser.add_argument("--check-campaign", action="store_true", help="also complete three linked shards across app restarts")
    args = parser.parse_args()
    if args.skip_smoke and args.check_campaign:
        parser.error('--check-campaign requires the extracted archive smoke check')
    if sys.platform not in ("darwin", "win32"):
        parser.error("This recipe currently targets macOS and Windows only")
    if platform.python_version() != "3.13.2":
        parser.error("Use the documented Python 3.13.2 build command")
    for name, expected in TOOL_VERSIONS.items():
        if metadata.version(name) != expected:
            parser.error(f"Expected {name}=={expected}; use packaging/requirements.txt")
    macos = sys.platform == "darwin"
    if not macos and platform.machine().lower() not in ("amd64", "x86_64"):
        parser.error("Windows packaging requires an x64 Python runtime")
    work = ROOT / "build" / "shardbound"
    source = work / "source"
    output = ROOT / "dist" / "shardbound"
    output.mkdir(parents=True, exist_ok=True)
    info = snapshot(source)
    env = {**os.environ, "SHARDBOUND_BUILD_SOURCE": str(source)}
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
         "--distpath", output, "--workpath", work / "pyinstaller",
         source / "shardbound.spec"], cwd=source, env=env)
    artifact = output / ("Shardbound.app" if macos else "Shardbound")
    target = "macos-" + platform.machine() if macos else "windows-x64"
    archive = output / f"Shardbound-{target}.zip"
    if macos:
        run(["/usr/bin/ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", artifact, archive])
    else:
        shutil.make_archive(str(archive.with_suffix("")), "zip", output, artifact.name)
    info["artifact"] = {"file": archive.name, "sha256": sha256(archive), "bytes": archive.stat().st_size}
    info["files"] = inventory(artifact)
    info["smoke"] = None if args.skip_smoke else smoke_archive(
        archive, output, macos, info["package_data"], campaign=args.check_campaign)
    write_json(output / "build-manifest.json", info)
    print(f"Built {archive}\nSHA256 {info['artifact']['sha256']}\nManifest {output / 'build-manifest.json'}", flush=True)


if __name__ == "__main__":
    main()
