"""GB batch 2 display and accessibility items: season forecast (B-12), plot card (B-16), request pace
(B-6), announcer and C/R hotkeys (B-7), high-contrast plots (B-8), soil overlay (B-10), number formats (B-26)."""

import json

import pytest

from .gb_helpers import advance_to, make_mature, tile, tile_marks


# --- B-12: season forecast ----------------------------------------------------------------------------------------

def test_forecast_names_the_next_two_seasons_with_multipliers_and_countdowns(game_env):
    m = game_env.module
    advance_to(game_env, 28)  # spring, 12 ticks to summer
    text = m.season_forecast_text()
    assert text.startswith("Forecast: Summer x1.00 in 12 ticks, then Autumn x0.95 in 52 ticks")
    assert game_env.elements["season-forecast"].innerText == text


def test_forecast_wraps_from_winter_to_spring(game_env):
    m = game_env.module
    m.forest_tick = 3 * m.SEASON_CYCLE_TICKS + 5  # winter
    text = m.season_forecast_text()
    assert "Spring x1.10 in 35 ticks, then Summer x1.00 in 75 ticks" in text


@pytest.mark.parametrize("start", [0, 10, 31, 77, 140, 333])
def test_forecast_weather_is_exact(game_env, start):
    """The weather the forecast promises arrives on exactly the tick it names, with the stated length."""
    m = game_env.module
    m.forest_tick = start
    upcoming = m._next_weather_episode()
    assert upcoming is not None
    kind, begins_in, start_tick = upcoming
    assert start_tick == start + begins_in and begins_in >= 1
    assert m.weather_at(start_tick - 1) != kind or m._weather_episode(start_tick - 1)[1] != start_tick
    for k in range(m.WEATHER_DURATION_TICKS):
        assert m.weather_at(start_tick + k) == kind
    assert f"in {begins_in} ticks, lasting {m.WEATHER_DURATION_TICKS}" in m.season_forecast_text()


def test_forecast_skips_the_episode_already_under_way(game_env):
    m = game_env.module
    m.forest_tick = 0
    kind, begins_in, start_tick = m._next_weather_episode()
    m.forest_tick = start_tick + 2  # inside that episode
    nxt = m._next_weather_episode()
    assert nxt is None or nxt[2] > start_tick


def test_forecast_text_follows_the_clock_each_tick(game_env):
    m = game_env.module
    before = m.season_forecast_text()
    game_env.tick()
    assert game_env.elements["season-forecast"].innerText != before


# --- B-16: the plot card ---------------------------------------------------------------------------------------------

def test_plot_card_has_a_second_line_with_age_biodiversity_and_clears(game_env):
    m = game_env.module
    game_env.tick(7)
    card = tile(game_env, 0).getAttribute("data-tooltip")
    first, second = card.split("\n")
    assert first.startswith("A1 · Preserved") and "soil 100%" in first
    assert second == "Age: standing 7 ticks · biodiversity +0.02/tick · never cleared"
    assert tile(game_env, 0).getAttribute("aria-label") == card


def test_plot_card_for_replanting_bare_and_cleared_plots(game_env):
    m = game_env.module
    game_env.select(1)
    game_env.clear()
    assert "Age: bare · biodiversity +0.00/tick · cleared 1 time" in tile(game_env, 1).getAttribute("data-tooltip")
    assert not tile(game_env, 1).getAttribute("data-tooltip").endswith("times")
    game_env.replant()
    second = tile(game_env, 1).getAttribute("data-tooltip").split("\n")[1]
    assert second.startswith("Age: replanting, 10 ticks to go") and "cleared 1 time" in second
    m.plots[1].clear_count = 3
    assert "cleared 3 times" in m._plot_tooltip_detail(m.plots[1])


def test_biodiversity_specialist_shows_its_faster_rate(game_env):
    m = game_env.module
    m.plots[2].specialization = m.SPECIALIZATION_BIODIVERSITY
    assert "biodiversity +0.05/tick" in m._plot_tooltip_detail(m.plots[2])


