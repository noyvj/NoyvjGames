"""2026-10-07 TODO pass: D-1 Harbor Ledger, D-7 screen-reader text and focus, D-14 game keys (file
checks only: the key handler is plain JS), D-15 Advance x5, D-17 ticker filters, D-18 copy as text,
D-24 tab title and favicon, D-27 remembered <details> panels (file checks)."""

import re
import types
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
LEDGER_KEYS = ["season", "funds", "acidity", "fish_yield", "damage", "rows_dry", "population", "tier", "invested"]


def play(env, seasons=3, invest_output=2):
    for _ in range(invest_output):
        env.invest("output")
    for _ in range(seasons):
        env.advance_season()


# ---- D-1 Harbor Ledger -------------------------------------------------------------------------
def test_each_season_adds_one_ledger_row_with_every_column(game_env):
    play(game_env, seasons=4)
    ledger = game_env.state.season_ledger
    assert [e["season"] for e in ledger] == [1, 2, 3, 4]
    assert all(set(e) == set(LEDGER_KEYS) for e in ledger)
    last = ledger[-1]
    assert last["funds"] == pytest.approx(game_env.state.funds, abs=0.06)
    assert last["rows_dry"] == game_env.state.rows_dry_count()
    assert last["invested"] == 2
    assert last["fish_yield"] == pytest.approx(game_env.state.fish_yield_multiplier(), abs=1e-3)


def test_ledger_damage_matches_damage_log(game_env):
    play(game_env, seasons=3)
    state = game_env.state
    for entry, damage in zip(state.season_ledger, state.damage_log):
        assert entry["damage"] == pytest.approx(damage, abs=0.01)


def test_ledger_is_capped(game_env):
    state = game_env.state
    limit = game_env.module.LEDGER_LIMIT
    for _ in range(limit + 10):
        state.advance_season()
    assert len(state.season_ledger) == limit
    assert state.season_ledger[-1]["season"] == limit + 10


def test_sorting_by_every_column_is_ordered_and_does_not_mutate(game_env):
    play(game_env, seasons=6)
    state = game_env.state
    before = list(state.season_ledger)
    for key in LEDGER_KEYS:
        ascending = [e[key] for e in state.sorted_ledger(key, False)]
        descending = [e[key] for e in state.sorted_ledger(key, True)]
        assert ascending == sorted(ascending)
        assert descending == sorted(descending, reverse=True)
    assert state.season_ledger == before
    assert [e["season"] for e in state.sorted_ledger("nonsense", False)] == [1, 2, 3, 4, 5, 6]


def test_ledger_panel_opens_and_renders_rows_and_charts(game_env):
    play(game_env, seasons=4)
    elements = game_env.elements
    assert elements["ledger-panel"].hidden is True
    game_env.toggle_ledger()
    assert elements["ledger-panel"].hidden is False
    assert elements["ledger-toggle-button"].innerText == "Hide Harbor Ledger"
    body = elements["ledger-body"].innerHTML
    assert body.count("<tr>") == 4
    assert elements["ledger-chart-funds"].innerHTML.startswith("<svg")
    assert elements["ledger-chart-season"].innerHTML == ""
    assert "4 season(s) recorded" in elements["ledger-summary"].innerText
    game_env.toggle_ledger()
    assert elements["ledger-panel"].hidden is True


def test_clicking_a_column_sorts_and_clicking_again_reverses(game_env):
    play(game_env, seasons=5)
    elements = game_env.elements
    game_env.toggle_ledger()
    # Default: newest season first.
    first_cells = re.findall(r"<tr><td>(\d+)</td>", elements["ledger-body"].innerHTML)
    assert first_cells == ["5", "4", "3", "2", "1"]
    elements["ledger-sort-season"].dispatch("click", None)
    assert re.findall(r"<tr><td>(\d+)</td>", elements["ledger-body"].innerHTML) == ["1", "2", "3", "4", "5"]
    assert elements["ledger-th-season"].getAttribute("aria-sort") == "ascending"
    elements["ledger-sort-funds"].dispatch("click", None)
    assert elements["ledger-th-funds"].getAttribute("aria-sort") == "descending"
    assert elements["ledger-th-season"].getAttribute("aria-sort") == "none"
    assert "▼" in elements["ledger-sort-funds"].innerText


