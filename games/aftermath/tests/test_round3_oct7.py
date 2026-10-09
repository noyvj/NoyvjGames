"""Round-3 batch (2026-10-07), planning/TODO.md "GE + E. Aftermath":
E-12 Disaster Codex, E-1 Lifetime Stats, E-15 x1/x5/Max steps, GE-18 undo, GE-15 Flawless Defense,
GE-13 prevented-damage popup, E-23 knowledge itemisation, E-24 copy run summary, E-27 tab title,
E-5 (partial) announcements, E-14 keys (ui.js), E-16 settings options."""

import re
import sys
import types
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _text(env, id_):
    return env.elements[id_].innerText


def _all_text(element):
    out = [element.innerText]
    for child in element.children:
        out.append(_all_text(child))
    return "\n".join(t for t in out if t)


def _finish(env):
    while not env.run.is_complete():
        env.resolve_event()


def _fortify(env, units=20):
    """Max mitigation (20 units = 100% raw, capped at 85%) without spending."""
    env.run.resilience_capacity = units


# ---- GE-15 Flawless Defense ---------------------------------------------
def test_flawless_threshold_is_fifteen_percent_of_base(game_env):
    m = game_env.module
    assert m.entry_is_flawless({"type": "flood", "damage": 6.0, "severity": 1.0})
    assert not m.entry_is_flawless({"type": "flood", "damage": 6.5, "severity": 1.0})
    assert not m.entry_is_flawless({"type": "nope", "damage": 0.0, "severity": 1.0})


def test_capped_mitigation_against_a_typical_event_is_flawless(game_env):
    _fortify(game_env)
    game_env.resolve_event()
    assert game_env.module.entry_is_flawless(game_env.run.event_log[0])
    assert game_env.module.achievement_progress["ever_flawless_defense"] is True
    assert "flawless_defense" in game_env.module.achievement_ids_earned()


def test_unfortified_run_has_no_flawless_event_and_no_bonus(game_env):
    game_env.resolve_event()
    assert not game_env.module.entry_is_flawless(game_env.run.event_log[0])
    assert game_env.module.achievement_progress["ever_flawless_defense"] is False
    assert game_env.run.knowledge_breakdown()["flawless_bonus"] == 0


def test_each_flawless_event_adds_one_knowledge_point(game_env):
    _fortify(game_env)
    game_env.run.resources = 400.0
    _finish(game_env)
    info = game_env.run.knowledge_breakdown()
    assert info["flawless"] >= 1
    assert info["total"] == info["base"] + info["flawless"]
    assert game_env.run.knowledge_points_earned() == info["total"]
    assert game_env.skill_tree.knowledge_points == info["total"]


def test_flawless_hint_names_the_limit_for_the_next_event(game_env):
    game_env.module.render()
    text = _text(game_env, "flawless-hint-display")
    assert "Flawless Defense" in text and "Flood" in text and "6 or less" in text
    assert "expected 40" in text
    _fortify(game_env)
    game_env.module.render()
    assert "on track" in _text(game_env, "flawless-hint-display")


def test_flawless_hint_clears_when_the_run_is_over(game_env):
    _finish(game_env)
    assert _text(game_env, "flawless-hint-display") == ""


# ---- E-23 knowledge itemisation -----------------------------------------
def test_breakdown_lines_explain_the_total(game_env):
    m = game_env.module
    game_env.run.resources = 100.0
    lines = m.knowledge_breakdown_lines(game_env.run)
    assert lines[0] == "Resources left 100 ÷ 20 = 5 knowledge"
    assert lines[-1] == "Total: 5 knowledge points"


def test_breakdown_mentions_the_minimum_when_it_applies(game_env):
    game_env.run.resources = 0.0
    lines = game_env.module.knowledge_breakdown_lines(game_env.run)
    assert any("Minimum of 1" in line for line in lines)
    assert lines[-1] == "Total: 1 knowledge point"


