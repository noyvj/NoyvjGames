"""Farm filter and sort: which plots and weeks are shown, in what order, and the CSS classes and tooltip each plot cell gets.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import minigames
import champ_runstate as runstate
from champ_rules import STAGE_AUTOMATED, STAGE_RANK
from champ_model import is_due, is_wilting, state
from champ_grading import weeds_confusions_for
from champ_labels import AUTOMATED_TOOLTIP_NOTE, DUE_NOTE, STAGE_LABEL, WEEDS_TOOLTIP_NOTE
from champ_util import _element
from champ_stats import dashboard_row_mastery
from champ_points import GOLDEN_POINTS, is_golden
from champ_practice_base import plot_cells
from champ_leech import is_leech
from champ_semesters import semester_bands


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


# ===========================================================================
# L-24: filter and sort for the farm grid
# ===========================================================================
#
# A "show" filter hides the plots that do not match (and any week left with
# nothing to show), and a "sort" re-orders the weeks and the plots inside each
# week. Both are plain DOM moves on the grid build_farm() already made: cells
# are re-appended in the new order (a real DOM append MOVES a node), so the
# tab order always matches what the eye sees. Session-only, like the review
# controls: nothing here reaches get_state(), and nothing changes any plot.
# The order is applied when a control changes, when the day moves on, when a
# save loads and at boot -- not after every answer, so a plot never slides out
# from under the cursor mid-session. The filter, being a cheap hide/show, does
# follow every repaint.
FARM_FILTERS = {
    "all": "All plots",
    "due": "Due today",
    "weeds": "In the weeds",
    "unwatered": "Never watered",
    "vocab": "Vocabulary",
    "phrase": "Phrases",
    "grammar": "Grammar",
    "phonetic": "Phonetics",
}
FARM_SORTS = {
    "syllabus": "Syllabus order",
    "weakest": "Weakest first",
    "overdue": "Most overdue first",
    "type": "By type",
}
FARM_TYPE_ORDER = ["vocab", "phrase", "grammar", "phonetic"]


def plot_matches_filter(plot, key):
    if key == "all" or key not in FARM_FILTERS:
        return True
    if key == "due":
        return is_due(plot, state.current_day)
    if key == "weeds":
        return plot.in_weeds
    if key == "unwatered":
        return plot.last_reviewed is None
    return plot.topic_type == key


def _plot_sort_key(plot, key, position):
    if key == "weakest":
        return (STAGE_RANK[plot.stage], plot.ease_factor, position)
    if key == "overdue":
        if is_due(plot, state.current_day):
            if plot.last_reviewed is not None and plot.next_due is not None:
                return (0, plot.next_due, position)
            return (1, 0, position)
        return (2, 0, position)
    if key == "type":
        kind = plot.topic_type
        return (FARM_TYPE_ORDER.index(kind) if kind in FARM_TYPE_ORDER else len(FARM_TYPE_ORDER), 0, position)
    return (0, 0, position)


def farm_row_order(key):
    """[(sequence, [plot ids in display order])] for the chosen sort."""
    rows = []
    for index, row in enumerate(state.rows):
        plots = state.row_plots(row.sequence)
        ordered = sorted(
            enumerate(plots), key=lambda pair: _plot_sort_key(pair[1], key, pair[0])
        )
        if key == "weakest":
            row_key = (dashboard_row_mastery(row.sequence), index)
        elif key == "overdue":
            row_key = (-sum(1 for p in plots if is_due(p, state.current_day) and p.last_reviewed is not None), index)
        else:
            row_key = (0, index)
        rows.append((row_key, row.sequence, [p.plot_id for _i, p in ordered]))
    rows.sort(key=lambda entry: entry[0])
    return [(sequence, ids) for _key, sequence, ids in rows]


def apply_farm_arrangement(force=False):
    """Re-order the weeks and each week's plots for the current sort."""
    order = farm_row_order(runstate.farm_sort)
    signature = (runstate.farm_sort, tuple((seq, tuple(ids)) for seq, ids in order))
    if not force and signature == runstate._farm_order_cache:
        return False
    runstate._farm_order_cache = signature
    farm = _element("farm")
    # LM-1: in Syllabus order every week sits inside its semester's band; any other
    # sort mixes the semesters, so the weeks come out of the bands (which hide).
    bands = semester_bands()
    for band in bands:
        farm.appendChild(_element(f"semester-{band['index']}"))
    band_of = {band["course"]: band["index"] for band in bands}
    course_of = {row.sequence: row.course for row in state.rows}
    in_bands = runstate.farm_sort == "syllabus"
    for sequence, ids in order:
        home = _element(f"semester-rows-{band_of[course_of[sequence]]}") if in_bands else farm
        home.appendChild(_element(f"row-{sequence}"))
        container = _element(f"row-plots-{sequence}")
        for plot_id in ids:
            cell = plot_cells.get(plot_id)
            if cell is not None:
                container.appendChild(cell)
    return True


