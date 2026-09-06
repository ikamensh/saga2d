"""PROPOSAL ONLY: audit a safe Ruins duplicate and real paid arrival; change no content.

The local copied-world mutation below audits exactly four proposed site fields.
Travel plays the current game. Tactical comparisons then author a separate copy
of each actual arrival, using the isolated prototype registry. Original worlds
remain untouched. This does not accept the Causeway tactical design.
"""
import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.model import BUILDINGS, State, UNITS
from eador.worldgen import FRONTIER_SITES, generate
from tools.audit_eador_aerie import Purchases
from tools.eador_campaign import march_to, rest
from tools.eador_explorer_campaign import prepare_explorer
from tools.eador_extraction_campaign import prepare_adventure
from tools.prototype_eador_causeway import (commander_route, entered, focus_route,
                                           hypothetical_content, scout_route, settle_once)


def reward(province):
    return province.site_gold, province.site_crystals, province.site_relic


def select_source(provinces):
    """Same narrow duplicate guarantee as Relief49fb921, applied only to Ruins data."""
    for province in sorted(provinces.values(), key=lambda p: p.pos):
        if province.pos[0] < 0 or province.pos == (1, 0) or province.site_kind not in FRONTIER_SITES:
            continue
        for witness in sorted(provinces.values(), key=lambda p: p.pos):
            if (witness.pos != province.pos and witness.pos[0] <= province.pos[0]
                    and witness.site_kind == province.site_kind and reward(witness) == reward(province)
                    and Counter(witness.site_guards) <= Counter(province.site_guards)):
                return province.pos, witness.pos
    raise AssertionError('No unchanged ordinary duplicate for the proposed source.')


def world_audit(seeds):
    witnesses, distribution = [], Counter()
    for seed in range(seeds):
        provinces = generate(seed, 'ruins')
        eligible = [p for p in provinces.values() if p.pos[0] >= 0 and p.site_kind in FRONTIER_SITES]
        # Current _ruins structure: 12 eastern/central cells minus capital,
        # Aerie and one Watch; these nine ordinary sites use only three kinds.
        assert len(eligible) == 9
        assert {p.site_kind for p in eligible} <= {'tower', 'barrow', 'shrine'}
        assert provinces[(1, 0)].site_kind == 'barrow' and provinces[(1, 0)].site_relic == 'iron_crown'
        # Reserve the direct road's fixed Crown source as well: eight eligible
        # ordinary sites still guarantee a duplicate among these three kinds.
        assert len([p for p in eligible if p.pos != (1, 0)]) == 8
        pos, witness_pos = select_source(provinces)
        before = {key: asdict(value) for key, value in provinces.items()}
        proposed = deepcopy(provinces)
        chosen = proposed[pos]
        chosen.site, chosen.site_kind = 'Runebound Causeway — proposal', 'causeway_proposal'
        chosen.site_guards = ['adept', 'pikeman', 'ranger', 'guard']
        chosen.site_guard_hp = [UNITS[kind].hp for kind in chosen.site_guards]
        after = {key: asdict(value) for key, value in proposed.items()}
        changed = {key: (before[pos][key], after[pos][key]) for key in before[pos] if before[pos][key] != after[pos][key]}
        assert set(changed) == {'site', 'site_kind', 'site_guards', 'site_guard_hp'}
        assert all(before[key] == after[key] for key in before if key != pos)
        assert Counter(reward(p) for p in provinces.values()) == Counter(reward(p) for p in proposed.values())
        assert before[witness_pos] == after[witness_pos]
        distribution[str(pos)] += 1
        witnesses.append(dict(seed=seed, selected=before[pos], witness=before[witness_pos], changed=changed,
                              original_world_sha256=hashlib.sha256(json.dumps(
                                  [before[key] for key in sorted(before)], sort_keys=True).encode()).hexdigest()))
    return dict(seeds=seeds, selected_positions=dict(distribution), witnesses=witnesses)


class PaidTravel(Purchases):
    """Record public campaign commands and exact saves; automatic tactical preparation is explicit."""
    def __init__(self, state):
        super().__init__(state)
        self.events = []

    def checkpoint(self, command, args, before):
        saved = self.state.to_json()
        self.state = State.from_json(saved)
        assert self.state.to_json() == saved
        self.events.append(dict(command=command, args=args, before=before, after=json.loads(saved)))

    def _buy(self, command, kind):
        before = json.loads(self.state.to_json())
        super()._buy(command, kind)
        self.checkpoint(command, [kind], before)

    def __getattr__(self, name):
        value = getattr(self.state, name)
        if name not in ('explore', 'travel', 'end_turn', 'resolve_battle', 'choose', 'equip'):
            return value

        def command(*args):
            before = json.loads(self.state.to_json())
            result = value(*args)
            self.checkpoint(name, args, before)
            return result
        return command


def snapshot(paid):
    return json.loads(paid.to_json())


