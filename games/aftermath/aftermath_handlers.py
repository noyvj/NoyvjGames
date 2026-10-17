"""Click and change handlers: every on_* function plus the handler factories (_make_*)."""

import info_page
from js import document, localStorage

import aftermath_runstate as runstate
from aftermath_achievements import _check_new_achievements_for_toast, update_achievements_display
from aftermath_actions import begin_second_founding, start_custom_run
from aftermath_bonuses import entry_aid, run_timer_enabled
from aftermath_challenges import (
    _builder_message, _custom_named, builder_draft, builder_move, builder_remove, delete_custom_schedule,
    render_ghost, save_custom_schedule, schedule_code,
)
from aftermath_chronicle import (
    buy_founding_skill, chronicle_note, chronicle_text, founding_kept_lost_text, founding_ready,
    put_away_founding_skill, render_chronicle,
)
from aftermath_codex import render_codex_panel, render_stats_panel
from aftermath_flourish import play_hit_effect
from aftermath_model_run import RunState
from aftermath_panels import (
    _confirm_dialog_ask, _display_skill_unlock_toast, _flash_element, _maybe_trigger_callouts,
    export_progress_code, import_progress_code, progress_summary_text, render_info_page, reset_refund_total,
    reset_skill_tree, update_changelog_display,
)
from aftermath_pastruns import (
    MENTOR_STORAGE_KEY, PAST_RUN_SORTS, render_mentor, render_past_runs_panel, set_run_archived,
    set_run_note, set_settlement_name, toggle_pin_skill,
)
from aftermath_persist import (
    CUSTOM_MAX_EVENTS, FOUNDING_SKILLS, GHOST_STORAGE_KEY, PRESET_NAME_MAX, _clean_name, _el, _focus,
    _storage_write,
)
from aftermath_renderer import render
from aftermath_rules import EVENT_LABEL, GROWTH_COST, RESILIENCE_COST, SCENARIOS, SKILLS
from aftermath_runview import _copy_to_clipboard, announce, event_announcement, run_summary_text
from aftermath_skillmap import note_skill_reveal, render_skill_move, reveal_text, skill_rank_callout_text
from aftermath_tools import (
    _int_or_zero, apply_preset, clear_skill_filters, delete_preset, save_preset, this_turn_allocation,
)


def on_neighbour_aid_setting(event=None):
    render()


def on_toggle_achievements(event=None):
    runstate.achievements_open = not runstate.achievements_open
    update_achievements_display()


def on_toggle_info_page(event=None):
    runstate.info_page_open = info_page.toggle(runstate.info_page_open)
    render_info_page()


def on_toggle_mentor(event=None):
    runstate.mentor_enabled = document.getElementById("mentor-toggle").checked
    _storage_write(MENTOR_STORAGE_KEY, "1" if runstate.mentor_enabled else "0")
    render_mentor()


def on_toggle_past_runs(event=None):
    runstate.past_runs_open = not runstate.past_runs_open
    render_past_runs_panel()


def on_past_runs_event(event=None):
    """One delegated handler for everything inside the Past Runs list: the note boxes, the
    Compare ticks and the Archive buttons (cards are rebuilt on every render, so a handler
    per card would pile up)."""
    target = getattr(event, "target", None)
    if target is None:
        return
    action = target.getAttribute("data-action")
    raw_run = target.getAttribute("data-run")
    if not action or raw_run is None or not str(raw_run).isdigit():
        return
    run_number = int(raw_run)
    if action == "note":
        set_run_note(run_number, target.value)
    elif action == "archive":
        set_run_archived(run_number, run_number not in runstate.meta["archived_runs"])
        render()
    elif action == "compare":
        if target.checked:
            if run_number not in runstate.past_runs_compare:
                runstate.past_runs_compare = (runstate.past_runs_compare + [run_number])[-2:]
        else:
            runstate.past_runs_compare = [n for n in runstate.past_runs_compare if n != run_number]
        render()


