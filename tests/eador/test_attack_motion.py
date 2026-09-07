"""Attack poses move the illustration, never the tactical position or saved result."""
import math

import pytest

from eador.app import create_game
from eador.model import State
from eador.scene import BattleScene, ShardScene
from tools.eador_observatory_campaign import prepare_observatory
from tools.eador_ui import PlayerInput


def melee_state():
    """A paid Commander expedition earns a real melee attack and Guard retaliation."""
    state = prepare_observatory()
    state.explore(approach='clear')
    for ident, pos in ((1, (1, -1)), (0, (0, 0)), (3, (0, -1))):
        state.battle.move(ident, pos)
    target = next(unit for unit in state.battle.units if unit.team == 'enemy' and unit.kind == 'guard')
    return state, 0, target.id


def rendered_base(game, ident):
    """Locate the miniature's painted base in the actual recording backend output."""
    scene = game.scene
    unit = scene.battle.unit(ident)
    cx, cy = scene.grid.center(unit.pos)
    cy += scene.grid.size * .22 + 7 * min(1, scene.grid.size / 56)
    bases = [(sum(x for x, y in shape['points']) / len(shape['points']),
              sum(y for x, y in shape['points']) / len(shape['points']))
             for shape in game.backend.polygons if shape['color'] == (31, 42, 40, 255)]
    return min(bases, key=lambda point: math.dist(point, (cx, cy)))


@pytest.mark.parametrize('playback', [False, True])
@pytest.mark.parametrize('still', [False, True])
def test_attack_and_recoil_return_home_with_health_and_saved_positions_fixed(tmp_path, playback, still):
    """Real damage/reaction has directional figures, stationary health labels and exact reloads."""
    state, actor, target = melee_state()
    expected = State.from_json(state.to_json())
    expected.battle.attack(actor, target)
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(0)
        player = PlayerInput(game, finish_actions=False)
        if still:
            for key in ('f2', 'up', 'right', 'return'):
                player.press(key)
        home = {ident: rendered_base(game, ident) for ident in (actor, target)}
        vector = tuple(b - a for a, b in zip(home[actor], home[target]))
        if playback:
            scene = game.scene
            scene.play_phase(lambda: scene.root.order('attack', actor, target, target='battle'))
        else:
            player.order('battle.attack', actor, target)
        game.tick(.24)
        attack = rendered_base(game, actor)
        dot = sum((p - origin) * direction for p, origin, direction in zip(attack, home[actor], vector))
        assert (dot > 1) is not still
        assert rendered_base(game, target) == pytest.approx(home[target])
        game.tick(.24)
        hit = rendered_base(game, target)
        recoil = sum((p - origin) * direction for p, origin, direction in zip(hit, home[target], vector))
        assert (recoil > 1) is not still
        for ident in (actor, target):
            unit = game.scene.battle.unit(ident)
            x, y = game.scene.grid.center(unit.pos)
            assert any(item['text'] == str(unit.hp) and abs(item['x'] - x) < .01
                       and abs(item['y'] - (y + game.scene.grid.size * .23)) < .01
                       for item in game.backend.texts)
        game.tick(2)
        assert type(game.scene) is BattleScene
        for ident in (actor, target):
            assert rendered_base(game, ident) == pytest.approx(home[ident])
        assert state.to_json() == expected.to_json()
        player.reload(expected.to_json())
    finally:
        game.close()


@pytest.mark.parametrize('still', [False, True])
def test_defeated_target_recoils_briefly_without_resurrecting_or_changing_the_saved_outcome(tmp_path, still):
    """The earned final arrow retains only the drawing of its victim, then removes it."""
    from tools.verify_eador_final_blow import earned_last_arrow

    order = earned_last_arrow()
    state = State.from_json(order['before'])
    actor, target = order['args']
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(0)
        player = PlayerInput(game, finish_actions=False)
        if still:
            for key in ('f2', 'up', 'right', 'return'):
                player.press(key)
        home = rendered_base(game, target)
        direction = tuple(b - a for a, b in zip(rendered_base(game, actor), home))
        player.order('battle.attack', actor, target)
        game.tick(.5)
        assert state.battle.unit(target).hp == 0
        position = rendered_base(game, target)
        if still:
            assert math.dist(position, home) > game.scene.grid.size * .5
        else:
            assert 1 < math.dist(position, home) < game.scene.grid.size * .25
            assert sum((p - h) * d for p, h, d in zip(position, home, direction)) > 0
        game.tick(.4)
        assert math.dist(rendered_base(game, target), home) > game.scene.grid.size * .5
        assert state.to_json() == order['after']
        player.reload(order['after'])
    finally:
        game.close()


def test_retaliation_casualty_stays_visible_through_its_own_attack_before_recoiling(tmp_path):
    """Two actual rounds wound a Militia; its final order animates in recorded causal order."""
    state, _, target = melee_state()
    for _ in range(2):
        state.battle.attack(1, target)
        state.battle.end_turn()
    assert state.battle.unit(1).alive
    expected = State.from_json(state.to_json())
    expected.battle.attack(1, target)
    assert not expected.battle.unit(1).alive and expected.battle.outcome is None
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(0)
        player = PlayerInput(game, finish_actions=False)
        home = rendered_base(game, 1)
        player.order('battle.attack', 1, target)
        game.tick(.2)
        assert 1 < math.dist(rendered_base(game, 1), home) < game.scene.grid.size * .4
        game.tick(.8)
        assert math.dist(rendered_base(game, 1), home) < game.scene.grid.size * .25
        assert state.to_json() == expected.to_json()
        game.tick(1.4)
        assert math.dist(rendered_base(game, 1), home) > game.scene.grid.size * .5
        player.reload(expected.to_json())
    finally:
        game.close()
