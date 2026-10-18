"""Click and change handlers: every on_* function plus the handler factories (_make_*) and the batch-3 wiring."""

import info_page
from js import document
from pyodide.ffi import create_proxy

import drift_runstate as runstate
from drift_achievements import announce, update_achievements_display
from drift_assist import ASSIST_MODES, plan_suggestion, plan_summary_line, set_assist_mode
from drift_calendar import (
    _reset_civic_notes, _round_marks, council_options, council_pick, round_announcement_text,
)
from drift_collection import (
    SKIN_BY_ID, _check_new_achievements_for_toast, _collect_after_round, _seed_achievement_toast_baseline,
    choose_skin, render_collection_summary, render_skins,
)
from drift_ledger import LEDGER_FILTERS, LEDGER_SORTS, _copy_to_clipboard, ledger_csv, render_ledger
from drift_loading import render_load_note
from drift_model_region import region
from drift_newsview import render_trend_graph, trend_layers
from drift_pages import _write_local_storage_item, render_info_page, update_changelog_display
from drift_plans import (
    _clean_autopilot, _counts_text, apply_template, autopilot_run, budget_templates, rename_template,
    render_autopilot, render_templates, run_summary_text, save_template, template_summary,
)
from drift_regional import _sync_spillover, invest_neighbor, open_neighbor, support_neighbor
from drift_renderer import render
from drift_report import (
    _celebrate_band_rise, _clear_band_note, region_report_html, region_report_text, render_report,
)
from drift_rules import (
    CALENDAR_KINDS, CAPACITY_LABEL, CAPACITY_TYPES, INVEST_COST, NEIGHBOR_SUPPORT_AMOUNT, POLICIES,
    POLICY_MAX_LEVEL, REALLOCATION_FUNDS_COST, REALLOCATION_UNITS, REGION_NAME_MAX_LENGTH, _to_float,
    _to_int,
)
from drift_settings import (
    CONFIRM_CHOICES, CONFIRM_STORAGE_KEY, GLOSSARY_ORDER, _guard_large_move, _note_save_activity,
    policy_confirm_message, policy_move_share, realloc_confirm_message, realloc_move_share,
    render_confirm_threshold, render_glossary, render_save_nudge,
)
from drift_tiers import TIERS, _set_accelerated_severity, apply_tier
from drift_trendgraph import TREND_LAYER_LABEL, TREND_RANGES, wellbeing_band
from drift_undo import (
    _take_full_snapshot, _take_round_start_snapshot, play_rounds, render_round_tools, reset_round,
    rewind_available, use_rewind_token,
)
from drift_visuals import _pop_building, region_visual_building_count


def on_toggle_changelog(event=None):
    runstate.changelog_open = not runstate.changelog_open
    update_changelog_display()


def on_toggle_achievements(event=None):
    runstate.achievements_open = not runstate.achievements_open
    update_achievements_display()


def on_toggle_info_page(event=None):
    runstate.info_page_open = info_page.toggle(runstate.info_page_open)
    render_info_page()


def on_toggle_ledger(event=None):
    runstate.ledger_open = not runstate.ledger_open
    render_ledger()


def on_ledger_sort(event=None):
    value = getattr(document.getElementById("ledger-sort-select"), "value", runstate.ledger_sort)
    runstate.ledger_sort = value if value in LEDGER_SORTS else "round_desc"
    render_ledger()


def on_ledger_filter(event=None):
    value = getattr(document.getElementById("ledger-filter-select"), "value", runstate.ledger_filter)
    runstate.ledger_filter = value if value in LEDGER_FILTERS else "all"
    render_ledger()


def on_copy_ledger_csv(event=None):
    text = ledger_csv()
    status = document.getElementById("ledger-copy-status")
    area = document.getElementById("ledger-copy-area")
    if _copy_to_clipboard(text):
        area.hidden = True
        status.innerText = "Copied the ledger as CSV to the clipboard."
    else:
        area.hidden = False
        area.value = text
        status.innerText = "Could not copy automatically. Select the text below and copy it yourself."


def on_reset_round(event=None):
    if reset_round():
        runstate.round_tools_message = "This round's decisions were refunded. Funds and capacity are back to the start of the round."
        _seed_achievement_toast_baseline()
        render()
        announce(runstate.round_tools_message)
        return
    render()
    announce("Nothing to reset: you have not made a decision this round")