def on_past_runs_controls_change(event=None):
    sort_el = document.getElementById("past-runs-sort")
    filter_el = document.getElementById("past-runs-filter")
    archived_el = document.getElementById("past-runs-archived")
    if sort_el is not None and sort_el.value in PAST_RUN_SORTS:
        runstate.past_runs_sort = sort_el.value
    if filter_el is not None:
        value = filter_el.value
        if value in ("all", "standard", "extended", "custom") or (value.startswith("scenario:") and value.split(":", 1)[1] in SCENARIOS):
            runstate.past_runs_filter = value
    if archived_el is not None:
        runstate.past_runs_show_archived = bool(archived_el.checked)
    render()


def on_toggle_changelog(event=None):
    runstate.changelog_open = not runstate.changelog_open
    update_changelog_display()


def on_export_progress(event=None):
    document.getElementById("progress-export-output").value = export_progress_code()
    document.getElementById("progress-code-status").innerText = (
        "Progress code generated below — copy it somewhere safe. Contains: " + progress_summary_text()
    )


def on_import_progress(event=None):
    code = document.getElementById("progress-import-input").value
    status = document.getElementById("progress-code-status")
    if not code or not code.strip():
        status.innerText = "Paste a progress code first."
        return
    if import_progress_code(code):
        status.innerText = "Progress imported successfully."
        render()
    else:
        status.innerText = "That code couldn't be read — check you copied the whole thing."


def on_reset_skill_tree(event=None):
    if not runstate.skill_tree.unlocked:
        return  # nothing to lose -- render()'s own disabled-state already guards this too

    def _do_reset():
        reset_skill_tree()
        render()

    _confirm_dialog_ask(
        action_id="aftermath-reset-skill-tree",
        message=(
            f"Reset the skill tree? This refunds all {reset_refund_total()} knowledge points "
            "spent and unspent, and clears every unlocked skill. Your lifetime knowledge total "
            "is not affected. This cannot be undone."
        ),
        confirm_label="Reset skill tree",
        on_confirm=_do_reset,
    )


def on_toggle_codex(event=None):
    runstate.codex_open = not runstate.codex_open
    render_codex_panel()


def on_toggle_stats(event=None):
    runstate.stats_open = not runstate.stats_open
    render_stats_panel()


def on_copy_run_summary(event=None):
    text = run_summary_text()
    status = document.getElementById("copy-run-summary-status")
    area = document.getElementById("copy-run-summary-area")
    if _copy_to_clipboard(text):
        area.hidden = True
        status.innerText = "Copied the run summary to the clipboard."
    else:
        area.hidden = False
        area.value = text
        status.innerText = "Could not copy automatically. Select the text below and copy it yourself."


def on_skill_search(event=None):
    search = _el("skill-search-input")
    runstate.skill_search_text = str(search.value or "") if search is not None else ""
    render()


def on_skill_map_search(event=None):
    """E-2: the map's own search box feeds the same search text as the list's."""
    search = _el("skill-map-search-input")
    runstate.skill_search_text = str(search.value or "") if search is not None else ""
    render()


def on_skill_filter_clear(event=None):
    clear_skill_filters()
    render()


def on_preset_save(event=None):
    name_el = _el("preset-name-input")
    ok, message = save_preset(
        name_el.value if name_el is not None else "",
        _int_or_zero(_el("preset-resilience-input").value),
        _int_or_zero(_el("preset-growth-input").value),
    )
    runstate.preset_status_text = message
    if ok:
        runstate.preset_selected = _clean_name(name_el.value, PRESET_NAME_MAX)
    render()
    announce(message)


def on_preset_from_turn(event=None):
    resilience, growth = this_turn_allocation()
    _el("preset-resilience-input").value = str(resilience)
    _el("preset-growth-input").value = str(growth)
    runstate.preset_status_text = (
        f"Filled in {resilience} resilience, {growth} growth from this turn. Name it and press Save."
        if resilience or growth else "Nothing bought this turn yet: buy some units first, or type the numbers."
    )
    render()


