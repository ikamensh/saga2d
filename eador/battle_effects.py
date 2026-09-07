"""Small, deterministic drawing effects from an already-resolved battle event."""
import math

from eador.battle_audio import is_magic_attack, seal_progress_change
from eador.style import BLUE, GOLD, RED, TEAL, TEXT


_CIRCLE = tuple((math.cos(i * math.tau / 16), math.sin(i * math.tau / 16)) for i in range(16))
_HITS = ('attack', 'pin', 'brace', 'retaliation', 'bolt')


def _ring(scene, x, y, radius, color, *, width=2, flat=1):
    # Ground ellipses belong below feet and HP; upright impacts belong in front.
    with scene.screen_layer(2 if flat < 1 else 8):
        for (ax, ay), (bx, by) in zip(_CIRCLE, _CIRCLE[1:] + _CIRCLE[:1]):
            scene.draw_line(x + ax * radius, y + ay * radius * flat,
                            x + bx * radius, y + by * radius * flat, color, width)


def _impact(scene, x, y, size, color, progress, still):
    radius = size * (.42 if still else .16 + .46 * progress)
    alpha = 190 if still else round(230 * (1 - progress))
    _ring(scene, x, y, radius, (*color[:3], alpha), width=2.5)
    for dx, dy in _CIRCLE[::2]:
        inner, outer = radius * .7, radius * 1.25
        scene.draw_line(x + dx * inner, y + dy * inner,
                        x + dx * outer, y + dy * outer, (*TEXT[:3], alpha), 2)


def _projectile(scene, start, end, amount, size, *, arcane=False):
    ax, ay = start; bx, by = end
    length = math.hypot(bx - ax, by - ay)
    if not length:
        return
    dx, dy = (bx - ax) / length, (by - ay) / length
    x, y = ax + (bx - ax) * amount, ay + (by - ay) * amount
    tail = min(size * .6, length * amount)
    tx, ty = x - dx * tail, y - dy * tail
    if arcane:
        scene.draw_line(tx, ty, x, y, (*BLUE[:3], 90), 9)
        scene.draw_line(tx, ty, x, y, TEXT, 2)
        scene.draw_circle(x, y, size * .13, (*BLUE[:3], 95))
        scene.draw_circle(x, y, size * .055, TEXT)
    else:
        scene.draw_line(tx, ty, x, y, GOLD, 2.5)
        wing = size * .095
        scene.draw_polygon([(x + dx * wing, y + dy * wing),
                            (x - dx * wing - dy * wing, y - dy * wing + dx * wing),
                            (x - dx * wing + dy * wing, y - dy * wing - dx * wing)], TEXT)
        for side in (-1, 1):
            scene.draw_line(tx, ty, tx + dx * wing - dy * wing * side,
                            ty + dy * wing + dx * wing * side, GOLD, 2)


