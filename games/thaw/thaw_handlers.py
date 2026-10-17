"""Click handlers: every on_* function that changes the game, plus the factories that build them."""

import json

import info_page
from js import document

import thaw_runstate as runstate
from thaw_achievements import (
    _check_new_achievements_for_toast, render_skins, set_skin, update_achievements_display,
)
from thaw_flavour import start_temperature_roll
from thaw_loading import load_state
from thaw_mechanics import (
    apply_tipping_cascades, bank_carbon_credits, deliver_crate_if_due, lock_forecast, open_crate,
    resolve_forecast, set_long_game, spend_carbon_credits,
)
from thaw_model import SECONDARY_REGIONS, escalation_level, region, region_b, region_c, set_hold_the_line
from thaw_panels import (
    render_climate_scientist, render_info_page, update_changelog_display, update_community_compare_panel,
)
from thaw_presets import (
    PRESET_WEIGHTS, _guard_spend, _preset_spend, apply_custom_preset, apply_preset, custom_preset_weights,
    render_confirm_threshold, save_custom_preset, set_confirm_threshold, set_hard_mode,
)
from thaw_readouts import (
    _routing_selection, apply_balance_bonus, highlights_text, render_rate_inspector, round_announcement,
    route_funds, set_temp_unit,
)
from thaw_records import render_climate_archive
from thaw_renderer import render
from thaw_rules import CATEGORIES, RESCUE_COST
from thaw_runs import _announce_escalation, check_run_end, render_compare
from thaw_saveparts import load_problems, render_load_notice
from thaw_savestate import get_state
from thaw_sciencelog import (
    MAX_PINNED, _auto_play_worst_case_region, _log_action, _record_round_events, render_science_log,
    science_log, science_log_text, set_log_filter, set_log_pinned, set_log_query,
)
from thaw_settingscode import export_settings_code, import_settings_code, settings_code_message
from thaw_timeline import UNDO_COST, can_undo, render_planner, render_replay, replay_rounds, replay_selected
from thaw_views import _focus_key, _focus_region_for, render_board, render_focus, set_board_sort


def on_log_filter(name):
    def handler(event=None):
        if set_log_filter(name):
            render_science_log()
    return handler


def on_log_search(event=None):
    set_log_query(document.getElementById("log-search").value)
    render_science_log()


def on_log_list_click(event=None):
    """One delegated listener for every pin button in the list (the buttons are re-created on each
    render, so they cannot carry their own listeners)."""
    target = getattr(event, "target", None)
    closest = getattr(target, "closest", None)
    button = closest("button[data-pin-index]") if closest is not None else None
    if button is None:
        return
    try:
        index = int(button.getAttribute("data-pin-index"))
    except (TypeError, ValueError, AttributeError):
        return
    entry = science_log[index] if 0 <= index < len(science_log) else None
    if entry is None:
        return
    if set_log_pinned(index, not entry.get("pinned")):
        render()
    else:
        document.getElementById("log-status").innerText = (
            f"You can pin up to {MAX_PINNED} entries; unpin one first." if not entry.get("pinned") else ""
        )


def on_copy_log(event=None):
    status = document.getElementById("log-status")
    text = science_log_text()
    if not text:
        status.innerText = "The log is empty."
        return
    try:
        from js import navigator  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        navigator.clipboard.writeText("Thaw scientist's log\n" + text)
        status.innerText = "Log copied to the clipboard as plain text."
    except Exception:  # noqa: BLE001 -- no clipboard (tests, or a blocked page)
        status.innerText = "Copy isn't available here: select the entries above instead."


def _make_custom_preset_handler(prefix):
    def handler(event=None):
        if _guard_spend(
            _preset_spend(SECONDARY_REGIONS[prefix], custom_preset_weights()),
            f"Spend {{amount}} funds on the Custom mix in Region {prefix.upper()}?",
            "thaw-custom-preset",
            lambda: _finish_custom_preset(prefix),
        ):
            return
        _finish_custom_preset(prefix)
    return handler


def _finish_custom_preset(prefix):
    apply_custom_preset(SECONDARY_REGIONS[prefix])
    render()
    _check_new_achievements_for_toast()


def _make_save_preset_handler(prefix):
    def handler(event=None):
        save_custom_preset(SECONDARY_REGIONS[prefix])
        render()
    return handler


def on_confirm_threshold_change(event=None):
    set_confirm_threshold(document.getElementById("confirm-threshold-select").value)
    render_confirm_threshold()


def on_toggle_hard_mode(event=None):
    set_hard_mode(not runstate.hard_mode)
    render()


def on_toggle_info_page(event=None):
    runstate.info_page_open = info_page.toggle(runstate.info_page_open)
    render_info_page()


def _make_carbon_handler(key):
    def handler(event=None):
        if spend_carbon_credits(key):
            render()
    return handler


def on_open_crate(event=None):
    result = open_crate()
    if result is None:
        return
    document.getElementById("sr-announcer").innerText = f"Supply crate opened. {result[1]}"
    render()
    _check_new_achievements_for_toast()


