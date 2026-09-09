"""Buy Aerie parties and replay their manual orders through real keyboard/mouse controls."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from saga2d import Label
from eador.app import create_game
from eador.codex import CodexScene
from eador.encounter_scene import EncounterScene
from eador.preferences import reading_scale
from eador.scene import BattleScene, ChoiceScene, ResultScene, ShardScene, TitleScene
from tools.eador_sources import source_name
from tools.audit_eador_aerie import Purchases, without_flight_reachable
from tools.eador_aerie_campaign import (prepare_aerie, aerie_western_route, aerie_northern_route,
                                       aerie_scout_route, aerie_failed_sortie, aerie_retry_route)
from tools.eador_ui import PlayerInput
from tools.verify_eador_control import ControlOrders
from tools.verify_eador_guidance import check_reading_layout
from tools.verify_eador_reading import check_page

PLANS = ('western', 'western-heal', 'northern', 'scout', 'failed-retry')


class AerieOrders(ControlOrders):
    def __init__(self, state):
        self.flight_landings = []
        super().__init__(state)
        self.player.capture('aerie-deployment')

    def do(self, command, *args, **kwargs):
        if command == 'move' and self.battle.unit(args[0]).can_fly:
            if args[1] not in without_flight_reachable(self.battle, args[0]):
                self.flight_landings.append(dict(unit=args[0], source=self.battle.unit(args[0]).pos, destination=args[1]))
        if command == 'attack':
            attacker, target = (self.battle.unit(ident) for ident in args)
            hp, forecast = (target.hp, attacker.hp), self.battle.preview(*args)
            self.select(attacker.id)
            before = self.state.to_json()
            self.aim(target.id)
            assert self.state.to_json() == before
            self.player.capture(f'round-{self.battle.round}-attack-{attacker.id}-forecast')
            self.player.press('return')
            assert (hp[0]-target.hp, hp[1]-attacker.hp) == forecast
            self.orders.append((command,args,kwargs))
        else:
            super().do(command,*args,**kwargs)
        if command == 'move' and self.battle.unit(args[0]).can_fly:
            self.player.capture(f'round-{self.battle.round}-flight-landed')
            self.player.reload(self.state.to_json())
        elif command == 'guard' and self.battle.unit(args[0]).stance == 'brace' and self.battle.round <= 2:
            self.player.capture(f'round-{self.battle.round}-braced-reserve')
        elif command == 'end_turn' and self.battle.round <= 3 and isinstance(self.player.game.scene,BattleScene):
            self.player.capture(f'round-{self.battle.round}-after-enemies')


def inspect_briefing(player):
    before = player.state.to_json()
    player.press('x')
    assert isinstance(player.game.scene,EncounterScene)
    player.press('t'); player.press('right'); player.button('Apply')
    assert reading_scale(player.game) == 125
    for index, approach in enumerate(player.game.scene.approaches):
        player.press(str(index+1))
        scene = player.game.scene
        text = '\n'.join(label.text for label in scene.ui.find_all(lambda item:isinstance(item,Label)))
        guards = player.state.provinces[player.state.hero.pos].site_guards
        assert ('Skyriders cross marsh' in text) == ('skyrider' in guards)
        assert ('Their Pikeman can Brace' in text) == ('pikeman' in guards)
        if 'skyrider' not in guards:
            assert 'raider sooner' not in text and 'attack your rear' not in text
        check_reading_layout(scene)
        assert player.state.to_json() == before
        player.capture(f'briefing-{approach.id}-125')
    player.press('c'); assert isinstance(player.game.scene,CodexScene)
    player.press('1')
    for _ in range(player.game.scene.pages):
        if any(entry.title=='Skyrider' for entry in player.game.scene.visible_entries):
            break
        player.press('right')
    assert any(entry.title=='Skyrider' for entry in player.game.scene.visible_entries)
    check_page(player.game.scene); player.capture('codex-flight-125')
    player.press('escape'); player.press('escape')
    assert isinstance(player.game.scene,ShardScene) and player.state.to_json() == before
    player.reload(before)


def failed_retry(state):
    player, output = state.player, state.player.output
    source = state.hero.pos
    player.output = output/'failure'
    failure = aerie_failed_sortie(state,orders_type=AerieOrders)
    assert isinstance(player.game.scene,ResultScene)
    player.capture('hero-defeat')
    dead = [u.id for u in failure.battle.units if u.team=='player' and u.id and not u.alive]
    assert failure.battle.outcome_reason=='hero_death' and failure.battle.round==56
    gold,crystals,xp = state.gold,state.crystals,state.hero.xp
    state.resolve_battle()
    assert (state.gold,state.crystals,state.hero.xp)==(gold-20,crystals,xp)
    assert state.choice is None and not state.provinces[source].explored
    assert state.provinces[source].site_guards==['archer'] and state.provinces[source].site_guard_hp==[11]
    player.reload(state.to_json()); player.capture('saved-loss')
    gold,crystals=state.gold,state.crystals
    state.recruit('skyrider')
    assert (state.gold,state.crystals)==(gold-60,crystals-3)
    assert not set(dead).intersection(t.id for t in state.hero.army)
    player.reload(state.to_json()); player.capture('paid-new-skyrider')
    player.output=output/'retry'; inspect_briefing(player)
    entry = state.gold,state.crystals,state.hero.mana
    retry = aerie_retry_route(state,orders_type=AerieOrders)
    return retry,entry,dict(outcome_reason='hero_death',round=56,dead_troop_ids=dead,retreat_gold=20,
                            replacement_gold=60,replacement_crystals=3,guards_on_retry=[['archer',11]],
                            reward_before_retry=False,orders=failure.orders)


def verify(output, *, backend='pyglet', plan='western'):
    output.mkdir(parents=True,exist_ok=True)
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'),*ROOT.joinpath('saga2d').rglob('*.py'),
                      *ROOT.joinpath('tools').glob('eador_*.py'),*[ROOT/'tools'/name for name in (
                          'audit_eador_aerie.py','audit_eador_extraction.py','verify_eador_control.py',
                          'verify_eador_extraction.py','verify_eador_guidance.py','verify_eador_reading.py',
                          'verify_eador_aerie.py')]])
    hashes = {source_name(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty = subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True).splitlines()
    started=perf_counter(); hero='Scout' if plan=='scout' else 'Commander'
    with TemporaryDirectory(prefix='shardbound-aerie-') as directory:
        game=create_game(backend=backend,visible=False,save_dir=Path(directory)/'saves')
        player=PlayerInput(game,native=backend=='pyglet',output=output)
        try:
            game.push(TitleScene(7,hero_class=hero,theme='ruins')); player.press('return')
            state=Purchases(player.state)
            prepare_aerie(hero,party='ground' if plan=='scout' else 'flight',state=state)
            inspect_briefing(player)
            gold,crystals,mana=state.gold,state.crystals,state.hero.mana
            failure=None
            if plan=='failed-retry':
                play,(gold,crystals,mana),failure=failed_retry(state)
            elif plan in ('western','western-heal'):
                play=aerie_western_route(state,heal=plan=='western-heal',orders_type=AerieOrders)
            else:
                play=(aerie_northern_route if plan=='northern' else aerie_scout_route)(state,orders_type=AerieOrders)
            battle,reward=state.battle,state.battle_adventure
            assert battle.outcome_reason=='rout' and isinstance(game.scene,ResultScene)
            assert all(u.alive for u in battle.units if u.team=='player')
            assert (state.gold,state.crystals)==(gold,crystals)
            player.capture('aerie-rout-victory'); player.reload(state.to_json())
            battle=state.battle
            survivors=[dict(id=u.id,kind=u.kind,hp=u.hp,max_hp=u.max_hp)for u in battle.units if u.team=='player']
            report=dict(plan=plan,hero=hero,backend=backend,logical_resolution=game.resolution,window_size=game.window_size,
                        framebuffer_size=game.backend.capture_frame().size if backend=='pyglet' else None,
                        purchases=state.purchases,failed_attempt=failure,reading_scale=reading_scale(game),
                        campaign_turn=state.turn,battle_rounds=battle.round,outcome_reason=battle.outcome_reason,
                        fee_gold=0,fee_crystals=0,reward_gold=reward.gold,reward_crystals=reward.crystals,reward_relic=reward.relic,
                        mana_spent=mana-battle.mana,survivors=survivors,troops_lost=0,
                        hp_deficit=sum(u['max_hp']-u['hp']for u in survivors),flight_only_landings=play.flight_landings)
            source=state.hero.pos
            state.resolve_battle()
            assert (state.gold,state.crystals)==(gold+reward.gold,crystals+reward.crystals)
            while isinstance(game.scene,ChoiceScene):player.press('1')
            assert state.provinces[source].explored and reward.relic in state.inventory
            before=state.to_json();player.press('x')
            assert state.to_json()==before and isinstance(game.scene,ShardScene)
            player.reload(before)
            check_reading_layout(game.scene)
            player.capture('aerie-reward-kept-once')
            changed=[name for name,digest in hashes.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
            assert not changed
            report.update(input_activations=len(player.events),exact_save_reloads=player.reloads,orders=play.orders,
                          inputs=player.events,source_revision=revision,dirty_at_start=dirty,source_sha256=hashes,
                          source_files_changed=changed,elapsed_seconds=perf_counter()-started,
                          python=platform.python_version(),platform=platform.platform())
            (output/'journey.json').write_text(json.dumps(report,indent=2)+'\n')
            print(f'Aerie/{plan}: round{report["battle_rounds"]}, {len(player.events)} inputs, {player.reloads} exact reloads ({backend})',flush=True)
            return report
        finally:
            game._teardown()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/shardbound-aerie'))
    parser.add_argument('--plan',choices=PLANS,default='western')
    args=parser.parse_args();verify(args.output,plan=args.plan)
