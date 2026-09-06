"""Replay paid Aerie plans with exact saves and retain a compressed, source-attributed report."""
import argparse
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.battle import Battle
from eador.model import RuleError, State
from tools.audit_eador_extraction import PaidState
from tools.eador_aerie_campaign import (prepare_aerie, aerie_western_route, aerie_northern_route,
                                       aerie_scout_route, aerie_failed_sortie, aerie_retry_route)
from tools.eador_extraction_campaign import AdventureOrders


class Purchases(PaidState):
    def __init__(self, state):
        super().__init__(state)
        self.purchases = []

    def _buy(self, command, kind):
        gold, crystals = self.gold, self.crystals
        getattr(super(), command)(kind)
        self.purchases.append(dict(command=command, kind=kind, gold=gold-self.gold, crystals=crystals-self.crystals))

    def build(self, kind):
        self._buy('build', kind)

    def recruit(self, kind):
        self._buy('recruit', kind)


def without_flight_reachable(battle, ident):
    """Labelled query counterfactual: same base move, only flight absent; never a played order."""
    clone = Battle.from_dict(battle.to_dict())
    unit = clone.unit(ident)
    clone.units[clone.units.index(unit)] = replace(unit, abilities=tuple(a for a in unit.abilities if a != 'fly'))
    return clone.reachable(ident)


class RecordedOrders(AdventureOrders):
    def __init__(self, state, *, budget=None):
        super().__init__(State.from_json(state.to_json()), budget=budget)
        self.initial = json.loads(self.state.to_json())
        self.snapshots, self.flight_landings = [], []

    def do(self, command, *args, **kwargs):
        b = self.battle
        if command in ('attack', 'pin'):
            attacker, target = (b.unit(uid) for uid in args)
            hp = target.hp, attacker.hp
            forecast = b.preview(*args) if command == 'attack' else b.pin_preview(*args)
        elif command == 'cast':
            target = b.unit(args[1]); hp = target.hp
            forecast = b.spell_preview(*args, **kwargs)
        elif command == 'repulse':
            target = b.unit(args[1]); before = target.__dict__.copy()
            forecast = b.repulse_preview(*args)
        elif command == 'move' and 'fly' in b.unit(args[0]).abilities:
            if args[1] not in without_flight_reachable(b, args[0]):
                self.flight_landings.append(dict(unit=args[0], source=b.unit(args[0]).pos, destination=args[1]))
        super().do(command, *args, **kwargs)
        if command in ('attack', 'pin'):
            assert (hp[0]-target.hp, hp[1]-attacker.hp) == forecast
        elif command == 'cast':
            assert abs(target.hp-hp) == forecast
        elif command == 'repulse':
            assert target.pos == forecast
            assert target.__dict__ == {**before, 'pos':forecast}
        text = self.state.to_json()
        self.state = State.from_json(text)
        assert self.state.to_json() == text
        self.snapshots.append(json.loads(text))

    def report(self):
        b = self.battle
        return dict(initial=self.initial, commands=self.orders, snapshots=self.snapshots,
                    rounds=b.round, reason=b.outcome_reason, orders=len(self.orders), exact_reloads=len(self.snapshots),
                    dead=[u.id for u in b.units if u.team == 'player' and not u.alive],
                    wounds=sum(u.max_hp-u.hp for u in b.units if u.team == 'player'),
                    mana_spent=self.state.hero.mana-b.mana, flight_only_landings=self.flight_landings)


def settle_once(play):
    state = play.state
    gold, crystals, reward = state.gold, state.crystals, state.battle_adventure
    state.resolve_battle()
    assert (state.gold, state.crystals) == (gold+reward.gold, crystals+reward.crystals)
    while state.choice:
        state.choose(state.choice.options[0].id)
    text = state.to_json()
    for command in (state.explore, state.resolve_battle):
        try:
            command()
        except RuleError:
            pass
        else:
            raise AssertionError('The completed Aerie rewarded twice.')
        assert state.to_json() == text
    return json.loads(text)


def measure():
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'),
                      *ROOT.joinpath('tools').glob('eador_*.py'), Path(__file__).resolve(),
                      ROOT/'tools/audit_eador_extraction.py'])
    hashes = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    commander = prepare_aerie(state=Purchases(State.new(7, theme='ruins')))
    scout = prepare_aerie('Scout', party='ground', state=Purchases(State.new(7, 'Scout', theme='ruins')))
    parties = {name:dict(snapshot=json.loads(paid.to_json()), purchases=paid.purchases)
               for name, paid in [('commander',commander), ('scout',scout)]}
    plans = {}
    for name, route, paid in [('western',aerie_western_route,commander),
                              ('northern',aerie_northern_route,commander), ('scout',aerie_scout_route,scout)]:
        play = route(State.from_json(paid.to_json()), orders_type=RecordedOrders)
        plans[name] = play.report()
        assert play.battle.outcome_reason == 'rout' and not plans[name]['dead']
        plans[name]['settled'] = settle_once(play)
    sustain = aerie_western_route(State.from_json(commander.to_json()), heal=True, orders_type=RecordedOrders)
    plans['western-heal'] = {**sustain.report(), 'settled':settle_once(sustain)}
    failure = aerie_failed_sortie(State.from_json(commander.to_json()), orders_type=RecordedOrders)
    plans['failed-sortie'] = failure.report()
    state = failure.state
    gold, crystals, xp = state.gold, state.crystals, state.hero.xp
    state.resolve_battle()
    assert (state.gold,state.crystals,state.hero.xp) == (gold-20,crystals,xp) and state.choice is None
    plans['failed-sortie']['settled'] = json.loads(state.to_json())
    replacement = Purchases(State.from_json(state.to_json())); replacement.recruit('skyrider')
    retry = aerie_retry_route(replacement, orders_type=RecordedOrders)
    plans['retry'] = {**retry.report(), 'purchases':replacement.purchases, 'settled':settle_once(retry)}
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items())
    return dict(source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source_sha256=hashes, python=platform.python_version(), platform=platform.platform(),
                parties=parties, plans=plans, scope='Actual seed-seven Standard purchases and manual model orders; no native or optimal-play claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/aerie-production.json.gz'))
    args = parser.parse_args()
    report = measure()
    payload = (json.dumps(report, separators=(',', ':'))+'\n').encode()
    args.output.write_bytes(gzip.compress(payload,mtime=0) if args.output.suffix == '.gz' else payload)
    for name, plan in report['plans'].items():
        print(name,plan['reason'],'round',plan['rounds'],'wounds',plan['wounds'],'mana',plan['mana_spent'],
              'orders/reloads',plan['orders'],plan['exact_reloads'])


if __name__ == '__main__':
    main()
