"""Build Tribes or Warband from the working tree and install the app on this Mac.

    uv run python tools/install_game.py warband                 # build, self-test, back up, install, self-test again
    uv run python tools/install_game.py warband --skip-build --output dist/warband-races
    uv run python tools/install_game.py tribes --version 0.1.0-local.test --allow-dirty

The build is the release recipe (``tools/build_game.py`` under the pinned
packaging environment), versioned ``<project version>-local.<commit>`` unless
``--version`` says otherwise, so an installed app always names the commit it
came from.  The previous ``/Applications/<Game>.app`` is kept under
``dist/local-app-backups/`` before the new bundle is copied in with ``ditto``
(which preserves the ad-hoc signature).  Both the fresh bundle and the
installed one must pass the game's ``--selftest`` (a hidden window, one frame
saved to PNG) before the install counts; the display must be awake for that,
so the self-tests run under ``caffeinate``.  A receipt with the commit, version
and executable hash is written beside the build.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = {"warband": "Warband", "tribes": "Tribes"}
BUILD_ENV = ["uv", "run", "--locked", "--isolated", "--python", "3.13.2", "--with-requirements", "packaging/requirements.txt", "python"]


def run(command: list[str], **kwargs) -> None:
    print("$", " ".join(str(part) for part in command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def default_version() -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    return f"{project}-local.{commit}"


def selftest(app: Path, png: Path) -> None:
    """The bundle starts a match in a hidden window and writes one frame, or fails loudly."""
    executable = app / "Contents" / "MacOS" / app.stem
    png.parent.mkdir(parents=True, exist_ok=True)
    run(["caffeinate", "-u", "-i", str(executable), "--selftest", str(png)], timeout=300)
    if not png.is_file() or png.stat().st_size < 10_000:
        raise RuntimeError(f"{app} self-test wrote no usable frame at {png}")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("game", choices=sorted(PRODUCTS))
    parser.add_argument("--version", default=None, help="build version (default: <project version>-local.<commit>)")
    parser.add_argument("--output", type=Path, default=None, help="build directory (default: dist/<game>-local)")
    parser.add_argument("--skip-build", action="store_true", help="install the bundle already in --output")
    parser.add_argument("--allow-dirty", action="store_true", help="build from an uncommitted working tree")
    parser.add_argument("--applications", type=Path, default=Path("/Applications"))
    args = parser.parse_args()
    if platform.system() != "Darwin":
        raise SystemExit("install_game.py installs Mac app bundles; on Windows run the installer from tools/build_game.py --installer.")
    product = PRODUCTS[args.game]
    output = (args.output or ROOT / "dist" / f"{args.game}-local").resolve()
    version = args.version or default_version()
    if not args.skip_build:
        if output.exists():
            shutil.rmtree(output)
        build = BUILD_ENV + ["tools/build_game.py", args.game, "--version", version, "--output", str(output)]
        if not args.allow_dirty:
            build.append("--require-clean")
        run(build)
    app = output / f"{product}.app"
    if not app.is_dir():
        raise SystemExit(f"No {app}; build first or pass --output")
    manifest = json.loads((output / "build-manifest.json").read_text(encoding="utf-8"))
    selftest(app, output / "selftest-built.png")

    installed = args.applications / f"{product}.app"
    backup = None
    if installed.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        backup = ROOT / "dist" / "local-app-backups" / f"{product}-before-{version}-{stamp}.app"
        backup.parent.mkdir(parents=True, exist_ok=True)
        run(["ditto", str(installed), str(backup)])
        shutil.rmtree(installed)
    run(["ditto", str(app), str(installed)])
    selftest(installed, output / "selftest-installed.png")

    executable = installed / "Contents" / "MacOS" / product
    receipt = {
        "game": args.game, "version": version, "commit": manifest["source_commit"], "installed": str(installed),
        "executable_sha256": sha256(executable), "backup": str(backup) if backup else None,
        "installed_at_utc": datetime.now(timezone.utc).isoformat(), "frames": ["selftest-built.png", "selftest-installed.png"],
    }
    (output / "install-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Installed {product} {version} ({receipt['commit']}) at {installed}; previous app backed up to {backup}. "
          f"Frames: {output / 'selftest-built.png'}, {output / 'selftest-installed.png'}")


if __name__ == "__main__":
    sys.exit(main())