def test_ledger_round_trips_through_save_and_load(game_env):
    play(game_env, seasons=4)
    saved = game_env.module.get_state()
    before = list(game_env.state.season_ledger)
    play(game_env, seasons=2, invest_output=0)
    assert game_env.module.load_state(saved)
    assert game_env.state.season_ledger == before


def test_old_save_without_ledger_loads_with_an_empty_ledger_and_a_note(game_env):
    play(game_env, seasons=3)
    saved = game_env.module.get_state()
    del saved["season_ledger"]
    assert game_env.module.load_state(saved)
    assert game_env.state.season_ledger == []
    assert "No seasons recorded" in game_env.state.ledger_summary_text()
    game_env.state.advance_season()
    assert "older saves" in game_env.state.ledger_summary_text()


def test_damaged_ledger_entries_are_dropped_on_load(game_env):
    play(game_env, seasons=3)
    saved = game_env.module.get_state()
    good = dict(saved["season_ledger"][0])
    saved["season_ledger"] = [
        good,
        {"season": 2},
        "junk",
        {**good, "funds": float("nan")},
        {**good, "fish_yield": 7},
        {**good, "tier": True},
        {**good, "season": 9, "funds": 10.0},
    ]
    assert game_env.module.load_state(saved)
    assert [e["season"] for e in game_env.state.season_ledger] == [1, 9]


def test_load_state_rejects_a_non_list_ledger(game_env):
    saved = game_env.module.get_state()
    saved["season_ledger"] = {"a": 1}
    assert game_env.module.load_state(saved)
    assert game_env.state.season_ledger == []


def test_replay_rewinds_the_ledger_with_the_run(game_env):
    state = game_env.state
    play(game_env, seasons=2)
    state.set_checkpoint()
    assert "season_ledger" not in state.checkpoint
    for _ in range(3):
        state.advance_season()
    assert len(state.season_ledger) == 5
    assert game_env.module.replay_from_checkpoint()
    assert [e["season"] for e in state.season_ledger] == [1, 2]
    state.advance_season()
    assert [e["season"] for e in state.season_ledger] == [1, 2, 3]


# ---- D-15 Advance x5 ----------------------------------------------------------------------------
def settle_heritage(env):
    """Both heritage sites already decided (lost), so they never interrupt a quiet run."""
    for site in env.module.HERITAGE_SITES:
        env.state.heritage[site["id"]] = env.module.HERITAGE_LOST


def test_advance_x5_runs_five_quiet_seasons(game_env):
    state = game_env.state
    settle_heritage(game_env)
    for _ in range(3):
        game_env.invest("reduction")
    game_env.advance_x5()
    assert state.season == 6
    assert len(state.season_ledger) == 5
    assert "Ran 5 quiet seasons" in game_env.elements["advance-x5-note"].innerText
    assert "Season 5 resolved" in game_env.elements["season-announcer"].innerText


def test_advance_x5_stops_before_a_storm_forecast(game_env):
    state = game_env.state
    settle_heritage(game_env)
    state.set_storm_mode(True)
    ran, stop = state.advance_quiet_seasons(5)
    # Season 4 is the forecast season for a storm landing on season 5.
    assert state.season == 4
    assert ran == 3
    assert "storm surge is forecast for next season" in stop


def test_advance_x5_refuses_to_start_while_something_needs_attention(game_env):
    state = game_env.state
    state.set_storm_mode(True)
    state.season = 4
    game_env.advance_x5()
    assert state.season == 4
    assert "Not started" in game_env.elements["advance-x5-note"].innerText
    assert "storm" in game_env.elements["advance-x5-note"].innerText


