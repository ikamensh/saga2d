"""Read paid and historical battle bodies, then execute their unchanged public orders."""
from __future__ import annotations

import argparse
from functools import cache
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

from saga2d import Button, Label, SaveManager
from eador.app import create_game
from eador.diagnostics import DiagnosticScene
from eador.model import RECRUITABLE, State
from eador.persistence import AUTO_SLOTS, CampaignSaves
from eador.preferences import reading_scale
from eador.scene import BattleScene, ShardScene
from tools.eador_control_campaign import prepare_control_watch
from tools.eador_explorer_campaign import prepare_explorer
from tools.eador_roles_campaign import prepare_support_watch
from tools.eador_ui import PlayerInput
from tools.verify_eador_diagnostics import queued_keys, read_all
from tools.verify_eador_guidance import check_reading_layout


@cache
def prepared_battles():
    """Only ordinary paid routes and unchanged historical active saves supply these bodies."""
    cases = [('control-watch', prepare_control_watch()),
             ('support-watch', prepare_support_watch()),
             ('infantry-watch', prepare_control_watch(kinds=('swordsman', 'pikeman')))]
    explorer = prepare_explorer()
    explorer.explore(approach='north')
    cases.append(('explorer', explorer))
    for name in ('v10_pinned_crossing', 'v8_acolyte_battle'):
        cases.append((name, State.from_json((ROOT / 'tests/eador/fixtures' / f'{name}.json').read_text())))
    return tuple((name, state.to_json()) for name, state in cases)


def centers(scene):
    return {pos: scene.grid.center(pos) for pos in scene.battle.terrain}


