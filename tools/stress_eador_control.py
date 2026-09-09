#!/usr/bin/env python3
"""Reproduce varied control orders and two disclosed paid campaign plans.

Battle fixtures test legality and saved continuation. Fixed campaign plans measure
robustness and resource use, not difficulty balance or player enjoyment.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eador.battle import Battle
from eador.model import BUILDINGS, HERO_CLASSES, Hero, State, Troop, UNITS
from eador.worldgen import THEMES
from tools.eador_sources import source_name
from tools.audit_eador_economy import Trial
from saga2d.testing.cpu_budget import CpuBudget

PLANS = {
    'control': (('build', 'market'), ('recruit', 'sapper'), ('build', 'mage_tower'),
                ('recruit', 'adept'), ('build', 'temple'), ('build', 'barracks')),
    'flight': (('build', 'temple'), ('recruit', 'skyrider'), ('build', 'barracks'),
               ('recruit', 'warden')),
}


class ControlTrial(Trial):
    def invest(self):
        state = self.state
        if state.status != 'playing':
            return
        while self.plan_step < len(PLANS[self.plan]):
            action, kind = PLANS[self.plan][self.plan_step]
            if action == 'build':
                spec = BUILDINGS[kind]
                affordable = state.gold >= spec.cost and state.crystals >= spec.crystals
            else:
                if len(state.hero.army) == state.hero.max_army:
                    self.plan_step += 1
                    continue
                affordable = state.gold >= state.recruit_cost(kind) and state.crystals >= state.recruit_crystal_cost(kind)
            if not affordable:
                return
            self.buy(action, kind)
            self.plan_step += 1
        desired = ('sapper', 'adept') if self.plan == 'control' else ('skyrider', 'warden')
        while len(state.hero.army) < state.hero.max_army:
            kind = next((kind for kind in desired if not any(t.kind == kind for t in state.hero.army)), 'swordsman')
            if state.gold < state.recruit_cost(kind) or state.crystals < state.recruit_crystal_cost(kind):
                return
            self.buy('recruit', kind)


def fixture(seed):
    rng = random.Random(seed)
    if seed % 17 == 0:
        battle = Battle.clash([('ranger', 22), ('militia', 24)], [('archer', 20)], 'plains')
        battle.move(0, (0, 0)); battle.move(1, (-1, 0))
        battle.guard(0); battle.guard(1); battle.end_turn()
        assert battle.unit(0).pinned
        return battle
    kinds = ['militia', 'sapper', 'adept', 'skyrider', 'archer']
    enemies = ['archer', 'sapper', 'adept', 'skyrider', rng.choice(('pikeman', 'guard', 'warden'))]
    if seed % 5 == 4:
        return Battle.clash([(kind, rng.randint(1, UNITS[kind].hp)) for kind in kinds],
                            [(kind, UNITS[kind].hp) for kind in enemies], 'forest', seed)
    hero_class = tuple(HERO_CLASSES)[seed % 4]
    hp = 48 if hero_class == 'Warrior' else 36
    army = [Troop(uid, kind, rng.randint(1, UNITS[kind].hp), UNITS[kind].hp)
            for uid, kind in enumerate(kinds, 1)]
    hero = Hero('Alden', hero_class, (-2, 0), hp // 2, hp, 16, 16, army)
    encounter = (None, 'border_watch', 'last_gate', 'courier_direct', 'courier_guided',
                 'supply_cache', 'vault_crossfire', 'vault_unsealed')[seed % 8]
    return Battle.create(hero, enemies, 'forest', {'bolt', 'heal'}, seed, encounter=encounter,
                         cargo_penalty=int(encounter == 'supply_cache'))


def issue(battle, command, uid, target):
    if command in ('bolt', 'heal'):
        battle.cast(command, target, caster_id=uid)
    elif command == 'evacuate':
        battle.evacuate()
    elif command == 'guard':
        battle.guard(uid)
    else:
        getattr(battle, command)(uid, target)


def exercise(seed, metrics, *, battle=None, checkpoint=None, budget=None):
    rng = random.Random(seed)
    battle = fixture(seed) if battle is None else battle
    metrics['fixture.' + battle.objective.kind] += 1
    metrics['fixture.hero_free'] += battle.hero_id is None
    for _ in range(80):
        if battle.outcome:
            break
        for _ in range(9):
            if budget:
                budget.checkpoint()
            if battle.outcome:
                break
            unit = rng.choice([u for u in battle.units if u.alive and u.team == 'player'])
            options = [('move', pos) for pos in sorted(battle.reachable(unit.id))]
            options += [('smoke', pos) for pos in sorted(battle.smoke_targets(unit.id))]
            for command in ('attack', 'pin', 'swap', 'rally', 'repulse'):
                targets = battle.targets(unit.id) if command == 'attack' else getattr(battle, command + '_targets')(unit.id)
                options += [(command, target.id) for target in targets]
            for spell in ('bolt', 'heal'):
                options += [(spell, target.id) for target in battle.spell_targets(spell, caster_id=unit.id)]
            if not unit.acted:
                options.append(('guard', None))
            if unit.id == battle.hero_id and battle.evacuation_blocked_reason is None:
                options.append(('evacuate', None))
            if not options:
                continue
            rallies = [option for option in options if option[0] == 'rally']
            command, target = rng.choice(rallies if rallies and rng.random() < .5 else options)
            before, actor = battle.to_dict(), asdict(unit)
            target_before = asdict(battle.unit(target)) if isinstance(target, int) else None
            preview = None
            if command in ('attack', 'pin', 'repulse', 'rally', 'smoke'):
                query = battle.preview if command == 'attack' else getattr(battle, command + '_preview')
                preview = query(unit.id, target)
            elif command in ('bolt', 'heal'):
                preview = battle.spell_preview(command, target, caster_id=unit.id)
            assert battle.to_dict() == before, 'Forecast mutated a battle'
            restored = Battle.from_dict(before)
            issue(battle, command, unit.id, target); issue(restored, command, unit.id, target)
            assert battle.to_dict() == restored.to_dict(), 'An order changed after reload'
            if command in ('attack', 'pin'):
                assert (target_before['hp'] - battle.unit(target).hp, actor['hp'] - unit.hp) == preview
            elif command in ('bolt', 'heal'):
                assert abs(target_before['hp'] - battle.unit(target).hp) == preview
            elif command == 'repulse':
                assert asdict(battle.unit(target)) == {**target_before, 'pos': preview}
            elif command == 'rally':
                assert asdict(battle.unit(target)) == {**target_before, 'pinned': False}
                assert battle.reachable(target) == preview.reachable
            elif command == 'smoke':
                assert preview in battle.smoke_clouds
            metrics['order.' + command] += 1
            if unit.id == battle.hero_id:
                metrics['hero_order.' + command] += 1
            metrics['flight_moves'] += command == 'move' and unit.can_fly
            metrics['forecast_checks'] += preview is not None
            if checkpoint is not None:
                checkpoint()
        if not battle.outcome:
            if budget:
                budget.checkpoint()
            restored = Battle.from_dict(battle.to_dict())
            battle.auto_turn(); restored.auto_turn()
            assert battle.to_dict() == restored.to_dict(), 'Automatic policy changed after reload'
            metrics['automatic_rounds'] += 1
            if checkpoint is not None:
                checkpoint()
        alive = [u for u in battle.units if u.alive]
        assert len({u.pos for u in alive}) == len(alive)
        assert all(0 <= u.hp <= u.max_hp and u.effective_move_range >= 1 for u in battle.units)
        assert all(set(u.spent_abilities) <= set(u.abilities) and len(set(u.spent_abilities)) == len(u.spent_abilities) for u in battle.units)
        assert len({c.pos for c in battle.smoke_clouds}) == len(battle.smoke_clouds)
        metrics['invariant_checks'] += 1
    assert battle.outcome is not None, 'Control fixture exceeded 80 phases'
    metrics['outcome.' + battle.outcome_reason] += 1
    for unit in battle.units:
        for ability in unit.spent_abilities:
            metrics['spent.' + unit.team + '.' + ability] += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--battles', type=int, default=200)
    parser.add_argument('--campaign-seeds', type=int, default=5)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--cpu-percent', type=float, default=25,
                        help='cooperative CPU allowance (default: 25; 100 disables yielding)')
    args = parser.parse_args()
    try:
        budget = CpuBudget(args.cpu_percent)
    except ValueError as error:
        parser.error(str(error))
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'),
                      Path(__file__).resolve(), ROOT / 'tools/audit_eador_economy.py',
                      ROOT / 'tools/eador_campaign.py'])
    hashes = {source_name(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    report = {'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'dirty_at_start': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
              'source_sha256': hashes, 'plans': PLANS, 'seed': args.seed, 'battles': args.battles,
              'campaign_seeds': args.campaign_seeds, 'cpu_percent': budget.percent}
    started, metrics, campaigns = time.perf_counter(), Counter(), []
    for seed in range(args.seed, args.seed + args.battles):
        exercise(seed, metrics, budget=budget)
        if (seed - args.seed + 1) % 100 == 0:
            print(f'{seed - args.seed + 1} battle fixtures passed', flush=True)
    for seed in range(args.seed, args.seed + args.campaign_seeds):
        for theme in THEMES:
            for hero_class in HERO_CLASSES:
                for plan in PLANS:
                    campaigns.append(ControlTrial(seed, hero_class, theme, plan, budget=budget).run())
        print(f'{len(campaigns)} campaigns exercised', flush=True)
    report.update(metrics=dict(metrics), campaigns=campaigns, elapsed_seconds=time.perf_counter() - started,
                  source_files_changed=[str(p.relative_to(ROOT)) for p in sources
                                        if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))]])
    assert not report['source_files_changed']
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(metrics, sort_keys=True))
    print(dict(Counter((r['plan'], r['status']) for r in campaigns)))


if __name__ == '__main__':
    main()
