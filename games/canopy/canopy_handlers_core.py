"""Click handlers for plots and regions (clear, replant, tend, names, undo, hotkeys, survey queue)."""

import json

import canopy_runstate as runstate
from canopy_clearcut import CLEAR_CUT_BONUS, _note_harvester_badge
from canopy_expedition import expedition_payout_multiplier
from canopy_forecast import _hotkey_refusal, render_announcer
from canopy_hazards import relieve_blight
from canopy_helpers import _announce, _log_event, _plot_ref, _write_local_storage_item, plot_coordinate_label
from canopy_plotsheet import close_plot_sheet
from canopy_records import PERSONAL_BEST_STORAGE_KEY, personal_best
from canopy_regions import note_wetland_wildlife, wetland_plot_coordinate_label, wetland_plot_flooded
from canopy_renderer import render, reset_session
from canopy_rules import (
    BARE, CLEAR_CUT_HEAL_TICKS, DIFFICULTY_NORMAL, SCENARIO_NONE, SEASON_CYCLE_TICKS, SPECIES,
    SPECIES_MANGROVE, SPECIES_STANDARD, species_planted,
)
from canopy_survey import _leave_survey_mode, _survey_find, survey_can_queue, survey_queue
from canopy_tend import (
    _arm_undo, _clean_name, _event_value, _tendable, _tended_plot, render_tend_panel, render_undo_chip,
)
from canopy_worldvars import CHALLENGE_NONE, FOREST_NAME_MAX, NICKNAME_MAX, PACE_NORMAL, TEND_DURATION_TICKS


def on_highland_clear(event=None):
    if runstate.highland_selected_index is None:
        return
    payout = runstate.highland_plots[runstate.highland_selected_index].clear()
    if payout is not None:
        runstate.highland_income += payout
    render()


def on_highland_replant(event=None):
    if runstate.highland_selected_index is None:
        return
    runstate.highland_plots[runstate.highland_selected_index].replant()
    render()


def on_wetland_clear(event=None):
    if runstate.wetland_selected_index is None:
        return
    payout = runstate.wetland_plots[runstate.wetland_selected_index].clear()
    if payout is not None:
        runstate.wetland_income += payout
    render()


def on_wetland_replant(event=None):
    if runstate.wetland_selected_index is None:
        return
    if wetland_plot_flooded(runstate.wetland_selected_index):  # GB-24: no seedlings under water
        _announce("That plot is under water: plant a mangrove, or wait for the tide to turn.")
        return
    runstate.wetland_plots[runstate.wetland_selected_index].replant()
    render()


def on_wetland_mangrove(event=None):
    """GB-24: plants a mangrove, which only takes root on a bare plot that is under water right now."""
    if runstate.wetland_selected_index is None or not wetland_plot_flooded(runstate.wetland_selected_index):
        _announce("Mangroves are planted on flooded plots: wait for this plot to go under water.")
        return False
    plot = runstate.wetland_plots[runstate.wetland_selected_index]
    if plot.replant(species=SPECIES_MANGROVE):
        _log_event("replant", f"Planted a mangrove on wetland plot {wetland_plot_coordinate_label(plot.index)}", None)
        note_wetland_wildlife()
    render()
    return True


def tend_plot(index=None):
    """GB-4: a short growth boost (TEND_GROWTH_MULTIPLIER for
    TEND_DURATION_TICKS ticks; a replanting plot recovers an extra tick per
    tick) on one plot, then a TEND_COOLDOWN_TICKS cooldown. `index` is the
    hovered plot (the "T" key); without one it uses the selected plot."""
    if index is None:
        index = runstate.selected_index
    if isinstance(index, bool) or not isinstance(index, (int, float)) or index != index:
        index = None
    else:
        index = int(index)
    if index is None or not (0 <= index < len(runstate.plots)):
        runstate._tend_message = "Hover or select a plot first."
        render_tend_panel()
        return False
    plot = runstate.plots[index]
    if _tended_plot() is not None or runstate.tend_cooldown_ticks > 0:
        runstate._tend_message = ""
        render_tend_panel()
        return False
    if not _tendable(plot):
        runstate._tend_message = "A bare plot has nothing to tend yet: replant it first."
        render_tend_panel()
        return False
    plot.tend_ticks_left = TEND_DURATION_TICKS
    relieve_blight(index)  # GB-7
    runstate.tends_done += 1  # GB-9: counts toward a Ranger contract
    runstate._tend_message = ""
    _log_event("tend", f"Tended {_plot_ref(index)}", index)
    render()
    return True


