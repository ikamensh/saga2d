"""Earn, reload and read every current reward family through actual player input."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d import Button, Label
from eador.app import create_game
from eador.content import RELICS
from eador.model import HERO_CLASSES, State
from eador.persistence import AUTO_SLOTS
from eador.preferences import reading_scale
from eador.scene import ChoiceScene, ShardScene
from tools.eador_campaign import play_campaign
from tools.eador_ui import PlayerInput
from saga2d.testing.cpu_budget import CpuBudget
from saga2d.testing.native_frames import tick
from tools.verify_eador_guidance import check_reading_layout


def prepared_choices(*, budget=None):
    """Record decisions before the public campaign policy chooses; no invented inventory, XP or text."""
    budget = CpuBudget(25) if budget is None else budget
    choices = {}

    class Rewards:
        def __init__(self, state):
            self.state = state

        def __getattr__(self, name):
            return getattr(self.state, name)

        def choose(self, option_id):
            choice = self.state.choice
            key = choice.kind, choice.context, tuple(option.name for option in choice.options)
            choices.setdefault(key, self.state.to_json())
            self.state.choose(option_id)

    for hero in HERO_CLASSES:
        for theme in ('frontier', 'elderwild', 'ruins'):
            budget.checkpoint()
            state = State.new(0, hero, theme=theme)
            route = [state.hero.pos] + [pos for pos in sorted(state.provinces)
                                       if pos not in (state.hero.pos, (2, 0))] + [(2, 0)]
            play_campaign(Rewards(state), route, reload_state=lambda snapshot: Rewards(State.from_json(snapshot)),
                          budget=budget)
    assert {key[1] for key in choices if key[0] == 'relic'} == set(RELICS)
    assert {key[1] for key in choices if key[0] == 'skill'} == set(HERO_CLASSES)
    assert any('Distill the duplicate' in key[2] for key in choices)
    budget.checkpoint()
    return tuple((f'{index + 1:02}-{kind}-{context.lower()}', snapshot)
                 for index, ((kind, context, _), snapshot) in enumerate(choices.items()))


def check_choice(scene):
    """Whole option labels and numbered controls appear in the model's saved order."""
    assert isinstance(scene, ChoiceScene)
    count = check_reading_layout(scene)
    labels = [item.text for item in scene.ui.find_all(lambda item: isinstance(item, Label))]
    choice = scene.root.state.choice
    assert choice.title in labels and choice.description in labels
    controls = scene.ui.find_all(lambda item: isinstance(item, Button) and item.text.startswith('Choose '))
    assert len(controls) == len(choice.options)
    for option, control in zip(choice.options, controls):
        assert option.name in labels and option.description in labels
        title = scene.ui.find(lambda item: isinstance(item, Label) and item.text == option.name)
        assert title.bounds[0] == control.bounds[0]
        assert title.bounds[1] < control.bounds[1]
    assert [labels.index(option.name) for option in choice.options] == sorted(labels.index(option.name) for option in choice.options)
    return count


