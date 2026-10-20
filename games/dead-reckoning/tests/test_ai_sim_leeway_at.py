import pytest
from sim import leeway_at
from tests.golden_charts import GOLDEN_B


def test_leeway_returns_zero_when_chart_has_no_wind():
    chart = {}
    assert leeway_at(chart, 45, "charted") == (0.0, 0.0)


def test_leeway_returns_zero_for_nominal_model():
    chart = {"wind": {"from": 270, "range": [10, 15], "true": 12.5}}
    assert leeway_at(chart, 45, "nominal") == (0.0, 0.0)


def test_leeway_pushes_to_port_on_starboard_beam_wind():
    chart = {"wind": {"from": 270, "range": [10, 15], "true": 12.5}}
    # Wind from West (270) blows East. Ship heading North (0). Starboard is East.
    # Leeway pushes the ship to leeward (starboard here), so x component must be positive.
    result = leeway_at(chart, 0, "charted")
    assert isinstance(result, tuple) and len(result) == 2
    assert result[0] > 0, f"Expected starboardward (positive x) leeway, got {result}"


def test_leeway_is_zero_when_wind_is_directly_astern():
    chart = {"wind": {"from": 180, "range": [10, 15], "true": 12.5}}
    # Wind from South (180) blows North. Ship heading North (0). No cross component.
    result = leeway_at(chart, 0, "charted")
    assert result == pytest.approx((0.0, 0.0)), f"Expected zero leeway for astern wind, got {result}"


def test_leeway_with_real_chart_data():
    # Uses GOLDEN_B which has a known wind configuration from the game's data.
    if "wind" not in GOLDEN_B:
        pytest.skip("GOLDEN_B does not have wind configured")
    result = leeway_at(GOLDEN_B, 0, "charted")
    assert isinstance(result, tuple) and len(result) == 2
    assert result != (0.0, 0.0), f"Expected non-zero leeway for GOLDEN_B at heading 0, got {result}"
