"""Inspect earned battle/world conclusions and save failures at both reading sizes."""
from __future__ import annotations

import argparse
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d import Label
from eador.app import create_game
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import BattleScene, ResultScene, ShardScene, TitleScene
from tools.eador_campaign import finish_battle, play_campaign
from tools.eador_extraction_campaign import AdventureOrders, prepare_adventure, crossing_route
from tools.eador_observatory_campaign import prepare_observatory, observatory_route
from tools.eador_ui import PlayerInput
from tools.cpu_budget import CpuBudget
from tools.verify_eador_guidance import check_reading_layout


def prepared_results(*, budget=None):
    """Actual public purchases and tactics earn all conclusion types without editing saved fields."""
    budget = CpuBudget(25) if budget is None else budget
    cases = []
    state = State.new(7, 'Wizard')
    state.explore()
    while not state.battle.outcome:
        budget.checkpoint()
        state.battle.auto_turn()
    cases.append(('rout', state.to_json()))

    # March east without recovery or investment until the first genuine defeat.
    state = State.new(0)
    for _ in range(8):
        budget.checkpoint()
        if not state.actions_left:
            state.end_turn()
        if not state.battle:
            state.travel(state.grid.path(state.hero.pos, (2, 0))[1])
        if not state.battle:
            continue
        while not state.battle.outcome:
            budget.checkpoint()
            state.battle.auto_turn()
        if state.battle.outcome == 'enemy':
            break
        state.resolve_battle()
        while state.choice:
            state.choose(state.choice.options[0].id)
    assert state.battle.outcome_reason == 'hero_death'
    cases.append(('hero-death', state.to_json()))

    crossing = prepare_adventure(budget=budget)
    observatory = prepare_observatory(budget=budget)
    orders = partial(AdventureOrders, budget=budget)
    for name, play in (('escape', crossing_route(State.from_json(crossing.to_json()), 'guided', orders_type=orders)),
                       ('hold', observatory_route(State.from_json(observatory.to_json()), 'clear', orders_type=orders))):
        assert play.battle.outcome_reason == name
        cases.append((name, play.state.to_json()))
    for name, state, approach in (('extract-deadline', crossing, 'direct'), ('hold-deadline', observatory, 'clear')):
        state.explore(approach=approach)
        for _ in range(20):
            budget.checkpoint()
            battle = state.battle
            if battle.outcome:
                break
            for unit in battle.units:
                if unit.team == 'player' and unit.alive and not unit.acted:
                    battle.guard(unit.id)
            battle.end_turn()
        assert state.battle.outcome_reason == 'deadline'
        cases.append((name, state.to_json()))

    victory = play_campaign(State.new(0), budget=budget)
    assert victory.status == 'victory'
    cases.append(('shard-victory', victory.to_json()))
    defeat = State.new(7)
    defeat.travel((-1, 0))
    finish_battle(defeat, budget=budget)
    for _ in range(50):
        budget.checkpoint()
        if defeat.status != 'playing':
            break
        defeat.end_turn()
        if defeat.battle:
            finish_battle(defeat, budget=budget)
    assert defeat.status == 'defeat'
    cases.append(('capital-lost', defeat.to_json()))
    budget.checkpoint()
    return cases


def verify(output, *, backend='pyglet', budget=None):
    budget = CpuBudget(25) if budget is None else budget
    output.mkdir(parents=True, exist_ok=True)
    sources = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'), *ROOT.glob('tools/*.py')]
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    metrics, native = [], backend == 'pyglet'
    with TemporaryDirectory(prefix='eador-results-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=native, output=output)
        try:
            game.set_window_size((1280, 720))
            game.push(TitleScene(7, hero_class='Wizard'))
            player.press('return')
            player.press('x')
            while isinstance(game.scene, BattleScene):
                player.press('a')
            assert isinstance(game.scene, ResultScene)
            before = player.state.to_json()
            for key in ('t', 'right', 'escape'):
                player.press(key)
            assert not (Path(directory) / 'settings.json').exists()
            for key in ('t', 'right', 'return', 'c', 'escape'):
                player.press(key)
            assert player.state.to_json() == before
            check_reading_layout(game.scene)
            player.capture('earned-rout-125')
            player.button('Saves')
            player.press('escape')
            player.reload(before)
            (saves / 'save_1.json').write_bytes(b'damaged manual save')
            for key in ('f5', 'f9'):
                player.press(key)
                assert isinstance(game.scene, ResultScene) and player.state.to_json() == before
                assert game.scene.message and any(item.text == game.scene.message
                       for item in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
                check_reading_layout(game.scene)
                assert (saves / 'save_1.json').read_bytes() == b'damaged manual save'
            player.capture('result-save-error-125')
            expected = State.from_json(before)
            expected.resolve_battle()
            player.button('Return to shard')
            assert player.state.to_json() == expected.to_json()

            for name, snapshot in prepared_results(budget=budget):
                for size in ((1280, 720), (1280, 800), (1920, 1080)):
                    game.set_window_size(size)
                    game.clear_and_push(ShardScene(State.from_json(snapshot)))
                    assert isinstance(game.scene, ResultScene), name
                    for percent in (100, 125):
                        for key in ('t', 'left' if percent == 100 else 'right', 'return'):
                            player.press(key)
                        record = dict(case=name, percent=percent, window=game.window_size,
                                      snapshot_sha256=hashlib.sha256(snapshot.encode()).hexdigest(),
                                      labels=check_reading_layout(game.scene))
                        if native:
                            record['framebuffer'] = game.backend.capture_frame().size
                        metrics.append(record)
                        if size == (1280, 720):
                            player.capture(f'{name}-{percent}')
                        assert player.state.to_json() == snapshot
            before_restart = player.state.to_json()
        finally:
            try:
                game._teardown()
            finally:
                game.backend.quit()
        restarted = create_game(backend=backend, visible=False, save_dir=saves)
        try:
            assert reading_scale(restarted) == 125
            replay = PlayerInput(restarted, native=native, output=output)
            restarted.push(ShardScene(State.from_json(before_restart)))
            restarted.tick(1 / 60)
            assert isinstance(restarted.scene, ResultScene)
            check_reading_layout(restarted.scene)
            replay.capture('result-restarted-125')
            replay.button('New shard')
            assert isinstance(restarted.scene, TitleScene)
            events = len(player.events) + len(replay.events)
        finally:
            try:
                restarted._teardown()
            finally:
                restarted.backend.quit()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  backend=backend, source_sha256=hashes, source_unchanged=True, input_events=events,
                  exact_reloads=player.reloads, matrix=metrics, cpu_percent=budget.percent)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Result reading passed ({backend}): {len(metrics)} outcome views, {events} inputs; {output}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-results'))
    parser.add_argument('--backend', choices=('pyglet', 'mock'), default='pyglet')
    parser.add_argument('--cpu-percent', type=float, default=25,
                        help='Model preparation CPU allowance as a percent of one core (default 25; 100 for explicit stress)')
    args = parser.parse_args(argv)
    try:
        budget = CpuBudget(args.cpu_percent)
    except ValueError as error:
        parser.error(str(error))
    verify(args.output, backend=args.backend, budget=budget)


if __name__ == '__main__':
    main()
