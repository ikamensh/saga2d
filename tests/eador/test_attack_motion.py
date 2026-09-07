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


@pytest.mark.parametrize('still', [False, True])
def test_damage_numbers_arrive_with_each_contact_instead_of_revealing_retaliation_during_windup(tmp_path, still):
    """The public melee order shows each actual loss when it lands, with saves already resolved."""
    state, actor, target = melee_state()
    expected = State.from_json(state.to_json())
    before = {unit.id: unit.hp for unit in state.battle.units}
    expected.battle.attack(actor, target)
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(0)
        player = PlayerInput(game, finish_actions=False)
        if still:
            for key in ('f2', 'up', 'right', 'return'):
                player.press(key)

        def loss(ident):
            x, _ = game.scene.grid.center(state.battle.unit(ident).pos)
            amount = expected.battle.unit(ident).hp - before[ident]
            return [item for item in game.backend.texts
                    if item['text'] == f'{amount:+}' and abs(item['x'] - x) < .01]

        player.order('battle.attack', actor, target)
        assert state.to_json() == expected.to_json()
        game.tick(.2)
        assert not loss(target) and not loss(actor), 'Wind-up must not announce future damage'
        game.tick(.22)
        assert loss(target) and not loss(actor), 'The first contact is the target hit alone'
        game.tick(.65)
        assert loss(actor), 'Retaliation announces its own actual loss at contact'
        game.tick(2)
        assert not loss(actor) and not loss(target)
        player.reload(expected.to_json())
    finally:
        game.close()


def test_playback_contact_number_remains_readable_when_the_next_action_starts(tmp_path):
    """A hit remains visible into retaliation; short event slots must not flash away its number."""
    state, actor, target = melee_state()
    expected = State.from_json(state.to_json())
    before_hp = state.battle.unit(target).hp
    expected.battle.attack(actor, target)
    change = f'{expected.battle.unit(target).hp - before_hp:+}'
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(0)
        scene = game.scene
        scene.play_phase(lambda: scene.root.order('attack', actor, target, target='battle'))
        game.tick(.45)
        x, _ = game.scene.grid.center(state.battle.unit(target).pos)
        notices = lambda: [item for item in game.backend.texts
                           if item['text'] == change and abs(item['x'] - x) < .01]
        assert len(notices()) == 1
        game.tick(.45)  # The next event has begun, but the hit is only half a second old.
        assert len(notices()) == 1, 'Readability lifetime must survive a change of event'
        game.scene.refresh(); game.tick(0)
        assert len(notices()) == 1, 'Redraw does not duplicate the notice'
        game.tick(.4)  # Retaliation has now landed.
        actor_x, _ = game.scene.grid.center(state.battle.unit(actor).pos)
        actor_notices = lambda: [item for item in game.backend.texts
                                 if item['text'].startswith('-') and item['text'][1:].isdigit()
                                 and abs(item['x'] - actor_x) < .01]
        assert actor_notices()
        game.tick(.4)  # The last event ends before its contact notice's readability lifetime.
        assert type(game.scene) is BattleScene
        assert actor_notices(), 'Natural completion must not erase the last hit immediately'
        game.tick(1.2)
        assert not actor_notices()
        assert state.to_json() == expected.to_json()
    finally:
        game.close()


def test_swap_cannot_leave_a_wounded_heros_number_over_the_healthy_replacement(tmp_path):
    """Paid Warden input moves the wounded hero away; the unrelated Guard hit stays readable."""
    state, actor, target = melee_state()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(0)
        player = PlayerInput(game, finish_actions=False)
        player.order('battle.attack', actor, target)
        game.tick(1.05)
        old_x, _ = game.scene.grid.center(state.battle.unit(actor).pos)
        guard_x, _ = game.scene.grid.center(state.battle.unit(target).pos)
        notices_at = lambda x: [item for item in game.backend.texts
                               if item['text'].startswith('-') and item['text'][1:].isdigit()
                               and abs(item['x'] - x) < .01]
        assert notices_at(old_x) and notices_at(guard_x)
        expected = State.from_json(state.to_json())
        expected.battle.move(4, (-1, 0)); expected.battle.swap(4, actor)
        player.order('battle.move', 4, (-1, 0))
        player.order('battle.swap', 4, actor)
        assert state.battle.unit(4).hp == state.battle.unit(4).max_hp
        assert not notices_at(old_x), 'The healthy Warden must not inherit the hero’s damage label'
        assert notices_at(guard_x), 'An unrelated hit still gets its readability time'
        assert state.to_json() == expected.to_json()
        player.reload(expected.to_json())
    finally:
        game.close()