def set_farm_filter(key):
    runstate.farm_filter = key if key in FARM_FILTERS else "all"
    _element("farm-filter-select").value = runstate.farm_filter
    render()
    return runstate.farm_filter


def set_farm_sort(key):
    runstate.farm_sort = key if key in FARM_SORTS else "syllabus"
    _element("farm-sort-select").value = runstate.farm_sort
    apply_farm_arrangement(force=True)
    render()
    return runstate.farm_sort


def on_farm_filter_change(event=None):
    set_farm_filter(_element("farm-filter-select").value)


def on_farm_sort_change(event=None):
    set_farm_sort(_element("farm-sort-select").value)


def farm_filter_count_text():
    total = len(state.plots)
    if runstate.farm_filter == "all":
        return ""
    shown = sum(1 for p in state.plots if plot_matches_filter(p, runstate.farm_filter))
    return f"Showing {shown} of {total} plots"


def _plot_classes(plot):
    classes = ["plot", f"plot--{plot.stage}"]
    # L16 -- a non-colour cue for the topic type (border style, see style.css).
    classes.append(f"plot--type-{plot.topic_type}")
    # Weeds takes the place ordinary wilting would otherwise show for this
    # specific plot -- a known mix-up is more informative than a generic
    # "overdue" droop, so it's checked first and wilting is skipped when
    # weeds already applies.
    if plot.in_weeds:
        classes.append("plot--weeds")
    elif is_wilting(plot, state.current_day):
        classes.append("plot--wilting")
    if is_due(plot, state.current_day):
        classes.append("plot--due")
    # L-17 / L-18: the golden plot of the day and a stubborn weed.
    if is_golden(plot):
        classes.append("plot--golden")
    if is_leech(plot):
        classes.append("plot--leech")
    # L-16: a false-friend badge when the live list (Faux Amis) names this plot's French word.
    if minigames.amis_for_plot(plot) is not None:
        classes.append("plot--amis")
    if not state.is_row_unlocked(plot.sequence):
        classes.append("plot--locked")
    return " ".join(classes)


def _plot_title(plot):
    parts = [f"{plot.label} — {plot.topic_title}", STAGE_LABEL[plot.stage].split(" — ")[0]]
    if plot.stage == STAGE_AUTOMATED:
        parts.append(AUTOMATED_TOOLTIP_NOTE)
        # L12 -- how long until this automated plot next wants water.
        if plot.next_due is not None and plot.next_due > state.current_day:
            days = plot.next_due - state.current_day
            parts.append(f"next review in {days} day{'s' if days != 1 else ''}")
    if plot.in_weeds:
        parts.append(WEEDS_TOOLTIP_NOTE)
        confusions = weeds_confusions_for(plot)
        if confusions:
            parts.append("Easy to mix up with: " + ", ".join(f"\u201c{c}\u201d" for c in confusions))
    if is_golden(plot):
        parts.append(f"golden plot of the day: a correct answer earns {GOLDEN_POINTS} practice points")
    if is_leech(plot):
        parts.append(
            f"stubborn weed: missed {plot.fail_run} times in a row, so a short re-teach card shows first"
        )
    amis_note = minigames.amis_plot_note(plot)
    if amis_note:
        parts.append(amis_note)
    if is_due(plot, state.current_day):
        parts.append(DUE_NOTE)
    return " · ".join(parts)
