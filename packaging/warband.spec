"""PyInstaller recipe; tools/build_warband.py freezes every source input first."""
import os
from pathlib import Path
import sys

source = Path(os.environ["WARBAND_BUILD_SOURCE"])
a = Analysis(
    [str(source / "warband_entry.py")], pathex=[str(source)],
    datas=[(str(source / "saga2d/assets/fonts"), "saga2d/assets/fonts"), (str(source / "release"), "release")],
    hiddenimports=["saga2d.backends.pyglet_backend", "warband.textures", "warband.sound", "websockets.asyncio.client"],
    excludes=["pytest", "anthropic", "eador", "tribes", "tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Warband", debug=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Warband")
if sys.platform == "darwin":
    app = BUNDLE(coll, name="Warband.app", bundle_identifier="org.saga2d.warband", info_plist={"NSHighResolutionCapable": True})