def on_preset_apply(event=None):
    select = _el("preset-select")
    name = select.value if select is not None else runstate.preset_selected
    message, _r, _g = apply_preset(name)
    runstate.preset_status_text = message
    render()
    announce(message)
    _check_new_achievements_for_toast()


def on_preset_select(event=None):
    select = _el("preset-select")
    if select is not None:
        runstate.preset_selected = select.value


def on_preset_list_event(event=None):
    target = getattr(event, "target", None)
    if target is None:
        return
    action, name = target.getAttribute("data-action"), target.getAttribute("data-name")
    if not action or not name:
        return
    if action == "apply":
        message, _r, _g = apply_preset(name)
        runstate.preset_status_text = message
        announce(message)
        _check_new_achievements_for_toast()
    elif action == "delete" and delete_preset(name):
        runstate.preset_status_text = f"Deleted preset {name}."
        announce(runstate.preset_status_text)
    render()


def on_save_health_export(event=None):
    """One click: builds the progress code, shows it selected in a box and tries the clipboard."""
    area = _el("save-health-code")
    status = _el("save-health-code-status")
    code = export_progress_code()
    if area is not None:
        area.hidden = False
        area.value = code
        _focus(area)
        try:
            area.select()
        except Exception:
            pass
    copied = _copy_to_clipboard(code)
    if status is not None:
        status.innerText = (
            "Copied your progress code. Paste it somewhere safe; Import Progress restores it."
            if copied else
            "Copy this code and keep it somewhere safe; Import Progress (Backup / Transfer) restores it."
        )


def on_toggle_ghost(event=None):
    toggle = _el("ghost-toggle")
    on = True if toggle is None else bool(toggle.checked)
    _storage_write(GHOST_STORAGE_KEY, "1" if on else "0")
    render_ghost()


def on_builder_clear(event=None):
    del builder_draft[:]
    _builder_message("Cleared the draft.")


def on_builder_save(event=None):
    name_el = _el("builder-name-input")
    ok, message = save_custom_schedule(name_el.value if name_el is not None else "")
    _builder_message(message)


def on_builder_draft_event(event=None):
    target = getattr(event, "target", None)
    if target is None:
        return
    action, raw = target.getAttribute("data-action"), target.getAttribute("data-index")
    if not action or raw is None or not str(raw).isdigit():
        return
    index = int(raw)
    if action == "remove" and builder_remove(index):
        _builder_message(f"Removed event {index + 1}. {len(builder_draft)} of {CUSTOM_MAX_EVENTS} events.")
        _focus(_el("builder-draft"))
    elif action in ("up", "down") and builder_move(index, -1 if action == "up" else 1):
        _builder_message(f"Moved event {index + 1} {action}.")
        _focus(_el("builder-draft"))


def on_builder_saved_event(event=None):
    target = getattr(event, "target", None)
    if target is None:
        return
    action, name = target.getAttribute("data-action"), target.getAttribute("data-name")
    entry = _custom_named(name) if name else None
    if not action or entry is None:
        return
    if action == "load":
        builder_draft[:] = list(entry["events"])
        name_el = _el("builder-name-input")
        if name_el is not None:
            name_el.value = entry["name"]
        _builder_message(f"Loaded {entry['name']} into the draft.")
    elif action == "run":
        message = start_custom_run(entry["name"])
        _builder_message(message)
    elif action == "delete":
        delete_custom_schedule(entry["name"])
        _builder_message(f"Deleted schedule {entry['name']}.")
    elif action == "share":
        code = schedule_code(entry["events"])
        area = _el("builder-code")
        if area is not None and code:
            area.hidden = False
            area.value = code
            _focus(area)
            try:
                area.select()
            except Exception:
                pass
        copied = bool(code) and _copy_to_clipboard(code)
        _builder_message(
            f"Copied the code for {entry['name']}: a friend can paste it under Run codes and challenges." if copied
            else f"The code for {entry['name']} is in the box below: copy it and send it to a friend."
        )