def test_advance_x5_stops_at_a_fish_yield_warning(game_env):
    state = game_env.state
    for _ in range(12):
        state.capacity["output"] += 1
    state.funds = 5000
    ran, stop = state.advance_quiet_seasons(5)
    assert stop is not None and "fish-yield warning" in stop
    assert state.fish_warning_active()
    # Once stopped, a second click will not start while the warning shows.
    again, stop_again = state.advance_quiet_seasons(5)
    assert again == 0 and "fish-yield warning" in stop_again


def test_advance_x5_stops_when_an_affordable_heritage_site_is_about_to_flood(game_env):
    state = game_env.state
    state.funds = 1000
    site = game_env.module.HERITAGE_SITES[0]
    state.sea_level = game_env.module.row_flood_threshold(site["row"]) - 5.0
    assert [s["id"] for s in state.heritage_at_risk()] == [site["id"]]
    ran, stop = state.advance_quiet_seasons(5)
    assert ran == 0 and "old lighthouse" in stop
    state.protect_heritage(site["id"])
    assert state.heritage_at_risk() == []


def test_unaffordable_heritage_does_not_block_advance_x5(game_env):
    state = game_env.state
    state.funds = 10
    site = game_env.module.HERITAGE_SITES[0]
    state.sea_level = game_env.module.row_flood_threshold(site["row"]) - 5.0
    assert state.heritage_at_risk() == []


def test_advance_x5_stops_when_monitoring_becomes_available_again(game_env):
    state = game_env.state
    settle_heritage(game_env)
    state.funds = 1000
    assert state.fund_monitoring()
    # A player who never used monitoring is never stopped for it.
    ran, stop = state.advance_quiet_seasons(5)
    assert ran == 2 and "monitoring crew" in stop
    assert state.season - state.monitoring_last_season == 2


def test_monitoring_never_stops_a_player_who_has_not_used_it(game_env):
    state = game_env.state
    settle_heritage(game_env)
    state.funds = 1000
    assert not state.monitoring_ready_again()
    ran, stop = state.advance_quiet_seasons(5)
    assert ran == 5 and stop is None


# ---- D-7 screen-reader text and focus -----------------------------------------------------------
def test_coastline_row_description_names_status_and_seawall_tier(game_env):
    state = game_env.state
    assert state.coastline_row_description(5).startswith("Row 6: dry")
    state.capacity["adaptation"] = 6
    state.funds = 0
    text = state.coastline_row_description(5)
    assert text.startswith("Row 6: dry, seawall tier 2")
    assert "seawall" not in state.coastline_row_description(0)
    state.sea_level = 60.0
    assert state.coastline_row_description(5).startswith("Row 6: flooded")
    state.retreat_rows = [2]
    assert state.coastline_row_description(2).startswith("Row 3: cleared by managed retreat")


def test_coastline_description_covers_every_row(game_env):
    text = game_env.state.coastline_description()
    for row in range(1, 7):
        assert f"Row {row}:" in text
    assert "6 dry" in text


def test_row_tiles_are_one_focus_stop_per_row_with_labels(game_env):
    elements = game_env.elements
    grid = elements["coastline-grid"]
    assert len(grid.children) == 48
    stops = [t for t in grid.children if t.tabIndex == 0]
    assert len(stops) == 6
    assert all(t.getAttribute("role") == "img" and t.getAttribute("aria-label").startswith("Row ") for t in stops)
    others = [t for t in grid.children if t.tabIndex != 0]
    assert all(t.getAttribute("aria-hidden") == "true" for t in others)
    assert grid.getAttribute("aria-label")
    assert "Row 1:" in elements["coastline-description"].innerText


def test_advance_announces_the_season_result(game_env):
    game_env.invest("output")
    game_env.advance_season()
    text = game_env.elements["season-announcer"].innerText
    assert "Season 1 resolved" in text and "Funds" in text and "coastline rows dry" in text


def test_invest_announces_and_buttons_get_descriptive_names(game_env):
    game_env.invest("output")
    assert "Invested in Output" in game_env.elements["season-announcer"].innerText
    button = game_env.elements["adaptation-invest-button"]
    assert button.getAttribute("aria-label") == "Invest 30 funds in Adaptation"
    game_env.state.funds = 0
    game_env.invest("adaptation")
    assert "Not enough funds" in game_env.elements["season-announcer"].innerText


