"""The Vault's crystal choice and manual escapes work through player controls."""
import pytest


@pytest.mark.parametrize('approach,rounds,fee', [('crossfire', 4, 0), ('unseal', 2, 2)])
def test_vault_routes_spend_the_disclosed_fee_and_save_an_explicit_escape(tmp_path, approach, rounds, fee):
    from tools.verify_eador_vault import verify

    report = verify(tmp_path, backend='mock', approach=approach)
    assert report['battle_rounds'] == rounds
    assert report['fee_gold'] == 0 and report['fee_crystals'] == fee
    assert report['reward_gold'] == 60 and report['reward_crystals'] == 1
    assert report['exact_save_reloads'] >= 4
