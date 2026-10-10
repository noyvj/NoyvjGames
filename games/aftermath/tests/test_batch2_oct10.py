"""Batch 2 (2026-10-10): E-19 tree search and filters, E-25 allocation presets, E-30 save health badge,
E-9 difficulty-adjusted score, E-4 shareable run codes and challenge runs, E-13 schedule builder,
E-3 purchase route planner and the plain-text schedule of E-5."""

import json

import pytest


def _finish(env):
    while not env.run.is_complete():
        env.resolve_event()


def _chips(env):
    return [chip for group in env.elements["skill-filter-chips"].children for chip in group.children]


def _chip(env, kind, value):
    for chip in _chips(env):
        if chip.getAttribute("data-filter-kind") == kind and chip.getAttribute("data-filter-value") == value:
            return chip
    raise AssertionError((kind, value))


# ---------------------------------------------------------------------------------------------- E-19
def test_chips_are_built_once_for_status_and_type(game_env):
    kinds = [(c.getAttribute("data-filter-kind"), c.getAttribute("data-filter-value")) for c in _chips(game_env)]
    assert ("status", "affordable") in kinds and ("group", "weather") in kinds
    assert len(kinds) == 4 + 5
    assert _chip(game_env, "status", "all").getAttribute("aria-pressed") == "true"


def test_search_matches_name_effect_and_the_real_world_note(game_env):
    m = game_env.module
    assert m.skill_matches("early_warning", query="early")
    assert m.skill_matches("early_warning", query="mitigation all events")  # effect text, two words
    assert m.skill_matches("climate_hardening", query="retrofit")  # real-world note
    assert not m.skill_matches("early_warning", query="retrofit")
    assert m.skill_matches("early_warning", query="  EARLY  ")


def test_status_chips(game_env):
    m = game_env.module
    m.skill_tree.knowledge_points = 3
    assert m.skill_matches("reinforced_infrastructure", status="affordable")
    assert not m.skill_matches("early_warning", status="affordable")  # costs 5
    assert not m.skill_matches("mutual_aid_network", status="affordable")  # prerequisites missing
    m.skill_tree.unlocked.add("community_reserves")
    assert m.skill_matches("community_reserves", status="owned")
    assert not m.skill_matches("early_warning", status="owned")
    m.meta["pinned_skills"] = ["early_warning", "community_reserves"]
    assert m.skill_matches("early_warning", status="pinned")
    assert not m.skill_matches("community_reserves", status="pinned")  # owned skills are not "pinned"


def test_type_chips_and_every_skill_has_a_type(game_env):
    m = game_env.module
    assert set(m.SKILL_GROUP) == set(m.SKILLS)
    assert m.skill_matches("climate_hardening", group="weather")
    assert not m.skill_matches("civic_preparedness", group="weather")
    assert m.skill_matches("civic_preparedness", group="social")
    assert [s for s in m.SKILLS if m.skill_matches(s, group="starting")] == [
        "reinforced_infrastructure", "community_reserves", "adaptive_growth"
    ]


def test_clicking_a_chip_hides_rows_and_updates_the_summary(game_env):
    m = game_env.module
    _chip(game_env, "group", "weather").dispatch("click", None)
    assert m.skill_filter_group == "weather"
    hidden = {s for s in m.SKILLS if game_env.elements[f"skill-{s}-row"].hidden}
    assert hidden == set(m.SKILLS) - {"climate_hardening"}
    assert game_env.elements["skill-filter-summary"].innerText == "Showing 1 of 7 skills."
    assert _chip(game_env, "group", "weather").getAttribute("aria-pressed") == "true"
    assert _chip(game_env, "group", "any").getAttribute("aria-pressed") == "false"
    assert game_env.elements["skill-filter-clear"].hidden is False


def test_search_input_filters_and_an_empty_result_says_so(game_env):
    m = game_env.module
    game_env.elements["skill-search-input"].value = "zzzz"
    game_env.elements["skill-search-input"].dispatch("input", None)
    assert all(game_env.elements[f"skill-{s}-row"].hidden for s in m.SKILLS)
    assert "No skills match" in game_env.elements["skill-filter-summary"].innerText


def test_clear_restores_everything(game_env):
    m = game_env.module
    _chip(game_env, "status", "owned").dispatch("click", None)
    game_env.elements["skill-search-input"].value = "x"
    game_env.elements["skill-search-input"].dispatch("input", None)
    game_env.elements["skill-filter-clear"].dispatch("click", None)
    assert (m.skill_search_text, m.skill_filter_status, m.skill_filter_group) == ("", "all", "any")
    assert not any(game_env.elements[f"skill-{s}-row"].hidden for s in m.SKILLS)
    assert game_env.elements["skill-search-input"].value == ""
    assert game_env.elements["skill-filter-clear"].hidden is True


def test_filters_follow_the_state_after_an_unlock(game_env):
    m = game_env.module
    m.skill_tree.knowledge_points = 3
    _chip(game_env, "status", "affordable").dispatch("click", None)
    assert not game_env.elements["skill-reinforced_infrastructure-row"].hidden
    game_env.unlock_skill("reinforced_infrastructure")
    assert game_env.elements["skill-reinforced_infrastructure-row"].hidden  # owned now, no longer "affordable"


