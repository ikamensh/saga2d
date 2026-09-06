"""Inspect earned rival orders, finite forces and saved counterplay at both reading sizes."""
from __future__ import annotations

import argparse
from collections import Counter
from functools import cache
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d import Label
from eador.app import create_game
from eador.difficulty import DIFFICULTIES
from eador.model import State, UNITS
from eador.preferences import reading_scale
from eador.rival import RECRUIT_COSTS
from eador.rival_scene import RivalScene, rival_order
from eador.scene import ShardScene
from tools.eador_campaign import finish_battle
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


@cache
def prepared_rivals():
    """Pay for a central expedition, intercept/withdraw, or win defense and observe paid refits."""
    cases = []
    for mode in DIFFICULTIES:
        opening = State.new(7, difficulty=mode)
        cases.append((f'{mode}-opening', opening.to_json()))
        for _ in range(opening.rival.turns_until_action):
            opening.end_turn()
        assert any(t.hp < t.max_hp for t in opening.rival.army)
        cases.append((f'{mode}-conquest', opening.to_json()))
        if mode != 'standard':
            continue
        central = State.new(7, difficulty=mode)
        central.build('barracks'); central.recruit('swordsman')
        central.explore(); finish_battle(central); central.end_turn()
        for destination in ((-1, 0), (0, 0)):
            central.travel(destination)
            if central.battle:
                finish_battle(central)
            central.end_turn()
        assert central.rival.target == central.hero.pos and central.rival.intent == 'attack'
        cases.append((f'{mode}-announced-attack', central.to_json()))
        retreat = State.from_json(central.to_json())
        retreat.travel(retreat.rival.pos)
        assert retreat.battle_kind == 'intercept'
        for _ in range(2):
            retreat.battle.auto_turn()
        wounded = {unit.source_id: unit.hp for unit in retreat.battle.units if unit.team == 'enemy' and unit.alive}
        retreat.retreat()
        assert {troop.id: troop.hp for troop in retreat.rival.army} == wounded
        assert retreat.rival.intent == 'return' and any(t.hp < t.max_hp for t in retreat.rival.army)
        cases.append((f'{mode}-intercept-survivors', retreat.to_json()))
        for _ in range(8):
            if retreat.rival.intent == 'recover':
                break
            retreat.end_turn()
        assert retreat.rival.pos == (2, 0) and retreat.rival.intent == 'recover'
        cases.append((f'{mode}-recovering', retreat.to_json()))
        before_gold = retreat.rival.gold + retreat.rival.income(retreat) - retreat.rival.upkeep
        missing = sum(t.max_hp - t.hp for t in retreat.rival.army)
        retreat.end_turn()
        assert retreat.rival.gold == before_gold - missing and all(t.hp == t.max_hp for t in retreat.rival.army)
        cases.append((f'{mode}-healed', retreat.to_json()))
        for _ in range(central.rival.turns_until_action):
            central.end_turn()
        assert central.battle_kind == 'defense'
        finish_battle(central)
        assert not central.rival.army and central.rival.defeats == 1
        cases.append((f'{mode}-defeated', central.to_json()))
        for _ in range(central.rival.turns_until_action):
            central.end_turn()
        assert len(central.rival.army) == 1 and central.rival.army[0].id >= 7
        cases.append((f'{mode}-paid-recruit', central.to_json()))
    fixtures = ROOT / 'tests/eador/fixtures'
    v11 = next(case for case in json.loads((fixtures / 'v11_difficulty_cases.json').read_text()) if case['name'] == 'rival_order')
    cases.append(('saved-v11-order', State.from_json(json.dumps(v11['before'])).to_json()))
    v12 = next(case for case in json.loads((fixtures / 'v12_challenge1_cases.json').read_text())['cases'] if case['name'] == 'rest')
    old = State.from_json(json.dumps(v12['before']))
    assert old.rules_id == 'challenge-1'
    cases.append(('saved-challenge-1', old.to_json()))
    surrounded = State.from_json((fixtures / 'v3_fortified_capital.json').read_text())
    for _ in range(100):
        if surrounded.upkeep_shortfall:
            break
        surrounded.end_turn()
    assert surrounded.encircled and surrounded.upkeep_shortfall
    cases.append(('saved-encircled', surrounded.to_json()))
    for _, snapshot in cases:
        state = State.from_json(snapshot)
        assert state.status == 'playing' and not state.battle and not state.choice
    return tuple(cases)


