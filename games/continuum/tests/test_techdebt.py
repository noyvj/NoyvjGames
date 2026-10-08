"""K-4: technical debt (Digital Age and later)."""

import copy

import pytest

import sim
import sustainability
import techdebt
import views


def digital(game_env):
    """A settlement set straight into the Digital Age with plenty of materials."""
    module = game_env.module
    module.state.era = "digital"
    module.tree.current_era = "digital"
    module.state.population = 40
    module.state.buildings["shelter"] = 12
    module.state.buildings["hearth"] = 6
    module.state.resources["materials"] = 500.0
    module.state.resources["food"] = 200.0
    module.render()
    return module


# --- the pure module ---------------------------------------------------------
def test_active_only_from_the_digital_age():
    assert not techdebt.active("industrial")
    assert techdebt.active("digital") and techdebt.active("space") and techdebt.active("relay")
    assert not techdebt.active("nonsense")


def test_clean_survives_junk():
    assert techdebt.clean(None) == techdebt.fresh()
    assert techdebt.clean("x") == techdebt.fresh()
    rec = techdebt.clean({"debt": 5, "quick": "yes", "refactor": 1, "refactors": -3, "quick_builds": True})
    assert rec["debt"] == 1.0 and rec["quick"] is False and rec["refactor"] is False
    assert rec["refactors"] == 0 and rec["quick_builds"] == 0
    assert techdebt.clean({"debt": float("nan")})["debt"] == 0.0
    assert techdebt.clean({"debt": -2})["debt"] == 0.0
    assert techdebt.clean({"debt": [1]})["debt"] == 0.0


def test_get_reads_from_the_ui_dict_and_tolerates_a_bad_ui():
    assert techdebt.get({})["debt"] == 0.0
    assert techdebt.get(None) == techdebt.fresh()
    assert techdebt.get({techdebt.KEY: {"debt": 0.3}})["debt"] == 0.3


def test_no_debt_leaves_effects_untouched():
    effects = dict(sim.NEUTRAL_EFFECTS)
    assert techdebt.apply_effects(effects, {}, "digital") is effects
    assert techdebt.apply_effects(effects, {techdebt.KEY: {"debt": 0.0}}, "digital") is effects


def test_debt_scales_output_but_never_food_or_land():
    ui = {techdebt.KEY: {"debt": 0.5}}
    out = techdebt.apply_effects(dict(sim.NEUTRAL_EFFECTS), ui, "digital")
    expected = 1.0 - techdebt.OUTAGE_PER_DEBT * 0.5
    for key in techdebt.OUTPUT_KEYS:
        assert out[key] == pytest.approx(expected)
    assert out["food_yield_mult"] == 1.0 and out["regen_mult"] == 1.0
    assert techdebt.apply_effects(dict(sim.NEUTRAL_EFFECTS), ui, "industrial")["materials_yield_mult"] == 1.0


def test_outage_share_is_capped():
    assert techdebt.outage_share({"debt": 1.0}) == techdebt.OUTAGE_CAP
    assert techdebt.outage_share({"debt": 0.0}) == 0.0


def test_a_scheduled_refactor_cuts_output_and_one_season_pays_the_debt_down():
    ui = {}
    techdebt.put(ui, {"debt": 0.6})
    techdebt.schedule_refactor(ui, True)
    out = techdebt.apply_effects(dict(sim.NEUTRAL_EFFECTS), ui, "digital")
    assert out["tool_yield_mult"] == pytest.approx((1 - techdebt.outage_share({"debt": 0.6})) * techdebt.REFACTOR_OUTPUT)
    state = sim.CityState(era="digital")
    result = techdebt.after_season(ui, state)
    assert result["refactored"] and result["eased"] == pytest.approx(techdebt.REFACTOR_PAYDOWN)
    rec = techdebt.get(ui)
    assert rec["debt"] == pytest.approx(0.3) and rec["refactor"] is False and rec["refactors"] == 1