# ---------------------------------------------------------------------------------------------- E-25
def test_save_preset_validates(game_env):
    m = game_env.module
    assert m.save_preset("", 1, 1)[0] is False
    assert m.save_preset("Empty", 0, 0)[0] is False
    assert m.save_preset("Big", 21, 0)[0] is False
    assert m.save_preset("Words", "x", 0)[0] is False
    ok, message = m.save_preset("  Flood   plan ", 3, 1)
    assert ok and message == "Saved preset: Flood plan: 3 resilience, 1 growth."
    assert m.meta["presets"] == [{"name": "Flood plan", "resilience": 3, "growth": 1}]


def test_same_name_replaces_and_the_list_is_capped(game_env):
    m = game_env.module
    m.save_preset("Flood plan", 3, 1)
    ok, message = m.save_preset("flood PLAN", 2, 0)
    assert ok and message.startswith("Updated") and len(m.meta["presets"]) == 1
    assert m.meta["presets"][0]["resilience"] == 2
    for i in range(7):
        assert m.save_preset(f"P{i}", 1, 0)[0]
    ok, message = m.save_preset("One too many", 1, 0)
    assert not ok and "up to 8" in message


def test_presets_persist_and_survive_a_sanitised_reload(game_env):
    m = game_env.module
    m.save_preset("Flood plan", 3, 1)
    stored = json.loads(game_env.local_storage.getItem(m.META_STORAGE_KEY))
    assert stored["presets"] == [{"name": "Flood plan", "resilience": 3, "growth": 1}]
    cleaned = m._sanitize_meta({"presets": [
        {"name": "ok", "resilience": 1, "growth": 0}, {"name": "", "resilience": 1, "growth": 0},
        {"name": "zero", "resilience": 0, "growth": 0}, {"name": "ok", "resilience": 2, "growth": 2},
        {"name": "bad", "resilience": "3", "growth": 0}, "junk", {"name": "neg", "resilience": -1, "growth": 2},
    ]})
    assert cleaned["presets"] == [{"name": "ok", "resilience": 1, "growth": 0}]


def test_presets_travel_in_the_progress_export(game_env):
    m = game_env.module
    m.save_preset("Flood plan", 3, 1)
    code = m.export_progress_code()
    m.meta["presets"] = []
    assert m.import_progress_code(code)
    assert m.meta["presets"] == [{"name": "Flood plan", "resilience": 3, "growth": 1}]


def test_apply_buys_resilience_then_growth_in_one_undoable_click(game_env):
    m = game_env.module
    m.save_preset("Flood plan", 3, 1)
    start = game_env.run.resources
    message, bought_r, bought_g = m.apply_preset("Flood plan")
    assert (bought_r, bought_g) == (3, 1)
    assert game_env.run.resilience_capacity == 3 and game_env.run.growth_capacity == 1
    assert game_env.run.resources == start - 3 * m.RESILIENCE_COST - m.GROWTH_COST
    assert message == "Applied Flood plan: bought 3 resilience, 1 growth."
    assert game_env.run.undo_count() == 1  # one click
    game_env.elements["undo-allocation-button"].dispatch("click", None)
    assert game_env.run.resilience_capacity == 0 and game_env.run.growth_capacity == 0
    assert game_env.run.resources == start


def test_apply_stops_at_what_you_can_afford(game_env):
    m = game_env.module
    m.save_preset("Big", 10, 5)
    game_env.run.resources = 80.0  # 3 resilience (75) then 0 growth
    message, bought_r, bought_g = m.apply_preset("Big")
    assert (bought_r, bought_g) == (3, 0)
    assert "in part" in message and "3 of 10 resilience" in message and "not enough resources" in message
    game_env.run.resources = 5.0
    message, bought_r, bought_g = m.apply_preset("Big")
    assert (bought_r, bought_g) == (0, 0) and "nothing bought" in message
    assert game_env.run.undo_count() == 1  # the empty apply recorded nothing


def test_apply_respects_the_resilience_cap(game_env):
    m = game_env.module
    m.save_preset("Cap", 20, 0)
    game_env.run.resources = 1000.0
    _msg, bought_r, _g = m.apply_preset("Cap")
    assert game_env.run.mitigation_fraction() == pytest.approx(m.MAX_MITIGATION)
    assert bought_r == 17  # 17 x 5% = 85%


def test_apply_after_the_run_ends_does_nothing(game_env):
    m = game_env.module
    m.save_preset("Flood plan", 3, 1)
    _finish(game_env)
    message, bought_r, bought_g = m.apply_preset("Flood plan")
    assert (bought_r, bought_g) == (0, 0) and "run is over" in message


def test_the_ui_lists_applies_and_deletes(game_env):
    m = game_env.module
    game_env.elements["preset-name-input"].value = "Flood plan"
    game_env.elements["preset-resilience-input"].value = "2"
    game_env.elements["preset-growth-input"].value = "1"
    game_env.elements["preset-save-button"].dispatch("click", None)
    assert game_env.elements["preset-status"].innerText.startswith("Saved preset")
    assert game_env.elements["preset-apply-row"].hidden is False
    options = game_env.elements["preset-select"].children
    assert [o.innerText for o in options] == ["Flood plan: 2 resilience, 1 growth"]
    game_env.elements["preset-apply-button"].dispatch("click", None)
    assert game_env.run.resilience_capacity == 2 and game_env.run.growth_capacity == 1
    rows = game_env.elements["preset-list"].children
    delete = [b for b in rows[0].children if b.getAttribute("data-action") == "delete"][0]

    class Event:
        target = delete

    game_env.elements["preset-list"].dispatch("click", Event())
    assert m.meta["presets"] == [] and game_env.elements["preset-apply-row"].hidden is True


