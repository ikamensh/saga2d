"""Compare three public campaign itineraries; save reproducible route costs, not balance claims."""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from statistics import mean
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.model import HERO_CLASSES, State
from eador.worldgen import NORTH_ROAD, SOUTH_ROAD, THEMES
from tools.cpu_budget import CpuBudget
from tools.eador_campaign import CampaignMetrics, play_campaign


def audit(seed_count: int, *, budget=None) -> dict:
    rows = []
    for theme in THEMES:
        for seed in range(seed_count):
            for hero_class in HERO_CLASSES:
                for route_name, route in (('direct', None), ('north', NORTH_ROAD), ('south', SOUTH_ROAD)):
                    metrics = CampaignMetrics()
                    state = play_campaign(State.new(seed, hero_class, theme=theme), route, metrics, budget=budget)
                    rows.append(dict(theme=theme, seed=seed, hero_class=hero_class, route=route_name,
                                     outcome=state.status, turn=state.turn, gold=state.gold,
                                     army_size=len(state.hero.army), relics=state.inventory,
                                     hero_hp=state.hero.hp, hero_mana=state.hero.mana, **asdict(metrics)))
    groups = defaultdict(list)
    for row in rows:
        groups[(row['theme'], row['route'])].append(row)
    columns = ('turn', 'gold', 'army_size', *CampaignMetrics.__dataclass_fields__)
    summary = [dict(theme=theme, route=route, campaigns=len(group),
                    victories=sum(row['outcome'] == 'victory' for row in group),
                    **{column: round(mean(row[column] for row in group), 2) for column in columns})
               for (theme, route), group in groups.items()]
    sources = [*sorted((ROOT / 'eador').glob('*.py')), Path(__file__),
               ROOT / 'tools/eador_campaign.py', ROOT / 'tools/cpu_budget.py']
    return dict(seed_count=seed_count, campaigns=len(rows), cpu_percent=budget.percent if budget else None,
                source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in sources},
                policy='Explore itinerary sites; buy Barracks/Swordsman, then Temple (Wizard tower first); '
                       'choose first skill option; use first relic in battle, Merchant Seal when recruiting; '
                       'intercept nearby rival; refill before Duskspire. Automatic tactical orders only.',
                metric_notes='battle_hp_attrition is net HP lost per encounter before campaign advancement, '
                             'including dead units, after any tactical healing; lost_troops counts actual soldiers. '
                             'recovery_turns counts extra final-approach rests for wounds/mana; end_turns counts all rests. '
                             'hp_recovered/mana_recovered count end-turn recovery only. Gold is final treasury, not profit per turn.',
                summary=summary, runs=rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=10)
    parser.add_argument('--cpu-percent', type=float, default=25,
                        help='CPU allowance as a percent of one core (default 25; 100 for explicit stress)')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error('--seeds must be positive')
    try:
        budget = CpuBudget(args.cpu_percent)
    except ValueError as error:
        parser.error(str(error))
    report = audit(args.seeds, budget=budget)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(campaigns=report['campaigns'], summary=report['summary']), indent=2))


if __name__ == '__main__':
    main()