def on_rewind(event=None):
    if not rewind_available():
        return
    if not runstate.rewind_armed:
        runstate.rewind_armed = True
        render_round_tools()
        announce("Press Rewind again to confirm undoing the last Advance Round")
        return
    use_rewind_token()
    runstate.round_tools_message = (
        f"Rewound: round {region.round_number} is open again exactly as it was before you advanced. "
        "The Rewind Token is spent for this region."
    )
    _seed_achievement_toast_baseline()
    render()
    announce(runstate.round_tools_message)


def on_play_rounds(event=None):
    runstate.collection_note = ""
    _clear_band_note()
    _note_save_activity()
    marks_before = _round_marks()
    band_before = wellbeing_band(region.wellbeing_score())
    advanced, reason = play_rounds()
    unit = "round" if advanced == 1 else "rounds"
    if reason:
        runstate.round_tools_message = f"Played {advanced} {unit} and stopped early: {reason}."
    else:
        runstate.round_tools_message = f"Played {advanced} {unit} with your current allocation."
    render()
    announce(runstate.round_tools_message)
    if advanced:
        band_up = _celebrate_band_rise(band_before)  # GI-29
        announce(round_announcement_text(marks_before) + (f" {runstate.band_note_text}" if band_up else ""))
    _check_new_achievements_for_toast()


def on_toggle_collection(event=None):
    runstate.collection_open = not runstate.collection_open
    render_collection_summary()


def _make_skin_handler(skin_id):
    def handler(event=None):
        if choose_skin(skin_id):
            announce(f"{SKIN_BY_ID[skin_id]['label']} skin chosen")
        render_skins()
    return handler


def on_toggle_calendar(event=None):
    region.calendar_enabled = not region.calendar_enabled
    runstate.calendar_note_text = ""
    render()


def on_brace(event=None):
    target = region.brace_target()
    if target is not None and region.brace():
        runstate.calendar_note_text = f"Braced for {target['name']}. {CALENDAR_KINDS[target['kind']]['brace_cost']:.0f} funds spent."
        announce(runstate.calendar_note_text)
    elif target is None:
        announce("Nothing to brace for right now")
    else:
        announce(
            f"Cannot brace for {target['name']}: it costs {CALENDAR_KINDS[target['kind']]['brace_cost']:.0f} "
            f"and you have {region.funds:.0f}"
        )
    render()


def on_council_pick(branch):
    program = council_options().get(branch)
    if program is not None and council_pick(branch):
        runstate.council_note_text = f"Adopted: {program['name']}. {program['text']}."
    render()


def _make_council_handler(branch):
    def handler(event=None):
        on_council_pick(branch)

    return handler


def on_autopilot_change(event=None):
    def value(element_id, default):
        return getattr(document.getElementById(element_id), "value", default)

    share_raw = str(value("autopilot-share-select", "50"))
    surplus_raw = str(value("autopilot-surplus-select", "housing"))
    raw = {
        "services_share": None if share_raw == "off" else _to_float(share_raw, 50.0) / 100.0,
        "surplus": None if surplus_raw == "hold" else surplus_raw,
        "reserve": _to_int(value("autopilot-reserve-select", "40"), 40),
        "rounds": _to_int(value("autopilot-rounds-select", "10"), 10),
    }
    if raw["services_share"] is not None:
        raw["services_share"] = round(raw["services_share"], 2)
    region.autopilot = _clean_autopilot(raw)
    render_autopilot()


def on_autopilot_run(event=None):
    runstate.collection_note = ""
    _clear_band_note()
    _note_save_activity()
    marks_before = _round_marks()
    band_before = wellbeing_band(region.wellbeing_score())
    advanced, reason = autopilot_run()
    unit = "round" if advanced == 1 else "rounds"
    runstate.round_tools_message = (
        f"Autopilot ran {advanced} {unit} and stopped early: {reason}." if reason
        else f"Autopilot ran {advanced} {unit}."
    )
    render()
    announce(runstate.round_tools_message)
    if advanced:
        band_up = _celebrate_band_rise(band_before)  # GI-29
        announce(round_announcement_text(marks_before) + (f" {runstate.band_note_text}" if band_up else ""))
    _check_new_achievements_for_toast()


def _make_template_save_handler(slot):
    def handler(event=None):
        name = getattr(document.getElementById(f"template-{slot + 1}-name"), "value", "") or ""
        if save_template(slot, str(name)):
            runstate.template_note = f"Saved this round's buys as {budget_templates[slot]['name']}: {template_summary(budget_templates[slot])}."
        else:
            runstate.template_note = "Nothing bought since this round began, so there is nothing to save."
        announce(runstate.template_note)
        render_templates()
    return handler


