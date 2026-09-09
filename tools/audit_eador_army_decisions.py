"""Compare one disclosed tactical choice from a paid army-plan journal.

Both branches resume the same earned save, resolve the battle and its rewards,
then attempt the existing plan's purchases with their actual remaining funds.
This is a local decision comparison, not a manual campaign or a balance verdict.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.model import State
from tools.eador_sources import framework_sources, source_name
from tools.audit_eador_army_plans import ArmyTrial, PLANS, SavedCommands
from saga2d.testing.cpu_budget import CpuBudget


CASES = {
    'control': dict(
        stage=0, battle=8, command=80,
        journal_sha256='6609eb4f334a956f6d6873e378b0b87bdd6901f3ad2f4688226265b8ede0b72a',
        state_sha256='4eb6076224527ed7a1240f030e8cc0c4f4902af7814eb58813b86277375b72e1',
        orders=(('battle.move', (0, (-2, -1))),
                ('battle.attack', (0, 1011)),
                ('battle.attack', (8, 1011)),
                ('battle.attack', (10, 1011))),
        description='Use three other ready attackers before exposing the wounded Rune Adept to retaliation.'),
    'mobile': dict(
        stage=0, battle=5, command=42,
        journal_sha256='1962ca77a5cbad06de2d81a5591e18d35e5502429dbe0d55b8b07a36bde00d5c',
        state_sha256='6c7f32a60644af8d5d71f04bbbe5b7f340f02ea57b3d3273473dc905ca823691',
        orders=(('battle.move', (4, (-2, 2))), ('battle.guard', (4,))),
        description='Withdraw the wounded Warden and Guard, then resume autoplay; another troop may bear the loss.'),
}


def _branch(initial, plan, orders, budget):
    state = SavedCommands(State.from_json(initial), budget)
    assert state.to_json() == initial, 'The earned input must restore exactly'
    for command, args in orders:
        state.order(command, *args)

    trial = ArmyTrial(state, plan, route=(), budget=budget)
    # Finish with the same autoplay policy, then apply real rewards and choices.
    trial.battle()
    finished = trial.battles[0]['resolved']
    battle = State.from_json(finished).battle
    players = [unit for unit in battle.units if unit.team == 'player']
    resolved = state.to_json()
    purchase_start = len(state.commands)
    trial.invest()
    purchases = [order for order in state.commands[purchase_start:]
                 if order['command'] in ('build', 'recruit', 'replace_troop')]
    missing = Counter(PLANS[plan].roster) - Counter(troop.kind for troop in state.hero.army)
    return dict(
        outcome=battle.outcome, round=battle.round, mana=battle.mana,
        living_hp=sum(unit.hp for unit in players),
        living_max_hp=sum(unit.max_hp for unit in players if unit.hp > 0),
        wounds=sum(unit.max_hp - unit.hp for unit in players if unit.hp > 0),
        battle_hp=[dict(id=unit.id, kind=unit.kind, hp=unit.hp, max_hp=unit.max_hp) for unit in players],
        casualties=[dict(id=unit.id, kind=unit.kind) for unit in players if unit.id != 0 and unit.hp == 0],
        finished_battle=finished, resolved=resolved, replenished=state.to_json(),
        purchase_gold=sum(order['gold_spent'] for order in purchases),
        purchase_crystals=sum(order['crystals_spent'] for order in purchases),
        purchase_commands=purchases, missing_roles=dict(missing), commands=state.commands)


def compare(plan='control', *, cpu_percent=25):
    """Execute one saved decision and its autoplay control through paid replenishment."""
    budget = CpuBudget(cpu_percent)
    case = CASES[plan]
    path = ROOT / 'docs/evidence/shardbound-army-plans-cd351a9' / f'{plan}.json.gz'
    compressed = path.read_bytes()
    journal_hash = hashlib.sha256(compressed).hexdigest()
    assert journal_hash == case['journal_sha256'], 'The source army journal changed'
    journal = json.loads(gzip.decompress(compressed))
    command = journal['commands'][case['command']]
    initial = command['before']
    assert hashlib.sha256(initial.encode()).hexdigest() == case['state_sha256'], 'The selected earned save changed'
    assert command['command'] == 'battle.auto_turn', 'The control must begin with the recorded autoplay command'
    auto = _branch(initial, plan, (('battle.auto_turn', ()),), budget)
    manual = _branch(initial, plan, case['orders'], budget)
    current_after = auto['commands'][0]['after']
    return dict(
        plan=plan, description=case['description'], cpu_percent=cpu_percent,
        policy='One disclosed manual decision versus autoplay from the same earned save; '
               'remaining tactical rounds use autoplay; existing army-plan rewards, equipment and '
               'immediate affordable purchases follow. No rest, journey, injected funds or native input.',
        source=dict(path=str(path.relative_to(ROOT)), journal_sha256=journal_hash,
                    journal_source_commit=journal['source_commit'],
                    stage_index=case['stage'], battle_index=case['battle'],
                    command_index=case['command'], state_sha256=case['state_sha256'],
                    historical_first_after=command['after'],
                    historical_first_after_sha256=hashlib.sha256(command['after'].encode()).hexdigest()),
        current_first_after_sha256=hashlib.sha256(current_after.encode()).hexdigest(),
        historical_first_after_matches_current=current_after == command['after'],
        initial_state=initial, manual_orders=case['orders'], auto=auto, manual=manual)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', choices=CASES, default='control')
    parser.add_argument('--cpu-percent', type=float, default=25)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    paths = [*ROOT.glob('eador/**/*.py'), *framework_sources(),
             *(ROOT / 'tools' / name for name in ('audit_eador_army_decisions.py',
                 'audit_eador_army_plans.py', 'audit_eador_economy.py',
                 'eador_campaign.py'))]
    hashes = {source_name(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    report = compare(args.plan, cpu_percent=args.cpu_percent)
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == value for path, value in hashes.items())
    report.update(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, source_unchanged=True, python_version=sys.version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(args.output, 'wt') as stream:
        json.dump(report, stream, indent=2)
    for name in ('auto', 'manual'):
        branch = report[name]
        print(f"{args.plan} {name}: {branch['outcome']}, round {branch['round']}, "
              f"{len(branch['casualties'])} fallen, {branch['living_hp']} living HP, "
              f"purchased {branch['purchase_gold']} gold / {branch['purchase_crystals']} crystals, "
              f"missing roles {branch['missing_roles']}", flush=True)
    print(args.output, flush=True)


if __name__ == '__main__':
    main()
