"""Linked challenges and retinues are reviewable, saved player decisions."""

from eador.app import create_game
from eador.scene import ShardScene, TitleScene
from eador.model import State
from tools.eador_linked_campaign import play_stage
import pytest


def press(game, name):
    game.backend.inject_key(name)
    game.backend.inject_key(name, type='key_release')
    game.tick(1 / 60)


def test_linked_title_and_saved_departure_preserve_the_selected_retinue(tmp_path):
    """Choose a real offered challenge, inspect carryover, then leave through a checkpointed action."""
    from eador.campaign_scene import CampaignScene
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(TitleScene())
        press(game, 'l')
        assert game.scene.state.campaign.stage == 1
        # Prepare a genuine finished shard through public play commands; enter as a restarted save.
        state = play_stage(game.scene.state)
        assert state.campaign.phase == 'departure'
        game.clear_and_push(ShardScene(State.from_json(state.to_json())))
        game.tick(1 / 60)
        assert isinstance(game.scene, CampaignScene)
        press(game, 'f5')
        before = game.scene.root.state.to_json()
        press(game, '2')
        assert game.scene.offer_id == 'foundries'
        assert game.scene.root.state.to_json() == before
        # Start with an explicit empty retinue, choose the first veteran and first relic.
        press(game, 'space')
        carried = game.scene.troop_ids.copy()
        assert len(carried) == 1
        press(game, 'right')
        press(game, 'space')
        relics = game.scene.relic_ids.copy()
        press(game, 'return')
        assert isinstance(game.scene, ShardScene)
        new = game.scene.state
        assert new.campaign.stage == 2 and new.campaign.contract == 'foundries'
        assert carried <= {troop.id for troop in new.hero.army}
        assert set(new.inventory) == relics and len(new.hero.army) == 3
        press(game, 'f9')
        assert isinstance(game.scene, CampaignScene) and game.scene.root.state.to_json() == before
    finally:
        game._teardown()


@pytest.mark.parametrize('middle,finale,recovery', [('rootward', 'gate', False), ('foundries', 'throne', True)])
def test_linked_campaign_can_be_completed_with_visible_input_and_exact_saved_transitions(tmp_path, middle, finale, recovery):
    """Replay the native verifier: real tactics, offered challenges, retinues, recovery and ending."""
    from tools.verify_eador_campaign import verify
    report = verify(tmp_path, backend='mock', middle=middle, finale=finale, recovery=recovery)
    assert len(report['records']) == 3 and report['exact_save_reloads'] >= 5


def test_failed_departure_checkpoint_preserves_the_offer_and_retinue_for_retry(tmp_path):
    """A real unavailable save directory cannot consume a reviewed campaign departure."""
    from eador.campaign_scene import CampaignScene
    save_dir = tmp_path / 'saves'
    game = create_game(backend='mock', save_dir=save_dir)
    try:
        game.push(ShardScene(play_stage(State.new_campaign())))
        game.tick(1 / 60)
        press(game, '1')
        press(game, 'space')
        before = game.scene.root.state.to_json()
        selected = game.scene.troop_ids.copy()
        # Reproduce a disk-path conflict without replacing the persistence implementation.
        save_dir.write_text('A file occupies the configured directory.')
        press(game, 'return')
        assert isinstance(game.scene, CampaignScene) and game.scene.root.state.to_json() == before
        assert game.scene.troop_ids == selected and 'Autosave failed' in game.scene.message
        save_dir.unlink()
        press(game, 'return')
        assert isinstance(game.scene, ShardScene) and game.scene.state.campaign.stage == 2
    finally:
        game._teardown()


def test_recovery_can_be_declined_and_its_ending_resumed(tmp_path):
    """Declining the one recovery reaches a saved ending with a working return-to-title action."""
    from eador.campaign_scene import CampaignScene
    from tools.verify_eador_campaign import lose_shard
    state = State.new_campaign()
    lose_shard(state)
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        game.tick(1 / 60)
        assert isinstance(game.scene, CampaignScene) and game.scene.phase == 'recovery'
        press(game, 'q')
        assert game.scene.phase == 'lost'
        press(game, 'f5')
        before = game.scene.root.state.to_json()
        press(game, 'f9')
        assert isinstance(game.scene, CampaignScene) and game.scene.root.state.to_json() == before
        press(game, 'return')
        assert isinstance(game.scene, TitleScene)
    finally:
        game._teardown()


def test_current_campaign_plan_locates_required_provinces_without_spending_actions(tmp_path):
    """The foundry contract is discoverable and locating either requirement leaves play untouched."""
    from eador.campaign_scene import CampaignPlanScene
    from eador.campaign import FOUNDRIES
    state = play_stage(State.new_campaign())
    state.advance('foundries')
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        for index, destination in enumerate(FOUNDRIES, 1):
            before = state.to_json()
            press(game, 'j')
            assert isinstance(game.scene, CampaignPlanScene)
            press(game, str(index))
            assert isinstance(game.scene, ShardScene) and game.scene.selected == destination
            assert state.to_json() == before
    finally:
        game._teardown()


def test_every_earned_relic_can_join_the_retinue_using_only_mouse_controls(tmp_path):
    """An expedition that earns more than one page of relics can carry its last treasure."""
    from saga2d import Button
    from tools.eador_campaign import play_campaign
    from eador.content import RELICS
    state = State.new_campaign(0)
    route = [state.hero.pos] + [p for p in sorted(state.provinces) if p not in (state.hero.pos, (2, 0))] + [(2, 0)]
    state = play_campaign(state, route)
    assert len(state.inventory) > 6
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        game.tick(1 / 60)

        def click(label):
            control = game.scene.ui.find(lambda c: isinstance(c, Button) and c.text == label)
            assert control is not None and control.enabled, label
            x, y, width, height = control.bounds
            game.backend.inject_click(round(x + width / 2), round(y + height / 2))
            game.backend.inject_release(round(x + width / 2), round(y + height / 2))
            game.tick(1 / 60)

        click('Choose challenge')
        click('Next')
        relic = state.inventory[-1]
        click('Leave · ' + RELICS[relic].name)
        click('Previous')
        click('Depart for the next shard')
        assert isinstance(game.scene, ShardScene) and state.inventory == [relic]
    finally:
        game._teardown()


@pytest.mark.parametrize('recovery', [False, True])
def test_damaged_autosaves_do_not_trap_a_transition_after_an_exact_manual_save(tmp_path, recovery):
    """The screen's suggested manual-save recovery actually permits the blocked transition."""
    from tools.verify_eador_checkpoint import verify
    verify(tmp_path, backend='mock', recovery=recovery)
