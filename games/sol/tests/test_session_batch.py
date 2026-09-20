"""Tests for the TODO.md 'Per-game: SOL' batch: A1/A3 prestige tree, A2 badge,
A4 tooltip, A5 away report, A6 copy flash, A7 governor personalities, A9
overview, A12/A30 floaters, A13 build plan, A14 tier collapse, A15 sandbox,
A16 travel progress, A17 stats code, A18 tooltips, A19 close calls, A21
compare, A23 specialization, A24 bonus tag, A27 epilogue."""
import json
import sys
import types


def _win(env):
    for p in env.module.PLANETS:
        env.module.planet_state[p]["terraform_progress"] = env.module.TERRAFORM_MAX
    env.module.update_win_display()


def _texts(el):
    out = [el.innerText]
    for c in el.children:
        out.extend(_texts(c))
    return out


# --- A9 overview ---
def test_overview_hidden_then_lists_unlocked_worlds(game_env):
    m = game_env.module
    assert game_env.elements["overview-panel"].hidden is True
    m.unlocked_bodies.add("Mars")
    game_env.elements["overview-toggle-button"].dispatch("click")
    assert game_env.elements["overview-panel"].hidden is False
    joined = " ".join(_texts(game_env.elements["overview-panel"]))
    assert "Mars" in joined and "Moon" not in joined


def test_overview_updates_in_place_without_rebuilding(game_env):
    m = game_env.module
    game_env.elements["overview-toggle-button"].dispatch("click")
    panel = game_env.elements["overview-panel"]
    first_children = list(panel.children)
    game_env.earth["resource_count"] = 42
    game_env.timers.tick_intervals()
    assert list(panel.children) == first_children
    assert any("Iron: 4" in t for t in _texts(panel))


def test_overview_travel_button(game_env):
    m = game_env.module
    m.unlocked_bodies.add("Mars")
    game_env.elements["overview-toggle-button"].dispatch("click")
    game_env.panel_click("overview-panel", action="travel", planet="Mars")
    assert m.current_planet == "Mars"
    assert game_env.elements["mars-view"].hidden is False


def test_overview_travel_refuses_locked_world(game_env):
    game_env.panel_click("overview-panel", action="travel", planet="Pluto")
    assert game_env.module.current_planet == "Earth"


# --- A7 personalities ---
def test_personality_overrides_global_dial(game_env):
    m = game_env.module
    m.unlocked_bodies.add("Mars")
    game_env.panel_click("overview-panel", action="personality", planet="Mars", value="aggressive")
    assert m.governor_settings("Mars") == ("growth", 80.0)
    assert m.governor_settings("Earth") == (m.governor_priority, m.governor_budget_pct)


def test_conservative_personality_only_builds_recyclers(game_env):
    m = game_env.module
    game_env.mars["governor_personality"] = "conservative"
    game_env.mars["resource_count"] = 1000
    game_env.timers.tick_intervals(3)
    assert game_env.mars["generator_count"] == 0
    assert game_env.mars["recycler_count"] > 0


def test_invalid_personality_rejected(game_env):
    game_env.panel_click("overview-panel", action="personality", planet="Mars", value="reckless")
    assert game_env.mars["governor_personality"] == "default"


# --- A23 specialization ---
def test_specialization_needs_development(game_env):
    game_env.panel_click("overview-panel", action="specialize", planet="Mars", value="output")
    assert game_env.mars["specialization"] is None
    game_env.mars["terraform_progress"] = 80
    game_env.panel_click("overview-panel", action="specialize", planet="Mars", value="output")
    assert game_env.mars["specialization"] == "output"
    game_env.panel_click("overview-panel", action="specialize", planet="Mars", value="output")
    assert game_env.mars["specialization"] is None


def test_output_specialization_boosts_production_and_decay(game_env):
    m = game_env.module
    base = _produced(game_env, None)
    spec = _produced(game_env, "output")
    assert spec[0] > base[0] and spec[1] > base[1]
    stab = _produced(game_env, "stability")
    assert stab[1] < base[1]


def _produced(env, spec):
    m = env.module
    env.mars.update(generator_count=10, resource_count=0.0, ecology_health=90.0, terraform_progress=80.0,
                    specialization=spec)
    m._simulate_planet("Mars", 0.0)
    return env.mars["resource_count"], 90.0 - env.mars["ecology_health"]


# --- A1/A3 prestige tree ---
def _prestige(env):
    _win(env)
    env.prestige()


