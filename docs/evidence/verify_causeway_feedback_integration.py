"""Read-only integration harness: existing paid native routes, capture then visible Finish."""
import hashlib,json
from pathlib import Path
from eador.battle_playback_scene import BattlePlaybackScene
from tools.eador_ui import PlayerInput
import tools.verify_eador_causeway as verifier

class CapturedInput(PlayerInput):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.playback_frames=[]
    def finish_playback(self):
        if isinstance(self.game.scene,BattlePlaybackScene) and self.root.state.battle_encounter=='runebound_causeway':
            saved=self.state.to_json()
            index=len(self.playback_frames)+1
            scene=self.game.scene
            frame=dict(index=index,round=self.root.state.battle.round,
                       event=scene.playback.event.text,event_count=len(scene.playback.trace.events),
                       state_sha256=hashlib.sha256(saved.encode()).hexdigest(),
                       image=str(self.output / f'playback-{index}.png'))
            self.capture(f'playback-{index}',settle=False)
            assert self.state.to_json()==saved
            self.playback_frames.append(frame)
        super().finish_playback()

instances=[]
class RetainedInput(CapturedInput):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        instances.append(self)
verifier.PlayerInput=RetainedInput
root=Path('/tmp/causeway-feedback-integration-native')
for plan in ('infused-guard','failed-retry'):
    report=verifier.verify(root/plan,plan=plan)
    player=instances[-1]
    finishes=[e for e in report['inputs'] if e[:2]==('BattlePlaybackScene','key') and e[2]=='space']
    assert finishes and player.playback_frames
    extra=dict(plan=plan,visible_space_finishes=len(finishes),playback_frames=player.playback_frames,
               harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (root/plan/'playback-captures.json').write_text(json.dumps(extra,indent=2)+'\n')
    print('Visible modal Finish orders',plan,len(finishes),flush=True)