def test_plot_tooltip_element_keeps_line_breaks(game_env):
    css = (game_env.module.__file__.rsplit("/", 1)[0] + "/style.css")
    text = open(css, encoding="utf-8").read()
    start = text.index(".plot-tooltip {")
    assert "white-space: pre;" in text[start:start + 500]


# --- B-6: request pace ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("pace,expected", [("relaxed", 22), ("normal", 15), ("frequent", 10)])
def test_each_pace_scales_the_request_interval(game_env, pace, expected):
    m = game_env.module
    m.reset_session(pace=pace)
    assert m.current_request_interval() == expected
    for _ in range(expected - 1):
        game_env.tick()
    assert m.pending_stakeholder_request is None
    game_env.tick()
    assert m.pending_stakeholder_request is not None


def test_normal_pace_is_the_old_interval(game_env):
    m = game_env.module
    assert m.current_request_interval() == m.STAKEHOLDER_EVENT_INTERVAL_TICKS


def test_the_pace_select_resets_the_session_and_stays_in_sync(game_env):
    m = game_env.module
    game_env.tick(4)
    game_env.change_pace("frequent")
    assert m.current_pace == "frequent" and m.forest_tick == 0
    assert game_env.elements["request-pace-select"].value == "frequent"
    game_env.change_pace("normal")
    assert m.current_pace == "normal"


def test_an_unknown_pace_is_refused(game_env):
    m = game_env.module
    assert m.reset_session(pace="warp") is False and m.current_pace == "normal"


def test_pace_is_saved_only_when_not_normal_and_restored(game_env):
    m = game_env.module
    assert "request_pace" not in m.get_state()
    m.reset_session(pace="relaxed")
    snapshot = json.loads(json.dumps(m.get_state()))
    assert snapshot["request_pace"] == "relaxed"
    m.reset_session(pace="frequent")
    m.load_state(snapshot)
    assert m.current_pace == "relaxed"


@pytest.mark.parametrize("junk", ["warp", 3, None, ["relaxed"], {"a": 1}])
def test_a_bad_saved_pace_means_normal(game_env, junk):
    m = game_env.module
    snapshot = json.loads(json.dumps(m.get_state()))
    snapshot["request_pace"] = junk
    m.reset_session(pace="frequent")
    m.load_state(snapshot)
    assert m.current_pace == "normal"


def test_pace_is_named_in_the_shared_result_so_stats_stay_honest(game_env):
    m = game_env.module
    assert m.session_tag_text() == "" and "(" not in m.share_snippet().split("plots still standing.")[1]
    m.reset_session(pace="frequent", difficulty="ranger")
    assert m.session_tag_text() == "Forest ranger, frequent requests"
    assert m.share_snippet().endswith("(Forest ranger, frequent requests)")
    m.reset_session(challenge="sprint")
    assert "Sprint challenge" in m.session_tag_text()


# --- B-7: announcer, cursor and hotkeys ---------------------------------------------------------------------------

def spoken(env):
    return env.elements["sr-announcer"].innerText


def test_clearing_and_replanting_are_announced(game_env):
    game_env.select(3)
    game_env.clear()
    assert "Cleared D1 for" in spoken(game_env)
    game_env.replant()
    assert "Replanted" in spoken(game_env)


def test_a_new_request_is_announced_with_its_text(game_env):
    m = game_env.module
    game_env.tick(m.current_request_interval())
    assert m.pending_stakeholder_request is not None
    assert "New community request." in spoken(game_env)
    assert m.stakeholder_request_message().split(",")[0] in spoken(game_env)


def test_a_new_season_is_announced(game_env):
    m = game_env.module
    advance_to(game_env, m.SEASON_CYCLE_TICKS - 1)
    game_env.tick()
    assert "Summer begins, growth x1.00" in spoken(game_env)


