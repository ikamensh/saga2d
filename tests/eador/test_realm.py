"""Separate realms share purchase rules while solo State retains its saved interface."""
from copy import deepcopy
from dataclasses import asdict, fields

import pytest

from eador.model import RuleError, State


def test_two_realms_purchase_independently_using_the_same_rules_as_solo():
    """A real starter army buys a Swordsman without spending another realm's funds or IDs."""
    from eador.realm import Realm

    solo = State.new(7)
    first = Realm(hero=deepcopy(solo.hero), log=list(solo.log))
    second = Realm(hero=State.new(8, 'Wizard').hero)
    untouched = asdict(second)
    province = solo.provinces[solo.hero.pos]
    first.build('barracks')
    first.purchase_recruit('swordsman', province=province, owner='player')
    solo.build('barracks')
    solo.recruit('swordsman')
    assert asdict(first) == {field.name: asdict(solo)[field.name] for field in fields(Realm)}
    assert asdict(second) == untouched
    assert first.gold == 10 and first.next_troop_id == 5
    assert 'barracks' not in second.buildings and second.next_troop_id == 4
    saved = solo.to_json()
    assert State.from_json(saved).to_json() == saved
    before = asdict(first)
    with pytest.raises(RuleError, match='Recruit in one of your provinces'):
        first.purchase_recruit('militia', province=province, owner='other')
    assert asdict(first) == before