def _make_template_apply_handler(slot):
    def handler(event=None):
        template = budget_templates[slot]
        count_before = region_visual_building_count(region.total_capacity())
        bought, short = apply_template(slot)
        if bought:
            _pop_building(count_before)
        if not template["buys"]:
            runstate.template_note = f"{template['name']} is empty."
        elif not bought:
            runstate.template_note = f"{template['name']}: not enough funds to buy anything from it."
        else:
            runstate.template_note = f"{template['name']}: bought {_counts_text(bought)}."
            if short:
                runstate.template_note += f" Could not afford {_counts_text(short)}."
        announce(runstate.template_note)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_template_rename_handler(slot):
    def handler(event=None):
        value = getattr(document.getElementById(f"template-{slot + 1}-name"), "value", "")
        if rename_template(slot, str(value or "")):
            render_templates()
    return handler


def on_copy_summary(event=None):
    text = run_summary_text()
    area = document.getElementById("summary-copy-area")
    if _copy_to_clipboard(text):
        area.hidden = True
        runstate.summary_note_text = "Copied the run summary to the clipboard."
    else:
        area.hidden = False
        area.value = text
        runstate.summary_note_text = "Could not copy automatically. Select the text below and copy it yourself."
    document.getElementById("round-tools-note").innerText = runstate.summary_note_text
    document.getElementById("round-tools-note").hidden = False


def _make_trend_range_handler(key):
    def handler(event=None):
        runstate.trend_range = key
        render_trend_graph()
        label = "all rounds" if TREND_RANGES[key] is None else f"the last {TREND_RANGES[key]} rounds"
        announce(f"Trend graph shows {label}")
    return handler


def _make_trend_layer_handler(key):
    def handler(event=None):
        trend_layers[key] = not trend_layers[key]
        render_trend_graph()
        announce(f"{TREND_LAYER_LABEL[key]} {'shown' if trend_layers[key] else 'hidden'} on the trend graph")
    return handler


def on_advance_round(event=None):
    runstate.round_tools_message = ""
    runstate.collection_note = ""
    _reset_civic_notes()
    _clear_band_note()
    _note_save_activity()  # I-27: a save made since the last action restarts the rounds-since-save count here
    _sync_spillover()
    runstate.rewind_snapshot = _take_full_snapshot()  # GI-18: the state just before this advance
    completed_round = region.round_number
    marks_before = _round_marks()
    band_before = wellbeing_band(region.wellbeing_score())
    region.advance_round()
    if runstate.neighbor is not None:
        runstate.neighbor.advance_round()
    runstate.round_start_snapshot = _take_round_start_snapshot()  # I-15: the new round's starting point
    _collect_after_round(completed_round)
    render()
    band_up = _celebrate_band_rise(band_before)  # GI-29
    announce(round_announcement_text(marks_before) + (f" {runstate.band_note_text}" if band_up else ""))
    _check_new_achievements_for_toast()


def on_open_neighbor(event=None):
    if open_neighbor():
        announce("Neighbouring district opened. It runs beside your region every round")
    render()


def on_support_neighbor(event=None):
    if support_neighbor():
        announce(f"Sent {NEIGHBOR_SUPPORT_AMOUNT:.0f} funds to the neighbouring district. Funds {region.funds:.0f}")
    else:
        announce("Cannot send support: your region must be calm and keep a cushion of funds first")
    render()


def _make_neighbor_invest_handler(capacity_type):
    def handler(event=None):
        if invest_neighbor(capacity_type):
            announce(
                f"Neighbouring district invested in {CAPACITY_LABEL[capacity_type]}. "
                f"Its funds are {runstate.neighbor.funds:.0f}"
            )
        else:
            announce(f"The neighbouring district cannot afford {CAPACITY_LABEL[capacity_type]}")
        render()
    return handler


def _do_policy_invest(policy):
    label = POLICIES[policy]["label"]
    if region.invest_policy(policy):
        announce(
            f"Funded {label}, level {region.policy_level[policy]} of {POLICY_MAX_LEVEL}. Funds {region.funds:.0f}"
        )
    elif region.policy_level[policy] >= POLICY_MAX_LEVEL:
        announce(f"{label} is already at its top level")
    else:
        announce(f"Cannot fund {label}: it costs {region.policy_cost(policy):.0f} and you have {region.funds:.0f}")
    render()
    _check_new_achievements_for_toast()


