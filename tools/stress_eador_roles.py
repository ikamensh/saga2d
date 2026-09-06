#!/usr/bin/env python3
"""Exercise public troop orders in repeatable battle fixtures, not campaign balance claims."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.battle import Battle
from eador.model import HERO_CLASSES, RECRUITABLE, Hero, Troop, UNITS


def fixture(seed, metrics):
    rng = random.Random(seed)
    hero_class = tuple(HERO_CLASSES)[seed % 4]
    kinds = ['healer', 'ranger', 'warden'] + rng.choices(RECRUITABLE, k=seed % 3)
    enemies = ['archer', 'warden', 'ranger'] + rng.choices(('brigand', 'wolf', 'pikeman', 'guard'), k=seed % 4)
    if seed % 4 == 3:
        metrics['fixtures.clash'] += 1
        return Battle.clash([(kind, rng.randint(1, UNITS[kind].hp)) for kind in kinds],
                            [(kind, UNITS[kind].hp) for kind in enemies], 'forest', seed)
    army = [Troop(uid, kind, rng.randint(1, UNITS[kind].hp), UNITS[kind].hp)
            for uid, kind in enumerate(kinds, 1)]
    hp, mana = (48 if hero_class == 'Warrior' else 36), (16 if hero_class == 'Wizard' else 10)
    hero = Hero('Alden', hero_class, (-2, 0), hp // 2, hp, mana, mana, army)
    encounter = (None, 'border_watch', 'last_gate', 'courier_direct', 'courier_guided', 'supply_cache')[seed % 6]
    metrics['fixtures.' + (encounter or 'rout')] += 1
    return Battle.create(hero, enemies, 'forest', {'bolt', 'heal'}, seed, encounter=encounter,
                         cargo_penalty=int(encounter == 'supply_cache' and seed % 2 == 1))


def issue(battle, command, unit_id, target):
    if command in ('move', 'attack', 'pin', 'swap'):
        getattr(battle, command)(unit_id, target)
    elif command == 'evacuate':
        battle.evacuate()
    elif command == 'guard':
        battle.guard(unit_id)
    else:
        battle.cast(command, target, caster_id=unit_id)


def exercise(seed, metrics):
    rng = random.Random(seed)
    battle = fixture(seed, metrics)
    while battle.outcome is None:
        for _ in range(7):
            if battle.outcome:
                break
            unit = rng.choice([u for u in battle.units if u.team == 'player' and u.alive])
            options = [('move', pos) for pos in sorted(battle.reachable(unit.id))]
            options += [(command, target.id) for command, targets in (
                ('attack', battle.targets(unit.id)), ('pin', battle.pin_targets(unit.id)),
                ('swap', battle.swap_targets(unit.id)),
                ('heal', battle.spell_targets('heal', caster_id=unit.id)),
                ('bolt', battle.spell_targets('bolt', caster_id=unit.id))) for target in targets]
            if not unit.acted:
                options.append(('guard', None))
            if unit.id == battle.hero_id and battle.evacuation_blocked_reason is None:
                options.append(('evacuate', None))
            if not options:
                continue
            command, target_id = rng.choice(options)
            before = battle.to_dict()
            restored = Battle.from_dict(before)
            forecast = None
            if command in ('attack', 'pin'):
                forecast = (battle.preview if command == 'attack' else battle.pin_preview)(unit.id, target_id)
                hp = battle.unit(target_id).hp, unit.hp
            elif command in ('heal', 'bolt'):
                forecast = battle.spell_preview(command, target_id, caster_id=unit.id)
                hp = battle.unit(target_id).hp
            assert battle.to_dict() == before, 'A forecast changed the battle'
            if command == 'move' and unit.kind == 'ranger' and unit.acted:
                metrics['ranger_shot_then_moves'] += 1
            issue(battle, command, unit.id, target_id)
            issue(restored, command, unit.id, target_id)
            assert battle.to_dict() == restored.to_dict(), 'Reload changed a commanded order'
            if command in ('attack', 'pin'):
                assert (hp[0] - battle.unit(target_id).hp, hp[1] - unit.hp) == forecast
            elif command in ('heal', 'bolt'):
                assert abs(battle.unit(target_id).hp - hp) == forecast
            metrics['orders.' + command] += 1
            metrics['forecast_checks'] += forecast is not None
        if battle.outcome is None:
            battle.auto_turn()
            metrics['automatic_rounds'] += 1
        saved = battle.to_dict()
        battle = Battle.from_dict(saved)
        assert battle.to_dict() == saved
        alive = [u for u in battle.units if u.alive]
        assert len({u.pos for u in alive}) == len(alive)
        assert all(0 <= u.hp <= u.max_hp and u.effective_move_range >= 1 for u in battle.units)
        assert all(not u.pin_cooldown or u.can_pin for u in battle.units)
        metrics['roundtrip_checks'] += 1
    metrics['outcome.' + battle.outcome_reason] += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=500)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.cases < 1:
        parser.error('--cases must be positive')
    sources = [*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'), Path(__file__).resolve()]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)}
    report = {'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'dirty_at_start': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
              'python': platform.python_version(), 'platform': platform.platform(), 'seed': args.seed,
              'cases': args.cases, 'source_sha256': hashes}
    started = time.perf_counter()
    metrics = Counter()
    for seed in range(args.seed, args.seed + args.cases):
        if (seed - args.seed) % 50 == 0:
            print(f'Battle fixture {seed - args.seed + 1}/{args.cases}', flush=True)
        exercise(seed, metrics)
    report.update(elapsed_seconds=time.perf_counter() - started, metrics=dict(metrics),
                  source_files_changed=[str(p.relative_to(ROOT)) for p in sorted(sources)
                                        if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))]])
    assert not report['source_files_changed']
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(metrics, sort_keys=True))
    print(f'Passed {args.cases} battle fixtures in {report["elapsed_seconds"]:.2f}s')


if __name__ == '__main__':
    main()