def test_prestige_awards_a_point_and_tree_button_appears(game_env):
    assert game_env.elements["prestige-tree-toggle-button"].hidden is True
    _prestige(game_env)
    m = game_env.module
    assert m.prestige_points_earned == 1
    assert m.prestige_points_available() == 1
    assert game_env.elements["prestige-tree-toggle-button"].hidden is False


def test_unlock_node_spends_points_and_cannot_overspend(game_env):
    m = game_env.module
    _prestige(game_env)
    game_env.elements["prestige-tree-toggle-button"].dispatch("click")
    game_env.panel_click("prestige-tree-panel", action="unlock", node="cheaper_machinery")
    assert m.prestige_has("cheaper_machinery")
    game_env.panel_click("prestige-tree-panel", action="unlock", node="eco_conscious")
    assert not m.prestige_has("eco_conscious")  # no points left


def test_tier_two_locked_until_level_three(game_env):
    m = game_env.module
    m.prestige_level = 1
    m.prestige_points_earned = 5
    game_env.panel_click("prestige-tree-panel", action="unlock", node="deep_research")
    assert not m.prestige_has("deep_research")
    m.prestige_level = 3
    game_env.panel_click("prestige-tree-panel", action="unlock", node="deep_research")
    assert m.prestige_has("deep_research")


def test_cheaper_machinery_discounts_costs(game_env):
    m = game_env.module
    before = m.generator_cost("Earth")
    m.prestige_nodes.add("cheaper_machinery")
    assert m.generator_cost("Earth") < before


def test_head_start_grants_iron_after_prestige(game_env):
    m = game_env.module
    m.prestige_nodes.add("head_start")
    _prestige(game_env)
    assert game_env.earth["resource_count"] == 50.0


def test_deep_research_adds_more_progress(game_env):
    m = game_env.module
    m.prestige_nodes.add("deep_research")
    game_env.earth["resource_count"] = 100
    game_env.fund_research()
    assert m.research_progress == 75.0


def test_governors_mandate_boosts_governed_worlds(game_env):
    m = game_env.module
    game_env.mars["generator_count"] = 10
    m._simulate_planet("Mars", 0.0)
    plain = game_env.mars["resource_count"]
    game_env.mars["resource_count"] = 0.0
    m.prestige_nodes.add("governors_mandate")
    m._simulate_planet("Mars", 0.0)
    assert abs(game_env.mars["resource_count"] - plain * 1.2) < 1e-9


def test_ng_challenge_raises_growth_and_awards_extra_point(game_env):
    m = game_env.module
    m.prestige_level = 2
    m.prestige_points_earned = 2
    game_env.panel_click("prestige-tree-panel", action="unlock", node="ng_challenge")
    assert m.prestige_has("ng_challenge")
    game_env.earth["generator_count"] = 10
    plain = m.generator_cost("Earth")
    game_env.panel_click("prestige-tree-panel", action="challenge")
    assert m.ng_challenge_active and m.generator_cost("Earth") > plain
    _prestige(game_env)
    assert m.prestige_points_earned == 4  # 2 + 1 + 1 extra


def test_challenge_toggle_requires_the_node(game_env):
    game_env.panel_click("prestige-tree-panel", action="challenge")
    assert game_env.module.ng_challenge_active is False


# --- A2 / A4 / A24 ---
def test_badge_and_bonus_tag(game_env):
    m = game_env.module
    assert game_env.elements["prestige-badge"].hidden is True
    m.prestige_level = 2
    m.update_win_display()
    assert game_env.elements["prestige-badge"].innerText == "Prestige 2"
    assert "+20%" in game_env.elements["mars-prestige-bonus"].innerText
    assert game_env.elements["prestige-bonus"].hidden is False


# --- A5 away report ---
def test_away_report_on_return(game_env):
    m = game_env.module
    m.unlocked_bodies.add("Mars")
    game_env.travel_to("Mars")
    game_env.mars["generator_count"] = 1
    game_env.return_to_earth()
    m.total_ticks += 300
    game_env.mars["governed_resource_generated"] += 42
    game_env.travel_to("Mars")
    report = game_env.elements["away-report"]
    assert report.hidden is False
    assert "+42 Water Ice" in game_env.elements["away-report-text"].innerText


def test_no_away_report_for_short_trips(game_env):
    game_env.module.unlocked_bodies.add("Mars")
    game_env.travel_to("Mars")
    game_env.return_to_earth()
    game_env.travel_to("Mars")
    assert game_env.elements["away-report"].hidden is True


