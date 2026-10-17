"""Tide — Ocean Acidification & Sea-Level Rise Game.

Runs in-browser via Pyodide. Milestone 1: the core settlement loop —
seasonal rounds, funds, and three investment categories (output/
reduction/adaptation), mirroring Grid's build-capacity pattern. Acidity,
sea-level rise, and the tile-grid coastline land in later milestones.
"""

import importlib
import sys
import types

from js import document
from pyodide.ffi import create_proxy

import tide_runstate as runstate
from tide_almanac import _load_almanac, _make_planner_input_handler, almanac_resync
from tide_chrome import _make_graph_range_handler
from tide_coastline import _resync_previous_flooded_rows
from tide_coasts import heritage_sites
from tide_flavour import CRITTERS, _make_critter_handler
from tide_graphs import _load_graph_prefs
from tide_handlers import (
    _make_diversify_handler, _make_heritage_handler, _make_invest_handler, on_advance_season, on_advance_x5,
    on_afford_pin_change, on_autosave_click, on_brace, on_brace_button, on_coastline_change, on_copy_text,
    on_crew_button, on_daily_date_change, on_daily_start, on_enable_sister, on_goal_change, on_library_save,
    on_live_search, on_make_postcard, on_market_answer, on_monitor, on_output_mix_change, on_planner_clear,
    on_planner_commit, on_planner_length, on_replay, on_retreat, on_rewind, on_roll_name, on_run_code_clear,
    on_run_code_load, on_scene_theme_change, on_scrub_input, on_scrub_live, on_sea_scenario_change,
    on_set_baseline, on_set_checkpoint, on_settlement_name_change, on_ticker_search, on_toggle_achievements,
    on_toggle_acid_boss, on_toggle_almanac, on_toggle_changelog, on_toggle_chess, on_toggle_daily,
    on_toggle_graph_markers, on_toggle_hard_lag, on_toggle_info_page, on_toggle_ledger, on_toggle_library,
    on_toggle_planner, on_toggle_session_summary, on_toggle_storms, on_why_button, on_workshop_apply,
    on_workshop_reset, on_workshop_slider,
)
from tide_libraryview import _make_library_select_handler
from tide_readouts import _make_net_funds_handler, load_afford_pin
from tide_renderer import render
from tide_rules import (
    CATEGORIES, CREW, DIVERSIFY_COST, GRAPH_RANGES, LEDGER_KEYS, PLANNER_MAX_SEASONS, TICKER_FILTERS,
    WORKSHOP_DEFAULTS,
)
from tide_ticker import _make_ledger_sort_handler, _make_live_filter_handler, _make_ticker_filter_handler

# ---------------------------------------------------------------------------
# File map: this file is the entry point and the wiring. Everything else lives in the modules named in
# _PART_NAMES, in dependency order (a module only imports from the ones before it). See "File map" in
# games/tide/CLAUDE.md for what each one holds.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "tide_rules",
    "tide_runstate",
    "tide_coasts",
    "tide_bridge",
    "tide_model_town",
    "tide_model_economy",
    "tide_model_season",
    "tide_coastline",
    "tide_library",
    "tide_graphs",
    "tide_panels",
    "tide_achievements",
    "tide_ticker",
    "tide_runcode",
    "tide_libraryview",
    "tide_daily",
    "tide_almanac",
    "tide_chrome",
    "tide_controls",
    "tide_readouts",
    "tide_seasonflow",
    "tide_flavour",
    "tide_workshop",
    "tide_events",
    "tide_savestate",
    "tide_renderer",
    "tide_loading",
    "tide_actions",
    "tide_handlers",
)
_PARTS = [importlib.import_module(_name) for _name in _PART_NAMES]
_LIVE = frozenset(runstate.LIVE_NAMES)

# Every name the old single-file game.py had is still reachable as game.<name> (tests and the page use them).
for _part in _PARTS:
    for _name, _value in vars(_part).items():
        if not _name.startswith("__") and _name not in _LIVE:
            globals()[_name] = _value
del _part, _name, _value


class _GameModule(types.ModuleType):
    """game.state & co. live in tide_runstate (they get replaced while playing), so reads go there; a write to
    any name copies to every module that holds the name, so monkeypatching game._write_local_storage_item or
    setting game.state = fresh still changes what the code uses."""

    def __getattr__(self, name):
        if name in _LIVE:
            return getattr(runstate, name)
        raise AttributeError(f"module {self.__name__!r} has no attribute {name!r}")

    def __setattr__(self, name, value):
        if name in _LIVE:
            setattr(runstate, name, value)
            return
        for _part in _PARTS:
            if name in vars(_part):
                setattr(_part, name, value)
        super().__setattr__(name, value)

    def __dir__(self):
        return sorted(set(super().__dir__()) | _LIVE)


try:
    sys.modules[__name__].__class__ = _GameModule
except TypeError:  # a host without module subclassing: plain names still work, only the forwarding is lost
    pass


