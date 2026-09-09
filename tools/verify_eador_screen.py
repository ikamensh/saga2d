"""Buy Screen parties and replay their exact orders through native or mock controls."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from saga2d import Label
from eador.app import create_game
from eador.codex import CodexScene
from eador.encounter_scene import EncounterScene
from eador.preferences import reading_scale
from eador.scene import BattleScene, ChoiceScene, ResultScene, ShardScene, TitleScene
from tools.eador_sources import source_name
from tools.audit_eador_extraction import PaidState
from tools.eador_screen_campaign import (prepare_screen, screen_western_route,
                                          screen_northern_route, screen_scout_route, screen_scout_opening)
from tools.eador_ui import PlayerInput
from tools.verify_eador_control import ControlOrders
from tools.verify_eador_guidance import check_reading_layout
from tools.verify_eador_reading import check_page

PLANS = ('western', 'western-heal', 'northern', 'scout', 'failed-retry')


class ScreenOrders(ControlOrders):
    """Use the existing exact control adapter, with Screen-specific saved milestones."""
    def __init__(self, state):
        self.rallied_after_shooting = False
        self.sapper_denied_before_charge = False
        self.smoke_seen = []
        super().__init__(state)
        self.player.capture('screen-deployment')

    def do(self, command, *args, **kwargs):
        target = self.battle.unit(args[1]) if command == 'attack' else None
        if command == 'rally':
            ranger = self.battle.unit(args[1])
            assert ranger.acted and not ranger.moved and ranger.pinned
            self.rallied_after_shooting = True
        super().do(command, *args, **kwargs)
        if command == 'rally':
            self.select(args[1])
            assert self.battle.unit(args[1]).acted and not self.battle.unit(args[1]).moved
            self.player.capture('rallied-ranger-keeps-unused-move')
        if command == 'move' and args == (5, (2, -3)):
            self.player.capture('northern-ranger-flank')
            self.player.reload(self.state.to_json())
        if target is not None and target.kind == 'sapper' and not target.alive and self.battle.round == 1:
            assert 'smoke' not in target.spent_abilities and not self.battle.smoke_clouds
            self.sapper_denied_before_charge = True
            self.player.capture('sapper-defeated-before-charge')
            self.player.reload(self.state.to_json())
        if command == 'end_turn' and isinstance(self.player.game.scene, BattleScene):
            if self.battle.smoke_clouds:
                self.smoke_seen.extend(cloud.pos for cloud in self.battle.smoke_clouds)
                sapper = next(unit for unit in self.battle.units if unit.kind == 'sapper')
                assert sapper.spent_abilities == ('smoke',)
                self.select(5)
            self.player.capture(f'round-{self.battle.round}-after-enemies')


def inspect_briefing(player):
    """Review both deployments, text setting and finite ability details without entering."""
    before = player.state.to_json()
    player.press('x')
    assert isinstance(player.game.scene, EncounterScene)
    player.press('t'); player.press('right'); player.button('Apply')
    assert reading_scale(player.game) == 125
    for index, approach in enumerate(player.game.scene.approaches):
        player.press(str(index + 1))
        text = '\n'.join(label.text for label in player.game.scene.ui.find_all(lambda item: isinstance(item, Label)))
        guards = player.state.provinces[player.state.hero.pos].site_guards
        assert ('one Smoke charge' in text) == ('sapper' in guards)
        assert ('Warden swaps' in text) == ('warden' in guards)
        if 'guard' not in guards:
            assert 'southern Guard' not in text
        if guards.count('archer') < 2:
            assert 'northern bowmen' not in text
        if 'sapper' in guards:
            assert 'both sides' in text
        assert 'Defeated guards stay defeated' in text
        check_reading_layout(player.game.scene)
        assert player.state.to_json() == before
        player.capture(f'briefing-{approach.id}-125')
    player.press('c')
    assert isinstance(player.game.scene, CodexScene)
    player.press('2')
    for _ in range(player.game.scene.pages):
        if any(entry.title == 'Smoke' for entry in player.game.scene.visible_entries):
            break
        player.press('right')
    assert any(entry.title == 'Smoke' for entry in player.game.scene.visible_entries)
    check_page(player.game.scene)
    player.capture('codex-finite-smoke-125')
    player.press('escape')
    assert isinstance(player.game.scene, EncounterScene)
    player.press('escape')
    assert isinstance(player.game.scene, ShardScene) and player.state.to_json() == before
    player.reload(before)


def failed_retry(state):
    """A real lost Scout attempt, paid recovery and a manual finite-roster retry."""
    from tools.eador_campaign import rest, march_to

    player = state.player
    source = state.hero.pos
    output = player.output
    player.output = output / 'failed-attempt'
    state.explore(approach='northern')
    p = ScreenOrders(state)
    screen_scout_opening(p)
    for _ in range(80):
        if p.battle.outcome:
            break
        p.guard_remaining(); p.do('end_turn')
    assert p.battle.outcome_reason == 'hero_death' and p.battle.round == 53
    player.capture('hero-defeat-and-casualties')
    dead = [u.id for u in p.battle.units if u.team == 'player' and not u.alive and u.id != 0]
    assert dead == [1, 2, 3, 4, 5]
    failed_round = p.battle.round
    xp, gold, crystals, turn = state.hero.xp, state.gold, state.crystals, state.turn
    state.resolve_battle()
    assert state.hero.xp == xp and (state.gold, state.crystals) == (gold - 20, crystals)
    assert state.choice is None and not state.provinces[source].explored
    assert state.provinces[source].site_guards == ['archer']
    assert state.provinces[source].site_guard_hp == [20]
    player.reload(state.to_json())
    player.capture('saved-loss-before-replacements')
    paid_before = state.recruitment_gold
    for _ in range(32):
        assert state.status == 'playing'
        if len(state.hero.army) < state.hero.max_army and state.gold >= state.recruit_cost('swordsman'):
            state.recruit('swordsman')
        march_to(state, source)
        if (state.hero.pos == source and state.actions_left and len(state.hero.army) >= 4
                and state.hero.hp == state.hero.max_hp and all(t.hp == t.max_hp for t in state.hero.army)):
            break
        rest(state)
    else:
        raise AssertionError('Could not return to the Screen with the paid replacement party recovered')
    replacement_gold = state.recruitment_gold - paid_before
    assert replacement_gold == 180 and not set(dead).intersection(t.id for t in state.hero.army)
    assert [troop.kind for troop in state.hero.army] == ['swordsman'] * 4
    replacement_ids = [troop.id for troop in state.hero.army]
    player.output = output / 'retry'
    inspect_briefing(player)
    entry_gold, entry_crystals, entry_mana = state.gold, state.crystals, state.hero.mana
    state.explore(approach='western')
    p_retry = ScreenOrders(state)
    assert [(u.kind, u.hp) for u in p_retry.battle.units if u.team == 'enemy'] == [('archer', 20)]
    bowman = p_retry.enemy('archer')
    # The old Warden died. Advance the first purchased Swordsman, freeing
    # the Scout's exit, then concentrate sword and bow on the saved survivor.
    front = replacement_ids[0]
    p_retry.do('move', front, (0, 0)); p_retry.do('attack', front, bowman)
    p_retry.do('move', 0, (-1, 0)); p_retry.do('attack', 0, bowman)
    assert p_retry.battle.outcome_reason == 'rout'
    return p_retry, dict(approach='northern', outcome_reason='hero_death', round=failed_round, campaign_turn=turn,
                         dead_troop_ids=dead, retreat_gold=20, replacement_gold=replacement_gold,
                         replacement_troop_ids=replacement_ids,
                         guards_on_retry=[['archer', 20]], orders=p.orders, reward_before_retry=False,
                         entry_gold=entry_gold, entry_crystals=entry_crystals, entry_mana=entry_mana)


def verify(output, *, backend='pyglet', plan='western'):
    output.mkdir(parents=True, exist_ok=True)
    sources = sorted([*ROOT.joinpath('eador').glob('*.py'), *ROOT.joinpath('saga2d').rglob('*.py'),
                      *[ROOT / 'tools' / name for name in (
                          'eador_campaign.py', 'eador_extraction_campaign.py', 'eador_control_campaign.py',
                          'eador_roles_campaign.py', 'eador_screen_campaign.py', 'audit_eador_extraction.py',
                          'eador_ui.py', 'verify_eador_extraction.py', 'verify_eador_control.py',
                          'verify_eador_guidance.py', 'verify_eador_reading.py', 'verify_eador_screen.py')]])
    hashes = {source_name(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines()
    started = perf_counter()
    hero = 'Scout' if plan in ('scout', 'failed-retry') else 'Commander'
    approach = 'northern' if plan in ('northern', 'scout') else 'western'
    with TemporaryDirectory(prefix='shardbound-screen-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            game.push(TitleScene(7, hero_class=hero, theme='elderwild'))
            player.press('return')
            state = PaidState(player.state)
            prepare_screen(hero, state=state)
            inspect_briefing(player)
            gold, crystals, mana = state.gold, state.crystals, state.hero.mana
            failure = None
            if plan == 'failed-retry':
                play, failure = failed_retry(state)
                gold, crystals, mana = (failure[key] for key in ('entry_gold', 'entry_crystals', 'entry_mana'))
            elif plan in ('western', 'western-heal'):
                play = screen_western_route(state, heal=plan == 'western-heal', orders_type=ScreenOrders)
            else:
                play = (screen_scout_route if plan == 'scout' else screen_northern_route)(state, orders_type=ScreenOrders)
            battle, reward = state.battle, state.battle_adventure
            assert battle.outcome_reason == 'rout' and isinstance(game.scene, ResultScene)
            assert all(u.alive for u in battle.units if u.team == 'player')
            assert (state.gold, state.crystals) == (gold, crystals)
            player.capture('screen-rout-victory')
            player.reload(state.to_json())
            battle = state.battle
            survivors = [dict(kind=u.kind, hp=u.hp, max_hp=u.max_hp) for u in battle.units if u.team == 'player']
            report = dict(plan=plan, hero=hero, approach=approach, backend=backend,
                          logical_resolution=game.resolution, window_size=game.window_size,
                          framebuffer_size=game.backend.capture_frame().size if backend == 'pyglet' else None,
                          failed_attempt=failure,
                          reading_scale=reading_scale(game), briefing_checked=True,
                          campaign_turn=state.turn, battle_rounds=battle.round, outcome_reason=battle.outcome_reason,
                          fee_gold=0, fee_crystals=0, building_gold=state.building_gold,
                          recruitment_gold=state.recruitment_gold, reward_gold=reward.gold,
                          reward_crystals=reward.crystals, reward_relic=reward.relic,
                          mana_spent=mana - battle.mana, survivors=survivors, troops_lost=0,
                          hp_deficit=sum(u['max_hp'] - u['hp'] for u in survivors),
                          rallied_after_shooting=play.rallied_after_shooting,
                          sapper_denied_before_charge=play.sapper_denied_before_charge, smoke_seen=play.smoke_seen)
            pos = state.hero.pos
            state.resolve_battle()
            assert (state.gold, state.crystals) == (gold + reward.gold, crystals + reward.crystals)
            while isinstance(game.scene, ChoiceScene):
                player.press('1')
            assert state.provinces[pos].explored and reward.relic in state.inventory
            before = state.to_json()
            player.press('x')
            assert state.to_json() == before and isinstance(game.scene, ShardScene)
            player.reload(before)
            player.capture('screen-reward-kept-once')
            changed = [name for name, digest in hashes.items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
            assert not changed
            report.update(input_activations=len(player.events), exact_save_reloads=player.reloads,
                          orders=play.orders, inputs=player.events, source_revision=revision,
                          dirty_at_start=dirty, source_sha256=hashes, source_files_changed=changed,
                          elapsed_seconds=perf_counter() - started, python=platform.python_version(), platform=platform.platform())
            (output / 'journey.json').write_text(json.dumps(report, indent=2) + '\n')
            print(f'Screen/{plan}: round {report["battle_rounds"]}, {len(player.events)} inputs, '
                  f'{player.reloads} exact reloads ({backend})', flush=True)
            return report
        finally:
            game.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-screen'))
    parser.add_argument('--plan', choices=PLANS, default='western')
    args = parser.parse_args()
    verify(args.output, plan=args.plan)
