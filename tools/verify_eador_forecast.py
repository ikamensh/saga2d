"""Read tactical objectives and consequences while executing paid, saved battle routes."""
import argparse
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
from eador.preferences import reading_scale
from eador.scene import BattleScene, ShardScene, TitleScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_control import verify as verify_control
from tools.verify_eador_extraction import verify as verify_extraction
from tools.verify_eador_guidance import check_reading_layout


class ForecastInput(PlayerInput):
    """Pause a real order to read it; settings and resize must preserve its entire state."""
    def __init__(self, *args, seen, layouts, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen, self.layouts = seen, layouts

    def press(self, name):
        super().press(name)
        self.inspect()

    def click(self, x, y):
        super().click(x, y)
        self.inspect()

    def inspect(self):
        scene = self.game.scene
        if not isinstance(scene, BattleScene):
            return
        labels = [c.text for c in scene.ui.walk() if isinstance(c, Label)]
        text = '\n'.join(labels)
        check_reading_layout(scene)
        categories = ('Smoke screen', 'Choose a highlighted hex', 'Pin ', 'Restore ',
                      'HP damage', 'Exchange positions', 'Rally:', 'Repulse to',
                      'Deal ', 'Sight blocked', 'Pinned:', 'Brace strikes first',
                      'Smoke clears', 'Guard +2 defense', 'Saved rules allow', 'F targets', 'Attack ')
        category = next((part for part in categories if part in text), None)
        assert category is not None, text
        objective = scene.battle.objective
        if objective.kind == 'hold':
            title = next(line for line in labels if line.startswith('HOLD THE SEAL'))
            assert f'{objective.progress}/{objective.required} turns' in title and f'By round {objective.deadline}' in title
            assert 'Keep an ally on the seal after consecutive enemy turns, with no adjacent foe. Losing control resets progress; rout also wins.' in labels
        elif objective.kind == 'extract':
            assert f'ESCAPE WITH CARGO · By round {objective.deadline}' in labels
            assert (scene.battle.evacuation_blocked_reason or 'Ready: V evacuates your hero and surviving army.') in labels
        else:
            assert 'Defeat every defender. Keep your hero alive. Exhaustion after 80 rounds.' in labels
        objective_key = f'objective.{objective.kind}.{objective.progress}.{scene.battle.evacuation_blocked_reason}'
        additions = {category, objective_key} - self.seen
        if not additions:
            return
        self.seen.update(additions)
        before = self.state.to_json()
        aim = scene.selected, scene.cursor, scene.hover, scene.targeting
        initial_window = self.game.window_size
        for window in ((1280, 720), (1280, 800), (1920, 1080)):
            self.game.set_window_size(window)
            self.game.tick(1 / 60)
            for percent in (100, 125):
                # Use base input here to avoid recursively observing the same pause.
                super().press('f2')
                super().press('left' if percent == 100 else 'right')
                super().press('return')
                assert self.game.scene is scene and reading_scale(self.game) == percent
                assert self.state.to_json() == before
                assert (scene.selected, scene.cursor, scene.hover, scene.targeting) == aim
                assert [c.text for c in scene.ui.walk() if isinstance(c, Label)] == labels
                check_reading_layout(scene)
                self.layouts.append(dict(category=category, objective=objective_key, new_cases=sorted(additions),
                                         window=window, percent=percent, text=labels))
                if window == (1280, 720):
                    name = ''.join(c if c.isalnum() else '-' for c in category).strip('-').lower()
                    super().capture(f'reading-{name}-{percent}', settle=False)
                    if objective_key in additions:
                        super().capture(f'objective-{len(self.seen)}-{objective.kind}-{percent}', settle=False)
        # Cancel an opposite setting at the queued target, then execute the route unchanged.
        super().press('f2'); super().press('left'); super().press('escape')
        assert reading_scale(self.game) == 125 and self.state.to_json() == before
        self.game.set_window_size(initial_window); self.game.tick(1 / 60)
        assert (scene.selected, scene.cursor, scene.hover, scene.targeting) == aim


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    sources = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'), *ROOT.glob('tools/*.py')]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    seen, layouts, routes = set(), [], []

    def player_type(*args, **kwargs):
        return ForecastInput(*args, seen=seen, layouts=layouts, **kwargs)

    for scenario in ('smoke', 'repulse', 'watch', 'rally', 'sight'):
        routes.append(verify_control(output / scenario, backend=backend, scenario=scenario, player_type=player_type))
    routes.append(verify_extraction(output / 'guided', backend=backend, player_type=player_type))
    with TemporaryDirectory(prefix='shardbound-forecast-bolt-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        try:
            player = player_type(game, native=backend == 'pyglet', output=output / 'bolt')
            game.push(TitleScene(7, hero_class='Wizard')); player.press('return')
            player.click(*game.scene.grid.center((-1, 0))); player.press('return')
            player.click(*game.scene.grid.center((-2, -1))); player.press('e')
            player.press('1'); player.press('f')
            battle, scene = player.state.battle, game.scene
            target = next(u for u in scene.action_targets() if u.pos == scene.cursor)
            hp, mana = target.hp, battle.mana
            damage, cost = battle.spell_preview('bolt', target.id), battle.spell_cost('bolt')
            player.press('return')
            assert target.hp == hp - damage and battle.mana == mana - cost and battle.unit(0).acted
            player.reload(player.state.to_json())
            player.press('t')
            assert isinstance(game.scene, ShardScene) and player.state.battle is None
            route = dict(input_activations=len(player.events), exact_save_reloads=player.reloads,
                         damage=damage, mana_cost=cost, inputs=player.events)
            (output / 'bolt').mkdir(exist_ok=True)
            (output / 'bolt' / 'journey.json').write_text(json.dumps(route, indent=2) + '\n')
            routes.append(route)
        finally:
            game._teardown(); game.backend.quit()
    required = {'Smoke screen', 'Pin ', 'Restore ', 'HP damage', 'Exchange positions',
                'Rally:', 'Repulse to', 'Deal ', 'Sight blocked', 'Saved rules allow', 'F targets'}
    assert required <= seen, required - seen
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha for name, sha in hashes.items())
    report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, backend=backend, layouts=layouts,
                  input_activations=sum(route['input_activations'] for route in routes),
                  exact_save_reloads=sum(route['exact_save_reloads'] for route in routes),
                  route_reports=[str(path.relative_to(output)) for path in sorted(output.glob('*/journey.json'))])
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Forecast reading passed ({backend}): {len(layouts)} layouts / {report["input_activations"]} inputs')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-forecast-reading'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    args = parser.parse_args()
    verify(args.output, backend=args.backend)