def setup():
    for category in CATEGORIES:
        document.getElementById(f"{category}-invest-button").addEventListener(
            "click", create_proxy(_make_invest_handler(category))
        )
    document.getElementById("advance-season-button").addEventListener(
        "click", create_proxy(on_advance_season)
    )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    # D-15 / D-1 / D-18 / D-17: later additions, each tolerant of a missing node.
    for element_id, handler in (
        ("advance-x5-button", on_advance_x5),
        ("ledger-toggle-button", on_toggle_ledger),
        ("copy-text-button", on_copy_text),
    ):
        el = document.getElementById(element_id)
        if el is not None:
            el.addEventListener("click", create_proxy(handler))
    # 2026-10-08 pass: graph range/markers, scrubber, library, almanac, planner.
    for element_id, handler in (
        ("graph-markers-toggle", on_toggle_graph_markers),
        ("scrub-live-button", on_scrub_live),
        ("library-toggle-button", on_toggle_library),
        ("library-save-button", on_library_save),
        ("almanac-toggle-button", on_toggle_almanac),
        ("planner-toggle-button", on_toggle_planner),
        ("planner-clear-button", on_planner_clear),
        ("planner-commit-button", on_planner_commit),
    ):
        el = document.getElementById(element_id)
        if el is not None:
            el.addEventListener("click", create_proxy(handler))
    for key, _label in GRAPH_RANGES:
        el = document.getElementById(f"graph-range-{key}")
        if el is not None:
            el.addEventListener("click", create_proxy(_make_graph_range_handler(key)))
    for element_id, event_name, handler in (
        ("scrub-slider", "input", on_scrub_input),
        ("library-select-a", "change", _make_library_select_handler("library_a")),
        ("library-select-b", "change", _make_library_select_handler("library_b")),
        ("library-overlay-select", "change", _make_library_select_handler("library_overlay_id")),
        ("planner-length", "change", on_planner_length),
    ):
        el = document.getElementById(element_id)
        if el is not None:
            el.addEventListener(event_name, create_proxy(handler))
    for number in range(1, PLANNER_MAX_SEASONS + 1):
        for category in CATEGORIES:
            el = document.getElementById(f"planner-s{number}-{category}")
            if el is not None:
                el.addEventListener("input", create_proxy(_make_planner_input_handler(number, category)))
    for key in LEDGER_KEYS:
        el = document.getElementById(f"ledger-sort-{key}")
        if el is not None:
            el.addEventListener("click", create_proxy(_make_ledger_sort_handler(key)))
    for key, _label in TICKER_FILTERS:
        el = document.getElementById(f"ticker-filter-{key}")
        if el is not None:
            el.addEventListener("click", create_proxy(_make_ticker_filter_handler(key)))
    search_el = document.getElementById("ticker-search-input")
    if search_el is not None:
        search_el.addEventListener("input", create_proxy(on_ticker_search))
    for key, _label in TICKER_FILTERS:
        el = document.getElementById(f"live-filter-{key}")
        if el is not None:
            el.addEventListener("click", create_proxy(_make_live_filter_handler(key)))
    live_search_el = document.getElementById("live-search-input")
    if live_search_el is not None:
        live_search_el.addEventListener("input", create_proxy(on_live_search))
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("session-summary-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_session_summary)
    )
    output_mix_select = document.getElementById("output-mix-select")
    if output_mix_select is not None:
        output_mix_select.addEventListener("change", create_proxy(on_output_mix_change))
    scenario_select = document.getElementById("sea-scenario-select")
    if scenario_select is not None:
        scenario_select.addEventListener("change", create_proxy(on_sea_scenario_change))
    coastline_select = document.getElementById("coastline-select")  # D-8
    if coastline_select is not None:
        coastline_select.addEventListener("change", create_proxy(on_coastline_change))
    for element_id, event_name, handler in (  # D-3 run codes and GD-5 Daily Tide
        ("run-code-load-button", "click", on_run_code_load),
        ("run-code-clear-button", "click", on_run_code_clear),
        ("daily-toggle-button", "click", on_toggle_daily),
        ("daily-start-button", "click", on_daily_start),
        ("daily-date-input", "change", on_daily_date_change),
    ):
        el = document.getElementById(element_id)
        if el is not None:
            el.addEventListener(event_name, create_proxy(handler))
    document.getElementById("sister-enable-button").addEventListener("click", create_proxy(on_enable_sister))
    document.getElementById("hard-lag-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_hard_lag)
    )
    for i, site in enumerate(heritage_sites()):
        protect_button = document.getElementById(f"heritage-protect-{i}")
        if protect_button is not None:
            protect_button.addEventListener("click", create_proxy(_make_heritage_handler(site["id"])))
    for kind in DIVERSIFY_COST:
        el = document.getElementById(f"diversify-{kind}-button")
        if el is not None:
            el.addEventListener("click", create_proxy(_make_diversify_handler(kind)))
    for element_id, handler in (
        ("monitor-button", on_monitor),
        ("storm-toggle-button", on_toggle_storms),
        ("retreat-button", on_retreat),
        ("checkpoint-button", on_set_checkpoint),
        ("replay-button", on_replay),
    ):
        el = document.getElementById(element_id)
        if el is not None:
            el.addEventListener("click", create_proxy(handler))
    name_input = document.getElementById("settlement-name-input")
    if name_input is not None:
        name_input.addEventListener("change", create_proxy(on_settlement_name_change))
    for critter_id in CRITTERS:  # GD-18
        critter_button = document.getElementById(f"critter-{critter_id}")
        if critter_button is not None:
            critter_button.addEventListener("click", create_proxy(_make_critter_handler(critter_id)))
    rewind_button = document.getElementById("rewind-button")  # GD-20
    if rewind_button is not None:
        rewind_button.addEventListener("click", create_proxy(on_rewind))
    roll_button = document.getElementById("roll-name-button")  # GD-26
    if roll_button is not None:
        roll_button.addEventListener("click", create_proxy(on_roll_name))
    for category in CATEGORIES:  # D-20: the net-funds chip follows hover and keyboard focus
        invest_el = document.getElementById(f"{category}-invest-button")
        if invest_el is not None:
            for event_name, name in (("mouseenter", category), ("focus", category), ("mouseleave", ""), ("blur", "")):
                invest_el.addEventListener(event_name, create_proxy(_make_net_funds_handler(name)))
    pin_select = document.getElementById("afford-pin-select")  # D-19
    if pin_select is not None:
        load_afford_pin()
        pin_select.addEventListener("change", create_proxy(on_afford_pin_change))
    for why_name in ("acidity", "funds"):  # D-28
        why_button = document.getElementById(f"why-{why_name}-button")
        if why_button is not None:
            why_button.addEventListener("click", create_proxy(on_why_button(why_name)))
    for market_id, market_accept in (("market-accept-button", True), ("market-decline-button", False)):  # GD-8
        market_button = document.getElementById(market_id)
        if market_button is not None:
            market_button.addEventListener("click", create_proxy(on_market_answer(market_accept)))
    for workshop_key in WORKSHOP_DEFAULTS:  # D-5
        workshop_slider = document.getElementById(f"workshop-{workshop_key}")
        if workshop_slider is not None:
            workshop_slider.addEventListener("input", create_proxy(on_workshop_slider(workshop_key)))
    for workshop_id, workshop_handler in (("workshop-apply-button", on_workshop_apply), ("workshop-reset-button", on_workshop_reset)):
        workshop_button = document.getElementById(workshop_id)
        if workshop_button is not None:
            workshop_button.addEventListener("click", create_proxy(workshop_handler))
    for crew_id in CREW:  # GD-11
        crew_button = document.getElementById(f"crew-{crew_id}-button")
        if crew_button is not None:
            crew_button.addEventListener("click", create_proxy(on_crew_button(crew_id)))
    autosave_list = document.getElementById("autosave-list")  # D-11
    if autosave_list is not None:
        autosave_list.addEventListener("click", create_proxy(on_autosave_click))
    postcard_button = document.getElementById("postcard-button")  # GD-9
    if postcard_button is not None:
        postcard_button.addEventListener("click", create_proxy(on_make_postcard))
    for brace_kind in ("barriers", "stockpile", "evacuate"):  # GD-3
        brace_button = document.getElementById(f"brace-{brace_kind}-button")
        if brace_button is not None:
            brace_button.addEventListener("click", create_proxy(on_brace_button(brace_kind)))
    chess_toggle = document.getElementById("chess-toggle-button")  # GD-4
    if chess_toggle is not None:
        chess_toggle.addEventListener("click", create_proxy(on_toggle_chess))
    acid_toggle = document.getElementById("acid-boss-toggle-button")  # GD-12
    if acid_toggle is not None:
        acid_toggle.addEventListener("click", create_proxy(on_toggle_acid_boss))
    acid_brace = document.getElementById("acid-boss-brace-button")
    if acid_brace is not None:
        acid_brace.addEventListener("click", create_proxy(on_brace))
    theme_select = document.getElementById("scene-theme-select")  # GD-22
    if theme_select is not None:
        theme_select.addEventListener("change", create_proxy(on_scene_theme_change))
    goal_select = document.getElementById("goal-select")  # GD-19
    if goal_select is not None:
        goal_select.addEventListener("change", create_proxy(on_goal_change))
    document.getElementById("set-baseline-button").addEventListener(
        "click", create_proxy(on_set_baseline)
    )
    # Explicit, not just relying on index.html's `hidden` attribute -- the
    # toast/banner elements are only otherwise touched by their own show/
    # hide logic (unlike every *panel*, which gets its `hidden` state
    # re-set on every render()), so they need their own starting state
    # set here rather than trusting markup alone.
    toast = document.getElementById("achievement-toast")
    if toast is not None:
        toast.hidden = True
    _resync_previous_flooded_rows()
    almanac_resync()
    render()


_load_graph_prefs()
runstate.almanac = _load_almanac()
setup()
