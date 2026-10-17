"""Thaw — Permafrost Feedback Loop Game.

Runs in-browser via Pyodide. Milestone 1: the background trajectory and
core loop — global temperature rises on a fixed schedule each round,
independent of the player, while the player allocates regional resources
across output/preserve/monitor. The permafrost melt + methane feedback
loop (the entire point of this game) lands in Milestone 2.
"""

import importlib
import sys
import types

from js import document
from pyodide.ffi import create_proxy

import thaw_runstate as runstate
from thaw_achievements import _seed_achievement_toast_baseline, load_skins
from thaw_handlers import (
    _make_board_sort_handler, _make_carbon_handler, _make_custom_preset_handler, _make_focus_invest_handler,
    _make_invest_handler, _make_policy_stance_handler, _make_preset_handler, _make_rescue_handler,
    _make_save_preset_handler, _make_secondary_invest_handler, _make_strategy_label_handler,
    on_advance_round, on_compare_change, on_confirm_threshold_change, on_copy_highlights, on_copy_log,
    on_copy_settings_code, on_dismiss_load_notice, on_focus_region_change, on_focus_rescue,
    on_lock_forecast, on_log_filter, on_log_list_click, on_log_search, on_open_crate, on_planner_change,
    on_planner_reset, on_rate_inspector_region_change, on_replay_change, on_replay_step,
    on_restore_settings_code, on_routing_change, on_send_convoy, on_settings_reset_click, on_skin_change,
    on_temp_unit_change, on_toggle_achievements, on_toggle_archive, on_toggle_changelog,
    on_toggle_climate_scientist, on_toggle_community_compare, on_toggle_framing, on_toggle_hard_mode,
    on_toggle_hold_the_line, on_toggle_info_page, on_toggle_long_game, on_toggle_worst_case_region, on_undo,
)
from thaw_model import SECONDARY_REGIONS
from thaw_presets import PRESET_WEIGHTS, load_confirm_threshold, preset_tooltip_text
from thaw_renderer import render
from thaw_rules import CATEGORIES, POLICY_STANCES
from thaw_sciencelog import LOG_FILTERS
from thaw_views import BOARD_COLUMNS

