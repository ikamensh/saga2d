"""EasyGame — a Python framework for 2D sprite-based games.

Public API re-exports.  Game code imports from here::

    from easygame import Game, Scene, RenderLayer, SpriteAnchor, AssetManager

Internal modules (backends, rendering internals) are **not** re-exported.
"""

from easygame.animation import AnimationDef
from easygame.assets import AssetManager, AssetNotFoundError
from easygame.backends.base import (
    Event,
    KeyEvent,
    MouseEvent,
    WindowEvent,
)
from easygame.game import Game
from easygame.input import InputEvent
from easygame.rendering.layers import RenderLayer, SpriteAnchor
from easygame.rendering.sprite import Sprite
from easygame.scene import Scene
from easygame.util.tween import Ease, tween

__all__ = [
    "AnimationDef",
    "AssetManager",
    "AssetNotFoundError",
    "Ease",
    "Event",
    "Game",
    "InputEvent",
    "KeyEvent",
    "MouseEvent",
    "RenderLayer",
    "Scene",
    "Sprite",
    "SpriteAnchor",
    "WindowEvent",
    "tween",
]
