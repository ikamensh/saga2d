"""THROWAWAY: does anchoring versus an occupied push landing earn an extraction variant?

Run this file to replay paid plans; add --step to inspect/advance every order.
Only this process registers the hypothetical source. Its installation into a
copy of an earned campaign is fixture authoring, not a public gameplay action
or a proposed world placement. Purchases, battles, saves and rewards are real.
Delete/absorb after the content decision; this is not a scenario framework.
"""
import argparse
from contextlib import contextmanager
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

from eador.content import AdventureApproach, SITES, SiteSpec
from eador.encounters import ENCOUNTERS, EncounterSpec
from eador.model import RuleError, State, UNITS
from tools.audit_eador_aerie import Purchases
from tools.eador_explorer_campaign import prepare_explorer
from tools.eador_extraction_campaign import AdventureOrders, prepare_adventure


KEY = 'causeway_prototype'
GUARDS = ('adept', 'pikeman', 'ranger', 'guard')
LAYOUT = EncounterSpec(
    'Runebound Causeway — prototype',
    tuple(((q, r), 'marsh' if q in (0, 1) and (q, r) != (0, 0) else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((-3, 0), (-2, -1), (-3, 1), (-2, 0), (-2, 1), (-3, 2), (-2, 2)),
    ((0, 0), (2, -1), (2, 1), (-3, 3)),
    exits=((3, -3),), deadline=5, objective='extract',
)
SITE = SiteSpec(LAYOUT.name, 'Temporary fixture; saved original reward is inherited.',
                GUARDS, 50, 2, 'veil_censer', approaches=(AdventureApproach(
                    'western', 'Western assembly', 'One assembly; compare manual control plans.',
                    KEY, cargo_penalty=1),))


@contextmanager
def hypothetical_content():
    assert KEY not in SITES and KEY not in ENCOUNTERS
    SITES[KEY], ENCOUNTERS[KEY] = SITE, LAYOUT
    try:
        yield
    finally:
        del SITES[KEY]
        del ENCOUNTERS[KEY]


def prepare(hero):
    paid = Purchases(State.new(7, hero))
    if hero == 'Scout':
        prepare_explorer(hero, support=None, state=paid)
    else:
        prepare_adventure(state=paid, support='healer')
    paid.build('mage_tower')
    return paid


def authored_copy(paid):
    """Explicit hypothetical fixture setup; keep original currency, army and reward."""
    state = State.from_json(paid.to_json())
    province = state.provinces[state.hero.pos]
    assert province.owner == 'player' and not province.explored
    province.site, province.site_kind = LAYOUT.name, KEY
    province.site_guards = list(GUARDS)
    province.site_guard_hp = [UNITS[kind].hp for kind in GUARDS]
    return State.from_json(state.to_json())


class Orders(AdventureOrders):
    def __init__(self, state, *, step=False):
        super().__init__(State.from_json(state.to_json()))
        self.initial = json.loads(self.state.to_json())
        self.snapshots, self.forecasts, self.step = [], [], step

    def do(self, command, *args, **kwargs):
        battle = self.battle
        forecast = None
        if command == 'attack':
            attacker, target = (battle.unit(uid) for uid in args)
            hp = target.hp, attacker.hp
            forecast = battle.preview(*args)
        elif command == 'cast':
            target = battle.unit(args[1])
            hp, forecast = target.hp, battle.spell_preview(*args, **kwargs)
        if self.step:
            print('\033[2J\033[H', end='')
            print('Round', battle.round, 'mana', battle.mana, 'outcome', battle.outcome_reason)
            for unit in battle.units:
                print(unit.id, unit.team, unit.kind, unit.pos, f'{unit.hp}/{unit.max_hp}',
                      unit.stance, unit.spent_abilities, 'acted', unit.acted, 'moved', unit.moved)
            print('\n'.join(battle.log[-4:]))
            print('Next:', command, args, kwargs, 'forecast:', forecast)
            if input('[Enter] execute  [q] quit: ').lower() == 'q':
                raise SystemExit(0)
        super().do(command, *args, **kwargs)
        if command == 'attack':
            assert (hp[0] - target.hp, hp[1] - attacker.hp) == forecast
        elif command == 'cast':
            assert abs(target.hp - hp) == forecast
        saved = self.state.to_json()
        self.state = State.from_json(saved)
        assert self.state.to_json() == saved
        self.snapshots.append(json.loads(saved))
        self.forecasts.append(forecast)

    def end(self):
        self.guard_remaining()
        self.do('end_turn')

    def report(self):
        return dict(initial=self.initial, commands=self.orders, snapshots=self.snapshots,
                    forecasts=self.forecasts, rounds=self.battle.round,
                    reason=self.battle.outcome_reason, orders=len(self.orders),
                    exact_reloads=len(self.snapshots),
                    dead=[u.id for u in self.battle.units if u.team == 'player' and not u.alive],
                    wounds=sum(u.max_hp - u.hp for u in self.battle.units if u.team == 'player'),
                    mana_spent=self.state.hero.mana - self.battle.mana)


def opening(play, *, backstop, exposed=False):
    for uid, pos in ((3, (-1, -1)), (4, (-1, 1)), (1, (-2, 2)),
                     (0, (-1, 0)), (5, (-2, 1))):
        play.do('move', uid, pos)
    play.do('attack', 3, play.enemy('adept'))
    play.do('move', 2, (-2, 0) if backstop else (-1, -2))
    if backstop or exposed:
        play.do('cast', 'bolt', play.enemy('adept'))
    play.guard_remaining()
    if exposed:
        assert play.battle.repulse_preview(play.enemy('adept'), 0) == (-2, 0)
    else:
        assert play.battle.unit(0) not in play.battle.repulse_targets(play.enemy('adept'))
    play.do('end_turn')
    assert play.battle.unit(0).pos == ((-2, 0) if exposed else (-1, 0))
    assert ('repulse' in play.battle.unit(play.enemy('adept')).spent_abilities) == exposed


def commander_route(play, *, backstop, heal=False):
    opening(play, backstop=backstop)
    play.do('move', 0, (0, -1))
    play.do('cast', 'bolt', play.enemy('pikeman' if backstop else 'adept'))
    play.do('move', 3, (0, -2)); play.do('attack', 3, play.enemy('adept'))
    play.do('move', 2, (-1, -2) if backstop else (0, -3))
    play.do('move', 4, (0, 0)); play.do('move', 5, (0, 1)); play.do('move', 1, (-1, 0))
    play.end()
    play.do('move', 0, (1, -2)); play.do('cast', 'bolt', play.enemy('pikeman'))
    if backstop:
        play.do('attack', 3, play.enemy('ranger'))
    else:
        play.do('attack', 3, play.enemy('pikeman'))
        play.do('move', 2, (2, -3)); play.do('attack', 2, play.enemy('pikeman'))
    play.do('move', 5, (1, 0)); play.do('attack', 5, play.enemy('ranger'))
    play.do('move', 4, (1, -1))
    if backstop:
        play.do('move', 2, (0, -3))
    play.end()
    play.do('attack', 3, play.enemy('ranger'))
    if not backstop:
        if heal:
            play.do('move', 2, (2, -1)); play.do('attack', 2, play.enemy('ranger'))
        else:
            play.do('attack', 5, play.enemy('ranger'))
    if heal:
        play.do('cast', 'heal', 0, caster_id=5)
    play.do('move', 4, (3, -3)); play.do('move', 0, (2, -2)); play.do('swap', 4, 0)
    assert not play.battle.unit(0).acted and play.battle.outcome is None
    play.do('evacuate')


def focus_route(play, *, heal=False):
    """Independent review's full-shot bypass; kill the Adept before it can act."""
    for uid, pos in ((3, (-1, -1)), (4, (-1, 1)), (1, (-2, 2)),
                     (0, (-1, 0)), (5, (-2, 1)), (2, (-1, -2))):
        play.do('move', uid, pos)
    for uid in (3, 0, 5):
        play.do('attack', uid, play.enemy('adept'))
    assert not play.battle.unit(play.enemy('adept')).alive
    play.end()
    for uid, pos in ((0, (0, -1)), (3, (0, -2)), (2, (0, -3)),
                     (4, (0, 0)), (5, (0, 1)), (1, (-1, 0))):
        play.do('move', uid, pos)
    play.do('attack', 3, play.enemy('ranger')); play.end()
    play.do('move', 0, (1, -2)); play.do('cast', 'bolt', play.enemy('pikeman'))
    play.do('attack', 3, play.enemy('pikeman'))
    play.do('move', 2, (2, -3)); play.do('attack', 2, play.enemy('pikeman'))
    play.do('move', 5, (1, 0)); play.do('attack', 5, play.enemy('ranger'))
    play.do('move', 4, (1, -1)); play.end()
    if heal:
        play.do('cast', 'heal', 0, caster_id=5)
    play.do('move', 4, (3, -3)); play.do('move', 0, (2, -2))
    play.do('swap', 4, 0); play.do('evacuate')


def scout_route(play, *, heal=False):
    for uid, pos in ((3, (-1, -1)), (4, (-1, 1)), (1, (-2, 2)),
                     (0, (0, -1)), (2, (-1, -2))):
        play.do('move', uid, pos)
    play.do('attack', 3, play.enemy('adept')); play.do('attack', 0, play.enemy('adept'))
    assert play.battle.repulse_preview(play.enemy('adept'), 0) == (0, -2)
    play.end()
    assert not play.battle.unit(play.enemy('adept')).spent_abilities
    play.do('move', 3, (0, -2)); play.do('attack', 3, play.enemy('adept'))
    play.do('move', 0, (2, -3)); play.do('attack', 0, play.enemy('ranger'))
    play.do('move', 2, (0, -3)); play.do('move', 4, (0, 0)); play.end()
    play.do('attack', 3, play.enemy('ranger')); play.do('move', 0, (2, -2))
    play.do('cast', 'bolt', play.enemy('pikeman'))
    play.do('move', 2, (2, -3)); play.do('attack', 2, play.enemy('pikeman'))
    play.do('move', 4, (1, -1)); play.end()
    play.do('move', 0, (3, -3))
    if heal:
        play.do('cast', 'heal', 0)
        play.end()
        if play.battle.outcome is None:
            play.do('attack', 3, play.enemy('guard'))
        assert play.battle.outcome_reason == 'rout'
    else:
        play.do('evacuate')


def settle_once(play):
    state = play.state
    gold, crystals, reward = state.gold, state.crystals, state.battle_adventure
    state.resolve_battle()
    assert (state.gold, state.crystals) == (gold + reward.gold, crystals + reward.crystals)
    while state.choice:
        state.choose(state.choice.options[0].id)
    saved = state.to_json()
    assert State.from_json(saved).to_json() == saved
    for command in (state.explore, state.resolve_battle):
        try:
            command()
        except RuleError:
            pass
        else:
            raise AssertionError('The prototype rewarded twice.')
        assert state.to_json() == saved
    return json.loads(saved)


def entered(paid, step):
    state = authored_copy(paid)
    state.explore(approach='western')
    return Orders(state, step=step)


def measure(*, step=False):
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'),
                      *ROOT.joinpath('tools').glob('eador_*.py'),
                      ROOT / 'tools/audit_eador_aerie.py', ROOT / 'tools/audit_eador_extraction.py',
                      ROOT / 'saga2d/hexgrid.py', Path(__file__).resolve()])
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    paid = {hero: prepare(hero) for hero in ('Commander', 'Scout')}
    originals = {hero: state.to_json() for hero, state in paid.items()}
    plans = {}
    for name, hero in (('backstop', 'Commander'), ('guard', 'Commander'), ('scout', 'Scout')):
        play = entered(paid[hero], step)
        if hero == 'Scout':
            scout_route(play)
        else:
            commander_route(play, backstop=name == 'backstop')
        report = play.report()
        assert report['reason'] == 'escape' and report['rounds'] == 4 and not report['dead']
        assert any(u.alive for u in play.battle.units if u.team == 'enemy')
        plans[name] = {**report, 'settled': settle_once(play)}
    assert [(plans[n]['wounds'], plans[n]['mana_spent']) for n in ('backstop', 'guard', 'scout')] == [(28, 12), (34, 8), (41, 4)]

    failure = entered(paid['Commander'], step)
    opening(failure, backstop=False, exposed=True)
    failure.do('attack', 3, failure.enemy('adept'))
    while failure.battle.outcome is None:
        failure.end()
    assert failure.battle.outcome_reason == 'deadline'
    plans['exposed-then-idle'] = failure.report()
    state = failure.state
    origin, gold, crystals, xp = state.hero.pos, state.gold, state.crystals, state.hero.xp
    state.resolve_battle()
    assert (state.gold, state.crystals, state.hero.xp) == (gold - 20, crystals, xp)
    assert state.choice is None and not state.provinces[origin].explored
    assert state.provinces[origin].site_guards == ['pikeman', 'ranger', 'guard']
    assert state.provinces[origin].site_guard_hp == [28, 22, 28]
    saved = state.to_json(); state = State.from_json(saved)
    assert state.to_json() == saved
    plans['exposed-then-idle']['settled'] = json.loads(saved)
    rests = []
    for _ in range(3):
        state.end_turn()
        assert state.battle is None and state.status == 'playing' and state.hero.pos == origin
        saved = state.to_json(); state = State.from_json(saved)
        assert state.to_json() == saved
        rests.append(json.loads(saved))
    state.explore(approach='western')
    retry = Orders(state, step=step)
    assert [(u.kind, u.hp) for u in retry.battle.units if u.team == 'enemy'] == [('pikeman', 28), ('ranger', 22), ('guard', 28)]
    for _ in range(16):
        if retry.battle.outcome:
            break
        retry.do('auto_turn')
    assert retry.battle.outcome_reason == 'rout'
    plans['finite-retry-auto'] = {**retry.report(), 'recovery_turns': rests, 'settled': settle_once(retry)}
    assert all(state.to_json() == originals[hero] for hero, state in paid.items())
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in hashes.items())
    return dict(source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                source_sha256=hashes, python=platform.python_version(), platform=platform.platform(),
                layout=asdict(LAYOUT), site=asdict(SITE), plans=plans,
                parties={hero: dict(snapshot=json.loads(originals[hero]), purchases=state.purchases)
                         for hero, state in paid.items()},
                scope='Temporary registered content in copied earned campaigns; no production placement, native, balance-matrix or optimal-play claim. Retry explicitly uses auto; first three wins use manual orders.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/causeway-prototype.json.gz'))
    parser.add_argument('--step', action='store_true', help='Inspect each manual/auto order and advance with Enter.')
    args = parser.parse_args()
    with hypothetical_content():
        report = measure(step=args.step)
    payload = (json.dumps(report, separators=(',', ':')) + '\n').encode()
    args.output.write_bytes(gzip.compress(payload, mtime=0) if args.output.suffix == '.gz' else payload)
    for name, result in report['plans'].items():
        print(name, result['reason'], 'round', result['rounds'], 'wounds', result['wounds'],
              'mana', result['mana_spent'], 'orders/reloads', result['orders'], result['exact_reloads'])
    print('Report:', args.output)


if __name__ == '__main__':
    main()