def on_tend(event=None):
    tend_plot()


def set_forest_name(value):
    cleaned = _clean_name(value, FOREST_NAME_MAX)
    if cleaned == runstate.forest_name:
        return False
    runstate.forest_name = cleaned
    if cleaned:
        _log_event("name", f"The forest was named {cleaned}")
    render()
    return True


def set_plot_nickname(value):
    """Nicknames the adopted plot (B27); ignored when no plot is adopted."""
    if runstate.adopted_plot_index is None:
        return False
    cleaned = _clean_name(value, NICKNAME_MAX)
    if cleaned == runstate.adopted_plot_nickname:
        return False
    runstate.adopted_plot_nickname = cleaned
    if cleaned:
        _log_event(
            "name",
            f"{plot_coordinate_label(runstate.adopted_plot_index)} is now known as {cleaned}",
            runstate.adopted_plot_index,
        )
    render()
    return True


def on_forest_name_change(event=None):
    set_forest_name(_event_value(event))


def on_plot_nickname_change(event=None):
    set_plot_nickname(_event_value(event))


def undo_last_clear(event=None):
    """Restores the plot cleared in the last UNDO_WINDOW_MS (not in Ranger
    difficulty). Only valid while that plot is still bare from that clear."""
    snapshot = runstate._undo_snapshot
    if snapshot is None:
        return False
    runstate._undo_snapshot = None
    plot = runstate.plots[snapshot["plot"]]
    if plot.state != BARE or plot.clear_count != snapshot["clear_count_after"]:
        render_undo_chip()
        return False
    plot.__dict__.update(snapshot["fields"])
    if personal_best["income"] <= runstate.total_income + 1e-9 and personal_best["income"] > snapshot["best_income_before"]:
        # The undone payout had just set the income record: take the record back too.
        personal_best["income"] = snapshot["best_income_before"]
        _write_local_storage_item(PERSONAL_BEST_STORAGE_KEY, json.dumps(personal_best))
    runstate.total_income = max(0.0, runstate.total_income - snapshot["payout"])
    if snapshot.get("cut"):
        runstate.clear_cuts_total = max(0, runstate.clear_cuts_total - 1)
    runstate.season_cleared = snapshot["season_cleared_before"]
    if snapshot["log_entry"] in runstate.forest_log:
        runstate.forest_log.remove(snapshot["log_entry"])
    _log_event("preserve", f"Took back the clear: {_plot_ref(plot.index)} is standing again", plot.index)
    render()
    return True


def hotkey_clear_cut_selected(event=None):
    """K: clear-cuts the selected plot (select one first, the same deliberate two steps as C)."""
    if runstate.selected_index is None:
        _announce("No plot selected. Select a plot with Enter or a click, then press K to clear-cut it")
        render_announcer()
        return False
    before = runstate.plots[runstate.selected_index].state
    on_clear_cut()
    changed = runstate.plots[runstate.selected_index].state != before
    if not changed and runstate.selected_index is not None and not runstate.survey_mode:
        _announce(_hotkey_refusal(runstate.selected_index, "cut"))
        render_announcer()
    return changed


def hotkey_clear_selected(event=None):
    """C: clears the selected plot (select one first: a deliberate two-step so a stray key cannot fell a tree)."""
    if runstate.selected_index is None:
        _announce("No plot selected. Select a plot with Enter or a click, then press C to clear it")
        render_announcer()
        return False
    before = runstate.plots[runstate.selected_index].state
    on_clear()
    changed = runstate.plots[runstate.selected_index].state != before
    if not changed and not (runstate.survey_mode and survey_queue):
        _announce(_hotkey_refusal(runstate.selected_index, "clear"))
        render_announcer()
    return changed


def hotkey_replant_selected(event=None):
    """R: replants the selected bare plot."""
    if runstate.selected_index is None:
        _announce("No plot selected. Select a plot with Enter or a click, then press R to replant it")
        render_announcer()
        return False
    before = runstate.plots[runstate.selected_index].state
    on_replant()
    changed = runstate.plots[runstate.selected_index].state != before
    if not changed and not (runstate.survey_mode and survey_queue):
        _announce(_hotkey_refusal(runstate.selected_index, "replant"))
        render_announcer()
    return changed


def on_pace_change(event=None):
    if event is None:
        return
    reset_session(pace=event.target.value)


