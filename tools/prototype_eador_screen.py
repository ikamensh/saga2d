"""Throwaway ninth-encounter comparison. No production sites or rules are changed.

Run: PYTHONPATH=. python tools/prototype_eador_screen.py --output /tmp/screen.json
Delete/absorb this probe after its selected layout receives production journeys.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from eador.battle import Battle
from eador.encounters import ENCOUNTERS, EncounterSpec
from eador.model import State
from tools.eador_explorer_campaign import prepare_explorer

POSITIONS = ((-3, 0), (-2, 0), (-3, 1), (-2, -1), (-3, 2), (-2, 1), (-3, 3))
ANCHOR = EncounterSpec(
    'PROTOTYPE Caravan Anchor',
    tuple(((q, r), 'forest' if (q, r) in {(-1, -1), (-1, 1), (0, -2), (0, 2), (1, 1)}
           else 'hills' if (q, r) in {(0, 0), (0, -1)} else 'marsh' if (q, r) == (0, 1) else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    POSITIONS, ((1, 0), (1, -1), (2, -1), (1, 1), (2, 0), (3, -1), (3, -3)),
)
SCREEN = EncounterSpec(
    'PROTOTYPE Smuggler Screen',
    tuple(((q, r), 'forest' if (q, r) in {(-1, -1), (0, 1), (1, -2)}
           else 'hills' if (q, r) in {(1, 0), (2, -1)} else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    POSITIONS, ((1, 0), (2, -1), (1, -1), (2, 0), (1, 1), (2, -2), (3, -1)),
)
KINDS = {'anchor': ['pikeman', 'pikeman', 'archer', 'warden'],
         'screen': ['sapper', 'archer', 'archer', 'warden', 'guard']}


class Purchases:
    """Record actual public purchases without changing preparation behavior."""
    def __init__(self):
        self.state = State.new(7)
        self.purchases = []

    def __getattr__(self, name):
        method = getattr(self.state, name)
        if name not in ('build', 'recruit'):
            return method

        def purchase(kind):
            gold, crystals = self.state.gold, self.state.crystals
            result = method(kind)
            self.purchases.append({'command': name, 'kind': kind, 'gold': gold - self.state.gold,
                                   'crystals': crystals - self.state.crystals})
            return result
        return purchase


def create(state, candidate):
    # Temporary catalogue insertion exercises the ordinary authored constructor.
    assert '_ninth_probe' not in ENCOUNTERS
    ENCOUNTERS['_ninth_probe'] = ANCHOR if candidate == 'anchor' else SCREEN
    try:
        return Battle.create(state.hero, KINDS[candidate], 'plains', state.spells, encounter='_ninth_probe')
    finally:
        del ENCOUNTERS['_ninth_probe']


class Orders:
    def __init__(self, battle):
        self.battle = battle
        self.initial = battle.to_dict()
        self.commands = []

    def do(self, command, *args):
        before = self.battle
        forecast = None
        if command == 'attack':
            forecast = before.preview(*args)
            actor_hp, target_hp = (before.unit(uid).hp for uid in args)
        elif command == 'cast':
            forecast = before.spell_preview(*args)
            target_hp = before.unit(args[1]).hp
        getattr(before, command)(*args)
        if command == 'attack':
            assert forecast == (target_hp - before.unit(args[1]).hp, actor_hp - before.unit(args[0]).hp)
        elif command == 'cast':
            assert forecast == before.unit(args[1]).hp - target_hp
        raw = json.dumps(before.to_dict(), sort_keys=True)
        self.battle = Battle.from_dict(json.loads(raw))
        assert self.battle.to_dict() == before.to_dict()
        self.commands.append({'command': command, 'args': args, 'forecast': forecast,
                              'saved_sha256': hashlib.sha256(raw.encode()).hexdigest()})

    def guard_end(self):
        for unit in list(self.battle.units):
            if unit.team == 'player' and unit.alive and not unit.acted:
                self.do('guard', unit.id)
        self.do('end_turn')

    def run(self, commands):
        for command, *args in commands:
            self.do(command, *args)

    def report(self):
        party = [u for u in self.battle.units if u.team == 'player']
        return {'outcome': self.battle.outcome, 'reason': self.battle.outcome_reason,
                'round': self.battle.round, 'deaths': sum(not u.alive for u in party),
                'missing_hp_including_dead': sum(u.max_hp - u.hp for u in party),
                'mana_spent': self.initial['mana'] - self.battle.mana,
                'order_count': len(self.commands), 'orders': self.commands,
                'initial_battle': self.initial, 'final_battle': self.battle.to_dict()}


def anchor(state):
    p = Orders(create(state, 'anchor'))
    p.do('swap', 4, 5); p.guard_end()
    checkpoint = p.battle.to_dict()
    p.run([('attack', 3, 1005), ('attack', 5, 1005), ('attack', 1, 1005),
           ('move', 5, (-1, 2)), ('move', 4, (-1, 1)), ('attack', 4, 1007), ('move', 2, (-2, 1))])
    p.guard_end()
    p.run([('cast', 'heal', 1), ('attack', 4, 1007), ('attack', 5, 1007), ('move', 5, (-3, 3)),
           ('move', 3, (0, -3)), ('attack', 3, 1006), ('attack', 1, 1006),
           ('move', 2, (-1, 0)), ('attack', 2, 1006)])
    p.guard_end()
    p.run([('attack', 5, 1008), ('attack', 4, 1008), ('move', 2, (0, 0)),
           ('attack', 2, 1008), ('move', 3, (1, -1)), ('attack', 3, 1008)])
    assert p.battle.outcome == 'player'
    return p, checkpoint


def screen_opening(state, *, advance=False):
    p = Orders(create(state, 'screen'))
    p.guard_end()
    assert p.battle.smoke_clouds[0].pos == p.battle.unit(5).pos
    assert not p.battle.targets(5)  # Its endpoint is actually screened.
    assert p.battle.unit(1).pinned
    p.run([('move', 4, (-3, 3)), ('attack', 4, 1009), ('move', 2, (-3, 2)), ('attack', 2, 1009),
           ('move', 5, (-1, 1) if advance else (-1, 3)), ('attack', 5, 1009),
           ('move', 0, (-2, 1)), ('attack', 0, 1009), ('attack', 3, 1006)])
    p.guard_end()
    return p


def screen(state, *, heal=False):
    p = screen_opening(state)
    checkpoint = p.battle.to_dict()
    p.run([('attack', 3, 1006), ('attack', 5, 1005), ('attack', 0, 1005), ('attack', 4, 1009),
           ('move', 1, (-1, 0)), ('attack', 1, 1008), ('move', 2, (-1, 1)),
           ('attack', 2, 1008), ('move', 5, (0, 2))])
    p.guard_end()
    if heal:
        p.do('cast', 'heal', 1)
    p.run([('move', 3, (0, -2)), ('attack', 3, 1008), ('move', 5, (1, 1)), ('attack', 5, 1008),
           ('attack', 2, 1008), ('move', 1, (0, 0)), ('attack', 1, 1007)])
    if heal:
        p.guard_end(); p.do('attack', 1, 1007)
    else:
        p.run([('move', 0, (0, -1)), ('attack', 0, 1007)])
    assert p.battle.outcome == 'player'
    assert all(u.alive for u in p.battle.units if u.team == 'player')
    return p, checkpoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    paths = sorted([*root.glob('eador/*.py'), *root.glob('saga2d/**/*.py'),
                    root / 'tools/eador_explorer_campaign.py', root / 'tools/eador_campaign.py', Path(__file__).resolve()])
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    state = prepare_explorer(state=Purchases())
    paid_snapshot = state.to_json()
    a, brace_checkpoint = anchor(state)
    s, rescue_checkpoint = screen(state)
    h, _ = screen(state, heal=True)
    automatic = {}
    for candidate in KINDS:
        p = Orders(create(state, candidate))
        for _ in range(40):
            if p.battle.outcome:
                break
            p.do('auto_turn')
        assert p.battle.outcome == 'player'
        automatic[candidate] = p.report()
    brace = Orders(Battle.from_dict(brace_checkpoint))
    ranged_forecast = brace.battle.preview(5, 1006)
    brace.do('move', 1, (-1, -1)); brace.do('attack', 1, 1006)
    rescue = Orders(Battle.from_dict(rescue_checkpoint))
    rescue.do('attack', 5, 1005); rescue.guard_end()
    assert rescue.battle.unit(1005).pos == (0, 0)
    assert rescue.battle.unit(1008).pos == (-1, 0)
    assert any('swaps places with Sapper' in line for line in rescue.battle.log)
    greedy = screen_opening(state, advance=True)
    # This is an observed failed tactical continuation, not a campaign loss/retry proof.
    assert not greedy.battle.unit(5).alive
    assert state.to_json() == paid_snapshot
    changed = [name for name, digest in hashes.items() if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest]
    assert not changed
    report = {'scope': 'Pure Battle prototype with an earned party; no production site, approach, reward, State attempt or native UI claims.',
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
              'source_files': hashes, 'source_files_changed': changed,
              'preparation': {'helper': 'prepare_explorer()', 'turn': state.turn, 'hero_class': state.hero.hero_class,
                              'hero_level': state.hero.level, 'purchases': state.purchases,
                              'building_gold': sum(p['gold'] for p in state.purchases if p['command'] == 'build'),
                              'recruitment_gold': sum(p['gold'] for p in state.purchases if p['command'] == 'recruit'),
                              'campaign_state': json.loads(paid_snapshot)},
              'manual': {'anchor': a.report(), 'screen_fast': s.report(), 'screen_heal': h.report()},
              'automatic': automatic, 'counterprobes': {'brace_melee': brace.report(), 'brace_ranged_forecast': ranged_forecast,
                                                       'enemy_warden_rescue': rescue.report(), 'ranger_overextension': greedy.report()}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({name: {k: v for k, v in result.items() if k in ('round', 'deaths', 'missing_hp_including_dead', 'mana_spent', 'order_count')}
                      for name, result in report['manual'].items()}, indent=2))


if __name__ == '__main__':
    main()