def _make_policy_handler(policy):
    def handler(event=None):
        # I-28: a big policy purchase can be confirmed first (Settings > Confirm large moves).
        if (
            region.policy_level[policy] < POLICY_MAX_LEVEL
            and region.funds >= region.policy_cost(policy)
            and _guard_large_move(
                policy_move_share(policy), policy_confirm_message(policy),
                f"drift-policy-{policy}", lambda: _do_policy_invest(policy),
            )
        ):
            return
        _do_policy_invest(policy)
    return handler


def _make_invest_handler(capacity_type):
    def handler(event=None):
        label = CAPACITY_LABEL[capacity_type]
        count_before = region_visual_building_count(region.total_capacity())
        if region.invest(capacity_type):
            _pop_building(count_before)
            announce(
                f"Invested in {label}: now {region.capacity[capacity_type]:.0f}. "
                f"Total capacity {region.total_capacity():.0f}. Funds {region.funds:.0f}. "
                f"Strain {region.strain_fraction() * 100:.0f}% ({region.strain_level()})"
            )
        else:
            announce(
                f"Cannot invest in {label}: it costs {INVEST_COST[capacity_type]:.0f} and you have {region.funds:.0f}"
            )
        render()
        _check_new_achievements_for_toast()
    return handler


def on_toggle_coda(event=None):
    runstate.coda_visible = not runstate.coda_visible
    if runstate.coda_visible:
        region.coda_ever_viewed = True
    render()
    _check_new_achievements_for_toast()


# I13: opt-in accelerated-severity difficulty toggle -- a settings-style
# flip, same as on_toggle_info_page/on_toggle_achievements, not a player
# action achievements can key off of, so no toast check here.
def on_toggle_accelerated_severity(event=None):
    # I20: the dot-density baseline is captured inside _set_accelerated_severity() the very first time the
    # toggle is ever switched on (never re-captured later).
    _set_accelerated_severity(not region.accelerated_severity_enabled)
    render()


def on_toggle_crisis_start(event=None):
    region.set_crisis_start(not region.crisis_start_enabled)
    runstate.round_start_snapshot = _take_round_start_snapshot()  # the new starting funds are the round's start
    render()


def _do_reallocate(from_type, to_type):
    if region.reallocate(from_type, to_type):
        announce(
            f"Moved {REALLOCATION_UNITS:.0f} capacity from {CAPACITY_LABEL[from_type]} to {CAPACITY_LABEL[to_type]}. "
            f"Cost {REALLOCATION_FUNDS_COST:.0f} funds. Funds {region.funds:.0f}"
        )
    elif from_type == to_type:
        announce("Choose two different capacity types to move capacity between")
    elif region.capacity.get(from_type, 0) < REALLOCATION_UNITS:
        announce(f"Cannot move capacity: {CAPACITY_LABEL.get(from_type, from_type)} has less than {REALLOCATION_UNITS:.0f}")
    else:
        announce(f"Cannot move capacity: it costs {REALLOCATION_FUNDS_COST:.0f} funds and you have {region.funds:.0f}")
    render()


def on_reallocate(event=None):
    from_type = getattr(document.getElementById("realloc-from"), "value", "housing")
    to_type = getattr(document.getElementById("realloc-to"), "value", "services")
    # I-28: a big reallocation can be confirmed first (Settings > Confirm large moves).
    if (
        from_type != to_type and from_type in CAPACITY_TYPES and to_type in CAPACITY_TYPES
        and region.capacity[from_type] >= REALLOCATION_UNITS and region.funds >= REALLOCATION_FUNDS_COST
        and _guard_large_move(
            realloc_move_share(from_type), realloc_confirm_message(from_type, to_type),
            "drift-reallocate", lambda: _do_reallocate(from_type, to_type),
        )
    ):
        return
    _do_reallocate(from_type, to_type)


def on_region_name_input(event=None):
    raw = getattr(document.getElementById("region-name-input"), "value", "") or ""
    region.region_name = str(raw).strip()[:REGION_NAME_MAX_LENGTH]
    render()


def _make_legacy_handler(choice):
    def handler(event=None):
        region.coda_legacy_choice = choice
        render()
    return handler


def on_dismiss_load_note(event=None):
    runstate.load_note_text = ""
    render_load_note()


def _make_tier_handler(tier_id):
    def handler(event=None):
        ok, runstate.tier_note_text = apply_tier(tier_id)
        render()
        announce(runstate.tier_note_text)
    return handler


def _make_assist_handler(mode):
    def handler(event=None):
        set_assist_mode(mode)
        render()
        if mode != "off":
            announce(plan_summary_line(plan_suggestion()))
    return handler


