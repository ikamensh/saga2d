"""Save earned phases through UI, stop, and continue them in a fresh Python process.

Two current title starts use only New campaign and Explore. Later phases are
exact retained checkpoints: the manual seed5 route, the frozen package's
autoplay campaign, and an actual lost capital. No historical battles are replayed.
The child starts each Game at Title; its only route into saved state is F9/F6.
This proves a fresh process using the selected backend, not a packaged-app launch.
"""
from __future__ import annotations

import argparse
import gzip
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
from eador.persistence import CampaignSaves
from eador.scene import SaveScene, ShardScene, TitleScene
from tools.cpu_budget import CpuBudget
from tools.eador_ui import PlayerInput

JOURNAL = 'docs/evidence/adventure-variety/route-seed5.json.gz'
DEPARTURE = 'docs/evidence/shardbound-package-7b5562d/campaign/direct/phase-2.json.gz'
RECOVERY = 'docs/evidence/shardbound-package-7b5562d/campaign/recovery/phase-3.json.gz'
COMPLETED = 'docs/evidence/shardbound-package-7b5562d/campaign/direct/phase-4.json.gz'
CAPITAL_LOSS = 'docs/evidence/shardbound-candidate-validation/complete-journey/capital-loss.json.gz'
FIXED = {
    JOURNAL: 'cdccd3ef5ae9750098d371b6c31de7c97196aaa4091c2b7f56bebe564ccda846',
    DEPARTURE: '994f3ad5e8920a56715b5b1ce9959fe393c442d6d0053f8094cd6db9590bd833',
    RECOVERY: '20ec0bd3c155216a5edfeecba4797e636cdf22a471168455ee9cc27b9bf87539',
    COMPLETED: '71907fe83b2fe5bfb016e3002d78b96afa0ad1c6c94470b7e715cbc990e69c71',
    CAPITAL_LOSS: '4e79d080d35929c17cb24ec13383e59a1e186abe0e81b709b4eb17e79bf2f47d',
}
CASES = ('campaign', 'battle', 'skill', 'relic', 'result',
         'departure', 'recovery', 'completed', 'capital-loss')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _fingerprints():
    paths = {Path(__file__), ROOT / 'tools/eador_ui.py', ROOT / 'tools/cpu_budget.py',
             *(ROOT / 'eador').glob('*.py'), *(ROOT / 'saga2d').rglob('*.py'),
             *(ROOT / name for name in FIXED)}
    paths.update(path for path in (ROOT / 'eador/assets').rglob('*') if path.is_file())
    return {str(path.relative_to(ROOT)): _sha(path.read_bytes()) for path in sorted(paths)}


def _earned(name):
    if name in ('result', 'skill', 'relic'):
        source, index = JOURNAL, {'result': 103, 'skill': 104, 'relic': 105}[name]
        selector = f'commands[{index}].after'
        preparation = 'Agent-directed seed5 paid route; no autoplay. Execution source 37a4e60.'
    else:
        source = {'departure': DEPARTURE, 'recovery': RECOVERY,
                  'completed': COMPLETED, 'capital-loss': CAPITAL_LOSS}[name]
        selector = ('state.campaign' if name == 'capital-loss' else
                    'checkpoint' if name == 'completed' else 'loaded_checkpoint')
        preparation = ('Actual capital loss from the earlier complete-journey test; visible A autoplay.'
                       if name == 'capital-loss' else
                       'Frozen package from clean 7b5562d; paid linked campaign using visible A autoplay.')
    data = (ROOT / source).read_bytes()
    assert _sha(data) == FIXED[source], f'Changed earned fixture: {source}'
    retained = json.loads(gzip.decompress(data))
    snapshot = (retained['commands'][index]['after'] if source == JOURNAL else
                retained['state']['campaign'] if name == 'capital-loss' else retained[selector])
    state = State.from_json(snapshot)
    assert state.to_json() == snapshot, f'Earned state changed while decoding {source}: {selector}'
    return state, dict(source=source, sha256=FIXED[source], selector=selector, preparation=preparation)


def _scenes(state):
    scenes = ['ShardScene']
    if state.battle:
        scenes.append('BattleScene')
        if state.battle.outcome:
            scenes.append('ResultScene')
    elif state.choice:
        scenes.append('ChoiceScene')
    elif state.campaign and state.campaign.phase != 'playing':
        scenes.append('CampaignScene')
    elif state.status != 'playing':
        scenes.append('ResultScene')
    return scenes