# --- A6 copy flash ---
def test_copy_button_flashes_copied(game_env):
    written = []
    clip = types.SimpleNamespace(writeText=lambda t: written.append(t))
    sys.modules["js"].navigator = types.SimpleNamespace(clipboard=clip)
    game_env.elements["copy-share-card-button"].dispatch("click")
    assert "Copied" in game_env.elements["copy-share-card-button"].innerText
    game_env.timers.flush()
    assert "Copy to Clipboard" in game_env.elements["copy-share-card-button"].innerText


# --- A12 / A30 floaters ---
def test_floaters_spawn_and_clean_up(game_env):
    for el in game_env.elements.values():
        el.getBoundingClientRect = lambda: types.SimpleNamespace(left=10, top=10, width=100, height=40)
    game_env.click()
    layer = game_env.elements["spark-layer"]
    assert len(layer.children) == 1
    game_env.timers.flush()
    assert len(layer.children) == 0


def test_floaters_skip_silently_without_layout(game_env):
    game_env.click()
    assert game_env.elements["spark-layer"].children == []


# --- A13 build plan ---
def test_build_plan_add_toggle_remove(game_env):
    m = game_env.module
    game_env.elements["build-plan-input"].value = "  Five miners  "
    game_env.elements["build-plan-add-button"].dispatch("click")
    assert m.build_plan == [{"text": "Five miners", "done": False}]
    assert game_env.elements["build-plan-input"].value == ""
    game_env.panel_click("build-plan-list", action="toggle", step="0")
    assert m.build_plan[0]["done"] is True
    game_env.elements["build-plan-clear-done-button"].dispatch("click")
    assert m.build_plan == []


def test_build_plan_suggest_is_idempotent_and_capped(game_env):
    m = game_env.module
    game_env.elements["build-plan-suggest-button"].dispatch("click")
    n = len(m.build_plan)
    game_env.elements["build-plan-suggest-button"].dispatch("click")
    assert len(m.build_plan) == n
    for i in range(100):
        m._add_build_step(f"s{i}")
    assert len(m.build_plan) == m.BUILD_PLAN_MAX_STEPS


def test_build_plan_ignores_empty_and_bad_clicks(game_env):
    m = game_env.module
    game_env.elements["build-plan-add-button"].dispatch("click")
    game_env.panel_click("build-plan-list", action="remove", step="9")
    game_env.panel_click("build-plan-list", action="remove", step="abc")
    assert m.build_plan == []


# --- A14 ---
def test_research_tier_collapse_toggles(game_env):
    m = game_env.module
    game_env.panel_click("research-tree", tier="0")
    assert 0 in m.research_tree_collapsed
    game_env.panel_click("research-tree", tier="0")
    assert 0 not in m.research_tree_collapsed


# --- A15 sandbox / A27 epilogue ---
def test_sandbox_zeroes_costs_only_after_win(game_env):
    m = game_env.module
    game_env.elements["sandbox-toggle-button"].dispatch("click")
    assert m.sandbox_mode is False  # not won yet
    _win(game_env)
    game_env.elements["sandbox-toggle-button"].dispatch("click")
    assert m.sandbox_mode and m.generator_cost("Earth") == 0 and m.research_fund_cost() == 0
    game_env.timers.tick_intervals()
    game_env.earth["terraform_progress"] = 10  # win lost -> costs return
    assert m.generator_cost("Earth") > 0


def test_prestige_turns_sandbox_off(game_env):
    _win(game_env)
    game_env.elements["sandbox-toggle-button"].dispatch("click")
    game_env.prestige()
    assert game_env.module.sandbox_mode is False


def test_epilogue_toggle_needs_win(game_env):
    game_env.elements["epilogue-button"].dispatch("click")
    assert game_env.elements["epilogue-panel"].hidden is True
    _win(game_env)
    game_env.elements["epilogue-button"].dispatch("click")
    assert game_env.elements["epilogue-panel"].hidden is False
    assert game_env.elements["epilogue-body"].children


# --- A16 ---
def test_travel_progress_readout(game_env):
    m = game_env.module
    m.unlocked_bodies.add("Mars")
    assert game_env.elements["travel-progress"].innerText == "1/8 bodies visited"
    game_env.travel_to("Mars")
    assert game_env.elements["travel-progress"].innerText == "2/8 bodies visited"


