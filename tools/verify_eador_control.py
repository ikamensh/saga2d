"""Buy control recruits and use their saved orders through real mouse/keyboard input."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['SAGA2D_SILENT'] = '1'

from eador.app import create_game
from eador.model import State
from eador.scene import ResultScene, ShardScene, TitleScene
from tools.eador_control_campaign import prepare_control_watch, watch_control_route
from tools.eador_extraction_campaign import crossing_route, prepare_adventure
from tools.eador_ui import PlayerInput
from tools.verify_eador_extraction import PlayerOrders


class ControlOrders(PlayerOrders):
    """Extend ordinary battle inputs with exact displacement, Pin removal and finite screens."""
    def do(self, command, *args, **kwargs):
        if command not in ('smoke', 'repulse', 'rally'):
            if command == 'move' and self.battle.unit(args[0]).can_fly:
                self.select(args[0])
                self.player.capture(f'round-{self.battle.round}-flight-reachable')
            return super().do(command, *args, **kwargs)
        actor = self.battle.unit(args[0])
        self.select(actor.id)
        before = self.state.to_json()
        forecast = getattr(self.battle, command + '_preview')(*args)
        if command != 'smoke':
            target = self.battle.unit(args[1])
            target_before = asdict(target)
        self.player.press({'smoke': 'd', 'repulse': 'r', 'rally': 'q'}[command])
        pos = args[1] if command == 'smoke' else target.pos
        for _ in self.battle.terrain:
            if self.player.game.scene.cursor == pos:
                break
            self.player.press('f')
        assert self.player.game.scene.cursor == pos and self.state.to_json() == before
        self.player.capture(f'round-{self.battle.round}-{command}-forecast')
        self.player.press('return')
        if command == 'smoke':
            assert forecast in self.battle.smoke_clouds
        elif command == 'repulse':
            assert asdict(target) == {**target_before, 'pos': forecast}
        else:
            assert asdict(target) == {**target_before, 'pinned': False}
            assert self.battle.reachable(target.id) == forecast.reachable
        assert actor.acted and actor.moved
        if command != 'rally':
            assert command in actor.spent_abilities
        self.orders.append((command, args, kwargs))
        self.player.reload(self.state.to_json())


def verify(output, *, backend='pyglet', scenario='smoke'):
    output.mkdir(parents=True, exist_ok=True)
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'),
                      *[ROOT / 'tools' / name for name in ('eador_campaign.py', 'eador_control_campaign.py',
                          'eador_extraction_campaign.py', 'eador_roles_campaign.py', 'eador_ui.py',
                          'verify_eador_control.py', 'verify_eador_extraction.py')]])
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines()
    started = perf_counter()
    with TemporaryDirectory(prefix='shardbound-controls-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        state = player.state

        def select(ident):
            player.click(*game.scene.grid.center(state.battle.unit(ident).pos))
            assert game.scene.selected == ident

        try:
            game.push(TitleScene(7))
            player.press('return')
            if scenario == 'sight':
                prepare_control_watch(state)
                archer = next(unit for unit in state.battle.units if unit.team == 'player' and unit.kind == 'archer')
                target = next(unit for unit in state.battle.units if unit.team == 'enemy' and unit.kind == 'pikeman')
                select(archer.id)
                player.click(*game.scene.grid.center((-2, -1)))
                assert archer.pos == (-2, -1) and not archer.acted
                for _ in range(3):
                    player.press('right')
                assert game.scene.cursor == target.pos and not state.battle.has_sight(archer.pos, target.pos)
                before = state.to_json()
                player.capture('forest-blocked-shot-preview')
                player.press('return')
                assert state.to_json() == before
                assert 'clear sight' in game.scene.message
                player.capture('forest-blocked-shot-refused')
                legacy = State.from_json((ROOT / 'tests/eador/fixtures/v10_pinned_crossing.json').read_text())
                game.clear_and_push(ShardScene(legacy))
                player.press('left')
                assert state.battle.sight_rules == 'open'
                player.capture('saved-open-sight-guidance')
                if backend == 'mock':
                    displayed = ' '.join(item['text'] for item in game.backend.texts)
                    assert 'Saved rules allow ranged orders through terrain.' in displayed
                    assert 'Forest and smoke block ranged orders.' not in displayed
                select(3)
                for key in ('right', 'right', 'up', 'up', 'up'):
                    player.press(key)
                target = next(unit for unit in state.battle.units if unit.pos == game.scene.cursor)
                assert target in state.battle.targets(3)
                damage, retaliation = state.battle.preview(3, target.id)
                health, own_health = target.hp, state.battle.unit(3).hp
                player.capture('saved-open-sight-attack-preview')
                player.press('return')
                assert target.hp == health - damage and state.battle.unit(3).hp == own_health - retaliation
                player.reload(state.to_json())
            elif scenario == 'watch':
                prepare_control_watch(state)
                play = watch_control_route(state, orders_type=ControlOrders)
                assert state.battle.outcome_reason == 'hold' and state.battle.round == 3
                assert all(unit.alive for unit in state.battle.units if unit.team == 'player')
                assert any(unit.alive for unit in state.battle.units if unit.team == 'enemy')
                assert isinstance(game.scene, ResultScene)
                player.capture('control-retinue-hold-victory')
                player.reload(state.to_json())
                gold, crystals = state.gold, state.crystals
                province = state.provinces[state.hero.pos]
                state.resolve_battle()
                assert state.gold == gold + province.site_gold and state.crystals == crystals + province.site_crystals
                while state.choice:
                    state.choose(state.choice.options[0].id)
                assert province.explored
                player.reload(state.to_json())
            elif scenario == 'rally':
                class PinReached(Exception):
                    pass

                class UntilPin(PlayerOrders):
                    def do(self, command, *args, **kwargs):
                        if self.battle.unit(0).pinned:
                            raise PinReached
                        super().do(command, *args, **kwargs)

                prepare_adventure(state=state, support='ranger')
                try:
                    crossing_route(state, 'direct', orders_type=UntilPin)
                except PinReached:
                    pass
                else:
                    raise AssertionError('The real enemy did not Pin the carrier')
                player.reload(state.to_json())
                battle = state.battle
                militia = next(unit for unit in battle.units if unit.can_rally and any(
                    battle.grid.distance(pos, battle.unit(0).pos) == 1 for pos in battle.reachable(unit.id)))
                destination = min(pos for pos in battle.reachable(militia.id) if battle.grid.distance(pos, battle.unit(0).pos) == 1)
                select(militia.id)
                player.click(*game.scene.grid.center(destination))
                forecast = battle.rally_preview(militia.id, 0)
                before, carrier = state.to_json(), asdict(battle.unit(0))
                player.press('q'); player.press('f')
                assert game.scene.cursor == battle.unit(0).pos and state.to_json() == before
                player.capture('rally-restored-route-forecast')
                player.press('escape')
                assert state.to_json() == before
                play = ControlOrders(state)
                play.do('rally', militia.id, 0)
                battle = state.battle
                assert asdict(battle.unit(0)) == {**carrier, 'pinned': False}
                assert battle.reachable(0) == forecast.reachable
                select(0)
                player.capture('rallied-carrier-keeps-order')
            else:
                kind, building = ('sapper', 'market') if scenario == 'smoke' else ('adept', 'mage_tower')
                state.build(building)
                while state.gold < state.recruit_cost(kind):
                    state.end_turn()
                gold, crystals = state.gold, state.crystals
                player.press('r'); player.press('right')
                player.capture('control-recruitment-costs')
                player.press('escape')
                state.recruit(kind)
                assert state.gold == gold - state.recruit_cost(kind)
                assert state.crystals == crystals - state.recruit_crystal_cost(kind)
                state.explore()
                battle = state.battle
                actor = next(unit for unit in battle.units if unit.kind == kind)
                select(actor.id)
                if scenario == 'smoke':
                    before = state.to_json()
                    player.press('d'); player.press('f')
                    assert game.scene.cursor in battle.smoke_targets(actor.id)
                    player.capture('smoke-hex-forecast')
                    player.press('escape')
                    assert state.to_json() == before
                    forecast = battle.smoke_preview(actor.id, actor.pos)
                    player.press('d')
                    player.click(*game.scene.grid.center(actor.pos))
                    assert battle.smoke_clouds == [forecast]
                    assert actor.acted and actor.spent_abilities == ('smoke',)
                    key = 'd'
                else:
                    player.click(*game.scene.grid.center((1, 0)))
                    target = battle.repulse_targets(actor.id)[0]
                    landing = battle.repulse_preview(actor.id, target.id)
                    before, target_before = state.to_json(), asdict(target)
                    player.press('r'); player.press('f')
                    assert game.scene.cursor == target.pos and state.to_json() == before
                    player.capture('repulse-landing-forecast')
                    player.press('return')
                    assert asdict(target) == {**target_before, 'pos': landing}
                    assert actor.acted and actor.spent_abilities == ('repulse',)
                    key = 'r'
                player.reload(state.to_json())
                select(actor.id)
                player.capture('saved-charge-spent')
                before = state.to_json()
                player.press(key)
                assert state.to_json() == before and game.scene.targeting is None
                player.press('e')
                assert not getattr(state.battle, scenario + '_targets')(actor.id)
                if scenario == 'smoke':
                    assert state.battle.smoke_clouds == []
                    player.capture('smoke-expired-charge-still-spent')
            report = dict(scenario=scenario, backend=backend, input_activations=len(player.events),
                          exact_save_reloads=player.reloads, inputs=player.events)
            changed = [str(path.relative_to(ROOT)) for path in sources
                       if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[str(path.relative_to(ROOT))]]
            assert not changed, 'Source changed during native verification'
            report.update(revision=revision, dirty_at_start=dirty, source_sha256=hashes,
                          source_files_changed=changed, elapsed_seconds=perf_counter() - started,
                          python=platform.python_version(), platform=platform.platform())
            (output / 'journey.json').write_text(json.dumps(report, indent=2) + '\n')
            print(f'{scenario}: {len(player.events)} inputs, {player.reloads} exact reloads ({backend})', flush=True)
            return report
        finally:
            game._teardown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-control-orders'))
    parser.add_argument('--scenario', choices=('smoke', 'rally', 'repulse', 'watch', 'sight'), default='smoke')
    args = parser.parse_args()
    verify(args.output, scenario=args.scenario)