def on_confirm_threshold_change(event=None):
    raw = getattr(document.getElementById("confirm-threshold-select"), "value", "0")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 0
    runstate.confirm_threshold = value if value in CONFIRM_CHOICES else 0
    _write_local_storage_item(CONFIRM_STORAGE_KEY, str(runstate.confirm_threshold))
    render_confirm_threshold()


def on_settings_reset_click(event=None):
    """Settings > Reset to Default also clears this game-side preference (settings.js handles the rest)."""
    runstate.confirm_threshold = 0
    _write_local_storage_item(CONFIRM_STORAGE_KEY, "0")
    render_confirm_threshold()


def on_dismiss_save_nudge(event=None):
    runstate.nudge_snooze_round = region.round_number
    render_save_nudge()


def _make_glossary_handler(term, action):
    def handler(event=None):
        if action == "click":
            if runstate.glossary_open == term and runstate.glossary_pinned:
                runstate.glossary_open = None
                runstate.glossary_pinned = False
            else:
                runstate.glossary_open = term
                runstate.glossary_pinned = True
        elif action == "show":
            if runstate.glossary_pinned:
                return
            runstate.glossary_open = term
        elif action == "hide":
            if runstate.glossary_pinned:
                return
            runstate.glossary_open = None
        render_glossary()
    return handler


def on_glossary_more(event=None):
    """Open The Real Story from the popover (clicks the real toggle button so the Desktop window opens too)."""
    if not runstate.info_page_open:
        button = document.getElementById("info-page-toggle-button")
        click = getattr(button, "click", None)
        if callable(click):
            click()
        else:
            on_toggle_info_page()


def on_toggle_report(event=None):
    runstate.report_open = not runstate.report_open
    render_report()


def on_copy_report(event=None):
    text = region_report_text()
    area = document.getElementById("report-copy-area")
    if _copy_to_clipboard(text):
        area.hidden = True
        runstate.report_note_text = "Copied the Region Report as text."
    else:
        area.hidden = False
        area.value = text
        runstate.report_note_text = "Could not copy automatically. Select the text below and copy it yourself."
    document.getElementById("report-copy-status").innerText = runstate.report_note_text


def on_print_report(event=None):
    """Fill the print-only sheet with the report and open the browser's print dialog."""
    document.getElementById("report-print-sheet").innerHTML = region_report_html()
    try:
        import js as _js  # noqa: PLC0415

        printer = getattr(_js.window, "print", None)
        if callable(printer):
            printer()
            runstate.report_note_text = "Opened the print dialog."
        else:
            runstate.report_note_text = "This browser cannot open the print dialog from here. Use Copy report as text instead."
    except Exception:  # noqa: BLE001 -- no window (tests) or a refused print
        runstate.report_note_text = "This browser cannot open the print dialog from here. Use Copy report as text instead."
    document.getElementById("report-copy-status").innerText = runstate.report_note_text


def setup_batch3():
    for tier in TIERS:
        document.getElementById(f"tier-{tier['id']}-button").addEventListener(
            "click", create_proxy(_make_tier_handler(tier["id"]))
        )
    for mode in ASSIST_MODES:
        document.getElementById(f"assist-{mode}-button").addEventListener(
            "click", create_proxy(_make_assist_handler(mode))
        )
    document.getElementById("confirm-threshold-select").addEventListener("change", create_proxy(on_confirm_threshold_change))
    document.getElementById("settings-reset-button").addEventListener("click", create_proxy(on_settings_reset_click))
    document.getElementById("save-nudge-dismiss").addEventListener("click", create_proxy(on_dismiss_save_nudge))
    for term in GLOSSARY_ORDER:
        button = document.getElementById(f"glossary-{term}-button")
        button.addEventListener("click", create_proxy(_make_glossary_handler(term, "click")))
        button.addEventListener("mouseenter", create_proxy(_make_glossary_handler(term, "show")))
        button.addEventListener("focus", create_proxy(_make_glossary_handler(term, "show")))
        button.addEventListener("mouseleave", create_proxy(_make_glossary_handler(term, "hide")))
        button.addEventListener("blur", create_proxy(_make_glossary_handler(term, "hide")))
    document.getElementById("glossary-more-button").addEventListener("click", create_proxy(on_glossary_more))
    document.getElementById("report-toggle-button").addEventListener("click", create_proxy(on_toggle_report))
    document.getElementById("report-copy-button").addEventListener("click", create_proxy(on_copy_report))
    document.getElementById("report-print-button").addEventListener("click", create_proxy(on_print_report))
    document.getElementById("report-copy-area").hidden = True
    document.getElementById("band-change-note").hidden = True
