"""Complete three linked shards through shipped input, with saved departures and recovery."""
import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SAGA2D_SILENT'] = '1'

from eador.app import create_game
from eador.campaign_scene import CampaignScene
from eador.scene import ShardScene, TitleScene
from tools.eador_campaign import finish_battle
from tools.eador_linked_campaign import play_stage, travel_selection
from tools.eador_ui import PlayerInput


def lose_shard(state):
    """Leave the capital exposed and decline its defenses through ordinary commands."""
    if state.hero.pos == (-2, 0):
        if not state.actions_left:
            state.end_turn()
        state.travel((-2, 1))
        if state.battle:
            finish_battle(state)
    for _ in range(120):
        if state.status == 'defeat':
            return
        state.end_turn()
        if state.battle:
            state.retreat()
    raise AssertionError('Neglect did not lose the capital')


def choose_retinue(player):
    selection = travel_selection(player.state)
    assert isinstance(player.game.scene, CampaignScene) and player.game.scene.step == 'retinue'
    for column, choices in ((0, selection['troop_ids']), (1, selection['relic_ids'])):
        player.press('left' if column == 0 else 'right')
        items = player.state.hero.army if column == 0 else player.state.inventory
        for index, item in enumerate(items):
            if (item.id if column == 0 else item) in choices:
                player.press('space')
            if index + 1 < len(items):
                player.press('down')
    return selection


def verify(output, *, backend='pyglet', middle='rootward', finale='gate', recovery=False):
    started = perf_counter()
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='shardbound-linked-') as directory:
        game = create_game('Shardbound linked journey', backend=backend, visible=False,
                           save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            game.push(TitleScene(7))
            player.capture('title')
            player.press('l')
            assert player.state.campaign.stage == 1
            for stage, destination in ((1, middle), (2, finale), (3, None)):
                if recovery and stage == 2:
                    lose_shard(player.state)
                    assert isinstance(game.scene, CampaignScene) and game.scene.phase == 'recovery'
                    before = player.state.to_json()
                    player.capture('recovery')
                    player.reload(before)
                    choose_retinue(player)
                    player.press('return')
                    assert player.state.campaign.recovery_used and player.state.campaign.phase == 'playing'
                    assert player.state.gold == 60 and len(player.state.hero.army) == 3
                    player.reload(player.state.to_json())
                play_stage(player.state, reload_state=player.reload)
                assert player.state.status == 'victory', f'Stage {stage} did not finish'
                assert isinstance(game.scene, CampaignScene)
                if destination is None:
                    assert player.state.campaign.phase == 'completed' and len(player.state.campaign.completed) == 3
                    player.capture('completed')
                    player.reload(player.state.to_json())
                    records = json.loads(player.state.to_json())['campaign']['completed']
                    player.press('return')
                    assert isinstance(game.scene, TitleScene)
                    break
                player.capture(f'stage-{stage}-offers')
                before = player.state.to_json()
                player.reload(before)
                index = next(index for index, offer in enumerate(player.state.campaign.offers) if offer.id == destination)
                player.press(str(index + 1))
                assert player.state.to_json() == before
                player.press('escape')
                assert player.state.to_json() == before and game.scene.step == 'offers'
                player.press(str(index + 1))
                selected = choose_retinue(player)
                player.capture(f'stage-{stage}-retinue')
                player.press('return')
                assert isinstance(game.scene, ShardScene) and player.state.campaign.stage == stage + 1
                assert set(selected['troop_ids']) <= {troop.id for troop in player.state.hero.army}
                assert set(selected['relic_ids']) == set(player.state.inventory)
                player.capture(f'stage-{stage + 1}-arrival')
                player.reload(player.state.to_json())
            report = dict(backend=backend, middle=middle, finale=finale, recovery=recovery,
                          elapsed_seconds=perf_counter() - started, input_activations=len(player.events),
                          exact_save_reloads=player.reloads, records=records, inputs=player.events)
            (output / 'journey.json').write_text(json.dumps(report, indent=2) + '\n')
            print(f'Linked {middle}/{finale}, recovery={recovery}: {len(player.events)} input activations, '
                  f'{player.reloads} exact reloads, {report["elapsed_seconds"]:.2f}s ({backend})', flush=True)
            return report
        finally:
            game._teardown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-linked'))
    parser.add_argument('--middle', choices=('rootward', 'foundries'), default='rootward')
    parser.add_argument('--finale', choices=('throne', 'gate'), default='gate')
    parser.add_argument('--recovery', action='store_true')
    args = parser.parse_args()
    verify(args.output, middle=args.middle, finale=args.finale, recovery=args.recovery)
