"""Seeded discoveries vary choices without changing earned worlds or realm rules."""

from tools.audit_eador_discoveries import audit_worlds


def test_new_discoveries_preserve_300_saved_worlds_and_vary_reachable_locations():
    """Public new/save/load worlds preserve exact realm data, site packages and fair access."""
    report = audit_worlds()
    assert report['world_count'] == 300
    assert report['exact_reloads'] == {'baseline': 300, 'current': 300}
    assert set(report['themes']) == {'frontier', 'elderwild', 'ruins'}
    assert all(theme['worlds_with_moved_sites'] > 0 for theme in report['themes'].values())