def test_use_this_turn_fills_the_boxes_from_what_was_bought(game_env):
    game_env.invest_resilience()
    game_env.invest_resilience()
    game_env.invest_growth()
    game_env.elements["preset-from-turn-button"].dispatch("click", None)
    assert game_env.elements["preset-resilience-input"].value == "2"
    assert game_env.elements["preset-growth-input"].value == "1"


# ---------------------------------------------------------------------------------------------- E-30
def test_format_age(game_env):
    f = game_env.module.format_age
    assert [f(0), f(4), f(12), f(125), f(7300)] == ["just now", "just now", "12s ago", "2 min ago", "2 h ago"]


def test_a_fresh_session_says_it_saves_automatically(game_env):
    assert game_env.elements["save-health"].getAttribute("data-state") == "ready"
    assert game_env.elements["save-health-export-button"].hidden is True


def test_a_write_makes_the_badge_say_saved_with_an_age(game_env, monkeypatch):
    m = game_env.module
    clock = {"t": 1000.0}
    monkeypatch.setattr(m, "_now", lambda: clock["t"])
    game_env.invest_resilience()
    m.save_meta()
    m.render()
    assert game_env.elements["save-health"].getAttribute("data-state") == "saved"
    assert game_env.elements["save-health-text"].innerText == "✓ Saved just now"
    assert game_env.elements["save-health"].getAttribute("data-saved-at") == "1000000"
    clock["t"] += 12
    m.render()
    assert game_env.elements["save-health-text"].innerText == "✓ Saved 12s ago"


def test_a_failing_store_shows_the_warning_and_the_export_button(game_env):
    m = game_env.module

    def boom(key, value):
        raise RuntimeError("QuotaExceededError")

    game_env.local_storage.setItem = boom
    assert m.save_meta() is None  # never raises
    m.render()
    assert game_env.elements["save-health"].getAttribute("data-state") == "failed"
    assert "Not saved" in game_env.elements["save-health-text"].innerText
    assert game_env.elements["save-health-export-button"].hidden is False
    assert "Not saved" in game_env.elements["save-health-alert"].innerText


def test_the_badge_recovers_when_the_key_writes_again(game_env):
    m = game_env.module
    original = game_env.local_storage.setItem

    def boom(key, value):
        raise RuntimeError("full")

    game_env.local_storage.setItem = boom
    m.save_meta()
    m.render()
    game_env.local_storage.setItem = original
    m.save_meta()
    m.render()
    assert game_env.elements["save-health"].getAttribute("data-state") == "saved"
    assert game_env.elements["save-health-export-button"].hidden is True
    assert game_env.elements["save-health-alert"].innerText == "Progress is saving again."


def test_progress_that_vanished_from_storage_is_flagged_unsaved(game_env):
    m = game_env.module
    m.skill_tree.add_knowledge(4)
    m.skill_tree.save()
    m.render()
    assert game_env.elements["save-health"].getAttribute("data-state") == "saved"
    game_env.local_storage.removeItem(m.SKILL_TREE_STORAGE_KEY)  # cleared from another tab
    m.render()
    assert game_env.elements["save-health"].getAttribute("data-state") == "unsaved"
    assert "skill tree" in game_env.elements["save-health-text"].innerText
    assert game_env.elements["save-health-export-button"].hidden is False


def test_export_button_shows_a_selected_code_and_says_where_it_went(game_env):
    m = game_env.module
    m.skill_tree.add_knowledge(2)
    game_env.elements["save-health-export-button"].dispatch("click", None)
    area = game_env.elements["save-health-code"]
    assert area.hidden is False and area.value == m.export_progress_code()
    assert "Copy this code" in game_env.elements["save-health-code-status"].innerText  # no clipboard in the test fake


def test_unreadable_stored_json_counts_as_unsaved(game_env):
    m = game_env.module
    game_env.local_storage.setItem(m.META_STORAGE_KEY, "{not json")
    assert "settlement notes and presets" in m.unsaved_progress()


# ---------------------------------------------------------------------------------------------- E-9
def test_adjusted_score_credits_harsh_draws_and_discounts_gentle_ones(game_env):
    m = game_env.module
    harsh = [{"type": "flood", "damage": 23.0, "severity": 1.15}]
    gentle = [{"type": "flood", "damage": 17.0, "severity": 0.85}]
    typical = [{"type": "flood", "damage": 20.0, "severity": 1.0}]
    assert m.adjusted_score(100, harsh) == pytest.approx(100 + 23 * (1 - 1 / 1.15))
    assert m.adjusted_score(100, harsh) > 100 > m.adjusted_score(100, gentle)
    assert m.adjusted_score(100, typical) == 100
    assert m.adjusted_score(100, []) == 100


def test_adjusted_score_is_never_negative_and_ignores_malformed_entries(game_env):
    m = game_env.module
    log = [{"type": "flood", "damage": 500.0, "severity": 0.5}, "junk", {"type": "storm"}]
    assert m.adjusted_score(0, log) == 0.0