def test_debt_never_goes_below_zero_and_slow_builds_add_none():
    ui = {}
    techdebt.put(ui, {"debt": 0.1, "refactor": True})
    techdebt.after_season(ui, sim.CityState(era="digital"))
    assert techdebt.get(ui)["debt"] == 0.0
    assert techdebt.quick_build(ui, 50.0) == 0.0  # quick builds off: no refund, no debt
    assert techdebt.get(ui)["debt"] == 0.0


def test_a_quick_build_refunds_a_quarter_and_adds_debt():
    ui = {}
    techdebt.set_quick(ui, True)
    assert techdebt.quick_build(ui, 40.0) == pytest.approx(40.0 * techdebt.QUICK_DISCOUNT)
    rec = techdebt.get(ui)
    assert rec["debt"] == pytest.approx(techdebt.DEBT_PER_QUICK_BUILD) and rec["quick_builds"] == 1


def test_debt_caps_at_one():
    ui = {}
    techdebt.put(ui, {"debt": 0.98, "quick": True})
    techdebt.quick_build(ui, 10.0)
    assert techdebt.get(ui)["debt"] == 1.0


def test_upkeep_is_paid_from_materials_and_never_below_zero():
    state = sim.CityState(era="digital")
    state.resources["materials"] = 1.0
    state.buildings["shelter"] = 40
    ui = {techdebt.KEY: {"debt": 1.0}}
    result = techdebt.after_season(ui, state)
    assert state.resources["materials"] == 0.0 and result["upkeep"] == pytest.approx(1.0)


def test_upkeep_scales_with_debt_and_buildings():
    state = sim.CityState(era="digital")
    rec = {"debt": 0.4, "quick": False, "refactor": False, "refactors": 0, "quick_builds": 0, "warned": False}
    total = techdebt.total_buildings(state)
    assert techdebt.upkeep(state, rec) == pytest.approx(0.4 * total * techdebt.UPKEEP_PER_BUILDING, abs=0.01)
    assert techdebt.upkeep(state, dict(rec, debt=0.0)) == 0.0


def test_warning_fires_once_when_debt_first_reaches_half_and_rearms_below_the_low_band():
    ui = {}
    state = sim.CityState(era="digital")
    techdebt.put(ui, {"debt": 0.55})
    assert techdebt.after_season(ui, state)["warn"] is True
    assert techdebt.after_season(ui, state)["warn"] is False
    techdebt.put(ui, {"debt": 0.05, "warned": True})
    techdebt.after_season(ui, state)
    assert techdebt.get(ui)["warned"] is False


def test_labels_and_hazard_levels():
    assert techdebt.label(0) == "none" and techdebt.label(0.1) == "low"
    assert techdebt.label(0.3) == "building up" and techdebt.label(0.7) == "high"
    assert [techdebt.hazard_level(d) for d in (0, 0.19, 0.2, 0.5, 1)] == [0, 0, 1, 2, 2]


def test_has_any():
    assert not techdebt.has_any({})
    assert techdebt.has_any({techdebt.KEY: {"debt": 0.1}})
    assert techdebt.has_any({techdebt.KEY: {"refactors": 2}})


# --- the dashboard and the civic map ---------------------------------------------
def test_dashboard_gets_debt_rows_only_when_a_record_is_passed_in_the_digital_age():
    state = sim.CityState(era="digital")
    rows = lambda debt: dict(  # noqa: E731
        r for sec in views.dashboard(state, sim.NEUTRAL_EFFECTS, None, debt) if sec["title"] == "Era pressures" for r in sec["rows"]
    )
    assert "Technical debt" not in rows(None)
    with_debt = rows(techdebt.fresh() | {"debt": 0.25})
    assert with_debt["Technical debt"] == "25% (building up)"
    assert "Output lost to outages" in with_debt and "Debt upkeep" in with_debt and "Refactor season" in with_debt
    older = sim.CityState(era="industrial")
    sections = views.dashboard(older, sim.NEUTRAL_EFFECTS, None, techdebt.fresh())
    assert all("Technical debt" not in dict(sec["rows"]) for sec in sections)


