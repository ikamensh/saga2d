"""Two earned Vault approaches followed through a production capture and rival operation.

The Vault uses its existing manual routes. Later battles use explicit autoplay;
this bounded comparison measures campaign consequences, not optimal tactics.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.model import State
from tools.eador_sources import framework_sources, source_name
from tools.audit_eador_army_plans import SavedCommands
from saga2d.testing.cpu_budget import CpuBudget
from tools.eador_extraction_campaign import AdventureOrders
from tools.eador_vault_campaign import prepare_vault, vault_route

TARGET = (0, 0)


class _PreparationBattle:
    """Let the existing preparation helper record its automatic rounds through SavedCommands."""
    def __init__(self, saved):
        self.saved = saved

    def __getattr__(self, name):
        return getattr(self.saved.state.battle, name)

    def auto_turn(self):
        return self.saved.order('battle.auto_turn')


class _Preparation(SavedCommands):
    @property
    def battle(self):
        return _PreparationBattle(self) if self.state.battle is not None else None


class _ManualOrders(AdventureOrders):
    def do(self, command, *args, **kwargs):
        self.state.order('battle.' + command, *args, **kwargs)
        self.orders.append((command, args, kwargs))


def _snapshot(state):
    return dict(turn=state.turn, status=state.status, gold=state.gold, crystals=state.crystals,
                actions=state.actions_left, hero=asdict(state.hero), rival=asdict(state.rival),
                income=state.income, crystal_income=state.crystal_income, upkeep=state.upkeep,
                buildings=sorted(state.buildings), inventory=list(state.inventory),
                recovery=asdict(state.recovery_preview()), infusion=asdict(state.infusion_preview()),
                provinces=[dict(pos=p.pos, owner=p.owner, guards=list(p.guards),
                                guard_hp=list(p.guard_hp), explored=p.explored)
                           for p in state.provinces.values()])


def _settle(state, before, tactics):
    """Resolve a finished battle and real first-option rewards, keeping the equipped relic."""
    battle = state.battle
    assert battle.outcome is not None
    initial = State.from_json(before)
    players = [unit for unit in battle.units if unit.team == 'player']
    dead = {unit.id for unit in players if unit.id != 0 and not unit.alive}
    record = dict(kind=state.battle_kind, province=state.battle_province,
                  encounter=state.battle_encounter, tactics=tactics,
                  turn=state.turn, round=battle.round, outcome=battle.outcome,
                  reason=battle.outcome_reason, before=before, finished_state=state.to_json(),
                  mana_spent=initial.battle.mana - battle.mana,
                  living_hp=sum(unit.hp for unit in players),
                  living_max_hp=sum(unit.max_hp for unit in players if unit.alive),
                  wounds=sum(unit.max_hp - unit.hp for unit in players if unit.alive),
                  casualties=[asdict(troop) for troop in initial.hero.army if troop.id in dead])
    if state.battle_adventure is not None:
        record['adventure_reward'] = asdict(state.battle_adventure)
    state.resolve_battle()
    record['reward_state'] = state.to_json()
    while state.choice:
        state.choose(state.choice.options[0].id)
    record['resolved_state'] = state.to_json()
    return record


def _automatic_battle(state):
    before = state.to_json()
    for _ in range(80):
        if state.battle.outcome is not None:
            break
        state.order('battle.auto_turn')
    assert state.battle.outcome is not None, 'Autoplay exceeded its 80-round bound'
    return _settle(state, before, 'Explicit public autoplay')


def _threat_step(state):
    """Intercept an imminent attack on owned land only when its current position is reachable."""
    rival = state.rival
    if (not rival.army or rival.intent != 'attack' or rival.turns_until_action > 1
            or rival.target is None or state.provinces[rival.target].owner != 'player'):
        return None
    path = state.grid.path(state.hero.pos, rival.pos)
    if 1 < len(path) <= state.actions_left + 1:
        return path[1]
    return None


def _continue(state, entry, mana_reserve, limit):
    """Make at most limit campaign orders, resolving every resulting battle before stopping."""
    desired = [troop.kind for troop in entry.hero.army]
    battles, turns, purchases, decisions = [], [], [], []
    captured = None
    rival_after_capture = False
    stop_reason = 'campaign_order_bound'
    for _ in range(limit):
        if state.status != 'playing':
            stop_reason = state.status
            break
        if captured is not None and rival_after_capture:
            stop_reason = 'objective_and_rival_operation'
            break

        before = _snapshot(state)
        threat = _threat_step(state)
        missing = Counter(desired) - Counter(troop.kind for troop in state.hero.army)
        replacement = next((kind for kind in desired if missing[kind]
                            and state.gold >= state.recruit_cost(kind)
                            and state.crystals >= state.recruit_crystal_cost(kind)), None)
        wounds = max([state.hero.max_hp - state.hero.hp]
                     + [troop.max_hp - troop.hp for troop in state.hero.army])
        if threat is not None:
            command, args, reason = 'travel', (threat,), 'Intercept the currently reachable imminent attack before elective recovery'
        elif (replacement is not None
              and state.provinces[state.hero.pos].owner == 'player'):
            command, args, reason = 'recruit', (replacement,), 'Buy an affordable missing entry-roster role at its ordinary price'
        elif captured is not None:
            command, args, reason = 'end_turn', (), 'Observe the next announced rival operation after production capture'
        elif not state.actions_left:
            command, args, reason = 'end_turn', (), 'Restore exhausted campaign actions'
        elif wounds > 6 or state.hero.mana < mana_reserve:
            command, args, reason = 'end_turn', (), 'Recover to at most six missing HP per survivor and one Heal reserve'
        else:
            path = state.grid.path(state.hero.pos, TARGET)
            assert len(path) > 1, 'An uncaptured target cannot already contain the hero'
            command, args, reason = 'travel', (path[1],), 'Advance toward the production province; leave its adventure unexplored'

        state.order(command, *args)
        order_index = len(state.commands) - 1
        after_order = _snapshot(state)
        decisions.append(dict(command_index=order_index, reason=reason, before=before, after_order=after_order))
        if command == 'recruit':
            purchases.append(state.commands[order_index])
        if command == 'end_turn':
            # End-turn income/recovery happens before the rival and any resulting
            # hero battle. Keep that intermediate state instead of conflating it
            # with subsequent rewards, advancement healing or combat casualties.
            operated = before['rival']['turns_until_action'] <= 1
            before_troops = {troop['id']: troop for troop in before['hero']['army']}
            surviving_ids = {troop.id for troop in state.hero.army}
            turns.append(dict(command_index=order_index, reason=reason,
                              before=before, after_order=after_order,
                              gold_received=state.gold - before['gold'],
                              crystals_received=state.crystals - before['crystals'],
                              hero_hp_recovered=state.hero.hp - before['hero']['hp'],
                              army_hp_recovered=sum(troop.hp - before_troops[troop.id]['hp']
                                                    for troop in state.hero.army),
                              mana_recovered=state.hero.mana - before['hero']['mana'],
                              deserters=[troop for uid, troop in before_troops.items() if uid not in surviving_ids],
                              rival_operation_due=operated,
                              campaign_log=json.loads(state.commands[order_index]['after'])['log'][
                                  len(json.loads(state.commands[order_index]['before'])['log']):]))
            if captured is not None and operated:
                rival_after_capture = True
        if state.battle is not None:
            battles.append(_automatic_battle(state))
        if captured is None and state.provinces[TARGET].owner == 'player':
            captured = dict(command_index=order_index, state=state.to_json(), summary=_snapshot(state))
    else:
        if captured is not None and rival_after_capture:
            stop_reason = 'objective_and_rival_operation'
        elif state.status != 'playing':
            stop_reason = state.status
    return dict(stop_reason=stop_reason, campaign_orders=len(decisions), decisions=decisions,
                capture=captured, rival_operation_after_capture=rival_after_capture,
                target_held_at_end=state.provinces[TARGET].owner == 'player',
                end_turns=turns, battles=battles, replacement_purchases=purchases,
                replacement_gold=sum(order['gold_spent'] for order in purchases),
                replacement_crystals=sum(order['crystals_spent'] for order in purchases))


def compare(*, cpu_percent=25, campaign_order_limit=24):
    """Compare one paid and one free manual Vault escape from exactly the same earned entry."""
    if type(campaign_order_limit) is not int or campaign_order_limit < 1:
        raise ValueError('Campaign order limit must be a positive integer')
    budget = CpuBudget(cpu_percent)
    prepared = _Preparation(State.new(7, 'Commander', theme='ruins'), budget)
    initial = prepared.to_json()
    prepare_vault(state=prepared, budget=budget)
    entry_json = prepared.to_json()
    entry = State.from_json(entry_json)
    assert entry.provinces[TARGET].owner != 'player', 'The selected next production objective is already owned'
    assert entry.provinces[entry.hero.pos].site_kind == 'sealed_vault'
    branches = {}
    for approach in ('crossfire', 'unseal'):
        state = SavedCommands(State.from_json(entry_json), budget)
        vault_route(state, approach, orders_type=_ManualOrders)
        entry_order = state.commands[0]
        mana_reserve = state.battle.spell_cost('heal')
        vault = _settle(state, entry_order['after'], 'Existing explicit manual Vault route')
        assert State.from_json(vault['reward_state']).provinces[entry.hero.pos].explored
        continuation = _continue(state, entry, mana_reserve, campaign_order_limit)
        branches[approach] = dict(entry_fee_gold=entry_order['gold_spent'],
                                 entry_fee_crystals=entry_order['crystals_spent'],
                                 mana_reserve=mana_reserve, vault=vault, **continuation,
                                 campaign_turns=state.turn - entry.turn,
                                 final=_snapshot(state), final_state=state.to_json(), commands=state.commands)
    return dict(seed=7, hero='Commander', theme='ruins', cpu_percent=cpu_percent,
                campaign_order_limit=campaign_order_limit, initial_state=initial,
                preparation_commands=prepared.commands, entry_state=entry_json,
                entry_sha256=hashlib.sha256(entry_json.encode()).hexdigest(), entry=_snapshot(entry),
                target=asdict(entry.provinces[TARGET]), branches=branches,
                policy='Ordinary paid seed-seven Warden/Ranger preparation; same saved entry and existing manual Vault routes. '
                       'Keep the equipped relic; take first offered rewards. Then capture production at (0,0), '
                       'without exploring its adventure, and observe the first rival operation due after capture. '
                       'Before elective healing, intercept an imminent attack on owned land if the current expedition '
                       'is reachable with remaining actions; re-read its position each order. Restore only missing '
                       'entry-roster roles when affordable, at normal prices; do not fill an unused capacity slot. '
                       'Otherwise recover to at most six missing HP per living combatant and one actual Heal cost '
                       'of mana before advancing. Quote but do not buy Infusion; no Tower investment. Later battles '
                       'use explicit autoplay. The campaign order bound excludes tactical rounds and reward resolution. '
                       'No injected resources, troop edits, source-site edits, native input or optimal-play claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cpu-percent', type=float, default=25)
    parser.add_argument('--campaign-order-limit', type=int, default=24)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    paths = [*ROOT.glob('eador/**/*.py'), *framework_sources(),
             *(ROOT / 'tools' / name for name in ('audit_eador_vault_continuation.py',
                 'audit_eador_army_plans.py', 'audit_eador_economy.py', 'eador_vault_campaign.py',
                 'eador_extraction_campaign.py', 'eador_roles_campaign.py', 'eador_campaign.py'))]
    hashes = {source_name(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    started = time.monotonic()
    report = compare(cpu_percent=args.cpu_percent, campaign_order_limit=args.campaign_order_limit)
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == value for path, value in hashes.items()), 'Source changed during the comparison'
    report.update(source_commit=revision, source_sha256=hashes, source_unchanged=True,
                  python=sys.version, platform=platform.platform(), elapsed_seconds=time.monotonic() - started)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(args.output, 'wt') as stream:
        json.dump(report, stream, indent=2)
    for name, branch in report['branches'].items():
        print(f"{name}: {branch['stop_reason']}; {branch['campaign_turns']} campaign turns, "
              f"{len(branch['end_turns'])} rests, {branch['replacement_gold']} replacement gold; "
              f"{branch['final']['gold']} gold / {branch['final']['crystals']} crystals left", flush=True)
    print(args.output, flush=True)


if __name__ == '__main__':
    main()