def test_graphs_are_keyboard_focusable_with_text_labels(game_env):
    play(game_env, seasons=3)
    svg = game_env.elements["acidity-fish-graph"].innerHTML
    assert 'tabindex="0"' in svg and "Latest: acidity" in svg


# ---- D-17 ticker filters ------------------------------------------------------------------------
@pytest.mark.parametrize(
    "message,category",
    [
        ("Fish stocks quietly declining — acidity from 3 seasons ago is catching up.", "fish"),
        ("Acidity is rising — the effect on fish stocks won't show for a few more seasons.", "fish"),
        ("⛈️ Storm surge in Season 5: 12 of 18 held back by your defences; the rest cost 20 funds.", "storm"),
        ("Adaptation upgraded to Storm-surge barriers — sea-level damage is now dampened 95%.", "sea"),
        ("The first coastline tile has flooded — the sea has arrived.", "sea"),
        ("Economy diversified: tourism is now level 1.", "economy"),
        ("Monitoring report in: oceans are absorbing a lot of the extra sea warmth.", "chronicle"),
        ("The old lighthouse has been lost to the sea.", "chronicle"),
        ("Checkpoint saved at Season 4.", "chronicle"),
        ("Something unrelated.", "other"),
    ],
)
def test_ticker_messages_are_categorised(game_env, message, category):
    assert game_env.module.ticker_category(message) == category


def test_ticker_filter_chips_and_search_narrow_the_history(game_env):
    module, elements, state = game_env.module, game_env.elements, game_env.state
    state.ticker_full_history = [
        "Fish stocks quietly declining — acidity is catching up.",
        "Economy diversified: tourism is now level 1.",
        "The first coastline tile has flooded — the sea has arrived.",
    ]
    module.render()
    assert elements["ticker-history-list"].innerHTML.count("<br>") == 2
    elements["ticker-filter-fish"].dispatch("click", None)
    assert elements["ticker-history-list"].innerHTML == state.ticker_full_history[0]
    assert elements["ticker-filter-fish"].getAttribute("aria-pressed") == "true"
    assert elements["ticker-filter-all"].getAttribute("aria-pressed") == "false"
    assert "Showing 1 of 3" in elements["ticker-filter-status"].innerText
    elements["ticker-filter-all"].dispatch("click", None)
    event = types.SimpleNamespace(target=types.SimpleNamespace(value="TOURISM"))
    elements["ticker-search-input"].dispatch("input", event)
    assert elements["ticker-history-list"].innerHTML == state.ticker_full_history[1]
    event.target.value = "no such text"
    elements["ticker-search-input"].dispatch("input", event)
    assert elements["ticker-history-list"].innerHTML == "No messages match this filter."
    # The stored history is never changed by filtering.
    assert len(state.ticker_full_history) == 3
    module.on_ticker_search(types.SimpleNamespace(target=types.SimpleNamespace(value="")))
    module.ticker_filter = "all"


def test_the_live_ticker_is_never_filtered(game_env):
    module, elements, state = game_env.module, game_env.elements, game_env.state
    state._log_ticker("Economy diversified: tourism is now level 1.")
    elements["ticker-filter-storm"].dispatch("click", None)
    module.render()
    assert "Economy diversified" in elements["ticker-log"].innerHTML
    elements["ticker-filter-all"].dispatch("click", None)


# ---- D-18 copy as text --------------------------------------------------------------------------
def test_share_text_names_the_settlement_summary_and_chronicle(game_env):
    state = game_env.state
    state.set_settlement_name("Port Regret")
    play(game_env, seasons=2)
    text = state.share_text()
    assert text.splitlines()[0] == "Port Regret — a Tide settlement"
    assert "Seasons played: 2" in text
    assert "coastline rows dry" in text