def test_achievements_are_announced_once(game_env):
    m = game_env.module
    game_env.select(0)
    game_env.clear()
    assert "Achievement unlocked" in spoken(game_env)
    heard = []
    real = m._announce
    m._announce = lambda message: (heard.append(message), real(message))[1]
    game_env.tick()
    assert not [h for h in heard if "Achievement" in h]


def test_the_queue_is_emptied_by_each_render_and_capped(game_env):
    m = game_env.module
    for n in range(20):
        m._announce(f"message {n}")
    assert len(m._announce_queue) == m.ANNOUNCE_MAX_QUEUED
    m.render()
    assert m._announce_queue == [] and "message 19" in spoken(game_env)


def test_wildlife_and_maturity_chatter_is_not_announced(game_env):
    m = game_env.module
    m._announce_queue.clear()
    m._log_event("wildlife", "A fox appeared", 1)
    m._log_event("mature", "A1 reached full maturity", 0)
    assert m._announce_queue == []


def test_hotkey_c_clears_and_r_replants_the_selected_plot(game_env):
    m = game_env.module
    game_env.select(4)
    assert m.hotkey_clear_selected() is True and m.plots[4].state == m.BARE
    assert m.hotkey_clear_selected() is False  # already bare
    assert m.hotkey_replant_selected() is True and m.plots[4].state == m.REPLANTING
    assert m.hotkey_replant_selected() is False


def test_hotkeys_do_nothing_without_a_selection_and_say_why(game_env):
    m = game_env.module
    assert m.selected_index is None
    assert m.hotkey_clear_selected() is False
    assert "No plot selected" in spoken(game_env) and "press C" in spoken(game_env)
    assert m.hotkey_replant_selected() is False
    assert "press R" in spoken(game_env)
    assert all(p.state == m.PRESERVED for p in m.plots)


def test_hotkey_c_respects_the_heart_tree(game_env):
    m = game_env.module
    m.heart_tree_index = 14
    game_env.select(14)
    assert m.hotkey_clear_selected() is False and m.plots[14].state == m.PRESERVED


def test_the_page_routes_c_and_r_and_lists_them(game_env):
    root = game_env.module.__file__.rsplit("/", 1)[0]
    html = open(root + "/index.html", encoding="utf-8").read()
    assert 'key !== "c" && key !== "r"' in html
    assert "hotkey_clear_selected" in html and "hotkey_replant_selected" in html
    assert "C — clear the selected plot; R — replant the selected plot" in html
    assert 'id="sr-announcer"' in html and 'aria-live="polite"' in html and 'role="status"' in html
    css = open(root + "/style.css", encoding="utf-8").read()
    assert ".plot-grid .plot-tile:focus-visible" in css and "outline: 3px solid #ffd54f" in css


# --- B-8: high-contrast plots -----------------------------------------------------------------------------------

def test_by_default_tiles_carry_no_letters_or_contrast_class(game_env):
    for index in range(4):
        assert "plot-contrast" not in tile(game_env, index).className
        assert tile_marks(game_env, index) == []


def test_high_contrast_adds_a_letter_and_a_class_to_every_tile(game_env):
    m = game_env.module
    game_env.select(1)
    game_env.clear()
    game_env.select(2)
    game_env.clear()
    game_env.replant()
    make_mature(m, 3)
    game_env.set_pref(m.UI_PREF_PLOT_CONTRAST, "true")
    m.render()
    letters = {}
    for index in range(6):
        marks = [c for c in tile(game_env, index).children if c.className == "state-letter"]
        assert len(marks) == 1 and "plot-contrast" in tile(game_env, index).className
        assert marks[0].getAttribute("aria-hidden") == "true"
        letters[index] = marks[0].innerText
    assert letters[0] == "G" and letters[1] == "B" and letters[2] == "R" and letters[3] == "M"
    assert "plot-mature" in tile(game_env, 3).className


