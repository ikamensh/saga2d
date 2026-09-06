"""Read earned campaign objectives and locate them through the public interface."""
from __future__ import annotations

import argparse
from functools import cache
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d import Button, Label
from eador.app import create_game
from eador.campaign import CONTRACTS, FOUNDRIES
from eador.campaign_scene import CampaignPlanScene, campaign_targets
from eador.difficulty import DIFFICULTIES
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import ShardScene, TitleScene
from tools.eador_campaign import finish_battle, march_to, rest
from tools.eador_linked_campaign import lose_shard, play_stage, secure_frontier, travel_selection
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


@cache
def prepared_plans():
    """Earn both contracts/finales and spend recovery using ordinary purchases, battles and travel."""
    cases = [(f'opening-{mode}', State.new_campaign(7, difficulty=mode).to_json()) for mode in DIFFICULTIES]
    first_victory = play_stage(State.new_campaign(7))
    assert first_victory.campaign.phase == 'departure'
    for middle, finale in (('rootward', 'gate'), ('foundries', 'throne')):
        state = State.from_json(first_victory.to_json())
        state.advance(middle, **travel_selection(state))
        cases.append((middle + '-arrival', state.to_json()))
        if middle == 'rootward':
            secure_frontier(state)
            watch = next(province for province in state.provinces.values() if province.site_kind == 'border_watch')
            march_to(state, watch.pos)
            if not state.actions_left:
                rest(state)
            state.explore()
            finish_battle(state)
            assert campaign_targets(state)[0][2]
            cases.append(('rootward-watch-cleared', state.to_json()))
        else:
            state.build('barracks'); state.recruit('swordsman')
            state.explore(); finish_battle(state)
            for index, position in enumerate(FOUNDRIES):
                march_to(state, position); rest(state)
                assert sum(complete for _, _, complete in campaign_targets(state)) == index + 1
                cases.append((f'foundries-held-{index + 1}', state.to_json()))
        state = play_stage(state)
        assert state.campaign.phase == 'departure'
        state.advance(finale, **travel_selection(state))
        cases.append((finale + '-arrival', state.to_json()))
    recovered = State.from_json(dict(cases)['foundries-arrival'])
    lose_shard(recovered)
    assert recovered.campaign.phase == 'recovery'
    recovered.recover(**travel_selection(recovered))
    assert recovered.campaign.recovery_used
    cases.append(('foundries-recovery-spent', recovered.to_json()))
    for _, snapshot in cases:
        state = State.from_json(snapshot)
        assert state.status == state.campaign.phase == 'playing' and not state.battle and not state.choice
    assert {State.from_json(snapshot).campaign.contract for _, snapshot in cases} == set(CONTRACTS)
    return tuple(cases)


def check_plan(scene):
    """Objective order, completion, live caps and recovery funding remain visible in the measured layout."""
    assert isinstance(scene, CampaignPlanScene)
    count = check_reading_layout(scene)
    state = scene.root.state
    labels = [item.text for item in scene.ui.find_all(lambda item: isinstance(item, Label))]
    assert state.campaign.objective in [' '.join(text.split()) for text in labels]
    assert any(state.rules.title.upper() in text and f'STAGE {state.campaign.stage}' in text for text in labels)
    targets = campaign_targets(state)
    controls = scene.ui.find_all(lambda item: isinstance(item, Button) and item.text == 'Locate')
    assert len(controls) == len(targets)
    for index, (_, name, complete) in enumerate(targets):
        text = f'{index + 1}. {name}'
        assert text in labels
        assert labels[labels.index(text) + 1] == ('Complete / held' if complete else 'Still required')
    if state.assault_blocked_reason:
        assert state.assault_blocked_reason in labels
    else:
        assert any('Duskspire is open to assault' in text for text in labels)
    assert any(f'hero {state.hero_level_cap}' in text and f'troops {state.troop_level_cap}' in text for text in labels)
    if state.campaign.recovery_used:
        assert any('Recovery spent' in text for text in labels)
        assert not any('One recovery remains' in text for text in labels)
    else:
        gold, crystals = state.expedition_funding(recovery=True)
        assert any(f'{gold} gold and {crystals} crystals' in text for text in labels)
    if state.campaign.stage == 3:
        assert any('Victory completes this three-shard campaign' in text for text in labels)
        assert not any('After a victory, carry' in text for text in labels)
    return count


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    metrics, native = [], backend == 'pyglet'
    with TemporaryDirectory(prefix='eador-campaign-plan-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=native, output=output)
        try:
            game.set_window_size((1280, 720))
            game.push(TitleScene(7))
            player.press('l')
            opening = player.state.to_json()
            player.press('j')
            for key in ('t', 'right', 'escape'):
                player.press(key)
            assert reading_scale(game) == 100 and not (Path(directory) / 'settings.json').exists()
            for key in ('t', 'right', 'return', 'h', 'escape'):
                player.press(key)
            check_plan(game.scene)
            assert player.state.to_json() == opening
            player.press('escape')
            player.reload(opening)
            for size in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(size)
                for percent in (100, 125):
                    for name, snapshot in prepared_plans():
                        state = State.from_json(snapshot)
                        game.clear_and_push(ShardScene(state))
                        for key in ('j', 't', 'left' if percent == 100 else 'right', 'return'):
                            player.press(key)
                        targets = campaign_targets(state)
                        metrics.append(dict(case=name, contract=state.campaign.contract, percent=percent,
                                            window=game.window_size, targets=targets, labels=check_plan(game.scene)))
                        if native:
                            metrics[-1]['framebuffer'] = game.backend.capture_frame().size
                        if size == (1280, 720) and (percent == 125 or name == 'foundries-held-1'):
                            player.capture(f'{name}-{percent}')
                        for index, (position, _, _) in enumerate(targets):
                            if percent == 100:
                                player.press(str(index + 1))
                            else:
                                button = game.scene.ui.find_all(lambda item: isinstance(item, Button) and item.text == 'Locate')[index]
                                x, y, width, height = button.bounds
                                player.click(x + width / 2, y + height / 2)
                            assert isinstance(game.scene, ShardScene) and game.scene.selected == position
                            assert state.to_json() == snapshot
                            player.press('j')
            inputs = len(player.events)
        finally:
            game._teardown()
        game = create_game(backend=backend, visible=False, save_dir=saves)
        try:
            game.push(ShardScene(State.from_json(opening)))
            player = PlayerInput(game, native=native, output=output)
            player.press('j')
            assert reading_scale(game) == 125
            check_plan(game.scene)
            player.capture('restarted-plan-125')
        finally:
            game._teardown()
    (output / 'matrix.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print(f'{backend} campaign plans passed: {len(metrics)} layouts / {inputs + len(player.events)} inputs; {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-campaign-plan-reading'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    args = parser.parse_args()
    verify(args.output, backend=args.backend)
