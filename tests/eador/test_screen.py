from eador.model import State
from tools.eador_screen_campaign import prepare_screen, screen_western_route
from tests.eador.test_extraction_journeys import Journey
from tests.eador.test_pack_hunt import assert_one_rout_reward


def test_paid_western_screen_relocates_under_smoke_and_wins_with_saved_orders():
    state = prepare_screen()
    assert state.hero.pos == (0, -1) and state.turn == 8
    assert state.provinces[state.hero.pos].site_kind == 'smuggler_screen'
    assert [troop.kind for troop in state.hero.army] == ['militia', 'militia', 'archer', 'warden', 'ranger']
    before = State.from_json(state.to_json())
    play = screen_western_route(state, orders_type=Journey)
    assert play.battle.outcome_reason == 'rout' and play.battle.round == 4
    assert all(u.alive for u in play.battle.units if u.team == 'player')
    assert sum(u.max_hp - u.hp for u in play.battle.units if u.team == 'player') == 62
    assert play.battle.mana == before.hero.mana
    assert play.state.gold == before.gold and play.state.crystals == before.crystals
    assert_one_rout_reward(play)


def test_saved_old_grove_and_caravan_keep_their_exact_active_battle_continuations():
    from pathlib import Path
    from tools.eador_campaign import finish_battle

    fixtures = Path(__file__).parent / 'fixtures'
    for kind in ('grove', 'caravan'):
        state = State.from_json((fixtures / f'v12_elderwild_{kind}_battle.json').read_text())
        assert state.provinces[(0, -1)].site_kind == kind
        assert all(province.site_kind != 'smuggler_screen' for province in state.provinces.values())
        finish_battle(state)
        expected = State.from_json((fixtures / f'v12_elderwild_{kind}_result.json').read_text())
        assert state.to_json() == expected.to_json()
