"""Integration journeys through the same scenes and input used by players."""

import json

import pytest

from eador.app import create_game


def press(game, key):
    from tools.eador_ui import PlayerInput
    PlayerInput(game).press(key)


def click(game, x, y):
    from tools.eador_ui import PlayerInput
    PlayerInput(game).click(x, y)


def button(game, label):
    """Click visible public UI bounds, not an implementation callback."""
    from saga2d import Button

    control = game.scene.ui.find(lambda child: isinstance(child, Button) and child.text == label)
    assert control is not None, label
    x, y, w, h = control.bounds
    click(game, x + w / 2, y + h / 2)


def test_new_game_opens_a_seeded_shard_from_title(tmp_path):
    """The executable's title flow must reach the playable strategy scene."""
    from eador.scene import ShardScene, TitleScene

    game = create_game("Shardbound test", backend="mock", save_dir=tmp_path)
    try:
        game.push(TitleScene(seed=7))
        game.tick(1 / 60)
        game.backend.inject_key("return")
        game.tick(1 / 60)
        assert isinstance(game.scene, ShardScene)
        assert len(game.scene.state.provinces) == 19
        assert game.scene.state.status == "playing"
    finally:
        game._teardown()


def test_invade_retreat_returns_to_campaign_without_losing_scene_state(tmp_path):
    """Retreat resolves the real battle and restores the underlying map scene."""
    from eador.model import State
    from eador.scene import BattleScene, ShardScene

    game = create_game("Shardbound test", backend="mock", save_dir=tmp_path)
    try:
        scene = ShardScene(State.new(7))
        game.push(scene)
        game.tick(1 / 60)
        destination = next(p for p in scene.grid.neighbors(scene.state.hero.pos)
                           if scene.state.provinces[p].owner == "neutral")
        click(game, *scene.grid.center(destination))
        button(game, "Invade province")
        assert isinstance(game.scene, BattleScene)
        button(game, "Retreat")
        assert game.scene is scene
        assert scene.state.battle is None
        assert scene.state.provinces[destination].owner == "neutral"
        assert len(game.scenes) == 1
    finally:
        game._teardown()


def test_battle_save_restores_playable_tactics_and_returns_wounds_to_map(tmp_path):
    """Save through F5, change play, restore through F9 and finish the encounter."""
    from eador.model import State
    from eador.scene import BattleScene, ShardScene

    game = create_game("Shardbound test", backend="mock", save_dir=tmp_path)
    try:
        state = State.new(7, "Wizard")
        root = ShardScene(state)
        game.push(root)
        game.tick(1 / 60)
        click(game, *root.grid.center((-1, 0)))
        press(game, "return")
        assert isinstance(game.scene, BattleScene)
        scene = game.scene
        enemy = next(u for u in state.battle.units if u.team == "enemy")
        # Let the advancing defender enter spell range before choosing a target.
        press(game, "e")
        press(game, "1")
        click(game, *scene.grid.center(enemy.pos))
        assert state.battle.unit(0).acted
        assert state.battle.mana < state.hero.mana
        press(game, "f5")
        saved = state.to_json()
        press(game, "e")
        press(game, "f9")
        assert isinstance(game.scene, BattleScene)
        restored = game.scene.root.state
        assert restored.to_json() == saved
        assert len(game.scenes) == 2
        for _ in range(30):
            if restored.battle.outcome:
                break
            press(game, "a")
        assert restored.battle.outcome == "player"
        press(game, "e")
        assert isinstance(game.scene, ShardScene)
        assert restored.battle is None
        assert restored.hero.pos == (-1, 0)
        assert restored.provinces[(-1, 0)].owner == "player"
        assert restored.hero.xp > 0 or restored.hero.level > 1
    finally:
        game._teardown()


def test_stronghold_unlocks_recruitment_through_keyboard_and_mouse(tmp_path):
    """The displayed building and troop catalogues drive real economy rules."""
    from eador.model import BUILDINGS, UNITS, State
    from eador.scene import CatalogScene, ShardScene

    game = create_game("Shardbound test", backend="mock", save_dir=tmp_path)
    try:
        state = State.new(7)
        root = ShardScene(state)
        game.push(root)
        game.tick(1 / 60)
        before = state.gold
        press(game, "b")
        assert isinstance(game.scene, CatalogScene)
        press(game, "1")
        assert "barracks" in state.buildings
        assert state.gold == before - BUILDINGS["barracks"].cost
        press(game, "escape")
        button(game, "Recruit troops")
        press(game, "2")
        assert state.hero.army[-1].kind == "swordsman"
        assert state.gold == before - BUILDINGS["barracks"].cost - UNITS["swordsman"].cost
        press(game, "escape")
        assert game.scene is root
        assert game.running
    finally:
        game._teardown()


