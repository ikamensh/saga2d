"""Follow each earned discipline through a linked campaign, including optional real recovery.

The ordinary paid itinerary and tactical autoplay are unchanged. Only the
preferred advancement choice varies. This proves continuation and a bounded
competent-policy result, not optimal manual play or balanced alternatives.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('SAGA2D_SILENT', '1')

from eador.content import SKILLS
from eador.model import State
from saga2d.testing.cpu_budget import CpuBudget
from tools.eador_sources import framework_sources, source_name
from tools.eador_campaign import CampaignMetrics
from tools.eador_linked_campaign import lose_shard, play_stage, travel_selection

ROOT = Path(__file__).resolve().parents[1]


def digest(snapshot):
    return hashlib.sha256(snapshot.encode()).hexdigest()


class DisciplinePath:
    """Choose the preferred offered discipline; delegate every other public command."""

    def __init__(self, state, skill, decisions, capture=None):
        self.state, self.skill, self.decisions = state, skill, decisions
        self.capture = capture

    def __getattr__(self, name):
        return getattr(self.state, name)

    def choose(self, option_id):
        choice = self.state.choice
        if choice.kind == 'skill' and self.skill in {option.id for option in choice.options}:
            option_id = self.skill
        if choice.kind == 'skill' and self.hero.level == 3 and self.capture is not None:
            self.capture('rank-two-choice')
        before = self.state.to_json()
        self.state.choose(option_id)
        after = self.state.to_json()
        assert State.from_json(after).to_json() == after
        self.decisions.append(dict(kind=choice.kind, offered=[option.id for option in choice.options],
                                   selected=option_id, before=before, after=after))


def journey(skill, *, seed=7, recovery=False, player=None, budget=None):
    """Earn ranks through ordinary paid battles, then preserve them through actual transitions."""
    decisions, checkpoints = [], []
    metrics = CampaignMetrics()
    if player is None:
        initial = State.new_campaign(seed, SKILLS[skill].hero_class)
    else:
        from eador.scene import TitleScene
        player.game.clear_and_push(TitleScene(seed, hero_class=SKILLS[skill].hero_class))
        player.press('l')
        initial = player.state
    capture = player.capture if player is not None else None
    state = DisciplinePath(initial, skill, decisions, capture)

    def reload_state(snapshot):
        restored = State.from_json(snapshot) if player is None else player.reload(snapshot)
        assert restored.to_json() == snapshot
        return DisciplinePath(restored, skill, decisions, capture)

    def checkpoint(phase):
        nonlocal state
        snapshot = state.to_json()
        state = reload_state(snapshot)
        checkpoints.append(dict(phase=phase, sha256=digest(snapshot), state=snapshot))
        if player is not None:
            player.capture(phase)

    for stage, destination in ((1, 'foundries'), (2, 'throne'), (3, None)):
        if stage == 2 and recovery:
            ranks = dict(state.hero.skill_ranks)
            lose_shard(state, budget=budget)
            assert state.campaign.phase == 'recovery'
            assert state.hero.skill_ranks == ranks
            checkpoint('capital-lost')
            if player is None:
                state.recover(**travel_selection(state))
            else:
                player.choose_retinue(travel_selection(state))
                player.press('return')
            assert state.campaign.recovery_used and state.hero.skill_ranks == ranks
            checkpoint('recovered')
        state = play_stage(state, metrics=metrics, reload_state=reload_state, budget=budget)
        checkpoint(f'stage-{stage}-{state.campaign.phase}')
        if state.status != 'victory':
            break
        assert state.hero.skill_ranks[skill] == min(stage + 1, SKILLS[skill].max_rank)
        if destination is not None:
            ranks = dict(state.hero.skill_ranks)
            state.advance(destination, **travel_selection(state))
            assert state.hero.skill_ranks == ranks
            checkpoint(f'stage-{stage + 1}-arrived')
    snapshot = state.to_json()
    return dict(skill=skill, hero=SKILLS[skill].hero_class, seed=seed, recovery=recovery,
                status=state.status, phase=state.campaign.phase, metrics=asdict(metrics),
                records=[asdict(record) for record in state.campaign.completed],
                ranks=dict(state.hero.skill_ranks), decisions=decisions, checkpoints=checkpoints,
                final_sha256=digest(snapshot), final_state=snapshot,
                input_events=player.events if player is not None else [],
                exact_ui_reloads=player.reloads if player is not None else 0)


def verify(output, *, skills=tuple(SKILLS), backend='model', recovery=False, seed=7, budget=None):
    output.mkdir(parents=True, exist_ok=True)
    paths = [*ROOT.glob('eador/**/*.py'), *framework_sources(),
             ROOT / 'tools/audit_eador_disciplines.py', ROOT / 'tools/eador_campaign.py',
             ROOT / 'tools/eador_linked_campaign.py', ROOT / 'tools/eador_ui.py']
    hashes = {source_name(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    results = []
    for skill in skills:
        if backend == 'model':
            result = journey(skill, seed=seed, recovery=recovery, budget=budget)
        else:
            from eador.app import create_game
            from tools.eador_ui import PlayerInput
            with TemporaryDirectory(prefix='shardbound-disciplines-') as directory:
                game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
                try:
                    player = PlayerInput(game, native=backend == 'pyglet', output=output / skill)
                    result = journey(skill, seed=seed, recovery=recovery, player=player, budget=budget)
                finally:
                    game._teardown()
        results.append(result)
        print(f"{skill}: {result['phase']}, ranks {result['ranks']}, "
              f"{len(result['input_events'])} inputs / {result['exact_ui_reloads']} reloads", flush=True)
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == checksum for path, checksum in hashes.items())
    report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, source_unchanged=True, backend=backend,
                  cpu_percent=budget.percent if budget else None,
                  policy='Paid standard seed itinerary, Foundries then Throne, tactical autoplay, preferred discipline until capped.',
                  recovery=recovery, results=results)
    with gzip.open(output / 'journeys.json.gz', 'wt') as stream:
        json.dump(report, stream, indent=2)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend', choices=('model', 'mock', 'pyglet'), default='model')
    parser.add_argument('--skills', nargs='+', choices=SKILLS, default=list(SKILLS))
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--recovery', action='store_true')
    parser.add_argument('--cpu-percent', type=float, default=25,
                        help='CPU allowance as a percent of one core (default 25; 100 for explicit stress)')
    args = parser.parse_args()
    try:
        budget = CpuBudget(args.cpu_percent)
    except ValueError as error:
        parser.error(str(error))
    verify(args.output, skills=args.skills, backend=args.backend, recovery=args.recovery, seed=args.seed, budget=budget)
