"""Trusted room checkpoints preserve real rules independently of player views."""
import json

import pytest

from online_server.games import create_match, restore_match


def orders_for(game, match):
    """Two legal, state-changing orders using the current game's public model."""
    if game == 'tribes-v1':
        return [(0, {'action': 'end_turn'}), (1, {'action': 'end_turn'})]
    if game == 'warband-v1':
        hall = next(building for building in match.world.buildings.values()
                    if building.player == 0 and building.type.value == 'town_hall')
        return [(0, {'action': 'train', 'args': [hall.id, 'peasant']}),
                (0, {'action': 'cancel_train', 'args': [hall.id]})]
    return [(0, {'target': 'state', 'action': 'build', 'args': ['barracks']}),
            (1, {'target': 'state', 'action': 'recruit', 'args': ['swordsman']})]


@pytest.mark.parametrize('game, options', [
    ('tribes-v1', {'size': 11}),
    ('warband-v1', {'width': 40, 'height': 32}),
    ('shardbound-v1', {}),
])
def test_trusted_checkpoint_keeps_existing_json_and_the_next_real_order(game, options):
    """Every current game resumes exact paid/turn state using its unchanged checkpoint format."""
    from online_server.games import checkpoint_match

    match = create_match(game, options)
    first, following = orders_for(game, match)
    match.apply(*first)
    # These games currently expose their complete state; preserve that stored format.
    before = json.loads(json.dumps(match.snapshot(0)))
    checkpoint = json.loads(json.dumps(checkpoint_match(game, match)))
    assert checkpoint == before
    resumed = restore_match(game, checkpoint)
    assert resumed.snapshot(0) == match.snapshot(0)
    assert resumed.snapshot(1) == match.snapshot(1)

    match.apply(*following)
    resumed.apply(*following)
    assert json.loads(json.dumps(resumed.snapshot(0))) != before
    assert resumed.snapshot(0) == match.snapshot(0)
    assert resumed.snapshot(1) == match.snapshot(1)


def test_room_storage_retains_campaign_hidden_from_player_snapshots(tmp_path):
    """A filtered view cannot erase an actual paid realm or its unfinished battle on restart."""
    from eador.multiplayer import ShardboundMatch
    from online_server import Room
    from online_server.storage import RoomStore

    class FilteredCampaign(ShardboundMatch):
        def snapshot(self, player):
            return {'status': self.state.status}

    match = FilteredCampaign()
    match.apply(0, {'target': 'state', 'action': 'build', 'args': ['barracks']})
    match.apply(1, {'target': 'state', 'action': 'explore', 'args': []})
    expected = ShardboundMatch.snapshot(match, 0)
    store = RoomStore(tmp_path)
    try:
        store.save(Room('shardbound-v1', match, 'private-campaign'), ttl=900)
    finally:
        store.close()

    reopened = RoomStore(tmp_path)
    try:
        saved, = reopened.load()
    finally:
        reopened.close()
    assert saved['state'] == expected
    resumed = restore_match(saved['game'], saved['state'])
    unit = next(unit for unit in resumed.state.battle.units if unit.team == 'player')
    guard = {'target': 'battle', 'action': 'guard', 'args': [unit.id]}
    match.apply(1, guard)
    resumed.apply(1, guard)
    assert resumed.state.battle.unit(unit.id).acted
    assert resumed.snapshot(0) == ShardboundMatch.snapshot(match, 0)
