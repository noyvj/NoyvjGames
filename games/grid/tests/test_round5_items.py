"""Round-5 pass: run history (C-1), perk gaps (C-2), lifetime stats (C-7),
round recap (C-8), difficulty presets (C-10), career backup/reset (C-16),
auto-advance (GC-17) and personal records (GC-26)."""
import json

from .test_career import _install_storage, _play


def _sure(g):
    return dict(rng=lambda: 1.0, age_rng=lambda: 1.0, weather_rng=lambda: 0.5)


# --- C-1 run history --------------------------------------------------------

def test_state_records_funds_and_demand_each_round(game_env):
    _play(game_env, 3)
    s = game_env.state
    assert len(s.funds_history) == 3 and len(s.demand_history) == 3
    assert s.demand_history[-1] == s.demand


def test_finish_run_files_a_history_record(game_env):
    g = game_env.module
    _install_storage()
    game_env.state.plant_counts["solar"] = 5
    _play(game_env, 6)
    g.finish_run()
    assert len(g.career["history"]) == 1
    rec = g.career["history"][0]
    assert rec["rounds"] == 6 and rec["scenario"] == "standard"
    assert len(rec["clean"]) == 6 and len(rec["funds_series"]) == 6 and len(rec["demand_series"]) == 6
    assert rec["built"]["solar"] == 0  # set directly, never built
    assert game_env.state.funds_history == []  # fresh run starts a fresh series


def test_series_are_thinned_and_history_capped(game_env):
    g = game_env.module
    _install_storage()
    assert len(g._thin(list(range(100)))) == g.CAREER_SERIES_POINTS
    assert g._thin(list(range(100)))[0] == 0 and g._thin(list(range(100)))[-1] == 99
    for _ in range(g.CAREER_HISTORY_MAX + 3):
        _play(game_env, 5)
        g.finish_run()
    assert len(g.career["history"]) == g.CAREER_HISTORY_MAX
    assert g.career["runs"] == g.CAREER_HISTORY_MAX + 3


def test_validate_career_drops_bad_history_and_defaults_old_careers(game_env):
    g = game_env.module
    old = g.validate_career({"runs": 2, "points": 5})  # pre-history career
    assert old["history"] == [] and old["best_streak"] == 0 and old["best_rounds_to_90"] is None
    bad = g.validate_career({"history": ["x", {"scenario": "nope", "grade": "A"}, {"scenario": "standard", "grade": "Z"}]})
    assert bad["history"] == []
    junk = g.validate_career({"history": [{"scenario": "standard", "grade": "B", "clean": [1, "a"], "rounds": float("nan")}]})
    assert junk["history"][0]["clean"] == [] and junk["history"][0]["rounds"] == 0


def test_career_panel_lists_runs_and_draws_stacked_charts(game_env):
    g = game_env.module
    _install_storage()
    game_env.state.plant_counts["solar"] = 5
    _play(game_env, 6)
    g.finish_run()
    game_env.state.plant_counts["wind"] = 3
    _play(game_env, 7)
    g.finish_run()
    game_env.toggle_career()
    chart = game_env.elements["career-history-chart"].innerHTML
    assert chart.count("<svg") >= 3 + 2  # three charts plus two legend swatches
    assert "run-line--0" in chart and "run-line--1" in chart and "Run 2" in chart
    rows = game_env.elements["career-history-list"].children
    assert len(rows) == 2 and rows[0].innerText.startswith("Run 2")  # newest first


# --- C-2 perk gaps ----------------------------------------------------------

def test_locked_perks_show_effect_and_points_gap(game_env):
    g = game_env.module
    g.career["points"] = 1
    game_env.toggle_career()
    text = g.career_perk_progress_text("seed_capital")
    assert "+75 funds" in text and "2 more point(s) needed" in text
    # The cheapest upgrade with its prerequisites met is the next one named (Old Coal Contract, 2 points).
    assert "Next perk: Old Coal Contract" in game_env.elements["career-next-perk-display"].innerText
    assert "1 point(s) away" in game_env.elements["career-next-perk-display"].innerText
    g.career["points"] = 3
    g.render()
    assert "ready to unlock" in g.career_perk_progress_text("seed_capital")
    g.unlock_career_perk("seed_capital")
    g.render()
    assert g.career_perk_progress_text("seed_capital").startswith("Unlocked: Seed capital")


# --- C-7 lifetime stats -----------------------------------------------------