def test_summary_panel_lists_the_breakdown_and_the_preview_matches(game_env):
    _fortify(game_env)
    game_env.run.resources = 300.0
    _finish(game_env)
    panel = _all_text(game_env.elements["run-summary-panel"])
    assert "Knowledge earned this run" in panel
    assert "Flawless Defense x" in panel
    assert f"Total: {game_env.run.knowledge_points_earned()} knowledge" in panel


def test_live_preview_explains_where_the_points_come_from(game_env):
    game_env.run.resources = 100.0
    game_env.module.render()
    text = _text(game_env, "knowledge-preview-display")
    assert "5 knowledge points (5 from 100 resources)" in text


# ---- E-15 steps -----------------------------------------------------------
def test_default_step_keeps_the_original_labels(game_env):
    game_env.module.render()
    assert _text(game_env, "resilience-invest-button") == "Invest in Resilience (25)"
    assert _text(game_env, "growth-invest-button").startswith("Invest in Growth (20)")


def test_x5_buys_five_units_in_one_click(game_env):
    game_env.elements["step-x5-button"].dispatch("click", None)
    assert _text(game_env, "resilience-invest-button") == "Invest in Resilience x5 (125)"
    game_env.invest_resilience()
    assert game_env.run.resilience_capacity == 5
    assert game_env.run.resources == 200 - 125
    assert game_env.run.undo_count() == 1


def test_x5_stops_at_what_you_can_afford(game_env):
    game_env.elements["step-x5-button"].dispatch("click", None)
    game_env.run.resources = 60.0
    game_env.invest_growth()
    assert game_env.run.growth_capacity == 3  # 60 // 20
    assert game_env.run.resources == 0


def test_max_resilience_stops_at_the_eighty_five_percent_cap(game_env):
    game_env.elements["step-max-button"].dispatch("click", None)
    game_env.run.resources = 1000.0
    game_env.invest_resilience()
    assert game_env.run.resilience_capacity == 17  # 17 * 5% = 85%
    assert game_env.run.mitigation_fraction() == game_env.module.MAX_MITIGATION
    assert game_env.elements["resilience-invest-button"].disabled is True  # nothing more to buy
    assert game_env.elements["growth-invest-button"].disabled is False


def test_max_growth_spends_everything_affordable(game_env):
    game_env.elements["step-max-button"].dispatch("click", None)
    game_env.invest_growth()
    assert game_env.run.growth_capacity == 10  # 200 // 20
    assert game_env.run.resources == 0


def test_growth_label_shows_units_and_total_cost(game_env):
    game_env.elements["step-x5-button"].dispatch("click", None)
    text = _text(game_env, "growth-invest-button")
    assert text.startswith("Invest in Growth x5 (100)") and "+0 → +40" in text


def test_step_choice_is_pressed_state_and_persists(game_env):
    game_env.elements["step-x5-button"].dispatch("click", None)
    assert game_env.elements["step-x5-button"].getAttribute("aria-pressed") == "true"
    assert game_env.elements["step-x1-button"].getAttribute("aria-pressed") == "false"
    assert game_env.local_storage.getItem("aftermath-invest-step") == "5"
    game_env.elements["step-max-button"].dispatch("click", None)
    assert game_env.local_storage.getItem("aftermath-invest-step") == "max"


def test_stored_step_is_read_back_and_bad_values_fall_back(game_env):
    m = game_env.module
    game_env.local_storage.setItem("aftermath-invest-step", "max")
    assert m.load_invest_step() == "max"
    game_env.local_storage.setItem("aftermath-invest-step", "7")
    assert m.load_invest_step() == 1
    assert m.set_invest_step(7) is False


def test_bulk_buy_still_counts_for_achievements(game_env):
    game_env.elements["step-x5-button"].dispatch("click", None)
    game_env.invest_resilience()
    assert game_env.module.achievement_progress["ever_invested_resilience"] is True


