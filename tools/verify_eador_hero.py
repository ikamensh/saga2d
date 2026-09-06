"""Verify readable equipment and optional Tower infusion through actual player controls."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d import Button, Label
from eador.app import create_game
from eador.content import RELICS
from eador.model import State
from eador.persistence import AUTO_SLOTS
from eador.preferences import reading_scale
from eador.scene import HeroScene, ShardScene, TitleScene
from tools.eador_campaign import finish_battle, play_campaign
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout

ROOT = Path(__file__).resolve().parents[1]


def prepared_heroes():
    """Earn collections and both disciplines using paid ordinary campaigns; retain victories and defeat."""
    old = ROOT / 'tests/eador/fixtures/v11_relic_collection.json'
    cases = [('legacy-v11', State.from_json(old.read_text()).to_json()),
             ('new-wizard', State.new(7, 'Wizard').to_json())]
    for hero, theme in (('Commander', 'frontier'), ('Commander', 'elderwild'), ('Commander', 'ruins'),
                        ('Warrior', 'frontier'), ('Scout', 'frontier'), ('Wizard', 'frontier')):
        state = State.new(0, hero, theme=theme)
        route = [state.hero.pos] + [p for p in sorted(state.provinces)
                                  if p not in (state.hero.pos, (2, 0))] + [(2, 0)]
        result = play_campaign(state, route)
        assert len(result.hero.skill_ranks) == 2
        cases.append((f'{hero.lower()}-{theme}-{result.status}', result.to_json()))
    assert {relic for _, data in cases for relic in State.from_json(data).inventory} == set(RELICS)
    return cases


def hero_pages(player, *, capture_prefix=None):
    """All inventory items appear once in order, with complete text clear of the controls."""
    scene = player.game.scene
    assert isinstance(scene, HeroScene) and scene.page == 0
    seen, metrics = [], []
    while True:
        seen.extend(scene.visible_relics)
        metrics.append(dict(page=scene.page + 1, pages=scene.pages, relics=scene.visible_relics,
                            labels=check_reading_layout(scene)))
        if capture_prefix:
            player.capture(f'{capture_prefix}-page-{scene.page + 1}')
        if scene.page + 1 == scene.pages:
            break
        if reading_scale(player.game) == 125:
            player.button('Next')
        else:
            player.press('right')
    assert seen == list(player.root.state.inventory)
    return metrics


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    paths = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'),
             ROOT / 'tools/verify_eador_hero.py', ROOT / 'tools/eador_ui.py',
             ROOT / 'tools/eador_campaign.py', ROOT / 'tools/verify_eador_guidance.py',
             ROOT / 'tests/eador/fixtures/v11_relic_collection.json']
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    native, metrics, outcomes = backend == 'pyglet', [], []
    with TemporaryDirectory(prefix='eador-hero-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=native, output=output)
        try:
            game.set_window_size((1280, 720))
            game.push(TitleScene(7, hero_class='Wizard'))
            player.press('return')
            player.state.build('mage_tower')
            player.state.explore()
            finish_battle(player.state)
            before = player.state.to_json()
            quote = player.state.infusion_preview()
            assert quote.blocked_reason is None and 0 < quote.mana < 8
            expected = State.from_json(before)
            expected.infuse()
            # Both input paths start from this identical earned, paid checkpoint.
            for method in ('keyboard', 'mouse'):
                game.clear_and_push(ShardScene(State.from_json(before)))
                player.press('h')
                for key in ('t', 'right', 'escape'):
                    player.press(key)
                if method == 'keyboard':
                    assert not (Path(directory) / 'settings.json').exists()
                for key in ('t', 'right', 'return'):
                    player.press(key)
                check_reading_layout(game.scene)
                player.capture(f'infusion-{method}-quoted-125')
                player.press('i') if method == 'keyboard' else player.button('Infuse mana')
                assert player.state.to_json() == expected.to_json()
                check_reading_layout(game.scene)
                player.capture(f'infusion-{method}-spent-125')
                files = {path.name: path.read_bytes() for path in saves.iterdir()}
                disabled = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Infuse mana')
                assert disabled is not None and not disabled.enabled
                x, y, w, h = disabled.bounds
                player.press('i')
                player.click(x + w / 2, y + h / 2)
                assert player.state.to_json() == expected.to_json()
                assert files == {path.name: path.read_bytes() for path in saves.iterdir()}
                player.press('escape')
                player.reload(expected.to_json())
                outcomes.append(dict(input=method, mana_gained=quote.mana, crystals_spent=quote.crystals,
                                     actions_spent=quote.actions, turn=expected.turn))

            for name, snapshot in prepared_heroes():
                for size in ((1280, 720), (1280, 800), (1920, 1080)):
                    game.set_window_size(size)
                    for percent in (100, 125):
                        state = State.from_json(snapshot)
                        root = ShardScene(state)
                        game.clear_and_push(root)
                        game.push(HeroScene(root))
                        player.press('t')
                        player.press('left' if percent == 100 else 'right')
                        player.button('Apply')
                        prefix = f'{name}-{percent}' if size == (1280, 720) else None
                        for record in hero_pages(player, capture_prefix=prefix):
                            record.update(case=name, percent=percent, window=game.window_size)
                            if native:
                                record['framebuffer'] = game.backend.capture_frame().size
                            metrics.append(record)
                        anchor = game.scene.visible_relics
                        for key in ('t', 'left' if percent == 125 else 'right', 'return'):
                            player.press(key)
                        assert game.scene.visible_relics[:1] == anchor[:1]
                        check_reading_layout(game.scene)
                        for key in ('t', 'right' if percent == 125 else 'left', 'escape'):
                            player.press(key)
                        assert game.scene.visible_relics[:1] == anchor[:1]
                        assert state.to_json() == snapshot

            # The real write failure must remain visible at the larger size.
            state = State.from_json(before)
            game.clear_and_push(ShardScene(state))
            player.press('h')
            for key in ('t', 'right', 'return'):
                player.press(key)
            for slot in AUTO_SLOTS:
                (saves / f'save_{slot}.json').write_bytes(b'damaged autosave')
            player.press('u')
            assert state.hero.relic is None
            assert any('All autosave slots are damaged' in label.text
                       for label in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
            assert all((saves / f'save_{slot}.json').read_bytes() == b'damaged autosave' for slot in AUTO_SLOTS)
            check_reading_layout(game.scene)
            player.capture('equipment-autosave-error-125')
        finally:
            game._teardown()

        restarted = create_game(backend=backend, visible=False, save_dir=saves)
        try:
            assert reading_scale(restarted) == 125
            replay = PlayerInput(restarted, native=native, output=output)
            restarted.push(ShardScene(State.from_json(expected.to_json())))
            replay.press('h')
            check_reading_layout(restarted.scene)
            replay.capture('hero-restarted-125')
            assert replay.state.to_json() == expected.to_json()
            events = len(player.events) + len(replay.events)
        finally:
            restarted._teardown()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  backend=backend, source_sha256=hashes, source_unchanged=True, input_events=events,
                  exact_reloads=player.reloads, infusion=outcomes, matrix=metrics)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Hero reading and infusion passed ({backend}): {len(metrics)} pages, {events} inputs; {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-hero'))
    parser.add_argument('--backend', choices=('pyglet', 'mock'), default='pyglet')
    args = parser.parse_args()
    verify(args.output, backend=args.backend)