def _press(player, budget, *keys):
    for key in keys:
        player.press(key)
        budget.checkpoint()


def _manual_files(directory):
    return {path.name: path.read_bytes() for path in directory.iterdir()
            if path.name in {f'save_{slot}{suffix}.json' for slot in (1, 2, 3) for suffix in ('', '.backup')}}


def _load(player, slot, budget):
    assert isinstance(player.game.scene, TitleScene)
    if slot == 1:
        _press(player, budget, 'f9')
    else:
        _press(player, budget, 'f6')
        assert isinstance(player.game.scene, SaveScene) and player.game.scene.root is None
        assert any(entry.slot == slot for entry in player.game.scene.visible_entries)
        _press(player, budget, str(slot))


def _prepare(directory, output, backend, budget):
    cases = []
    for index, name in enumerate(CASES):
        saves = directory / name / 'saves'
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=backend == 'pyglet')
        try:
            if name in ('campaign', 'battle'):
                game.push(TitleScene(7))
                _press(player, budget, 'l')
                expected = State.new_campaign(7)
                if name == 'battle':
                    _press(player, budget, 'x')
                    expected.explore()
                assert player.state.to_json() == expected.to_json()
                origin = dict(preparation='Current fresh title input: New campaign' +
                              (' then Explore.' if name == 'battle' else '.'), source=None)
            else:
                state, origin = _earned(name)
                game.push(ShardScene(state))
            before = player.state.to_json()
            slot = 1 if index % 2 == 0 else 2
            if slot == 1:
                _press(player, budget, 'f5')
            else:
                _press(player, budget, 'f6')
                player.button('Save slots')
                _press(player, budget, '2', 'escape')
            assert player.state.to_json() == before
            saved = CampaignSaves(game.save_manager).load(slot)
            assert saved is not None and saved.to_json() == before
            payload = (saves / f'save_{slot}.json').read_bytes()
            (output / f'{name}-saved.json').write_bytes(payload)
            cases.append(dict(name=name, before=before, slot=slot, origin=origin,
                              save_sha256=_sha(payload), preparation_inputs=player.events))
        finally:
            game.close()
        budget.checkpoint()
    (output / 'prepared.json').write_text(json.dumps(cases, indent=2) + '\n')
    return cases


def _continue(name, player, expected, budget):
    """One declared continuation; only the oracle copy calls model commands directly."""
    if name in ('campaign', 'battle', 'skill', 'relic', 'result'):
        command, args = {
            'campaign': ('end_turn', ()), 'battle': ('battle.guard', (0,)),
            'skill': ('choose', ('tactician',)), 'relic': ('choose', ('take',)),
            'result': ('resolve_battle', ()),
        }[name]
        target = expected.battle if command.startswith('battle.') else expected
        getattr(target, command.removeprefix('battle.'))(*args)
        player.order(command, *args)
        description = dict(command=command, args=args)
    elif name in ('departure', 'recovery'):
        # These are real survivors and relics in both fixed checkpoints.
        selection = dict(troop_ids=(4, 5), relic_ids=('moonstone', 'iron_crown'))
        if name == 'departure':
            expected.advance('rootward', **selection)
            player.order('advance', 'rootward', **selection)
        else:
            expected.recover(**selection)
            player.choose_retinue(selection)
            _press(player, budget, 'return')
        description = dict(command='advance' if name == 'departure' else 'recover',
                           destination='rootward', **selection)
    else:
        # Endings have no further world order. Starting a new game must leave
        # the ending save intact, then loading it must restore that same ending.
        _press(player, budget, 'return')
        assert isinstance(player.game.scene, TitleScene)
        title = player.game.scene
        new = State.new(title.seed, title.hero_class, theme=title.world_theme, difficulty=title.difficulty)
        _press(player, budget, 'return')
        assert player.state.to_json() == new.to_json() != expected.to_json()
        description = dict(command='Return to title; New shard; reload saved ending')
    budget.checkpoint()
    return description


