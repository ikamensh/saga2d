"""Codex journeys use the same input and visible content as players."""

from saga2d import Button

from eador.app import create_game
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


def category_text(game, *, mouse=False):
    """Read a whole category through paging; font/content may move page breaks."""
    press(game, 'home')
    text = rendered_text(game)
    while game.scene.ui.find(lambda child: isinstance(child, Button) and child.text == 'Next').enabled:
        click_button(game, 'Next') if mouse else press(game, 'right')
        text += ' ' + rendered_text(game)
    return text


def test_keyboard_browses_categories_and_pages_then_returns_without_changing_state(tmp_path):
    """Browsing can reach entries beyond page one without spending, saving, or ending a turn."""
    from eador.codex import CodexScene

    game = create_game("Codex test", backend="mock", save_dir=tmp_path)
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
        assert list(UNITS.values())[-1].name in rendered_text(game)
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

    game = create_game("Codex mouse test", backend="mock", save_dir=tmp_path)
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

    game = create_game("Codex price test", backend="mock", save_dir=tmp_path)
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
        text = category_text(game)
        for kind in ('adept', 'skyrider'):
            assert f"{state.recruit_cost(kind)} gold + {state.recruit_crystal_cost(kind)} crystals" in text
        assert state.to_json() == before
    finally:
        game._teardown()


