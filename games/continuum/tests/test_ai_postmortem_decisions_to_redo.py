"""Tests for postmortem.decisions_to_redo()."""

import minutes
import postmortem
import save


def _make_campaign_with_minutes(num_entries, pivot_season):
    """Create a Campaign and record `num_entries` minutes before or at `pivot_season`."""
    c = save.Campaign()
    for i in range(num_entries):
        season = max(1, pivot_season - (num_entries - 1 - i))
        minutes.record(c.ui, "build", f"Decision {i + 1}", c.state.era, season)
    return c


def test_exactly_three_decisions_before_pivot_are_returned_newest_first():
    c = _make_campaign_with_minutes(3, pivot_season=5)
    result = postmortem.decisions_to_redo(c.ui, 5, "fed_pct")
    assert len(result) == 3
    assert result[0]["decision"] == "Motion carried: the council resolves to build Decision 3."
    assert result[2]["decision"] == "Motion carried: the council resolves to build Decision 1."


def test_only_the_last_three_decisions_are_returned_when_more_exist():
    c = _make_campaign_with_minutes(5, pivot_season=6)
    result = postmortem.decisions_to_redo(c.ui, 6, "shelter_pct")
    assert len(result) == 3
    assert result[0]["decision"] == "Motion carried: the council resolves to build Decision 5."
    assert result[1]["decision"] == "Motion carried: the council resolves to build Decision 4."
    assert result[2]["decision"] == "Motion carried: the council resolves to build Decision 3."


def test_orders_are_filtered_out_and_empty_list_when_none_remain():
    c = save.Campaign()
    for i in range(3):
        minutes.record(c.ui, "order", f"Order {i + 1}", c.state.era, 1 + i)
    result = postmortem.decisions_to_redo(c.ui, 4, "social_pct")
    assert result == []


def test_hint_contains_cause_need():
    c = _make_campaign_with_minutes(1, pivot_season=2)
    result = postmortem.decisions_to_redo(c.ui, 2, "fed_pct")
    assert len(result) == 1
    assert "food for everyone" in result[0]["hint"]