def on_undo_allocation(event=None):
    if runstate.run.undo_last_allocation():
        announce(f"Undid the last allocation. Resources {runstate.run.resources:.0f}, resilience {runstate.run.resilience_capacity}, growth {runstate.run.growth_capacity}.")
    render()


def on_invest_resilience(event=None):
    bought = runstate.run.invest_steps("resilience", runstate.invest_step)
    render()
    if bought:
        _flash_element("resources-display")
        announce(f"Invested in resilience x{bought}. Resilience {runstate.run.resilience_capacity}, resources {runstate.run.resources:.0f}.")
    _check_new_achievements_for_toast()


def on_invest_growth(event=None):
    bought = runstate.run.invest_steps("growth", runstate.invest_step)
    render()
    if bought:
        _flash_element("resources-display")
        announce(f"Invested in growth x{bought}. Growth {runstate.run.growth_capacity}, resources {runstate.run.resources:.0f}.")
    _check_new_achievements_for_toast()


# E-28: an optional "you still have resources" check before Face Next Event. Off by default
# (the Settings checkbox writes this key); it only ever asks, never changes a number.
CONFIRM_UNSPENT_STORAGE_KEY = "aftermath-confirm-unspent"


def confirm_unspent_enabled():
    return localStorage.getItem(CONFIRM_UNSPENT_STORAGE_KEY) == "true"


