"""Build a standalone Warband for this machine with PyInstaller, then prove it runs.

    uv run --with pyinstaller python tools/build_warband.py [dist_dir]

The result is ``dist/Warband`` (a folder with the executable and its
libraries; on macOS also ``dist/Warband.app``).  After building, the
executable is launched with ``--selftest`` from a clean temporary directory
so fonts, procedural art, the sound files it generates and a rendered frame
are all exercised outside the repository.  Requires the display to be awake.
"""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    dist = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist"
    work = ROOT / "build"
    entry = ROOT / "tools" / "warband_entry.py"
    entry.write_text("from warband.__main__ import main\n\nmain()\n")
    fonts = ROOT / "saga2d" / "assets" / "fonts"
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", "Warband",
        "--distpath", str(dist), "--workpath", str(work), "--specpath", str(work),
        "--add-data", f"{fonts}{':' if platform.system() != 'Windows' else ';'}saga2d/assets/fonts",
        "--collect-submodules", "pyglet", "--hidden-import", "warband.textures", "--hidden-import", "warband.sound",
        str(entry),
    ]
    print(" ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)
    exe = dist / "Warband" / ("Warband.exe" if platform.system() == "Windows" else "Warband")
    digest = hashlib.sha256(exe.read_bytes()).hexdigest()[:16]
    with tempfile.TemporaryDirectory() as clean:
        png = Path(clean) / "selftest.png"
        env = {"HOME": clean, "SAGA2D_SILENT": "1", "PATH": "/usr/bin:/bin"}
        result = subprocess.run([str(exe), "--selftest", str(png)], cwd=clean, env=env, capture_output=True, text=True, timeout=300)
        print(result.stdout, result.stderr[-2000:])
        if result.returncode != 0 or not png.exists():
            raise SystemExit(f"selftest failed with code {result.returncode}")
        size = png.stat().st_size
    print(f"built {exe} ({exe.stat().st_size / 1e6:.1f} MB, sha256 {digest}) on {platform.platform()}; selftest frame {size} bytes")


if __name__ == "__main__":
    main()
