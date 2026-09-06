"""Check shared reading size through native Guide/Settings input and restart."""

import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SAGA2D_SILENT'] = '1'

from saga2d import Button, Label
from eador.app import create_game
from eador.encounter_scene import EncounterScene
from eador.preferences import reading_scale
from eador.scene import BattleScene, HelpScene, ShardScene, TitleScene
from tools.eador_ui import PlayerInput


def check_reading_layout(scene):
    """Every reading Label stays on canvas and clear of other text and controls."""
    labels = scene.ui.find_all(lambda item: isinstance(item, Label) and item.visible)
    controls = scene.ui.find_all(lambda item: isinstance(item, Button) and item.visible)
    assert labels
    for index, label in enumerate(labels):
        x, y, width, height = label.bounds
        assert 0 <= x < x + width <= scene.game.width
        assert 0 <= y < y + height <= scene.game.height
        for other in labels[index + 1:] + controls:
            ox, oy, ow, oh = other.bounds
            assert x + width <= ox or ox + ow <= x or y + height <= oy or oy + oh <= y, (label.text, other.text)
    return len(labels)


def prepared_briefings():
    """Actual paid routes plus retreat checkpoints; no injected units, prices or wounds."""
    from eador.model import State, UNITS
    from tools.eador_campaign import finish_battle, march_to, rest
    from tools.eador_extraction_campaign import prepare_adventure
    from tools.eador_explorer_campaign import prepare_explorer
    from tools.eador_hunt_campaign import prepare_pack_hunt
    from tools.eador_observatory_campaign import prepare_observatory
    from tools.eador_relic_campaign import prepare_relic_gate
    from tools.eador_vault_campaign import prepare_vault
    from tools.eador_screen_campaign import prepare_screen
    from tools.eador_aerie_campaign import prepare_aerie, aerie_failed_sortie

    cases = [('crossing', prepare_adventure(), None),
             ('cache', prepare_adventure(theme='elderwild'), None),
             ('vault', prepare_vault(), None), ('hunt', prepare_pack_hunt(), None),
             ('observatory', prepare_observatory(), None),
             ('aerie', prepare_aerie(), None),
             ('aerie-scout', prepare_aerie('Scout', party='ground'), None),
             ('screen-commander', prepare_screen(), None),
             ('screen-scout', prepare_screen('Scout'), None),
             ('explorer-ranger', prepare_explorer(), None),
             ('explorer-acolyte', prepare_explorer('Warrior', support='healer'), None),
             ('explorer-alone', prepare_explorer('Scout', support=None), None)]
    watch = State.new(7)
    watch.build('barracks'); watch.recruit('pikeman'); watch.explore(); finish_battle(watch)
    for pos in ((-1, -1), (0, -2)):
        march_to(watch, pos); rest(watch)
    cases.append(('watch', watch, None))
    gate = prepare_relic_gate('porter_rune')
    gate.retreat()
    cases.append(('gate-retry', gate, (2, 0)))
    wounded = prepare_observatory()
    wounded.explore(approach='clear'); wounded.battle.auto_turn(); wounded.retreat()
    province = wounded.provinces[wounded.hero.pos]
    assert 0 < sum(province.site_guard_hp) < sum(UNITS[kind].hp for kind in province.site_guards)
    cases.append(('observatory-wounded', wounded, None))
    screened = prepare_screen()
    screened.explore(approach='western'); screened.battle.auto_turn(); screened.retreat()
    cases.append(('screen-wounded', screened, None))
    aerie = aerie_failed_sortie(prepare_aerie()).state
    aerie.resolve_battle()
    cases.append(('aerie-wounded', aerie, None))
    poor = prepare_adventure()
    poor.build('archery'); poor.build('market'); poor.recruit('ranger')
    poor.explore(approach='guided'); poor.retreat()
    assert poor.actions_left and poor.gold < poor.adventure_approaches()[1].gold_cost
    cases.append(('crossing-fee-blocked', poor, None))
    return [(name, state.to_json(), destination) for name, state, destination in cases]