def test_run_one_has_equal_raw_and_adjusted_scores(game_env):
    _finish(game_env)
    m = game_env.module
    assert m.adjusted_score(game_env.run.run_score(), game_env.run.event_log) == pytest.approx(game_env.run.run_score())


def test_raw_and_adjusted_show_in_the_summary_the_card_and_the_copy_text(game_env):
    m = game_env.module
    _finish(game_env)
    game_env.start_new_run()
    _finish(game_env)  # run 2 has varied severity
    stats_line = game_env.elements["run-summary-panel"].children[0].innerText
    assert f"Score {game_env.run.run_score():.0f}, adjusted" in stats_line
    assert "average severity" in stats_line
    assert "adjusted" in m.run_summary_text().split("\n")[1]
    game_env.toggle_past_runs()
    titles = [card.children[0].innerText for card in game_env.elements["past-runs-list"].children]
    assert all("adjusted" in t and "average severity" in t for t in titles)


def test_the_toughest_run_text_and_badge_show_both_numbers(game_env):
    m = game_env.module
    m.run_history[:] = [50.0]
    m.run_log_history[:] = [{
        "run_number": 1, "score": 50.0, "resilience_capacity": 0, "growth_capacity": 0, "damage_taken": 150.0,
        "knowledge_earned": 3, "event_log": [{"type": "flood", "damage": 40.0, "severity": 1.15}] * 3,
    }]
    m.render()
    text = game_env.elements["toughest-run-display"].innerText
    assert "scored 50" in text and "adjusted" in text
    assert "run 1 scored 50" in game_env.elements["settlement-badge-toughest"].title
    assert "adjusted" in game_env.elements["settlement-badge-toughest"].title


def test_the_badge_title_says_what_earns_it_before_it_is_earned(game_env):
    assert "not earned yet" in game_env.module.toughest_badge_title()


def test_past_runs_can_be_sorted_by_adjusted_score(game_env):
    m = game_env.module
    assert "score_adjusted" in m.PAST_RUN_SORTS
    m.run_log_history[:] = [
        {"run_number": 1, "score": 100.0, "event_log": [{"type": "flood", "damage": 20.0, "severity": 0.85}]},
        {"run_number": 2, "score": 95.0, "event_log": [{"type": "flood", "damage": 60.0, "severity": 1.15}]},
    ]
    m.past_runs_sort = "score_high"
    assert [e["run_number"] for _i, e in m.past_runs_view()] == [1, 2]
    m.past_runs_sort = "score_adjusted"
    assert [e["run_number"] for _i, e in m.past_runs_view()] == [2, 1]


# ---------------------------------------------------------------------------------------------- E-3
def test_the_route_puts_prerequisites_first_and_skips_owned_skills(game_env):
    m = game_env.module
    m.meta["pinned_skills"] = ["climate_hardening"]
    assert m.purchase_route() == ["reinforced_infrastructure", "early_warning", "climate_hardening"]
    m.skill_tree.unlocked.add("reinforced_infrastructure")
    assert m.purchase_route() == ["early_warning", "climate_hardening"]


def test_the_route_has_no_duplicates_across_pins(game_env):
    m = game_env.module
    m.meta["pinned_skills"] = ["mutual_aid_network", "civic_preparedness", "reinforced_infrastructure"]
    route = m.purchase_route()
    assert len(route) == len(set(route))
    assert route.index("community_reserves") < route.index("mutual_aid_network")
    assert route.index("community_reserves") < route.index("civic_preparedness")


def test_running_totals_and_the_estimate_use_the_average_knowledge_per_run(game_env):
    m = game_env.module
    m.meta["pinned_skills"] = ["climate_hardening"]
    rows = m.route_rows()
    assert [r["running_total"] for r in rows] == [3, 8, 14]  # costs 3, 5, 6
    assert all(r["runs"] is None for r in rows)  # no run completed: no earning rate yet
    m.run_history[:] = [100.0, 100.0]
    m.skill_tree.lifetime_knowledge = 8  # average 4 per run
    m.skill_tree.knowledge_points = 4
    rows = m.route_rows()
    assert [r["short"] for r in rows] == [0, 4, 10]
    assert [r["runs"] for r in rows] == [0, 1, 3]  # ceil(4/4), ceil(10/4)
    assert rows[0]["prerequisite_only"] and not rows[2]["prerequisite_only"]


def test_the_planner_panel_follows_pins_live(game_env):
    m = game_env.module
    assert game_env.elements["route-planner"].hidden is True
    m.toggle_pin_skill("mutual_aid_network")
    m.render()
    assert game_env.elements["route-planner"].hidden is False
    steps = [c.innerText for c in game_env.elements["route-list"].children]
    assert len(steps) == 3 and steps[0].startswith("1. Reinforced Infrastructure (needed first)")
    assert "Route total 12 knowledge" in game_env.elements["route-summary"].innerText
    assert game_env.elements["route-planner-summary"].innerText == "Purchase route (3 steps)"
    m.skill_tree.knowledge_points = 12
    m.render()
    assert "can afford the whole route now" in game_env.elements["route-summary"].innerText


