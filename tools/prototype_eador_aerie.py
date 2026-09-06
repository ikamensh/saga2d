"""THROWAWAY: does a flying raid demand landing control instead of a front line?

No production content or world is changed. Compare two purchased parties using
ordinary Battle orders. Delete/absorb after the design decision.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import subprocess

from eador.battle import Battle
from eador.content import RELICS
from eador.encounters import ENCOUNTERS, EncounterSpec
from eador.model import State
from eador.worldgen import generate, THEMES
from tools.audit_eador_extraction import PaidState
from tools.eador_control_campaign import prepare_control_watch


AERIE = EncounterSpec(
    'PROTOTYPE Aerie Raid',
    tuple(((q, r), 'marsh' if (q in (-1, 0) and (q, r) != (-1, 0)) or (q, r) in {(1, 0), (1, 1)} else
           'hills' if (q, r) in {(1, -1), (2, -1)} else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((-3, 0), (-1, 0), (-2, 0), (-3, 1), (-3, 2), (-2, 2), (-1, 1)),
    ((1, -2), (1, 1), (2, -1), (1, -1), (3, -1), (2, 1), (3, -3)),
)
ENEMIES = ['skyrider', 'skyrider', 'archer', 'pikeman']
PARTIES = {'flight': ('pikeman', 'adept', 'skyrider'),
           'ground': ('pikeman', 'warden', 'archer')}


def prepare(party):
    paid = Purchases(State.new(7))
    prepare_control_watch(paid, kinds=PARTIES[party])
    return paid


class Purchases(PaidState):
    def __init__(self, state):
        super().__init__(state)
        self.purchases = []

    def buy(self, command, kind):
        gold, crystals = self.gold, self.crystals
        getattr(super(), command)(kind)
        self.purchases.append(dict(command=command, kind=kind, gold=gold-self.gold,
                                   crystals=crystals-self.crystals))

    def build(self, kind):
        self.buy('build', kind)

    def recruit(self, kind):
        self.buy('recruit', kind)


def create(paid):
    assert '_tenth_probe' not in ENCOUNTERS
    ENCOUNTERS['_tenth_probe'] = AERIE
    try:
        return Battle.create(paid.hero, ENEMIES, 'plains', paid.spells, encounter='_tenth_probe')
    finally:
        del ENCOUNTERS['_tenth_probe']


def show(battle):
    print('ROUND', battle.round, battle.outcome_reason, 'MANA', battle.mana)
    for u in battle.units:
        print(u.id, u.team, u.kind, u.pos, f'{u.hp}/{u.max_hp}',
              'moved', u.moved, 'acted', u.acted, 'stance', u.stance,
              'pin', u.pinned, 'spent', u.spent_abilities)
    print('\n'.join(battle.log[-8:]))


def ground_reachable(battle, ident):
    """A labelled counterfactual query, never part of a played route."""
    clone = Battle.from_dict(battle.to_dict())
    index = next(i for i, unit in enumerate(clone.units) if unit.id == ident)
    unit = clone.units[index]
    clone.units[index] = replace(unit, abilities=tuple(ability for ability in unit.abilities if ability != 'fly'))
    return clone.reachable(ident)


class Orders:
    def __init__(self, battle, *, verbose=False):
        self.battle, self.verbose = battle, verbose
        self.initial, self.commands, self.flight_landings = battle.to_dict(), [], []

    def do(self, command, *args):
        b, forecast = self.battle, None
        if command in ('attack', 'pin'):
            forecast = (b.preview if command == 'attack' else b.pin_preview)(*args)
            own_hp, enemy_hp = (b.unit(uid).hp for uid in args)
        elif command == 'cast':
            forecast, old_hp = b.spell_preview(*args), b.unit(args[1]).hp
        elif command == 'repulse':
            forecast, target_before = b.repulse_preview(*args), asdict(b.unit(args[1]))
        elif command == 'move':
            uid, pos = args
            assert pos in b.reachable(uid)
            if b.unit(uid).can_fly and pos not in ground_reachable(b, uid):
                self.flight_landings.append(dict(unit=uid, source=b.unit(uid).pos, destination=pos))
        getattr(b, command)(*args)
        if command in ('attack', 'pin'):
            assert forecast == (enemy_hp-b.unit(args[1]).hp, own_hp-b.unit(args[0]).hp)
        elif command == 'cast':
            assert forecast == abs(b.unit(args[1]).hp-old_hp)
        elif command == 'repulse':
            assert asdict(b.unit(args[1])) == {**target_before, 'pos': forecast}
        raw = json.dumps(b.to_dict(), sort_keys=True)
        self.battle = Battle.from_dict(json.loads(raw))
        assert self.battle.to_dict() == b.to_dict()
        self.commands.append(dict(command=command, args=args, forecast=forecast,
                                  saved_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                                  state=self.battle.to_dict()))
        if self.verbose:
            show(self.battle)

    def run(self, commands):
        for command, *args in commands:
            self.do(command, *args)

    def guard_end(self):
        for unit in list(self.battle.units):
            if unit.alive and unit.team == 'player' and not unit.acted:
                self.do('guard', unit.id)
        self.do('end_turn')

    def report(self):
        party = [u for u in self.battle.units if u.team == 'player']
        return dict(outcome=self.battle.outcome, reason=self.battle.outcome_reason,
                    round=self.battle.round, dead=[u.id for u in party if not u.alive],
                    missing_hp_including_dead=sum(u.max_hp-u.hp for u in party),
                    mana_spent=self.initial['mana']-self.battle.mana,
                    order_count=len(self.commands), orders=self.commands,
                    flight_only_landings=self.flight_landings,
                    initial=self.initial, final=self.battle.to_dict())


def flight(paid, *, heal=False):
    p = Orders(create(paid)); p.guard_end()
    p.run([('attack',3,1007), ('move',5,(-3,3)), ('repulse',5,1007),
           ('move',4,(-2,3)), ('guard',4), ('move',2,(-2,2)),
           ('move',6,(2,0)), ('attack',6,1008), ('cast','heal',1)])
    p.guard_end()
    assert p.battle.unit(5).hp == 22 and p.battle.unit(4).hp == 21
    p.run([('attack',5,1007), ('attack',4,1007)])
    if heal:
        p.run([('attack',1,1006), ('attack',3,1006), ('attack',6,1008), ('cast','heal',1)])
        p.guard_end()
        p.run([('attack',3,1009), ('cast','bolt',1009)])
    else:
        p.run([('attack',3,1006), ('move',6,(1,-1)), ('attack',6,1006),
               ('move',1,(0,-1)), ('guard',1), ('move',2,(-1,1)), ('attack',2,1009),
               ('move',0,(-1,0)), ('cast','bolt',1008)])
        p.guard_end()
        p.run([('attack',3,1009), ('attack',0,1009)])
    assert p.battle.outcome_reason == 'rout' and all(u.alive for u in p.battle.units if u.team == 'player')
    return p


def ground(paid):
    p = Orders(create(paid)); p.guard_end()
    p.run([('move',5,(-1,2)), ('swap',5,6), ('move',2,(-2,2)), ('attack',2,1007),
           ('move',4,(-3,3)), ('attack',4,1007), ('attack',3,1007),
           ('move',0,(-2,0)), ('cast','heal',6)])
    p.guard_end()
    p.run([('move',5,(0,0)), ('attack',5,1006), ('attack',3,1006), ('attack',6,1008),
           ('move',2,(-1,1)), ('cast','heal',6)])
    p.guard_end()
    p.run([('move',0,(-2,-1)), ('cast','heal',1), ('attack',1,1009),
           ('move',3,(-1,-1)), ('attack',3,1008), ('move',5,(1,-1)),
           ('attack',5,1008), ('attack',6,1008)])
    assert p.battle.outcome_reason == 'rout' and all(u.alive for u in p.battle.units if u.team == 'player')
    return p


def premature_flight(paid):
    p = Orders(create(paid))
    p.run([('move',6,(2,0)), ('attack',6,1008)])
    p.guard_end()
    assert not p.battle.unit(6).alive and p.battle.outcome is None
    return p


def no_repulse(paid):
    p = Orders(create(paid)); p.guard_end()
    p.run([('attack',3,1007), ('move',4,(-3,3)), ('guard',4),
           ('move',6,(2,0)), ('attack',6,1008), ('cast','heal',1)])
    p.guard_end()
    assert p.battle.unit(5).hp < 22 and p.battle.unit(4).hp == 28
    return p


def auto_baseline(paid):
    p = Orders(create(paid))
    for _ in range(80):
        if p.battle.outcome:
            return p
        p.do('auto_turn')
    raise AssertionError('Automatic baseline did not finish.')


def source_audit():
    fixed = {'frontier': {(0,2):'courier_crossing', (-1,1):'muster_yard', (0,-1):'stranded_explorer'},
             'elderwild': {(-1,-1):'supply_cache', (-1,1):'pack_hunt', (0,-1):'smuggler_screen'},
             'ruins': {(-1,1):'sealed_vault', (-1,0):'broken_observatory'}}
    for seed in range(100):
        rewards = set()
        for theme in THEMES:
            world = generate(seed, theme)
            for pos, kind in {(-2,0):'shrine', (-2,2):'den', (-1,2):'explorer_camp', **fixed[theme]}.items():
                assert world[pos].site_kind == kind
            assert any(p.site_kind == 'border_watch' for p in world.values())
            rewards.update(p.site_relic for p in world.values() if p.site_relic)
        assert rewards == set(RELICS)
    return dict(seeds_per_theme=100, themes=list(THEMES), relic_union=sorted(RELICS),
                production_placement_changed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/aerie-prototype.json'))
    parser.add_argument('--interactive', choices=PARTIES)
    args = parser.parse_args()
    if args.interactive:
        p = Orders(create(prepare(args.interactive)), verbose=True)
        show(p.battle)
        print('Enter a JSON command, e.g. ["move",6,[2,0]], ["end_turn"], or q.')
        while (line := input('order> ')) != 'q':
            command, *values = json.loads(line)
            p.do(command, *(tuple(value) if isinstance(value,list) else value for value in values))
        return
    root = Path(__file__).resolve().parents[1]
    sources = sorted([*root.joinpath('eador').glob('*.py'), *root.joinpath('saga2d').rglob('*.py'),
                      *root.joinpath('tools').glob('eador_*.py'),
                      root/'tools/prototype_eador_aerie.py', root/'tools/audit_eador_extraction.py'])
    hashes = {str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    parties = {name:prepare(name) for name in PARTIES}
    snapshots = {name:paid.to_json() for name,paid in parties.items()}
    plays = {'flight-control':flight(parties['flight']), 'flight-heal':flight(parties['flight'],heal=True),
             'ground-escort':ground(parties['ground']), 'premature-flight':premature_flight(parties['flight']),
             'no-repulse':no_repulse(parties['flight']),
             'flight-auto':auto_baseline(parties['flight']), 'ground-auto':auto_baseline(parties['ground'])}
    for name,paid in parties.items():
        assert snapshots[name] == paid.to_json()
    b = create(parties['flight'])
    assert (-2,3) in b.reachable(1007) and (-2,3) not in ground_reachable(b,1007)
    assert (2,0) in b.reachable(6) and (2,0) not in ground_reachable(b,6)
    report = dict(source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
                  source_sha256=hashes, layout=asdict(AERIE), enemies=ENEMIES, source_audit=source_audit(),
                  parties={name:dict(snapshot=json.loads(snapshots[name]), purchases=paid.purchases)
                           for name,paid in parties.items()},
                  plans={name:play.report() for name,play in plays.items()},
                  ability_counterfactual='Same initial unit with only fly removed cannot reach either recorded landing; this is a query, not a played order.')
    assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items())
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    for name,p in plays.items():
        r=p.report(); print(name,r['reason'],r['round'],'dead',r['dead'],'HP',r['missing_hp_including_dead'],
                            'mana',r['mana_spent'],'orders',r['order_count'],'flight-only',r['flight_only_landings'])


if __name__ == '__main__':
    main()
