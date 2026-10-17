"""Aftermath — Climate Adaptation & Resilience Game.

Runs in-browser via Pyodide. A repeated-short-run core loop: a fixed
schedule of extreme weather (and other resilience-relevant) events,
resource allocation between events (resilience vs. growth investment),
and damage resolution, feeding a persistent cross-run skill tree and
"how far you've come" run comparison. See CLAUDE.md for the full
milestone history.
"""

import importlib
import sys
import types

from js import document
from pyodide.ffi import create_proxy

import aftermath_runstate as runstate
from aftermath_achievements import _seed_achievement_toast_baseline
from aftermath_actions import leave_challenge, start_new_run
from aftermath_bonuses import load_cached_community_resilience
from aftermath_challenges import build_library_buttons
from aftermath_codex import INVEST_STEPS
from aftermath_handlers import (
    _make_pin_handler, _make_unlock_handler, on_builder_clear, on_builder_draft_event, on_builder_save,
    on_builder_saved_event, on_copy_chronicle, on_copy_run_summary, on_export_progress, on_founding_begin,
    on_founding_event, on_import_progress, on_invest_growth, on_invest_resilience, on_neighbour_aid_setting,
    on_past_runs_controls_change, on_past_runs_event, on_preset_apply, on_preset_from_turn,
    on_preset_list_event, on_preset_save, on_preset_select, on_reset_skill_tree, on_resolve_event,
    on_run_timer_setting, on_save_health_export, on_scenario_change, on_settlement_name_change,
    on_skill_filter_clear, on_skill_map_pin, on_skill_map_search, on_skill_map_unlock, on_skill_move,
    on_skill_move_select, on_skill_search, on_toggle_achievements, on_toggle_changelog, on_toggle_chronicle,
    on_toggle_codex, on_toggle_ghost, on_toggle_info_page, on_toggle_mentor, on_toggle_past_runs,
    on_toggle_stats, on_undo_allocation,
)
from aftermath_pastruns import load_mentor_enabled
from aftermath_persist import _el, probe_storage
from aftermath_renderer import _make_step_handler, render
from aftermath_rules import SKILLS
from aftermath_skillmap import build_skill_map, clear_skill_map_selection
from aftermath_tools import build_skill_filter_chips

