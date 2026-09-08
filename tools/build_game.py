"""Build a versioned standalone Tribes or Warband; verification is a separate recorded step.

uv run --locked --isolated --python 3.13.2 --with-requirements packaging/requirements.txt \
    python tools/build_game.py warband --version 0.1.0 --installer

Shardbound keeps its own recipe in tools/build_eador.py because it ships
verified audio and art assets; these two games generate everything at runtime.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("numpy", "Pillow", "pyglet", "websockets")
TOOLS = {"pyinstaller": "6.22.2", "pyinstaller-hooks-contrib": "2026.7"}
GAMES = {
    "warband": {
        "product": "Warband", "package": "warband", "bundle_id": "org.saga2d.warband",
        "installer_id": "{B51768BC-40A4-4705-BE86-D55131C7B414}",
        "hiddenimports": ["saga2d.backends.pyglet_backend", "warband.textures", "warband.sound", "websockets.asyncio.client"],
        "documents": {"windows-warband.md": "docs/windows-warband.md", "warband-play-together.md": "docs/warband-play-together.md"},
    },
    "tribes": {
        "product": "Tribes", "package": "tribes", "bundle_id": "org.saga2d.tribes",
        "installer_id": "{E28B2BAE-57BB-442E-A6F6-6E29AFCA6AB6}",
        "hiddenimports": ["saga2d.backends.pyglet_backend", "tribes.textures", "tribes.sound", "websockets.asyncio.client"],
        "documents": {"online-multiplayer.md": "docs/online-multiplayer.md", "tribes-scores.md": "docs/tribes-scores.md"},
    },
}


def version(value: str) -> str:
    """Use a filename-safe version that Inno Setup can also represent numerically."""
    match = re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?", value)
    if match is None or any(int(part) > 65535 for part in match.groups()):
        raise argparse.ArgumentTypeError("Use MAJOR.MINOR.PATCH with an optional prerelease suffix; each number must be <=65535.")
    return value


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def copy_licenses(output: Path) -> None:
    output.mkdir(parents=True)
    for name in (*RUNTIME, "pyinstaller"):
        distribution = metadata.distribution(name)
        found = False
        for item in distribution.files or ():
            if any(part.upper().startswith(("LICENSE", "COPYING")) for part in item.parts):
                origin = Path(distribution.locate_file(item))
                if origin.is_file():
                    target = output / name / item
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(origin, target)
                    found = True
        if not found:
            raise RuntimeError(f"No license files found for {name}")
    candidates = [Path(sys.base_prefix) / "LICENSE.txt", Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"]
    python_license = next((path for path in candidates if path.is_file()), None)
    if python_license is None:
        raise FileNotFoundError("The build interpreter must include CPython's LICENSE.txt")
    shutil.copyfile(python_license, output / "CPython-LICENSE.txt")


def build(game: str, args) -> None:
    spec = GAMES[game]
    product = spec["product"]
    if platform.python_version() != "3.13.2":
        raise RuntimeError("Build with the pinned CPython 3.13.2 command in the module docstring")
    for name, expected in TOOLS.items():
        if metadata.version(name) != expected:
            raise RuntimeError(f"{name} must be {expected}")
    if args.installer and platform.system() != "Windows":
        raise RuntimeError("The Windows installer must be built on Windows")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    if args.require_clean and dirty:
        raise RuntimeError("Release builds require a clean working tree")
    output = (args.output or ROOT / "dist" / game).resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = ROOT / "build" / game
    source = work / "source"
    if source.exists():
        shutil.rmtree(source)
    source.mkdir(parents=True)
    for package in ("saga2d", spec["package"]):
        shutil.copytree(ROOT / package, source / package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in (f"{game}_entry.py", f"{game}_package_check.py", "game.spec", "game.iss"):
        shutil.copyfile(ROOT / "packaging" / name, source / name)
    release = source / "release"
    release.mkdir()
    documents = {"LICENSE": "LICENSE", **spec["documents"], "uv.lock": "uv.lock", "build-tools.txt": "packaging/requirements.txt"}
    for name, origin in documents.items():
        shutil.copyfile(ROOT / origin, release / name)
    copy_licenses(release / "licenses")
    info = {
        "product": product, "game": game, "version": args.version, "source_commit": commit, "working_tree_dirty": dirty,
        "built_at_utc": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
        "architecture": platform.machine(), "python": platform.python_version(),
        "packages": {name: metadata.version(name) for name in (*RUNTIME, *TOOLS)},
        "source_sha256": {path.relative_to(source).as_posix(): sha256(path) for path in sorted(source.rglob("*")) if path.is_file()},
        "packaging": {"package": spec["package"], "entry": f"{game}_entry.py", "bundle_id": spec["bundle_id"],
                      "hiddenimports": spec["hiddenimports"],
                      "excludes": ["pytest", "anthropic", "tkinter", *sorted({"eador", "tribes", "warband"} - {spec["package"]})]},
        "runtime_verified": False,
    }
    write_json(release / "build-info.json", info)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", str(output),
                    "--workpath", str(work / "pyinstaller"), str(source / "game.spec")], cwd=ROOT,
                   env={**os.environ, "SAGA2D_BUILD_SOURCE": str(source)}, check=True)
    target = "windows-x64" if platform.system() == "Windows" else f"{platform.system().lower()}-{platform.machine().lower()}"
    archive = Path(shutil.make_archive(str(output / f"{product}-{args.version}-{target}-portable"), "zip", output, product))
    artifacts = [archive]
    if args.installer:
        compiler = args.iscc or shutil.which("ISCC.exe")
        if not compiler:
            candidate = Path(os.environ["ProgramFiles(x86)"]) / "Inno Setup 6" / "ISCC.exe"
            if candidate.is_file():
                compiler = str(candidate)
        if not compiler:
            raise FileNotFoundError("Install Inno Setup or pass --iscc with the path to ISCC.exe")
        subprocess.run([str(compiler), f"/DAppName={product}", f"/DAppId={spec['installer_id']}",
                        f"/DAppVersion={args.version}", f"/DAppNumericVersion={args.version.partition('-')[0]}.0",
                        f"/DSourceDir={output / product}", f"/DOutputDir={output}", str(source / "game.iss")], check=True)
        artifacts.append(output / f"{product}-{args.version}-windows-x64-setup.exe")
    info["artifacts"] = [{"file": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)} for path in artifacts]
    write_json(output / "build-manifest.json", info)
    (output / "SHA256SUMS").write_text("".join(f"{item['sha256']}  {item['file']}\n" for item in info["artifacts"]), encoding="ascii")
    print(f"Built {product} {args.version} from {commit}. Run tools/verify_game_package.py before publishing.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game", choices=sorted(GAMES))
    parser.add_argument("--version", required=True, type=version)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--installer", action="store_true")
    parser.add_argument("--iscc", type=Path)
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    build(args.game, args)


if __name__ == "__main__":
    main()
