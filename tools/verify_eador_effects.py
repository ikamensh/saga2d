"""Capture short native effects from legal orders on fresh and paid preparation states."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from eador.app import create_game
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import BattleScene, ShardScene
from saga2d.testing.cpu_budget import CpuBudget
from tools.eador_sources import framework_sources, source_name
from tools.eador_observatory_campaign import prepare_observatory
from tools.eador_ui import PlayerInput
from saga2d.testing.native_frames import tick

CASES = ('arrow', 'bolt', 'melee', 'heal', 'swap', 'smoke')


def verify(output, *, backend='pyglet', budget=None, case=None):
    """Presentation evidence, not an independent first run: preparation uses public model commands."""
    if case is not None and case not in CASES:
        raise ValueError(f'Unknown effect case: {case}')
    budget = CpuBudget(25) if budget is None else budget
    output.mkdir(parents=True, exist_ok=True)
    started, cpu_started = time.monotonic(), time.process_time()
    paths = [*ROOT.glob('eador/*.py'), *framework_sources(),
             *ROOT.glob('tools/eador_*.py'), *ROOT.glob('eador/assets/*manifest.json'),
             Path(__file__).resolve()]
    hashes = {source_name(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    prepared = prepare_observatory(budget=budget)
    budget.checkpoint()
    report = {'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'dirty_at_start': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
              'source_sha256': hashes, 'backend': backend, 'reading_scale': 100,
              'preparation': 'Fresh Wizard home site; Commander army from prepare_observatory using public model commands. Site entry, the paid two-crystal clear approach and all demonstrated orders use native controls.',
              'cases': [], 'cpu_percent_requested': budget.percent}
    with TemporaryDirectory(prefix='shardbound-effects-') as temporary:
        game = create_game(backend=backend, visible=False, save_dir=Path(temporary) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output, finish_actions=False)
        try:
            for name in CASES if case is None else (case,):
                state = State.new(hero_class='Wizard') if name in ('arrow', 'bolt') else State.from_json(prepared.to_json())
                game.clear_and_push(ShardScene(state))
                tick(game) if backend == 'pyglet' else game.tick(1 / 60)
                assert reading_scale(game) == 100
                example = {'name': name, 'orders': [], 'captures': []}
                expected = State.from_json(state.to_json())
                approach = None if name in ('arrow', 'bolt') else 'clear'
                expected.explore(approach=approach)
                player.state.explore(approach=approach)
                assert player.state.to_json() == expected.to_json()
                budget.checkpoint()

                def order(command, *args, **options):
                    before = player.state.to_json()
                    expected = State.from_json(before)
                    getattr(expected.battle, command)(*args, **options)
                    player.order('battle.' + command, *args, **options)
                    assert type(game.scene) is BattleScene
                    assert player.state.to_json() == expected.to_json()
                    example['orders'].append({'command': command, 'args': args, 'options': options,
                                           'before': json.loads(before), 'after': json.loads(expected.to_json())})
                    budget.checkpoint()

                battle = player.state.battle
                if name == 'arrow':
                    archer = next(unit for unit in battle.units if unit.team == 'player' and unit.can_pin)
                    order('move', archer.id, (-1, 0))
                    order('attack', archer.id, battle.targets(archer.id)[0].id)
                elif name == 'bolt':
                    destination = min(battle.reachable(0), key=lambda pos: min(
                        battle.grid.distance(pos, unit.pos) for unit in battle.units if unit.team == 'enemy'))
                    order('move', 0, destination)
                    order('cast', 'bolt', battle.spell_targets('bolt')[0].id)
                elif name in ('melee', 'heal'):
                    for ident, pos in ((1, (1, -1)), (0, (0, 0)), (3, (0, -1))):
                        order('move', ident, pos)
                    guard = next(unit for unit in battle.units if unit.team == 'enemy' and unit.kind == 'guard')
                    order('attack', 0, guard.id)
                    if name == 'heal':
                        assert 0 < battle.unit(0).hp < battle.unit(0).max_hp
                        for ident, pos in ((4, (-1, 0)), (5, (-1, 1)), (6, (-2, 1))):
                            order('move', ident, pos)
                        order('cast', 'heal', 0, caster_id=6)
                elif name == 'swap':
                    warden = next(unit for unit in battle.units if unit.team == 'player' and unit.can_swap)
                    order('swap', warden.id, battle.swap_targets(warden.id)[0].id)
                else:
                    sapper = next(unit for unit in battle.units if unit.team == 'player' and unit.can_smoke)
                    destination = min(battle.smoke_targets(sapper.id), key=lambda pos: battle.grid.distance(pos, (0, 0)))
                    order('smoke', sapper.id, destination)
                resolved = player.state.to_json()
                for frame in range(39):
                    tick(game) if backend == 'pyglet' else game.tick(1 / 60)
                    budget.checkpoint()
                    assert player.state.to_json() == resolved
                    if frame in (6, 20, 34):
                        filename = f'{name}-{frame:02}.png'
                        if backend == 'pyglet':
                            game.backend.capture_frame().save(output / filename)
                        example['captures'].append({'file': filename if backend == 'pyglet' else None,
                                                 'frame': frame, 'game_seconds': (frame + 2) / 60})
                player.reload(resolved)
                budget.checkpoint()
                report['cases'].append(example)
            report['inputs'], report['input_activations'] = player.events, len(player.events)
            report['exact_save_reloads'] = player.reloads
            report['briefings'] = player.briefings
        finally:
            game.close()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    report['wall_seconds'], report['cpu_seconds'] = time.monotonic() - started, time.process_time() - cpu_started
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"Effects: {len(report['cases'])} cases, {player.reloads} exact reloads, {len(player.events)} inputs ({backend})")
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-effects'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--case', choices=CASES)
    parser.add_argument('--cpu-percent', type=float, default=25)
    args = parser.parse_args()
    verify(args.output, backend=args.backend, budget=CpuBudget(args.cpu_percent), case=args.case)
