"""Edge-case tests for sustainability.py.

Tests limits, clamping, and zero/empty inputs for public functions in
sustainability.py without relying on the full simulation loop.
"""

import save
import sustainability


def test_food_security_clamps_negative_and_over_100():
    """food_security should clamp fed_fraction to 0..1 even if state is corrupted."""
    campaign = save.Campaign()
    campaign.state.fed_fraction = -0.5
    assert sustainability.food_security(campaign.state) == 0.0

    campaign.state.fed_fraction = 1.5
    assert sustainability.food_security(campaign.state) == 1.0


def test_shelter_adequacy_handles_zero_population():
    """When population is zero, _ratio returns 1.0 so shelter_adequacy doesn't crash."""
    campaign = save.Campaign()
    campaign.state.population = 0
    campaign.state.housing_capacity = lambda effects=None: 10
    assert sustainability.shelter_adequacy(campaign.state) == 1.0


def test_equity_penalises_lopsided_provisions():
    """Equity should drop when one provision is met and others are not."""
    campaign = save.Campaign()
    campaign.state.population = 10
    campaign.state.fed_fraction = 1.0
    campaign.state.housing_capacity = lambda effects=None: 5  # only half housed
    campaign.state.culture_capacity = lambda effects=None: 0
    campaign.state.resources = {}
    campaign.state.sprawl = 0.0
    campaign.state.era = "tribal"

    eq = sustainability.equity(campaign.state)
    assert eq < 1.0  # Should be penalised for spread


def test_balance_handles_zero_extraction():
    """balance() must not divide by zero when extraction is zero or negative."""
    campaign = save.Campaign()
    campaign.state.last_extraction = 0
    campaign.state.last_sustainable_yield = 100
    campaign.state.land_health = 1.0
    campaign.state.pollution = 0.5
    campaign.state.era = "industrial"

    bal = sustainability.balance(campaign.state)
    assert 0.0 <= bal <= 1.0


def test_score_label_respects_hard_mode_thresholds():
    """score_label should use higher thresholds when hard_mode=True."""
    # Normal mode thresholds: [30, 50, 70, 85]
    assert sustainability.score_label(29) == "Collapsing"
    assert sustainability.score_label(30) == "Failing"
    assert sustainability.score_label(49) == "Failing"
    assert sustainability.score_label(50) == "Strained"

    # Hard mode thresholds: [38, 58, 78, 92]
    assert sustainability.score_label(37, hard_mode=True) == "Collapsing"
    assert sustainability.score_label(38, hard_mode=True) == "Failing"
    assert sustainability.score_label(57, hard_mode=True) == "Failing"
    assert sustainability.score_label(58, hard_mode=True) == "Strained"


def test_evaluate_returns_score_and_components_within_bounds():
    """evaluate() should return a score and components all clamped to 0..100."""
    campaign = save.Campaign()
    campaign.state.population = 5
    campaign.state.fed_fraction = 0.8
    campaign.state.housing_capacity = lambda effects=None: 5
    campaign.state.culture_capacity = lambda effects=None: 5
    campaign.state.resources = {"food": 10, "tools": 5}
    campaign.state.role_diversity = lambda: 0.5
    campaign.state.public_works_coverage = lambda effects=None: 0
    campaign.state.pollution = 0.0
    campaign.state.sprawl = 0.0
    campaign.state.allocation = {}
    campaign.state.era = "tribal"
    campaign.state.last_extraction = 10
    campaign.state.last_sustainable_yield = 20
    campaign.state.land_health = 0.8

    result = sustainability.evaluate(campaign.state)
    assert 0.0 <= result["score"] <= 100.0
    for comp in sustainability.COMPONENTS:
        assert 0.0 <= result["components"][comp] <= 100.0
