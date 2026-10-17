"""Grid — Energy Transition Game.

Runs in-browser via Pyodide. Turn-based loop across demand growth, funds,
six plant types to build/retire/maintain, capacity-based revenue on round
advance, an emissions meter and renewable cost curve, and emissions-driven
disruption events plus infrastructure aging — see CLAUDE.md's milestone
table for how each system landed.
"""

import importlib
import sys
import types

from js import document
from pyodide.ffi import create_proxy

import grid_runstate as runstate
from grid_rules import GENERATION_TYPES, PLANT_TYPES
from grid_state import GridState
from grid_sandbox_state import SANDBOX_BALANCE
from grid_career_data import _default_career, _sync_perks, load_career_from_storage
from grid_prefs import load_prefs_from_storage
from grid_panels import on_toggle_changelog, on_toggle_info_page, on_toggle_weather_log
from grid_views import TREND_CHECKBOX_PREFS
from grid_announce import _seed_achievement_toast_baseline
from grid_summary import on_toggle_summary_panel
from grid_achievement_cards import on_toggle_achievements
from grid_fleet import FLEET_COLUMNS
from grid_callouts import _make_mix_hover_handler
from grid_renderer import render
from grid_handlers_panels import (
    _make_fleet_sort_handler, _make_pref_checkbox_handler, _make_pref_select_handler, on_accept_grant,
    on_apply_run_seed, on_copy_run_seed, on_decline_grant, on_export_career, on_finish_run, on_import_career,
    on_peek_forecast, on_rank_theme_change, on_reset_career, on_reset_confirmations, on_reset_prefs,
    on_slot_clear, on_slot_load, on_slot_new, on_slot_save, on_slot_select, on_start_option_change,
    on_toggle_career, on_toggle_ironman, on_undo_build,
)
from grid_handlers_play import (
    _make_build_handler, _make_maintain_handler, _make_maintenance_schedule_handler, _make_plant_key_handler,
    _make_retire_handler, _make_sandbox_balance_handler, on_advance_round, on_auto_advance,
    on_connect_regional_grid, on_cycle_arbitrage_mode, on_cycle_scenario, on_decline_policy,
    on_difficulty_preset_change, on_dismiss_maintain_callout, on_dismiss_renewable_milestone,
    on_dismiss_retire_callout, on_enact_carbon_pricing, on_enact_renewable_subsidy, on_invest_demand_response,
    on_real_grid_change, on_sandbox_balance_reset, on_shadow_change, on_toggle_steeper_demand,
    on_toggle_weather_variability,
)

# ---------------------------------------------------------------------------
# File map: this file is the entry point and the wiring. Everything else lives in the modules named in
# _PART_NAMES, in dependency order (a module only imports from the ones before it). See "File map" in
# games/grid/CLAUDE.md for what each one holds. The same list (as .py file names) is GRID_PY_MODULES in boot.js.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "grid_rules",
    "grid_runstate",
    "grid_state_round",
    "grid_state_extras",
    "grid_state",
    "grid_sandbox_state",
    "grid_whatif",
    "grid_career_data",
    "grid_career_actions",
    "grid_prefs",
    "grid_achievements",
    "grid_shadow",
    "grid_savegame",
    "grid_trend",
    "grid_panels",
    "grid_views",
    "grid_messages",
    "grid_announce",
    "grid_difficulty",
    "grid_summary",
    "grid_skyline",
    "grid_achievement_cards",
    "grid_runs",
    "grid_sandbox",
    "grid_fleet",
    "grid_runsetup",
    "grid_coach",
    "grid_arbitrage",
    "grid_schematic",
    "grid_realgrid",
    "grid_slots",
    "grid_gridley",
    "grid_callouts",
    "grid_advance",
    "grid_careerpanel",
    "grid_renderer",
    "grid_loading",
    "grid_handlers_panels",
    "grid_handlers_play",
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
    """game.state & co. live in runstate (they get replaced while playing), so reads go there; a write to any
    name copies to every module that holds the name, so monkeypatching a function or setting
    game.career_open = True still changes what the code uses."""

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

