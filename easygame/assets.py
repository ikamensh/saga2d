"""Convention-based asset loading with caching and @2x variant support.

The :class:`AssetManager` resolves asset names to file paths under a
configurable base directory, loads them through the backend, and caches
the returned handles so repeated requests for the same asset are free.

Usage (from game code)::

    img = game.assets.image("sprites/knight")   # loads assets/images/sprites/knight.png
    img2 = game.assets.image("sprites/knight")  # returns cached handle

Resolution variant support::

    # If scale_factor >= 1.5 and "knight@2x.png" exists alongside "knight.png",
    # the @2x variant is loaded automatically.

The asset manager is owned by :class:`~easygame.game.Game` and exposed as
``game.assets``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class AssetNotFoundError(FileNotFoundError):
    """Raised when an asset file cannot be found.

    The message includes the attempted path(s) so the developer can see
    exactly what was looked up.
    """


# ---------------------------------------------------------------------------
# AssetManager
# ---------------------------------------------------------------------------

class AssetManager:
    """Convention-based asset loader with caching.

    Parameters:
        backend:      The backend instance (must implement ``load_image``).
        base_path:    Root directory for assets (e.g. ``Path("assets")``).
                      Resolved relative to CWD if not absolute.
        scale_factor: Display scale factor.  When ``>= 1.5``, the manager
                      prefers ``@2x`` image variants if they exist on disk.
    """

    def __init__(
        self,
        backend: Any,
        base_path: Path | str = Path("assets"),
        *,
        scale_factor: float = 1.0,
    ) -> None:
        self._backend = backend
        self._base_path = Path(base_path)
        self._scale_factor = scale_factor
        self._image_cache: dict[str, Any] = {}
        self._frames_cache: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Image loading
    # ------------------------------------------------------------------

    def image(self, name: str) -> Any:
        """Load an image by convention name and return an opaque handle.

        *name* is resolved under ``<base_path>/images/``.  If *name* has
        no file extension, ``.png`` is appended automatically.

        Examples::

            game.assets.image("sprites/knight")
            # → <base_path>/images/sprites/knight.png

            game.assets.image("backgrounds/forest.jpg")
            # → <base_path>/images/backgrounds/forest.jpg

        On high-DPI displays (``scale_factor >= 1.5``), the manager first
        checks for a ``@2x`` variant (e.g. ``knight@2x.png``).  If found
        it is loaded instead; otherwise the base file is used.

        Returns:
            An opaque ``ImageHandle``.

        Raises:
            AssetNotFoundError: If the file does not exist.
        """
        if name in self._image_cache:
            return self._image_cache[name]

        handle = self._load_image(name)
        self._image_cache[name] = handle
        return handle

    def _load_image(self, name: str) -> Any:
        """Resolve *name* to a path, try @2x variant, and load."""
        # Append .png if no extension given.
        if "." not in Path(name).name:
            name_with_ext = name + ".png"
        else:
            name_with_ext = name

        images_dir = self._base_path / "images"
        base_path = images_dir / name_with_ext

        # On high-DPI, try @2x variant first.
        if self._scale_factor >= 1.5:
            hi_res_path = _make_2x_path(base_path)
            if hi_res_path.exists():
                return self._backend.load_image(str(hi_res_path))

        # Fall back to base resolution.
        if base_path.exists():
            return self._backend.load_image(str(base_path))

        # Nothing found — raise with clear message.
        tried = [str(base_path)]
        if self._scale_factor >= 1.5:
            tried.insert(0, str(_make_2x_path(base_path)))

        raise AssetNotFoundError(
            f"Image asset '{name}' not found.  "
            f"Looked in: {', '.join(tried)}"
        )

    # ------------------------------------------------------------------
    # Animation frames
    # ------------------------------------------------------------------

    def frames(self, prefix: str) -> list[str]:
        """Discover numbered animation frames by prefix.

        Finds files matching ``{prefix}_01.png``, ``{prefix}_02.png``, etc.
        under ``<base_path>/images/``.  Returns a list of asset names
        (suitable for :meth:`image`) sorted by frame number.  Result is
        cached.

        Example::

            game.assets.frames("sprites/knight_walk")
            # → ["sprites/knight_walk_01", "sprites/knight_walk_02", ...]

        Raises:
            AssetNotFoundError: If no matching files exist.
        """
        if prefix in self._frames_cache:
            return self._frames_cache[prefix]

        images_dir = self._base_path / "images"
        full_prefix = images_dir / prefix
        pattern = full_prefix.name + "_*.png"
        matches = sorted(
            full_prefix.parent.glob(pattern),
            key=lambda p: int(p.stem.rsplit("_", 1)[-1]),
        )

        if not matches:
            raise AssetNotFoundError(
                f"No animation frames for '{prefix}'.  "
                f"Looked for: {full_prefix.parent / pattern}"
            )

        names = [
            str(m.relative_to(images_dir).with_suffix(""))
            for m in matches
        ]
        self._frames_cache[prefix] = names
        return names


def _make_2x_path(path: Path) -> Path:
    """Insert ``@2x`` before the file extension.

    ``sprites/knight.png`` → ``sprites/knight@2x.png``
    """
    return path.with_stem(path.stem + "@2x")
