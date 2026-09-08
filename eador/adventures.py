"""Quote an authored approach from the province's recorded reward, without spending it."""
from dataclasses import dataclass

from eador.content import AdventureAttempt, SITES
from eador.entities import Province, RuleError


@dataclass(frozen=True)
class AdventureQuote:
    """The saved attempt and its entry fees; reward totals belong to the attempt."""
    attempt: AdventureAttempt | None
    gold: int
    crystals: int


def quote_adventure(province: Province, *, gold: int, crystals: int,
                    approach: str | None = None) -> AdventureQuote:
    """Choose an affordable offered approach; the caller owns exploration readiness."""
    options = SITES[province.site_kind].approaches if province.site_kind else ()
    selected = None
    if options:
        selected_id = options[0].id if approach is None else approach
        selected = next((option for option in options if option.id == selected_id), None)
    if approach is not None and selected is None:
        raise RuleError('Choose one of the offered adventure approaches.')
    if selected is None:
        return AdventureQuote(None, 0, 0)
    if gold < selected.gold_cost or crystals < selected.crystals_cost:
        raise RuleError('Not enough gold or crystals for that approach.')
    attempt = AdventureAttempt(selected.id, selected.encounter,
                               province.site_gold + selected.bonus_gold,
                               province.site_crystals, province.site_relic, selected.cargo_penalty)
    return AdventureQuote(attempt, selected.gold_cost, selected.crystals_cost)