def test_turning_high_contrast_off_removes_the_letters(game_env):
    m = game_env.module
    game_env.set_pref(m.UI_PREF_PLOT_CONTRAST, "true")
    m.render()
    game_env.set_pref(m.UI_PREF_PLOT_CONTRAST, "false")
    m.render()
    assert all("plot-contrast" not in tile(game_env, i).className for i in range(36))


def test_recovered_and_preserved_both_read_as_growing_until_mature(game_env):
    m = game_env.module
    m.plots[0].state = m.RECOVERED
    m.plots[0].ticks_intact = 5
    game_env.set_pref(m.UI_PREF_PLOT_CONTRAST, "true")
    m.render()
    assert [c.innerText for c in tile(game_env, 0).children if c.className == "state-letter"] == ["G"]


# --- B-10: soil overlay -----------------------------------------------------------------------------------------

def test_soil_overlay_is_off_by_default(game_env):
    assert "plot-soil" not in tile(game_env, 0).className
    assert not [c for c in tile(game_env, 0).children if c.className == "soil-badge"]


@pytest.mark.parametrize("clears,pct,band", [(0, 100, "good"), (1, 90, "good"), (2, 80, "fair"), (3, 70, "fair"), (4, 60, "poor"), (5, 50, "poor"), (6, 40, "depleted"), (20, 20, "depleted")])
def test_soil_bands_and_numbers(game_env, clears, pct, band):
    m = game_env.module
    m.plots[0].clear_count = clears
    game_env.set_pref(m.UI_PREF_SOIL_OVERLAY, "true")
    m.render()
    assert f"plot-soil--{band}" in tile(game_env, 0).className
    badge = [c for c in tile(game_env, 0).children if c.className == "soil-badge"]
    assert len(badge) == 1 and badge[0].innerText == str(pct)


def test_soil_overlay_reads_the_ranger_difficulty_steeper_degradation(game_env):
    m = game_env.module
    m.reset_session(difficulty="ranger")
    m.plots[0].clear_count = 2
    game_env.set_pref(m.UI_PREF_SOIL_OVERLAY, "true")
    m.render()
    assert [c.innerText for c in tile(game_env, 0).children if c.className == "soil-badge"] == ["60"]
    assert "plot-soil--poor" in tile(game_env, 0).className


def test_both_overlays_can_be_on_together(game_env):
    m = game_env.module
    game_env.set_pref(m.UI_PREF_PLOT_CONTRAST, "true")
    game_env.set_pref(m.UI_PREF_SOIL_OVERLAY, "true")
    m.render()
    classes = [c.className for c in tile(game_env, 0).children]
    assert "state-letter" in classes and "soil-badge" in classes


# --- B-26: number format ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("mode,value,expected", [
    ("standard", 12345.678, "12345.7"),
    ("grouped", 12345.678, "12,345.7"),
    ("grouped", 12.0, "12.0"),
    ("compact", 12345.678, "12.3k"),
    ("compact", 1000.0, "1k"),
    ("compact", 999.94, "999.9"),
    ("compact", 999950.0, "1M"),
    ("compact", 2_500_000.0, "2.5M"),
    ("compact", 3_100_000_000.0, "3.1B"),
    ("compact", 7.25, "7.2"),
    ("compact", 0.0, "0.0"),
    ("compact", -4500.0, "-4.5k"),
    ("precise", 12345.678, "12345.68"),
    ("bogus", 12345.678, "12345.7"),
])
def test_fmt_num_in_every_mode(game_env, mode, value, expected):
    m = game_env.module
    game_env.set_pref(m.UI_PREF_NUMBER_FORMAT, mode)
    assert m.fmt_num(value) == expected