# ---- GE-18 undo -----------------------------------------------------------
def test_undo_gives_back_the_last_click_only(game_env):
    game_env.invest_resilience()
    game_env.invest_growth()
    assert _text(game_env, "undo-allocation-button") == "↶ Undo (2)"
    game_env.elements["undo-allocation-button"].dispatch("click", None)
    assert game_env.run.growth_capacity == 0 and game_env.run.resilience_capacity == 1
    assert game_env.run.resources == 200 - 25
    assert _text(game_env, "undo-allocation-button") == "↶ Undo (1)"


def test_undo_reverses_a_whole_bulk_click(game_env):
    game_env.elements["step-x5-button"].dispatch("click", None)
    game_env.invest_resilience()
    game_env.elements["undo-allocation-button"].dispatch("click", None)
    assert game_env.run.resilience_capacity == 0 and game_env.run.resources == 200


def test_undo_is_disabled_with_nothing_to_undo_and_after_resolve(game_env):
    assert game_env.elements["undo-allocation-button"].disabled is True
    game_env.invest_resilience()
    assert game_env.elements["undo-allocation-button"].disabled is False
    game_env.resolve_event()
    assert game_env.elements["undo-allocation-button"].disabled is True
    assert game_env.run.undo_last_allocation() is False


def test_undo_does_not_survive_a_load(game_env):
    game_env.invest_resilience()
    snapshot = game_env.module.get_state()
    game_env.module.load_state(snapshot)
    assert game_env.run.undo_count() == 0
    assert game_env.elements["undo-allocation-button"].disabled is True
    assert game_env.run.resilience_capacity == 1  # the investment itself was saved


def test_undo_never_runs_on_a_finished_run(game_env):
    game_env.invest_resilience()
    _finish(game_env)
    assert game_env.run.undo_last_allocation() is False


# ---- GE-13 popup + E-5 announcer -----------------------------------------
def test_popup_hidden_before_any_event(game_env):
    assert game_env.elements["damage-prevented-popup"].hidden is True


def test_popup_states_damage_prevented_and_marks_the_event(game_env):
    for _ in range(4):
        game_env.invest_resilience()  # 20% mitigation
    game_env.resolve_event()
    entry = game_env.run.event_log[0]
    prevented = round(game_env.module.entry_prevented(entry))
    popup = game_env.elements["damage-prevented-popup"]
    assert popup.hidden is False
    assert popup.innerText == f"-{prevented} damage prevented!"
    assert popup.dataset.prevented == str(prevented)
    assert popup.dataset.eventKey == "1-1"


def test_popup_is_gentle_when_nothing_was_prevented(game_env):
    game_env.resolve_event()
    assert "No damage prevented" in _text(game_env, "damage-prevented-popup")


def test_streak_appears_after_two_held_events(game_env):
    _fortify(game_env)
    game_env.resolve_event()
    assert game_env.elements["damage-streak-display"].innerText.count("Held") == 0
    game_env.resolve_event()
    assert "Held 2 events in a row" in _text(game_env, "damage-streak-display")


def test_streak_resets_on_a_bad_event(game_env):
    m = game_env.module
    log = [
        {"type": "flood", "damage": 5.0, "severity": 1.0},
        {"type": "flood", "damage": 40.0, "severity": 1.0},
        {"type": "flood", "damage": 5.0, "severity": 1.0},
    ]
    assert m.held_streak(log) == 1
    assert m.held_streak(log[:1]) == 1
    assert m.held_streak([]) == 0


def test_popup_clears_on_a_new_run(game_env):
    _finish(game_env)
    game_env.start_new_run()
    assert game_env.elements["damage-prevented-popup"].hidden is True


def test_announcer_reads_out_each_resolution_and_investment(game_env):
    game_env.invest_resilience()
    assert "Invested in resilience x1" in _text(game_env, "event-announcer")
    game_env.resolve_event()
    text = _text(game_env, "event-announcer")
    assert text.startswith("Flood hit, ") and "damage" in text and "prevented" in text


def test_announcer_mentions_flawless_defense(game_env):
    _fortify(game_env)
    game_env.resolve_event()
    assert "Flawless Defense" in _text(game_env, "event-announcer")