# ---------------------------------------------------------------------------------------------- E-5
def test_the_plain_text_schedule_names_every_event_in_words(game_env):
    m = game_env.module
    text = m.schedule_plain_text()
    assert text.count("; ") == len(game_env.run.schedule) - 1
    assert "1. Flood (next, about 40 damage)" in text and "2. Heatwave (upcoming" in text
    game_env.resolve_event()
    assert "1. Flood (faced," in m.schedule_plain_text()
    assert game_env.elements["schedule-text"].innerText == m.schedule_plain_text()


# ---------------------------------------------------------------------------------------------- E-4
def test_seed_text_round_trips_every_kind_of_number(game_env):
    m = game_env.module
    for number in (0, 1, 2, 97, 30, 123456, 28_629_150):
        text = m.seed_text_for_int(number)
        assert text.startswith("AFTERMATH-") and len(text) == len("AFTERMATH-") + 5
        assert m.int_from_seed_text(text) == number
    assert m.seed_text_for_int(28_629_151) is None and m.seed_text_for_int(-1) is None


def test_custom_schedule_numbers_round_trip_and_reject_garbage(game_env):
    m = game_env.module
    events = ["flood", "storm", "heat_mortality", "civil_unrest", "supply_chain"]
    assert m.custom_schedule_from_number(m.custom_schedule_number(events)) == events
    seven = list(m.EVENT_CODE_ORDER)
    assert m.custom_schedule_from_number(m.custom_schedule_number(seven)) == seven
    assert m.custom_schedule_number(seven + ["flood"]) is None  # too long for the seed
    assert m.custom_schedule_from_number(m.custom_schedule_number(["flood", "storm"])) is None  # too short
    assert m.custom_schedule_from_number(0) is None and m.custom_schedule_from_number(1) is None
    assert m.custom_schedule_from_number(8 ** 4 + 7 * 8 ** 3 + 8 ** 2 + 1) is None  # digit 7 is reserved


def test_every_event_type_has_a_slot_in_the_code_order(game_env):
    m = game_env.module
    assert set(m.EVENT_CODE_ORDER) == set(m.EVENT_LABEL)
    assert len(m.EVENT_CODE_ORDER) <= 8


def test_every_scenario_word_fits_the_mode_limit_even_extended(game_env):
    m = game_env.module
    assert set(m.CODE_WORD_SCENARIO.values()) == set(m.SCENARIOS)
    for word in m.CODE_WORD_SCENARIO:
        assert len(word) + 1 <= 8 and word.isalpha()
    assert len(m.CUSTOM_CODE_WORD) <= 8
    names = m.run_code_mode_names()
    assert names["coastal"] == "Coastal" and names["coastalx"] == "Coastal, extended" and "custom" in names


def test_no_run_code_until_the_run_is_finished(game_env):
    m = game_env.module
    assert m.run_code_fields() is None and m.make_run_code() is None
    assert game_env.elements["run-end-code-wrap"].hidden is True
    assert "Finish a run" in game_env.elements["run-end-code-note"].innerText
    _finish(game_env)
    assert game_env.elements["run-end-code-wrap"].hidden is False


def test_a_finished_run_makes_a_code_that_decodes_to_its_numbers(game_env):
    m = game_env.module
    game_env.invest_resilience()
    _finish(game_env)
    code = m.make_run_code()
    decoded = m.shared_run_code.decode(code, "aftermath")
    assert decoded["ok"] and decoded["mode"] == "classic" and decoded["verified"] is False
    assert decoded["score"] == round(game_env.run.run_score())
    assert decoded["stats"] == [
        round(m.adjusted_score(game_env.run.run_score(), game_env.run.event_log)), round(game_env.run.damage_taken)
    ]
    assert m.int_from_seed_text(decoded["seed"]) == 1  # run number 1 is the draw


def test_scenario_and_extended_runs_get_their_own_mode_words(game_env):
    m = game_env.module
    assert m.run_code_mode(m.RunState(scenario="coastal")) == "coastal"
    assert m.run_code_mode(m.RunState(scenario="san_francisco", extended=True)) == "sanfranx"
    assert m.run_code_mode(m.RunState(custom_events=["flood", "storm", "flood"])) == "custom"


def test_challenge_spec_reads_scenario_extended_draw_and_custom(game_env):
    m = game_env.module
    code = m.shared_run_code.encode({"game": "aftermath", "seed": m.seed_text_for_int(42), "mode": "houstonx"})
    spec, error = m.challenge_spec(m.shared_run_code.decode(code, "aftermath"))
    assert error == "" and spec == {"scenario": "houston", "extended": True, "draw": 42, "custom_events": None}
    events = ["storm", "storm", "flood"]
    code = m.schedule_code(events)
    spec, _e = m.challenge_spec(m.shared_run_code.decode(code, "aftermath"))
    assert spec["custom_events"] == events and spec["draw"] == 1


def test_challenge_spec_refuses_what_it_cannot_play(game_env):
    m = game_env.module
    no_seed = m.shared_run_code.encode({"game": "aftermath", "mode": "classic"})
    assert "no schedule" in m.challenge_spec(m.shared_run_code.decode(no_seed, "aftermath"))[1]
    odd_mode = m.shared_run_code.encode({"game": "aftermath", "seed": m.seed_text_for_int(5), "mode": "zzzz"})
    assert "does not know" in m.challenge_spec(m.shared_run_code.decode(odd_mode, "aftermath"))[1]
    bad_custom = m.shared_run_code.encode({"game": "aftermath", "seed": m.seed_text_for_int(0), "mode": "custom"})
    assert "not valid" in m.challenge_spec(m.shared_run_code.decode(bad_custom, "aftermath"))[1]
    assert m.challenge_spec(m.shared_run_code.decode("RUN-NOPE", "aftermath"))[0] is None


