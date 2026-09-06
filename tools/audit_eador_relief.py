"""Record earned Relief orders, costs, exact reloads and finite retries across a bounded matrix."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.model import RuleError, State
from tools.audit_eador_aerie import Purchases, RecordedOrders
from tools.eador_relief_campaign import (prepare_relief, relief_forward_route, relief_western_route,
                                         relief_passive_route, relief_scout_route,
                                         relief_failed_support, relief_retry_route)


def settle_once(play):
    state = play.state
    gold, crystals, reward = state.gold, state.crystals, state.battle_adventure
    guards = [(u.kind, u.hp) for u in play.battle.units if u.team == 'enemy' and u.alive]
    state.resolve_battle()
    assert (state.gold, state.crystals) == (gold + reward.gold, crystals + reward.crystals)
    province = state.provinces[state.hero.pos]
    assert province.explored and list(zip(province.site_guards, province.site_guard_hp)) == guards
    while state.choice:
        state.choose(state.choice.options[0].id)
        state = State.from_json(state.to_json())
    text = state.to_json()
    for command in (state.explore, state.resolve_battle):
        try:
            command()
        except RuleError:
            pass
        else:
            raise AssertionError('A resolved Relief site rewarded twice.')
        assert state.to_json() == text
    return json.loads(text)


def measure():
    sources = sorted([*ROOT.glob('eador/*.py'), *ROOT.glob('saga2d/**/*.py'),
                      *ROOT.glob('tools/eador_*.py'), Path(__file__).resolve(),
                      ROOT/'tools/audit_eador_aerie.py', ROOT/'tools/audit_eador_extraction.py'])
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines()
    parties, plans = {}, {}
    for mode in ('accessible', 'standard', 'challenge'):
        for seed in (0, 2, 7, 11, 29):
            for hero, routes in (
                ('Commander', [('forward', relief_forward_route), ('western', relief_western_route),
                               ('passive', relief_passive_route)]),
                ('Scout', [('scout', relief_scout_route)])):
                key = f'{mode}/{seed}/{hero}'
                paid = prepare_relief(state=Purchases(State.new(seed, hero, difficulty=mode)))
                parties[key] = dict(snapshot=json.loads(paid.to_json()), purchases=paid.purchases)
                for name, route in routes:
                    play = route(State.from_json(paid.to_json()), orders_type=RecordedOrders)
                    report = play.report()
                    assert report['reason'] == 'hold' and not report['dead']
                    assert report['rounds'] == (4 if name == 'western' else 2)
                    assert any(u.alive for u in play.battle.units if u.team == 'enemy')
                    plans[f'{key}/{name}'] = {**report, 'settled': settle_once(play)}
    baseline = State.from_json(json.dumps(parties['standard/7/Commander']['snapshot']))
    failed = relief_failed_support(baseline, orders_type=RecordedOrders)
    failure = failed.report()
    assert failure['reason'] == 'deadline' and failure['dead'] == [4]
    assert any('rallies Skyrider' in line for line in failed.battle.log)
    state = failed.state
    gold, crystals, xp = state.gold, state.crystals, state.hero.xp
    state.resolve_battle()
    assert (state.gold, state.crystals, state.hero.xp) == (gold - 20, crystals, xp)
    assert state.choice is None and not state.provinces[state.hero.pos].explored
    province = state.provinces[state.hero.pos]
    assert list(zip(province.site_guards, province.site_guard_hp)) == [('archer', 20), ('guard', 36)]
    failure['settled'] = json.loads(state.to_json())
    replacement = Purchases(State.from_json(state.to_json()))
    replacement.recruit('pikeman')
    fresh = replacement.hero.army[-1]
    assert fresh.id != 4 and fresh.level == 1 and fresh.xp == 0
    retry = relief_retry_route(replacement, orders_type=RecordedOrders)
    assert retry.battle.outcome_reason == 'rout'
    retry_report = retry.report()
    assert not retry_report['dead']
    retry_report.update(purchases=replacement.purchases, settled=settle_once(retry))
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    return dict(source_revision=revision, dirty_at_start=dirty, source_sha256=hashes,
                parties=parties, plans=plans, failed_support=failure, paid_automatic_retry=retry_report,
                scope='60 earned manual holds: 3 modes, 5 seeds, Commander active/western/passive and Scout. '
                      'Every tactical order reloads the complete State. One missed-support defeat and paid '
                      'finite retry uses explicit automatic rounds. No native, all-class, optimal-play or difficulty claim.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/relief-production.json.gz'))
    args = parser.parse_args()
    report = measure()
    payload = (json.dumps(report, separators=(',', ':')) + '\n').encode()
    args.output.write_bytes(gzip.compress(payload, mtime=0) if args.output.suffix == '.gz' else payload)
    for key, plan in report['plans'].items():
        print(key, plan['reason'], plan['rounds'], 'wounds', plan['wounds'], 'mana', plan['mana_spent'])
    print('Manual holds:', len(report['plans']), 'orders/reloads:', sum(p['orders'] for p in report['plans'].values()))
    print('Failed support:', report['failed_support']['reason'], report['failed_support']['dead'],
          'paid automatic retry:', report['paid_automatic_retry']['reason'])
