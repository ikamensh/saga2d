"""Adventure quotes disclose real entry fees without spending campaign progress."""
import pytest

from tools.cpu_budget import CpuBudget


@pytest.mark.parametrize('approach, fee', [(None, 0), ('unseal', 2)])
def test_vault_quote_matches_the_actual_paid_exploration_without_mutation(approach, fee):
    """A purchased army reaches a generated Vault; quoting and entering choose the same attempt."""
    from eador.adventures import quote_adventure
    from eador.model import State
    from tools.eador_vault_campaign import prepare_vault

    state = prepare_vault(budget=CpuBudget(25))
    province = state.provinces[state.hero.pos]
    assert province.site_kind == 'sealed_vault'
    before = state.to_json()
    gold, crystals, actions = state.gold, state.crystals, state.actions_left
    quote = quote_adventure(province, gold=gold, crystals=crystals, approach=approach)
    assert state.to_json() == before
    assert (quote.gold, quote.crystals) == (0, fee)

    state.explore(approach=approach)
    assert state.battle_adventure == quote.attempt
    assert (state.gold, state.crystals, state.actions_left) == (
        gold - quote.gold, crystals - quote.crystals, actions - 1)
    assert state.battle_adventure.encounter == state.battle_encounter
    assert State.from_json(state.to_json()).battle_adventure == quote.attempt
