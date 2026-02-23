"""
3D wireframe math for procedural asset generation.

Defines platonic-solid meshes, rotation matrices, perspective/orthographic
projection, and a Pillow renderer — all using only the Python stdlib *math*
module (no numpy).

Vertex = (x, y, z)   float tuple
Edge   = (i, j)       index pair into vertex list

Conventions:
    Right-handed coordinate system.
    +X right, +Y up, +Z toward viewer.
    Shapes are centred at origin with unit-ish extent.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
Vec3 = Tuple[float, float, float]
Vec2 = Tuple[float, float]
Edge = Tuple[int, int]
Mesh = Tuple[List[Vec3], List[Edge]]  # (vertices, edges)


# ---------------------------------------------------------------------------
# Platonic solids — vertices + edge lists
# ---------------------------------------------------------------------------

def tetrahedron() -> Mesh:
    """Return (vertices, edges) for a regular tetrahedron centred at origin.

    Edge length is approximately 2.
    """
    # Place vertices so the centroid is at origin.
    a = 1.0
    verts: List[Vec3] = [
        ( a,  a,  a),
        ( a, -a, -a),
        (-a,  a, -a),
        (-a, -a,  a),
    ]
    edges: List[Edge] = [
        (0, 1), (0, 2), (0, 3),
        (1, 2), (1, 3), (2, 3),
    ]
    return verts, edges


def octahedron() -> Mesh:
    """Return (vertices, edges) for a regular octahedron centred at origin.

    Vertices lie on the coordinate axes at distance 1.
    """
    verts: List[Vec3] = [
        ( 1,  0,  0),
        (-1,  0,  0),
        ( 0,  1,  0),
        ( 0, -1,  0),
        ( 0,  0,  1),
        ( 0,  0, -1),
    ]
    # Each vertex connects to all others except its antipodal vertex.
    edges: List[Edge] = [
        (0, 2), (0, 3), (0, 4), (0, 5),
        (1, 2), (1, 3), (1, 4), (1, 5),
        (2, 4), (2, 5), (3, 4), (3, 5),
    ]
    return verts, edges


def cube() -> Mesh:
    """Return (vertices, edges) for a cube centred at origin.

    Vertices at (+-1, +-1, +-1).
    """
    verts: List[Vec3] = [
        (-1, -1, -1),
        (-1, -1,  1),
        (-1,  1, -1),
        (-1,  1,  1),
        ( 1, -1, -1),
        ( 1, -1,  1),
        ( 1,  1, -1),
        ( 1,  1,  1),
    ]
    edges: List[Edge] = [
        # bottom face
        (0, 1), (0, 2), (1, 3), (2, 3),
        # top face
        (4, 5), (4, 6), (5, 7), (6, 7),
        # vertical pillars
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    return verts, edges


# ---------------------------------------------------------------------------
# Rotation matrices (applied per-vertex)
# ---------------------------------------------------------------------------

def rotate_x(v: Vec3, angle: float) -> Vec3:
    """Rotate *v* around the X axis by *angle* radians."""
    x, y, z = v
    c = math.cos(angle)
    s = math.sin(angle)
    return (x, y * c - z * s, y * s + z * c)


def rotate_y(v: Vec3, angle: float) -> Vec3:
    """Rotate *v* around the Y axis by *angle* radians."""
    x, y, z = v
    c = math.cos(angle)
    s = math.sin(angle)
    return (x * c + z * s, y, -x * s + z * c)


def rotate_z(v: Vec3, angle: float) -> Vec3:
    """Rotate *v* around the Z axis by *angle* radians."""
    x, y, z = v
    c = math.cos(angle)
    s = math.sin(angle)
    return (x * c - y * s, x * s + y * c, z)


# ---------------------------------------------------------------------------
# Projection helpers
# ---------------------------------------------------------------------------

def project_perspective(
    v: Vec3,
    fov_degrees: float = 60.0,
    viewer_distance: float = 5.0,
) -> Vec2:
    """Project a 3D point onto 2D using simple perspective division.

    Args:
        v:               (x, y, z) in world space.
        fov_degrees:     Horizontal field of view.
        viewer_distance: Distance from the camera to the origin along +Z.

    Returns:
        (px, py) in normalised device coordinates (roughly -1..1 for objects
        near the origin).  Caller scales to pixel coords.
    """
    x, y, z = v
    # Camera sits at z = +viewer_distance, looking toward origin.
    dz = viewer_distance - z
    if dz <= 0.01:
        dz = 0.01  # avoid division by zero / behind camera
    fov_rad = math.radians(fov_degrees)
    f = 1.0 / math.tan(fov_rad / 2.0)
    px = x * f / dz
    py = y * f / dz
    return (px, py)


def project_orthographic(
    v: Vec3,
    scale: float = 1.0,
) -> Vec2:
    """Project a 3D point onto 2D by simply dropping the Z coordinate.

    Args:
        v:     (x, y, z) in world space.
        scale: Uniform scale factor applied to x and y.

    Returns:
        (px, py) in scaled world units.
    """
    x, y, _z = v
    return (x * scale, y * scale)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_wireframe(
    img: Image.Image,
    vertices: Sequence[Vec3],
    edges: Sequence[Edge],
    *,
    color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    width: int = 1,
    projection: str = "perspective",
    fov_degrees: float = 60.0,
    viewer_distance: float = 5.0,
    ortho_scale: float = 1.0,
    center: Tuple[float, float] | None = None,
    scale: float | None = None,
) -> None:
    """Project and draw wireframe edges onto a Pillow RGBA image.

    Args:
        img:             Target image.
        vertices:        3D vertex list (already rotated as desired).
        edges:           Index pairs into *vertices*.
        color:           RGBA line colour.
        width:           Line width in pixels.
        projection:      ``"perspective"`` or ``"orthographic"``.
        fov_degrees:     FOV for perspective projection.
        viewer_distance: Camera distance for perspective projection.
        ortho_scale:     Scale for orthographic projection.
        center:          Pixel (cx, cy) for the projected origin.
                         Defaults to image centre.
        scale:           Pixel scale applied after projection.
                         Defaults to ``min(w, h) * 0.35``.
    """
    w, h = img.size
    if center is None:
        center = (w / 2.0, h / 2.0)
    if scale is None:
        scale = min(w, h) * 0.35

    # Project all vertices to 2D.
    if projection == "perspective":
        pts_2d = [
            project_perspective(v, fov_degrees, viewer_distance)
            for v in vertices
        ]
    elif projection == "orthographic":
        pts_2d = [
            project_orthographic(v, ortho_scale)
            for v in vertices
        ]
    else:
        raise ValueError(f"Unknown projection {projection!r}")

    # Map normalised coords to pixel space.
    # Y is flipped: positive Y in world = upward, but pixel Y grows downward.
    cx, cy = center
    pixel_pts = [
        (cx + px * scale, cy - py * scale)
        for px, py in pts_2d
    ]

    # Draw edges.
    draw = ImageDraw.Draw(img, "RGBA")
    for i, j in edges:
        draw.line([pixel_pts[i], pixel_pts[j]], fill=color, width=width)