def _friend_code(m, mode="classic", draw=7, score=150, adjusted=170, damage=90):
    return m.shared_run_code.encode({
        "game": "aftermath", "seed": m.seed_text_for_int(draw), "mode": mode, "score": score, "stats": [adjusted, damage],
    })


def test_a_challenge_run_ignores_the_players_tree_and_memory(game_env):
    m = game_env.module
    for skill in m.SKILLS:
        m.skill_tree.unlocked.add(skill)
    m.societal_memory.update({"weather", "social"})
    plain = m.RunState(run_number=3)
    assert plain.resilience_capacity == 2 and plain.resources == 250 and plain.growth_capacity == 1
    state, error = m.challenge_run_from_code(_friend_code(m))
    assert error == "" and state.normalised
    assert (state.resources, state.resilience_capacity, state.growth_capacity) == (m.STARTING_RESOURCES, 0, 0)
    assert state.mitigation_for("flood") == 0.0 and state.mitigation_for("civil_unrest") == 0.0


def test_a_challenge_uses_the_codes_draw_at_the_plain_band_whatever_your_career(game_env):
    m = game_env.module
    state, _e = m.challenge_run_from_code(_friend_code(m, draw=11))
    before = [state.severity_at(i) for i in range(7)]
    for skill in m.SKILLS:
        m.skill_tree.unlocked.add(skill)
    m.run_history[:] = [100.0] * 40
    assert [state.severity_at(i) for i in range(7)] == before
    assert all(0.85 <= s <= 1.15 for s in before)
    assert before == [m.event_severity(11, i, 0, 0) for i in range(7)]


def test_start_challenge_is_refused_mid_run(game_env):
    m = game_env.module
    game_env.resolve_event()
    message = m.start_challenge(_friend_code(m))
    assert "Finish your current run first" in message and not game_env.run.normalised


def test_start_challenge_between_runs_swaps_the_run_and_shows_the_banner(game_env):
    m = game_env.module
    message = m.start_challenge(_friend_code(m, mode="coastal"))
    assert message.startswith("Challenge started")
    assert game_env.run.normalised and game_env.run.schedule == m.SCENARIOS["coastal"]["schedule"]
    assert game_env.elements["challenge-banner"].hidden is False
    assert "Their run ended with 150" in game_env.elements["challenge-banner"].innerText
    assert game_env.elements["challenge-leave-button"].hidden is False
    assert game_env.elements["scenario-wrapper"].hidden is True
    assert "Challenge runs earn no knowledge" in game_env.elements["knowledge-preview-display"].innerText


def test_a_bad_code_changes_nothing(game_env):
    m = game_env.module
    before = game_env.run
    message = m.start_challenge("RUN-AFTERMATH-AAAAA-BBB")
    assert message and game_env.run is before and not game_env.run.normalised
    assert game_env.elements["challenge-status"].innerText == message


def test_finishing_a_challenge_pays_nothing_and_counts_toward_the_tally(game_env):
    m = game_env.module
    kp, history, logs, awarded = m.skill_tree.knowledge_points, list(m.run_history), list(m.run_log_history), m.highest_awarded_run
    m.start_challenge(_friend_code(m))
    _finish(game_env)
    assert (m.skill_tree.knowledge_points, m.run_history, m.run_log_history, m.highest_awarded_run) == (kp, history, logs, awarded)
    assert m.meta["challenge_runs"] == 1
    best = m.meta["challenge_best"]
    assert list(best.values()) == [round(game_env.run.run_score())]
    text = game_env.elements["run-summary-display"].innerText
    assert text.startswith("Challenge finished: you ended with") and "Their run ended with 150, 170 adjusted" in text
    assert "friendly note, not a ranking" in text and "earn no knowledge" in text
    assert "Challenge runs finished: 1." in game_env.elements["challenge-stats"].innerText
    for child in game_env.elements["run-summary-panel"].children:
        assert child.className != "knowledge-breakdown"


def test_the_best_score_per_code_is_kept_and_capped(game_env):
    m = game_env.module
    code = _friend_code(m)
    for _ in range(2):
        m.start_challenge(code)
        _finish(game_env)
    assert m.meta["challenge_runs"] == 2 and len(m.meta["challenge_best"]) == 1
    for i in range(m.CHALLENGE_BEST_MAX + 5):
        m.meta["challenge_best"][f"RUN-{i}"] = i
        while len(m.meta["challenge_best"]) > m.CHALLENGE_BEST_MAX:
            m.meta["challenge_best"].pop(next(iter(m.meta["challenge_best"])))
    assert len(m.meta["challenge_best"]) == m.CHALLENGE_BEST_MAX


def test_the_next_real_run_follows_the_last_awarded_run_not_the_challenge(game_env):
    m = game_env.module
    _finish(game_env)  # run 1 awarded
    m.start_challenge(_friend_code(m))
    _finish(game_env)
    game_env.start_new_run()
    assert game_env.run.run_number == 2 and not game_env.run.normalised


