"""A directed command journal must reproduce actual game input and saved continuation."""
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from eador.model import State
from tools.audit_eador_army_plans import SavedCommands
from saga2d.testing.cpu_budget import CpuBudget


ROOT = Path(__file__).resolve().parents[2]


def earned_report(anchor='control', *, skill='pathfinder'):
    """Prepare real commands from one fixed, earned opening without replaying its campaign."""
    index = {'control': 38, 'mobile': 14}[anchor]
    path = ROOT / f'docs/evidence/shardbound-army-plans-cd351a9/{anchor}.json.gz'
    blob = path.read_bytes()
    history = json.loads(gzip.decompress(blob))
    initial = history['commands'][index]['before']
    played = SavedCommands(State.from_json(initial), CpuBudget(100))
    commands = (
        ('infuse', (), {}),
        ('travel', ((0, -1),), {}),
        ('battle.cast', ('heal', 4), {'caster_id': 5}),
        ('battle.guard', (0,), {}),
        ('battle.end_turn', (), {}),
    ) if anchor == 'control' else (('choose', (skill,), {}),)
    for command, args, kwargs in commands:
        played.order(command, *args, **kwargs)
        played.commands[-1]['reason'] = 'Exercise the recorded public command through real input.'
    return dict(
        source=dict(path=str(path.relative_to(ROOT)), journal_sha256=hashlib.sha256(blob).hexdigest(),
                    journal_source=history['source_commit'], command_index=index,
                    initial_sha256=hashlib.sha256(initial.encode()).hexdigest()),
        execution_source='test working source',
        source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py')]},
        initial_state=initial, final_state=played.state.to_json(), commands=played.commands,
    )


def fresh_report(seed=5):
    """Record a paid opening from exactly the state produced by starting a new campaign."""
    state = State.new_campaign(seed, 'Commander')
    initial = state.to_json()
    played = SavedCommands(state, CpuBudget(100))
    for command, args in (('build', ('barracks',)), ('recruit', ('warden',)),
                          ('explore', ()), ('battle.guard', (0,))):
        played.order(command, *args)
        played.commands[-1]['reason'] = 'Buy a starting formation and enter the actual home shrine.'
    return dict(
        source=dict(kind='new_campaign', seed=seed, hero_class='Commander', difficulty='standard',
                    initial_sha256=hashlib.sha256(initial.encode()).hexdigest()),
        execution_source='test working source',
        source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py')]},
        initial_state=initial, final_state=played.state.to_json(), commands=played.commands,
    )


def test_fresh_campaign_journal_starts_through_title_and_pays_for_its_army(tmp_path):
    """A generated opening must be reproduced by New Campaign input, before any save is loaded."""
    from tools.verify_eador_directed_journey import verify

    source = fresh_report()
    path = tmp_path / 'fresh.json.gz'
    path.write_bytes(gzip.compress(json.dumps(source).encode()))
    result = verify(path, tmp_path / 'verified', backend='mock')
    assert result['inputs'][0] == ('TitleScene', 'key', 'l')
    assert result['final_state'] == source['final_state']
    assert result['reloads'] == result['exact_commands'] == 4
    assert State.from_json(result['final_state']).gold == 0
    assert 'fresh campaign' in result['scope'] and 'historical autoplay' not in result['scope']