# ---------------------------------------------------------------------------
# File map: this file is the entry point and the wiring. Everything else lives in the modules named in
# _PART_NAMES, in dependency order (a module only imports from the ones before it). See "File map" in
# games/aftermath/CLAUDE.md for what each one holds.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "aftermath_runstate",
    "aftermath_rules",
    "aftermath_persist",
    "aftermath_skilltree",
    "aftermath_bonuses",
    "aftermath_achievements",
    "aftermath_pastruns",
    "aftermath_panels",
    "aftermath_codex",
    "aftermath_runview",
    "aftermath_tools",
    "aftermath_challenges",
    "aftermath_skillmap",
    "aftermath_chronicle",
    "aftermath_flourish",
    "aftermath_model_run",
    "aftermath_renderer",
    "aftermath_actions",
    "aftermath_savestate",
    "aftermath_handlers",
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
    """game.state & co. live in aftermath_runstate (they get replaced while playing), so reads go there; a write to
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


def _listen(element_id, event_name, handler):
    element = _el(element_id)
    if element is not None:
        element.addEventListener(event_name, create_proxy(handler))


def _wire_round3_batch2():
    """Event wiring and one-time construction for E-19, E-25, E-30, E-13 and E-4 (each tolerates a
    cached older page that lacks the element)."""
    probe_storage()
    build_skill_filter_chips()
    build_library_buttons()
    _listen("skill-search-input", "input", on_skill_search)
    _listen("skill-filter-clear", "click", on_skill_filter_clear)
    _listen("preset-save-button", "click", on_preset_save)
    _listen("preset-from-turn-button", "click", on_preset_from_turn)
    _listen("preset-apply-button", "click", on_preset_apply)
    _listen("preset-select", "change", on_preset_select)
    for event_name in ("click",):
        _listen("preset-list", event_name, on_preset_list_event)
        _listen("builder-draft", event_name, on_builder_draft_event)
        _listen("builder-saved-list", event_name, on_builder_saved_event)
    _listen("builder-clear-button", "click", on_builder_clear)
    _listen("builder-save-button", "click", on_builder_save)
    _listen("save-health-export-button", "click", on_save_health_export)
    _listen("challenge-leave-button", "click", leave_challenge)
    _listen("skill-map-search-input", "input", on_skill_map_search)
    _listen("skill-map-filter-clear", "click", on_skill_filter_clear)
    _listen("skill-map-clear-button", "click", clear_skill_map_selection)
    _listen("skill-map-unlock-button", "click", on_skill_map_unlock)
    _listen("skill-map-pin-button", "click", on_skill_map_pin)
    build_skill_map()  # E-2
    _listen("founding-begin-button", "click", on_founding_begin)
    _listen("founding-skills", "click", on_founding_event)
    _listen("skill-move-button", "click", on_skill_move)
    _listen("skill-move-from", "change", on_skill_move_select)
    _listen("skill-move-to", "change", on_skill_move_select)
    _listen("neighbour-aid-checkbox", "change", on_neighbour_aid_setting)  # R-31
    _listen("run-timer-checkbox", "change", on_run_timer_setting)  # GE-23
    _listen("chronicle-toggle-button", "click", on_toggle_chronicle)  # E-7
    _listen("chronicle-copy-button", "click", on_copy_chronicle)


def setup():
    document.getElementById("resilience-invest-button").addEventListener(
        "click", create_proxy(on_invest_resilience)
    )
    document.getElementById("growth-invest-button").addEventListener(
        "click", create_proxy(on_invest_growth)
    )
    document.getElementById("resolve-event-button").addEventListener(
        "click", create_proxy(on_resolve_event)
    )
    runstate.mentor_enabled = load_mentor_enabled()
    document.getElementById("mentor-toggle").addEventListener("change", create_proxy(on_toggle_mentor))
    ghost_toggle = _el("ghost-toggle")
    if ghost_toggle is not None:
        ghost_toggle.addEventListener("change", create_proxy(on_toggle_ghost))
    document.getElementById("scenario-select").addEventListener("change", create_proxy(on_scenario_change))
    document.getElementById("new-run-button").addEventListener(
        "click", create_proxy(start_new_run)
    )
    for skill_id in SKILLS:
        document.getElementById(f"skill-{skill_id}-unlock-button").addEventListener(
            "click", create_proxy(_make_unlock_handler(skill_id))
        )
        document.getElementById(f"skill-{skill_id}-pin-button").addEventListener(
            "click", create_proxy(_make_pin_handler(skill_id))
        )
    document.getElementById("settlement-name-input").addEventListener(
        "change", create_proxy(on_settlement_name_change)
    )
    document.getElementById("settlement-name-input").value = runstate.meta["settlement_name"]
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("past-runs-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_past_runs)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    # E-22 / E-21 / E-20: one delegated handler for the whole Past Runs list, plus the controls.
    past_runs_list = document.getElementById("past-runs-list")
    if past_runs_list is not None:
        for event_name in ("click", "change"):
            past_runs_list.addEventListener(event_name, create_proxy(on_past_runs_event))
    for control_id in ("past-runs-sort", "past-runs-filter", "past-runs-archived"):
        control = document.getElementById(control_id)
        if control is not None:
            control.addEventListener("change", create_proxy(on_past_runs_controls_change))
    document.getElementById("reset-skill-tree-button").addEventListener(
        "click", create_proxy(on_reset_skill_tree)
    )
    document.getElementById("progress-export-button").addEventListener(
        "click", create_proxy(on_export_progress)
    )
    document.getElementById("progress-import-button").addEventListener(
        "click", create_proxy(on_import_progress)
    )
    document.getElementById("undo-allocation-button").addEventListener(
        "click", create_proxy(on_undo_allocation)
    )
    for step in INVEST_STEPS:
        button_id = f"step-{'max' if step == 'max' else 'x' + str(step)}-button"
        document.getElementById(button_id).addEventListener("click", create_proxy(_make_step_handler(step)))
    document.getElementById("codex-toggle-button").addEventListener("click", create_proxy(on_toggle_codex))
    document.getElementById("stats-toggle-button").addEventListener("click", create_proxy(on_toggle_stats))
    document.getElementById("copy-run-summary-button").addEventListener(
        "click", create_proxy(on_copy_run_summary)
    )
    document.getElementById("copy-run-summary-area").hidden = True
    load_cached_community_resilience()  # R-31: the last community figure this browser fetched
    _wire_round3_batch2()
    document.getElementById("achievement-toast").hidden = True
    document.getElementById("skill-unlock-toast").hidden = True
    render()
    _seed_achievement_toast_baseline()


setup()
