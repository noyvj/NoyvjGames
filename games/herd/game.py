"""Herd — Industrial Agriculture & Methane Game.

Runs in-browser via Pyodide. The core farm loop (herd growth, income,
and round progression), the methane meter (coupled to herd size by
default), the decoupling investments that reduce that coupling, and the
soft market/regulatory consequence system are all implemented below --
all 7 milestones are complete (see CLAUDE.md's milestone table).
"""

import importlib
import sys
import types

from js import document
from pyodide.ffi import create_proxy

import herd_runstate as runstate
from herd_rules import DECOUPLING_MEASURES, DELTA_KEYS, POULTRY_MEASURES, RULE_SPECS
from herd_model import FarmState, rules_are_custom
from herd_visuals import load_record_coupling_ratio
from herd_messages import on_toggle_info_page
from herd_achievements import _seed_achievement_toast_baseline, on_toggle_achievements
from herd_pasture import PASTURE_COW_THRESHOLDS, _make_cow_click_handler, on_cow_listen
from herd_changelog import on_toggle_changelog
from herd_sandbox import SANDBOX_CONTROLS, sandbox_control_id
from herd_barns import BARN_SKINS, DEFAULT_BARN
from herd_rules_ui import _load_stored_rules, rule_id
from herd_ledger import _ghost_el, on_ledger_clear, on_ledger_filter
from herd_collection import on_lever_history_filter
from herd_round import BULK_BUTTON_IDS, _make_delta_pin_handler, on_herd_slider_input
from herd_explain import EXPLAIN_KINDS, _make_explain_handler
from herd_planner import (
    PLAN_HORIZONS, _make_plan_horizon_handler, on_plan_add, on_plan_clear, on_plan_remove_last,
)
from herd_pins import PIN_STATS, _make_pin_handler, load_pins
from herd_savegame import on_recovery_dismiss
from herd_settings_code import on_settings_export
from herd_summary import on_toggle_report_card
from herd_renderer import render
from herd_handlers_play import (
    _make_bulk_handler, _make_decoupling_handler, _make_perk_handler, _make_policy_handler,
    _make_poultry_handler, _make_satellite_handler, on_advance_round, on_event_choice, on_grow_herd, on_grow_poultry,
    on_hand_over_farm, on_herd_slider_buy, on_invest_genetics, on_invest_plant_pivot, on_invest_supply_chain,
    on_toggle_cap, on_toggle_variation, on_undo_round,
)
from herd_handlers_panels import (
    _make_barn_handler, _make_family_choice_handler, _make_rule_handler, _make_sandbox_handler,
    on_family_retell, on_ledger_add, on_loadout_change, on_mixer_auto, on_mixer_result, on_profile_change,
    on_recovery_defaults, on_reset_rules, on_reveal_blind_run, on_sandbox_reset, on_settings_import,
    on_toggle_blind_run, on_toggle_ghost, on_welcome_golden_cow,
)

# ---------------------------------------------------------------------------
# File map: this file is the entry point and the wiring. Everything else lives in the modules named in
# _PART_NAMES, in dependency order (a module only imports from the ones before it). See "File map" in
# games/herd/CLAUDE.md for what each one holds. The same list (as .py file names) is HERD_PY_MODULES in boot.js.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "herd_rules",
    "herd_runstate",
    "herd_util",
    "herd_model",
    "herd_purchases",
    "herd_blind",
    "herd_visuals",
    "herd_messages",
    "herd_achievements",
    "herd_pasture",
    "herd_changelog",
    "herd_sandbox",
    "herd_barns",
    "herd_loadouts",
    "herd_rules_ui",
    "herd_ledger",
    "herd_succession",
    "herd_extras",
    "herd_collection",
    "herd_round",
    "herd_explain",
    "herd_planner",
    "herd_pins",
    "herd_mixer",
    "herd_family",
    "herd_profile",
    "herd_savegame",
    "herd_settings_code",
    "herd_summary",
    "herd_renderer",
    "herd_loading",
    "herd_handlers_play",
    "herd_handlers_panels",
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
    """game.farm & co. live in runstate (they get replaced while playing), so reads go there; a write to any
    name copies to every module that holds the name, so monkeypatching a function or setting
    game.bulk_mode = 5 still changes what the code uses."""

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
# from several modules, so the matching variables in herd_runstate start as None and are filled in here.
runstate.farm = FarmState()

