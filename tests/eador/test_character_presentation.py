"""Character identity stays attached to the selected class and saved roster."""
import pytest

from eador.model import HERO_CLASSES
from tools.verify_eador_characters import verify, verify_class_carryover


@pytest.mark.parametrize('hero_class', HERO_CLASSES)
def test_selected_class_keeps_its_portrait_and_miniature_through_start(tmp_path, hero_class):
    """A real class click carries the same identity through Hero, battle and exact reload."""
    receipt = verify_class_carryover(tmp_path, hero_class)
    assert receipt['hero_class'] == hero_class
    assert receipt['exact_reloads'] == 1


def test_character_journey_keeps_earned_rosters_and_equipment_readable(tmp_path):
    """The native route also runs headlessly, including real orders and fixed earned saves."""
    receipt = verify(tmp_path, backend='mock')
    assert set(receipt['title_classes']) == set(HERO_CLASSES)
    assert receipt['reading_sizes'] == [100, 125]
    assert receipt['exact_reloads'] == 2
    assert set(receipt['specialist_kinds']) >= {'warden', 'sapper', 'healer', 'guard', 'archer'}
    assert receipt['equipment_seen'] == receipt['equipment_inventory']
    assert len(receipt['equipment_seen']) == 8
    assert receipt['source_unchanged']
