"""The dedicated server's game catalog; no game knowledge lives in the transport."""
from saga2d import CommandError

GAME_IDS = ('tribes-v1', 'warband-v1', 'shardbound-v1')


def create_match(game, options):
    """Validate resource-bounded creation options before constructing any world."""
    if not isinstance(options, dict):
        raise CommandError('Match options must be an object.')
    allowed = {'seed'} | {
        'tribes-v1': {'size'},
        'warband-v1': {'width', 'height', 'theme'},
        'shardbound-v1': {'hero', 'theme', 'difficulty', 'campaign'},
    }[game]
    if options.keys() - allowed:
        raise CommandError('Unknown match option.')

    def integer(name, default, low, high):
        value = options.get(name, default)
        if type(value) is not int or not low <= value <= high:
            raise CommandError(f'{name} must be an integer from {low} to {high}.')
        return value

    def choice(name, default, values):
        value = options.get(name, default)
        if not isinstance(value, str) or value not in values:
            raise CommandError(f'Unknown {name}.')
        return value

    seed = integer('seed', 3 if game == 'warband-v1' else 7, -(2**31), 2**31 - 1)
    if game == 'tribes-v1':
        from tribes.multiplayer import TribesMatch
        return TribesMatch(seed, size=integer('size', 14, 11, 18))
    if game == 'warband-v1':
        from warband.multiplayer import WarbandMatch
        from warband.rules import MapTheme
        return WarbandMatch(seed, width=integer('width', 48, 40, 64),
                            height=integer('height', 40, 32, 48),
                            theme=MapTheme(choice('theme', 'summer', {t.value for t in MapTheme})))
    from eador.multiplayer import ShardboundMatch
    from eador.model import HERO_CLASSES
    from eador.worldgen import THEMES
    from eador.difficulty import DIFFICULTIES
    campaign = options.get('campaign', False)
    if type(campaign) is not bool:
        raise CommandError('campaign must be true or false.')
    return ShardboundMatch(seed, hero=choice('hero', 'Commander', HERO_CLASSES),
                          theme=choice('theme', 'frontier', THEMES),
                          difficulty=choice('difficulty', 'standard', DIFFICULTIES),
                          campaign=campaign)


def restore_match(game, snapshot):
    """Rebuild authoritative rules from trusted JSON, without regenerating any map."""
    if game == 'tribes-v1':
        from tribes.multiplayer import TribesMatch
        from tribes.model import World
        match = TribesMatch.__new__(TribesMatch)
        match.seed, match.world = snapshot['seed'], World.from_dict(snapshot['world'])
    elif game == 'warband-v1':
        from warband.multiplayer import WarbandMatch
        from warband.model import World
        match = WarbandMatch.__new__(WarbandMatch)
        match.seed, match.world = snapshot['seed'], World.from_dict(snapshot['world'])
        match.events = snapshot['events']
        match.event_id = max((event[0] for event in match.events), default=0)
    elif game == 'shardbound-v1':
        from eador.multiplayer import ShardboundMatch
        from eador.model import State
        match = ShardboundMatch.__new__(ShardboundMatch)
        match.state = State.from_json(snapshot['campaign'])
    else:
        raise ValueError(f'Checkpoint belongs to an incompatible game version: {game}')
    return match
