"""Click and change handlers: every on_* function that changes the game, plus the factories that build them."""

import copy

import info_page
from js import document

import tide_runstate as runstate
from tide_achievements import update_achievements_display
from tide_actions import (
    record_autosave, restore_autosave, rewind_season, start_daily, start_new_run, take_rewind_snapshot,
)
from tide_almanac import planner_plan, render_almanac, render_planner
from tide_bridge import _write_local_storage_item
from tide_chrome import (
    _copy_to_clipboard, _show_copy_fallback, announce, render_graph_controls,
    update_session_summary_display,
)
from tide_coastline import _resync_previous_flooded_rows, scrub_to
from tide_coasts import flooded_row_count
from tide_daily import _daily_ui, daily_today, render_daily
from tide_events import POSTCARD_MIN_SEASONS, _postcard_status, collect_postcard
from tide_flavour import (
    SCENE_THEMES, SCENE_THEME_KEY, _delta_open, render_delta_popover, render_scene_theme, speak_quip,
    theme_unlocked,
)
from tide_graphs import _save_graph_prefs, render_graphs
from tide_library import library_save_current
from tide_libraryview import render_library
from tide_loading import load_state
from tide_panels import render_info_page, update_changelog_display
from tide_readouts import (
    AFFORD_PIN_KEY, apply_rolled_name, check_pinned_goal, pin_goal, render_afford, render_goal,
    roll_harbor_name,
)
from tide_renderer import render
from tide_rules import (
    ADVANCE_BATCH, CATEGORIES, INVEST_LABELS, PLANNER_MAX_SEASONS, PLANNER_MIN_SEASONS, WORKSHOP_DEFAULTS,
)
from tide_runcode import clear_ghosts, load_ghost
from tide_seasonflow import _season_numbers, note_action, record_speedrun, show_season_report
from tide_ticker import render_ledger, render_live_ticker, render_ticker_history
from tide_workshop import clean_workshop_value, render_workshop, workshop_pending


def on_toggle_info_page(event=None):
    runstate.info_page_open = info_page.toggle(runstate.info_page_open)
    render_info_page()


def on_toggle_achievements(event=None):
    runstate.achievements_open = not runstate.achievements_open
    update_achievements_display()


def on_toggle_changelog(event=None):
    runstate.changelog_open = not runstate.changelog_open
    update_changelog_display()


def on_toggle_session_summary(event=None):
    runstate.session_summary_open = not runstate.session_summary_open
    update_session_summary_display()


def on_ticker_search(event):
    runstate.ticker_search = str(event.target.value or "")
    render_ticker_history()


def on_live_search(event):
    runstate.live_ticker_search = str(event.target.value or "")
    render_live_ticker()


def on_toggle_ledger(event=None):
    runstate.ledger_open = not runstate.ledger_open
    render_ledger()


def on_toggle_graph_markers(event=None):
    runstate.graph_markers = not runstate.graph_markers
    _save_graph_prefs()
    render_graph_controls()
    render_graphs()
    render_library()
    render_planner()


def on_scrub_input(event=None):
    target = getattr(event, "target", None)
    try:
        position = int(float(getattr(target, "value", "")))
    except (TypeError, ValueError):
        return
    scrub_to(position)


def on_scrub_live(event=None):
    scrub_to(runstate.state.season)


def on_toggle_library(event=None):
    runstate.library_open = not runstate.library_open
    render_library()


def on_library_save(event=None):
    library_save_current()
    render_library()


def on_run_code_load(event=None):
    field = document.getElementById("run-code-input")
    text = str(getattr(field, "value", "") or "")
    if load_ghost(text):
        if field is not None:
            field.value = ""
        render_graphs()
    render_library()


def on_run_code_clear(event=None):
    clear_ghosts()
    render_graphs()
    render_library()


def on_toggle_daily(event=None):
    runstate.daily_open = not runstate.daily_open
    render_daily()


def on_daily_date_change(event=None):
    _daily_ui["confirm_date"] = ""
    _daily_ui["message"] = ""
    render_daily()


def on_daily_start(event=None):
    picker = document.getElementById("daily-date-input")
    chosen = str(getattr(picker, "value", "") or daily_today())
    if runstate.state.season > 1 and _daily_ui["confirm_date"] != chosen:
        _daily_ui["confirm_date"] = chosen
        _daily_ui["message"] = "This replaces your current run. Save it first with the save buttons if you want to keep it."
        render_daily()
        return
    start_daily(chosen)


def on_toggle_almanac(event=None):
    runstate.almanac_open = not runstate.almanac_open
    render_almanac()


def on_toggle_planner(event=None):
    runstate.planner_open = not runstate.planner_open
    render_planner()


def on_planner_length(event=None):
    try:
        value = int(float(getattr(getattr(event, "target", None), "value", "")))
    except (TypeError, ValueError):
        return
    runstate.planner_length = max(PLANNER_MIN_SEASONS, min(PLANNER_MAX_SEASONS, value))
    render_planner()


