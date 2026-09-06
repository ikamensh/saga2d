"""Recover blocked departure and recovery checkpoints through real player controls."""
import argparse
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SAGA2D_SILENT'] = '1'

from eador.app import create_game
from eador.campaign_scene import CampaignScene
from eador.model import State
from eador.persistence import AUTO_SLOTS, CampaignSaves
from eador.scene import ShardScene
from tools.eador_linked_campaign import lose_shard, play_stage
from tools.eador_ui import PlayerInput


def verify(output, *, backend='pyglet', recovery=False):
    """Prepare an earned transition, retain damaged autosaves, and follow the manual-save remedy."""
    state = State.new_campaign()
    if recovery:
        lose_shard(state)
    else:
        state = play_stage(state)
    phase = state.campaign.phase
    with TemporaryDirectory(prefix='shardbound-checkpoint-') as directory:
        save_dir = Path(directory) / 'saves'
        game = create_game(backend=backend, visible=False, save_dir=save_dir)
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            saves = CampaignSaves(game.save_manager)
            for _ in AUTO_SLOTS:
                saves.autosave(state)
            paths = list(save_dir.glob('*.json'))
            assert len(paths) == len(AUTO_SLOTS)
            for path in paths:
                path.write_bytes(b'Damaged autosave')
            game.push(ShardScene(state))
            game.tick(1 / 60)
            if not recovery:
                player.press('1')
            player.press('space')
            before = state.to_json()
            selected = game.scene.troop_ids.copy()
            player.press('return')
            assert isinstance(game.scene, CampaignScene) and state.to_json() == before
            assert game.scene.troop_ids == selected and 'Autosave failed' in game.scene.message
            player.capture(phase + '-blocked')
            player.press('f5')
            player.press('return')
            assert isinstance(game.scene, ShardScene) and state.campaign.phase == 'playing'
            assert state.campaign.recovery_used if recovery else state.campaign.stage == 2
            assert 'Arrived.' in game.scene.message
            assert all(path.read_bytes() == b'Damaged autosave' for path in paths)
            player.capture(phase + '-arrival')
            player.press('f9')
            assert isinstance(game.scene, CampaignScene) and player.state.to_json() == before
            print(f'{phase.title()} checkpoint refusal, manual remedy and exact reload passed ({backend})')
        finally:
            game._teardown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-checkpoints'))
    args = parser.parse_args()
    for recovery in (False, True):
        verify(args.output, recovery=recovery)