# ---- E-12 Disaster Codex -------------------------------------------------
def test_codex_starts_empty_and_locked(game_env):
    m = game_env.module
    assert m.codex_completion() == (0, 7)
    rows = m.codex_entries()
    assert [r["type"] for r in rows] == list(m.EVENT_LABEL)
    assert all(r["faced"] == 0 and r["example"] is None for r in rows)
    assert "0/7" in _text(game_env, "codex-toggle-button")


def test_facing_an_event_fills_its_page_even_mid_run(game_env):
    m = game_env.module
    game_env.resolve_event()  # a flood
    row = next(r for r in m.codex_entries() if r["type"] == "flood")
    assert row["faced"] == 1 and row["avg_damage"] == row["worst_damage"] == row["lowest_damage"]
    assert row["example"]["title"] == m.REAL_WORLD_EXAMPLES["flood"]["title"]
    assert m.codex_completion() == (1, 7)


def test_a_finished_run_is_counted_once(game_env):
    m = game_env.module
    _finish(game_env)
    floods = next(r for r in m.codex_entries() if r["type"] == "flood")
    assert floods["faced"] == 2  # the classic schedule has two floods
    assert m.codex_completion() == (6, 7)  # the Classic mix holds six of the seven kinds


def test_codex_panel_shows_stats_note_and_source_once_unlocked(game_env):
    m = game_env.module
    _finish(game_env)
    game_env.toggle_codex = lambda: game_env.elements["codex-toggle-button"].dispatch("click", None)
    game_env.toggle_codex()
    panel = game_env.elements["codex-panel"]
    assert panel.hidden is False
    text = _all_text(panel)
    assert "Disaster Codex" in text and "Faced x2" in text
    assert m.REAL_WORLD_EXAMPLES["flood"]["title"] in text
    assert "Source:" in text and m.REAL_WORLD_READ_DATE in text
    assert "Hide Disaster Codex" == _text(game_env, "codex-toggle-button")
    game_env.toggle_codex()
    assert panel.hidden is True


def test_locked_pages_say_how_to_unlock(game_env):
    game_env.elements["codex-toggle-button"].dispatch("click", None)
    text = _all_text(game_env.elements["codex-panel"])
    assert "Not faced yet. Weather a Flood" in text
    assert "0 of 7 kinds of shock recorded" in text


def test_codex_completion_achievement(game_env):
    m = game_env.module
    assert "codex_complete" not in m.achievement_ids_earned()
    m.legacy_events.update(m.EVENT_LABEL)
    assert "codex_complete" in m.achievement_ids_earned()
    entry = next(a for a in m.achievements_summary() if a["id"] == "codex_complete")
    assert entry["progress"] == (6, 6)


def test_codex_handles_old_runs_without_a_log(game_env):
    m = game_env.module
    m.legacy_event_counts["flood"] = 3
    m.legacy_events.add("flood")
    row = next(r for r in m.codex_entries() if r["type"] == "flood")
    assert row["faced"] == 3 and row["avg_damage"] is None
    assert "since the run log began" in m.codex_stats_text(row)


# ---- E-1 Lifetime Stats --------------------------------------------------
def test_stats_panel_prompts_before_any_run(game_env):
    game_env.elements["stats-toggle-button"].dispatch("click", None)
    assert "No completed runs" in _all_text(game_env.elements["stats-panel"])


def test_lifetime_stats_aggregate_damage_by_category(game_env):
    m = game_env.module
    _finish(game_env)
    stats = m.lifetime_stats()
    assert stats["runs"] == 1
    total = sum(e["damage"] for e in game_env.run.event_log)
    assert abs(sum(stats["category_damage"].values()) - total) < 1e-6
    assert stats["category_damage"]["social"] > 0


def test_matchups_rank_by_average_mitigation(game_env):
    m = game_env.module
    m.run_log_history.append({
        "run_number": 9, "score": 50.0, "knowledge_earned": 3, "skill_strength": 2,
        "event_log": [
            {"type": "flood", "damage": 4.0, "severity": 1.0},
            {"type": "heatwave", "damage": 35.0, "severity": 1.0},
        ],
    })
    stats = m.lifetime_stats()
    assert stats["matchups"][0]["type"] == "flood"
    assert stats["matchups"][-1]["type"] == "heatwave"
    game_env.elements["stats-toggle-button"].dispatch("click", None)
    text = _all_text(game_env.elements["stats-panel"])
    assert "Best matchup: Flood" in text and "Worst matchup: Heatwave" in text