def verify(output, *, backend='pyglet', budget=None):
    budget = CpuBudget(25) if budget is None else budget
    output.mkdir(parents=True, exist_ok=True)
    metrics = []
    native = backend == 'pyglet'
    with TemporaryDirectory(prefix='eador-choices-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=native, output=output)
        try:
            cases = prepared_choices(budget=budget)
            before = cases[0][1]
            game.push(ShardScene(State.from_json(before)))
            for key in ('t', 'right', 'escape'):
                player.press(key)
            assert reading_scale(game) == 100 and not (Path(directory) / 'settings.json').exists()
            for key in ('t', 'right', 'return', 'c', 'escape', 'h', 'escape', 'f6', 'escape'):
                player.press(key)
            assert player.state.to_json() == before
            player.reload(before)
            for size in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(size)
                for percent in (100, 125):
                    for name, snapshot in cases:
                        budget.checkpoint()
                        state = State.from_json(snapshot)
                        game.clear_and_push(ShardScene(state))
                        for key in ('t', 'left' if percent == 100 else 'right', 'return'):
                            player.press(key)
                        metrics.append(dict(case=name, kind=state.choice.kind, context=state.choice.context,
                                            options=[option.name for option in state.choice.options],
                                            percent=percent, window=game.window_size,
                                            labels=check_choice(game.scene), cpu_percent=budget.percent))
                        assert state.to_json() == snapshot
                        if native:
                            metrics[-1]['framebuffer'] = game.backend.capture_frame().size
                        representative = (state.choice.kind == 'relic' and state.choice.context in
                                          ('moonstone', 'veil_censer', 'mirror_badge') and state.choice.options[0].id == 'take'
                                          or state.choice.context == 'storm_quiver' and state.choice.options[0].id == 'distill'
                                          or state.choice.kind == 'skill' and state.choice.context == 'Wizard'
                                          and state.choice.options[0].name == 'Channeling 1')
                        if size == (1280, 720) and representative:
                            player.capture(f'{name}-{percent}')
                        if percent == 125 and size == (1280, 720):
                            for index, option in enumerate(state.choice.options):
                                for method in ('keyboard', 'mouse'):
                                    budget.checkpoint()
                                    game.clear_and_push(ShardScene(State.from_json(snapshot)))
                                    tick(game) if native else game.tick(1 / 60)
                                    expected = State.from_json(snapshot)
                                    expected.choose(option.id)
                                    if method == 'keyboard':
                                        player.press(str(index + 1))
                                    else:
                                        control = game.scene.ui.find_all(lambda item: isinstance(item, Button)
                                                                         and item.text.startswith('Choose '))[index]
                                        x, y, width, height = control.bounds
                                        player.click(x + width / 2, y + height / 2)
                                    assert player.state.to_json() == expected.to_json()
            game.set_window_size((1280, 720))
            for slot in AUTO_SLOTS:
                (saves / f'save_{slot}.json').write_bytes(b'damaged autosave')
            state = State.from_json(before)
            game.clear_and_push(ShardScene(state))
            expected = State.from_json(before)
            expected.choose(expected.choice.options[1].id)
            player.press('2')
            assert isinstance(game.scene, ChoiceScene) and state.choice is None
            assert state.to_json() == expected.to_json()
            assert 'All autosave slots are damaged' in game.scene.message
            assert not game.scene.ui.find(lambda item: isinstance(item, Button) and item.text.startswith('Choose '))
            check_reading_layout(game.scene)
            player.capture('applied-save-error-125')
            for key in ('1', '2', 't', 'left', 'escape', 'f6', 'escape'):
                player.press(key)
            assert isinstance(game.scene, ChoiceScene) and state.to_json() == expected.to_json()
            player.press('f5')
            player.press('f9')
            assert isinstance(game.scene, ShardScene) and player.state.to_json() == expected.to_json()
            assert all((saves / f'save_{slot}.json').read_bytes() == b'damaged autosave' for slot in AUTO_SLOTS)
            for _, snapshot in cases:
                budget.checkpoint()
                state = State.from_json(snapshot)
                expected = State.from_json(snapshot)
                expected.choose(expected.choice.options[0].id)
                if expected.choice:
                    break
            else:
                raise AssertionError('The earned routes must produce a queued decision')
            game.clear_and_push(ShardScene(state))
            player.press('1')
            assert isinstance(game.scene, ChoiceScene) and state.to_json() == expected.to_json()
            assert 'All autosave slots are damaged' in game.scene.message
            check_choice(game.scene)
            player.capture('queued-save-error-125')
            restart = cases[0][1]
        finally:
            game.close()
        game = create_game(backend=backend, visible=False, save_dir=saves)
        try:
            game.push(ShardScene(State.from_json(restart)))
            tick(game) if native else game.tick(1 / 60)
            assert reading_scale(game) == 125
            check_choice(game.scene)
            PlayerInput(game, native=native, output=output).capture('restarted-125')
        finally:
            game.close()
    budget.checkpoint()
    (output / 'matrix.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print(f'{backend} earned choices passed: {len(cases)} decisions / {len(metrics)} layouts / '
          f'{len(player.events)} inputs; {output}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-choice-reading'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--cpu-percent', type=float, default=25,
                        help='CPU allowance as a percent of one core (default 25; 100 for explicit stress)')
    args = parser.parse_args(argv)
    try:
        budget = CpuBudget(args.cpu_percent)
    except ValueError as error:
        parser.error(str(error))
    verify(args.output, backend=args.backend, budget=budget)


if __name__ == '__main__':
    main()
