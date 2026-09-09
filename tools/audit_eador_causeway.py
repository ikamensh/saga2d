"""Audit actual paid Causeway plans, finite retry and preserved ordinary sources.

Standard seed7 manual examples are not optimal-play or all-difficulty claims.
Preparation battles use the ordinary public automatic policy; tactical route
orders and every recorded campaign checkpoint reload the complete State.
"""
import argparse
from collections import Counter
from dataclasses import asdict
from functools import partial
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.model import RuleError, State
from eador.worldgen import generate
from tools.eador_sources import framework_sources, source_name
from tools.audit_eador_aerie import Purchases, RecordedOrders
from saga2d.testing.cpu_budget import CpuBudget
from tools.eador_causeway_campaign import (prepare_causeway, causeway_focus_route,
    causeway_guard_route, causeway_scout_route, causeway_failed_attempt, causeway_retry_route)

class PaidTravel(Purchases):
    """Record public campaign commands and exact saves; automatic tactical preparation is explicit."""
    def __init__(self, state, *, budget=None):
        super().__init__(state)
        self.budget = budget
        self.events = []

    def checkpoint(self, command, args, before):
        if self.budget:
            self.budget.checkpoint()
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
        if name not in ('explore', 'travel', 'end_turn', 'resolve_battle', 'choose', 'equip', 'infuse'):
            return value

        def command(*args, **kwargs):
            before = json.loads(self.state.to_json())
            result = value(*args, **kwargs)
            self.checkpoint(name, dict(args=args, kwargs=kwargs), before)
            return result
        return command



def snapshot(state):
    return json.loads(state.to_json())


def source_audit(*, budget=None):
    """Restore only the intended source fields and compare the real prechange whole-world hash."""
    provenance = ROOT / 'docs/evidence/causeway-placement-2026-09-06.json.gz'
    with gzip.open(provenance, 'rt') as handle:
        previous = json.load(handle)['source_audit']
    positions = Counter()
    for row in previous['witnesses']:
        if budget:
            budget.checkpoint()
        world = generate(row['seed'], 'ruins')
        before, witness = row['selected'], row['witness']
        pos = tuple(before['pos'])
        assert sum(p.site_kind == 'runebound_causeway' for p in world.values()) == 1
        current = json.loads(json.dumps(asdict(world[pos])))
        assert current['site_kind'] == 'runebound_causeway'
        assert json.loads(json.dumps(asdict(world[tuple(witness['pos'])]))) == witness
        for field in ('site', 'site_kind', 'site_guards', 'site_guard_hp'):
            current[field] = before[field]
        assert current == before
        restored = [before if key == pos else asdict(world[key]) for key in sorted(world)]
        assert hashlib.sha256(json.dumps(restored, sort_keys=True).encode()).hexdigest() == row['original_world_sha256']
        assert world[(1, 0)].site_kind == 'barrow' and world[(1, 0)].site_relic == 'iron_crown'
        positions[str(pos)] += 1
    return dict(seeds=len(previous['witnesses']), selected_positions=dict(positions),
                provenance=str(provenance.relative_to(ROOT)), provenance_sha256=hashlib.sha256(provenance.read_bytes()).hexdigest(),
                scope='Every other province and every reward exact; unchanged ordinary witness and direct Crown preserved.')


def settle_once(play, *, budget=None):
    state = play.state
    gold, crystals, reward = state.gold, state.crystals, state.battle_adventure
    state.resolve_battle()
    assert (state.gold, state.crystals) == (gold + reward.gold, crystals + reward.crystals)
    while state.choice:
        if budget:
            budget.checkpoint()
        state.choose(state.choice.options[0].id)
    saved = state.to_json()
    for command in (state.explore, state.resolve_battle):
        try:
            command()
        except RuleError:
            pass
        else:
            raise AssertionError('The completed Causeway rewarded twice.')
        assert state.to_json() == saved
    return snapshot(state)


