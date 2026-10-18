"""Drift — Climate Migration & Displacement Game.

Runs in-browser via Pyodide. Milestone 1: the core allocation loop — a
receiving region invests its budget across housing, integration
services, and infrastructure capacity, round by round. Displacement
pressure, strain, integration payoff, and composite scoring land in
later milestones; this milestone is just "can the region build
capacity at all."
"""

import importlib
import sys
import types

import drift_runstate as runstate
from js import document
from pyodide.ffi import create_proxy

from drift_collection import SKINS, _seed_achievement_toast_baseline
from drift_handlers import (
    _make_council_handler, _make_invest_handler, _make_legacy_handler, _make_neighbor_invest_handler,
    _make_policy_handler, _make_skin_handler, _make_template_apply_handler, _make_template_rename_handler,
    _make_template_save_handler, _make_trend_layer_handler, _make_trend_range_handler, on_advance_round,
    on_autopilot_change, on_autopilot_run, on_brace, on_copy_ledger_csv, on_copy_summary,
    on_dismiss_load_note, on_ledger_filter, on_ledger_sort, on_open_neighbor, on_play_rounds, on_reallocate,
    on_region_name_input, on_reset_round, on_rewind, on_support_neighbor, on_toggle_accelerated_severity,
    on_toggle_achievements, on_toggle_calendar, on_toggle_changelog, on_toggle_coda, on_toggle_collection,
    on_toggle_crisis_start, on_toggle_info_page, on_toggle_ledger, setup_batch3,
)
from drift_messages import CODA_LEGACY_CHOICES
from drift_pages import update_changelog_display
from drift_plans import TEMPLATE_SLOTS
from drift_renderer import render
from drift_rules import CAPACITY_TYPES, COUNCIL_BRANCHES, POLICIES
from drift_trendgraph import TREND_LAYER_ORDER, TREND_RANGES
from drift_undo import _reset_undo_state

# ---------------------------------------------------------------------------
# File map: this file is the entry point and the wiring. Everything else lives in the modules named in
# _PART_NAMES, in dependency order (a module only imports from the ones before it). See "File map" in
# games/drift/CLAUDE.md for what each one holds.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "drift_runstate",
    "drift_rules",
    "drift_model_region",
    "drift_regional",
    "drift_trendgraph",
    "drift_visuals",
    "drift_messages",
    "drift_achievements",
    "drift_pages",
    "drift_ledger",
    "drift_calendar",
    "drift_collection",
    "drift_undo",
    "drift_tiers",
    "drift_plans",
    "drift_assist",
    "drift_settings",
    "drift_loading",
    "drift_report",
    "drift_newsview",
    "drift_renderer",
    "drift_handlers",
    "drift_savestate",
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
    """game.state & co. live in drift_runstate (they get replaced while playing), so reads go there; a write to
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
    # index.html already marks this hidden via the `hidden` attribute, but
    # that markup default doesn't exist for the pytest fake-DOM harness (a
    # FakeElement starts with hidden=False) -- setting it explicitly here
    # keeps both environments consistent and costs nothing in a real
    # browser, where it's already true.
    document.getElementById("achievement-toast").hidden = True
    document.getElementById("advance-round-button").addEventListener(
        "click", create_proxy(on_advance_round)
    )
    for capacity_type in CAPACITY_TYPES:
        document.getElementById(f"{capacity_type}-invest-button").addEventListener(
            "click", create_proxy(_make_invest_handler(capacity_type))
        )
    for policy in POLICIES:
        document.getElementById(f"policy-{policy.replace('_', '-')}-button").addEventListener(
            "click", create_proxy(_make_policy_handler(policy))
        )
    document.getElementById("coda-button").addEventListener(
        "click", create_proxy(on_toggle_coda)
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
    document.getElementById("accelerated-severity-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_accelerated_severity)
    )
    document.getElementById("crisis-start-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_crisis_start)
    )
    document.getElementById("realloc-button").addEventListener("click", create_proxy(on_reallocate))
    document.getElementById("neighbor-open-button").addEventListener("click", create_proxy(on_open_neighbor))
    document.getElementById("neighbor-support-button").addEventListener("click", create_proxy(on_support_neighbor))
    for capacity_type in CAPACITY_TYPES:
        document.getElementById(f"neighbor-{capacity_type}-button").addEventListener(
            "click", create_proxy(_make_neighbor_invest_handler(capacity_type))
        )
    document.getElementById("region-name-input").addEventListener(
        "change", create_proxy(on_region_name_input)
    )
    for legacy_choice in CODA_LEGACY_CHOICES:
        document.getElementById(f"coda-legacy-{legacy_choice}-button").addEventListener(
            "click", create_proxy(_make_legacy_handler(legacy_choice))
        )
    for button_id, handler in (
        ("reset-round-button", on_reset_round),
        ("rewind-button", on_rewind),
        ("play-rounds-button", on_play_rounds),
        ("ledger-toggle-button", on_toggle_ledger),
        ("collection-toggle-button", on_toggle_collection),
        ("copy-ledger-csv-button", on_copy_ledger_csv),
        ("calendar-toggle-button", on_toggle_calendar),
        ("calendar-brace-button", on_brace),
        ("autopilot-run-button", on_autopilot_run),
        ("copy-summary-button", on_copy_summary),
    ):
        document.getElementById(button_id).addEventListener("click", create_proxy(handler))
    for branch in COUNCIL_BRANCHES:
        document.getElementById(f"council-pick-{branch}").addEventListener(
            "click", create_proxy(_make_council_handler(branch))
        )
    for select_id in (
        "autopilot-share-select", "autopilot-surplus-select", "autopilot-reserve-select", "autopilot-rounds-select",
    ):
        document.getElementById(select_id).addEventListener("change", create_proxy(on_autopilot_change))
    document.getElementById("load-note-dismiss").addEventListener("click", create_proxy(on_dismiss_load_note))
    for slot in range(TEMPLATE_SLOTS):
        document.getElementById(f"template-{slot + 1}-save").addEventListener(
            "click", create_proxy(_make_template_save_handler(slot))
        )
        document.getElementById(f"template-{slot + 1}-apply").addEventListener(
            "click", create_proxy(_make_template_apply_handler(slot))
        )
        document.getElementById(f"template-{slot + 1}-name").addEventListener(
            "change", create_proxy(_make_template_rename_handler(slot))
        )
    for skin in SKINS:
        document.getElementById(f"skin-{skin['id']}-button").addEventListener(
            "click", create_proxy(_make_skin_handler(skin["id"]))
        )
    for range_key in TREND_RANGES:
        document.getElementById(f"trend-range-{range_key}-button").addEventListener(
            "click", create_proxy(_make_trend_range_handler(range_key))
        )
    for layer_key in TREND_LAYER_ORDER:
        document.getElementById(f"trend-layer-{layer_key}-button").addEventListener(
            "click", create_proxy(_make_trend_layer_handler(layer_key))
        )
    document.getElementById("summary-copy-area").hidden = True
    document.getElementById("ledger-sort-select").addEventListener("change", create_proxy(on_ledger_sort))
    document.getElementById("ledger-filter-select").addEventListener("change", create_proxy(on_ledger_filter))
    document.getElementById("ledger-copy-area").hidden = True
    setup_batch3()
    _reset_undo_state()
    update_changelog_display()
    render()
    _seed_achievement_toast_baseline()


setup()
