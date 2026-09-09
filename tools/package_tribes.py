"""Build, verify and install the standalone Tribes app.

    uv run --extra package python tools/package_tribes.py build --version 0.1.0 --installer
    uv run --extra package python tools/package_tribes.py verify dist/tribes --native
    uv run --extra package python tools/package_tribes.py install
"""
from pathlib import Path

from saga2d.packaging import GamePackage, main

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = GamePackage(
    game="tribes", product="Tribes", package="tribes", online="tribes.multiplayer:ONLINE",
    bundle_id="org.saga2d.tribes", installer_id="{E28B2BAE-57BB-442E-A6F6-6E29AFCA6AB6}",
    hiddenimports=("saga2d.backends.pyglet_backend", "tribes.textures", "tribes.sound", "websockets.asyncio.client"),
    documents={"online-multiplayer.md": "docs/online-multiplayer.md", "tribes-scores.md": "docs/tribes-scores.md"},
    root=ROOT, check=ROOT / "packaging" / "tribes_package_check.py",
)

if __name__ == "__main__":
    main(PACKAGE)
