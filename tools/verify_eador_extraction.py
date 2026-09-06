"""Buy an army, compare an adventure approach, then manually evacuate through native controls."""
import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SAGA2D_SILENT'] = '1'

from eador.app import create_game
from eador.scene import BattleScene, ChoiceScene, ResultScene, TitleScene
from tools.eador_extraction_campaign import AdventureOrders, prepare_adventure, crossing_route, cache_route
from tools.eador_ui import PlayerInput


class PlayerOrders(AdventureOrders):
    """Replay the same public route through buttons, aimed keys and map clicks."""
    def __init__(self, state):
        super().__init__(state)
        self.player = state.player
        self.player.capture('entered-adventure')
        before = state.to_json()
        self.player.press('v')
        assert state.to_json() == before, 'A disabled Evacuate shortcut changed play'
        for pos in self.battle.objective.exits:
            self.player.press('o')
            assert self.player.game.scene.cursor == pos
        assert state.to_json() == before, 'Locating an exit spent an order'
        self.player.reload(before)

    def select(self, ident):
        self.player.click(*self.player.game.scene.grid.center(self.battle.unit(ident).pos))
        assert self.player.game.scene.selected == ident

    def aim(self, ident):
        pos = self.battle.unit(ident).pos
        for _ in self.battle.units:
            if self.player.game.scene.cursor == pos:
                return
            self.player.press('f')
        raise AssertionError('The requested legal target was not reachable by F')

    def do(self, command, *args, **kwargs):
        battle = self.battle
        forecast = None
        if command in ('attack', 'pin'):
            attacker, target = (battle.unit(ident) for ident in args)
            before = target.hp, attacker.hp
            forecast = getattr(battle, 'preview' if command == 'attack' else 'pin_preview')(*args)
        elif command == 'cast':
            target = battle.unit(args[1])
            before = target.hp
            forecast = battle.spell_preview(*args, **kwargs)
        if command in ('move', 'attack', 'pin', 'swap', 'guard'):
            self.select(args[0])
        if command in ('move', 'attack'):
            pos = args[1] if command == 'move' else battle.unit(args[1]).pos
            self.player.click(*self.player.game.scene.grid.center(pos))
        elif command in ('pin', 'swap'):
            self.player.press('p' if command == 'pin' else 's')
            self.aim(args[1])
            self.player.capture(f'round-{battle.round}-{command}-forecast')
            self.player.press('return')
        elif command == 'cast':
            self.select(kwargs.get('caster_id') or 0)
            self.player.press('1' if args[0] == 'bolt' else '2')
            self.aim(args[1])
            self.player.capture(f'round-{battle.round}-{args[0]}-forecast')
            self.player.press('return')
        elif command == 'guard':
            self.player.press('g')
        elif command == 'end_turn':
            self.player.press('e')
        elif command == 'evacuate':
            assert battle.outcome is None and battle.evacuation_blocked_reason is None
            self.select(0)
            self.player.capture('ready-to-evacuate')
            self.player.press('v')
            assert isinstance(self.player.game.scene, ResultScene)
            self.player.capture('cargo-safe')
        else:
            raise AssertionError(f'No input adapter for {command!r}')
        if command in ('attack', 'pin'):
            assert (before[0] - target.hp, before[1] - attacker.hp) == forecast
        elif command == 'cast':
            assert abs(target.hp - before) == forecast
        self.orders.append((command, args, kwargs))
        if command in ('end_turn', 'swap', 'evacuate'):
            self.player.reload(self.state.to_json())


def verify(output, *, backend='pyglet', theme='frontier', approach='guided', hero_class='Commander', player_type=PlayerInput):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='shardbound-escape-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = player_type(game, native=backend == 'pyglet', output=output)
        try:
            game.push(TitleScene(7, hero_class=hero_class, theme=theme))
            player.press('return')
            state = prepare_adventure(theme=theme, support='ranger' if approach == 'direct' else 'healer', state=player.state)
            gold, crystals = state.gold, state.crystals
            selected = next(choice for choice in state.adventure_approaches() if choice.id == approach)
            route = crossing_route if theme == 'frontier' else cache_route
            play = route(state, approach, orders_type=PlayerOrders)
            battle, reward = state.battle, state.battle_adventure
            assert battle.outcome_reason == 'escape' and any(u.alive and u.team == 'enemy' for u in battle.units)
            assert all(u.alive for u in battle.units if u.team == 'player')
            assert state.gold == gold - selected.gold_cost
            assert state.crystals == crystals - selected.crystals_cost
            rounds, destination = battle.round, state.hero.pos
            before_gold, before_crystals = state.gold, state.crystals
            state.resolve_battle()
            assert state.gold == before_gold + reward.gold and state.crystals == before_crystals + reward.crystals
            while isinstance(game.scene, ChoiceScene):
                player.press('1')
            assert state.provinces[destination].explored
            before = state.to_json()
            player.press('x')
            assert state.to_json() == before and not isinstance(game.scene, BattleScene)
            report = dict(theme=theme, approach=approach, hero=hero_class, backend=backend, battle_rounds=rounds,
                          fee_gold=selected.gold_cost, fee_crystals=selected.crystals_cost,
                          reward_gold=reward.gold, reward_crystals=reward.crystals, input_activations=len(player.events),
                          exact_save_reloads=player.reloads, orders=play.orders, inputs=player.events)
            (output / 'journey.json').write_text(json.dumps(report, indent=2) + '\n')
            print(f'{theme}/{approach}: escaped in round {rounds}, {len(player.events)} inputs, '
                  f'{player.reloads} exact reloads ({backend})', flush=True)
            return report
        finally:
            game._teardown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-extraction'))
    parser.add_argument('--theme', choices=('frontier', 'elderwild'), default='frontier')
    parser.add_argument('--approach', choices=('direct', 'guided', 'light', 'full'), default='guided')
    parser.add_argument('--hero', choices=('Commander', 'Warrior', 'Scout', 'Wizard'), default='Commander')
    args = parser.parse_args()
    if (args.theme == 'frontier') != (args.approach in ('direct', 'guided')):
        parser.error('Use direct/guided for Frontier or light/full for Elderwild.')
    verify(args.output, theme=args.theme, approach=args.approach, hero_class=args.hero)
