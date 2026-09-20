"""K1/K24/K28 -- the optional City Views panel (views.py) and its wiring."""

import copy
import re

import save
import sim
import views


def _campaign_after_season():
    c = save.Campaign()
    c.state.advance_season(c.tree.effects())
    return c


def test_dashboard_covers_every_stat_group_and_is_all_text():
    c = _campaign_after_season()
    sections = views.dashboard(c.state, c.tree.effects(), (1, 45))
    titles = [s["title"] for s in sections]
    for expected in ("Settlement", "Stores", "Land", "Sustainability", "Workforce", "Buildings", "Last season", "Research"):
        assert expected in titles
    for s in sections:
        for label, value in s["rows"]:
            assert isinstance(label, str) and isinstance(value, str)


def test_dashboard_before_any_season_and_with_garbage_values_does_not_raise():
    c = save.Campaign()
    views.dashboard(c.state, c.tree.effects())
    c.state.resources["food"] = float("nan")
    c.state.land_health = float("inf")
    rows = dict(next(s for s in views.dashboard(c.state, c.tree.effects()) if s["title"] == "Stores")["rows"])
    assert rows["Food"].startswith("-")


def test_dashboard_lists_era_pressures_only_when_reached():
    c = save.Campaign()
    assert "Era pressures" not in [s["title"] for s in views.dashboard(c.state, c.tree.effects())]
    c.state.era = "industrial"
    titles = [s["title"] for s in views.dashboard(c.state, c.tree.effects())]
    assert "Era pressures" in titles


def test_views_are_pure_readers():
    c = _campaign_after_season()
    before = copy.deepcopy(c.state.__dict__)
    views.dashboard(c.state, c.tree.effects())
    views.civic_map_svg(c.state)
    views.flow_svg(c.state, c.state.last_report)
    assert c.state.__dict__ == before


def test_map_has_one_labelled_district_per_unlocked_building():
    c = save.Campaign()
    svg = views.civic_map_svg(c.state)
    for b in sim.buildings_for_era("tribal"):
        assert sim.BUILDING_LABEL[b] in svg
    assert sim.BUILDING_LABEL["farmland"] not in svg
    c.state.era = "space"
    svg = views.civic_map_svg(c.state)
    assert sim.BUILDING_LABEL["habitat_rings"] in svg


def test_every_building_has_a_distinct_glyph_shape():
    assert set(views.GLYPH_SHAPES) == set(sim.BUILDINGS)
    assert len(set(views.GLYPH_SHAPES.values())) == len(sim.BUILDINGS)


def test_map_caps_glyphs_and_reports_the_true_count():
    c = save.Campaign()
    c.state.buildings["shelter"] = 200
    svg = views.civic_map_svg(c.state)
    assert "200 (showing" in svg
    assert svg.count("<rect") < 60


def test_map_survives_bad_building_counts():
    c = save.Campaign()
    c.state.buildings["shelter"] = "lots"
    c.state.buildings["granary"] = -4
    assert views.civic_map_svg(c.state).startswith("<svg")
    assert "shelters" in views.map_caption(c.state) or "people" in views.map_caption(c.state)


def test_flow_is_empty_before_a_season_and_conserves_flow_after():
    c = save.Campaign()
    assert views.flow_svg(c.state, c.state.last_report) == ""
    c = _campaign_after_season()
    links, labels = views.flow_links(c.state, c.state.last_report)
    assert links
    for res in ("food", "materials"):
        node = f"res:{res}"
        inflow = sum(v for _, t, v in links if t == node)
        outflow = sum(v for s, _, v in links if s == node)
        assert outflow <= inflow + 1e-6
    assert all(v > 0 for _, _, v in links)


def test_flow_uses_the_report_totals():
    c = _campaign_after_season()
    report = c.state.last_report
    links, _ = views.flow_links(c.state, report)
    food_in = sum(v for _, t, v in links if t == "res:food")
    assert abs(food_in - report["food_gathered"]) < 1e-6


def test_flow_labels_every_node_with_text():
    c = _campaign_after_season()
    svg = views.flow_svg(c.state, c.state.last_report)
    assert "Foragers" in svg and "Eaten" in svg
    assert len(re.findall("<text", svg)) >= 4


def test_flow_handles_garbage_report_values():
    c = save.Campaign()
    report = {"food_gathered": "x", "materials_gathered": float("nan"), "tools_made": -3, "knowledge_made": None}
    assert views.flow_svg(c.state, report) == ""
    assert views.flow_svg(c.state, "nope") == ""


def test_flow_with_starving_settlement_never_exceeds_gathered():
    c = save.Campaign()
    c.state.resources["food"] = 0.0
    c.state.population = 30
    c.state.advance_season(c.tree.effects())
    links, _ = views.flow_links(c.state, c.state.last_report)
    out = sum(v for s, _, v in links if s == "res:food")
    assert out <= c.state.last_report["food_gathered"] + 1e-6
    assert "drew down" in views.flow_caption(
        {"food_gathered": 1.0, "food_consumed": 5.0}
    )


def test_panel_toggle_tabs_and_render(game_env):
    e = game_env
    panel = e.elements["views-panel"]
    assert panel.hidden is True
    e.toggle_views()
    assert panel.hidden is False
    assert e.elements["views-toggle-button"].innerText == "Hide City Views"
    assert len(e.elements["views-dashboard"].children) >= 6
    e.elements["views-tab-map-button"].dispatch("click", None)
    assert e.elements["views-dashboard"].hidden is True
    assert e.elements["views-map"].hidden is False
    assert "<svg" in e.elements["views-map-svg"].innerHTML
    e.advance_season()
    e.elements["views-tab-flow-button"].dispatch("click", None)
    assert "<svg" in e.elements["views-flow-svg"].innerHTML
    e.toggle_views()
    assert panel.hidden is True


def test_panel_content_updates_with_state(game_env):
    e = game_env
    e.toggle_views()
    e.elements["views-tab-map-button"].dispatch("click", None)
    before = e.elements["views-map-svg"].innerHTML
    e.state.resources["materials"] = 500
    e.build("shelter")
    assert e.elements["views-map-svg"].innerHTML != before