def inspect_body(scene, unit):
    """Visible numeric facts and ordinary guidance agree with the actual saved capability."""
    check_reading_layout(scene)
    labels = [component.text for component in scene.ui.walk() if isinstance(component, Label)]
    assert f'{unit.hp} / {unit.max_hp} HP' in labels
    assert f'Attack {unit.attack}   Defense {unit.effective_defense}' in labels
    movement = f"{'Fly' if unit.can_fly else 'Move'} {unit.effective_move_range}"
    assert any(movement in text and f'Range {unit.attack_range}' in text for text in labels)
    if unit.pinned:
        assert any('Pinned' in text for text in labels)
    if unit.cargo_penalty:
        assert any(f'Cargo −{unit.cargo_penalty}' in text for text in labels)
    assert any(str(scene.battle.mana) in text and 'SHARED MANA' in text for text in labels)
    assert scene.order_hint() in labels, (unit.kind, scene.order_hint(), labels)
    assert not scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Read message')
    caster = 'Acolyte' if unit.can_heal else 'Hero'
    assert scene.ui.find(lambda item: isinstance(item, Button) and
                         item.text == f"{caster} Heal · {scene.battle.spell_cost('heal')} mana")
    return labels


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    paths = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'), *ROOT.glob('tools/*.py')]
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines()
    native, matrix, roles, orders = backend == 'pyglet', [], set(), []
    with TemporaryDirectory(prefix='battle-hud-reading-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=native, output=output)
        try:
            for window in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(window)
                for percent in (100, 125):
                    for name, snapshot in prepared_battles():
                        game.clear_and_push(ShardScene(State.from_json(snapshot)))
                        scene = game.scene
                        assert isinstance(scene, BattleScene)
                        player.press('f2'); player.press('left' if percent == 100 else 'right'); player.press('return')
                        assert reading_scale(game) == percent
                        state, geometry = player.root.state, centers(scene)
                        for unit in scene.battle.units:
                            if unit.team != 'player' or not unit.alive:
                                continue
                            player.click(*scene.grid.center(unit.pos))
                            assert scene.selected == unit.id
                            labels = inspect_body(scene, unit)
                            assert centers(scene) == geometry and state.to_json() == snapshot
                            roles.add(unit.kind)
                            matrix.append(dict(case=name, unit_id=unit.id, kind=unit.kind, window=game.window_size,
                                               percent=percent, grid_size=scene.grid.size, footer_top=scene.footer_top,
                                               unit=dict(hp=unit.hp, max_hp=unit.max_hp, attack=unit.attack,
                                                    defense=unit.effective_defense, move=unit.effective_move_range,
                                                    range=unit.attack_range, can_heal=unit.can_heal),
                                               text=labels))
                            if native and window == (1280, 720) and percent == 125 and (
                                    name == 'explorer' or unit.kind in ('warden', 'adept', 'skyrider', 'swordsman', 'pikeman') or unit.id == 0):
                                player.capture(f'{name}-{unit.id}-125')
                            if scene.unit_order:
                                title, key, _, _ = scene.unit_orders[scene.unit_order]
                                control = scene.ui.find(lambda item: isinstance(item, Button) and item.text.startswith(title))
                                if control.enabled:
                                    player.press(key.lower())
                                    text = [item.text for item in scene.ui.walk() if isinstance(item, Label)]
                                    assert scene.message in text and state.to_json() == snapshot
                                    check_reading_layout(scene)
                                    assert not scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Read message')
                                    player.press('escape')
                                    assert centers(scene) == geometry
                        player.press('f')
                        aim = scene.selected, scene.cursor, scene.hover, scene.targeting
                        player.press('l')
                        assert isinstance(game.scene, DiagnosticScene)
                        assert game.scene.message == '\n'.join(scene.battle.log)
                        for key in ('e', 'g', 'a', '1', 'f5', 'f9'):
                            player.press(key)
                            assert isinstance(game.scene, DiagnosticScene) and state.to_json() == snapshot
                        player.press('t'); player.press('left' if percent == 125 else 'right'); player.press('escape')
                        player.press('escape')
                        assert game.scene is scene and reading_scale(game) == percent and state.to_json() == snapshot
                        assert (scene.selected, scene.cursor, scene.hover, scene.targeting) == aim
                        # A real move followed by Guard changes precisely the public model result.
                        unit_id, destination = next((unit.id, pos) for unit in scene.battle.units
                            if unit.team == 'player' and unit.alive and not unit.acted
                            for pos in sorted(scene.battle.reachable(unit.id)) if pos != unit.pos)
                        player.click(*scene.grid.center(scene.battle.unit(unit_id).pos))
                        expected = State.from_json(state.to_json()); expected.battle.move(unit_id, destination)
                        player.click(*scene.grid.center(destination))
                        assert state.to_json() == expected.to_json() and centers(scene) == geometry
                        expected.battle.guard(unit_id); player.press('g')
                        assert state.to_json() == expected.to_json() and centers(scene) == geometry
                        orders.append(dict(case=name, percent=percent, window=game.window_size,
                                           unit_id=unit_id, move=destination, guard=True))
                        player.reload(state.to_json())
            assert set(RECRUITABLE) <= roles, set(RECRUITABLE) - roles
            events, reloads = len(player.events), player.reloads
        finally:
            game._teardown(); game.backend.quit()

    # A filesystem failure occurs after End round; the already-applied battle survives reading and reload.
    error_pages = []
    with TemporaryDirectory(prefix='battle-hud-save-error-') as directory:
        saves_dir = Path(directory)
        for index in range(9):
            saves_dir /= f'ordinary-directory-{index}-' + 'a' * 70
        saves_dir.mkdir(parents=True)
        state = State.new(7); state.travel((-1, 0))
        saves = CampaignSaves(SaveManager(saves_dir))
        for slot in AUTO_SLOTS:
            assert saves.autosave(state) == slot
        conflict = saves_dir / f'save_{AUTO_SLOTS[0]}.backup.json'
        conflict.mkdir()
        old_files = {path.name: path.read_bytes() for path in saves_dir.iterdir() if path.is_file()}
        game = create_game(backend=backend, visible=False, save_dir=saves_dir)
        player = PlayerInput(game, native=native, output=output)
        try:
            game.set_window_size((1280, 720)); game.push(ShardScene(state))
            scene = game.scene
            player.press('f2'); player.press('right'); player.press('return')
            geometry = centers(scene)
            expected = State.from_json(state.to_json()); expected.battle.end_turn()
            player.press('e')
            assert state.to_json() == expected.to_json() and game.scene is scene and centers(scene) == geometry
            check_reading_layout(scene); player.capture('actual-applied-autosave-error')
            player.press('m')
            assert isinstance(game.scene, DiagnosticScene)
            message = read_all(player, error_pages, 'actual-autosave-error', capture=True)
            assert str(conflict) in message
            queued_keys(player, ('return', 'e', 'return', 'space'))
            assert game.scene is scene and state.to_json() == expected.to_json()
            assert all((saves_dir / name).read_bytes() == data for name, data in old_files.items())
            player.press('m'); assert game.scene.message == message
            player.press('escape')
            player.reload(expected.to_json())
            assert player.state.to_json() == expected.to_json()
            events += len(player.events); reloads += player.reloads
        finally:
            game._teardown(); game.backend.quit()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    report = dict(source_commit=source, dirty_at_start=dirty, source_sha256=hashes, source_files_changed=False,
                  backend=backend, unit_views=matrix, roles=sorted(roles), orders=orders,
                  input_activations=events, exact_save_reloads=reloads, error_pages=error_pages)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Battle HUD passed ({backend}): {len(matrix)} unit views / {events} inputs / {reloads} exact reloads', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-battle-hud'))
    args = parser.parse_args()
    verify(args.output, backend=args.backend)
