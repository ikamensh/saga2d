"""Relic presentation must preserve earned rewards and paged equipment controls."""


def test_saved_collection_paging_and_earned_reward_remain_playable_with_relic_icons(tmp_path):
    """Native review's same input journey equips a paged old relic and four saved new rewards.

    Repeated activation of Equipped must neither change state nor rotate saves.
    Every original icon also draws through the same public Scene/Game path.
    """
    from tools.verify_eador_relic_art import verify
    verify(tmp_path, backend='mock')