# ---------------------------------------------------------------------------
# File map: this file is the entry point and the wiring. Everything else lives in the modules named in
# _PART_NAMES, in dependency order (a module only imports from the ones before it). See "File map" in
# games/thaw/CLAUDE.md for what each one holds.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "thaw_runstate",
    "thaw_rules",
    "thaw_model",
    "thaw_bridge",
    "thaw_sciencelog",
    "thaw_presets",
    "thaw_graphs",
    "thaw_mechanics",
    "thaw_records",
    "thaw_achievements",
    "thaw_panels",
    "thaw_readouts",
    "thaw_runs",
    "thaw_views",
    "thaw_saveparts",
    "thaw_timeline",
    "thaw_flavour",
    "thaw_pace",
    "thaw_settingscode",
    "thaw_savestate",
    "thaw_renderer",
    "thaw_loading",
    "thaw_handlers",
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
    """game.hard_mode & co. live in thaw_runstate (they get replaced while playing), so reads go there; a write to
    any name copies to every module that holds the name, so monkeypatching game._write_local_storage_item or
    setting game.carbon_bank = 5 still changes what the code uses."""

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
    runstate.confirm_threshold = load_confirm_threshold()
    load_skins()  # GG-18
    document.getElementById("crate-open-button").addEventListener("click", create_proxy(on_open_crate))
    document.getElementById("skin-select").addEventListener("change", create_proxy(on_skin_change))
    document.getElementById("confirm-threshold-select").addEventListener(
        "change", create_proxy(on_confirm_threshold_change)
    )
    document.getElementById("hard-mode-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_hard_mode)
    )
    document.getElementById("settings-code-copy-button").addEventListener(
        "click", create_proxy(on_copy_settings_code)
    )
    document.getElementById("settings-code-restore-button").addEventListener(
        "click", create_proxy(on_restore_settings_code)
    )
    document.getElementById("settings-reset-button").addEventListener(
        "click", create_proxy(on_settings_reset_click)
    )
    for key in ("a", "b", "c"):
        document.getElementById(f"carbon-bank-{key}-button").addEventListener(
            "click", create_proxy(_make_carbon_handler(key))
        )
    document.getElementById("archive-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_archive)
    )
    document.getElementById("routing-send-button").addEventListener(
        "click", create_proxy(on_send_convoy)
    )
    for select_id in ("routing-source", "routing-dest"):
        document.getElementById(select_id).addEventListener("change", create_proxy(on_routing_change))
    document.getElementById("undo-button").addEventListener("click", create_proxy(on_undo))
    document.getElementById("load-notice-dismiss").addEventListener("click", create_proxy(on_dismiss_load_notice))
    document.getElementById("replay-slider").addEventListener("input", create_proxy(on_replay_change))
    document.getElementById("replay-slider").addEventListener("change", create_proxy(on_replay_change))
    for name, delta in (("first", "first"), ("back", -1), ("forward", 1), ("last", "last")):
        document.getElementById(f"replay-{name}").addEventListener("click", create_proxy(on_replay_step(delta)))
    document.getElementById("rate-inspector-region").addEventListener(
        "change", create_proxy(on_rate_inspector_region_change)
    )
    for name in LOG_FILTERS:
        document.getElementById(f"log-filter-{name}").addEventListener("click", create_proxy(on_log_filter(name)))
    document.getElementById("focus-region").addEventListener("change", create_proxy(on_focus_region_change))
    for name in ("planner-region", "planner-output", "planner-preserve", "planner-monitor", "planner-repeat"):
        document.getElementById(name).addEventListener("change", create_proxy(on_planner_change))
        document.getElementById(name).addEventListener("input", create_proxy(on_planner_change))
    document.getElementById("planner-reset-button").addEventListener("click", create_proxy(on_planner_reset))
    for category in CATEGORIES:
        document.getElementById(f"focus-invest-{category}").addEventListener(
            "click", create_proxy(_make_focus_invest_handler(category))
        )
    document.getElementById("focus-rescue-button").addEventListener("click", create_proxy(on_focus_rescue))
    for key, _label in BOARD_COLUMNS:
        document.getElementById(f"board-sort-{key}").addEventListener(
            "click", create_proxy(_make_board_sort_handler(key))
        )
    document.getElementById("log-search").addEventListener("input", create_proxy(on_log_search))
    document.getElementById("log-export-button").addEventListener("click", create_proxy(on_copy_log))
    document.getElementById("science-log-list").addEventListener("click", create_proxy(on_log_list_click))
    document.getElementById("highlights-copy-button").addEventListener(
        "click", create_proxy(on_copy_highlights)
    )
    document.getElementById("long-game-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_long_game)
    )
    document.getElementById("hold-line-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_hold_the_line)
    )
    for select_id in ("compare-run-a", "compare-run-b"):
        document.getElementById(select_id).addEventListener("change", create_proxy(on_compare_change))
    document.getElementById("temp-unit-select").addEventListener(
        "change", create_proxy(on_temp_unit_change)
    )
    document.getElementById("framing-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_framing)
    )
    document.getElementById("forecast-lock-button").addEventListener(
        "click", create_proxy(on_lock_forecast)
    )
    for key in POLICY_STANCES:
        document.getElementById(f"policy-stance-{key}-button").addEventListener(
            "click", create_proxy(_make_policy_stance_handler(key))
        )
    document.getElementById("rescue-button").addEventListener(
        "click", create_proxy(_make_rescue_handler(""))
    )
    for prefix in SECONDARY_REGIONS:
        document.getElementById(f"{prefix}-rescue-button").addEventListener(
            "click", create_proxy(_make_rescue_handler(prefix))
        )
    for category in CATEGORIES:
        document.getElementById(f"{category}-invest-button").addEventListener(
            "click", create_proxy(_make_invest_handler(category))
        )
    for prefix in SECONDARY_REGIONS:
        for category in CATEGORIES:
            document.getElementById(f"{prefix}-{category}-invest-button").addEventListener(
                "click", create_proxy(_make_secondary_invest_handler(prefix, category))
            )
        for preset_name in PRESET_WEIGHTS:
            preset_button = document.getElementById(f"{prefix}-preset-{preset_name}-button")
            preset_button.addEventListener(
                "click", create_proxy(_make_preset_handler(prefix, preset_name))
            )
            # Onboarding-tooltip audit: presets were added (G11) after the
            # tutorial/How to Play copy was written, so a returning player
            # has no permanent explanation of what a preset click actually
            # does. title= is set once here since the text is static per
            # preset, not state-dependent.
            preset_button.title = preset_tooltip_text(preset_name)
        # G-20: the shared custom slot (its label, tooltip and enabled state follow the saved mix).
        document.getElementById(f"{prefix}-preset-custom-button").addEventListener(
            "click", create_proxy(_make_custom_preset_handler(prefix))
        )
        document.getElementById(f"{prefix}-preset-save-button").addEventListener(
            "click", create_proxy(_make_save_preset_handler(prefix))
        )
        # G4: "input" (not "change") so the label updates live as the
        # player types, without waiting for the field to lose focus.
        document.getElementById(f"{prefix}-strategy-label-input").addEventListener(
            "input", create_proxy(_make_strategy_label_handler(prefix))
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
    document.getElementById("worst-case-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_worst_case_region)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("community-compare-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_community_compare)
    )
    document.getElementById("climate-scientist-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_climate_scientist)
    )
    # Belt-and-suspenders: the toast starts hidden via the static
    # `hidden` attribute in index.html, but every other stateful element
    # in this file has its shown/hidden state actively driven by code
    # rather than left to rely on markup alone (matches Continuum's own
    # documented fix for exactly this gap).
    document.getElementById("achievement-toast").hidden = True
    render()
    _seed_achievement_toast_baseline()


setup()
