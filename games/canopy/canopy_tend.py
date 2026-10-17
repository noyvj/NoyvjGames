"""Golden seedlings, Tend, the Heart Tree, forest and plot names, and Undo clear."""

import canopy_runstate as runstate
from canopy_effects import expedition_tend_cooldown
from canopy_helpers import _el, _gb_hash, _gb_toast, _log_event, _neighbour_indices, _plot_ref
from canopy_rules import ACCRUING_STATES, BARE, DIFFICULTY_RANGER, REPLANTING, STAKEHOLDER_KIND_CLEAR
from canopy_worldvars import (
    GOLDEN_SEEDLING_GAP_SPREAD, GOLDEN_SEEDLING_MIN_GAP, GOLDEN_SEEDLING_RECOVERY_TICKS,
    GOLDEN_SEEDLING_TICKS, HEART_TREE_MIN_MATURE_NEIGHBOURS, UNDO_WINDOW_TICKS, _pending_golden_bursts,
)


# --- GB-2: golden seedling ------------------------------------------------------

def _schedule_golden_seedling():
    runstate._golden_next_tick = runstate.forest_tick + GOLDEN_SEEDLING_MIN_GAP + _gb_hash(runstate.forest_tick, 3) % GOLDEN_SEEDLING_GAP_SPREAD


def _advance_golden_seedling():
    if runstate.golden_seedling is not None:
        runstate.golden_seedling["ticks_left"] -= 1
        if runstate.golden_seedling["ticks_left"] <= 0 or runstate.plots[runstate.golden_seedling["plot"]].state not in (BARE, REPLANTING):
            runstate.golden_seedling = None
            _schedule_golden_seedling()
        return
    if runstate.forest_tick < runstate._golden_next_tick:
        return
    candidates = [p.index for p in runstate.plots if p.state in (BARE, REPLANTING)]
    if not candidates:
        return  # nothing to grow on; try again next tick
    runstate.golden_seedling = {
        "plot": candidates[_gb_hash(runstate.forest_tick, 5) % len(candidates)],
        "ticks_left": GOLDEN_SEEDLING_TICKS,
    }


def collect_golden_seedling(index=None):
    """Banks a burst of recovery on the plot the golden seedling sits on (a
    bare plot is replanted first). `index` lets a tile click say which plot it
    was; the "G" key passes nothing. Returns True on a real collect."""
    if runstate.golden_seedling is None or (index is not None and index != runstate.golden_seedling["plot"]):
        return False
    plot = runstate.plots[runstate.golden_seedling["plot"]]
    runstate.golden_seedling = None
    runstate.seedlings_caught += 1  # GB-9: counts toward a Ranger contract
    _schedule_golden_seedling()
    if plot.state == BARE and plot.replant():
        runstate.total_replants += 1
        _log_event("replant", f"A golden seedling sprouted on {_plot_ref(plot.index)}", plot.index)
    if plot.state == REPLANTING:
        for _ in range(GOLDEN_SEEDLING_RECOVERY_TICKS):
            if plot.advance_recovery():
                runstate.total_recoveries += 1
                _log_event("recovered", f"{_plot_ref(plot.index)} finished recovering", plot.index)
                break
    _pending_golden_bursts.add(plot.index)
    _log_event("golden", f"Caught a golden seedling on {_plot_ref(plot.index)}", plot.index)
    return True


# --- GB-4: Tend ---------------------------------------------------------------------

def _tended_plot():
    for plot in runstate.plots:
        if plot.tend_ticks_left > 0:
            return plot
    return None


def _tendable(plot):
    return plot.state in ACCRUING_STATES or plot.state == REPLANTING


def tend_status_text():
    tended = _tended_plot()
    if tended is not None:
        return f"Tending {_plot_ref(tended.index)}: {tended.tend_ticks_left} more ticks of faster growth."
    if runstate.tend_cooldown_ticks > 0:
        return f"Tend is recharging: {runstate.tend_cooldown_ticks} ticks."
    return runstate._tend_message or "Tend is ready: hover a plot and press T, or select one and press Tend."


def _advance_tend():
    active = False
    for plot in runstate.plots:
        if plot.tend_ticks_left > 0:
            active = True
            plot.tend_ticks_left -= 1
            if plot.tend_ticks_left == 0:
                runstate.tend_cooldown_ticks = expedition_tend_cooldown()  # GB-3: 20 ticks, 10 with the Expedition's Tend rhythm upgrade
    if not active and runstate.tend_cooldown_ticks > 0:
        runstate.tend_cooldown_ticks -= 1


