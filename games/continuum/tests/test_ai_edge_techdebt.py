"""Edge-case tests for techdebt.py."""

import techdebt


def test_clean_handles_junk_and_clamps():
    """Test clean() with None, strings, out-of-range numbers, and booleans."""
    assert techdebt.clean(None) == techdebt.fresh()
    assert techdebt.clean("junk") == techdebt.fresh()
    assert techdebt.clean({"debt": -5.0})["debt"] == 0.0
    assert techdebt.clean({"debt": 2.0})["debt"] == 1.0
    assert techdebt.clean({"debt": float("inf")})["debt"] == 0.0
    assert techdebt.clean({"debt": True})["debt"] == 0.0


def test_outage_share_caps_at_constant():
    """Test outage_share() respects OUTAGE_CAP at maximum debt."""
    record = techdebt.fresh()
    record["debt"] = 1.0
    assert techdebt.outage_share(record) == techdebt.OUTAGE_CAP
    record["debt"] = 0.5
    assert techdebt.outage_share(record) < techdebt.OUTAGE_CAP


def test_output_multiplier_applies_refactor_and_outage():
    """Test output_multiplier() combines outage loss and refactor penalty."""
    record = techdebt.fresh()
    record["debt"] = 1.0
    record["refactor"] = True
    mult = techdebt.output_multiplier(record)
    expected = (1.0 - techdebt.OUTAGE_CAP) * techdebt.REFACTOR_OUTPUT
    assert abs(mult - expected) < 1e-9


def test_label_returns_correct_bands():
    """Test label() returns the right string for LOW and HIGH thresholds."""
    assert techdebt.label(0.0) == "none"
    assert techdebt.label(0.01) == "low"
    assert techdebt.label(techdebt.LOW) == "building up"
    assert techdebt.label(0.3) == "building up"
    assert techdebt.label(techdebt.HIGH) == "high"
    assert techdebt.label(1.0) == "high"


def test_hazard_level_returns_0_1_2():
    """Test hazard_level() returns 0, 1, or 2 at band boundaries."""
    assert techdebt.hazard_level(0.0) == 0
    assert techdebt.hazard_level(techdebt.LOW - 0.01) == 0
    assert techdebt.hazard_level(techdebt.LOW) == 1
    assert techdebt.hazard_level(techdebt.HIGH - 0.01) == 1
    assert techdebt.hazard_level(techdebt.HIGH) == 2
    assert techdebt.hazard_level(1.0) == 2


def test_quick_build_refuses_when_off():
    """Test quick_build() returns 0.0 and does not modify state when disabled."""
    ui = {}
    techdebt.set_quick(ui, False)
    assert techdebt.quick_build(ui, 100.0) == 0.0
    assert techdebt.get(ui)["quick"] is False


def test_quick_build_clamps_debt_and_counts():
    """Test quick_build() clamps debt at 1.0 and increments the build counter."""
    ui = {}
    techdebt.set_quick(ui, True)
    for _ in range(21):
        techdebt.quick_build(ui, 10.0)
    assert techdebt.get(ui)["debt"] == 1.0
    assert techdebt.get(ui)["quick_builds"] > 0