def verify_briefing_matrix(game, *, native=False, output=None):
    """Review every current authored approach at both sizes without spending its entry cost."""
    from eador.model import State

    cases = prepared_briefings()
    player = PlayerInput(game, native=native, output=output)
    metrics = []
    for size in ((1280, 720), (1280, 800), (1920, 1080)):
        game.set_window_size(size)
        for name, snapshot, destination in cases:
            state = State.from_json(snapshot)
            before = state.to_json()
            game.clear_and_push(ShardScene(state))
            if destination is None:
                player.press('x')
            else:
                player.click(*game.scene.grid.center(destination))
                player.press('return')
            assert isinstance(game.scene, EncounterScene), name
            for percent in (100, 125):
                player.press('t')
                player.press('left' if percent == 100 else 'right')
                player.button('Apply')
                for index in range(max(1, len(game.scene.approaches))):
                    if game.scene.approaches:
                        if percent == 100:
                            player.press(str(index + 1))
                        else:
                            player.button(game.scene.approaches[index].title)
                    scene = game.scene
                    metrics.append(dict(screen=name, encounter=scene.approach.encounter if scene.approach else state.encounter_at(scene.destination, kind=scene.kind),
                                        approach=scene.approach.id if scene.approach else None,
                                        percent=percent, window=game.window_size,
                                        labels=check_reading_layout(scene), blocked=scene.entry_blocked_reason))
                    if native:
                        metrics[-1]['framebuffer'] = game.backend.capture_frame().size
                    if scene.entry_blocked_reason:
                        player.press('return')
                        assert game.scene is scene
                    assert state.to_json() == before
                    if size == (1280, 720) and (percent == 125 or name == 'explorer-ranger'):
                        player.capture(f'{name}-{index + 1}-{percent}')
            player.press('escape')
            assert isinstance(game.scene, ShardScene) and state.to_json() == before
    from eador.encounters import ENCOUNTERS
    assert {row['encounter'] for row in metrics} == set(ENCOUNTERS), 'Add a public preparation for the new encounter'
    return metrics


def verify(output, *, matrix=False):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='eador-guidance-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(visible=False, save_dir=saves)
        player = PlayerInput(game, native=True, output=output)
        metrics = []
        try:
            game.set_window_size((1280, 720))
            game.push(TitleScene(7))
            player.press('return')
            saved = player.state.to_json()
            player.press('f1')
            assert isinstance(game.scene, HelpScene)
            check_reading_layout(game.scene)
            player.capture('guide-100')
            for key in ('o', 'd', 'down', 'down', 'down', 'right'):
                player.press(key)
            player.capture('settings-reading-125')
            player.button('Cancel')
            assert reading_scale(game) == 100
            assert not (Path(directory) / 'settings.json').exists()
            for key in ('o', 'd', 'down', 'down', 'down', 'right', 'return'):
                player.press(key)
            assert reading_scale(game) == 125
            for size in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(size)
                game.tick(1 / 60)
                metrics.append(dict(screen='guide', window=game.window_size,
                                    framebuffer=game.backend.capture_frame().size,
                                    percent=reading_scale(game), labels=check_reading_layout(game.scene)))
                player.capture(f'guide-125-{size[0]}x{size[1]}')
            player.press('c')
            assert any(entry.title == 'Militia' for entry in game.scene.visible_entries)
            player.press('escape')
            assert isinstance(game.scene, HelpScene) and player.state.to_json() == saved
            from tools.eador_observatory_campaign import prepare_observatory
            state = prepare_observatory()
            before = state.to_json()
            game.clear_and_push(ShardScene(state))
            player.press('x')
            player.press('2')
            assert isinstance(game.scene, EncounterScene)
            approach, definition = game.scene.approach, game.scene.definition
            for size in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(size)
                game.tick(1 / 60)
                metrics.append(dict(screen='observatory-clear-briefing', window=game.window_size,
                                    framebuffer=game.backend.capture_frame().size,
                                    percent=reading_scale(game), labels=check_reading_layout(game.scene)))
                player.capture(f'observatory-clear-125-{size[0]}x{size[1]}')
            for key in ('t', 'left', 'escape'):
                player.press(key)
            assert reading_scale(game) == 125 and game.scene.approach == approach
            assert state.to_json() == before
            player.button('Enter expedition')
            assert isinstance(game.scene, BattleScene)
            assert state.battle.terrain == dict(definition.terrain)
            player.reload(state.to_json())
            if matrix:
                metrics.extend(verify_briefing_matrix(game, native=True, output=output / 'matrix'))
        finally:
            game._teardown()
            game.backend.quit()
        game = create_game(visible=False, save_dir=saves)
        try:
            from eador.model import State
            game.push(ShardScene(State.from_json(saved)))
            player = PlayerInput(game, native=True, output=output)
            player.press('f1')
            assert reading_scale(game) == 125
            check_reading_layout(game.scene)
            player.capture('guide-restarted-125')
        finally:
            game._teardown()
            game.backend.quit()
    (output / 'matrix.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print(f'Native guidance preview, Cancel, Apply, resize and restart passed: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-guidance'))
    parser.add_argument('--matrix', action='store_true', help='review every current paid approach at both sizes')
    args = parser.parse_args()
    verify(args.output, matrix=args.matrix)
