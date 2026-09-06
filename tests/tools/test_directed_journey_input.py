"""A directed command journal must reproduce actual game input and saved continuation."""
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from eador.model import State
from tools.audit_eador_army_plans import SavedCommands
from tools.cpu_budget import CpuBudget


ROOT = Path(__file__).resolve().parents[2]


def earned_report():
    """Prepare a few real commands from the authenticated paid Control opening."""
    path = ROOT / 'docs/evidence/shardbound-army-plans-cd351a9/control.json.gz'
    blob = path.read_bytes()
    history = json.loads(gzip.decompress(blob))
    initial = history['commands'][38]['before']
    played = SavedCommands(State.from_json(initial), CpuBudget(100))
    for command, args, kwargs in (
        ('infuse', (), {}),
        ('travel', ((0, -1),), {}),
        ('battle.cast', ('heal', 4), {'caster_id': 5}),
        ('battle.guard', (0,), {}),
        ('battle.end_turn', (), {}),
    ):
        played.order(command, *args, **kwargs)
        played.commands[-1]['reason'] = 'Exercise the recorded public command through real input.'
    return dict(
        source=dict(path=str(path.relative_to(ROOT)), journal_sha256=hashlib.sha256(blob).hexdigest(),
                    journal_source=history['source_commit'], command_index=38,
                    initial_sha256=hashlib.sha256(initial.encode()).hexdigest()),
        execution_source='test working source',
        source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py')]},
        initial_state=initial, final_state=played.state.to_json(), commands=played.commands,
    )


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


@pytest.mark.parametrize('tamper', ('opening', 'source_index', 'model', 'chain', 'autoplay', 'query'))
def test_directed_replay_rejects_unearned_stale_or_automatic_journals(tmp_path, tamper):
    """Self-consistent hashes cannot authenticate a fabricated opening or replace explicit commands."""
    from tools.verify_eador_directed_journey import verify

    source = earned_report()
    if tamper == 'opening':
        source['initial_state'] = source['commands'][0]['after']
        source['source']['initial_sha256'] = hashlib.sha256(source['initial_state'].encode()).hexdigest()
    elif tamper == 'source_index':
        source['source']['command_index'] = 37
    elif tamper == 'model':
        source['source_sha256']['eador/model.py'] = '0' * 64
    elif tamper == 'chain':
        source['commands'][1]['before'] = source['initial_state']
    elif tamper == 'autoplay':
        source['commands'][0]['command'] = 'battle.auto_turn'
    else:
        source['commands'] = [dict(command='to_json', args=[], kwargs={}, reason='Read the current state.',
                                   before=source['initial_state'], after=source['initial_state'])]
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
