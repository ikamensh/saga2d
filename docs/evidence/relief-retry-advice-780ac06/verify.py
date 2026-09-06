import hashlib,json,os,subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
os.environ.setdefault('SAGA2D_SILENT','1')
from saga2d import Label
from eador.app import create_game
from eador.model import State
from eador.persistence import CampaignSaves
from eador.scene import ShardScene
from tools.eador_extraction_campaign import AdventureOrders
from tools.eador_relief_campaign import prepare_relief,relief_forward_opening
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout
root=Path.cwd();out=Path('/tmp/relief-retry-advice-native');out.mkdir(exist_ok=True)
files=sorted([*root.glob('eador/*.py'),*root.glob('saga2d/**/*.py'),root/'tests/eador/test_relief_scene.py'])
hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
state=prepare_relief();state.explore(approach='forward');orders=AdventureOrders(state)
relief_forward_opening(orders);state.retreat();saved=state.to_json()
assert state.provinces[state.hero.pos].site_guards==['skyrider','archer','guard']
frames=[]
with TemporaryDirectory(prefix='relief-retry-advice-') as folder:
 game=create_game(backend='pyglet',visible=False,save_dir=Path(folder)/'saves')
 try:
  game.set_window_size((1280,720))
  CampaignSaves(game.save_manager).save(state);game.push(ShardScene(State.new(7)))
  player=PlayerInput(game,native=True,output=out);player.press('f9');assert player.state.to_json()==saved
  player.press('x');player.press('t');player.press('right');player.press('return')
  for shortcut,name in [('1','forward'),('2','western')]:
   player.press(shortcut);check_reading_layout(game.scene)
   labels=[c.text for c in game.scene.ui.walk() if isinstance(c,Label)]
   assert 'Skyrider crosses occupied cells; deny its landing.' in labels
   assert not any('remove support' in s or "Militia clears adjacent allies' Pin" in s for s in labels)
   assert player.state.to_json()==saved
   path=player.capture(f'{name}-retry-125')
   frames.append(dict(approach=name,labels=labels,window=game.window_size,height=game.scene.height))
  report=dict(source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
   source_sha256=hashes,input_activations=len(player.events),inputs=player.events,frames=frames,
   initial_saved_state=json.loads(saved),earned_opening_orders=orders.orders,
   scope='Paid model preparation and opening, actual retreat; native file load and 125% briefing inputs. No injected wounds or roster.')
 finally:game._teardown();game.backend.quit()
assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==sha for name,sha in hashes.items())
report['source_files_changed']=False
(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('Passed native: both125retrybriefings,',report['input_activations'],'inputs, exactstate preserved')
