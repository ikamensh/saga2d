"""Recorded-save comparisons distinguish visited worlds from future generation."""
from copy import deepcopy
from dataclasses import asdict
import json

from eador.worldgen import generate


def expected_rootward_arrival(recorded):
    """Keep every recorded rule/result field, using current content for a new shard.

    This is deliberately limited to the unentered Rootward arrival fixtures.
    Loading a current world, resting or recovering a saved entry world must
    compare its original province arrays exactly, without this substitution.
    """
    assert recorded['theme'] == 'elderwild'
    assert recorded['campaign']['stage'] == 2
    assert recorded['campaign']['contract'] == 'rootward'
    expected = deepcopy(recorded)
    provinces = json.loads(json.dumps([asdict(p) for p in generate(recorded['seed'], recorded['theme']).values()]))
    expected['provinces'] = provinces
    expected['campaign']['entry']['provinces'] = deepcopy(provinces)
    return expected


def expected_fresh_replay(recorded):
    """Replay starts a newly generated shard but retains its recorded difficulty parameters."""
    assert recorded['turn'] == 1 and recorded['theme'] == 'frontier'
    expected = deepcopy(recorded)
    provinces = json.loads(json.dumps([asdict(p) for p in generate(recorded['seed'], recorded['theme']).values()]))
    expected['provinces'] = provinces
    if expected['campaign'] is not None:
        assert expected['campaign']['stage'] == 1 and expected['campaign']['phase'] == 'playing'
        expected['campaign']['entry']['provinces'] = deepcopy(provinces)
    return expected