def test_knowledge_over_time_is_cumulative(game_env):
    m = game_env.module
    for number, earned in ((1, 3), (2, 5)):
        m.run_log_history.append({"run_number": number, "score": 1.0, "knowledge_earned": earned, "event_log": []})
    rows = m.lifetime_stats()["kp_rows"]
    assert [r["total"] for r in rows] == [3, 8]


def test_score_bands_use_only_logs_that_record_skill_strength(game_env):
    m = game_env.module
    m.run_log_history.extend([
        {"run_number": 1, "score": 100.0, "knowledge_earned": 1, "event_log": []},
        {"run_number": 2, "score": 60.0, "knowledge_earned": 1, "skill_strength": 0, "event_log": []},
        {"run_number": 3, "score": 120.0, "knowledge_earned": 1, "skill_strength": 5, "event_log": []},
    ])
    bands = {b["label"]: b for b in m.lifetime_stats()["bands"]}
    assert bands["0-1 skills"]["avg_score"] == 60.0 and bands["0-1 skills"]["runs"] == 1
    assert bands["4+ skills"]["avg_score"] == 120.0
    assert bands["2-3 skills"]["avg_score"] is None


def test_new_run_logs_record_skill_strength(game_env):
    _finish(game_env)
    assert game_env.module.run_log_history[-1]["skill_strength"] == 0


def test_stats_panel_writes_numbers_beside_every_bar(game_env):
    _finish(game_env)
    game_env.elements["stats-toggle-button"].dispatch("click", None)
    text = _all_text(game_env.elements["stats-panel"])
    for needle in ("Damage taken by category", "Average mitigation by event type", "Knowledge points over time",
                   "Average score by skill strength", "% prevented", "Run 1", "Flawless Defenses so far"):
        assert needle in text, needle


def test_stats_tolerate_malformed_log_entries(game_env):
    m = game_env.module
    m.run_log_history.extend(["junk", {"event_log": [{"type": "alien", "damage": 5}, "x"]}, {}])
    assert m.lifetime_stats()["runs"] == 2
    game_env.elements["stats-toggle-button"].dispatch("click", None)  # renders without raising


# ---- E-24 copy run summary -----------------------------------------------
def test_copy_button_appears_once_an_event_is_faced(game_env):
    assert game_env.elements["run-summary-actions"].hidden is True
    game_env.resolve_event()
    assert game_env.elements["run-summary-actions"].hidden is False


def test_summary_text_has_name_run_score_and_events(game_env):
    m = game_env.module
    m.set_settlement_name("New Haven")
    _finish(game_env)
    text = m.run_summary_text()
    lines = text.split("\n")
    assert lines[0].startswith("Aftermath: New Haven, run 1 (Classic mix)")
    assert f"Score: {game_env.run.run_score():.0f}" in lines[1]
    assert sum(1 for line in lines if re.match(r"^\d+\. ", line)) == len(game_env.run.schedule)


def test_in_progress_summary_is_labelled(game_env):
    game_env.resolve_event()
    assert "in progress" in game_env.module.run_summary_text().split("\n")[0]


def test_copy_falls_back_to_a_text_box_without_a_clipboard(game_env):
    game_env.elements["copy-run-summary-button"].dispatch("click", None)
    area = game_env.elements["copy-run-summary-area"]
    assert area.hidden is False and area.value.startswith("Aftermath:")
    assert "Select the text" in _text(game_env, "copy-run-summary-status")


