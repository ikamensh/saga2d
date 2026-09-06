"""Campaign reading preserves the selected province and the command it describes."""
from saga2d import Label
from eador.app import create_game
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import BattleScene, ShardScene
from eador.settings_scene import SettingsScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def test_reading_the_selected_province_preserves_and_executes_its_actual_order(tmp_path):
    """Apply/cancel and resize leave the selected province intact; Enter invades that province."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        root = ShardScene(State.new(7, 'Wizard'))
        game.push(root)
        player = PlayerInput(game)
        destination = (-1, 0)
        player.click(*root.grid.center(destination))
        before = root.state.to_json()
        player.press('f2')
        assert isinstance(game.scene, SettingsScene)
        player.press('right'); player.press('escape')
        assert root.selected == destination and reading_scale(game) == 100
        player.button('Text size'); player.press('right'); player.press('return')
        assert reading_scale(game) == 125 and root.selected == destination
        for window in ((1280, 720), (1920, 1080), (1280, 800)):
            game.set_window_size(window); game.tick(1 / 60)
            assert root.state.to_json() == before and root.selected == destination
            check_reading_layout(root)
            labels = '\n'.join(c.text for c in root.ui.walk() if isinstance(c, Label))
            assert root.state.provinces[destination].name in labels
            assert f'{root.state.gold} gold' in labels
            assert f'{root.state.actions_left} actions left' in labels
        player.press('return')
        assert isinstance(game.scene, BattleScene)
        assert root.state.battle_province == destination
    finally:
        game._teardown()


def test_a_real_long_save_error_remains_complete_without_spending_the_selected_order(tmp_path):
    """Read a failed save through Settings and pages; Return must not invoke the underlying invasion."""
    from eador.diagnostics import DiagnosticScene
    from tests.eador.test_diagnostics import long_save_directory, read_diagnostic

    saves = long_save_directory(tmp_path)
    occupied = saves / 'save_1.json'
    occupied.mkdir()
    game = create_game(backend='mock', save_dir=saves)
    try:
        root = ShardScene(State.new(7))
        game.push(root)
        player = PlayerInput(game)
        player.click(*root.grid.center((-1, 0)))
        before = root.state.to_json()
        player.press('f5')
        assert game.scene is root and root.state.to_json() == before
        check_reading_layout(root)
        player.press('d')
        assert isinstance(game.scene, DiagnosticScene)
        assert any(c.text == 'Complete campaign message' for c in game.scene.ui.walk() if isinstance(c, Label))
        message = read_diagnostic(player)
        assert str(occupied) in message and root.state.to_json() == before
        player.press('t'); player.press('right'); player.press('return')
        assert read_diagnostic(player) == message and reading_scale(game) == 125
        for key in ('return', 'return', 'space'):
            game.backend.inject_key(key)
        game.tick(1 / 60)
        assert game.scene is root and root.selected == (-1, 0) and root.state.to_json() == before
        player.button('Read message')
        assert read_diagnostic(player) == message and occupied.is_dir()
    finally:
        game._teardown()


def test_a_campaign_command_refreshes_its_applied_autosave_error_immediately(tmp_path):
    """End turn spends exactly once even when every autosave is damaged; the map explains that failure."""
    from eador.persistence import AUTO_SLOTS

    saves = tmp_path / 'saves'
    saves.mkdir()
    for slot in AUTO_SLOTS:
        (saves / f'save_{slot}.json').write_bytes(b'damaged')
    game = create_game(backend='mock', save_dir=saves)
    try:
        state = State.new(7)
        expected = State.from_json(state.to_json()); expected.end_turn()
        game.push(ShardScene(state))
        player = PlayerInput(game)
        player.press('e')
        assert state.to_json() == expected.to_json()
        assert any('All autosave slots are damaged' in c.text
                   for c in game.scene.ui.walk() if isinstance(c, Label))
        check_reading_layout(game.scene)
        assert state.to_json() == expected.to_json()
        assert all((saves / f'save_{slot}.json').read_bytes() == b'damaged' for slot in AUTO_SLOTS)
    finally:
        game._teardown()


def test_earned_and_historical_shards_keep_all_facts_and_map_cells_accessible(tmp_path):
    """Zero resources, full armies and old encirclement retain complete facts for every selected province."""
    from tools.verify_eador_shard_reading import prepared_shards, check_shard

    (tmp_path / 'settings.json').write_text('{"codex_text_scale": 125}')
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        player = PlayerInput(game)
        for name, snapshot in prepared_shards():
            game.clear_and_push(ShardScene(State.from_json(snapshot)))
            for pos in player.state.provinces:
                player.click(*player.root.grid.center(pos))
                assert player.root.selected == pos
                check_shard(player.root)
                assert player.state.to_json() == snapshot, name
    finally:
        game._teardown()


def earned_contract_arrivals():
    """Use paid historical departures and their public offers, without replaying their battles."""
    import gzip
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / 'docs/evidence/shardbound-army-plans-cd351a9/control.json.gz'
    with gzip.open(path, 'rt') as source:
        history = json.load(source)
    arrivals = [history['commands'][0]['before']]
    for entry in history['commands']:
        if entry['command'] == 'advance':
            departure = State.from_json(entry['before'])
            for offer in departure.campaign.offers:
                state = State.from_json(entry['before'])
                state.advance(offer.id, **entry['kwargs'])
                arrivals.append(state.to_json())
    return arrivals


def test_every_earned_contract_objective_stays_readable_on_the_map_after_selection_and_reload(tmp_path):
    """At 125%, the full contract remains above rival controls through selection, J-return and F5/F9."""
    from saga2d import Button
    from eador.campaign import CONTRACTS
    from eador.campaign_scene import CampaignPlanScene
    from eador.rival_scene import rival_order
    from tools.verify_eador_shard_reading import check_shard

    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        player = PlayerInput(game)
        seen = set()
        for snapshot in earned_contract_arrivals():
            state = State.from_json(snapshot)
            game.clear_and_push(ShardScene(state))
            for key in ('f2', 'right', 'return'):
                player.press(key)
            assert reading_scale(game) == 125
            seen.add(state.campaign.contract)

            def check_objective():
                root = player.root
                check_shard(root)
                labels = [item for item in root.ui.walk() if isinstance(item, Label) and item.visible]
                objective = next((item for item in labels if item.text == state.campaign.objective), None)
                assert objective is not None, 'The map must show the complete current contract'
                stage = next(item for item in labels if item.text == f'Stage {state.campaign.stage} of 3')
                rival = root.ui.find(lambda item: isinstance(item, Button) and item.text == 'Rival plan')
                warning = next(item for item in labels if item.text == rival_order(root.state))
                assert stage.bounds[1] + stage.bounds[3] <= objective.bounds[1]
                assert objective.bounds[1] + objective.bounds[3] <= rival.bounds[1]
                assert rival.bounds[1] + rival.bounds[3] <= warning.bounds[1]
                assert player.state.to_json() == snapshot

            for window in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(window)
                for destination in (state.hero.pos, (0, -1), (2, 0)):
                    player.click(*player.root.grid.center(destination))
                    assert player.root.selected == destination
                    check_objective()
                player.press('j')
                assert isinstance(game.scene, CampaignPlanScene)
                player.press('escape')
                assert isinstance(game.scene, ShardScene) and player.root.selected == (2, 0)
                check_objective()
                player.reload(snapshot)
                check_objective()
        assert seen == set(CONTRACTS)
    finally:
        game.close()