def render_tend_panel():
    button = _el("tend-button")
    status = _el("tend-status")
    if status is not None:
        status.innerText = tend_status_text()
    if button is None:
        return
    plot = runstate.plots[runstate.selected_index] if runstate.selected_index is not None else None
    busy = _tended_plot() is not None or runstate.tend_cooldown_ticks > 0
    button.disabled = busy or plot is None or not _tendable(plot)
    if _tended_plot() is not None:
        button.innerText = "\U0001F33F Tending..."
    elif runstate.tend_cooldown_ticks > 0:
        button.innerText = f"\U0001F33F Tend ({runstate.tend_cooldown_ticks})"
    else:
        button.innerText = "\U0001F33F Tend (T)"


# --- GB-8: the Heart Tree ------------------------------------------------------------

def _mature_neighbour_count(index):
    return sum(
        1
        for n in _neighbour_indices(index)
        if runstate.plots[n].state in ACCRUING_STATES and runstate.plots[n].maturity_fraction() >= 1.0
    )


def _find_heart_tree_centre():
    for plot in runstate.plots:
        if plot.state in ACCRUING_STATES and len(_neighbour_indices(plot.index)) == 8:
            if _mature_neighbour_count(plot.index) >= HEART_TREE_MIN_MATURE_NEIGHBOURS:
                return plot.index
    return None


def _check_heart_tree():
    """A standing plot ringed by HEART_TREE_MIN_MATURE_NEIGHBOURS fully mature
    plots (of its 8 neighbours) grows the Heart Tree. There is no hint of this
    anywhere in the UI; finding it is the reward."""
    if runstate.heart_tree_index is not None:
        return
    centre = _find_heart_tree_centre()
    if centre is None:
        return
    runstate.heart_tree_index = centre
    if (
        runstate.pending_stakeholder_request is not None
        and runstate.pending_stakeholder_request["plot_index"] == centre
        and runstate.pending_stakeholder_request.get("kind", STAKEHOLDER_KIND_CLEAR) == STAKEHOLDER_KIND_CLEAR
    ):
        runstate.pending_stakeholder_request = None  # nobody asks to fell the Heart Tree
    _log_event(
        "discovery",
        f"\U0001F333 The Heart Tree woke at {_plot_ref(centre)}: the ring of old trees around it gave it a "
        "place to grow. It will not be felled, and the plots around it thrive.",
        centre,
    )
    _gb_toast("\U0001F333 The forest has grown something ancient. The Heart Tree is awake.")


def _heart_tree_aura():
    if runstate.heart_tree_index is None:
        return frozenset()
    return frozenset(_neighbour_indices(runstate.heart_tree_index))


# --- GB-14: names ----------------------------------------------------------------------

def _clean_name(value, limit):
    if not isinstance(value, str):
        return ""
    printable = "".join(ch for ch in value if ch.isprintable())
    return " ".join(printable.split())[:limit]


def _event_value(event):
    return getattr(getattr(event, "target", None), "value", "")


def _sync_name_inputs():
    """Writes the saved names back into the two text fields (only on load,
    reset and adopt/release, never every render, so typing is never clobbered)."""
    forest_input = _el("forest-name-input")
    if forest_input is not None:
        forest_input.value = runstate.forest_name
    nickname_input = _el("plot-nickname-input")
    if nickname_input is not None:
        nickname_input.value = runstate.adopted_plot_nickname
        nickname_input.disabled = runstate.adopted_plot_index is None


# --- GB-18: undo a clear -------------------------------------------------------------------

def _arm_undo(plot_index, before_fields, payout, log_entry, season_cleared_before, best_income_before, cut=False):
    if runstate.current_difficulty == DIFFICULTY_RANGER:
        runstate._undo_snapshot = None
        return
    runstate._undo_snapshot = {
        "plot": plot_index,
        "fields": before_fields,
        "payout": payout,
        "clear_count_after": runstate.plots[plot_index].clear_count,
        "log_entry": log_entry,
        "season_cleared_before": season_cleared_before,
        "best_income_before": best_income_before,
        "ticks_left": UNDO_WINDOW_TICKS,
        "cut": cut,  # GB-21: undoing a clear-cut also takes the clear-cut count back
    }


def _advance_undo():
    """Counts the undo window down one tick; the chip is gone the tick after it hits 0."""
    if runstate._undo_snapshot is None:
        return
    if runstate._undo_snapshot["ticks_left"] <= 0:
        runstate._undo_snapshot = None
    else:
        runstate._undo_snapshot["ticks_left"] -= 1


def render_undo_chip():
    chip = _el("undo-clear-button")
    if chip is None:
        return
    if runstate._undo_snapshot is None:
        chip.hidden = True
        return
    label = _plot_ref(runstate._undo_snapshot["plot"])
    chip.hidden = False
    seconds = max(1, runstate._undo_snapshot["ticks_left"])
    chip.innerText = f"\u21a9 Undo clear ({label}, {seconds}s)"
    chip.setAttribute("aria-label", f"Undo {'clear-cutting' if runstate._undo_snapshot.get('cut') else 'clearing'} {label}. About {seconds} seconds left.")