def test_the_hud_follows_the_chosen_format(game_env):
    m = game_env.module
    for plot in m.plots:
        plot.value = 400.0
    game_env.set_pref(m.UI_PREF_NUMBER_FORMAT, "compact")
    m.render()
    assert game_env.elements["standing-value-display"].innerText == "Standing forest value: 14.4k"
    game_env.set_pref(m.UI_PREF_NUMBER_FORMAT, "grouped")
    m.render()
    assert game_env.elements["standing-value-display"].innerText == "Standing forest value: 14,400.0"
    game_env.set_pref(m.UI_PREF_NUMBER_FORMAT, "standard")
    m.render()
    assert game_env.elements["standing-value-display"].innerText == "Standing forest value: 14400.0"


def test_income_and_personal_best_follow_the_format_too(game_env):
    m = game_env.module
    m.total_income = 12345.0
    game_env.set_pref(m.UI_PREF_NUMBER_FORMAT, "compact")
    m.render()
    assert game_env.elements["income-display"].innerText == "Harvested income: 12.3k"
    assert "12.3k" in game_env.elements["personal-best-display"].innerText


def test_default_format_is_unchanged(game_env):
    m = game_env.module
    m.total_income = 1234.5
    m.render()
    assert game_env.elements["income-display"].innerText == "Harvested income: 1234.5"


# --- settings.js, index.html, pc page ------------------------------------------------------------------------------

def _read(game_env, name):
    root = game_env.module.__file__.rsplit("/", 1)[0]
    return open(f"{root}/{name}", encoding="utf-8").read()


def test_settings_js_stores_and_reapplies_the_three_options(game_env):
    js = _read(game_env, "settings.js")
    for key in ("canopy-plot-contrast", "canopy-soil-overlay", "canopy-number-format"):
        assert key in js
    for element_id in ("plot-contrast-checkbox", "soil-overlay-checkbox", "number-format-select"):
        assert element_id in js
    assert 'globals.get("render")' in js  # a change redraws at once
    assert "applyPlotContrast(false)" in js and "applySoilOverlay(false)" in js  # Reset to Default clears them


def test_python_and_settings_js_agree_on_the_storage_keys(game_env):
    m = game_env.module
    js = _read(game_env, "settings.js")
    for key in (m.UI_PREF_PLOT_CONTRAST, m.UI_PREF_SOIL_OVERLAY, m.UI_PREF_NUMBER_FORMAT):
        assert f'"{key}"' in js
    for mode in m.NUMBER_FORMATS:
        assert f'value="{mode}"' in _read(game_env, "index.html")


def test_every_new_element_exists_on_both_pages(game_env):
    for name in ("index.html", "pc.html"):
        html = _read(game_env, name)
        for element_id in (
            "season-forecast", "challenge-status", "challenge-select", "request-pace-select",
            "contracts-toggle-button", "contracts-panel", "sr-announcer",
            "plot-contrast-checkbox", "soil-overlay-checkbox", "number-format-select",
        ):
            assert f'id="{element_id}"' in html, (name, element_id)


def test_the_desktop_boot_can_reach_every_new_panel_and_setting(game_env):
    cfg = json.loads(_read(game_env, "pc-config.json"))
    assert ["contracts-panel", "contracts-toggle-button", "Ranger contracts"] in cfg["windows"]
    assert ["contracts-toggle-button", "\U0001F4DC"] in cfg["toolbar"]["icons"]
    assert "#season-forecast" in cfg["zones"]["stagebar"] and "#challenge-status" in cfg["zones"]["stagebar"]
    setup = [c for c in cfg["composites"] if c["id"] == "pc-setup-panel"][0]
    assert ".grid-size-label" in setup["members"]  # the new selects are .grid-size-label, so they ride along
    index = _read(game_env, "index.html")
    assert index.count('class="grid-size-label"') == 5  # grid size, difficulty, request pace, challenge, scenario (B-11)
    hints = [h[0] for h in cfg["hints"]]
    assert "C" in hints and "R" in hints


def test_both_pages_list_contracts_in_the_keyboard_shortcut_panels(game_env):
    for name in ("index.html", "pc.html"):
        assert '{ toggle: "contracts-toggle-button", panel: "contracts-panel" }' in _read(game_env, name)
