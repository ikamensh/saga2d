"""Codex journeys use the same input and visible content as players."""

from saga2d import Button, Game
from eador.model import State, UNITS
from eador.scene import ShardScene


def press(game, key, **modifiers):
    game.backend.inject_key(key, **modifiers)
    game.backend.inject_key(key, type="key_release", **modifiers)
    game.tick(1 / 60)


def rendered_text(game):
    return " ".join(record["text"] for record in game.backend.texts)


def click_button(game, label):
    control = game.scene.ui.find(lambda child: isinstance(child, Button) and child.text == label)
    assert control is not None and control.enabled
    x, y, width, height = control.bounds
    game.backend.inject_click(round(x + width / 2), round(y + height / 2))
    game.backend.inject_release(round(x + width / 2), round(y + height / 2))
    game.tick(1 / 60)


def test_keyboard_browses_categories_and_pages_then_returns_without_changing_state(tmp_path):
    """Browsing can reach entries beyond page one without spending, saving, or ending a turn."""
    from eador.codex import CodexScene

    game = Game("Codex test", backend="mock", save_dir=tmp_path)
    try:
        root = ShardScene(State.new(7))
        game.push(root)
        before = root.state.to_json()
        game.push(CodexScene(root))
        game.tick(1 / 60)
        assert UNITS["swordsman"].name in rendered_text(game)
        press(game, "right")
        assert UNITS["goblin"].name in rendered_text(game)
        press(game, "end")
        assert UNITS["guard"].name in rendered_text(game)
        press(game, "tab")
        assert "Arcane Bolt" in rendered_text(game)
        press(game, "tab", shift=True)
        assert UNITS["militia"].name in rendered_text(game)
        press(game, "6")
        assert "Wayfarer Boots" in rendered_text(game)
        press(game, "right")
        assert "Merchant Seal" in rendered_text(game)
        press(game, "escape")
        assert game.scene is root
        assert root.state.to_json() == before
        assert list(tmp_path.iterdir()) == []
    finally:
        game._teardown()


def test_mouse_tabs_and_paging_show_every_reference_category_without_mutating_the_campaign(tmp_path):
    """Every tab and paging/close control is reachable through visible mouse bounds."""
    from eador.codex import CodexScene

    game = Game("Codex mouse test", backend="mock", save_dir=tmp_path)
    try:
        root = ShardScene(State.new(7))
        game.push(root)
        before = root.state.to_json()
        game.push(CodexScene(root))
        game.tick(1 / 60)
        for category, expected in (("Abilities", "Arcane Bolt"), ("Buildings", "Barracks"),
                                   ("Skills", "Quartermaster"), ("Sites", "Buried Shrine"),
                                   ("Relics", "Wayfarer Boots"), ("Troops", "Militia")):
            click_button(game, category)
            assert expected in rendered_text(game)
        click_button(game, "Next")
        assert "Goblin" in rendered_text(game)
        click_button(game, "Previous")
        assert "Militia" in rendered_text(game)
        click_button(game, "Close codex")
        assert game.scene is root and root.state.to_json() == before
        assert list(tmp_path.iterdir()) == []
    finally:
        game._teardown()


def test_reference_prices_include_current_hero_recruitment_discounts(tmp_path):
    """The displayed purchase price matches the campaign's actual discounted quote."""
    from eador.codex import CodexScene

    game = Game("Codex price test", backend="mock", save_dir=tmp_path)
    try:
        state = State.new(7)
        state.hero.level = 3
        state.hero.skill_ranks = {"quartermaster": 2}
        state.inventory = ["merchant_seal"]
        state.equip("merchant_seal")
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        game.tick(1 / 60)
        assert f"Recruit for {state.recruit_cost('swordsman')} gold now (base {UNITS['swordsman'].cost})" in rendered_text(game)
        assert "Requires Barracks" in rendered_text(game)
        assert state.to_json() == before
    finally:
        game._teardown()


def test_spell_reference_uses_current_skills_and_equipped_relic_without_starting_a_battle(tmp_path):
    """Inspection quotes the same mana and effect values as the next real battle."""
    from eador.battle import Battle
    from eador.codex import CodexScene

    game = Game("Codex spell test", backend="mock", save_dir=tmp_path)
    try:
        state = State.new(7, "Wizard")
        state.hero.level = 3
        state.hero.skill_ranks = {"restoration": 2}
        state.inventory = ["moonstone"]
        state.equip("moonstone")
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        press(game, "2")
        battle = Battle.create(state.hero, ["brigand"], "plains", state.spells)
        assert f"{battle.spell_cost('heal')} mana · {battle.spell_power['heal']} healing · Learned" in rendered_text(game)
        assert state.to_json() == before and state.battle is None
    finally:
        game._teardown()


def test_ability_pages_explain_pin_timing_and_current_readiness_without_mutation(tmp_path):
    """A spent Archer's cooldown is inspectable, alongside the command's limits and counters."""
    from eador.codex import CodexScene
    state = State.new(7)
    state.explore()
    archer = next(u for u in state.battle.units if u.team == 'player' and u.can_pin)
    state.battle.move(archer.id, (-1, 0))
    state.battle.pin(archer.id, state.battle.pin_targets(archer.id)[0].id)
    game = Game('Pin reference', backend='mock', save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        press(game, '2')
        text = rendered_text(game)
        assert 'Pin' in text and '1 capable / 0 ready' in text
        assert 'skip the following turn' in text and 'Cannot stack or extend' in text
        assert 'minimum 1' in text and 'forecast' in text
        press(game, 'end')
        assert 'Brace' in rendered_text(game) and 'Watch Bell' in rendered_text(game)
        press(game, 'escape')
        assert state.to_json() == before
    finally:
        game._teardown()


def test_relic_catalog_uses_recorded_sources_in_an_older_saved_shard(tmp_path):
    """New definitions cannot claim a reward that was never recorded in a loaded realm."""
    from pathlib import Path
    from eador.codex import CodexScene
    state = State.from_json((Path(__file__).parent / 'fixtures/v6_archer_battle.json').read_text())
    game = Game('Saved relic sources', backend='mock', save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        press(game, '6')
        assert 'Wolf Den' in rendered_text(game)  # Boots still belong to this saved Den.
        press(game, 'end')
        assert 'Watch Bell' in rendered_text(game) and 'Storm Quiver' in rendered_text(game)
        assert 'No recorded source on this shard' in rendered_text(game)
        assert state.to_json() == before
    finally:
        game._teardown()


def test_current_relic_sources_and_equipped_pin_capability_are_visible_with_mouse_navigation(tmp_path):
    """The Quiver adds the hero to the ready count, and the Camp remains the Boots source."""
    from eador.codex import CodexScene
    state = State.new(7)
    state.inventory = ['storm_quiver']
    state.equip('storm_quiver')
    game = Game('Relic ability reference', backend='mock', save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        game.tick(1 / 60)
        click_button(game, 'Abilities')
        assert '2 capable / 2 ready' in rendered_text(game)
        click_button(game, 'Relics')
        assert 'Explorer’s Camp' in rendered_text(game)
        click_button(game, 'Next')
        click_button(game, 'Next')
        assert 'Border Watch' in rendered_text(game) and 'Wolf Den' in rendered_text(game)
        click_button(game, 'Sites')
        click_button(game, 'Next')
        click_button(game, 'Next')
        assert 'Explorer’s Camp' in rendered_text(game) and 'Wayfarer Boots' in rendered_text(game)
        click_button(game, 'Close codex')
        assert state.to_json() == before
    finally:
        game._teardown()
