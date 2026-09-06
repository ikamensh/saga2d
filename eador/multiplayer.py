"""Shared-realm co-op: both partners issue orders, the host resolves them in order."""
import inspect

from saga2d import CommandError
from eador.model import State, RuleError, BUILDINGS, UNITS
from eador.battle import Battle, SPELLS
from eador.content import RELICS

STATE_ORDERS = {'build', 'recruit', 'replace_troop', 'travel', 'explore', 'end_turn', 'choose', 'equip',
                'infuse', 'retreat', 'resolve_battle', 'advance', 'recover', 'abandon_campaign'}
BATTLE_ORDERS = {'move', 'attack', 'guard', 'pin', 'repulse', 'smoke', 'rally', 'swap', 'cast',
                 'end_turn', 'auto_turn', 'evacuate'}


class ShardboundMatch:
    def __init__(self, seed=7, hero='Commander', *, theme='frontier', difficulty='standard', campaign=False):
        self.state = (State.new_campaign(seed, hero, difficulty=difficulty) if campaign else
                      State.new(seed, hero, theme=theme, difficulty=difficulty))

    def snapshot(self, player):
        return {'campaign': self.state.to_json()}

    def apply(self, player, command):
        if player not in (0, 1):
            raise CommandError('Unknown partner.')
        action, target = command.get('action'), command.get('target')
        allowed = STATE_ORDERS if target == 'state' else BATTLE_ORDERS if target == 'battle' else set()
        args, kwargs = command.get('args'), command.get('kwargs', {})
        if not isinstance(action, str) or action not in allowed or not isinstance(args, list) or not isinstance(kwargs, dict):
            raise CommandError('Invalid Shardbound order.')
        trial = State.from_json(self.state.to_json())
        receiver = trial if target == 'state' else trial.battle
        if receiver is None:
            raise CommandError('There is no active battle.')
        method = getattr(State if target == 'state' else Battle, action)
        try:
            bound = inspect.signature(method).bind(receiver, *args, **kwargs)
        except TypeError as exc:
            raise CommandError('Invalid order arguments.') from exc
        for name, value in list(bound.arguments.items()):
            if name == 'self':
                continue
            if name in ('destination', 'pos'):
                if (not isinstance(value, (tuple, list)) or len(value) != 2
                        or any(type(n) is not int for n in value)):
                    raise CommandError('Choose a hex.')
                bound.arguments[name] = tuple(value)
            elif name in ('unit_id', 'target_id', 'outgoing_id', 'caster_id'):
                if type(value) is not int:
                    raise CommandError('Choose a unit.')
            elif name in ('troop_ids', 'relic_ids'):
                kind = int if name == 'troop_ids' else str
                if not isinstance(value, (tuple, list)) or len(value) > 2 or any(type(item) is not kind for item in value):
                    raise CommandError('Choose up to two veterans or relics.')
            elif value is not None and not isinstance(value, str):
                raise CommandError(f'Invalid {name}.')
        values = bound.arguments
        if 'kind' in values and values['kind'] not in (BUILDINGS if action == 'build' else UNITS):
            raise CommandError('Unknown building or troop.')
        if 'spell' in values and values['spell'] not in SPELLS:
            raise CommandError('Unknown spell.')
        if 'relic_id' in values and values['relic_id'] is not None and values['relic_id'] not in RELICS:
            raise CommandError('Unknown relic.')
        try:
            method(*bound.args, **bound.kwargs)
        except RuleError as exc:
            raise CommandError(str(exc)) from exc
        self.state = trial


from eador.scene import ShardScene, OrderPending, BattleScene, CatalogScene, HeroScene


class NetworkShardScene(ShardScene):
    """Keep the existing complete campaign UI; refresh it from accepted orders."""
    live_match = True

    def __init__(self, session, match=None, *, selection=None):
        self.session = session
        self._revision = session.revision
        self._transferring = False
        super().__init__(State.from_json(session.state['campaign']))
        if selection in self.state.provinces:
            self.selected = selection

    def on_enter(self):
        super().on_enter()
        self.every(1 / 60, self._poll)

    def on_close(self):
        if not self._transferring:
            self.session.close()

    def _poll(self):
        self.session.poll()
        notice = self.session.error
        if not self.session.ready:
            notice = ('Match paused — waiting for your partner.' if self.session.player == 0 else
                      'Disconnected — return to the title and rejoin the host.')
        elif notice:
            self.session.error = ''
        if notice and notice != self.game.scene.message:
            self.game.scene.message = notice
            self.game.scene.refresh()
        if self._revision == self.session.revision:
            return
        game = self.game
        top = game.scene
        selection = self.selected
        next_scene = NetworkShardScene(self.session, selection=selection)
        self._transferring = True
        game.clear_and_push(next_scene)
        # Keep a repeated shopping action or tactical selection in context.
        if isinstance(top, CatalogScene) and game.scene is next_scene:
            game.push(CatalogScene(next_scene, top.kind))
        elif isinstance(top, HeroScene) and game.scene is next_scene:
            game.push(HeroScene(next_scene))
        elif isinstance(top, BattleScene) and isinstance(game.scene, BattleScene):
            battle_scene = game.scene
            if any(u.id == top.selected and u.alive for u in battle_scene.battle.units):
                battle_scene.selected = top.selected
                battle_scene.refresh()

    def order(self, action, *args, target='state', **kwargs):
        try:
            self.session.submit({'action': action, 'target': target, 'args': list(args), 'kwargs': kwargs},
                                revision=self.session.revision)
        except CommandError as exc:
            raise RuleError(str(exc)) from exc
        raise OrderPending('Order sent to the host.')

    def save_game(self):
        self.message = 'Co-op runs live on the host; offline saves are separate.'

    def load_game(self, slot=1, *, backup=False):
        self.message = 'Rejoin the host to resume this co-op campaign.'
        return False

    def browse_saves(self, mode="load"):
        self.save_game()