def test_lifetime_statistics_accumulate_beyond_the_history_cap(game_env):
    g = game_env.module
    _install_storage()
    assert "No finished runs" in g.career_lifetime_lines()[0]
    for _ in range(g.CAREER_HISTORY_MAX + 2):
        game_env.state.cumulative_built["wind"] = 2
        _play(game_env, 5)
        g.finish_run()
    life = g.career["lifetime"]
    assert life["rounds"] == 5 * (g.CAREER_HISTORY_MAX + 2)
    assert life["built"]["wind"] == 2 * (g.CAREER_HISTORY_MAX + 2)
    lines = "\n".join(g.career_lifetime_lines())
    assert "Most-built plant: Wind" in lines and "Standard start" in lines
    assert "brownout" in lines


def test_grade_average_letter_and_heatmap(game_env):
    g = game_env.module
    assert g._grade_from_average(4) == "A" and g._grade_from_average(0.2) == "F" and g._grade_from_average(2.6) == "B"
    _install_storage()
    game_env.state.plant_counts["solar"] = 5
    _play(game_env, 5)
    g.finish_run()
    html = g.career_heatmap_html(g.career["history"])
    assert html.count('class="heat-cell"') == 5 and "% clean" in html
    game_env.toggle_career()
    assert "heat-row" in game_env.elements["career-heatmap"].innerHTML


# --- GC-26 records ----------------------------------------------------------

def test_first_run_sets_records_without_a_flash(game_env):
    g = game_env.module
    _install_storage()
    game_env.state.plant_counts["nuclear"] = 4
    _play(game_env, 6)
    assert game_env.state.first_90_clean_round == 1
    g.finish_run()
    assert g.career["best_rounds_to_90"] == 1 and g.career["best_streak"] == 6
    assert g.last_finish_records == []


def test_beating_a_record_flashes_new_record(game_env):
    g = game_env.module
    _install_storage()
    g.career.update(runs=1, best_streak=2, best_rounds_to_90=9, best_score=10.0, best_grade="C")
    game_env.state.plant_counts["nuclear"] = 4
    _play(game_env, 6)
    g.finish_run()
    assert g.career["best_streak"] == 6 and g.career["best_rounds_to_90"] == 1
    assert any("streak" in r for r in g.last_finish_records)
    assert any("90% clean" in r for r in g.last_finish_records)
    game_env.toggle_career()
    flash = game_env.elements["career-record-flash"]
    assert flash.hidden is False and flash.innerText.startswith("New record!")
    game_env.advance_round()  # next round clears the flash
    assert game_env.elements["career-record-flash"].hidden is True


def test_a_worse_run_breaks_no_record(game_env):
    g = game_env.module
    _install_storage()
    g.career.update(runs=1, best_streak=50, best_rounds_to_90=1, best_score=100.0, best_grade="A")
    _play(game_env, 5)
    g.finish_run()
    assert g.last_finish_records == [] and g.career["best_streak"] == 50


def test_never_reaching_90_percent_leaves_the_record_unset(game_env):
    g = game_env.module
    _install_storage()
    game_env.state.plant_counts["coal"] = 3
    _play(game_env, 5)
    assert game_env.state.first_90_clean_round is None
    g.finish_run()
    assert g.career["best_rounds_to_90"] is None
    assert "not reached yet" in g.career_records_text()


# --- C-16 export / import / reset ------------------------------------------

def test_export_fills_the_box_with_career_json(game_env):
    g = game_env.module
    g.career["points"] = 4
    game_env.elements["career-export-button"].dispatch("click", None)
    data = json.loads(game_env.elements["career-data-field"].value)
    assert data["points"] == 4
    assert "box" in g.career_data_message


def test_import_rejects_garbage_and_accepts_a_career(game_env):
    g = game_env.module
    _install_storage()
    assert g.import_career_from_text("not json") is False
    assert g.import_career_from_text("[1, 2]") is False
    assert g.import_career_from_text('{"hello": 1}') is False
    assert g.career["points"] == 0
    assert g.import_career_from_text(json.dumps({"runs": 3, "points": 9, "unlocked": ["seed_capital"]})) is True
    assert g.career["points"] == 9 and game_env.state.perks == {"seed_capital"}
    # an import can never grant perks the points could not pay for
    g.import_career_from_text(json.dumps({"runs": 1, "points": 1, "unlocked": ["demand_analytics"]}))
    assert g.career["unlocked"] == []