def draw_event(scene, event, fraction, *, still=False):
    """Draw only recorded actors, targets and changed smoke cells; never consult rules."""
    grid, size = scene.grid, scene.grid.size
    kind = event.kind
    actor = scene.battle.unit(event.actor_id) if event.actor_id is not None else None
    target = scene.battle.unit(event.target_id) if event.target_id is not None else None
    arcane = kind == 'bolt' or (kind in ('attack', 'pin') and
                              is_magic_attack(actor, scene.root.state.hero.hero_class))
    progress = seal_progress_change(scene.battle, event)
    if progress and fraction >= .5:
        x, y = grid.center(scene.battle.objective.target)
        amount = .5 if still else (fraction - .5) * 2
        radius = size * (.65 + .25 * amount if progress > 0 else .9 - .25 * amount)
        color = TEAL if progress > 0 else RED
        alpha = 220 if still else round(240 * (1 - amount * .65))
        # Ground rings remain below the holder and its persistent health label.
        _ring(scene, x, y + size * .12, radius, (*color[:3], alpha), width=3.5, flat=.62)
        _ring(scene, x, y + size * .12, radius * .8, (*color[:3], alpha // 2), width=2, flat=.62)

    def center(frame, ident):
        x, y = grid.center(frame.unit(ident).pos)
        return x, y - size * .27

    if actor is not None:
        x, y = grid.center(event.before.unit(actor.id).pos)
        _ring(scene, x, y + size * .26, size * .52, (*GOLD[:3], 180), flat=.42)
    if target is not None:
        x, y = center(event.before, target.id)
        color = TEAL if kind in ('heal', 'rally', 'swap') else BLUE if arcane else RED
        if kind in _HITS:
            if still or fraction >= .5:
                _impact(scene, x, y + size * .25, size, color, (fraction - .5) * 2, still)
            elif kind == 'bolt' or actor.attack_range > 1 and kind in ('attack', 'pin'):
                _projectile(scene, center(event.before, actor.id), (x, y), fraction * 2,
                            size, arcane=arcane)
            else:
                # A brief blade arc closes on the recorded contact point.
                reach = size * .48
                sweep = (fraction * 2 - .5) * 1.8
                for step in range(4):
                    angle = sweep + step * .25
                    scene.draw_line(x + math.cos(angle) * reach, y + math.sin(angle) * reach,
                                    x + math.cos(angle + .22) * reach, y + math.sin(angle + .22) * reach,
                                    (*TEXT[:3], 100 + step * 35), 3)
        elif kind in ('heal', 'rally'):
            progress = .5 if still else fraction
            _ring(scene, x, y + size * .4, size * (.36 + progress * .16), (*TEAL[:3], 180), flat=.5)
            for dx, dy in ((-.32, .08), (.3, -.06), (0, -.3)):
                px, py = x + dx * size, y + (dy - progress * .22) * size
                scene.draw_line(px - size * .07, py, px + size * .07, py, TEAL, 2.5)
                scene.draw_line(px, py - size * .07, px, py + size * .07, TEAL, 2.5)
        elif kind in ('swap', 'repulse'):
            for ident in (actor.id, target.id) if kind == 'swap' else (target.id,):
                ax, ay = center(event.before, ident); bx, by = center(event.after, ident)
                _ring(scene, bx, by + size * .5, size * .45, BLUE, flat=.5)
                if not still:
                    midx, midy = (ax + bx) / 2 - (by - ay) * .25, (ay + by) / 2 + (bx - ax) * .25
                    scene.draw_line(ax, ay, midx, midy, (*BLUE[:3], 110), 2)
                    scene.draw_line(midx, midy, bx, by, (*BLUE[:3], 110), 2)
                    amount = fraction * 2 if fraction < .5 else (fraction - .5) * 2
                    start, end = ((ax, ay), (midx, midy)) if fraction < .5 else ((midx, midy), (bx, by))
                    scene.draw_circle(start[0] + (end[0] - start[0]) * amount,
                                      start[1] + (end[1] - start[1]) * amount, size * .065, TEXT)
    if kind == 'smoke':
        for pos, expiry in event.after.smoke:
            if (pos, expiry) in event.before.smoke:
                continue
            x, y = grid.center(pos)
            spread = .65 if still else .35 + fraction * .6
            for dx, dy, radius in ((-.25, .06, .3), (.24, -.02, .28), (0, -.22, .34)):
                scene.draw_circle(x + dx * size * spread, y + dy * size * spread,
                                  radius * size * spread, (184, 199, 214, 130))
            _ring(scene, x, y, size * .5 * spread, (*BLUE[:3], 180), flat=.6)
    elif kind == 'guard':
        x, y = center(event.after, actor.id)
        _ring(scene, x, y, size * .4, (*GOLD[:3], 160), flat=1.15)


def draw_trace(scene, trace, elapsed, *, still=False):
    """Direct orders stay immediate; their latest trace gets at most 1.4 seconds of feedback."""
    events = trace.events
    duration = min(.65, 1.4 / len(events))
    index = int(elapsed / duration)
    if index < len(events):
        draw_event(scene, events[index], elapsed / duration - index, still=still)