def on_toggle_framing(event=None):
    runstate.framing = "global" if runstate.framing == "regional" else "regional"
    render()


def on_toggle_long_game(event=None):
    set_long_game(not runstate.long_game)
    render()


def on_lock_forecast(event=None):
    """The box is read in the unit chosen in Settings, then stored in the game's own degrees."""
    raw = document.getElementById("forecast-input").value
    try:
        raw = str(float(str(raw).strip()) / (1.8 if runstate.temp_unit == "f" else 1.0))
    except (TypeError, ValueError):
        pass  # lock_forecast() rejects it
    if lock_forecast(raw):
        render()


def on_toggle_achievements(event=None):
    runstate.achievements_open = not runstate.achievements_open
    update_achievements_display()


def on_skin_change(event=None):
    chosen = document.getElementById("skin-select").value
    set_skin(chosen)
    render_skins()


def on_toggle_archive(event=None):
    runstate.archive_open = not runstate.archive_open
    render_climate_archive()


def on_toggle_changelog(event=None):
    runstate.changelog_open = not runstate.changelog_open
    update_changelog_display()


def on_toggle_community_compare(event=None):
    runstate.community_compare_open = not runstate.community_compare_open
    update_community_compare_panel()


def on_toggle_climate_scientist(event=None):
    runstate.climate_scientist_open = not runstate.climate_scientist_open
    render_climate_scientist()


def on_routing_change(event=None):
    render()


def on_send_convoy(event=None):
    src, dst = _routing_selection()
    if route_funds(src, dst):
        render()


def on_rate_inspector_region_change(event=None):
    render_rate_inspector()


def on_copy_highlights(event=None):
    status = document.getElementById("highlights-status")
    try:
        from js import navigator  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        navigator.clipboard.writeText(highlights_text())
        status.innerText = "Copied to the clipboard."
    except Exception:  # noqa: BLE001 -- no clipboard (tests, or a blocked page)
        status.innerText = "Copy isn't available here: select the three lines above instead."


def on_temp_unit_change(event=None):
    if set_temp_unit(document.getElementById("temp-unit-select").value):
        render()


def on_compare_change(event=None):
    render_compare()


def on_toggle_hold_the_line(event=None):
    set_hold_the_line(not runstate.hold_the_line)
    render()


def _make_board_sort_handler(key):
    def handler(event=None):
        if set_board_sort(key):
            render_board()
    return handler


def on_focus_region_change(event=None):
    render_focus()


def _make_focus_invest_handler(category):
    def handler(event=None):
        if runstate.run_over:
            return
        _focus_region_for(_focus_key()).invest(category)
        render()
        _check_new_achievements_for_toast()
    return handler


def _do_focus_rescue(key):
    r = _focus_region_for(key)
    if r.rescue():
        _log_action(key.upper(), "the one-time emergency rescue was used.")
        render()
        _check_new_achievements_for_toast()


def on_focus_rescue(event=None):
    key = _focus_key()
    if _focus_region_for(key).can_rescue() and _guard_spend(
        RESCUE_COST, f"Use Region {key.upper()}'s one emergency rescue for {{amount}} funds?",
        "thaw-rescue", lambda: _do_focus_rescue(key),
    ):
        return
    _do_focus_rescue(key)


def on_planner_change(event=None):
    render_planner()


def on_planner_reset(event=None):
    for category in CATEGORIES:
        document.getElementById(f"planner-{category}").value = ""
    document.getElementById("planner-repeat").checked = False
    render_planner()


def undo_last_round():
    """Restores the pre-Advance snapshot and charges the cost. Returns True if it happened."""
    if not can_undo():
        return False
    snapshot = json.loads(json.dumps(runstate._undo_snapshot))
    # interface choices that are not part of the round stay as the player has them now
    keep_info, keep_d, keep_d_intro = runstate.info_page_open, runstate.worst_case_region_revealed, runstate.worst_case_intro_seen
    keep_labels = (region_b.strategy_label, region_c.strategy_label)
    load_state(snapshot)
    runstate.info_page_open, runstate.worst_case_region_revealed, runstate.worst_case_intro_seen = keep_info, keep_d, keep_d_intro
    region_b.strategy_label, region_c.strategy_label = keep_labels
    document.getElementById("b-strategy-label-input").value = region_b.strategy_label
    document.getElementById("c-strategy-label-input").value = region_c.strategy_label
    region.funds -= UNDO_COST
    runstate.undo_used = True
    runstate._undo_snapshot = None
    document.getElementById("sr-announcer").innerText = f"Rewound to round {region.round_number}."
    render()
    return True


def on_undo(event=None):
    undo_last_round()


def on_replay_change(event=None):
    runstate.replay_follow = replay_selected() >= replay_rounds()
    render_replay()