def _resume(directory, output, backend, budget):
    started, cpu_started = time.monotonic(), time.process_time()
    hashes = _fingerprints()
    prepared = json.loads((output / 'prepared.json').read_text())
    assert [case['name'] for case in prepared] == list(CASES)
    results = []
    for case in prepared:
        name, slot, before = case['name'], case['slot'], case['before']
        saves = directory / name / 'saves'
        manual = _manual_files(saves)
        assert _sha(manual[f'save_{slot}.json']) == case['save_sha256']
        expected = State.from_json(before)  # Detached oracle; never supplied to the fresh Game.
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            game.push(TitleScene(999, hero_class='Wizard', theme='ruins'))
            assert not any(isinstance(scene, ShardScene) for scene in game.scenes)
            _load(player, slot, budget)
            assert player.state.to_json() == before
            loaded_scenes = [type(scene).__name__ for scene in game.scenes]
            assert loaded_scenes == _scenes(expected)
            assert _manual_files(saves) == manual, 'Title loading rewrote a manual save'
            player.capture(f'{name}-restarted', settle=False)
            assert player.state.to_json() == before
            continuation = _continue(name, player, expected, budget)
            ending = name in ('completed', 'capital-loss')
            if ending:
                # The UI is now in a different campaign. Its normal quickload/
                # browser shortcut must still reach the manually saved ending.
                if slot == 1:
                    _press(player, budget, 'f9')
                else:
                    _press(player, budget, 'f6', str(slot))
            assert player.state.to_json() == expected.to_json(), f'{name}: continuation differs from the model'
            assert [type(scene).__name__ for scene in game.scenes] == _scenes(expected)
            assert _manual_files(saves) == manual, 'Continuing play changed the manual checkpoint'
            results.append(dict(name=name, origin=case['origin'], before=json.loads(before),
                                after=json.loads(expected.to_json()), load_control='F9' if slot == 1 else 'F6 / 2',
                                loaded_scenes=loaded_scenes, exact_load=True, exact_continuation=True,
                                manual_bytes_unchanged=True, save_sha256=case['save_sha256'],
                                new_game_started=ending, continuation=continuation,
                                preparation_inputs=case['preparation_inputs'], inputs=player.events))
        finally:
            game.close()
        budget.checkpoint()
    assert _fingerprints() == hashes, 'Source changed during the fresh-process journey'
    report = dict(resume_pid=os.getpid(), cases=results, source_sha256=hashes, source_unchanged=True,
                  elapsed_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu_started)
    (output / 'resumed.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Restarted {len(results)} saved phases through title input in process {os.getpid()}.')


def verify(output, *, backend='mock', budget=None):
    """All writer Games close before one distinct child process loads and continues them."""
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    budget = CpuBudget(25) if budget is None else budget
    started, cpu_started = time.monotonic(), time.process_time()
    hashes = _fingerprints()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    with TemporaryDirectory(prefix='shardbound-phase-restarts-') as temporary:
        directory = Path(temporary)
        _prepare(directory, output, backend, budget)
        command = [sys.executable, str(Path(__file__).resolve()), '--resume', str(directory),
                   '--output', str(output), '--backend', backend, '--cpu-percent', str(budget.percent)]
        # Parent waits without a live Game. The child gets files, never live State
        # or Scene objects; it imports the shipped modules in a new interpreter.
        with (output / 'resume.log').open('w') as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    resumed = json.loads((output / 'resumed.json').read_text())
    assert resumed['resume_pid'] != os.getpid()
    assert _fingerprints() == hashes == resumed['source_sha256']
    report = dict(scope=__doc__, source_revision=revision, backend=backend,
                  source_sha256=hashes, fixed_sha256=FIXED, source_unchanged=True,
                  writer_pid=os.getpid(), resume_pid=resumed['resume_pid'], fresh_process=True,
                  writer_games_closed=len(CASES), resumed_games_closed=len(CASES),
                  cpu_percent_requested=budget.percent, native_fps=30 if backend == 'pyglet' else None,
                  elapsed_seconds=time.monotonic() - started,
                  writer_cpu_seconds=time.process_time() - cpu_started,
                  resume_cpu_seconds=resumed['cpu_seconds'], cases=resumed['cases'])
    report['cpu_seconds'] = report['writer_cpu_seconds'] + report['resume_cpu_seconds']
    report['input_activations'] = sum(len(case['inputs']) + len(case['preparation_inputs']) for case in report['cases'])
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Phase restart proof passed ({backend}): {len(CASES)} phases; {output}')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-phase-restarts'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='mock')
    parser.add_argument('--cpu-percent', type=float, default=25)
    parser.add_argument('--resume', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        budget = CpuBudget(args.cpu_percent)
    except ValueError as error:
        parser.error(str(error))
    if args.resume is not None:
        _resume(args.resume, args.output, args.backend, budget)
    else:
        verify(args.output, backend=args.backend, budget=budget)


if __name__ == '__main__':
    main()
