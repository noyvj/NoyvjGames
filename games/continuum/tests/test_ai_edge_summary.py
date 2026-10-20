"""Edge-case tests for summary.py (K5).

Tests limits, empty/zero inputs, rejected values, and fallback behavior
for public functions in the civilization summary report engine."""

import save
import summary


def test_total_seasons_zero_and_parked_zero():
    campaign = save.Campaign()
    campaign.state.season = 0
    assert summary.total_seasons(campaign) == 0

    # Mid-revisit: _live_progress_city returns parked_state
    campaign.revisiting = "tribal"
    campaign.parked_state = {"city": {"season": 0}}
    assert summary.total_seasons(campaign) == 0


def test_peak_population_empty_rows_and_non_numeric():
    campaign = save.Campaign()
    # Empty rows list returns 0
    assert summary.peak_population(campaign, []) == 0

    # Rows with non-numeric populations are ignored
    rows = [
        {"population": None},
        {"population": "unknown"},
        {"population": ""},
    ]
    assert summary.peak_population(campaign, rows) == 0


def test_peak_score_empty_and_mixed_history():
    campaign = save.Campaign()
    campaign.state.peak_score = None
    assert summary.peak_score(campaign) is None

    # Exercise parked city history reading (requires revisiting to activate _live_progress_city)
    campaign.revisiting = "tribal"
    campaign.parked_state = {"city": {"score_history": [40.0, "invalid", None, -5]}}
    assert summary.peak_score(campaign) == 40.0


def test_efficiency_rank_rejected_and_edge_values():
    # NaN should be rejected per `peak != peak` check
    assert summary.efficiency_rank(float("nan")) is None

    # Zero and negative scores fall back to Bronze (no Thriving/Steady bands)
    assert summary.efficiency_rank(0) == "Bronze"
    assert summary.efficiency_rank(-100) == "Bronze"

    # Very large scores are still rated Thriving and get Gold
    assert summary.efficiency_rank(9999) == "Gold"


def test_stakeholder_statement_edge_data():
    data = {
        "peak_score": None,
        "total_seasons": 0,
        "peak_population": 0,
        "furthest_era_label": "",
    }
    text = summary.stakeholder_statement(data, rank=None, name="")

    assert "not yet rated" in text
    assert "over 0 seasons" in text
    assert "a peak of 0 people" in text
    assert "the settlement" in text
    assert "The council's efficiency rank stands at" not in text