runstate.record_coupling_ratio = load_record_coupling_ratio()

_load_stored_rules()
if rules_are_custom():
    runstate.farm = FarmState()  # the farm built above predates the stored rules

runstate.pinned_stats = load_pins()

runstate.barn_skin = DEFAULT_BARN


def current_farm():
    """The farm being played right now. settings.js reads it through pyodide.globals: the farm itself is a live
    variable in herd_runstate (it gets replaced), so a plain `farm` global in this file would go stale."""
    return runstate.farm


def setup():
    # index.html already marks these hidden via the `hidden` attribute,
    # but that markup default doesn't exist for the pytest fake-DOM
    # harness (a FakeElement starts with hidden=False) -- setting it
    # explicitly here keeps both environments consistent and costs
    # nothing in a real browser, where it's already true.
    document.getElementById("achievement-toast").hidden = True
    document.getElementById("milestone-toast").hidden = True
    document.getElementById("save-recovery-defaults-button").addEventListener("click", create_proxy(on_recovery_defaults))
    document.getElementById("save-recovery-dismiss-button").addEventListener("click", create_proxy(on_recovery_dismiss))
    document.getElementById("save-recovery-panel").hidden = True
    document.getElementById("grow-herd-button").addEventListener(
        "click", create_proxy(on_grow_herd)
    )
    document.getElementById("advance-round-button").addEventListener(
        "click", create_proxy(on_advance_round)
    )
    for measure in DECOUPLING_MEASURES:
        document.getElementById(f"{measure}-invest-button").addEventListener(
            "click", create_proxy(_make_decoupling_handler(measure))
        )
    document.getElementById("plant-pivot-invest-button").addEventListener(
        "click", create_proxy(on_invest_plant_pivot)
    )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("report-card-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_report_card)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    for element_id, handler in (
        ("poultry-grow-button", on_grow_poultry),
        ("succession-button", on_hand_over_farm),
        ("perk-family-savings-button", _make_perk_handler("family_savings")),
        ("perk-heritage-flock-button", _make_perk_handler("heritage_flock")),
        ("perk-mentor-methods-button", _make_perk_handler("mentor_methods")),
        ("genetics-invest-button", on_invest_genetics),
        ("supply-chain-invest-button", on_invest_supply_chain),
        ("variation-checkbox", on_toggle_variation),
        ("cap-checkbox", on_toggle_cap),
        ("policy-subsidy-button", _make_policy_handler(0)),
        ("policy-cash-button", _make_policy_handler(1)),
    ):
        document.getElementById(element_id).addEventListener("click", create_proxy(handler))
    for element_id, action in (
        ("satellite-open-button", "open_satellite"),
        ("satellite-grow-button", "grow_satellite"),
        ("satellite-retrofit-button", "retrofit_satellite"),
    ):
        document.getElementById(element_id).addEventListener(
            "click", create_proxy(_make_satellite_handler(action, element_id))
        )
    for measure in POULTRY_MEASURES:
        document.getElementById(f"{measure}-invest-button").addEventListener(
            "click", create_proxy(_make_poultry_handler(measure))
        )
    document.getElementById("lever-history-filter").addEventListener(
        "change", create_proxy(on_lever_history_filter)
    )
    for mode, element_id in BULK_BUTTON_IDS.items():
        document.getElementById(element_id).addEventListener("click", create_proxy(_make_bulk_handler(mode)))
    document.getElementById("herd-size-slider").addEventListener("input", create_proxy(on_herd_slider_input))
    document.getElementById("herd-slider-buy-button").addEventListener("click", create_proxy(on_herd_slider_buy))
    for key in DELTA_KEYS:
        document.getElementById(f"delta-chip-{key}").addEventListener(
            "click", create_proxy(_make_delta_pin_handler(key))
        )
    document.getElementById("undo-round-button").addEventListener("click", create_proxy(on_undo_round))
    for rule_name in RULE_SPECS:
        document.getElementById(rule_id(rule_name)).addEventListener("input", create_proxy(_make_rule_handler(rule_name)))
    document.getElementById("rules-reset-button").addEventListener("click", create_proxy(on_reset_rules))
    for element_id, handler in (
        ("plan-add-button", on_plan_add), ("plan-undo-button", on_plan_remove_last),
        ("plan-clear-button", on_plan_clear),
    ):
        document.getElementById(element_id).addEventListener("click", create_proxy(handler))
    for slot, button_id in enumerate(("family-story-choice-a", "family-story-choice-b", "family-story-choice-c")):
        document.getElementById(button_id).addEventListener("click", create_proxy(_make_family_choice_handler(slot)))
    document.getElementById("family-story-retell-button").addEventListener("click", create_proxy(on_family_retell))
    for slot, (cow_id, _threshold) in enumerate(PASTURE_COW_THRESHOLDS):
        document.getElementById(cow_id).addEventListener("click", create_proxy(_make_cow_click_handler(slot)))
    document.getElementById("cow-listen-button").addEventListener("click", create_proxy(on_cow_listen))
    for skin in BARN_SKINS:
        document.getElementById(f"barn-use-{skin['id']}").addEventListener("click", create_proxy(_make_barn_handler(skin["id"])))
    for name in SANDBOX_CONTROLS:
        document.getElementById(sandbox_control_id(name)).addEventListener("input", create_proxy(_make_sandbox_handler(name)))
    document.getElementById("sandbox-reset-button").addEventListener("click", create_proxy(on_sandbox_reset))
    document.getElementById("loadout-select").addEventListener("change", create_proxy(on_loadout_change))
    document.getElementById("blind-run-checkbox").addEventListener("click", create_proxy(on_toggle_blind_run))
    document.getElementById("blind-reveal-button").addEventListener("click", create_proxy(on_reveal_blind_run))
    document.getElementById("golden-cow-claim-button").addEventListener("click", create_proxy(on_welcome_golden_cow))
    document.getElementById("golden-cow-glider").addEventListener("click", create_proxy(on_welcome_golden_cow))
    document.getElementById("settings-export-button").addEventListener("click", create_proxy(on_settings_export))
    document.getElementById("settings-import-button").addEventListener("click", create_proxy(on_settings_import))
    document.getElementById("profile-select").addEventListener("change", create_proxy(on_profile_change))
    document.getElementById("settings-reset-button").addEventListener("click", create_proxy(on_profile_change))
    document.getElementById("mixer-result-button").addEventListener("click", create_proxy(on_mixer_result))
    document.getElementById("mixer-auto-button").addEventListener("click", create_proxy(on_mixer_auto))
    for stat in PIN_STATS:
        document.getElementById(f"pin-{stat.replace('_', '-')}").addEventListener("click", create_proxy(_make_pin_handler(stat)))
    document.getElementById("ledger-filter").addEventListener("change", create_proxy(on_ledger_filter))
    document.getElementById("ledger-add-button").addEventListener("click", create_proxy(on_ledger_add))
    ghost_toggle = _ghost_el("ghost-toggle")  # Z-3e
    if ghost_toggle is not None:
        ghost_toggle.addEventListener("change", create_proxy(on_toggle_ghost))
    document.getElementById("ledger-clear-button").addEventListener("click", create_proxy(on_ledger_clear))
    document.getElementById("event-choice-a").addEventListener("click", create_proxy(lambda: on_event_choice("a")))
    document.getElementById("event-choice-b").addEventListener("click", create_proxy(lambda: on_event_choice("b")))
    for horizon in PLAN_HORIZONS:
        document.getElementById(f"plan-horizon-{horizon}-button").addEventListener(
            "click", create_proxy(_make_plan_horizon_handler(horizon))
        )
    for kind in EXPLAIN_KINDS:
        document.getElementById(f"explain-{kind}-button").addEventListener("click", create_proxy(_make_explain_handler(kind)))
    render()
    _seed_achievement_toast_baseline()


setup()