def on_clear(event=None):
    _manual_clear(cut=False)


def _manual_clear(cut):
    """Clear (or, with cut=True, the GB-21 clear-cut) on the selected main-forest plot."""
    if runstate.selected_index is None:
        return
    if runstate.survey_mode:  # B-13: planning only, nothing happens until Commit
        if cut:
            _announce("Clear-cut is not part of a Survey plan. Use Clear, or leave Survey mode first")
            return
        queue_survey_action("clear", runstate.selected_index)
        return
    if runstate.selected_index == runstate.heart_tree_index:
        return  # GB-8: the Heart Tree is never felled
    plot = runstate.plots[runstate.selected_index]
    before_fields = dict(plot.__dict__)
    best_income_before = personal_best["income"]
    payout = plot.clear_cut() if cut else plot.clear()
    if payout is not None:
        bonus = payout - payout / (1 + CLEAR_CUT_BONUS) if cut else 0.0
        payout *= expedition_payout_multiplier()  # GB-3: the Expedition's Trade route upgrade (1.0 outside one)
        runstate.total_income += payout
        if cut:  # GB-21
            runstate.clear_cuts_total += 1
            _log_event(
                "clear",
                f"Clear-cut {_plot_ref(runstate.selected_index)} for {payout:.1f} income (+{bonus:.1f} bonus); its soil dips and heals over about {CLEAR_CUT_HEAL_TICKS // SEASON_CYCLE_TICKS} seasons",
                runstate.selected_index,
            )
        else:
            _log_event("clear", f"Cleared {_plot_ref(runstate.selected_index)} for {payout:.1f} income", runstate.selected_index)
        was_cleared = runstate.season_cleared
        runstate.season_cleared = True  # GB-30
        _arm_undo(runstate.selected_index, before_fields, payout, runstate.forest_log[-1], was_cleared, best_income_before, cut=cut)  # GB-18
        if cut:
            _note_harvester_badge()
    render()


def on_clear_cut(event=None):
    _manual_clear(cut=True)


def on_replant(event=None):
    if runstate.selected_index is None:
        return
    if runstate.survey_mode:  # B-13
        queue_survey_action("replant", runstate.selected_index)
        return
    if runstate.plots[runstate.selected_index].replant(species=runstate.species_choice if runstate.species_choice != SPECIES_MANGROVE else None):  # GB-6
        runstate.total_replants += 1
        if runstate.species_choice != SPECIES_STANDARD:
            species_planted.add(runstate.species_choice)
        label = SPECIES[runstate.species_choice]["label"].lower() if runstate.species_choice != SPECIES_STANDARD else ""
        _log_event("replant", f"Replanted {_plot_ref(runstate.selected_index)}" + (f" with {label}" if label else ""), runstate.selected_index)
    render()


def start_new_forest():
    """A new, empty forest from the forest menu: the plain starting game (normal grid, difficulty and pace, no
    challenge, scenario, level, custom layout or expedition). Meta-progress (levels done, Seed Vault, bests) and
    achievements belong to the browser, not to one forest, and are untouched."""
    return reset_session(
        grid_size="normal", difficulty=DIFFICULTY_NORMAL, challenge=CHALLENGE_NONE, pace=PACE_NORMAL,
        scenario=SCENARIO_NONE, level=None, layout=None, expedition=None,
    )


def queue_survey_action(kind, plot=None):
    """Adds an action to the plan; asking again for the same action takes it back out. Returns True if the plan changed."""
    if not runstate.survey_mode:
        return False
    if kind == "decline" and plot is None and runstate.pending_stakeholder_request is not None:
        plot = runstate.pending_stakeholder_request["plot_index"]
    if plot is None:
        return False
    existing = _survey_find(kind, plot)
    if existing is not None:
        survey_queue.remove(existing)
        # Taking a clear back out also removes a replant that depended on it.
        if kind == "clear":
            dependent = _survey_find("replant", plot)
            if dependent is not None and runstate.plots[plot].state != BARE:
                survey_queue.remove(dependent)
        render()
        return True
    allowed, reason = survey_can_queue(kind, plot)
    if not allowed:
        _announce(reason)
        return False
    survey_queue.append({"kind": kind, "plot": plot})
    render()
    return True


def enter_survey_mode(event=None):
    runstate.survey_mode = True
    survey_queue.clear()
    close_plot_sheet()
    render()


def cancel_survey(event=None):
    _leave_survey_mode()
    render()
