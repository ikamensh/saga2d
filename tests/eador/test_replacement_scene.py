"""Paid role changes are reviewed through the same controls a player uses."""
import json
from pathlib import Path

from saga2d import Label
from eador.app import create_game
from eador.model import State
from eador.scene import CatalogScene, ShardScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def earned_army():
    """The retained paid campaign has a full, experienced army at a supplied camp."""
    path = Path(__file__).parents[2] / 'docs/evidence/crystal-service-comparison.examples.json'
    return State.from_json(json.dumps(json.loads(path.read_text())['late_full_roster']['state']))


def review(player, outgoing_id, kind):
    player.press('r')
    player.press('m')
    player.press(str(next(i for i, troop in enumerate(player.state.hero.army, 1) if troop.id == outgoing_id)))
    assert isinstance(player.game.scene, CatalogScene)
    while kind not in player.game.scene.visible_items:
        player.press('right')
    player.press(str(player.game.scene.visible_items.index(kind) + 1))


def test_retiring_a_veteran_requires_an_exact_visible_review_then_saves_once(tmp_path):
    """Selections and Cancel spend nothing; explicit Replace buys the quoted fresh identity in the same slot."""
    state = earned_army()
    before = state.to_json()
    quote = state.replacement_preview(1, 'warden')
    expected = State.from_json(before)
    expected.replace_troop(1, 'warden')
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        review(player, 1, 'warden')
        assert state.to_json() == before
        labels = [item.text for item in game.scene.ui.find_all(lambda item: isinstance(item, Label))]
        assert any(f'Rank {quote.outgoing.level}' in text and f'{quote.outgoing.xp} XP' in text for text in labels)
        assert any(f'{quote.gold} gold' in text and '1 campaign action' in text for text in labels)
        assert any('No refund' in text and 'no experience transfers' in text for text in labels)
        check_reading_layout(game.scene)
        player.press('escape')
        assert isinstance(game.scene, CatalogScene) and state.to_json() == before
        player.press(str(game.scene.visible_items.index('warden') + 1))
        player.button('Replace veteran')
        assert state.to_json() == expected.to_json()
        after = state.to_json()
        player.press('1')
        assert state.to_json() == after
        player.button('Return to shard')
        assert isinstance(game.scene, ShardScene)
        player.reload(after)
    finally:
        game._teardown()


def test_reading_overlays_and_failed_checkpoint_preserve_review_and_completed_purchase(tmp_path):
    """Larger text never spends; damaged autosaves leave an applied decision and manual recovery visible."""
    from eador.persistence import AUTO_SLOTS
    from eador.preferences import reading_scale
    from eador.replacement_scene import ReplacementScene

    state = earned_army()
    before = state.to_json()
    saves = tmp_path / 'saves'
    saves.mkdir()
    for slot in AUTO_SLOTS:
        (saves / f'save_{slot}.json').write_bytes(b'damaged autosave')
    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        review(player, 1, 'warden')
        for key in ('t', 'right', 'escape'):
            player.press(key)
        assert reading_scale(game) == 100
        for key in ('t', 'right', 'return', 'c', 'escape'):
            player.press(key)
        assert state.to_json() == before and reading_scale(game) == 125
        assert game.scene.quote.outgoing.id == 1 and game.scene.quote.incoming.kind == 'warden'
        check_reading_layout(game.scene)
        player.press('return')
        assert isinstance(game.scene, ReplacementScene) and game.scene.applied
        after = state.to_json()
        assert any('All autosave slots are damaged' in item.text
                   for item in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
        check_reading_layout(game.scene)
        player.press('f6')
        player.press('1')
        assert game.scene.saves.load(1).to_json() == after
        player.press('escape')
        assert game.scene.applied
        player.press('f9')
        assert isinstance(game.scene, ShardScene) and player.state.to_json() == after
        assert all((saves / f'save_{slot}.json').read_bytes() == b'damaged autosave' for slot in AUTO_SLOTS)
    finally:
        game._teardown()


def test_unavailable_role_still_has_a_complete_quote_without_spending_or_rotating_saves(tmp_path):
    """The catalog permits reviewing a missing prerequisite, but neither mouse nor Enter can buy it."""
    from saga2d import Button
    state = State.new(7)
    before = state.to_json()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        review(player, state.hero.army[0].id, 'adept')
        quote = game.scene.quote
        assert quote.blocked_reason == 'Build Mage Tower first.'
        button = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Replace veteran')
        assert button is not None and not button.enabled
        player.press('return')
        x, y, width, height = button.bounds
        player.click(x + width / 2, y + height / 2)
        assert state.to_json() == before
        assert not list((tmp_path / 'saves').glob('*.json'))
        check_reading_layout(game.scene)
    finally:
        game._teardown()


def test_complete_replacement_reading_and_saved_manual_rescue(tmp_path):
    """Every offered role reflows; file errors preserve all roster rows and the paid Warden rescues a real flank."""
    from tools.verify_eador_replacement import verify
    verify(tmp_path, backend='mock')


def test_replacement_without_a_special_ability_uses_only_visible_reading_rows(tmp_path):
    """An ordinary Swordsman has no ability paragraph; its review must still have valid text bounds."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(State.new(7)))
        player = PlayerInput(game)
        player.press('b')
        player.press('1')
        player.press('escape')
        before = player.state.to_json()
        review(player, 1, 'swordsman')
        check_reading_layout(game.scene)
        assert player.state.to_json() == before
    finally:
        game.close()