def test_reset_asks_first_after_putting_a_backup_in_the_box(game_env):
    from .test_confirm_dialog import _install_fake_confirm_dialog

    g = game_env.module
    storage = _install_storage()
    g.career.update(runs=2, points=7, unlocked=["seed_capital"])
    window = _install_fake_confirm_dialog()
    game_env.elements["career-reset-button"].dispatch("click", None)
    assert json.loads(game_env.elements["career-data-field"].value)["points"] == 7
    assert g.career["points"] == 7  # not reset yet
    call = window.ConfirmDialog.calls[0]
    assert call["id"] == "grid-reset-career" and call["allowSkip"] is False
    window.ConfirmDialog.confirm()
    assert g.career["points"] == 0 and g.career["unlocked"] == [] and game_env.state.perks == set()
    assert json.loads(storage.data[g.CAREER_STORAGE_KEY])["points"] == 0
    # the backup in the box can bring it back
    g.import_career_from_text(game_env.elements["career-data-field"].value)
    assert g.career["points"] == 7


def test_import_goes_through_a_confirm_dialog_without_skip(game_env):
    from .test_confirm_dialog import _install_fake_confirm_dialog

    g = game_env.module
    _install_storage()
    window = _install_fake_confirm_dialog()
    game_env.elements["career-data-field"].value = json.dumps({"runs": 1, "points": 2})
    game_env.elements["career-import-button"].dispatch("click", None)
    assert window.ConfirmDialog.calls[0]["allowSkip"] is False and g.career["points"] == 0
    window.ConfirmDialog.confirm()
    assert g.career["points"] == 2


# --- GC-17 auto-advance -----------------------------------------------------

def test_auto_advance_plays_five_quiet_rounds(game_env):
    g = game_env.module
    game_env.state.plant_counts["nuclear"] = 2
    played, message = g.auto_advance(**_sure(g))
    assert played == 5 and game_env.state.round_number == 6
    assert "all 5 rounds" in message


def test_auto_advance_stops_at_the_first_disruption(game_env):
    g = game_env.module
    game_env.state.plant_counts["coal"] = 3
    game_env.state.emissions = 5000  # certain disruption
    played, message = g.auto_advance(rng=lambda: 0.0, age_rng=lambda: 1.0, weather_rng=lambda: 0.5)
    assert played == 1 and "disruption" in message


def test_auto_advance_stops_at_an_aging_breakdown(game_env):
    g = game_env.module
    game_env.state.plant_counts["gas"] = 2
    game_env.state.plant_age["gas"] = 30
    played, message = g.auto_advance(rng=lambda: 1.0, age_rng=lambda: 0.0, weather_rng=lambda: 0.5)
    assert played == 1 and "aging breakdown" in message


def test_auto_advance_stops_when_a_policy_lever_is_offered(game_env):
    g = game_env.module
    game_env.state.round_number = g.POLICY_LEVER_INTERVAL - 2
    played, message = g.auto_advance(**_sure(g))
    assert game_env.state.policy_lever_available is True
    assert played == 3 and "policy lever" in message
    # an open offer must be answered first
    assert g.auto_advance(**_sure(g))[0] == 0


def test_auto_advance_button_wiring(game_env):
    g = game_env.module
    game_env.state.plant_counts["nuclear"] = 2
    button = game_env.elements["auto-advance-button"]
    assert button.disabled is False and "5 rounds" in button.innerText
    game_env.state.emissions = 0
    game_env.auto_advance()
    assert game_env.state.round_number > 1
    status = game_env.elements["auto-advance-status"]
    assert status.hidden is False and "Auto-advanced" in status.innerText
    game_env.advance_round()
    assert game_env.elements["auto-advance-status"].hidden is True
    game_env.state.policy_lever_available = True
    g.render()
    assert game_env.elements["auto-advance-button"].disabled is True


# --- C-8 round recap --------------------------------------------------------

def test_recap_before_any_round(game_env):
    summary, details = game_env.module.round_recap_text()
    assert "no round played" in summary


def test_recap_collates_the_round(game_env):
    g = game_env.module
    s = game_env.state
    s.plant_counts["coal"] = 2
    s.plant_counts["solar"] = 2
    s.weather_variability_enabled = True
    s.set_maintenance_schedule("coal", 3)
    s.round_number = 3  # schedule fires this round
    funds = s.funds
    s.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0, weather_rng=lambda: 1.0)
    r = s.last_round_recap
    assert r["round"] == 3 and abs(r["net"] - (s.funds - funds)) < 1e-6
    assert r["scheduled"] and r["scheduled"][0]["plant"] == "coal"
    assert r["weather_pct"] is not None and r["weather_pct"] > 0
    g.render()
    summary = game_env.elements["round-recap-summary"].innerText
    body = game_env.elements["round-recap-body"].innerText
    assert summary.startswith("Round 3 recap: net ")
    assert "Scheduled maintenance: Coal" in body and "above nameplate" in body and "Demand grew by" in body


