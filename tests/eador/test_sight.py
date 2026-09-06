"""Tactical sight has symmetric forest/smoke rules independent of scenes and armies."""
from eador.sight import line_of_sight


def field(radius=3):
    return {(q, r): 'plains' for q in range(-radius, radius + 1)
            for r in range(-radius, radius + 1) if abs(q + r) <= radius}


def test_intervening_forest_blocks_but_endpoint_cover_does_not():
    """A forest screen obstructs distant fire; a unit can still shoot into or out of cover."""
    terrain = field()
    assert line_of_sight(terrain, (-2, 0), (2, 0))
    terrain[(-2, 0)] = terrain[(2, 0)] = 'forest'
    assert line_of_sight(terrain, (-2, 0), (2, 0))
    terrain[(0, 0)] = 'forest'
    assert not line_of_sight(terrain, (-2, 0), (2, 0))
    assert not line_of_sight(terrain, (2, 0), (-2, 0))


def test_a_shared_edge_needs_both_routes_blocked_without_directional_favoritism():
    """An edge shot can pass either side of cover, symmetrically in all six orientations."""
    def rotate(pos):
        q, r = pos
        return -r, q + r
    source, target, near, far = (0, 0), (1, 1), (1, 0), (0, 1)
    for _ in range(6):
        terrain = field()
        terrain[near] = 'forest'
        assert line_of_sight(terrain, source, target)
        assert line_of_sight(terrain, target, source)
        terrain[far] = 'forest'
        assert not line_of_sight(terrain, source, target)
        assert not line_of_sight(terrain, target, source)
        source, target, near, far = map(rotate, (source, target, near, far))


def test_smoke_blocks_from_inside_and_into_it_but_leaves_self_visible():
    """Smoke is two-way concealment; it never supplies a one-way firing bunker."""
    terrain = field()
    for smoke in ({(-2, 0)}, {(0, 0)}, {(2, 0)}):
        before = terrain.copy(), smoke.copy()
        assert not line_of_sight(terrain, (-2, 0), (2, 0), smoke=smoke)
        assert not line_of_sight(terrain, (2, 0), (-2, 0), smoke=smoke)
        assert (terrain, smoke) == before
    assert line_of_sight(terrain, (0, 0), (0, 0), smoke={(0, 0)})
    assert line_of_sight(terrain, (-2, 0), (2, 0), smoke={(0, 1)})


def test_invalid_endpoints_fail_and_missing_intermediate_cells_obstruct_sight():
    """A query cannot see through an absent board cell or hide an invalid selection."""
    import pytest
    terrain = field()
    with pytest.raises(ValueError, match='endpoints'):
        line_of_sight(terrain, (4, 0), (0, 0))
    with pytest.raises(ValueError, match='endpoints'):
        line_of_sight(terrain, (0, 0), (4, 0))
    del terrain[(0, 0)]
    assert not line_of_sight(terrain, (-2, 0), (2, 0))


def test_sight_is_symmetric_translatable_and_obstruction_monotone_on_generated_fields():
    """Across actual board sizes, adding forest cannot open a shot and coordinates confer no advantage."""
    import random
    rng = random.Random(37)
    cells = tuple(field())
    offset = (11, -7)
    shifted = lambda pos: (pos[0] + offset[0], pos[1] + offset[1])
    for _ in range(12):
        terrain = {cell: rng.choice(('plains', 'hills', 'marsh', 'forest')) for cell in cells}
        smoke = set(rng.sample(cells, 3))
        denser = {cell: 'forest' if rng.random() < .25 else value for cell, value in terrain.items()}
        translated = {shifted(cell): value for cell, value in terrain.items()}
        translated_smoke = {shifted(cell) for cell in smoke}
        for source in cells:
            for target in cells:
                visible = line_of_sight(terrain, source, target, smoke=smoke)
                assert visible == line_of_sight(terrain, target, source, smoke=smoke)
                assert visible == line_of_sight(translated, shifted(source), shifted(target), smoke=translated_smoke)
                assert visible or not line_of_sight(denser, source, target, smoke=smoke)


def test_an_oblique_shot_cannot_skip_a_crossed_forest_between_hex_steps():
    """Nearest-center samples miss this intervening hex; sight follows the actual straight segment."""
    terrain = field()
    terrain[(-2, 1)] = 'forest'
    assert not line_of_sight(terrain, (-3, 0), (-2, 3))
    assert not line_of_sight(terrain, (-2, 3), (-3, 0))