def measure(*, budget=None):
    budget = CpuBudget(25) if budget is None else budget
    sources = sorted([*ROOT.glob('eador/*.py'), *framework_sources(), *ROOT.glob('tools/eador_*.py'),
                      ROOT / 'tools/audit_eador_aerie.py', ROOT / 'tools/audit_eador_extraction.py', Path(__file__).resolve()])
    hashes = {source_name(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    parties, plans = {}, {}
    for hero, mana in (('Commander', 0), ('Commander', 12), ('Commander', 16), ('Scout', 0), ('Scout', 8)):
        paid = PaidTravel(State.new(7, hero, theme='ruins'), budget=budget)
        prepare_causeway(state=paid, mana=mana, budget=budget)
        parties[f'{hero}:{mana}'] = dict(arrival=snapshot(paid), purchases=paid.purchases, campaign_orders=paid.events)
    infused = PaidTravel(State.from_json(json.dumps(parties['Commander:0']['arrival'])), budget=budget)
    infused.infuse()
    assert (infused.turn, infused.actions_left, infused.hero.mana) == (9, 1, 18)
    parties['Commander:infused'] = dict(arrival=snapshot(infused), purchases=parties['Commander:0']['purchases'], campaign_orders=infused.events,
                                       preparation='Commander:0 arrival followed by exactly one recorded infusion')
    rows = (
        ('focus', 'Commander:0', causeway_focus_route, {}),
        ('focus-heal', 'Commander:0', causeway_focus_route, dict(heal=True)),
        ('guard', 'Commander:0', causeway_guard_route, {}),
        ('guard-heal-rest', 'Commander:12', causeway_guard_route, dict(heal=True)),
        ('backstop-rest', 'Commander:12', causeway_guard_route, dict(backstop=True)),
        ('backstop-heal-rest', 'Commander:16', causeway_guard_route, dict(backstop=True, heal=True)),
        ('guard-heal-infused', 'Commander:infused', causeway_guard_route, dict(heal=True)),
        ('backstop-heal-infused', 'Commander:infused', causeway_guard_route, dict(backstop=True, heal=True)),
        ('scout', 'Scout:0', causeway_scout_route, {}),
        ('scout-heal', 'Scout:8', causeway_scout_route, dict(heal=True)),
    )
    record_orders = partial(RecordedOrders, budget=budget)
    for name, party, route, options in rows:
        state = State.from_json(json.dumps(parties[party]['arrival']))
        play = route(state, orders_type=record_orders, **options)
        report = play.report(); report.pop('flight_only_landings')
        assert not report['dead'] and report['reason'] in ('escape', 'rout')
        plans[name] = dict(party=party, **report, settled=settle_once(play, budget=budget))
    failed = causeway_failed_attempt(State.from_json(json.dumps(parties['Commander:0']['arrival'])), orders_type=record_orders)
    report = failed.report(); report.pop('flight_only_landings')
    assert report['reason'] == 'deadline' and not report['dead']
    state = failed.state
    gold, crystals, xp = state.gold, state.crystals, state.hero.xp
    state.resolve_battle()
    assert (state.gold, state.crystals, state.hero.xp) == (gold - 20, crystals, xp)
    assert state.choice is None
    province = state.provinces[state.hero.pos]
    assert list(zip(province.site_guards, province.site_guard_hp)) == [('pikeman', 28), ('ranger', 22), ('guard', 28)]
    plans['deliberate-deadline'] = dict(**report, settled=snapshot(state),
                                      scope='Exposed carrier is really pushed; continued guarding deliberately misses deadline. Failure is not unavoidable.')
    recovering = PaidTravel(State.from_json(state.to_json()), budget=budget)
    retry = causeway_retry_route(recovering, orders_type=record_orders, budget=budget)
    report = retry.report(); report.pop('flight_only_landings')
    assert report['reason'] == 'rout' and not report['dead']
    plans['finite-retry'] = dict(**report, recovery_orders=recovering.events, settled=settle_once(retry, budget=budget))
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in hashes.items())
    return dict(source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                source_sha256=hashes, python=platform.python_version(), platform=platform.platform(), cpu_percent=budget.percent,
                source_audit=source_audit(budget=budget), parties=parties, plans=plans,
                scope='Actual seed7 Standard campaigns and manual model routes. Automatic preparation combat is explicit; no optimal-play/all-mode/native claim.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/causeway-production.json.gz'))
    parser.add_argument('--cpu-percent', type=float, default=25,
                        help='CPU allowance as a percent of one core (default 25; 100 for explicit stress)')
    args = parser.parse_args(argv)
    try:
        budget = CpuBudget(args.cpu_percent)
    except ValueError as error:
        parser.error(str(error))
    report = measure(budget=budget)
    args.output.write_bytes(gzip.compress((json.dumps(report, separators=(',', ':')) + '\n').encode(), mtime=0))
    for name, plan in report['plans'].items():
        print(name, 'turn', plan['initial']['turn'], plan['reason'], 'round', plan['rounds'],
              'wounds', plan['wounds'], 'mana', plan['mana_spent'], 'orders/reloads', plan['orders'])
    print('Source-preserving worlds:', report['source_audit']['seeds'])


if __name__ == '__main__':
    main()
