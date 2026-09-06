"""Two human tribes, validated orders and the existing map presentation."""
from copy import deepcopy

from saga2d import CommandError
from tribes import mapgen
from tribes.model import World, RuleError
from tribes.rules import UnitType, Tech, Reward


class TribesMatch:
    def __init__(self, seed=7, size=14):
        self.seed = seed
        self.world = mapgen.generate(seed, size=size, tribe_count=2)
        for tribe in self.world.tribes:
            tribe.human = True

    def snapshot(self, player):
        return {'seed': self.seed, 'world': deepcopy(self.world.to_dict())}

    def apply(self, player, command):
        if player != self.world.current or self.world.winner is not None:
            raise CommandError('It is not your turn, or the match is over.')
        # Commit the whole order only after the rules accept it.
        world = World.from_dict(deepcopy(self.world.to_dict()))
        def own(collection, field):
            key = command.get(field)
            item = collection.get(key) if type(key) is int else None
            if item is None or item.tribe != player:
                raise CommandError(f'Choose your own {field}.')
            return item
        def pos():
            value = command.get('pos')
            if not isinstance(value, (list, tuple)) or len(value) != 2 or any(type(n) is not int for n in value):
                raise CommandError('Choose a map tile.')
            if not world.in_bounds(value):
                raise CommandError('That tile is outside the map.')
            return tuple(value)
        try:
            action = command.get('action')
            if action == 'end_turn':
                world.end_turn()
            elif action == 'move':
                world.move(own(world.units, 'unit'), pos())
            elif action == 'attack':
                target_id = command.get('target')
                target = world.units.get(target_id) if type(target_id) is int else None
                if target is None:
                    raise CommandError('Choose an enemy unit.')
                world.attack(own(world.units, 'unit'), target)
            elif action == 'capture':
                world.capture(own(world.units, 'unit'))
            elif action == 'hold':
                own(world.units, 'unit').done = True
            elif action == 'train':
                world.train(own(world.cities, 'city'), UnitType(command.get('kind')))
            elif action == 'harvest':
                world.harvest(player, pos())
            elif action == 'research':
                world.research(player, Tech(command.get('tech')))
            elif action == 'reward':
                world.choose_reward(own(world.cities, 'city'), Reward(command.get('reward')))
            else:
                raise CommandError('Unknown Tribes order.')
        except (RuleError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.world = world


from tribes.scene import MapScene, TechScene, RewardScene


class NetworkMapScene(MapScene):
    def __init__(self, session, match=None):
        self.session = session
        self._revision = session.revision
        data = session.state
        super().__init__(World.from_dict(data['world']), data['seed'], player=session.player)

    def on_enter(self):
        super().on_enter()
        self.every(1 / 60, self._poll)

    def on_close(self):
        self.session.close()

    def _poll(self):
        self.session.poll()
        if self.session.error and self.session.ready:
            self.say(self.session.error)
            self.session.error = ""
        if not self.session.ready:
            self.say('Match paused — waiting for your partner.' if self.session.player == 0 else
                     'Disconnected — return to the title and rejoin the host.')
        if self._revision == self.session.revision:
            return
        self._revision = self.session.revision
        fresh = World.from_dict(self.session.state['world'])
        # HUD callbacks retain the world and tribe objects, so update their contents.
        for old, new in zip(self.world.tribes, fresh.tribes):
            old.__dict__.update(new.__dict__)
        fresh.tribes = self.world.tribes
        self.world.__dict__.update(fresh.__dict__)
        self._refresh_selection()
        self.view.sync()
        if isinstance(self.game.scene, (TechScene, RewardScene)):
            self.game.pop()
        self._check_game_over()

    def _submit_order(self, action, **fields):
        try:
            self.session.submit({'action': action, **fields}, revision=self.session.revision)
        except CommandError as exc:
            self.warn(str(exc))
            return False
        return True

    def _turn_banner(self):
        self.say(f'Multiplayer · You command {self.tribe.name}')

    def update(self, dt):
        super().update(dt)
        self.btn_end_turn.enabled = self.session.ready and self.world.current == self.human and self.world.winner is None

    def _score_text(self):
        turn = 'Your turn' if self.world.current == self.human else 'Opponent’s turn'
        return f'{turn} · {self.world.score(self.human)} points'

    def _move_selected(self, pos):
        if self.selected:
            self._submit_order('move', unit=self.selected.id, pos=list(pos))

    def _attack_selected(self, target):
        if self.selected:
            self._submit_order('attack', unit=self.selected.id, target=target.id)

    def capture(self):
        unit = self.selected or self.world.unit_at(self.cursor)
        if unit:
            self._submit_order('capture', unit=unit.id)

    def hold_unit(self):
        if self.selected:
            self._submit_order('hold', unit=self.selected.id)

    def train(self, unit_type):
        city = self._city()
        if city:
            self._submit_order('train', city=city.id, kind=unit_type.value)

    def harvest(self, pos):
        self._submit_order('harvest', pos=list(pos))

    def end_turn(self):
        if self.world.pending_rewards(self.human):
            self._offer_reward()
        else:
            self._submit_order('end_turn')

    def research(self, tech):
        return self._submit_order('research', tech=tech.value)

    def choose_reward(self, city, reward):
        return self._submit_order('reward', city=city.id, reward=reward.value)

    def quick_save(self):
        self.say('Multiplayer runs live on the host; offline saves are separate.')

    def quick_load(self):
        self.say('Rejoin the host to resume this multiplayer match.')

    def open_tech(self):
        if self.session.ready and self.world.current == self.human:
            super().open_tech()

    def _offer_reward(self):
        if self.session.ready and self.world.current == self.human:
            super()._offer_reward()