def test_directed_journal_replays_infusion_and_acolyte_cast_through_saved_input(tmp_path):
    """Campaign investment, the chosen caster, Guard and enemy response match after every F5/F9."""
    from tools.verify_eador_directed_journey import verify

    source = earned_report()
    path = tmp_path / 'directed.json.gz'
    path.write_bytes(gzip.compress(json.dumps(source).encode()))
    result = verify(path, tmp_path / 'verified', backend='mock')
    assert result['final_state'] == source['final_state']
    assert result['reloads'] == result['exact_commands'] == len(source['commands'])
    assert result['input_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result['source_unchanged']
    assert 'historical autoplay opening' in result['scope']


@pytest.mark.parametrize('skill', ['pathfinder', 'skirmisher'])
def test_scout_journal_replays_the_earned_skill_choice_through_saved_input(tmp_path, skill):
    """Either first Scout discipline is earned through ChoiceScene and survives actual F5/F9 controls."""
    from tools.verify_eador_directed_journey import verify

    source = earned_report('mobile', skill=skill)
    initial = State.from_json(source['initial_state'])
    assert initial.hero.hero_class == 'Scout' and initial.hero.skill_ranks == {}
    assert initial.choice.kind == 'skill'
    path = tmp_path / 'scout.json.gz'
    path.write_bytes(gzip.compress(json.dumps(source).encode()))
    result = verify(path, tmp_path / 'verified', backend='mock')
    final = State.from_json(result['final_state'])
    assert final.hero.skill_ranks == {skill: 1} and final.choice is None
    assert (final.hero.level, final.hero.xp) == (initial.hero.level, initial.hero.xp)
    assert result['final_state'] == source['final_state']
    assert result['reloads'] == result['exact_commands'] == 1
    assert result['input_source'] == source['source'] and result['source_unchanged']


def test_scout_replay_captures_the_first_warden_swap(tmp_path):
    """The tactical action gets its own indexed capture while saved input remains exact."""
    from tools.verify_eador_directed_journey import verify

    source = earned_report('mobile')
    played = SavedCommands(State.from_json(source['final_state']), CpuBudget(100))
    for command, args in (('explore', ()), ('battle.swap', (4, 3))):
        played.order(command, *args)
        played.commands[-1]['reason'] = 'Observe the earned Warden swap in the nearby shrine.'
    source['commands'].extend(played.commands)
    source['final_state'] = played.state.to_json()
    path = tmp_path / 'scout-swap.json.gz'
    path.write_bytes(gzip.compress(json.dumps(source).encode()))
    result = verify(path, tmp_path / 'verified', backend='mock')
    assert result['captures'] == ['003-battle-swap', 'final-state']
    assert result['final_state'] == source['final_state']
    assert result['reloads'] == result['exact_commands'] == 3


@pytest.mark.parametrize('anchor', ['control', 'mobile'])
@pytest.mark.parametrize('tamper', ('opening', 'source_index', 'source_path', 'source_hash',
                                   'model', 'chain', 'autoplay', 'query', 'final'))
def test_directed_replay_rejects_unearned_stale_or_automatic_journals(tmp_path, anchor, tamper):
    """Self-consistent hashes cannot authenticate a fabricated opening or replace explicit commands."""
    from tools.verify_eador_directed_journey import verify

    source = earned_report(anchor)
    if tamper == 'opening':
        source['initial_state'] = source['commands'][0]['after']
        source['source']['initial_sha256'] = hashlib.sha256(source['initial_state'].encode()).hexdigest()
    elif tamper == 'source_index':
        # Even a legal, exactly saved continuation from the next earned command
        # must not let the journal choose a different authentication checkpoint.
        history = json.loads(gzip.decompress((ROOT / source['source']['path']).read_bytes()))
        index = source['source']['command_index'] + 1
        initial = history['commands'][index]['before']
        played = SavedCommands(State.from_json(initial), CpuBudget(100))
        played.order('end_turn')
        played.commands[-1]['reason'] = 'Continue from a different earned command.'
        source.update(initial_state=initial, final_state=played.state.to_json(), commands=played.commands)
        source['source'].update(command_index=index, initial_sha256=hashlib.sha256(initial.encode()).hexdigest())
    elif tamper == 'source_path':
        # Matching bytes and provenance elsewhere do not authorize arbitrary file reads.
        copied = tmp_path / 'copied-opening.json.gz'
        copied.write_bytes((ROOT / source['source']['path']).read_bytes())
        source['source']['path'] = str(copied)
    elif tamper == 'source_hash':
        source['source']['journal_sha256'] = '0' * 64
    elif tamper == 'model':
        source['source_sha256']['eador/model.py'] = '0' * 64
    elif tamper == 'chain':
        source['commands'][0]['before'] = source['commands'][0]['after']
    elif tamper == 'autoplay':
        source['commands'][0]['command'] = 'battle.auto_turn'
    elif tamper == 'query':
        source['commands'] = [dict(command='to_json', args=[], kwargs={}, reason='Read the current state.',
                                   before=source['initial_state'], after=source['initial_state'])]
        source['final_state'] = source['initial_state']
    else:
        source['final_state'] = source['initial_state']
    path = tmp_path / 'invalid.json.gz'
    path.write_bytes(gzip.compress(json.dumps(source).encode()))
    output = tmp_path / 'verified'
    with pytest.raises(ValueError):
        verify(path, output, backend='mock')
    assert not output.exists(), 'Rejected journals must not produce verification evidence'


@pytest.mark.parametrize('missing', ('f5', 'f9'))
def test_input_reload_cannot_count_an_unhandled_save_or_load_key(tmp_path, missing):
    """Equal live state alone is insufficient: both persistence and actual input continuation must work."""
    from eador.app import create_game
    from eador.scene import ShardScene
    from tools.eador_ui import PlayerInput

    class IncompleteShortcuts(ShardScene):
        controls = {**ShardScene.controls, missing: 'unavailable'}

        def unavailable(self):
            self.message = 'This shortcut is unavailable.'

    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        game.push(IncompleteShortcuts(State.new(7)))
        player = PlayerInput(game)
        with pytest.raises(AssertionError, match='quicksave|reload'):
            player.reload(player.state.to_json())
        assert player.reloads == 0
    finally:
        try:
            game._teardown()
        finally:
            game.backend.quit()
