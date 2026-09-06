"""Versioned realm policies. Existing IDs retain their meaning in saved campaigns."""
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class DifficultySpec:
    id: str
    title: str
    description: str
    starting_gold: int
    starting_crystals: int
    gold_percent: int
    army_recovery: int
    mana_recovery: int
    opening_delay: int
    arrival_delay: int
    replacement_delay: int
    recovery_gold: int
    recovery_crystals: int


# Tune by adding a new ID and updating the new-game catalog, never by rewriting
# a published record. Only these realm parameters are frozen, not all game rules.
RULESETS = MappingProxyType({
    'standard-1': DifficultySpec('standard-1', 'Standard',
        'The original realm rules: 100 gold, normal recovery and finite rival pressure.',
        100, 4, 100, 6, 4, 3, 2, 4, 60, 2),
    'accessible-1': DifficultySpec('accessible-1', 'Accessible',
        'More starting funds, faster recovery and longer rival preparation windows.',
        130, 6, 100, 8, 6, 4, 3, 5, 90, 4),
    'challenge-1': DifficultySpec('challenge-1', 'Challenge',
        '90 starting gold, 80% realm gold income, slower mana recovery and shorter rival preparation.',
        90, 2, 80, 6, 3, 2, 2, 3, 60, 2),
    # Mana recovery revised after matched route/purchase and saved-policy checks.
    'challenge-2': DifficultySpec('challenge-2', 'Challenge',
        '90 starting gold, 80% realm gold income, normal mana recovery and shorter rival preparation.',
        90, 2, 80, 6, 4, 2, 2, 3, 60, 2),
})
DIFFICULTIES = MappingProxyType({
    'accessible': RULESETS['accessible-1'],
    'standard': RULESETS['standard-1'],
    'challenge': RULESETS['challenge-2'],
})


@dataclass(frozen=True)
class RecoveryPreview:
    """Actual hero gains and HP per surviving troop, before the rival operates."""
    hero_hp: int
    army_hp: int
    mana: int
    blocked_reason: str | None = None
