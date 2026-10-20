"""Tests for sustainability.score_note().

Checks that score_note() returns the correct narrative string based on the
weakest component, and the positive fallback when all components are healthy.
"""

import save
import sustainability


def _make_state():
    campaign = save.Campaign()
    campaign.state.era = "tribal"
    campaign.state.sprawl = 0.0
    campaign.state.pollution = 0.0
    return campaign.state


def test_score_note_returns_equity_when_provision_is_uneven():
    state = _make_state()
    # High food, low shelter/culture -> large spread drags equity down below livability
    state.fed_fraction = 1.0
    state.population = 10
    state.housing_capacity = lambda effects=None: 1
    state.culture_capacity = lambda effects=None: 1
    # Keep balance and resilience high
    state.land_health = 1.0
    state.last_extraction = 10
    state.last_sustainable_yield = 20
    state.resources = {"food": 100, "tools": 100}
    state.role_diversity = lambda: 1.0
    state.public_works_coverage = lambda effects=None: 10

    note = sustainability.score_note(state)
    assert "some and poorly for others" in note


def test_score_note_returns_balance_when_land_health_is_low():
    state = _make_state()
    # Low land health and over-extraction drags balance down
    state.land_health = 0.1
    state.last_extraction = 200
    state.last_sustainable_yield = 50
    # Keep provisions high so livability/equity stay healthy
    state.fed_fraction = 1.0
    state.population = 10
    state.housing_capacity = lambda effects=None: 20
    state.culture_capacity = lambda effects=None: 20
    # Keep resilience high
    state.resources = {"food": 100, "tools": 100}
    state.role_diversity = lambda: 1.0
    state.public_works_coverage = lambda effects=None: 10

    note = sustainability.score_note(state)
    assert "taking more from the land" in note


def test_score_note_returns_positive_when_all_components_are_high():
    state = _make_state()
    # Set everything high so the weakest component is >= 0.85
    state.fed_fraction = 1.0
    state.population = 10
    state.housing_capacity = lambda effects=None: 20
    state.culture_capacity = lambda effects=None: 20
    state.land_health = 1.0
    state.last_extraction = 10
    state.last_sustainable_yield = 50
    state.resources = {"food": 100, "tools": 100}
    state.role_diversity = lambda: 1.0
    state.public_works_coverage = lambda effects=None: 20

    note = sustainability.score_note(state)
    assert "Nothing here is going badly" in note
