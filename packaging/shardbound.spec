# Executed by PyInstaller. Build inputs are snapshotted by tools/build_eador.py.
import os
from pathlib import Path
import sys

source = Path(os.environ["SHARDBOUND_BUILD_SOURCE"])
datas = [(str(source / "release"), "release")]
for package in ("eador", "saga2d"):
    for path in sorted((source / package).rglob("*")):
        if path.is_file() and path.suffix not in (".py", ".pyc"):
            datas.append((str(path), str(path.parent.relative_to(source))))

a = Analysis(
    [str(source / "entry.py")],
    pathex=[str(source)],
    datas=datas,
    hiddenimports=["saga2d.backends.pyglet_backend"],
    excludes=["pytest", "anthropic", "tribes", "tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="Shardbound",
    debug=False, strip=False, upx=False, console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Shardbound")
if sys.platform == "darwin":
    app = BUNDLE(
        coll, name="Shardbound.app", bundle_identifier="org.saga2d.shardbound",
        version="0.1.0",
        info_plist={
            "CFBundleDisplayName": "Shardbound",
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright": "Shardbound / Saga2D contributors. See bundled release/credits.md.",
        },
    )