def test_copy_uses_the_clipboard_when_there_is_one(game_env):
    written = []
    clipboard = types.SimpleNamespace(writeText=lambda text: written.append(text))
    sys.modules["js"].navigator = types.SimpleNamespace(clipboard=clipboard)
    game_env.elements["copy-run-summary-button"].dispatch("click", None)
    assert written and written[0].startswith("Aftermath:")
    assert game_env.elements["copy-run-summary-area"].hidden is True
    assert "Copied" in _text(game_env, "copy-run-summary-status")


# ---- E-27 tab title ------------------------------------------------------
def test_tab_title_tracks_the_run(game_env):
    m = game_env.module
    assert m.tab_title() == "Aftermath - Run 1, event 1 of 7 (Flood next)"
    assert sys.modules["js"].document.title == m.tab_title()
    game_env.resolve_event()
    assert sys.modules["js"].document.title == "Aftermath - Run 1, event 2 of 7 (Heatwave next)"


def test_tab_title_when_complete(game_env):
    _finish(game_env)
    assert sys.modules["js"].document.title.startswith("Aftermath - Run 1 complete, score ")


# ---- pages, settings, keys ----------------------------------------------
def _html(name):
    return (GAME_DIR / name).read_text(encoding="utf-8")


def test_new_controls_exist_in_both_pages():
    for page in ("index.html", "pc.html"):
        html = _html(page)
        for id_ in ("step-x1-button", "step-x5-button", "step-max-button", "undo-allocation-button",
                    "codex-toggle-button", "codex-panel", "stats-toggle-button", "stats-panel",
                    "damage-prevented-popup", "event-announcer", "copy-run-summary-button",
                    "high-contrast-checkbox", "readable-font-checkbox", "flawless-hint-display"):
            assert f'id="{id_}"' in html, (page, id_)


def test_codex_and_stats_are_desktop_windows_and_menu_entries():
    import json
    cfg = json.loads(_html("pc-config.json"))
    windows = {w[1]: w[0] for w in cfg["windows"]}
    assert windows["codex-toggle-button"] == "codex-panel" and windows["stats-toggle-button"] == "stats-panel"
    menu_ids = [i for g in cfg["toolbar"]["menu"] for i in g["ids"]]
    assert "codex-toggle-button" in menu_ids and "stats-toggle-button" in menu_ids


def test_every_id_ui_js_presses_exists():
    js = _html("ui.js")
    html = _html("index.html")
    for id_ in re.findall(r'"([a-z-]+-(?:button))"', js):
        assert f'id="{id_}"' in html, id_


def test_ui_js_is_loaded_and_keys_are_listed_in_the_help():
    html = _html("index.html")
    assert '<script src="ui.js" defer></script>' in html
    for line in ("1 / 2", "Enter", "U —", "T —", "H —", "C —", "S —"):
        assert line in html


def test_settings_js_handles_contrast_and_font_including_reset():
    js = _html("settings.js")
    assert "aftermath-high-contrast" in js and "aftermath-readable-font" in js
    assert js.count("data-high-contrast") >= 2 and js.count("data-readable-font") >= 2
    reset = js[js.index("settingsResetButton.addEventListener"):]
    assert "applyFlag(\"data-high-contrast\", CONTRAST_KEY, false)" in reset
    assert "applyFlag(\"data-readable-font\", FONT_KEY, false)" in reset


def test_stylesheet_has_the_contrast_and_font_rules_in_both_themes():
    css = _html("style.css")
    assert 'html[data-high-contrast="true"] #game' in css
    assert 'html[data-high-contrast="true"][data-theme="light"] #game' in css
    assert 'html[data-readable-font="true"] body' in css


def test_level_matchups_do_not_name_a_best_and_worst(game_env):
    _finish(game_env)  # one run at one mitigation level: every type prevents the same share
    game_env.elements["stats-toggle-button"].dispatch("click", None)
    text = _all_text(game_env.elements["stats-panel"])
    assert "Every matchup is level" in text and "Best matchup" not in text


def test_category_rows_use_a_proper_label(game_env):
    _finish(game_env)
    game_env.elements["stats-toggle-button"].dispatch("click", None)
    assert "Non-weather" in _all_text(game_env.elements["stats-panel"])
