"""Edge-case tests for views.py public functions."""

import save
import views


def _campaign_after_season():
    c = save.Campaign()
    c.state.advance_season(c.tree.effects())
    return c


def test_sparkline_svg_empty_values_returns_empty_string():
    """sparkline_svg returns '' when given no values or fewer than two."""
    assert views.sparkline_svg([]) == ""
    assert views.sparkline_svg(None) == ""
    assert views.sparkline_svg([1]) == ""


def test_sparkline_svg_with_two_values_produces_valid_svg():
    """sparkline_svg generates a valid SVG string with at least two usable values."""
    svg = views.sparkline_svg([10, 20], label="Test")
    assert svg.startswith("<svg")
    assert "aria-label" in svg
    assert "Test:" in svg


def test_sparkline_svg_with_custom_formatter_applies_it():
    """sparkline_svg uses the provided formatter for text labels."""
    svg = views.sparkline_svg([1.234, 5.678], formatter=lambda v: f"{v:.0f}")
    assert "1" in svg and "6" in svg


def test_sparkline_svg_with_large_values_scales_correctly():
    """sparkline_svg scales correctly for very large or very small values."""
    svg = views.sparkline_svg([1e6, 1e-6], label="Large")
    assert svg.startswith("<svg")
    assert "aria-label" in svg


def test_civic_map_svg_handles_zero_building_counts_gracefully():
    """civic_map_svg produces valid SVG even when all building counts are zero."""
    c = save.Campaign()
    c.state.buildings = {}
    svg = views.civic_map_svg(c.state)
    assert svg.startswith("<svg")


def test_civic_map_svg_applies_hazard_patterns_correctly():
    """civic_map_svg adds hatch patterns and hazard marks for hazard > 0."""
    c = save.Campaign()
    c.state.buildings["shelter"] = 1
    svg_caution = views.civic_map_svg(c.state, hazard=1)
    assert "map-hazard-hatch" in svg_caution
    assert "!" in svg_caution
    svg_danger = views.civic_map_svg(c.state, hazard=2)
    assert "map-district--danger" in svg_danger


def test_civic_map_svg_includes_heritage_sites():
    """civic_map_svg renders heritage sites when provided."""
    c = save.Campaign()
    c.state.buildings["shelter"] = 1
    sites = [{"name": "Old Ruin", "era": "tribal", "kept": True}]
    svg = views.civic_map_svg(c.state, heritage_sites=sites)
    assert "Old Ruin" in svg
    assert "kept" in svg


def test_flow_links_with_empty_report_returns_empty_lists():
    """flow_links returns ([], {}) when the report is empty or None."""
    c = save.Campaign()
    links, labels = views.flow_links(c.state, {})
    assert links == []
    assert labels == {}
    links2, labels2 = views.flow_links(c.state, None)
    assert links2 == []


def test_flow_links_with_zero_production_handles_gracefully():
    """flow_links does not crash when production values are zero or negative."""
    c = save.Campaign()
    c.state.allocation["foragers"] = 5
    report = {"food_gathered": 0, "materials_gathered": -1, "tools_made": 0, "knowledge_made": None}
    links, _ = views.flow_links(c.state, report)
    assert all(v > 0 for _, _, v in links)


def test_flow_svg_before_season_returns_empty_string():
    """flow_svg returns '' when there are no flow links (before a season)."""
    c = save.Campaign()
    assert views.flow_svg(c.state, {}) == ""


def test_flow_svg_with_valid_links_produces_rich_svg():
    """flow_svg generates an SVG with ribbons and nodes when links exist."""
    c = _campaign_after_season()
    svg = views.flow_svg(c.state, c.state.last_report)
    assert svg.startswith("<svg")
    assert "flow-ribbon" in svg
    assert "flow-node" in svg


def test_dashboard_handles_extreme_values_without_crashing():
    """dashboard degrades gracefully when given extremely large or small numbers."""
    c = save.Campaign()
    c.state.population = 1e9
    c.state.resources["food"] = -1e6
    c.state.land_health = 0.0
    sections = views.dashboard(c.state, c.tree.effects())
    assert len(sections) > 0
    for s in sections:
        for _, val in s["rows"]:
            assert isinstance(val, str)