def unspent_confirm_message(run_state):
    """The question, naming what the unspent resources could still have bought, or
    None when there is nothing worth asking about (the run is over, or the
    resources cannot buy even one unit)."""
    if run_state.is_complete() or run_state.resources < min(RESILIENCE_COST, GROWTH_COST):
        return None
    resilience = run_state.step_units("resilience", "max")
    growth = int(run_state.resources // GROWTH_COST)
    options = []
    if resilience:
        options.append(f"up to {resilience} resilience")
    if growth:
        options.append(f"up to {growth} growth")
    return (
        f"Keep {run_state.resources:.0f} resources unspent? You could still buy {' or '.join(options)} "
        f"before {EVENT_LABEL[run_state.next_event_type()]} hits."
    )


def on_resolve_event(event=None):
    message = unspent_confirm_message(runstate.run) if confirm_unspent_enabled() else None
    if message is None:
        _resolve_event_now()
        return
    _confirm_dialog_ask(
        action_id="aftermath-unspent-resources",
        message=message,
        confirm_label="Face the event",
        on_confirm=_resolve_event_now,
        allow_skip=False,  # the Settings checkbox is the switch, so no hidden "don't ask again"
    )


def _resolve_event_now():
    before = len(runstate.run.event_log)
    runstate.run.resolve_next_event()
    _maybe_trigger_callouts(runstate.run)
    render()
    if len(runstate.run.event_log) > before:
        rank_text = skill_rank_callout_text() if runstate.run.is_complete() else ""
        aid_text = f" Neighbouring towns sent {entry_aid(runstate.run.event_log[-1]):.0f} resources." if entry_aid(runstate.run.event_log[-1]) else ""  # R-31
        announce(event_announcement(runstate.run.event_log[-1]) + aid_text + (" " + rank_text if rank_text else ""))  # E-5 / E-11
        play_hit_effect(runstate.run.event_log[-1])  # GE-14
    _check_new_achievements_for_toast()


def on_scenario_change(event=None):
    """E17a: picking a scenario before the current run's first event swaps its
    schedule immediately; between runs it is read by start_new_run(); once a
    run is underway the choice can no longer change it."""
    value = document.getElementById("scenario-select").value
    if value in SCENARIOS and runstate.run.event_index == 0 and not runstate.run.is_complete() and not runstate.run.normalised:
        runstate.run = RunState(run_number=runstate.run.run_number, extended=runstate.run.extended, scenario=value)
    render()


def _make_pin_handler(skill_id):
    def handler(event=None):
        toggle_pin_skill(skill_id)
        render()
    return handler


def on_settlement_name_change(event=None):
    set_settlement_name(document.getElementById("settlement-name-input").value)
    render()


def on_skill_move(event=None):
    from_id = _el("skill-move-from").value
    to_id = _el("skill-move-to").value
    if runstate.skill_tree.move(from_id, to_id):
        runstate.skill_move_message = f"Moved from {SKILLS[from_id]['label']} to {SKILLS[to_id]['label']}. Knowledge left: {runstate.skill_tree.knowledge_points}."
        chronicle_note("move", f"Moved a point from {SKILLS[from_id]['label']} to {SKILLS[to_id]['label']}.")  # E-7
        note_skill_reveal(to_id)  # GE-16
        announce(runstate.skill_move_message + " " + reveal_text())
    else:
        runstate.skill_move_message = runstate.skill_tree.move_check(from_id, to_id)[1] or "That move is not possible."
    status = _el("skill-move-status")
    if status is not None:
        status.innerText = runstate.skill_move_message
    render()
    runstate.skill_move_message = ""


def on_skill_move_select(event=None):
    runstate.skill_move_message = ""
    render_skill_move()


def _make_unlock_handler(skill_id):
    def handler(event=None):
        unlocked = runstate.skill_tree.unlock(skill_id)
        if unlocked:
            chronicle_note("skill", f"Adopted {SKILLS[skill_id]['label']} ({SKILLS[skill_id]['cost']} knowledge).")  # E-7
            note_skill_reveal(skill_id)  # GE-16: before render, so the map and the list light up the new children
        render()
        if unlocked:
            _display_skill_unlock_toast(skill_id)
        _check_new_achievements_for_toast()
    return handler


def on_skill_map_unlock(event=None):
    if runstate.skill_map_selected in SKILLS:
        _make_unlock_handler(runstate.skill_map_selected)()


def on_skill_map_pin(event=None):
    if runstate.skill_map_selected in SKILLS:
        toggle_pin_skill(runstate.skill_map_selected)
        render()


def on_founding_begin(event=None):
    if not founding_ready():
        return

    def _do():
        ok, text = begin_second_founding()
        runstate.founding_message_text = text
        render()

    _confirm_dialog_ask(
        action_id="aftermath-second-founding",
        message="Begin a Second Founding? " + founding_kept_lost_text() + " This cannot be undone, and nothing in the game needs it.",
        confirm_label="Begin the Second Founding",
        on_confirm=_do,
        allow_skip=False,
    )


def on_founding_event(event=None):
    target = getattr(event, "target", None)
    if target is None:
        return
    action, skill_id = target.getAttribute("data-action"), target.getAttribute("data-founding")
    if skill_id not in FOUNDING_SKILLS:
        return
    if action == "buy" and buy_founding_skill(skill_id):
        runstate.founding_message_text = f"{FOUNDING_SKILLS[skill_id]['label']} is yours. {FOUNDING_SKILLS[skill_id]['gain']}; the price: {FOUNDING_SKILLS[skill_id]['price']}."
    elif action == "away" and put_away_founding_skill(skill_id):
        runstate.founding_message_text = f"{FOUNDING_SKILLS[skill_id]['label']} put away; {FOUNDING_SKILLS[skill_id]['cost']} knowledge refunded."
    else:
        return
    announce(runstate.founding_message_text)
    render()


def on_run_timer_setting(event=None):
    """Switching the timer off ends timing for the run in progress (its time would be partial)."""
    if not run_timer_enabled() and runstate.run.timed:
        runstate.run.timed = False
        runstate.run._timer_last = None
    render()


def on_toggle_chronicle(event=None):
    runstate.chronicle_open = not runstate.chronicle_open
    render_chronicle()


def on_copy_chronicle(event=None):
    text = chronicle_text()
    status = _el("chronicle-copy-status")
    area = _el("chronicle-copy-area")
    if _copy_to_clipboard(text):
        if area is not None:
            area.hidden = True
        if status is not None:
            status.innerText = "Copied the chronicle to the clipboard."
    else:
        if area is not None:
            area.hidden = False
            area.value = text
        if status is not None:
            status.innerText = "Could not copy automatically. Select the text below and copy it yourself."
