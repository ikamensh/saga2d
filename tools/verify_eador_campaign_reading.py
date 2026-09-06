"""Inspect earned and legacy campaign transitions at both reading sizes and all supported windows."""
from __future__ import annotations

import argparse
from functools import cache
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d import Button, Label
from eador.app import create_game
from eador.campaign_scene import CampaignScene
from eador.content import RELICS, SKILLS
from eador.difficulty import DIFFICULTIES
from eador.model import State, UNITS
from eador.preferences import reading_scale
from eador.scene import ShardScene, TitleScene
from tools.eador_campaign import play_campaign
from tools.eador_linked_campaign import lose_shard, play_stage, travel_selection
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


@cache
def prepared_transitions():
    """Win or lose actual linked worlds; legacy snapshots retain their own saved difficulty rules."""
    cases = []
    for mode in DIFFICULTIES:
        victory = play_stage(State.new_campaign(7, difficulty=mode))
        assert victory.campaign.phase == 'departure'
        cases.append((mode + '-departure', victory.to_json()))
        lost = lose_shard(State.new_campaign(7, difficulty=mode))
        assert lost.campaign.phase == 'recovery'
        cases.append((mode + '-recovery', lost.to_json()))
    rich = State.new_campaign(0)
    route = [rich.hero.pos] + [p for p in sorted(rich.provinces) if p not in (rich.hero.pos, (2, 0))] + [(2, 0)]
    rich = play_campaign(rich, route)
    assert rich.campaign.phase == 'departure' and len(rich.inventory) > 6
    cases.append(('eight-earned-relics', rich.to_json()))
    for middle, finale in (('rootward', 'gate'), ('foundries', 'throne')):
        state = State.from_json(dict(cases)['standard-departure'])
        state.advance(middle, **travel_selection(state))
        if middle == 'foundries':
            lose_shard(state)
            cases.append(('foundries-recovery', state.to_json()))
            state.recover(**travel_selection(state))
        state = play_stage(state)
        assert state.campaign.phase == 'departure'
        cases.append((middle + '-departure', state.to_json()))
        state.advance(finale, **travel_selection(state))
        state = play_stage(state)
        assert state.campaign.phase == 'completed'
        cases.append((finale + '-completed', state.to_json()))
    declined = State.from_json(dict(cases)['standard-recovery'])
    declined.abandon_campaign()
    cases.append(('recovery-declined', declined.to_json()))
    lost = State.from_json(dict(cases)['foundries-recovery'])
    lost.recover(); lose_shard(lost)
    assert lost.campaign.phase == 'lost' and lost.campaign.recovery_used
    cases.append(('second-capital-loss', lost.to_json()))
    old_cases = json.loads((ROOT / 'tests/eador/fixtures/v12_challenge1_ui_cases.json').read_text())['cases']
    for case in old_cases:
        if case['name'] in ('advance', 'recover'):
            state = State.from_json(json.dumps(case['before']))
            assert state.rules_id == 'challenge-1'
            cases.append(('saved-challenge1-' + case['name'], state.to_json()))
    return tuple(cases)


def check_transition(scene):
    """Complete saved facts and the current focused row remain visible without changing model state."""
    assert isinstance(scene, CampaignScene)
    count = check_reading_layout(scene)
    state = scene.root.state
    texts = [item.text for item in scene.ui.find_all(lambda item: isinstance(item, Label))]
    assert any(state.rules.title.upper() in text for text in texts)
    if scene.message:
        assert scene.message in texts
    if scene.step == 'offers' and scene.prose_pages == 1:
        for offer in state.campaign.offers:
            assert offer.title in texts and offer.description in texts
        assert any(f'first operation in {state.rules.arrival_delay} turns' in text for text in texts)
    elif scene.step == 'retinue':
        gold, crystals = state.expedition_funding(recovery=scene.phase == 'recovery')
        assert any(f'{gold} gold · {crystals} crystals' in text for text in texts)
        assert any('Hero skills survive; traveling health and mana are restored.' in text for text in texts)
        controls = scene.ui.find_all(lambda item: isinstance(item, Button))
        for column in (0, 1):
            items = scene.items(column)
            ids = [item.id for item in items] if column == 0 else list(items)
            if ids:
                assert ids[scene.cursors[column]] in scene.visible_items[column]
            for ident in scene.visible_items[column]:
                item = items[ids.index(ident)]
                name = f'{UNITS[item.kind].name} · Lv{item.level} · {item.hp}/{item.max_hp} HP' if column == 0 else RELICS[item].name
                assert any(control.text in ('Keep · ' + name, 'Leave · ' + name) for control in controls)
        if scene.items(scene.column):
            item = scene.items(scene.column)[scene.cursors[scene.column]]
            if scene.column == 1:
                assert RELICS[item].description in texts
    elif scene.step == 'ending' and scene.prose_pages == 1:
        for record in state.campaign.completed:
            assert any(f'{record.turns} turns · Hero level {record.hero_level}' in text and
                       f'{record.casualties} troops lost · {len(record.garrison)} left as garrison' in text for text in texts)
        for ident, rank in state.hero.skill_ranks.items():
            assert any(f'{SKILLS[ident].name} {rank}' in text for text in texts)
    # Button text is a single line: verify the full scaled label, not just its hit rectangle.
    for button in scene.ui.find_all(lambda item: isinstance(item, Button)):
        if button.text.startswith(('Keep · ', 'Leave · ')):
            width, height = scene.game.backend.measure_text(button.text, round(13 * reading_scale(scene.game) / 100), 'Verdana')
            assert width + 20 <= button.bounds[2] and height + 20 <= button.bounds[3]
    return count


