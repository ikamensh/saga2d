"""Rendering primitives: layers, anchors, sprites, camera, particles (Stage 2+)."""

from easygame.rendering.camera import Camera
from easygame.rendering.color_swap import ColorSwap, get_palette, register_palette
from easygame.rendering.layers import RenderLayer, SpriteAnchor
from easygame.rendering.particles import ParticleEmitter
from easygame.rendering.sprite import Sprite

__all__ = [
    "Camera",
    "ColorSwap",
    "ParticleEmitter",
    "RenderLayer",
    "Sprite",
    "SpriteAnchor",
    "get_palette",
    "register_palette",
]