# --- A17 / A21 / A8 ---
def test_stats_code_round_trip_only_raises(game_env):
    m = game_env.module
    m.total_manual_clicks = 50
    code = m.export_stats_code()
    m.total_manual_clicks = 10
    ok, _ = m.import_stats_code(code)
    assert ok and m.total_manual_clicks == 50
    m.total_manual_clicks = 500
    m.import_stats_code(code)
    assert m.total_manual_clicks == 500


def test_stats_code_rejects_garbage(game_env):
    m = game_env.module
    assert m.import_stats_code("nope")[0] is False
    assert m.import_stats_code(m.STATS_CODE_PREFIX + "!!!")[0] is False
    import base64
    bad = m.STATS_CODE_PREFIX + base64.b64encode(json.dumps({"total_ticks": -5}).encode()).decode()
    assert m.import_stats_code(bad)[0] is False


def test_compare_run_hands_values_to_js(game_env):
    calls = []
    sys.modules["js"].SolCompare = types.SimpleNamespace(run=lambda s: calls.append(json.loads(s)))
    game_env.module.total_manual_clicks = 7
    game_env.elements["compare-run-button"].dispatch("click")
    assert calls[0]["total_manual_clicks"] == 7 and "prestige_level" in calls[0]


def test_compare_run_degrades_without_js_helper(game_env):
    game_env.elements["compare-run-button"].dispatch("click")
    assert "isn't available" in game_env.elements["compare-run-results"].innerText


def test_stats_panel_shows_governed_total(game_env):
    game_env.mars["governed_resource_generated"] = 12
    game_env.toggle_stats()
    assert any("governed (all worlds): 12" in t for t in _texts(game_env.elements["stats-panel-content"]))


# --- A19 close calls ---
def test_close_call_needs_drop_then_recovery(game_env):
    m = game_env.module
    game_env.mars["ecology_health"] = 1.0
    m._track_close_calls()
    assert not m.close_call_hit
    game_env.mars["ecology_health"] = 60.0
    m._track_close_calls()
    assert m.close_call_hit and not m.back_from_brink_hit
    assert "close_call" in m.achievement_ids_earned()


def test_back_from_the_brink_needs_zero(game_env):
    m = game_env.module
    game_env.mars["ecology_health"] = 0.0
    m._track_close_calls()
    game_env.mars["ecology_health"] = 55.0
    m._track_close_calls()
    assert m.back_from_brink_hit


def test_world_reset_forgets_pending_close_call(game_env):
    m = game_env.module
    game_env.mars["ecology_health"] = 0.0
    m._track_close_calls()
    game_env.reset_world("Mars")
    m._track_close_calls()
    assert not m.close_call_hit


# --- save robustness ---
def test_save_round_trip_of_new_state(game_env):
    m = game_env.module
    m.prestige_level = 3
    m.prestige_points_earned = 4
    m.prestige_nodes.add("head_start")
    m.build_plan.append({"text": "x", "done": True})
    game_env.mars["governor_personality"] = "balanced"
    m.close_call_hit = True
    data = json.loads(json.dumps(m.get_state()))
    m.prestige_nodes.clear()
    m.build_plan.clear()
    game_env.mars["governor_personality"] = "default"
    m.load_state(data)
    assert m.prestige_has("head_start") and m.build_plan == [{"text": "x", "done": True}]
    assert game_env.mars["governor_personality"] == "balanced" and m.close_call_hit


def test_legacy_save_defaults_points_to_level(game_env):
    m = game_env.module
    data = m.get_state()
    for key in ("prestige_points_earned", "prestige_nodes", "build_plan", "ng_challenge_active", "sandbox_mode"):
        data.pop(key)
    data["prestige_level"] = 2
    m.load_state(data)
    assert m.prestige_points_earned == 2 and m.prestige_nodes == set()


def test_garbage_new_fields_do_not_crash_load(game_env):
    m = game_env.module
    data = m.get_state()
    data.update(prestige_points_earned="lots", prestige_nodes="nope", build_plan=[1, {"text": 5}, {"text": " ok "}],
                ng_challenge_active="yes", ecology_low_seen=["Mars", "Narnia"])
    data["planet_state"]["Mars"].update(governor_personality="evil", specialization="chaos")
    m.load_state(data)
    assert m.build_plan == [{"text": "ok", "done": False}]
    assert m.ng_challenge_active is False and game_env.mars["governor_personality"] == "default"
    assert game_env.mars["specialization"] is None
    assert m._ecology_low_seen == {"Mars"}
    game_env.timers.tick_intervals()


def test_challenge_flag_without_node_is_inert(game_env):
    m = game_env.module
    m.ng_challenge_active = True
    assert m.generator_cost("Earth") == 10