def verify_reflow(player):
    """Keep actual selected relics and the first row; Space follows visible focus after font/size reflow."""
    game = player.game
    state = State.from_json(dict(prepared_transitions())['eight-earned-relics'])
    before = state.to_json()
    game.clear_and_push(ShardScene(state)); game.tick(1 / 60)
    for key in ('t', 'left', 'return', '1', 'right'):
        player.press(key)
    scene = game.scene
    first, last = scene.visible_items[1][0], scene.visible_items[1][-1]
    for _ in range(len(scene.visible_items[1]) - 1):
        player.press('down')
    player.press('space')
    assert last in scene.relic_ids
    for key in ('t', 'right', 'return'):
        player.press(key)
    assert scene.visible_items[1][0] == first and scene.relic_ids == {last}
    assert last not in scene.visible_items[1], 'The fixture must exercise actual page shrinkage.'
    assert state.inventory[scene.cursors[1]] == first
    player.press('space')
    assert scene.relic_ids == {first, last}
    check_transition(scene); player.capture('focus-reflow-125')
    player.button('Next')
    anchor = scene.visible_items[1][0]
    for key in ('t', 'left', 'escape'):
        player.press(key)
    for size in ((1920, 1080), (1280, 720)):
        game.set_window_size(size); game.tick(1 / 60)
        assert scene.visible_items[1][0] == anchor and scene.relic_ids == {first, last}
        check_transition(scene)
    assert state.to_json() == before