def test_copy_button_falls_back_to_a_text_box_without_a_clipboard(game_env):
    game_env.state.set_settlement_name("Kelp Junction")
    game_env.elements["copy-text-button"].dispatch("click", None)
    area = game_env.elements["copy-text-area"]
    assert area.hidden is False
    assert area.value.startswith("Kelp Junction")
    assert "Could not copy" in game_env.elements["copy-text-status"].innerText


def test_copy_button_uses_the_clipboard_when_there_is_one(game_env):
    import js

    written = []

    class Promise:
        def then(self, done, fail):
            self.done = done
            return self

    class Clipboard:
        def writeText(self, text):
            written.append(text)
            return Promise()

    js.navigator = types.SimpleNamespace(clipboard=Clipboard())
    try:
        game_env.elements["copy-text-button"].dispatch("click", None)
    finally:
        del js.navigator
    assert written and "a Tide settlement" in written[0]
    assert game_env.elements["copy-text-area"].hidden is True
    assert game_env.elements["copy-text-status"].innerText == "Copying..."


# ---- D-24 tab title and favicon -----------------------------------------------------------------
def test_tab_title_follows_the_season_and_warnings(game_env):
    state, module = game_env.state, game_env.module
    assert module.tab_status() == ("Tide S1", "normal")
    state.set_storm_mode(True)
    state.season = 4
    assert module.tab_status() == ("Tide S4 - storm forecast", "storm")
    state.set_storm_mode(False)
    state.season = 7
    assert module.tab_status() == ("Tide S7", "normal")


def test_tab_title_shows_a_fish_warning(game_env):
    state, module = game_env.state, game_env.module
    state.capacity["output"] = 12
    state.funds = 5000
    state.advance_quiet_seasons(5)
    title, kind = module.tab_status()
    assert title.endswith("- fish warning") and kind == "warning"


def test_render_writes_the_document_title(game_env):
    module = game_env.module
    game_env.invest("output")
    game_env.advance_season()
    assert module.document.title == "Tide S2"


def test_favicon_variants_differ_in_shape_not_only_colour(game_env):
    module = game_env.module
    warning, storm = module._favicon_data_uri("warning"), module._favicon_data_uri("storm")
    assert warning.startswith("data:image/svg+xml,") and storm.startswith("data:image/svg+xml,")
    assert "circle" in warning and "circle" not in storm
    assert "rect%20" in storm or "%3Crect x=" in storm


# ---- D-14 / D-7 / D-27 page-level script (plain JS: checked as files) ---------------------------
def read(name):
    return (GAME_DIR / name).read_text(encoding="utf-8")


def test_both_pages_load_ui_js_and_list_the_game_keys():
    for page in ("index.html", "pc.html"):
        html = read(page)
        assert '<script src="ui.js" defer></script>' in html
        for line in ("A — advance one season", "R — open or close the session report", "L — open or close the Harbor Ledger"):
            assert line in html


def test_ui_js_wires_every_documented_key_to_a_real_button():
    js = read("ui.js")
    html = read("index.html")
    for button_id in (
        "advance-season-button", "advance-x5-button", "output-invest-button", "reduction-invest-button",
        "adaptation-invest-button", "session-summary-toggle-button", "ledger-toggle-button",
    ):
        assert f'"{button_id}"' in js
        assert f'id="{button_id}"' in html
    assert "isTyping" in js and "modalShown" in js and "ctrlKey" in js


def test_ui_js_remembers_details_panels_and_skips_the_info_bubbles():
    js = read("ui.js")
    assert "tide-details-open:" in js and '"toggle"' in js and 'label === "i"' in js


def test_ledger_and_filters_exist_in_both_pages():
    for page in ("index.html", "pc.html"):
        html = read(page)
        for key in LEDGER_KEYS:
            assert f'id="ledger-sort-{key}"' in html and f'id="ledger-chart-{key}"' in html
        for key in ("all", "fish", "sea", "economy", "storm", "chronicle"):
            assert f'id="ticker-filter-{key}"' in html
        assert 'id="season-announcer"' in html and 'aria-live="polite"' in html
