"""One isolated, resumable linked-campaign phase through the shipped controls.

The builder invokes this in four or five separate app processes. Policies choose visible
orders, including explicit auto-play; they never set live model fields. This is
an executable regression journey, not a human playtest or manual-tactics claim.
"""

import hashlib
import json
import os
from pathlib import Path
import platform
import sys
from time import perf_counter, process_time


def run(output: Path, *, phase: int, recovery=False, backend='pyglet') -> dict:
    from eador.app import ASSETS, create_game
    from eador.campaign_scene import CampaignScene
    from eador.preferences import reading_scale
    from eador.scene import ShardScene, TitleScene
    from tools.cpu_budget import CpuBudget
    from tools.eador_linked_campaign import lose_shard, play_stage, travel_selection
    from tools.eador_ui import PlayerInput

    final_phase = 5 if recovery else 4
    if phase not in range(1, final_phase + 1):
        raise ValueError(f'This campaign verification has {final_phase} process phases.')
    os.environ['SAGA2D_SILENT'] = '1'
    output = output.resolve()
    if phase == 1:
        output.mkdir(parents=True)  # Refuse to overwrite a previous verification or its saves.
        previous = None
    else:
        previous = json.loads((output / f'phase-{phase - 1}.json').read_text())
        assert previous['recovery'] == recovery and previous['phase'] == phase - 1
    started = perf_counter()
    cpu_started = process_time()
    budget = CpuBudget(25)
    game = create_game('Shardbound packaged campaign check', backend=backend,
                       visible=False, save_dir=output / 'saves')
    player = PlayerInput(game, native=backend == 'pyglet', output=output / f'phase-{phase}')
    try:
        game.push(TitleScene(7))
        game.tick(1 / 60)
        loaded = None
        if previous is None:
            player.press('t'); player.press('right'); player.press('return')
            assert isinstance(game.scene, TitleScene) and reading_scale(game) == 125
            player.capture('title-125')
            player.press('l')
        else:
            assert reading_scale(game) == 125, 'Saved reading preference did not survive restart.'
            player.press('f9')
            loaded = player.state.to_json()
            assert loaded == previous['checkpoint'], 'Process restart changed the complete saved State.'
            player.capture('restored-checkpoint-125')
            assert isinstance(game.scene, CampaignScene)
            if phase < final_phase:
                recovering = player.state.campaign.phase == 'recovery'
                funds = player.state.expedition_funding(recovery=recovering)
                if recovering:
                    player.choose_retinue(travel_selection(player.state))
                    player.press('return')
                    assert player.state.campaign.recovery_used and player.state.campaign.phase == 'playing'
                    assert len(player.state.hero.army) == 3
                else:
                    assert player.state.campaign.phase == 'departure'
                    destination = 'rootward' if player.state.campaign.stage == 1 else 'gate'
                    player.state.advance(destination, **travel_selection(player.state))
                assert (player.state.gold, player.state.crystals) == funds
                player.reload(player.state.to_json())

        if phase < final_phase:
            assert isinstance(game.scene, ShardScene)
            stage = player.state.campaign.stage
            player.press('j'); player.capture('contract-125'); player.press('escape')
            if recovery and phase == 2:
                lose_shard(player.state, budget=budget)
                assert isinstance(game.scene, CampaignScene) and player.state.campaign.phase == 'recovery'
                assert not player.state.campaign.recovery_used
                player.capture('saved-capital-loss-125')
            else:
                play_stage(player.state, reload_state=player.reload, budget=budget)
                assert player.state.status == 'victory' and isinstance(game.scene, CampaignScene)
                assert len(player.state.campaign.completed) == stage
                if stage == 3:
                    assert 'The Last Gate' in player.briefings
                player.capture('saved-ending-125' if stage == 3 else 'saved-departure-125')

        checkpoint = player.state.to_json()
        completed = json.loads(checkpoint)['campaign']['completed']
        campaign_phase = player.state.campaign.phase
        recovery_used = player.state.campaign.recovery_used
        player.press('f5')
        returned_to_title = phase == final_phase
        if returned_to_title:
            assert campaign_phase == 'completed' and len(completed) == 3
            player.press('return')
            assert isinstance(game.scene, TitleScene)
            player.capture('return-to-title-125')
        report = dict(phase=phase, recovery=recovery, recovery_used=recovery_used,
                      backend=backend, frozen=bool(getattr(sys, 'frozen', False)),
                      executable=sys.executable, process_id=os.getpid(), platform=platform.platform(),
                      asset_path=str(ASSETS), elapsed_seconds=perf_counter() - started,
                      cpu_seconds=process_time() - cpu_started, cpu_percent=budget.percent,
                      input_activations=len(player.events), inputs=player.events,
                      exact_save_reloads=player.reloads, briefings=player.briefings,
                      loaded_checkpoint=loaded, checkpoint=checkpoint,
                      checkpoint_sha256=hashlib.sha256(checkpoint.encode()).hexdigest(),
                      campaign_phase=campaign_phase, completed_shards=completed,
                      returned_to_title=returned_to_title, reading_scale=reading_scale(game),
                      battle_policy='Explicit auto-play through the visible A control; not manual tactics.')
        (output / f'phase-{phase}.json').write_text(json.dumps(report, indent=2) + '\n')
        return report
    finally:
        game.close()
