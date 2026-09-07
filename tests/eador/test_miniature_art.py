"""Every authored miniature fits the existing battle/retinue geometry through Scene drawing."""

import pytest

from eador import art
from eador.model import UNITS
from saga2d import Game, Scene


def test_all_miniatures_scale_uniformly_inside_the_existing_cell_footprint():
    """Retinue scaling must shrink equipment and contour strokes along with the body, without clipping."""
    game = Game('Miniature geometry', backend='mock', resolution=(240, 240))

    class Piece(Scene):
        kind = 'archer'
        scale = 1

        def draw(self):
            art.piece(self, 120, 120, self.kind, 'player', scale=self.scale)

    def geometry(scale):
        scene.scale = scale
        game.tick(0)
        backend = game.backend
        result = []
        bounds = []
        for shape in backend.polygons:
            for x, y in shape['points']:
                result.extend(((x - 120) / scale, (y - 120) / scale))
                bounds.append(((x - 120) / scale, (y - 120) / scale))
        for shape in backend.lines:
            result.extend(((shape['x1'] - 120) / scale, (shape['y1'] - 120) / scale,
                           (shape['x2'] - 120) / scale, (shape['y2'] - 120) / scale, shape['width'] / scale))
            for end in (1, 2):
                radius = shape['width'] / scale / 2
                px, py = (shape[f'x{end}'] - 120) / scale, (shape[f'y{end}'] - 120) / scale
                bounds.extend(((px - radius, py - radius), (px + radius, py + radius)))
        for shape in backend.circles:
            cx, cy, radius = (shape['x'] - 120) / scale, (shape['y'] - 120) / scale, shape['radius'] / scale
            result.extend((cx, cy, radius))
            bounds.extend(((cx - radius, cy - radius), (cx + radius, cy + radius)))
        for shape in backend.rects:
            x, y = (shape['x'] - 120) / scale, (shape['y'] - 120) / scale
            w, h = shape['width'] / scale, shape['height'] / scale
            result.extend((x, y, w, h))
            bounds.extend(((x, y), (x + w, y + h)))
        assert result and not backend.texts and not backend.images
        assert all(-40 <= x <= 40 and -64 <= y <= 28 for x, y in bounds), scene.kind
        return result

    try:
        scene = Piece()
        game.push(scene)
        for kind in ('archer', *UNITS, 'Warrior', 'Wizard', 'Scout', 'Commander'):
            scene.kind = kind
            full = geometry(1)
            assert geometry(.53) == pytest.approx(full), kind
    finally:
        game.close()