def verify_long_error(output, *, backend='pyglet'):
    """Use a valid long nested path, then read every diagnostic page and return to the same retinue."""
    with TemporaryDirectory(prefix='campaign-reading-review-') as directory:
        saves = Path(directory)
        for index in range(7):
            saves /= 'ordinary-directory-name-' + str(index) + '-' + 'a' * 70
        saves.mkdir(parents=True)
        occupied = saves / 'save_1.json'; occupied.mkdir()
        state = play_stage(State.new_campaign())
        before = state.to_json()
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            game.push(ShardScene(state)); game.tick(1 / 60)
            for key in ('1', 'space', 't', 'right', 'return', 'f5'):
                player.press(key)
            scene = game.scene
            selected = scene.troop_ids.copy(), scene.relic_ids.copy()
            anchors = [page[0] for page in scene.visible_items if page]
            for key in ('space', 'down', 'up', 'q'):
                player.press(key)
            assert (scene.troop_ids, scene.relic_ids) == selected and state.to_json() == before
            parts = []
            while True:
                check_reading_layout(scene)
                labels = scene.ui.find_all(lambda item: isinstance(item, Label))
                part = next(label.text for label in labels if label.style.text_color == (228, 130, 112, 255))
                parts.append(part)
                player.capture(f'long-path-error-page-{len(parts)}')
                control = scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Next')
                if not control.enabled:
                    break
                player.press('pagedown')
            assert ''.join(parts) == scene.message
            for key in ('t', 'left', 'escape', 'f6', 'escape', 'return'):
                player.press(key)
            assert (scene.troop_ids, scene.relic_ids) == selected
            assert [page[0] for page in scene.visible_items if page] == anchors
            check_reading_layout(scene); player.capture('long-path-return-to-retinue-125')
            player.button('Read error'); player.press('escape')
            assert state.to_json() == before
            occupied.rmdir()
            player.press('f5'); player.press('return')
            assert isinstance(game.scene, ShardScene) and state.campaign.stage == 2
            player.press('f9'); assert player.state.to_json() == before
            return dict(path_characters=len(str(saves)), diagnostic_characters=sum(map(len, parts)),
                        pages=len(parts), input_activations=len(player.events), exact_save_reloads=1)
        finally:
            game._teardown()


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    native, matrix = backend == 'pyglet', []
    verified_reloads = 0
    with TemporaryDirectory(prefix='shardbound-campaign-reading-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=native, output=output)
        try:
            for size in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(size)
                for percent in (100, 125):
                    for name, snapshot in prepared_transitions():
                        state = State.from_json(snapshot)
                        game.clear_and_push(ShardScene(state)); game.tick(1 / 60)
                        for key in ('t', 'left' if percent == 100 else 'right', 'return'):
                            player.press(key)
                        page_texts = []
                        page_count = game.scene.prose_pages if game.scene.step != 'retinue' else 1
                        for page in range(page_count):
                            matrix.append(dict(case=name, step=game.scene.step, rules_id=state.rules_id, percent=percent,
                                               window=game.window_size, page=page, labels=check_transition(game.scene)))
                            page_texts.extend(item.text for item in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
                            if size == (1280, 720) and (percent == 125 or name == 'standard-departure'):
                                player.capture(f'{name}-{percent}-page-{page + 1}')
                            if page + 1 < page_count:
                                player.press('pagedown')
                        if game.scene.step == 'offers':
                            assert all(offer.description in page_texts for offer in state.campaign.offers)
                            assert any(f'first operation in {state.rules.arrival_delay} turns' in text for text in page_texts)
                        elif game.scene.step == 'ending':
                            for record in state.campaign.completed:
                                assert any(f'{record.turns} turns · Hero level {record.hero_level}' in text for text in page_texts)
                        while game.scene.step != 'retinue' and game.scene.prose_page:
                            player.press('pageup')
                        if game.scene.step == 'offers':
                            # Both offers remain independently reviewable without consuming the departure.
                            for key in ('2', 'escape', '1'):
                                player.press(key)
                                check_transition(game.scene)
                        if game.scene.step == 'retinue':
                            for column in (0, 1):
                                player.press('left' if column == 0 else 'right')
                                items = list(game.scene.items(column))
                                for index, item in enumerate(items):
                                    scene = game.scene
                                    assert scene.cursors[column] == index
                                    matrix.append(dict(case=name, step='retinue', percent=percent, window=game.window_size,
                                                       column=column, focused=index, visible=list(scene.visible_items[column]),
                                                       labels=check_transition(scene)))
                                    if name == 'eight-earned-relics' and column == 1 and index == len(items) - 1 and size == (1280, 720):
                                        player.capture(f'earned-last-relic-{percent}')
                                    if index + 1 < len(items):
                                        player.press('down')
                        assert state.to_json() == snapshot and not saves.exists()
            # Exercise saved callbacks, complete filesystem errors and post-error return in the native backend too.
            for name in ('standard-departure', 'foundries-recovery', 'throne-completed'):
                snapshot = dict(prepared_transitions())[name]
                state = State.from_json(snapshot)
                game.clear_and_push(ShardScene(state)); game.tick(1 / 60)
                saves.mkdir(exist_ok=True)
                occupied = saves / 'save_1.json'; occupied.mkdir()
                player.press('f5')
                page_texts = []
                page_count = game.scene.prose_pages if game.scene.step != 'retinue' else 1
                for page in range(page_count):
                    check_transition(game.scene)
                    page_texts.extend(item.text for item in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
                    player.capture(f'{name}-save-error-125-page-{page + 1}')
                    if page + 1 < page_count:
                        player.press('pagedown')
                if game.scene.step == 'offers':
                    assert all(offer.description in page_texts for offer in state.campaign.offers)
                    assert any(f'first operation in {state.rules.arrival_delay} turns' in text for text in page_texts)
                while game.scene.step != 'retinue' and game.scene.prose_page:
                    player.press('pageup')
                before = state.to_json()
                for key in ('t', 'left', 'escape', 'f6', 'escape'):
                    player.press(key)
                assert state.to_json() == before
                occupied.rmdir()
                if game.scene.step == 'offers':
                    player.press('1')
                if game.scene.step == 'retinue':
                    player.choose_retinue(travel_selection(state))
                    player.press('f5'); player.press('return')
                    assert isinstance(game.scene, ShardScene) and state.campaign.phase == 'playing'
                    player.press('f9')
                    assert player.state.to_json() == snapshot
                    verified_reloads += 1
                else:
                    player.reload(snapshot)
                    player.press('return'); assert isinstance(game.scene, TitleScene)
                # Keep each directory-error attempt isolated without deleting saved evidence.
                for path in saves.iterdir():
                    path.unlink()
            verify_reflow(player)
            events, reloads = len(player.events), player.reloads + verified_reloads
        finally:
            game._teardown()
    long_error = verify_long_error(output, backend=backend)
    report = dict(backend=backend, layouts=len(matrix), input_activations=events + long_error['input_activations'],
                  exact_save_reloads=reloads + long_error['exact_save_reloads'], long_error=long_error, matrix=matrix)
    (output / 'matrix.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'{backend} campaign reading passed: {len(matrix)} layouts / {report['input_activations']} inputs / {report['exact_save_reloads']} exact reloads; {output}')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-campaign-reading'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    args = parser.parse_args()
    verify(args.output, backend=args.backend)
