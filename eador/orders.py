"""Argument validation shared by Shardbound's authoritative match adapters."""
import inspect

from saga2d import CommandError
from eador.battle import SPELLS
from eador.content import RELICS
from eador.entities import BUILDINGS, UNITS, RuleError


BATTLE_ORDERS = {'move', 'attack', 'guard', 'pin', 'repulse', 'smoke', 'rally', 'swap', 'cast',
                 'end_turn', 'auto_turn', 'evacuate'}


def invoke_order(receiver, action, args, kwargs):
    """Invoke an allowed order, translating invalid arguments and game rules.

    The caller owns action authorization, argument-container validation and
    atomic state replacement; this function acts on its supplied receiver.
    """
    method = getattr(type(receiver), action)
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
        return method(*bound.args, **bound.kwargs)
    except RuleError as exc:
        raise CommandError(str(exc)) from exc
