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
from eador.campaign_scene import CampaignPlanScene, CampaignScene
from eador.content import RELICS
from eador.difficulty import DIFFICULTIES
from eador.model import State
from eador.scene import ShardScene, TitleScene
from tools.eador_campaign import play_campaign
from tools.eador_linked_campaign import lose_shard, play_stage, travel_selection
from tools.eador_ui import PlayerInput


def verify_inventory(output, *, backend='pyglet'):
    """An explicitly prepared, publicly earned eight-relic save tests the mouse page boundary."""
    state = State.new_campaign(0)
    route = [state.hero.pos] + [p for p in sorted(state.provinces) if p not in (state.hero.pos, (2, 0))] + [(2, 0)]
    state = play_campaign(state, route)
    with TemporaryDirectory(prefix='shardbound-retinue-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            game.push(ShardScene(state))
            game.tick(1 / 60)
            player.button('Choose challenge')
            player.capture('retinue-page-1')
            player.button('Next')
            relic = state.inventory[-1]
            player.button('Leave · ' + RELICS[relic].name)
            player.capture('retinue-page-2')
            player.button('Previous')
            player.button('Depart for the next shard')
            assert state.inventory == [relic] and isinstance(game.scene, ShardScene)
            print(f'Eight earned relics, mouse paging and last-item carryover passed ({backend})', flush=True)
        finally:
            game._teardown()


def verify(output, *, backend='pyglet', middle='rootward', finale='gate', recovery=False, difficulty='standard'):
    started = perf_counter()
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='shardbound-linked-') as directory:
        game = create_game('Shardbound linked journey', backend=backend, visible=False,
                           save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            game.push(TitleScene(7))
            player.press(str(list(DIFFICULTIES).index(difficulty) + 1))
            player.capture('title')
            player.press('l')
            assert player.state.campaign.stage == 1 and player.state.rules is DIFFICULTIES[difficulty]
            for stage, destination in ((1, middle), (2, finale), (3, None)):
                before = player.state.to_json()
                player.press('j')
                assert isinstance(game.scene, CampaignPlanScene)
                player.capture(f'stage-{stage}-plan')
                player.press('1')
                assert player.state.to_json() == before
                player.capture(f'stage-{stage}-objectives')
                if recovery and stage == 2:
                    lose_shard(player.state)
                    assert isinstance(game.scene, CampaignScene) and game.scene.phase == 'recovery'
                    before = player.state.to_json()
                    player.capture('recovery')
                    player.reload(before)
                    funds = player.state.expedition_funding(recovery=True)
                    player.choose_retinue(travel_selection(player.state))
                    player.press('return')
                    assert player.state.campaign.recovery_used and player.state.campaign.phase == 'playing'
                    assert (player.state.gold, player.state.crystals) == funds and len(player.state.hero.army) == 3
                    player.reload(player.state.to_json())
                play_stage(player.state, reload_state=player.reload)
                assert player.state.status == 'victory', f'Stage {stage} did not finish'
                assert isinstance(game.scene, CampaignScene)
                if destination is None:
                    assert player.state.campaign.phase == 'completed' and len(player.state.campaign.completed) == 3
                    player.capture('completed')
                    player.reload(player.state.to_json())
                    records = json.loads(player.state.to_json())['campaign']['completed']
                    rules_id = player.state.rules_id
                    player.press('return')
                    assert isinstance(game.scene, TitleScene) and game.scene.difficulty == difficulty
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
                selected = player.choose_retinue(travel_selection(player.state))
                funds = player.state.expedition_funding()
                player.capture(f'stage-{stage}-retinue')
                player.press('return')
                assert isinstance(game.scene, ShardScene) and player.state.campaign.stage == stage + 1
                assert player.state.rules is DIFFICULTIES[difficulty]
                assert (player.state.gold, player.state.crystals) == funds
                assert set(selected['troop_ids']) <= {troop.id for troop in player.state.hero.army}
                assert set(selected['relic_ids']) == set(player.state.inventory)
                player.capture(f'stage-{stage + 1}-arrival')
                player.reload(player.state.to_json())
            if finale == 'gate':
                assert 'The Last Gate' in player.briefings, 'The final ritual was not briefed before committing'
            report = dict(backend=backend, middle=middle, finale=finale, recovery=recovery, difficulty=difficulty,
                          rules_id=rules_id, briefings=player.briefings,
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
    parser.add_argument('--difficulty', choices=DIFFICULTIES, default='standard')
    parser.add_argument('--inventory', action='store_true', help='verify mouse pagination using a prepared full-inventory save')
    args = parser.parse_args()
    if args.inventory:
        verify_inventory(args.output)
    else:
        verify(args.output, middle=args.middle, finale=args.finale, recovery=args.recovery, difficulty=args.difficulty)
