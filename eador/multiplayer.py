"""Shared-realm co-op: both partners issue orders, the host resolves them in order."""
from saga2d import CommandError
from saga2d.server.games import GameSpec, option_choice, option_keys, option_seed
from eador.concurrent_campaign import ConcurrentCampaign
from eador.difficulty import DIFFICULTIES
from eador.model import HERO_CLASSES, State, RuleError
from eador.worldgen import THEMES
from eador.orders import BATTLE_ORDERS, invoke_order

STATE_ORDERS = {'build', 'recruit', 'replace_troop', 'travel', 'explore', 'end_turn', 'choose', 'equip',
                'infuse', 'retreat', 'resolve_battle', 'advance', 'recover', 'abandon_campaign'}


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
        invoke_order(receiver, action, args, kwargs)
        self.state = trial


def _create_coop(options):
    option_keys(options, {'seed', 'hero', 'theme', 'difficulty', 'campaign'})
    campaign = options.get('campaign', False)
    if type(campaign) is not bool:
        raise CommandError('campaign must be true or false.')
    return ShardboundMatch(option_seed(options, 7), hero=option_choice(options, 'hero', 'Commander', HERO_CLASSES),
                           theme=option_choice(options, 'theme', 'frontier', THEMES),
                           difficulty=option_choice(options, 'difficulty', 'standard', DIFFICULTIES),
                           campaign=campaign)


def _restore_coop(snapshot):
    match = ShardboundMatch.__new__(ShardboundMatch)
    match.state = State.from_json(snapshot['campaign'])
    return match


def _create_pvp(options):
    option_keys(options, {'seed', 'heroes', 'theme', 'difficulty'})
    heroes = options.get('heroes', ('Commander', 'Commander'))
    if (not isinstance(heroes, (list, tuple)) or len(heroes) != 2
            or any(not isinstance(hero, str) or hero not in HERO_CLASSES for hero in heroes)):
        raise CommandError('Choose two supported heroes.')
    return ConcurrentCampaign.new(option_seed(options, 7), heroes=heroes,
                                  theme=option_choice(options, 'theme', 'frontier', THEMES),
                                  difficulty=option_choice(options, 'difficulty', 'standard', DIFFICULTIES))


# Campaigns span sessions: their seats survive for days, suspended to storage between visits.
ONLINE = {
    'shardbound-v1': GameSpec(_create_coop, lambda match: {'campaign': match.state.to_json()}, _restore_coop,
                              campaign=True),
    'shardbound-pvp-v1': GameSpec(_create_pvp, ConcurrentCampaign.checkpoint, ConcurrentCampaign.restore,
                                  campaign=True),
}


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
            if getattr(self.session, 'online', False):
                notice = notice or 'Match paused — waiting for your partner to reconnect.'
            else:
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
        raise OrderPending('Order sent.')

    def save_game(self):
        self.message = 'This co-op campaign runs live; offline saves are separate.'

    def load_game(self, slot=1, *, backup=False):
        self.message = ('Use Multiplayer → Rejoin last room to resume online play.'
                        if getattr(self.session, 'online', False) else 'Rejoin the host to resume this co-op campaign.')
        return False

    def browse_saves(self, mode="load"):
        self.save_game()