def travel(hero):
    paid = PaidTravel(State.new(7, hero, theme='ruins'))
    original = snapshot(paid)
    destination, witness = select_source(paid.provinces)
    source_fields = asdict(paid.provinces[destination])
    if hero == 'Commander':
        prepare_adventure(theme='ruins', state=paid)
    else:
        prepare_explorer(hero, support=None, state=paid)
    tower = BUILDINGS['mage_tower']
    for _ in range(24):
        if paid.gold >= tower.cost and paid.crystals >= tower.crystals:
            break
        rest(paid)
    else:
        raise AssertionError('Could not fund the ordinary Mage Tower.')
    paid.build('mage_tower')
    for _ in range(48):
        march_to(paid, destination)
        if (paid.actions_left and paid.hero.hp == paid.hero.max_hp
                and all(t.hp == t.max_hp for t in paid.hero.army)):
            break
        rest(paid)
    else:
        raise AssertionError('Could not arrive with the purchased party recovered.')
    healthy = snapshot(paid)
    recovery_options = [dict(state=healthy, commands_so_far=len(paid.events))]
    for _ in range(48):
        if (paid.hero.pos == destination and paid.actions_left and paid.hero.mana == paid.hero.max_mana
                and paid.hero.hp == paid.hero.max_hp and all(t.hp == t.max_hp for t in paid.hero.army)):
            break
        rest(paid)
        march_to(paid, destination)
        if (paid.actions_left and paid.hero.hp == paid.hero.max_hp
                and all(t.hp == t.max_hp for t in paid.hero.army)):
            recovery_options.append(dict(state=snapshot(paid), commands_so_far=len(paid.events)))
    else:
        raise AssertionError('Could not arrive with full health and mana.')
    assert not paid.provinces[destination].explored
    for field in ('site', 'site_kind', 'site_guards', 'site_guard_hp', 'site_gold', 'site_crystals', 'site_relic'):
        assert getattr(paid.provinces[destination], field) == source_fields[field]
    assert all(p['command'] != 'recruit' or p['kind'] in ('warden', 'healer') for p in paid.purchases)
    return dict(original=original, destination=destination, witness=witness, source=source_fields,
                healthy_arrival=healthy, full_mana_arrival=snapshot(paid), purchases=paid.purchases,
                recovery_options=recovery_options, events=paid.events,
                scope='Actual current Ruins, seed7 Standard; automatic preparation battles, no hypothetical source installed or explored. Rest helper may intercept the real rival.')


def compare_arrivals(journeys):
    """Same full-mana snapshots and actual first affordable recovery checkpoints."""
    plans = (
        ('Commander', 'guard', 8, lambda p: commander_route(p, backstop=False)),
        ('Commander', 'guard-heal', 12, lambda p: commander_route(p, backstop=False, heal=True)),
        ('Commander', 'backstop', 12, lambda p: commander_route(p, backstop=True)),
        ('Commander', 'backstop-heal', 16, lambda p: commander_route(p, backstop=True, heal=True)),
        ('Commander', 'focus', 4, lambda p: focus_route(p)),
        ('Commander', 'focus-heal', 8, lambda p: focus_route(p, heal=True)),
        ('Scout', 'scout', 4, lambda p: scout_route(p)),
        ('Scout', 'scout-heal', 8, lambda p: scout_route(p, heal=True)),
    )
    results = {}
    with hypothetical_content():
        for hero, name, budget, routine in plans:
            journey = journeys[hero]
            first = next(option['state'] for option in journey['recovery_options'] if option['state']['hero']['mana'] >= budget)
            for timing, arrival in (('first-affordable', first), ('full-mana', journey['full_mana_arrival'])):
                original = json.dumps(arrival)
                play = entered(State.from_json(original), False)
                routine(play)
                report = play.report()
                assert not report['dead'] and report['mana_spent'] == budget
                assert report['reason'] == ('rout' if name == 'scout-heal' else 'escape')
                assert json.dumps(arrival) == original
                results[name + ':' + timing] = {**report, 'settled': settle_once(play),
                                               'campaign_arrival_turn': arrival['turn'],
                                               'campaign_arrival_level': arrival['hero']['level'],
                                               'campaign_arrival_mana': arrival['hero']['mana']}
    return results


def measure(seeds=1000):
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'),
                      *ROOT.joinpath('tools').glob('eador_*.py'),
                      ROOT / 'tools/audit_eador_aerie.py', ROOT / 'tools/audit_eador_extraction.py',
                      ROOT / 'tools/prototype_eador_causeway.py', ROOT / 'saga2d/hexgrid.py', Path(__file__).resolve()])
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    result = dict(source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, python=platform.python_version(), platform=platform.platform(),
                  source_audit=world_audit(seeds), journeys={hero: travel(hero) for hero in ('Commander', 'Scout')})
    result['tactical_comparison'] = compare_arrivals(result['journeys'])
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value for name, value in hashes.items())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/causeway-placement.json.gz'))
    parser.add_argument('--seeds', type=int, default=1000)
    args = parser.parse_args()
    result = measure(args.seeds)
    args.output.write_bytes(gzip.compress((json.dumps(result, separators=(',', ':')) + '\n').encode(), mtime=0))
    print('Unchanged witness/other provinces/reward multisets:', result['source_audit']['seeds'])
    print('Positions:', result['source_audit']['selected_positions'])
    for name, journey in result['journeys'].items():
        print(name, 'purchases', journey['purchases'], 'commands/reloads', len(journey['events']))
        for kind in ('healthy_arrival', 'full_mana_arrival'):
            state = journey[kind]
            print(kind, 'turn', state['turn'], 'hero level', state['hero']['level'],
                  'mana', state['hero']['mana'], 'gold/crystals', state['gold'], state['crystals'])
    for name, plan in result['tactical_comparison'].items():
        print(name, 'arrival', plan['campaign_arrival_turn'], 'level', plan['campaign_arrival_level'],
              plan['reason'], 'round', plan['rounds'], 'wounds', plan['wounds'], 'mana', plan['mana_spent'])


if __name__ == '__main__':
    main()