def test_civic_map_tint_has_pattern_mark_and_words_not_just_colour():
    state = sim.CityState(era="digital")
    plain = views.civic_map_svg(state)
    assert "map-hazard-hatch" not in plain and "map-hazard-mark" not in plain
    caution = views.civic_map_svg(state, 1)
    assert "map-district--caution" in caution and "map-hazard-hatch" in caution and ">!<" in caution
    danger = views.civic_map_svg(state, 2)
    assert "map-district--danger" in danger
    assert "technical-debt danger warning" in views.map_caption(state, 2)
    assert "technical-debt" not in views.map_caption(state, 0)


def test_empty_districts_are_not_tinted():
    state = sim.CityState(era="digital")
    state.buildings["transit_hubs"] = 0
    svg = views.civic_map_svg(state, 2)
    assert svg.count("map-hazard-mark") == svg.count("map-district--danger")


# --- the game ------------------------------------------------------------------------
def test_section_is_hidden_before_the_digital_age_with_its_buttons(game_env):
    el = game_env.elements
    assert el["techdebt"].hidden is True
    assert "Digital Age" in el["techdebt-status-display"].innerText
    assert el["quick-build-toggle-button"].hidden is True


def test_section_appears_in_the_digital_age(game_env):
    digital(game_env)
    el = game_env.elements
    assert el["techdebt"].hidden is False
    assert el["quick-build-toggle-button"].hidden is False
    assert "Technical debt: 0% (none)" in el["techdebt-status-display"].innerText
    assert el["refactor-button"].disabled is True  # nothing to refactor yet


def test_quick_builds_cost_less_and_add_debt(game_env):
    module = digital(game_env)
    el = game_env.elements
    cost = sim.BUILDING_COST["shelter"]
    before = module.state.resources["materials"]
    game_env.build("shelter")
    assert module.state.resources["materials"] == pytest.approx(before - cost)
    assert techdebt.get(module.campaign.ui)["debt"] == 0.0  # slow build: full price, no debt
    el["quick-build-toggle-button"].dispatch("click", None)
    assert "ON" in el["quick-build-toggle-button"].innerText
    assert el["quick-build-toggle-button"].attributes.get("aria-pressed") == "true"
    before = module.state.resources["materials"]
    game_env.build("shelter")
    assert module.state.resources["materials"] == pytest.approx(before - cost * (1 - techdebt.QUICK_DISCOUNT))
    assert techdebt.get(module.campaign.ui)["debt"] == pytest.approx(techdebt.DEBT_PER_QUICK_BUILD)
    assert el["refactor-button"].disabled is False


def test_a_failed_build_books_no_debt(game_env):
    module = digital(game_env)
    module.state.resources["materials"] = 0.0
    game_env.elements["quick-build-toggle-button"].dispatch("click", None)
    game_env.build("shelter")
    assert techdebt.get(module.campaign.ui)["debt"] == 0.0 and module.state.resources["materials"] == 0.0


def test_quick_build_toggle_does_nothing_before_the_digital_age(game_env):
    game_env.elements["quick-build-toggle-button"].dispatch("click", None)
    assert techdebt.get(game_env.module.campaign.ui)["quick"] is False