# Start-up steps that ran at import time in the single-file game.py, in the same order. Their first values need code
# from several modules, so the matching variables in grid_runstate start as None and are filled in here.
runstate.state = GridState()

runstate.career = _default_career()


def setup():
    runstate.career = load_career_from_storage()
    runstate.prefs = load_prefs_from_storage()
    _sync_perks()
    runstate.state.apply_scenario("standard")
    # index.html already marks this hidden via the `hidden` attribute, but
    # that markup default doesn't exist for the pytest fake-DOM harness (a
    # FakeElement starts with hidden=False) -- setting it explicitly here
    # keeps both environments consistent and costs nothing in a real
    # browser, where it's already true.
    document.getElementById("achievement-toast").hidden = True
    document.getElementById("disruption-toast").hidden = True
    for plant_type in PLANT_TYPES:
        document.getElementById(f"{plant_type}-build-button").addEventListener(
            "click", create_proxy(_make_build_handler(plant_type))
        )
        document.getElementById(f"{plant_type}-retire-button").addEventListener(
            "click", create_proxy(_make_retire_handler(plant_type))
        )
        document.getElementById(f"{plant_type}-maintain-button").addEventListener(
            "click", create_proxy(_make_maintain_handler(plant_type))
        )
        document.getElementById(f"{plant_type}-maintenance-schedule-select").addEventListener(
            "change", create_proxy(_make_maintenance_schedule_handler(plant_type))
        )
    document.getElementById("settings-reset-button").addEventListener("click", create_proxy(on_reset_prefs))
    document.getElementById("confirm-reset-button").addEventListener("click", create_proxy(on_reset_confirmations))
    document.getElementById("pref-coach").addEventListener("change", create_proxy(_make_pref_checkbox_handler("coach")))
    document.getElementById("pref-gauge-effects").addEventListener(
        "change", create_proxy(_make_pref_checkbox_handler("gauge_effects"))
    )
    document.getElementById("rank-theme-select").addEventListener("change", create_proxy(on_rank_theme_change))
    document.getElementById("pref-gridley").addEventListener(
        "change", create_proxy(_make_pref_checkbox_handler("gridley"))
    )
    document.getElementById("pref-skyline").addEventListener(
        "change", create_proxy(_make_pref_checkbox_handler("skyline"))
    )
    document.getElementById("pref-number-format").addEventListener(
        "change", create_proxy(_make_pref_select_handler("number_format"))
    )
    document.getElementById("pref-unit").addEventListener("change", create_proxy(_make_pref_select_handler("unit")))
    for balance_key in SANDBOX_BALANCE:
        document.getElementById(f"sandbox-bal-{balance_key.replace('_', '-')}").addEventListener(
            "input", create_proxy(_make_sandbox_balance_handler(balance_key))
        )
    document.getElementById("slot-select").addEventListener("change", create_proxy(on_slot_select))
    document.getElementById("slot-save-button").addEventListener("click", create_proxy(on_slot_save))
    document.getElementById("slot-load-button").addEventListener("click", create_proxy(on_slot_load))
    document.getElementById("slot-new-button").addEventListener("click", create_proxy(on_slot_new))
    document.getElementById("slot-clear-button").addEventListener("click", create_proxy(on_slot_clear))
    document.getElementById("sandbox-bal-reset").addEventListener("click", create_proxy(on_sandbox_balance_reset))
    document.getElementById("pref-round-animation").addEventListener(
        "change", create_proxy(_make_pref_checkbox_handler("round_animation"))
    )
    document.getElementById("pref-unlock-flash").addEventListener(
        "change", create_proxy(_make_pref_checkbox_handler("unlock_flash"))
    )
    document.getElementById("pref-chart-theme").addEventListener(
        "change", create_proxy(_make_pref_select_handler("chart_theme"))
    )
    for fleet_key, _label in FLEET_COLUMNS:
        document.getElementById(f"fleet-sort-{fleet_key}").addEventListener(
            "click", create_proxy(_make_fleet_sort_handler(fleet_key))
        )
    for element_id, pref_key in TREND_CHECKBOX_PREFS:
        document.getElementById(element_id).addEventListener(
            "change", create_proxy(_make_pref_checkbox_handler(pref_key))
        )
    document.getElementById("shadow-select").addEventListener("change", create_proxy(on_shadow_change))
    document.getElementById("real-grid-select").addEventListener("change", create_proxy(on_real_grid_change))
    document.getElementById("regional-grid-connect-button").addEventListener(
        "click", create_proxy(on_connect_regional_grid)
    )
    document.getElementById("advance-round-button").addEventListener(
        "click", create_proxy(on_advance_round)
    )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("summary-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_summary_panel)
    )
    document.getElementById("renewable-milestone-dismiss-button").addEventListener(
        "click", create_proxy(on_dismiss_renewable_milestone)
    )
    document.getElementById("retire-callout-dismiss-button").addEventListener(
        "click", create_proxy(on_dismiss_retire_callout)
    )
    document.getElementById("maintain-callout-dismiss-button").addEventListener(
        "click", create_proxy(on_dismiss_maintain_callout)
    )
    document.getElementById("steeper-demand-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_steeper_demand)
    )
    document.getElementById("weather-variability-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_weather_variability)
    )
    document.getElementById("scenario-toggle-button").addEventListener(
        "click", create_proxy(on_cycle_scenario)
    )
    document.getElementById("weather-log-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_weather_log)
    )
    document.getElementById("career-toggle-button").addEventListener("click", create_proxy(on_toggle_career))
    document.getElementById("career-finish-button").addEventListener("click", create_proxy(on_finish_run))
    for plant_type in PLANT_TYPES:
        document.getElementById(f"{plant_type}-row").addEventListener(
            "keydown", create_proxy(_make_plant_key_handler(plant_type))
        )
    for plant_type in GENERATION_TYPES:
        mix_row = document.getElementById(f"{plant_type}-mix-row")
        for event_name, entering in (("mouseenter", True), ("focus", True), ("mouseleave", False), ("blur", False)):
            mix_row.addEventListener(event_name, create_proxy(_make_mix_hover_handler(plant_type, entering)))
    document.getElementById("start-option-select").addEventListener("change", create_proxy(on_start_option_change))
    document.getElementById("run-seed-apply-button").addEventListener("click", create_proxy(on_apply_run_seed))
    document.getElementById("run-seed-copy-button").addEventListener("click", create_proxy(on_copy_run_seed))
    document.getElementById("ironman-toggle-button").addEventListener("click", create_proxy(on_toggle_ironman))
    document.getElementById("undo-build-button").addEventListener("click", create_proxy(on_undo_build))
    document.getElementById("grant-accept-button").addEventListener("click", create_proxy(on_accept_grant))
    document.getElementById("grant-decline-button").addEventListener("click", create_proxy(on_decline_grant))
    document.getElementById("peek-forecast-button").addEventListener("click", create_proxy(on_peek_forecast))
    document.getElementById("career-export-button").addEventListener("click", create_proxy(on_export_career))
    document.getElementById("career-import-button").addEventListener("click", create_proxy(on_import_career))
    document.getElementById("career-reset-button").addEventListener("click", create_proxy(on_reset_career))
    document.getElementById("auto-advance-button").addEventListener("click", create_proxy(on_auto_advance))
    document.getElementById("difficulty-preset-select").addEventListener(
        "change", create_proxy(on_difficulty_preset_change)
    )
    document.getElementById("arbitrage-mode-button").addEventListener(
        "click", create_proxy(on_cycle_arbitrage_mode)
    )
    document.getElementById("demand-response-button").addEventListener(
        "click", create_proxy(on_invest_demand_response)
    )
    document.getElementById("policy-accept-carbon-pricing-button").addEventListener(
        "click", create_proxy(on_enact_carbon_pricing)
    )
    document.getElementById("policy-accept-renewable-subsidy-button").addEventListener(
        "click", create_proxy(on_enact_renewable_subsidy)
    )
    document.getElementById("policy-decline-button").addEventListener(
        "click", create_proxy(on_decline_policy)
    )
    render()
    _seed_achievement_toast_baseline()


setup()
