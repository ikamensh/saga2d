"""Properties of the iter-45 ``rng=`` parameter on :class:`ParticleEmitter`.

Before iter-45, ParticleEmitter used module-level ``random.uniform`` /
``random.choice``. That made every particle stream non-reproducible,
which broke the iter-41 PNG snapshot regression net the first time an
example used particles (iter-45 dodge). iter-45 added an optional
``rng: random.Random`` parameter — pass one and the emitter's entire
output is deterministic under a fixed seed.

Tests below verify:

*   Two emitters with same seed produce byte-identical particle state.
*   Two emitters with *different* seeds produce different state.
*   The default behaviour (``rng=None``) still works and uses the
    module-level random (backwards compatibility).
*   A ``rng=`` emitter doesn't perturb the module-level ``random``
    state (wouldn't want our snapshot tests to drift someone else's
    tests).
"""

from __future__ import annotations

import random

import pytest

from saga2d import Game
from saga2d.rendering.particles import ParticleEmitter


@pytest.fixture
def game():
    g = Game("particles-rng-test", resolution=(200, 200),
             fullscreen=False, backend="mock", visible=False)
    # Ensure the asset is loaded so the emitter can resolve it.
    g.assets.image("player_token")
    yield g
    g._teardown()


def _particle_state(emitter: ParticleEmitter) -> list:
    """Return a snapshot of particle velocities and lifetimes."""
    return [
        (round(p.vx, 6), round(p.vy, 6), round(p.total_lifetime, 6))
        for p in emitter._particles
    ]


def test_same_seed_produces_identical_state(game: Game) -> None:
    rng1 = random.Random(7)
    rng2 = random.Random(7)
    e1 = ParticleEmitter(
        "player_token", position=(100, 100), count=10,
        speed=(50, 150), direction=(0, 360), lifetime=(0.5, 1.5),
        rng=rng1,
    )
    e2 = ParticleEmitter(
        "player_token", position=(100, 100), count=10,
        speed=(50, 150), direction=(0, 360), lifetime=(0.5, 1.5),
        rng=rng2,
    )
    e1.burst()
    e2.burst()
    assert _particle_state(e1) == _particle_state(e2)


def test_different_seeds_produce_different_state(game: Game) -> None:
    rng1 = random.Random(1)
    rng2 = random.Random(2)
    e1 = ParticleEmitter(
        "player_token", position=(100, 100), count=10,
        speed=(50, 150), direction=(0, 360), lifetime=(0.5, 1.5),
        rng=rng1,
    )
    e2 = ParticleEmitter(
        "player_token", position=(100, 100), count=10,
        speed=(50, 150), direction=(0, 360), lifetime=(0.5, 1.5),
        rng=rng2,
    )
    e1.burst()
    e2.burst()
    assert _particle_state(e1) != _particle_state(e2)


def test_no_rng_falls_back_to_module_random(game: Game) -> None:
    """Backwards compatibility: not passing ``rng=`` works unchanged.
    The emitter still spawns particles; they just aren't reproducible."""
    e = ParticleEmitter(
        "player_token", position=(100, 100), count=5,
        speed=(50, 150),
    )
    e.burst()
    assert len(e._particles) == 5


def test_rng_does_not_disturb_module_random_state(game: Game) -> None:
    """Consuming the seeded RNG must not ratchet the module-level
    random state forward. Otherwise, spawning a deterministic emitter
    during a test would corrupt other tests that depend on module-
    level ``random``."""
    # Capture module-random state before.
    before = random.getstate()
    rng = random.Random(123)
    e = ParticleEmitter(
        "player_token", position=(100, 100), count=20,
        speed=(50, 150), rng=rng,
    )
    e.burst()
    after = random.getstate()
    assert before == after, "module random state should be untouched"