def check_rival(scene):
    """The view shows exact saved orders, current resources, force health and applicable counterplay."""
    assert isinstance(scene, RivalScene)
    count = check_reading_layout(scene)
    state, rival = scene.root.state, scene.root.state.rival
    texts = [item.text for item in scene.ui.find_all(lambda item: isinstance(item, Label))]
    assert rival_order(state) in texts
    assert f'At {state.provinces[rival.pos].name} · {len(rival.army)} surviving troops' in texts
    assert f'{rival.gold} gold' in texts
    assert f'Income +{rival.income(state)} · Upkeep −{rival.upkeep} / turn' in texts
    assert any(state.rules.title.upper() in text for text in texts)
    for kind, cost in RECRUIT_COSTS.items():
        assert any(f'{UNITS[kind].name} {cost}' in text for text in texts)
    if state.encircled:
        advice = next(text for text in texts if text.startswith('Westwatch is encircled:'))
        assert all(state.provinces[pos].name in advice for pos in state.grid.neighbors((-2, 0)))
        assert 'Marketplace and rest are blocked' in advice and 'less experienced troops leave first' in advice
    else:
        assert any(f'first paid replacement waits {state.rules.replacement_delay} turns' in text for text in texts)
    visible = [troop for troop in rival.army if troop.id in scene.visible_troops]
    counts = Counter(texts)
    for text, expected in Counter(f'{troop.hp}/{troop.max_hp} health' for troop in visible).items():
        assert counts[text] == expected
    if not rival.army:
        assert 'Its expedition is broken.' in texts
        assert any("the capital's garrison is a separate force" in text for text in texts)
    return count


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    native, matrix = backend == 'pyglet', []
    with TemporaryDirectory(prefix='shardbound-rival-reading-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=native, output=output)
        try:
            opening = State.new(7).to_json()
            game.push(ShardScene(State.from_json(opening)))
            player.press('v')
            for key in ('t', 'right', 'escape'):
                player.press(key)
            assert reading_scale(game) == 100 and not (Path(directory) / 'settings.json').exists()
            for size in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(size)
                for percent in (100, 125):
                    for name, snapshot in prepared_rivals():
                        state = State.from_json(snapshot)
                        game.clear_and_push(ShardScene(state)); player.press('v')
                        for key in ('t', 'left' if percent == 100 else 'right', 'return'):
                            player.press(key)
                        ids = []
                        for page in range(game.scene.pages):
                            ids.extend(game.scene.visible_troops)
                            record = dict(case=name, rules_id=state.rules_id, percent=percent,
                                          window=game.window_size, page=page, troops=game.scene.visible_troops,
                                          order=rival_order(state), labels=check_rival(game.scene))
                            if native:
                                record['framebuffer'] = game.backend.capture_frame().size
                            matrix.append(record)
                            if size == (1280, 720) and (percent == 125 or name == 'standard-opening'):
                                player.capture(f'{name}-{percent}-page-{page + 1}')
                            if page + 1 < game.scene.pages:
                                player.press('right')
                        assert ids == [troop.id for troop in state.rival.army]
                        for key in ('e', 'return', 'f5', 'f9'):
                            player.press(key)
                        assert state.to_json() == snapshot and not saves.exists()
                        player.button('Locate expedition') if percent == 125 else player.press('l')
                        assert isinstance(game.scene, ShardScene) and game.scene.selected == state.rival.pos
                        assert state.to_json() == snapshot
            player.reload(snapshot)
            events, reloads = len(player.events), player.reloads
        finally:
            game._teardown()
        game = create_game(backend=backend, visible=False, save_dir=saves)
        try:
            player = PlayerInput(game, native=native, output=output)
            game.push(ShardScene(State.from_json(snapshot)))
            player.press('v')
            assert reading_scale(game) == 125
            check_rival(game.scene); player.capture('restarted-rival-125')
            player.press('escape')
            assert player.state.to_json() == snapshot
            events += len(player.events)
        finally:
            game._teardown()
    (output / 'matrix.json').write_text(json.dumps(matrix, indent=2) + '\n')
    print(f'{backend} rival reading passed: {len(matrix)} layouts / {events} inputs / {reloads} exact reload; {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-rival-reading'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    args = parser.parse_args()
    verify(args.output, backend=args.backend)