def test_leaving_a_challenge_starts_the_next_numbered_run(game_env):
    m = game_env.module
    m.start_challenge(_friend_code(m))
    game_env.resolve_event()
    game_env.elements["challenge-leave-button"].dispatch("click", None)
    assert not game_env.run.normalised and game_env.run.run_number == 1 and game_env.run.event_index == 0
    assert game_env.elements["challenge-banner"].hidden is True


def test_a_challenge_run_survives_a_save_round_trip(game_env):
    m = game_env.module
    code = _friend_code(m, mode="urban", draw=9)
    m.start_challenge(code)
    game_env.resolve_event()
    state = m.get_state()
    assert state["challenge_code"] == m.shared_run_code.decode(code, "aftermath")["code"]
    game_env.start_new_run() if game_env.run.is_complete() else None
    m.run = m.RunState()  # forget it
    m.load_state(json.loads(json.dumps(state)))
    assert game_env.run.normalised and game_env.run.event_index == 1
    assert game_env.run.schedule == m.SCENARIOS["urban"]["schedule"] and game_env.run.draw == 9
    assert game_env.run.challenge["their_score"] == 150


def test_ordinary_saves_have_no_challenge_or_custom_fields(game_env):
    state = game_env.module.get_state()
    assert "challenge_code" not in state and "custom_events" not in state


def test_the_scenario_picker_cannot_replace_a_challenge(game_env):
    m = game_env.module
    m.start_challenge(_friend_code(m))
    game_env.elements["scenario-select"].value = "coastal"
    game_env.elements["scenario-select"].dispatch("change", None)
    assert game_env.run.normalised


# ---------------------------------------------------------------------------------------------- E-13
def test_the_draft_is_capped_reorderable_and_removable(game_env):
    m = game_env.module
    for _ in range(m.CUSTOM_MAX_EVENTS):
        assert m.builder_add("flood")
    assert not m.builder_add("storm") and not m.builder_add("not_an_event")
    m.builder_draft[:] = ["flood", "storm", "heatwave"]
    assert m.builder_move(2, -1) and m.builder_draft == ["flood", "heatwave", "storm"]
    assert not m.builder_move(0, -1) and not m.builder_move(2, 1)
    assert m.builder_remove(1) and m.builder_draft == ["flood", "storm"]
    assert not m.builder_remove(5)


def test_save_needs_a_name_and_three_to_seven_events(game_env):
    m = game_env.module
    assert m.save_custom_schedule("A", ["flood", "storm"])[0] is False
    assert m.save_custom_schedule("", ["flood", "storm", "flood"])[0] is False
    ok, message = m.save_custom_schedule("  Triple   flood ", ["flood", "flood", "flood"])
    assert ok and message == "Saved schedule Triple flood (3 events)."
    ok, message = m.save_custom_schedule("TRIPLE FLOOD", ["flood", "storm", "flood"])
    assert ok and message.startswith("Updated") and len(m.meta["custom_schedules"]) == 1


def test_saved_schedules_persist_and_are_sanitised(game_env):
    m = game_env.module
    m.save_custom_schedule("Mine", ["flood", "storm", "heatwave"])
    assert json.loads(game_env.local_storage.getItem(m.META_STORAGE_KEY))["custom_schedules"][0]["name"] == "Mine"
    cleaned = m._sanitize_meta({"custom_schedules": [
        {"name": "ok", "events": ["flood", "storm", "storm"]},
        {"name": "short", "events": ["flood"]}, {"name": "bad", "events": ["flood", "storm", "tsunami"]},
        {"name": "long", "events": ["flood"] * 8}, {"name": "", "events": ["flood"] * 3},
    ]})
    assert cleaned["custom_schedules"] == [{"name": "ok", "events": ["flood", "storm", "storm"]}]


def test_the_library_buttons_feed_the_draft_and_the_ui_shows_it(game_env):
    m = game_env.module
    library = game_env.elements["builder-library"].children
    assert len(library) == len(m.EVENT_LABEL)
    library[0].dispatch("click", None)  # flood
    library[2].dispatch("click", None)  # storm
    library[0].dispatch("click", None)
    assert m.builder_draft == ["flood", "storm", "flood"]
    labels = [item.children[0].innerText for item in game_env.elements["builder-draft"].children]
    assert labels[0].endswith("Flood (40)") and len(labels) == 3
    assert game_env.elements["builder-save-button"].disabled is False
    assert "3 of 7 events" in game_env.elements["builder-summary"].innerText


def test_the_summary_states_the_knowledge_share(game_env):
    m = game_env.module
    m.builder_draft[:] = ["flood", "flood", "flood"]
    assert m.builder_knowledge_share() == pytest.approx(120 / 265)
    assert "45% of the usual knowledge" in m.builder_summary_text()
    m.builder_draft[:] = ["storm"] * 7
    assert m.builder_knowledge_share() == 1.0  # never more than the full amount


def test_running_a_saved_schedule_uses_the_events_and_the_players_tree(game_env):
    m = game_env.module
    m.skill_tree.unlocked.add("reinforced_infrastructure")
    m.save_custom_schedule("Triple flood", ["flood", "flood", "flood"])
    message = m.start_custom_run("Triple flood")
    assert "tagged as a custom schedule" in message
    assert game_env.run.schedule == ["flood", "flood", "flood"] and game_env.run.custom_name == "Triple flood"
    assert game_env.run.resilience_capacity == 2  # the tree applies
    assert not game_env.run.normalised