def test_adventure_choices_restore_then_equip_a_relic_through_input(tmp_path):
    """Decisions are playable saved state; equipment changes the next battle."""
    from eador.persistence import AUTO_SLOTS, CampaignSaves
    from eador.scene import BattleScene, ChoiceScene, HeroScene, ShardScene, TitleScene

    game = create_game("Shardbound test", backend="mock", save_dir=tmp_path)
    try:
        game.push(TitleScene(seed=7))
        press(game, "return")
        press(game, "b")
        press(game, "1")
        press(game, "escape")
        press(game, "r")
        press(game, "2")
        press(game, "escape")
        press(game, "x")
        assert isinstance(game.scene, BattleScene)
        state = game.scene.root.state
        for _ in range(80):
            if state.battle.outcome:
                break
            press(game, "a")
        assert state.battle.outcome == "player"
        press(game, "e")
        assert isinstance(game.scene, ChoiceScene)
        saved_choice = state.to_json()
        press(game, "f5")
        press(game, "1")
        press(game, "f9")
        assert isinstance(game.scene, ChoiceScene)
        state = game.scene.root.state
        assert state.to_json() == saved_choice
        press(game, "escape")
        assert isinstance(game.scene, ChoiceScene)
        while isinstance(game.scene, ChoiceScene):
            press(game, "1")
        assert isinstance(game.scene, ShardScene)
        assert state.inventory
        press(game, "h")
        assert isinstance(game.scene, HeroScene)
        button(game, "Equip")
        assert state.hero.relic == state.inventory[0]
        snapshots = CampaignSaves(game.save_manager)
        assert state.to_json() in [snapshots.load(slot).to_json() for slot in AUTO_SLOTS]
        press(game, "escape")
        press(game, "e")
        root = game.scene
        click(game, *root.grid.center((-1, 0)))
        press(game, "return")
        assert isinstance(game.scene, BattleScene)
        assert "heal" in game.scene.root.state.battle.spells
        for _ in range(80):
            if state.battle.outcome:
                break
            press(game, "a")
        assert state.battle.outcome == "player"
        press(game, "e")
        assert isinstance(game.scene, ChoiceScene)
        assert state.choice.kind == "skill"
        discipline = state.choice.options[1].id
        press(game, "2")
        assert isinstance(game.scene, ShardScene)
        assert state.hero.skill_ranks == {discipline: 1}
    finally:
        game._teardown()


@pytest.mark.parametrize("campaign", [None, "1" + "0" * 5000, "[" * 2000 + "0" + "]" * 2000],
                         ids=["broken-envelope", "oversized-number", "deep-json"])
def test_damaged_quickload_keeps_live_game_and_browser_recovers_backup(tmp_path, campaign):
    from eador.model import State
    from eador.persistence import CampaignSaves
    from eador.scene import SaveScene, ShardScene

    game = create_game("Shardbound test", backend="mock", save_dir=tmp_path)
    try:
        root = ShardScene(State.new(7))
        game.push(root)
        press(game, "f5")
        first = root.state.to_json()
        press(game, "e")
        press(game, "f5")
        press(game, "e")
        live = root.state.to_json()
        damaged = tmp_path / "save_1.json"
        if campaign is None:
            damaged.write_text("interrupted write")
        else:
            payload = json.loads(damaged.read_text())
            payload["state"]["campaign"] = campaign
            damaged.write_text(json.dumps(payload))
        damaged_bytes = damaged.read_bytes()
        press(game, "f9")
        assert game.scene is root
        assert root.state.to_json() == live
        assert root.message
        press(game, "f6")
        assert isinstance(game.scene, SaveScene)
        assert game.scene.entries[0].error
        assert game.scene.entries[0].backup_available
        button(game, "Backup")
        assert isinstance(game.scene, ShardScene)
        assert game.scene.state.to_json() == first
        button(game, "Save")
        press(game, "2")
        assert CampaignSaves(game.save_manager).load(2).to_json() == first
        assert damaged.read_bytes() == damaged_bytes
    finally:
        game._teardown()


def test_unavailable_autosaves_report_failure_and_allow_manual_play(tmp_path):
    from eador.persistence import AUTO_SLOTS, CampaignSaves
    from eador.scene import ShardScene, TitleScene

    for slot in AUTO_SLOTS:
        (tmp_path / f"save_{slot}.json").write_text("damaged autosave")
    game = create_game("Shardbound test", backend="mock", save_dir=tmp_path)
    try:
        game.push(TitleScene(seed=7))
        press(game, "return")
        assert isinstance(game.scene, ShardScene)
        assert "Autosave failed" in game.scene.message
        button(game, "Save")
        press(game, "2")
        assert CampaignSaves(game.save_manager).load(2).seed == 7
        assert all((tmp_path / f"save_{slot}.json").read_text() == "damaged autosave" for slot in AUTO_SLOTS)
    finally:
        game._teardown()