def test_debt_costs_upkeep_and_output_each_season(game_env):
    module = digital(game_env)
    module.state.allocation["gatherers"] = 6
    module.state.allocation["crafters"] = 0
    base = copy.deepcopy(module.state)
    baseline = base.advance_season(module.current_effects())
    techdebt.put(module.campaign.ui, {"debt": 0.6})
    expected_loss = techdebt.outage_share(techdebt.get(module.campaign.ui))
    game_env.advance_season()
    report = module.state.last_report
    assert report["materials_gathered"] == pytest.approx(baseline["materials_gathered"] * (1 - expected_loss))
    owed = techdebt.upkeep(base, techdebt.get(module.campaign.ui))
    assert owed > 0
    assert module.state.resources["materials"] == pytest.approx(
        base.resources["materials"] - (baseline["materials_gathered"] * expected_loss) - owed, abs=0.01
    )


def test_refactor_button_schedules_runs_and_clears(game_env):
    module = digital(game_env)
    el = game_env.elements
    techdebt.put(module.campaign.ui, {"debt": 0.5})
    module.render()
    el["refactor-button"].dispatch("click", None)
    assert techdebt.get(module.campaign.ui)["refactor"] is True
    assert "cancel" in el["refactor-button"].innerText
    el["refactor-button"].dispatch("click", None)
    assert techdebt.get(module.campaign.ui)["refactor"] is False
    el["refactor-button"].dispatch("click", None)
    game_env.advance_season()
    rec = techdebt.get(module.campaign.ui)
    assert rec["refactor"] is False and rec["refactors"] == 1 and rec["debt"] < 0.3
    texts = [e.text for e in module.chronicle.entries]
    assert any("Refactor season complete" in t for t in texts)


def test_crossing_half_debt_logs_a_warning_once(game_env):
    module = digital(game_env)
    techdebt.put(module.campaign.ui, {"debt": 0.55})
    game_env.advance_season()
    game_env.advance_season()
    warnings = [e for e in module.chronicle.entries if "Technical debt has passed 50%" in e.text]
    assert len(warnings) == 1


def test_debt_is_ignored_during_a_look_back(game_env):
    module = digital(game_env)
    techdebt.put(module.campaign.ui, {"debt": 0.9})
    assert module.current_effects()["materials_yield_mult"] < 1.0
    module.campaign.revisiting = "tribal"
    try:
        assert module.current_effects()["materials_yield_mult"] == 1.0
        assert module._debt_hazard() == 0
    finally:
        module.campaign.revisiting = None


def test_debt_rides_the_save_and_junk_reads_as_none(game_env):
    module = digital(game_env)
    game_env.elements["quick-build-toggle-button"].dispatch("click", None)
    game_env.build("shelter")
    saved = module.get_state()
    assert saved["ui"][techdebt.KEY]["debt"] == pytest.approx(techdebt.DEBT_PER_QUICK_BUILD)
    saved["ui"][techdebt.KEY] = {"debt": "lots", "quick": "x"}
    assert module.load_state(saved)
    assert techdebt.get(module.campaign.ui)["debt"] == 0.0


def test_a_game_that_never_uses_quick_builds_plays_as_before(game_env):
    module = digital(game_env)
    twin = copy.deepcopy(module.state)
    expected = twin.advance_season(sim.effects_or_neutral(module.tree.effects()))
    game_env.advance_season()
    assert module.state.last_report["materials_gathered"] == pytest.approx(expected["materials_gathered"])
    assert sustainability.score(module.state, module.current_effects()) > 0
    assert techdebt.get(module.campaign.ui)["debt"] == 0.0


def test_city_views_dashboard_and_map_show_debt(game_env):
    module = digital(game_env)
    techdebt.put(module.campaign.ui, {"debt": 0.55})
    game_env.toggle_views()
    dash = game_env.elements["views-dashboard"]
    texts = _all_text(dash)
    assert any("Technical debt" in t for t in texts)
    module.views_tab = "map"
    module.update_views_panel()
    assert "map-district--danger" in game_env.elements["views-map-svg"].innerHTML
    assert "technical-debt danger" in game_env.elements["views-map-caption"].innerText


def _all_text(element):
    out = [getattr(element, "innerText", "") or ""]
    for child in getattr(element, "children", []):
        out.extend(_all_text(child))
    return out