def test_spell_reference_uses_current_skills_and_equipped_relic_without_starting_a_battle(tmp_path):
    """Inspection quotes the same mana and effect values as the next real battle."""
    from eador.battle import Battle
    from eador.codex import CodexScene

    game = create_game("Codex spell test", backend="mock", save_dir=tmp_path)
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
    game = create_game('Pin reference', backend='mock', save_dir=tmp_path)
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
        while 'Pikemen and Watch Bell heroes' not in rendered_text(game):
            assert game.scene.page + 1 < game.scene.pages
            press(game, 'right')
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
    game = create_game('Saved relic sources', backend='mock', save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        press(game, '6')
        assert 'Wolf Den' in rendered_text(game)  # Boots still belong to this saved Den.
        while 'Watch Bell' not in rendered_text(game):
            assert game.scene.page + 1 < game.scene.pages
            press(game, 'right')
        assert 'Storm Quiver' in rendered_text(game)
        assert 'No recorded source on this shard' in rendered_text(game)
        press(game, 'end')
        assert 'Mirror Badge' in rendered_text(game) and 'Vanguard Drum' in rendered_text(game)
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
    game = create_game('Relic ability reference', backend='mock', save_dir=tmp_path)
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
        text = category_text(game, mouse=True)
        assert 'Border Watch' in text and 'Wolf Den' in text
        click_button(game, 'Sites')
        text = category_text(game, mouse=True)
        assert 'Explorer’s Camp' in text and 'Wayfarer Boots' in text
        click_button(game, 'Close codex')
        assert state.to_json() == before
    finally:
        game._teardown()


def test_paid_watch_army_can_read_its_role_orders_and_costs_without_spending_them(tmp_path):
    """A real support army sees mobility, extraction costs and its shared healing budget."""
    from eador.codex import CodexScene
    from tools.eador_roles_campaign import prepare_support_watch

    state = prepare_support_watch()
    game = create_game('Support role reference', backend='mock', save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        game.tick(1 / 60)
        click_button(game, 'Abilities')
        text = category_text(game, mouse=True)
        assert 'Ranger: shoot then move' in text and 'Moving first gives no second move' in text
        assert 'No Pin' in text and 'terrain costs' in text
        assert 'Swap' in text and "Spend your action and both remaining moves" in text
        assert "preserve the ally's action, spent or unspent" in text and 'Guard/Brace and Pin stay unchanged' in text
        assert 'Acolyte Heal' in text and 'Current battle: 1 of 1 Acolytes have Heal' in text
        assert f"{state.battle.spell_cost('heal')} mana / up to {state.battle.spell_power['heal']} healing" in text
        assert f'Shared mana: {state.battle.mana}' in text
        assert "The hero's action is untouched" in text and 'need not know Heal' in text
        click_button(game, 'Troops')
        troop_text = rendered_text(game)
        while game.scene.ui.find(lambda control: isinstance(control, Button) and control.text == 'Next').enabled:
            click_button(game, 'Next')
            troop_text += ' ' + rendered_text(game)
        assert 'Ranger' in troop_text and 'Shoot before moving to reposition' in troop_text
        assert 'Warden' in troop_text and 'Swap into an adjacent ally’s place' in troop_text
        click_button(game, 'Close codex')
        assert state.to_json() == before and not list(tmp_path.iterdir())
    finally:
        game._teardown()


def test_older_saved_acolyte_reference_never_advertises_an_unavailable_order(tmp_path):
    """The recorded v8 troop stays noncasting in both troop and ability references."""
    from pathlib import Path
    from eador.codex import CodexScene

    state = State.from_json((Path(__file__).parent / 'fixtures/v8_acolyte_battle.json').read_text())
    game = create_game('Saved support reference', backend='mock', save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        text = category_text(game)
        assert 'Acolyte' in text and '2 army recovery' in text
        assert 'shared mana' in text and 'This older battle retains its noncasting Acolytes' in text
        press(game, '2')
        text = category_text(game)
        assert 'Current battle: 0 of 1 Acolytes have Heal' in text
        assert 'This older battle retains its noncasting Acolytes' in text
        press(game, 'escape')
        assert state.to_json() == before and not list(tmp_path.iterdir())
    finally:
        game._teardown()


def test_saved_guided_extraction_reference_quotes_the_paid_contract_and_current_order(tmp_path):
    """A paid, reloaded attempt exposes its escape rules and exact reward without spending an order."""
    from eador.codex import CodexScene
    from eador.content import RELICS
    from tools.eador_extraction_campaign import prepared_crossing

    state = prepared_crossing()
    # A saved-site reward fixture checks that current loot is not replaced by the base table.
    state.provinces[state.hero.pos].site_gold = 61
    state.explore(approach='guided')
    state = State.from_json(state.to_json())
    game = create_game('Extraction reference', backend='mock', save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        press(game, '2')
        press(game, 'end')
        text = rendered_text(game)
        assert 'Evacuate' in text and 'Arrival alone never wins' in text
        assert 'unspent action' in text and 'no adjacent living enemy' in text
        assert state.battle.evacuation_blocked_reason in text
        assert f'Round {state.battle.round} of {state.battle.objective.deadline}' in text
        assert f'{len(state.battle.objective.exits)} marked exits' in text
        assert 'enemy phase' in text and 'rout every defender' in text
        press(game, '5')
        while 'Hire a guide' not in rendered_text(game):
            assert game.scene.page + 1 < game.scene.pages
            press(game, 'right')
        text = rendered_text(game)
        reward = state.battle_adventure
        assert 'Current attempt' in text and 'Paid at entry: 20 gold' in text
        assert f'{reward.gold} gold / {reward.crystals} crystals / {RELICS[reward.relic].name}' in text
        assert 'fee is not refunded' in text
        press(game, 'end')
        text = rendered_text(game)
        assert 'surviving defenders keep their wounds' in text
        assert 'one campaign action' in text and 'reward once' in text
        press(game, 'escape')
        assert state.to_json() == before and not list(tmp_path.iterdir())
    finally:
        game._teardown()


def test_full_cache_reference_matches_saved_cargo_reward_and_spent_hero_via_mouse(tmp_path):
    """The burden and reward belong to the chosen attempt; inspecting them cannot refund its spent order."""
    from eador.codex import CodexScene
    from tools.eador_extraction_campaign import prepare_adventure

    state = prepare_adventure(theme='elderwild')
    state.explore(approach='full')
    state.battle.guard(0)
    state = State.from_json(state.to_json())
    game = create_game('Cargo reference', backend='mock', save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        game.tick(1 / 60)
        click_button(game, 'Abilities')
        while 'Hero move allowance' not in rendered_text(game):
            assert game.scene.page + 1 < game.scene.pages
            click_button(game, 'Next')
        text = rendered_text(game)
        assert state.battle.evacuation_blocked_reason in text
        assert f'Hero move allowance: {state.battle.unit(0).effective_move_range}' in text
        assert 'Cargo: -1' in text and 'Pin and cargo reduce movement (minimum 1), but cannot block Evacuate' in text
        click_button(game, 'Sites')
        text = category_text(game, mouse=True)
        assert 'Travel light' in text and 'Carry the full cache' in text
        assert 'Current attempt' in text and f'Saved reward: {state.battle_adventure.gold} gold' in text
        assert '1 less movement this battle, minimum 1' in text
        click_button(game, 'Close codex')
        assert state.to_json() == before and not list(tmp_path.iterdir())
    finally:
        game._teardown()


def test_direct_route_reference_reports_real_pin_and_current_round_after_reload(tmp_path):
    """A naturally pinned courier sees the saved allowance, rather than its full base movement."""
    from eador.codex import CodexScene
    from tools.eador_extraction_campaign import AdventureOrders, crossing_route, prepared_crossing

    checkpoints = []

    class RecordOrders(AdventureOrders):
        def do(self, command, *args, **kwargs):
            super().do(command, *args, **kwargs)
            if self.battle.unit(0).pinned and self.battle.outcome is None:
                checkpoints.append(self.state.to_json())

    crossing_route(prepared_crossing(), 'direct', orders_type=RecordOrders)
    state = State.from_json(checkpoints[0])
    game = create_game('Pinned courier reference', backend='mock', save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        press(game, '2')
        press(game, 'end')
        text = rendered_text(game)
        assert f'Hero move allowance: {state.battle.unit(0).effective_move_range}' in text
        assert 'Cargo: 0' in text and 'Pin: -2' in text
        assert f'Round {state.battle.round} of {state.battle.objective.deadline}' in text
        press(game, 'escape')
        assert state.to_json() == before and not list(tmp_path.iterdir())
    finally:
        game._teardown()


def test_paid_control_army_reference_shows_both_currency_costs_and_recorded_roles(tmp_path):
    """A troop's quoted crystals come from the same purchase API as recruitment."""
    from eador.codex import CodexScene
    from tools.eador_control_campaign import prepare_control_watch

    state = State.from_json(prepare_control_watch().to_json())
    game = create_game('Control recruit reference', backend='mock', save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        game.tick(1 / 60)
        text = rendered_text(game)
        while game.scene.page + 1 < game.scene.pages:
            click_button(game, 'Next')
            text += ' ' + rendered_text(game)
        for kind in ('sapper', 'adept', 'skyrider'):
            assert UNITS[kind].name in text
            assert f"{state.recruit_cost(kind)} gold + {state.recruit_crystal_cost(kind)} crystal" in text
        assert 'Smoke' in text and 'Repulse' in text and 'Flight' in text
        click_button(game, 'Abilities')
        text = rendered_text(game)
        while game.scene.page + 1 < game.scene.pages:
            click_button(game, 'Next')
            text += ' ' + rendered_text(game)
        for ability in ('Smoke', 'Repulse', 'Flight'):
            assert f'{ability}: 1 capable' in text
        assert 'Rally: 2 capable / 2 unspent orders' in text
        assert '1 charge left' in text and 'terrain sight' in text
        click_button(game, 'Close codex')
        assert state.to_json() == before and not list(tmp_path.iterdir())
    finally:
        game._teardown()


def test_v10_active_battle_reference_keeps_open_sight_and_does_not_grant_new_orders(tmp_path):
    """An older pinned courier cannot gain Rally, charges or new sight rules by opening a reference."""
    from pathlib import Path
    from eador.codex import CodexScene

    state = State.from_json((Path(__file__).parent / 'fixtures/v10_pinned_crossing.json').read_text())
    game = create_game('Legacy control reference', backend='mock', save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        game.tick(1 / 60)
        assert "This older battle's Militia cannot Rally" in rendered_text(game)
        press(game, '2')
        text = rendered_text(game)
        while game.scene.page + 1 < game.scene.pages:
            press(game, 'right')
            text += ' ' + rendered_text(game)
        assert 'This older battle uses open sight' in text
        for ability in ('Rally', 'Smoke', 'Repulse', 'Flight'):
            assert f'{ability}: 0 capable' in text
        assert 'New battles use terrain sight' in text
        press(game, 'escape')
        assert state.to_json() == before and not list(tmp_path.iterdir())
    finally:
        game._teardown()


def test_paid_saved_sapper_reference_keeps_used_charge_after_the_cloud_expires(tmp_path):
    """Smoke duration and the once-per-battle charge are distinct, including after save/load."""
    from eador.codex import CodexScene

    state = State.new(7)
    state.build('market')
    while state.gold < state.recruit_cost('sapper'):
        state.end_turn()
    state.recruit('sapper')
    state.explore()
    sapper = next(unit for unit in state.battle.units if unit.can_smoke)
    state.battle.smoke(sapper.id, sapper.pos)
    state = State.from_json(state.to_json())
    game = create_game('Used control charge reference', backend='mock', save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        for expired in (False, True):
            before = state.to_json()
            game.push(CodexScene(root))
            game.tick(1 / 60)
            click_button(game, 'Abilities')
            text = rendered_text(game)
            while game.scene.page + 1 < game.scene.pages:
                click_button(game, 'Next')
                text += ' ' + rendered_text(game)
            assert f"Smoke: 1 capable / {int(expired)} unspent order{'s' if not expired else ''} · 0 charges left" in text
            assert f'Smoke clouds: {int(not expired)}' in text
            assert 'self-targeting works' in text and 'both sides' in text
            assert 'Guard/Brace anchors' in text and 'Target orders, retaliation and Pin stay unchanged' in text
            assert 'terrain sight' in text and 'endpoint forest gives cover' in text
            assert 'land on an empty hex' in text and 'Pin still slows flight' in text
            click_button(game, 'Close codex')
            assert state.to_json() == before and not list(tmp_path.iterdir())
            if not expired:
                state.battle.end_turn()
                assert state.battle.unit(sapper.id).alive
    finally:
        game._teardown()


def test_earned_censer_reference_uses_saved_hero_order_and_charge_without_writing(tmp_path):
    """A recovered, equipped Censer grants the hero Smoke; reloading keeps its spent charge.

    Catalog and ability pages must identify the acting hero and cannot resurrect
    that charge or imply that equipping multiple relics combines their powers.
    """
    from eador.codex import CodexScene
    from tools.eador_relic_campaign import prepare_censer_watch

    state = prepare_censer_watch()
    state.battle.smoke(0, state.battle.unit(0).pos)
    state = State.from_json(state.to_json())
    game = create_game('Earned relic reference', backend='mock', save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        game.push(CodexScene(root))
        press(game, '2')
        while 'Smoke: 1 capable' not in rendered_text(game):
            assert game.scene.page + 1 < game.scene.pages
            press(game, 'right')
        text = rendered_text(game)
        assert 'Smoke: 1 capable / 0 unspent orders · 0 charges left' in text
        assert 'Hero included' in text and 'Veil Censer' in text
        assert 'even if the caster dies' in text
        press(game, '6')
        assert 'Replacing Moonstone or Ember Lens removes its spell unless learned elsewhere' in rendered_text(game)
        while 'Veil Censer' not in rendered_text(game):
            assert game.scene.page + 1 < game.scene.pages
            press(game, 'right')
        assert 'Saved hero: Smoke recorded' in rendered_text(game)
        assert 'Recorded sources: Courier’s Crossing' in rendered_text(game)
        press(game, 'escape')
        assert state.to_json() == before and not list(tmp_path.iterdir())
    finally:
        game._teardown()
