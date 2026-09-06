#!/usr/bin/env python3
"""THROWAWAY: does split deployment create a useful rescue problem?

Run with Python from this checkout; --verbose prints each public order and state.
This registers one temporary layout in memory while constructing Battle, then
removes it. It does not add a site, price, reward, schema or production rule.
Delete or absorb this prototype after the design decision.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.battle import Battle
from eador.encounters import ENCOUNTERS, EncounterSpec
from eador.model import State
from tools.audit_eador_extraction import PaidState
from tools.eador_extraction_campaign import prepare_adventure


MARSH = {(0, -1), (0, 0), (0, 1), (-1, 0)}
FOREST = {(-1, -1), (1, 1), (-2, 2)}
LAYOUT = EncounterSpec(
    'PROTOTYPE Stranded Explorer',
    tuple(((q, r), 'marsh' if (q, r) in MARSH else 'forest' if (q, r) in FOREST else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((3, -1), (-3, 0), (-3, 1), (-2, -1), (-2, 0), (2, -1), (-2, 1)),
    ((1, 0), (1, -2), (0, 2), (-1, 2), (2, 0), (2, 1), (3, -3)),
    exits=((-3, 1),), deadline=6, objective='extract',
)
SOUTH = replace(LAYOUT, player_positions=(
    (3, -1), (-2, 3), (-1, 3), (-2, 2), (-2, 1), (2, -1), (-3, 3)))


def battle_for(state, layout=LAYOUT):
    name = '_prototype_stranded_explorer'
    assert name not in ENCOUNTERS
    ENCOUNTERS[name] = layout
    try:
        return Battle.create(state.hero, ['pikeman', 'archer', 'guard', 'warden'],
                             'plains', state.spells, encounter=name)
    finally:
        del ENCOUNTERS[name]


class Probe:
    def __init__(self, battle, verbose=False):
        self.battle, self.orders, self.verbose = battle, [], verbose

    def do(self, command, *args):
        battle = self.battle
        if command == 'attack':
            actor, target = (battle.unit(uid) for uid in args)
            hp, forecast = (target.hp, actor.hp), battle.preview(*args)
        getattr(battle, command)(*args)
        if command == 'attack':
            assert (hp[0] - target.hp, hp[1] - actor.hp) == forecast
        self.orders.append((command, args))
        saved = json.dumps(battle.to_dict(), sort_keys=True)
        self.battle = Battle.from_dict(json.loads(saved))
        assert json.dumps(self.battle.to_dict(), sort_keys=True) == saved
        if self.verbose:
            print(command, args, self.summary())

    def end(self):
        for unit in self.battle.units:
            if unit.team == 'player' and unit.alive and not unit.acted:
                self.do('guard', unit.id)
        self.do('end_turn')

    def summary(self):
        return dict(round=self.battle.round, outcome=self.battle.outcome_reason,
                    mana=self.battle.mana,
                    units=[dict(id=u.id, team=u.team, kind=u.kind, pos=u.pos, hp=u.hp,
                                max_hp=u.max_hp, pinned=u.pinned) for u in self.battle.units])


def rescue(play):
    defenders = {u.kind: u.id for u in play.battle.units if u.team == 'enemy'}
    # The occupied bowman's hex blocks the Ranger's short road west. Shooting
    # before the hero finishes it retains the Ranger's move for that cleared road.
    assert (0, -2) not in play.battle.reachable(5)
    play.do('attack', 5, defenders['archer'])
    play.do('move', 0, (2, -2)); play.do('attack', 0, defenders['archer'])
    assert (0, -2) in play.battle.reachable(5)
    play.do('move', 5, (0, -2))
    play.do('move', 3, (-1, -1)); play.do('attack', 3, defenders['pikeman'])
    for uid, pos in ((4, (-1, 0)), (1, (-1, 1)), (2, (-2, 2))):
        play.do('move', uid, pos)
    play.end()
    # The Ranger vacates the northern road before the hero crosses. The other
    # wing screens both approaches to the return exit instead of pursuing rout.
    for uid, pos in ((5, (-2, -1)), (0, (-1, -2)), (1, (-3, 2)), (3, (-2, 1))):
        play.do('move', uid, pos)
    play.do('attack', 3, defenders['guard'])
    play.do('move', 4, (-3, 1))
    play.end()
    play.do('attack', 5, defenders['pikeman']); play.do('move', 5, (0, -2))
    play.do('move', 0, (-3, 0)); play.do('swap', 4, 0); play.do('evacuate')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    prepared = prepare_adventure(support='ranger', state=PaidState(State.new(7)))
    rows = []
    for name, layout, manual in (
        ('north rescue', LAYOUT, True), ('north auto', LAYOUT, False), ('south auto', SOUTH, False),
    ):
        play = Probe(battle_for(prepared, layout), args.verbose)
        if manual:
            rescue(play)
            assert play.battle.outcome_reason == 'escape'
        else:
            while play.battle.outcome is None:
                play.do('auto_turn')
        row = dict(plan=name, **play.summary(), orders=play.orders,
                   battle_log=list(play.battle.log),
                   hp_deficit=sum(u.max_hp-u.hp for u in play.battle.units if u.team == 'player'),
                   player_deaths=sum(not u.alive for u in play.battle.units if u.team == 'player'),
                   enemy_survivors=sum(u.alive for u in play.battle.units if u.team == 'enemy'),
                   mana_spent=prepared.hero.mana-play.battle.mana)
        rows.append(row)
        print(name, {k: row[k] for k in ('outcome', 'round', 'hp_deficit', 'mana_spent', 'player_deaths', 'enemy_survivors')})
    if args.report:
        sources = sorted([*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'),
                          ROOT/'tools/eador_extraction_campaign.py', ROOT/'tools/eador_campaign.py',
                          ROOT/'tools/audit_eador_extraction.py', Path(__file__).resolve()])
        report = dict(prototype_only=True, python=platform.python_version(), platform=platform.platform(),
                      revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                      source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                      preparation=dict(campaign_turn=prepared.turn, hero_level=prepared.hero.level,
                                       building_gold=prepared.building_gold, recruitment_gold=prepared.recruitment_gold,
                                       hero=json.loads(prepared.to_json())['hero']),
                      layout=dict(terrain=LAYOUT.terrain, player_positions=LAYOUT.player_positions,
                                  enemy_positions=LAYOUT.enemy_positions, exits=LAYOUT.exits, deadline=LAYOUT.deadline),
                      journeys=rows)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')


if __name__ == '__main__':
    main()
