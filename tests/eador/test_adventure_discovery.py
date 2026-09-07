"""Players locate saved adventures before paying to conquer their provinces."""

from pathlib import Path

import pytest
from saga2d import Label

from eador.app import create_game
from eador.content import RELICS, SITES
from eador.model import State
from eador.scene import ShardScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout
from tools.verify_eador_reading import check_page


@pytest.mark.parametrize('world', ['new', 'old_locations', 'cleared_sources'])
def test_selected_provinces_and_codex_locate_saved_sources_without_spending(world, tmp_path):
    """125% input browsing locates neutral and cleared sources in new and untouched historical worlds."""
    fixture = {'old_locations': 'v12_ruins_seed7_before_site_variation.json',
               'cleared_sources': 'v12_frontier_caravan_result.json'}
    state = (State.new(7, theme='ruins') if world == 'new' else
             State.from_json((Path(__file__).parent / 'fixtures' / fixture[world]).read_text()))
    before = state.to_json()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        for key in ('f2', 'right', 'return'):
            player.press(key)
        sources = [p for p in state.provinces.values() if p.site]
        assert any(p.owner == 'neutral' for p in sources)
        if world == 'cleared_sources':
            assert any(p.explored and p.site_relic for p in sources)
        for province in sources:
            player.click(*player.root.grid.center(province.pos))
            assert player.root.selected == province.pos
            labels = '\n'.join(item.text for item in game.scene.ui.walk() if isinstance(item, Label))
            assert province.site in labels, (province.name, province.site)
            if province.explored:
                assert 'cleared' in labels.lower()
            check_reading_layout(game.scene)
            assert state.to_json() == before
        selected = player.root.selected
        player.press('c')

        def read_category(key):
            player.press(key)
            entries = {}
            for _ in range(game.scene.pages):
                check_page(game.scene)
                for entry in game.scene.visible_entries:
                    entries[entry.title] = entry.facts + ' ' + entry.description
                player.press('right')
            return entries

        sites = read_category('5')
        relics = read_category('6')
        for province in sources:
            location = province.name + (' (cleared)' if province.explored else '')
            assert location in sites[SITES[province.site_kind].name]
            if province.site_relic:
                assert province.site + ' at ' + location in relics[RELICS[province.site_relic].name]
        player.press('escape')
        assert game.scene is player.root and player.root.selected == selected
        assert state.to_json() == before
        assert not list((tmp_path / 'saves').glob('save_*.json'))
    finally:
        game.close()