def test_running_a_schedule_is_refused_mid_run(game_env):
    m = game_env.module
    m.save_custom_schedule("T", ["flood", "flood", "flood"])
    game_env.resolve_event()
    assert "Finish your current run first" in m.start_custom_run("T")
    assert game_env.run.custom_events is None


def test_a_custom_run_is_tagged_scaled_and_kept_off_the_board(game_env, monkeypatch):
    m = game_env.module
    reported = []
    monkeypatch.setattr(m, "_report_hardest_schedule", lambda run_state: reported.append(run_state))
    m.save_custom_schedule("Triple flood", ["flood", "flood", "flood"])
    m.start_custom_run("Triple flood")
    _finish(game_env)
    entry = m.run_log_history[-1]
    assert entry["custom_schedule"] == "Triple flood"
    assert reported == []  # never on the hardest-schedule board
    info = game_env.run.knowledge_breakdown()
    assert info["schedule_factor"] == pytest.approx(120 / 265)
    assert info["base"] == max(1, round(max(1, round(game_env.run.run_score() / 20)) * 120 / 265))
    assert m.run_mode_label(entry) == "Custom schedule: Triple flood"
    assert "Custom schedule: 45%" in " ".join(m.knowledge_breakdown_lines(game_env.run))


def test_a_custom_run_that_equals_a_scenario_is_still_tagged(game_env):
    m = game_env.module
    m.save_custom_schedule("Coast", m.SCENARIOS["coastal"]["schedule"])
    m.start_custom_run("Coast")
    _finish(game_env)
    assert m.run_mode_label(m.run_log_history[-1]) == "Custom schedule: Coast"
    m.past_runs_filter = "custom"
    assert len(m.past_runs_view()) == 1
    m.past_runs_filter = "scenario:coastal"
    assert len(m.past_runs_view()) == 0


def test_built_in_runs_keep_the_full_knowledge(game_env):
    for scenario in ("classic", "coastal"):
        assert game_env.module.RunState(scenario=scenario).custom_knowledge_factor() == 1.0
    assert game_env.module.RunState(extended=True).custom_knowledge_factor() == 1.0


def test_a_custom_run_survives_a_save_round_trip(game_env):
    m = game_env.module
    m.save_custom_schedule("Triple flood", ["flood", "storm", "flood"])
    m.start_custom_run("Triple flood")
    game_env.resolve_event()
    state = json.loads(json.dumps(m.get_state()))
    assert state["custom_events"] == ["flood", "storm", "flood"] and state["custom_name"] == "Triple flood"
    m.run = m.RunState()
    m.load_state(state)
    assert game_env.run.schedule == ["flood", "storm", "flood"] and game_env.run.event_index == 1
    assert game_env.run.custom_name == "Triple flood"


def test_a_malformed_custom_save_falls_back_to_a_normal_run(game_env):
    m = game_env.module
    state = m.get_state()
    state["custom_events"] = ["flood", "not_an_event", "storm"]
    m.load_state(state)
    assert game_env.run.custom_events is None and game_env.run.schedule == m.EVENT_SCHEDULE


def test_the_schedule_code_button_shows_a_code_that_plays_that_schedule(game_env):
    m = game_env.module
    m.save_custom_schedule("Mine", ["storm", "flood", "civil_unrest"])
    m.render()
    saved = game_env.elements["builder-saved-list"].children[0]
    share = [b for b in saved.children if b.getAttribute("data-action") == "share"][0]

    class Event:
        target = share

    game_env.elements["builder-saved-list"].dispatch("click", Event())
    code = game_env.elements["builder-code"].value
    assert game_env.elements["builder-code"].hidden is False and code.startswith("RUN-AFTERMATH-")
    state, error = m.challenge_run_from_code(code)
    assert error == "" and state.schedule == ["storm", "flood", "civil_unrest"] and state.normalised


def test_load_edit_and_delete_from_the_saved_list(game_env):
    m = game_env.module
    m.save_custom_schedule("Mine", ["storm", "flood", "civil_unrest"])
    m.render()

    def press(action):
        saved = game_env.elements["builder-saved-list"].children[0]
        button = [b for b in saved.children if b.getAttribute("data-action") == action][0]

        class Event:
            target = button

        game_env.elements["builder-saved-list"].dispatch("click", Event())

    press("load")
    assert m.builder_draft == ["storm", "flood", "civil_unrest"]
    assert game_env.elements["builder-name-input"].value == "Mine"
    press("delete")
    assert m.meta["custom_schedules"] == []


# ---------------------------------------------------------------------------------------------- challenge + schedule safety
def test_challenge_runs_report_exact_expected_damage(game_env):
    m = game_env.module
    m.start_challenge(_friend_code(m, draw=11))
    damage, severity = m.expected_next_event_damage(game_env.run)
    game_env.resolve_event()
    assert game_env.run.event_log[0]["damage"] == pytest.approx(damage)
    assert game_env.run.event_log[0]["severity"] == pytest.approx(severity)
    low, high = m.expected_damage_range(m.RunState(normalised=True, draw=11))
    assert low == high


def test_skill_help_lines_say_skills_are_off_in_a_challenge(game_env):
    m = game_env.module
    m.start_challenge(_friend_code(m))
    assert m.skill_helps_text("early_warning") == "Skills are switched off in a challenge run."
