#!/usr/bin/env python3
"""Compare fresh discoveries with 300 retained public-State worlds; never play battles.

Location and distance-sorted placement orders describe generated maps, not actual
player itineraries, tactical fairness, successful routes or completed campaigns.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.content import SITES
from eador.model import State
from eador.worldgen import NORTH_ROAD, SOUTH_ROAD, THEMES
from tools.cpu_budget import CpuBudget

BASELINE = ROOT / 'docs/evidence/adventure-variety/baseline-worlds.json.gz'
BASELINE_SHA256 = 'ce949cade506f8d341c74abe4c082cff719afadd13dafaeccb497ab78617a6e0'
SITE_FIELDS = ('site', 'site_kind', 'site_guards', 'site_guard_hp',
               'site_relic', 'site_gold', 'site_crystals')
VARIED_ADVENTURES = {
    'frontier': ('muster_yard', 'stranded_explorer', 'courier_crossing'),
    'elderwild': ('supply_cache', 'pack_hunt', 'smuggler_screen'),
    'ruins': ('sealed_vault', 'broken_observatory', 'aerie_raid'),
}
SOURCE_FILES = (
    'eador/model.py', 'eador/battle.py', 'eador/battle_trace.py', 'eador/campaign.py',
    'eador/content.py', 'eador/difficulty.py', 'eador/encounters.py', 'eador/rival.py',
    'eador/sight.py', 'eador/worldgen.py', 'saga2d/hexgrid.py',
    'tools/audit_eador_discoveries.py', 'tools/cpu_budget.py',
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_hashes() -> dict:
    return {name: _sha256((ROOT / name).read_bytes()) for name in SOURCE_FILES}


def _package(province: dict) -> str:
    return json.dumps({name: province[name] for name in SITE_FIELDS}, sort_keys=True)


def _band(pos: tuple) -> str:
    return 'western' if pos[0] < 0 else 'central' if pos[0] == 0 else 'eastern'


def _road_sources(theme: str, provinces: dict) -> list:
    """Read the baseline's economic road from its saved conquest/income facts."""
    if theme == 'frontier':
        return []
    if theme == 'elderwild':
        road = [pos for pos, p in provinces.items() if not p['capital'] and p['income'] >= 10]
    else:
        road = min((NORTH_ROAD, SOUTH_ROAD),
                   key=lambda route: sum(sum(provinces[pos]['guard_hp']) for pos in route[1:-1]))
    return [pos for pos in road if provinces[pos]['site_kind'] in ('caravan', 'tower')]


