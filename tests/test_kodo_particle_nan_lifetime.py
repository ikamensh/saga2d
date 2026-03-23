"""Regression tests for F26: ParticleEmitter NaN/Inf lifetime bug.

Bug: ``ParticleEmitter(lifetime=(nan, nan))`` was silently accepted.
``random.uniform(nan, nan)`` returns ``nan``, and ``nan <= 0`` is ``False``
under IEEE 754, so particles created via ``burst()`` (or continuous mode)
**never expired** — a memory/sprite leak.

Fix: ``ParticleEmitter.__init__`` now validates that both lifetime tuple
values are finite (``math.isfinite``) and non-negative (``>= 0``).

These tests exercise the **real particle workflow** (Game + Scene + Sprite +
ParticleEmitter + update loop) via the mock backend — no display required.
"""

from __future__ import annotations

import math

import pytest

from saga2d import Game, Scene
from saga2d.rendering.particles import ParticleEmitter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def game() -> Game:
    """Fresh Game with mock backend and a scene on the stack."""
    g = Game("ParticleNaNTest", backend="mock", resolution=(800, 600))
    g.push(Scene())
    return g


# ---------------------------------------------------------------------------
# F26 — NaN lifetime rejection
# ---------------------------------------------------------------------------


class TestF26NaNLifetimeRejection:
    """ParticleEmitter must reject non-finite lifetime values at construction."""

    def test_nan_nan_lifetime_raises(self, game: Game) -> None:
        """lifetime=(NaN, NaN) — the original bug report."""
        with pytest.raises(ValueError, match="finite"):
            ParticleEmitter(
                "sprites/knight",
                position=(100, 100),
                lifetime=(float("nan"), float("nan")),
            )

    def test_nan_min_lifetime_raises(self, game: Game) -> None:
        """Only the min value is NaN."""
        with pytest.raises(ValueError, match="finite"):
            ParticleEmitter(
                "sprites/knight",
                position=(100, 100),
                lifetime=(float("nan"), 1.0),
            )

    def test_nan_max_lifetime_raises(self, game: Game) -> None:
        """Only the max value is NaN."""
        with pytest.raises(ValueError, match="finite"):
            ParticleEmitter(
                "sprites/knight",
                position=(100, 100),
                lifetime=(0.5, float("nan")),
            )

    def test_inf_inf_lifetime_raises(self, game: Game) -> None:
        """lifetime=(Inf, Inf) — also causes NaN from random.uniform."""
        with pytest.raises(ValueError, match="finite"):
            ParticleEmitter(
                "sprites/knight",
                position=(100, 100),
                lifetime=(float("inf"), float("inf")),
            )

    def test_neg_inf_lifetime_raises(self, game: Game) -> None:
        """-Inf min value."""
        with pytest.raises(ValueError, match="finite"):
            ParticleEmitter(
                "sprites/knight",
                position=(100, 100),
                lifetime=(float("-inf"), 1.0),
            )

    def test_mixed_inf_nan_lifetime_raises(self, game: Game) -> None:
        """One Inf, one NaN."""
        with pytest.raises(ValueError, match="finite"):
            ParticleEmitter(
                "sprites/knight",
                position=(100, 100),
                lifetime=(float("inf"), float("nan")),
            )

    def test_negative_lifetime_raises(self, game: Game) -> None:
        """Negative (but finite) lifetime values are also rejected."""
        with pytest.raises(ValueError, match=">= 0"):
            ParticleEmitter(
                "sprites/knight",
                position=(100, 100),
                lifetime=(-1.0, 0.5),
            )

    def test_both_negative_lifetime_raises(self, game: Game) -> None:
        """Both min and max negative."""
        with pytest.raises(ValueError, match=">= 0"):
            ParticleEmitter(
                "sprites/knight",
                position=(100, 100),
                lifetime=(-2.0, -0.5),
            )


# ---------------------------------------------------------------------------
# Valid lifetimes still work (no false positives)
# ---------------------------------------------------------------------------