def test_recap_names_disruption_and_aging(game_env):
    s = game_env.state
    s.plant_counts["coal"] = 3
    s.emissions = 5000
    s.plant_age["coal"] = 30
    s.advance_round(rng=lambda: 0.0, age_rng=lambda: 0.0)
    game_env.module.render()
    body = game_env.elements["round-recap-body"].innerText
    assert "Disruption:" in body and "Aging breakdown: Coal" in body


def test_recap_survives_a_save_round_trip_and_bad_data(game_env):
    g = game_env.module
    _play(game_env, 2)
    data = json.loads(json.dumps(g.get_state()))
    assert data["last_round_recap"]["round"] == 2 and len(data["funds_history"]) == 2
    g.load_state(data)
    assert game_env.state.last_round_recap["round"] == 2
    data["last_round_recap"] = {"round": "x", "net": "y", "scheduled": [{"plant": "zzz"}], "weather_pct": float("nan")}
    data["funds_history"] = ["a"]
    data["first_90_clean_round"] = True
    g.load_state(data)
    assert game_env.state.funds_history == [] and game_env.state.first_90_clean_round is None
    assert game_env.state.last_round_recap["scheduled"] == []
    data["last_round_recap"] = "garbage"
    g.load_state(data)
    assert game_env.state.last_round_recap is None
    assert "no round played" in game_env.elements["round-recap-summary"].innerText


def test_old_save_without_new_fields_still_loads(game_env):
    g = game_env.module
    data = json.loads(json.dumps(g.get_state()))
    for key in ("funds_history", "demand_history", "aging_breakdown_count", "first_90_clean_round", "last_round_recap"):
        data.pop(key)
    data["career"].pop("history")
    assert g.load_state(data) is True


# --- C-10 difficulty presets ------------------------------------------------

def test_default_reads_standard(game_env):
    assert game_env.module.difficulty_preset_key() == "standard"
    assert game_env.elements["difficulty-header-display"].innerText == "Difficulty: Standard"


def test_operator_preset_sets_the_toggles(game_env):
    game_env.choose_difficulty_preset("operator")
    s = game_env.state
    assert s.steeper_demand_growth_enabled and s.weather_variability_enabled
    assert game_env.elements["difficulty-header-display"].innerText == "Difficulty: Operator"
    assert game_env.elements["difficulty-preset-select"].value == "operator"


def test_relaxed_preset_picks_the_greenfield_start(game_env):
    game_env.choose_difficulty_preset("operator")
    game_env.choose_difficulty_preset("relaxed")
    s = game_env.state
    assert s.scenario == "greenfield" and s.funds == 700
    assert not s.steeper_demand_growth_enabled and not s.weather_variability_enabled
    assert game_env.elements["difficulty-header-display"].innerText == "Difficulty: Relaxed"


def test_preset_after_the_scenario_locks_only_changes_the_toggles(game_env):
    game_env.build("coal")
    game_env.choose_difficulty_preset("relaxed")
    s = game_env.state
    assert s.scenario == "standard"
    assert "locked" in game_env.elements["difficulty-preset-note"].innerText
    assert game_env.elements["difficulty-header-display"].innerText == "Difficulty: Standard"
    game_env.choose_difficulty_preset("operator")
    assert game_env.elements["difficulty-preset-note"].innerText == ""


def test_mixed_controls_read_custom_and_custom_choice_is_ignored(game_env):
    game_env.toggle_steeper_demand()
    assert game_env.elements["difficulty-header-display"].innerText == "Difficulty: Custom"
    assert game_env.elements["difficulty-preset-select"].value == "custom"
    game_env.choose_difficulty_preset("custom")
    assert game_env.state.steeper_demand_growth_enabled is True
    game_env.choose_difficulty_preset("bogus")


def test_preset_survives_save_load_because_it_is_derived(game_env):
    g = game_env.module
    game_env.choose_difficulty_preset("operator")
    data = json.loads(json.dumps(g.get_state()))
    game_env.choose_difficulty_preset("standard")
    g.load_state(data)
    assert g.difficulty_preset_key() == "operator"