def on_planner_clear(event=None):
    for entry in planner_plan:
        for category in CATEGORIES:
            entry[category] = 0
    render_planner()


def on_planner_commit(event=None):
    """Applies the FIRST planned season for real (invest, then advance) and slides the
    rest of the plan up one place."""
    plan = planner_plan[0]
    bought = 0
    for category in CATEGORIES:
        for _ in range(plan[category]):
            if runstate.state.invest(category):
                bought += 1
    runstate.state.advance_season()
    del planner_plan[0]
    planner_plan.append({category: 0 for category in CATEGORIES})
    render()
    announce(f"Committed the first planned season: {bought} investment(s). " + runstate.state.season_result_text())
    _set_advance_note("")


def on_copy_text(event=None):
    text = runstate.state.share_text()
    status = document.getElementById("copy-text-status")
    area = document.getElementById("copy-text-area")
    if area is not None:
        area.hidden = True

    def done(_result=None):
        if status is not None:
            status.innerText = "Copied your settlement summary to the clipboard."

    def failed(_error=None):
        _show_copy_fallback(text)

    if _copy_to_clipboard(text, done, failed):
        if status is not None:
            status.innerText = "Copying..."
    else:
        _show_copy_fallback(text)


def on_afford_pin_change(event=None):
    select = document.getElementById("afford-pin-select")
    runstate.afford_pin = str(getattr(select, "value", "") or "")
    _write_local_storage_item(AFFORD_PIN_KEY, runstate.afford_pin)
    render_afford()


def on_goal_change(event=None):
    select = document.getElementById("goal-select")
    pin_goal(str(getattr(select, "value", "") or ""))
    render_goal()


def on_roll_name(event=None):
    name = apply_rolled_name(roll_harbor_name())
    name_input = document.getElementById("settlement-name-input")
    if name_input is not None:
        name_input.value = name
    announce(f"Harbour name: {name}.")
    render()


def on_rewind(event=None):
    rewind_season()


def on_scene_theme_change(event=None):
    select = document.getElementById("scene-theme-select")
    value = str(getattr(select, "value", "") or "")
    if value in SCENE_THEMES and theme_unlocked(value):
        _write_local_storage_item(SCENE_THEME_KEY, value)
    render_scene_theme()


def on_why_button(kind):
    def handler(event=None):
        _delta_open["kind"] = "" if _delta_open["kind"] == kind else kind
        render_delta_popover()
    return handler


def on_market_answer(accept):
    def handler(event=None):
        if runstate.state.answer_market(accept):
            check_pinned_goal()
            announce("Deal accepted." if accept else "Deal declined.")
        render()
    return handler


def on_crew_button(crew_id):
    def handler(event=None):
        if crew_id in runstate.state.crew:
            runstate.state.dismiss(crew_id)
        else:
            runstate.state.hire(crew_id)
        render()
    return handler


def on_autosave_click(event):
    target = getattr(event, "target", None)
    raw = target.getAttribute("data-slot") if target is not None and hasattr(target, "getAttribute") else None
    try:
        restore_autosave(int(raw))
    except (TypeError, ValueError):
        pass


def on_workshop_slider(key):
    def handler(event=None):
        element = document.getElementById(f"workshop-{key}")
        try:
            workshop_pending[key] = clean_workshop_value(key, float(element.value))
        except (TypeError, ValueError, AttributeError):
            return
        render_workshop()
    return handler


def on_workshop_apply(event=None):
    start_new_run(dict(workshop_pending))


def on_workshop_reset(event=None):
    workshop_pending.update(WORKSHOP_DEFAULTS)
    render_workshop()


def on_make_postcard(event=None):
    result = collect_postcard()
    _postcard_status["text"] = {
        "new": "A new postcard variant was added to your gallery.",
        "seen": "You already have this variant in your gallery.",
        "early": f"Play at least {POSTCARD_MIN_SEASONS} seasons (with standard rules) before a postcard counts for the gallery.",
    }[result]
    render()


def on_toggle_acid_boss(event=None):
    if runstate.state.acid_boss_result:
        return
    runstate.state.acid_boss_mode = not runstate.state.acid_boss_mode
    render()


def on_brace(event=None):
    if runstate.state.brace_for_acid_tide():
        announce("Braced for the Acid Tide.")
    render()


def on_brace_button(kind):
    def handler(event=None):
        if runstate.state.add_brace(kind):
            announce(f"Committed to {kind} for the storm.")
        render()
    return handler


def on_toggle_chess(event=None):
    runstate.state.set_chess_mode(not runstate.state.chess_mode)
    render()


def _make_invest_handler(category):
    def handler(event=None):
        funds_before = runstate.state.funds
        note_action()  # GD-23
        done = runstate.state.invest(category)
        record_speedrun()
        check_pinned_goal()  # GD-19
        render()
        if done:
            announce(f"Invested in {INVEST_LABELS[category]}. Funds now {runstate.state.funds:.0f}.")
        elif funds_before < runstate.state.invest_cost(category):
            announce(f"Not enough funds to invest in {INVEST_LABELS[category]}.")
    return handler