def audit_worlds(baseline_path: Path = BASELINE, *, cpu_percent: float = 25) -> dict:
    """Assert preserved public new/save/load properties and report seeded placement variety."""
    budget = CpuBudget(cpu_percent)
    started, cpu_started = time.monotonic(), time.process_time()
    source = _source_hashes()
    raw = Path(baseline_path).read_bytes()
    assert _sha256(raw) == BASELINE_SHA256, 'The retained baseline gzip bytes changed'
    baseline = json.loads(gzip.decompress(raw))
    entries = baseline['states']
    expected = {(seed, theme) for theme in THEMES for seed in range(100)}
    assert len(entries) == len(expected) == 300
    assert {(e['seed'], e['theme']) for e in entries} == expected
    rows = []
    locations = {version: {theme: defaultdict(Counter) for theme in THEMES}
                 for version in ('baseline', 'current')}
    orders = {version: {theme: Counter() for theme in THEMES}
              for version in ('baseline', 'current')}
    for entry in entries:
        budget.checkpoint()
        seed, theme, old_saved = entry['seed'], entry['theme'], entry['state']
        context = f'{theme} seed {seed}'
        old = json.loads(old_saved)
        assert old['seed'] == seed and old['theme'] == theme, context
        assert State.from_json(old_saved).to_json() == old_saved, (context, 'historical reload')
        state = State.new(seed, theme=theme, difficulty='standard')
        saved = state.to_json()
        assert State.new(seed, theme=theme, difficulty='standard').to_json() == saved, (context, 'determinism')
        assert State.from_json(saved).to_json() == saved, (context, 'new-world reload')
        current = json.loads(saved)
        assert {k: v for k, v in old.items() if k != 'provinces'} == {
            k: v for k, v in current.items() if k != 'provinces'}, (context, 'non-province State changed')
        before = {tuple(p['pos']): p for p in old['provinces']}
        after = {tuple(p['pos']): p for p in current['provinces']}
        assert before.keys() == after.keys(), (context, 'province coordinates')
        assert len(before) == len(old['provinces']) == len(current['provinces']), context
        road_sources = _road_sources(theme, before)
        watches = [pos for pos, p in before.items() if p['site_kind'] == 'border_watch']
        assert len(watches) == 1 and watches[0][0] == 0 and abs(watches[0][1]) == 2, context
        assert [pos for pos, p in after.items() if p['site_kind'] == 'border_watch'] == watches, context
        assert after[(-2, 0)]['site_kind'] == 'shrine', context
        assert after[(2, 0)]['site_kind'] is None, context
        fixed = set(road_sources + watches + [pos for pos, p in before.items()
                                            if p['capital'] or pos[0] >= 1])
        changed = []
        for pos, p in before.items():
            assert {k: v for k, v in p.items() if k not in SITE_FIELDS} == {
                k: v for k, v in after[pos].items() if k not in SITE_FIELDS}, (context, pos, 'realm province changed')
            if pos in fixed:
                assert after[pos] == p, (context, pos, 'fixed site changed')
            if _package(p) != _package(after[pos]):
                changed.append(pos)
        for band in ('western', 'central', 'eastern'):
            assert Counter(_package(p) for pos, p in before.items() if _band(pos) == band) == Counter(
                _package(p) for pos, p in after.items() if _band(pos) == band), (context, band, 'site packages changed')
        opening = [pos for pos in state.grid.neighbors(state.hero.pos)
                   if SITES[after[pos]['site_kind']].encounter is None]
        assert len(opening) >= 2, (context, 'two ordinary opening adventures')
        for version, provinces in (('baseline', before), ('current', after)):
            placement_order = []
            for pos, province in provinces.items():
                kind = province['site_kind']
                if kind is None:
                    continue
                locations[version][theme][kind][pos] += 1
                assert state.grid.path(state.hero.pos, pos), (context, pos, 'disconnected site')
                if kind in VARIED_ADVENTURES[theme]:
                    assert not province['capital'] and province['owner'] == 'neutral', (context, kind)
                    placement_order.append((state.grid.distance(state.hero.pos, pos), pos, kind))
            assert Counter(kind for _, _, kind in placement_order) == Counter(VARIED_ADVENTURES[theme]), context
            orders[version][theme][tuple(kind for _, _, kind in sorted(placement_order))] += 1
        rows.append(dict(seed=seed, theme=theme, baseline_save_sha256=_sha256(old_saved.encode()),
                         current_save_sha256=_sha256(saved.encode()), moved_sites=changed,
                         ordinary_opening_locations=opening, fixed_road_sources=road_sources))
        budget.checkpoint()
    themes = {}
    for theme in THEMES:
        for kind in VARIED_ADVENTURES[theme]:
            assert len(locations['current'][theme][kind]) >= 3, (theme, kind, 'adventure location variety')
        assert len(orders['current'][theme]) >= 3, (theme, 'distance-sorted placement order variety')
        themes[theme] = dict(
            world_count=sum(row['theme'] == theme for row in rows),
            worlds_with_moved_sites=sum(row['theme'] == theme and bool(row['moved_sites']) for row in rows),
            site_locations={kind: {version: [dict(position=pos, worlds=count)
                                            for pos, count in sorted(locations[version][theme][kind].items())]
                                   for version in locations}
                            for kind in sorted(locations['current'][theme])},
            distance_sorted_placement_orders={version: [dict(site_order=order, worlds=count)
                                                        for order, count in sorted(orders[version][theme].items())]
                                              for version in orders})
    assert _source_hashes() == source, 'Audited model/tool source changed during the run'
    return dict(
        method='Public State.new / to_json / from_json only; zero battles or campaign commands.',
        scope='Commander, Standard, seeds 0–99 in each theme. Geometric placement orders are not played routes or evidence of tactical fairness.',
        cpu_percent=cpu_percent, elapsed_seconds=time.monotonic() - started,
        cpu_seconds=time.process_time() - cpu_started, world_count=len(rows),
        exact_reloads=dict(baseline=len(rows), current=len(rows)),
        invariants=['identical non-province State', 'identical non-site province fields',
                    'complete site-package multisets per progression band including guard HP',
                    'home, Watch, eastern and economic-road Caravan/Tower sites fixed',
                    'two ordinary home-adjacent adventures', 'connected sites',
                    'deterministic current worlds', 'exact historical and current reloads',
                    'three locations per varied authored family and three geometric orders per theme'],
        baseline=dict(path=str(baseline_path), gzip_sha256=BASELINE_SHA256,
                      metadata={k: v for k, v in baseline.items() if k != 'states'}),
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        source_dirty_files=subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).splitlines(),
        audited_source_sha256=source, audited_source_unchanged=True, themes=themes, worlds=rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=BASELINE)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cpu-percent', type=float, default=25)
    args = parser.parse_args()
    report = audit_worlds(args.baseline, cpu_percent=args.cpu_percent)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, separators=(',', ':')) + '\n')
    print(json.dumps({key: report[key] for key in ('world_count', 'exact_reloads', 'elapsed_seconds', 'cpu_seconds', 'cpu_percent')}, sort_keys=True))


if __name__ == '__main__':
    main()
