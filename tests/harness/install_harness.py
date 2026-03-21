"""Install harness — verifies saga2d can be installed in a clean environment.

Uses README.md instructions: pip install -e .
Creates a temporary venv, installs the package, runs a minimal verification.

Run: python -m tests.harness.install_harness
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def _project_root() -> Path:
    """Project root (directory containing pyproject.toml)."""
    return Path(__file__).resolve().parent.parent.parent


def _verify_script() -> str:
    """Minimal script to verify install: import, Game(mock), tick."""
    return """
import saga2d
game = saga2d.Game("InstallTest", resolution=(800, 600), backend="mock")
game.tick(0.016)
game._teardown()
print("OK")
"""


def run_harness(verbose: bool = False) -> bool:
    """Create clean venv, pip install -e ., verify. Returns True on success."""
    root = _project_root()
    if not (root / "pyproject.toml").exists():
        if verbose:
            print(f"pyproject.toml not found at {root}")
        return False

    with tempfile.TemporaryDirectory(prefix="saga2d_install_") as tmp:
        venv = Path(tmp) / "venv"
        if verbose:
            print(f"Creating venv at {venv}")

        # Create venv
        r = subprocess.run(
            [sys.executable, "-m", "venv", str(venv)],
            cwd=str(root),
            capture_output=not verbose,
            text=True,
        )
        if r.returncode != 0:
            if verbose and r.stderr:
                print(r.stderr)
            return False

        if (venv / "bin" / "pip").exists():
            pip = venv / "bin" / "pip"
            python = venv / "bin" / "python"
        else:
            pip = venv / "Scripts" / "pip.exe"
            python = venv / "Scripts" / "python.exe"

        # pip install -e .
        if verbose:
            print("Running: pip install -e .")
        r = subprocess.run(
            [str(pip), "install", "-e", "."],
            cwd=str(root),
            capture_output=not verbose,
            text=True,
        )
        if r.returncode != 0:
            if verbose and r.stderr:
                print(r.stderr)
            return False

        # Verify: import saga2d, Game(mock), tick
        if verbose:
            print("Verifying: import saga2d, Game(mock), tick")
        r = subprocess.run(
            [str(python), "-c", _verify_script().strip()],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            if verbose and r.stderr:
                print(r.stderr)
            return False
        if "OK" not in r.stdout:
            return False

    return True


def main() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    ok = run_harness(verbose=verbose)
    if verbose and ok:
        print("Install harness: PASS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