def test_save_and_title_keeps_progress_until_a_usable_slot_is_written(tmp_path):
    from eador.model import State
    from eador.persistence import CampaignSaves
    from eador.scene import SaveScene, ShardScene, TitleScene

    game = create_game("Shardbound test", backend="mock", save_dir=tmp_path)
    try:
        root = ShardScene(State.new(7))
        game.push(root)
        press(game, "e")
        live = root.state.to_json()
        (tmp_path / "save_1.json").write_text("damaged current")
        press(game, "f1")
        button(game, "Save & title")
        assert isinstance(game.scene, SaveScene)
        press(game, "1")
        assert isinstance(game.scene, SaveScene)
        assert game.scene.message
        assert root.state.to_json() == live
        press(game, "2")
        assert isinstance(game.scene, TitleScene)
        assert CampaignSaves(game.save_manager).load(2).to_json() == live
    finally:
        game._teardown()


def test_repeated_equipment_hotkeys_preserve_autosave_history(tmp_path):
    from eador.model import State
    from eador.persistence import AUTO_SLOTS, CampaignSaves
    from eador.scene import ShardScene

    state = State.new(7)
    state.inventory = ["moonstone"]
    state.equip("moonstone")
    game = create_game("Shardbound test", backend="mock", save_dir=tmp_path)
    try:
        game.push(ShardScene(state))
        for _ in range(3):
            press(game, "e")
        saves = CampaignSaves(game.save_manager)
        snapshots = [saves.load(slot).to_json() for slot in AUTO_SLOTS]
        press(game, "h")
        for _ in range(3):
            press(game, "1")
        assert [saves.load(slot).to_json() for slot in AUTO_SLOTS] == snapshots
        press(game, "u")
        snapshots = [saves.load(slot).to_json() for slot in AUTO_SLOTS]
        press(game, "u")
        assert [saves.load(slot).to_json() for slot in AUTO_SLOTS] == snapshots
    finally:
        game._teardown()


def test_keyboard_only_tactics_move_cast_attack_reload_and_retreat(tmp_path):
    """Every aimed action uses the same legal-command path as a mouse click."""
    from eador.model import State
    from eador.scene import BattleScene, ShardScene

    game = create_game("Shardbound test", backend="mock", save_dir=tmp_path)
    try:
        root = ShardScene(State.new(7, "Wizard"))
        game.push(root)
        for _ in range(6):
            press(game, "tab")
            if root.selected == (-1, 0):
                break
        press(game, "return")
        assert isinstance(game.scene, BattleScene)
        b = root.state.battle
        hero = b.unit(0)
        before = root.state.to_json()
        press(game, "1")
        press(game, "up")
        press(game, "return")  # Empty spell targets must not move a unit.
        assert root.state.to_json() == before
        assert game.scene.message
        press(game, "escape")
        press(game, "return")
        assert hero.moved and hero.pos == (-3, 0)
        press(game, "e")
        mana = b.mana
        press(game, "1")
        press(game, "f")
        press(game, "return")
        assert b.mana < mana and hero.acted
        archer = next(u for u in b.units if u.team == "player" and u.kind == "archer")
        for _ in range(6):
            press(game, "tab")
            if game.scene.selected == archer.id:
                break
        health = sum(u.hp for u in b.units if u.team == "enemy")
        press(game, "f5")
        saved = root.state.to_json()
        press(game, "f")
        press(game, "return")
        assert archer.acted
        assert sum(u.hp for u in b.units if u.team == "enemy") < health
        press(game, "f9")
        assert isinstance(game.scene, BattleScene)
        assert game.scene.root.state.to_json() == saved
        press(game, "t")
        assert isinstance(game.scene, ShardScene)
        assert game.scene.state.battle is None
        assert game.scene.state.provinces[(-1, 0)].owner == "neutral"
    finally:
        game._teardown()