def on_replay_step(delta):
    def handler(event=None):
        n = replay_rounds()
        if n < 1:
            return
        target = replay_selected() + delta if delta not in ("first", "last") else (1 if delta == "first" else n)
        document.getElementById("replay-slider").value = str(max(1, min(n, target)))
        runstate.replay_follow = replay_selected() >= n
        render_replay()
    return handler


def on_dismiss_load_notice(event=None):
    del load_problems[:]
    render_load_notice()


def _make_invest_handler(category):
    def handler(event=None):
        region.invest(category)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_secondary_invest_handler(prefix, category):
    def handler(event=None):
        SECONDARY_REGIONS[prefix].invest(category)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_policy_stance_handler(key):
    def handler(event=None):
        if region.choose_policy_stance(key):
            render()
            _check_new_achievements_for_toast()
    return handler


def _do_rescue(prefix):
    target = region if prefix == "" else SECONDARY_REGIONS[prefix]
    if target.rescue():
        _log_action((prefix or "a").upper(), "the one-time emergency rescue was used.")
        render()
        _check_new_achievements_for_toast()


def _make_rescue_handler(prefix):
    """G21: prefix "" is Region A, "b"/"c" the secondary regions."""
    def handler(event=None):
        target = region if prefix == "" else SECONDARY_REGIONS[prefix]
        # G-23: the rescue is the biggest single spend, so it can ask first (only when it would go through).
        if target.can_rescue() and _guard_spend(
            RESCUE_COST, f"Use Region {(prefix or 'a').upper()}'s one emergency rescue for {{amount}} funds?",
            "thaw-rescue", lambda: _do_rescue(prefix),
        ):
            return
        _do_rescue(prefix)
    return handler


def _make_preset_handler(prefix, preset_name):
    def handler(event=None):
        r = SECONDARY_REGIONS[prefix]
        if _guard_spend(
            _preset_spend(r, PRESET_WEIGHTS.get(preset_name)),
            f"Spend {{amount}} funds on the {preset_name} preset in Region {prefix.upper()}?",
            "thaw-preset", lambda: _finish_preset(prefix, preset_name),
        ):
            return
        _finish_preset(prefix, preset_name)
    return handler


def _finish_preset(prefix, preset_name):
    apply_preset(SECONDARY_REGIONS[prefix], preset_name)
    render()
    _check_new_achievements_for_toast()


def _make_strategy_label_handler(prefix):
    """G4: reads the input's current value straight off the DOM into
    state on every "input" event. Deliberately does NOT call render() —
    render() never writes this input's .value back (see setup()'s own
    comment), but avoiding the call entirely also sidesteps ever needing
    to reason about it, and there's nothing else on screen this label
    needs to update."""
    def handler(event=None):
        SECONDARY_REGIONS[prefix].strategy_label = document.getElementById(
            f"{prefix}-strategy-label-input"
        ).value
    return handler


def on_toggle_worst_case_region(event=None):
    if runstate.worst_case_region_revealed:
        runstate.worst_case_intro_seen = True  # closing it after the first look retires the note
    runstate.worst_case_region_revealed = not runstate.worst_case_region_revealed
    render()
    _check_new_achievements_for_toast()


def on_advance_round(event=None):
    if runstate.run_over:
        return
    # GG-17: remember exactly how things stand before this round (one rewind per run uses it).
    runstate._undo_snapshot = json.loads(json.dumps(get_state()))
    level_before = escalation_level(region.round_number)
    temperature_before = region.temperature
    region.advance_round()
    resolve_forecast()
    for r in SECONDARY_REGIONS.values():
        r.advance_round()
    apply_tipping_cascades()
    bank_carbon_credits()
    apply_balance_bonus()
    deliver_crate_if_due()  # GG-22
    _auto_play_worst_case_region()
    _record_round_events()
    if escalation_level(region.round_number) > level_before:
        _announce_escalation(escalation_level(region.round_number))
    check_run_end()
    # G-10: announce before render() so the balance flag is still set.
    document.getElementById("sr-announcer").innerText = round_announcement()
    render()
    start_temperature_roll(temperature_before, region.temperature)  # GG-19
    _check_new_achievements_for_toast()


def on_copy_settings_code(event=None):
    code = export_settings_code()
    document.getElementById("settings-code-input").value = code
    status = document.getElementById("settings-code-status")
    try:
        from js import navigator  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        navigator.clipboard.writeText(code)
        status.innerText = "Settings code copied. Paste it into Thaw on another device."
    except Exception:  # noqa: BLE001 -- no clipboard (tests, or a blocked page)
        status.innerText = "The code is in the box: select it and copy it."


def on_restore_settings_code(event=None):
    code = document.getElementById("settings-code-input").value
    result = import_settings_code(code)
    document.getElementById("settings-code-status").innerText = settings_code_message(result)
    if result is not None:
        render()


def on_settings_reset_click(event=None):
    """The page's 'Reset to Default' (settings.js handles its own switches) also clears this file's
    big-spend threshold."""
    set_confirm_threshold(0)
    render_confirm_threshold()