def on_advance_season(event=None):
    before = _season_numbers()
    take_rewind_snapshot()  # GD-20
    note_action()  # GD-23
    rows_before = flooded_row_count(runstate.state.sea_level)
    runstate.state.advance_season()
    speak_quip(new_rows=flooded_row_count(runstate.state.sea_level) - rows_before, rescued=False)  # GD-17
    check_pinned_goal()  # GD-19
    render()
    record_autosave()  # D-11
    show_season_report(before, _season_numbers())  # GD-30
    announce(runstate.state.season_result_text())
    _set_advance_note("")


def _set_advance_note(text):
    note = document.getElementById("advance-x5-note")
    if note is not None:
        note.innerText = text


def on_advance_x5(event=None):
    """D-15: up to five quiet seasons in one click; stops before any season
    that needs a decision and says why."""
    take_rewind_snapshot()  # GD-20
    note_action()  # GD-23
    ran, stop_text = runstate.state.advance_quiet_seasons(ADVANCE_BATCH)
    if ran:
        record_autosave()  # D-11
    render()
    if ran == 0:
        note = f"Not started: {stop_text}. Use Advance Season to go one at a time."
    elif stop_text:
        note = f"Ran {ran} season(s), then stopped: {stop_text}."
    else:
        note = f"Ran {ADVANCE_BATCH} quiet seasons."
    _set_advance_note(note)
    announce((runstate.state.season_result_text() + " " if ran else "") + note)


def on_output_mix_change(event):
    """D16: reads the <select>'s chosen value the same way Canopy's own
    on_grid_size_change() reads event.target.value from a real DOM change
    event; an unrecognized value is a silent no-op via set_output_mix()."""
    runstate.state.set_output_mix(event.target.value)
    render()


def on_sea_scenario_change(event):
    runstate.state.set_sea_scenario(event.target.value)
    render()


def on_coastline_change(event):
    if runstate.state.set_coastline(str(getattr(event.target, "value", ""))):
        _resync_previous_flooded_rows()
    render()


def on_enable_sister(event=None):
    if runstate.state.enable_sister():
        render()


def on_toggle_hard_lag(event=None):
    runstate.state.set_hard_lag_mode(not runstate.state.hard_lag_mode)
    render()


def _make_heritage_handler(site_id):
    def handler(event=None):
        runstate.state.protect_heritage(site_id)
        if runstate.state.last_rescue is not None:
            speak_quip(rescued=True)  # GD-17
        render()
    return handler


def on_retreat(event=None):
    runstate.state.managed_retreat()
    render()


def _make_diversify_handler(kind):
    def handler(event=None):
        runstate.state.diversify(kind)
        render()
    return handler


def on_set_checkpoint(event=None):
    runstate.state.set_checkpoint()
    render()


def replay_from_checkpoint():
    """D27: rewinds to the checkpoint, keeping a record of what happened
    afterwards in the abandoned run as "foresight" -- unlike D6's
    counterfactual (a what-if computed on the same history), the player
    actually plays the stretch again knowing what is coming."""
    if not runstate.state.can_replay():
        return False
    snapshot = copy.deepcopy(runstate.state.checkpoint)
    start = snapshot["season"]
    rise = runstate.state.sea_rise_per_season()
    foresight = []
    for season in range(start, runstate.state.season):
        index = season - 1
        if index >= len(runstate.state.damage_log) or index >= len(runstate.state.fish_yield_history):
            continue
        foresight.append(
            {
                "season": season,
                "fish_yield": runstate.state.fish_yield_history[index],
                "damage": runstate.state.damage_log[index],
                "flooded": flooded_row_count(rise * season),
            }
        )
    replays = runstate.state.replay_count + 1
    kept_ledger = [e for e in runstate.state.season_ledger if e["season"] < start]
    kept_snapshots = [x for x in runstate.state.season_snapshots if x[0] < start]
    load_state(snapshot)
    runstate.state.season_ledger = kept_ledger
    runstate.state.season_snapshots = kept_snapshots
    runstate.state.checkpoint = copy.deepcopy(snapshot)
    runstate.state.foresight = foresight
    runstate.state.replay_count = replays
    runstate.state._log_ticker(
        f"Replaying from Season {start} — you now know what the earlier run brought."
    )
    render()
    return True


def on_replay(event=None):
    replay_from_checkpoint()


def on_monitor(event=None):
    runstate.state.fund_monitoring()
    render()


def on_toggle_storms(event=None):
    runstate.state.set_storm_mode(not runstate.state.storm_mode)
    render()


def on_settlement_name_change(event):
    """D29: reads the text input's value on change."""
    if runstate.state.set_settlement_name(event.target.value) and runstate.state.settlement_name:
        if not any("Founded" in e["text"] for e in runstate.state.chronicle):
            runstate.state.chronicle.insert(0, {"season": runstate.state.season, "text": f"Founded as {runstate.state.settlement_name}."})
    render()


def on_set_baseline(event=None):
    runstate.state.set_comparison_baseline()
    render()