class TestValidLifetimeStillWorks:
    """Ensure the validation doesn't break normal usage."""

    def test_normal_lifetime_accepted(self, game: Game) -> None:
        """Default-style lifetime range works."""
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(0.3, 0.8),
        )
        assert em._lifetime == (0.3, 0.8)

    def test_zero_zero_lifetime_accepted(self, game: Game) -> None:
        """(0, 0) is valid — particles die immediately."""
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(0.0, 0.0),
            speed=(0, 0),
        )
        em.burst(5)
        em.update(0.001)
        assert len(em._particles) == 0

    def test_equal_min_max_lifetime(self, game: Game) -> None:
        """Fixed lifetime (min == max) works."""
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(1.0, 1.0),
            speed=(0, 0),
        )
        em.burst(3)
        for p in em._particles:
            assert p.total_lifetime == 1.0

    def test_very_small_lifetime(self, game: Game) -> None:
        """Extremely small positive lifetime — dies on first reasonable tick."""
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(1e-10, 1e-10),
            speed=(0, 0),
        )
        em.burst(3)
        em.update(0.016)  # one frame
        assert len(em._particles) == 0

    def test_large_lifetime(self, game: Game) -> None:
        """Very long (but finite) lifetime — particles survive many ticks."""
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(1e6, 1e6),
            speed=(0, 0),
        )
        em.burst(2)
        em.update(1000.0)
        assert len(em._particles) == 2  # still alive


# ---------------------------------------------------------------------------
# Real particle workflow (burst → update → expire → cleanup)
# ---------------------------------------------------------------------------


class TestRealParticleWorkflow:
    """End-to-end particle lifecycle via Game.tick() — the real update path."""

    def test_burst_particles_expire_via_game_tick(self, game: Game) -> None:
        """Particles burst with valid lifetime expire through game.tick()."""
        em = ParticleEmitter(
            "sprites/knight",
            position=(200, 200),
            lifetime=(0.05, 0.05),
            speed=(50, 100),
        )
        em.burst(10)
        assert len(em._particles) == 10
        assert em.is_active is True

        # Tick enough to kill all particles
        game.tick(dt=0.1)
        assert len(em._particles) == 0
        assert em.is_active is False

    def test_burst_particles_move_and_fade_before_death(
        self, game: Game
    ) -> None:
        """Particles move and fade during their lifetime."""
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(1.0, 1.0),
            speed=(100, 100),
            direction=(0, 0),  # rightward
            fade_out=True,
        )
        em.burst(1)
        p = em._particles[0]
        initial_x = p.sprite._x

        game.tick(dt=0.5)
        # Moved right
        assert p.sprite._x > initial_x
        # Faded (opacity < 255)
        assert p.sprite.opacity < 255
        # Still alive
        assert len(em._particles) == 1

        # Now kill it
        game.tick(dt=0.6)
        assert len(em._particles) == 0

    def test_continuous_particles_spawn_and_expire(self, game: Game) -> None:
        """Continuous mode spawns and expires particles normally."""
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(0.05, 0.05),
            speed=(0, 0),
        )
        em.continuous(rate=100)  # 100/sec

        # First tick: spawn some, they die immediately
        game.tick(dt=0.1)  # spawns 10, all die (lifetime 0.05 < 0.1)
        # Particles spawned this tick die this same tick
        assert len(em._particles) == 0

        em.stop()

    def test_emitter_auto_deregisters_when_burst_done(
        self, game: Game
    ) -> None:
        """After burst particles expire, emitter deregisters from game."""
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(0.01, 0.01),
            speed=(0, 0),
        )
        em.burst(5)
        assert em in game._particle_emitters

        game.tick(dt=0.1)
        assert em not in game._particle_emitters
        assert em.is_active is False

    def test_burst_after_nan_rejection_works(self, game: Game) -> None:
        """After a failed NaN construction, a valid emitter works fine."""
        with pytest.raises(ValueError):
            ParticleEmitter(
                "sprites/knight",
                position=(100, 100),
                lifetime=(float("nan"), float("nan")),
            )

        # Now create a valid one and run the full workflow
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(0.1, 0.1),
            speed=(0, 0),
        )
        em.burst(3)
        assert len(em._particles) == 3

        game.tick(dt=0.2)
        assert len(em._particles) == 0

    def test_multiple_bursts_all_expire(self, game: Game) -> None:
        """Multiple burst() calls — all particles eventually expire."""
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(0.1, 0.1),
            speed=(0, 0),
        )
        em.burst(5)
        em.burst(5)
        assert len(em._particles) == 10

        game.tick(dt=0.2)
        assert len(em._particles) == 0

    def test_remove_after_burst_cleans_all(self, game: Game) -> None:
        """remove() immediately kills all particles and deregisters."""
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(10.0, 10.0),
            speed=(0, 0),
        )
        em.burst(10)
        sprite_count_before = len(game._all_sprites)

        em.remove()
        assert len(em._particles) == 0
        assert em not in game._particle_emitters
        # All 10 particle sprites should be removed
        assert len(game._all_sprites) == sprite_count_before - 10