def test_codex_is_reachable_from_campaign_guide_and_battle_without_advancing_play(tmp_path):
    from eador.codex import CodexScene
    from eador.model import State
    from eador.scene import BattleScene, HelpScene, ShardScene

    game = create_game("Shardbound test", backend="mock", save_dir=tmp_path)
    try:
        root = ShardScene(State.new(7, "Wizard"))
        game.push(root)
        before = root.state.to_json()
        press(game, "c")
        assert isinstance(game.scene, CodexScene)
        press(game, "4")
        press(game, "right")
        press(game, "escape")
        assert game.scene is root
        assert root.state.to_json() == before
        press(game, "f1")
        button(game, "Codex")
        assert isinstance(game.scene, CodexScene)
        press(game, "escape")
        assert isinstance(game.scene, HelpScene)
        press(game, "escape")
        click(game, *root.grid.center((-1, 0)))
        press(game, "return")
        assert isinstance(game.scene, BattleScene)
        battle = game.scene
        before = root.state.to_json()
        press(game, "c")
        press(game, "2")
        assert isinstance(game.scene, CodexScene)
        press(game, "e")
        assert root.state.to_json() == before
        press(game, "escape")
        assert game.scene is battle
    finally:
        game._teardown()


def test_complete_campaign_and_saved_victory_through_player_input(tmp_path):
    """Explore, invest, conquer, replay and restore a finished shard through UI."""
    from eador.model import BUILDINGS, UNITS
    from eador.scene import BattleScene, ChoiceScene, ResultScene, ShardScene, TitleScene

    game = create_game("Shardbound test", backend="mock", save_dir=tmp_path)
    try:
        game.push(TitleScene(seed=7))
        game.tick(1 / 60)
        press(game, "return")
        root, state = game.scene, game.scene.state

        def battle():
            assert isinstance(game.scene, BattleScene)
            for _ in range(80):
                if state.battle.outcome:
                    break
                press(game, "a")
            assert isinstance(game.scene, ResultScene)
            assert state.battle.outcome == "player"
            press(game, "e")
            while isinstance(game.scene, ChoiceScene):
                press(game, "1")

        def prepare():
            if "temple" not in state.buildings and state.gold >= BUILDINGS["temple"].cost:
                press(game, "b")
                press(game, "3")
                press(game, "escape")
            press(game, "r")
            while state.gold >= UNITS["swordsman"].cost and len(state.hero.army) < state.hero.max_army:
                press(game, "2")
            press(game, "escape")

        def rest():
            press(game, "e")
            if state.battle:
                battle()

        press(game, "b")
        press(game, "1")
        press(game, "escape")
        press(game, "r")
        press(game, "2")
        press(game, "escape")
        for destination in ((-2, 0), (-1, 0), (0, 0), (0, 1), (1, 0)):
            if state.hero.pos != destination:
                click(game, *root.grid.center(destination))
                press(game, "return")
                battle()
                rest()
                prepare()
            press(game, "x")
            if state.provinces[destination].site_kind == 'relief_column':
                from eador.encounter_scene import EncounterScene
                assert isinstance(game.scene, EncounterScene)
                before = state.to_json()
                press(game, 'escape')  # The same reward remains at the ordinary Grove next door.
                assert state.to_json() == before
                continue
            battle()
            rest()
            prepare()
        for _ in range(12):
            if max([state.hero.max_hp - state.hero.hp] + [u.max_hp - u.hp for u in state.hero.army]) <= 6:
                break
            rest()
        click(game, *root.grid.center((2, 0)))
        press(game, "return")
        battle()
        assert state.status == "victory"
        assert isinstance(game.scene, ResultScene)
        assert not game.scene.is_battle
        assert state.battle is None
        press(game, "f5")
        won = state.to_json()
        button(game, "New shard")
        assert isinstance(game.scene, TitleScene)
        press(game, "f9")
        assert isinstance(game.scene, ResultScene)
        assert game.scene.root.state.to_json() == won
        assert len(game.scenes) == 2
    finally:
        game._teardown()


def test_exhausted_actions_show_complete_guidance_above_the_disabled_travel_control(tmp_path):
    """Two real failed invasions retain readable next-step advice without spending again."""
    from saga2d import Button, Label
    from eador.model import State
    from eador.scene import ShardScene

    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        scene = ShardScene(State.new(7))
        game.push(scene)
        for _ in range(2):
            click(game, *scene.grid.center((-1, 0)))
            press(game, 'return')
            button(game, 'Retreat')
        assert scene.state.actions_left == 0
        hint = scene.ui.find(lambda c: isinstance(c, Label) and 'End the turn' in c.text)
        assert hint is not None
        travel = scene.ui.find(lambda c: isinstance(c, Button) and c.text == 'Invade province')
        x, y, width, height = hint.bounds
        assert x >= scene.edge and x + width <= game.width
        assert y + height <= travel.bounds[1] and not travel.enabled
        before = scene.state.to_json()
        press(game, 'return'); press(game, 'x')
        assert scene.state.to_json() == before
        press(game, 'e')
        assert scene.state.actions_left > 0
        assert scene.ui.find(lambda c: isinstance(c, Label) and 'End the turn' in c.text) is None
    finally:
        game._teardown()
