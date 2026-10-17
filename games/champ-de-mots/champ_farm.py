"""The farm grid: building it once, drawing every plot cell and the header status tiles.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_rules import STAGE_AUTOMATED, STAGE_ORDER, STAGE_SEED
from champ_model import is_due, state
from champ_labels import (
    DUE_MESSAGE_MANY, DUE_MESSAGE_ONE, LOCK_NOTE, NOTHING_DUE_MESSAGE, PACE_NOTE, ROW_DUE_NOTE, STAGE_ICON,
    STAGE_LABEL, WEEDS_ICON, WEEDS_LEGEND, WILTING_LEGEND,
)
from champ_util import _element
from champ_points import (
    ensure_golden, golden_text, quest_summary_text, render_practice_score, render_study_buddy,
)
from champ_practice_base import plot_cells, row_session_perfect_badge
from champ_semesters import (
    _build_semester_band, _last_row_shown, _semester_cache, render_semesters, semester_bands,
)
from champ_arrange import _plot_classes, _plot_title, farm_filter_count_text, plot_matches_filter
from champ_proficiency import _make_proficiency_handler
from champ_bonus import _make_bonus_handler
from champ_practice import open_practice


def _make_plot_handler(plot_id):
    def handler(event=None):
        open_practice(plot_id)
    return handler


def build_farm():
    """Build the grid once. Rows are sequence numbers, running straight from
    FREN151 into FREN152 with only the chapter label marking the join (§4)."""
    farm = _element("farm")
    farm.innerHTML = ""
    plot_cells.clear()
    _farm_cell_cache.clear()
    _farm_row_cache.clear()
    _semester_cache.clear()
    runstate._farm_order_cache = None

    # LM-1: one band per semester (course), each holding its own weeks. The
    # sequence underneath stays one continuous list (state.rows is untouched);
    # the band is only a wrapper the rows sit in while the sort is Syllabus order.
    band_rows = {}
    for band in semester_bands():
        band_rows[band["course"]] = _build_semester_band(band, farm)

    for row in state.rows:
        row_element = document.createElement("div")
        row_element.id = f"row-{row.sequence}"
        row_element.className = "row"

        head = document.createElement("div")
        head.className = "row-head"

        label = document.createElement("span")
        label.id = f"row-label-{row.sequence}"
        label.className = "row-label"
        label.innerText = row.label
        head.appendChild(label)

        chapter = document.createElement("span")
        chapter.id = f"row-chapter-{row.sequence}"
        chapter.className = "row-chapter"
        chapter.innerText = row.chapter_label
        head.appendChild(chapter)

        progress = document.createElement("span")
        progress.id = f"row-progress-{row.sequence}"
        progress.className = "row-progress"
        head.appendChild(progress)

        perfect_badge = document.createElement("span")
        perfect_badge.id = f"row-perfect-badge-{row.sequence}"
        perfect_badge.className = "row-perfect-badge"
        perfect_badge.innerText = "⭐ Perfect this session"
        perfect_badge.title = (
            "Every plot in this row answered correctly this session, with no misses along the way."
        )
        perfect_badge.hidden = True
        head.appendChild(perfect_badge)

        due = document.createElement("span")
        due.id = f"row-due-{row.sequence}"
        due.className = "row-due"
        due.hidden = True
        head.appendChild(due)

        lock = document.createElement("span")
        lock.id = f"row-lock-{row.sequence}"
        lock.className = "row-lock"
        lock.innerText = LOCK_NOTE.format(previous=row.sequence - 1)
        lock.hidden = True
        head.appendChild(lock)

        # §14.5: one proficiency test per sequence entry, started right from
        # that week's own row rather than a separate flat list of 23 buttons.
        proficiency_button = document.createElement("button")
        proficiency_button.id = f"row-proficiency-{row.sequence}"
        proficiency_button.className = "row-proficiency-button secondary"
        proficiency_button.innerText = "Proficiency test"
        proficiency_button.addEventListener(
            "click", create_proxy(_make_proficiency_handler(row.sequence))
        )
        head.appendChild(proficiency_button)

        # §14.6: a bonus sentence-building section per week, same row-header
        # placement as the proficiency test button above.
        bonus_button = document.createElement("button")
        bonus_button.id = f"row-bonus-{row.sequence}"
        bonus_button.className = "row-bonus-button secondary"
        bonus_button.innerText = "Bonus sentence"
        bonus_button.addEventListener("click", create_proxy(_make_bonus_handler(row.sequence)))
        head.appendChild(bonus_button)

        plots = document.createElement("div")
        plots.id = f"row-plots-{row.sequence}"
        plots.className = "row-plots"

        for plot_id in row.plot_ids:
            cell = document.createElement("button")
            cell.id = f"plot-{plot_id}"
            cell.className = "plot"
            cell.addEventListener("click", create_proxy(_make_plot_handler(plot_id)))
            plots.appendChild(cell)
            plot_cells[plot_id] = cell

        row_element.appendChild(head)
        row_element.appendChild(plots)
        band_rows[row.course].appendChild(row_element)


def render_legend():
    lines = [f"{STAGE_ICON[stage]} {STAGE_LABEL[stage]}" for stage in STAGE_ORDER]
    lines.append(f"💧 {WILTING_LEGEND}")
    lines.append(f"{WEEDS_ICON} {WEEDS_LEGEND}")
    _element("legend").innerText = "  ·  ".join(lines)


# U14: render_farm() used to rewrite five DOM properties on every plot cell on
# every render (about 20ms, the single biggest cost in this game). Each cell's
# and row's last-written values are remembered here and a property is only
# written when it actually changed; a rebuilt grid clears both caches.
_farm_cell_cache = {}
_farm_row_cache = {}


def render_farm():
    ensure_golden()
    row_shown = {}  # sequence -> how many of its plots pass the L-24 filter
    for plot in state.plots:
        cell = plot_cells.get(plot.plot_id)
        if cell is None:
            continue
        classes = _plot_classes(plot)
        icon = STAGE_ICON[plot.stage]
        title = _plot_title(plot)
        disabled = not state.is_row_unlocked(plot.sequence)
        shown = plot_matches_filter(plot, runstate.farm_filter)
        row_shown[plot.sequence] = row_shown.get(plot.sequence, 0) + (1 if shown else 0)
        values = (classes, icon, title, disabled, shown)
        if _farm_cell_cache.get(plot.plot_id) == values:
            continue
        _farm_cell_cache[plot.plot_id] = values
        cell.className = classes
        cell.innerText = icon
        cell.title = title
        cell.hidden = not shown
        # The sprite carries the meaning visually; screen readers get the same
        # sentence the tooltip does.
        cell.setAttribute("aria-label", title)
        cell.disabled = disabled

    _last_row_shown.clear()
    _last_row_shown.update(row_shown)
    for row in state.rows:
        plots = state.row_plots(row.sequence)
        grown = sum(1 for p in plots if p.stage != STAGE_SEED)
        # L20 -- separate "watered at least once" from "never watered yet"
        # (a wrong answer counts as watered but leaves the plot a seed, so
        # the grown/total number above can understate real catch-up).
        watered = sum(1 for p in plots if p.last_reviewed is not None)
        unlocked = state.is_row_unlocked(row.sequence)
        row_due = sum(1 for p in plots if is_due(p, state.current_day)) if unlocked else 0
        badge_hidden = row.sequence not in row_session_perfect_badge
        row_hidden = row_shown.get(row.sequence, 0) == 0
        row_values = (grown, len(plots), watered, unlocked, row_due, badge_hidden, row_hidden)
        if _farm_row_cache.get(row.sequence) == row_values:
            continue
        _farm_row_cache[row.sequence] = row_values
        _element(f"row-{row.sequence}").hidden = row_hidden

        _element(f"row-progress-{row.sequence}").innerText = f"{grown}/{len(plots)}"
        _element(f"row-progress-{row.sequence}").title = (
            f"{watered} of {len(plots)} plots watered at least once, {len(plots) - watered} never watered yet"
        )
        _element(f"row-lock-{row.sequence}").hidden = unlocked
        _element(f"row-{row.sequence}").className = "row" if unlocked else "row row--locked"
        _element(f"row-perfect-badge-{row.sequence}").hidden = badge_hidden

        due_element = _element(f"row-due-{row.sequence}")
        due_element.hidden = not row_due
        due_element.innerText = ROW_DUE_NOTE.format(count=row_due) if row_due else ""

        _element(f"row-proficiency-{row.sequence}").disabled = not unlocked
        _element(f"row-bonus-{row.sequence}").disabled = not unlocked

    render_semesters()


def render_status():
    due = state.due_plots()
    _element("day-display").innerText = f"Day {state.current_day + 1}"
    if not due:
        message = NOTHING_DUE_MESSAGE
    elif len(due) == 1:
        message = DUE_MESSAGE_ONE
    else:
        message = DUE_MESSAGE_MANY.format(count=len(due))
    _element("due-display").innerText = message
    _element("pace-display").innerText = PACE_NOTE

    # A tally rather than a score: how much of the farm is at each stage, with
    # no notion of how much of it "should" be further along by now.
    counts = {stage: 0 for stage in STAGE_ORDER}
    for plot in state.plots:
        counts[plot.stage] += 1
    _element("stage-summary-display").innerText = " · ".join(
        f"{STAGE_ICON[stage]} {counts[stage]}" for stage in STAGE_ORDER
    )

    # Audit note: the numerator here is scoped to available_plots() (rows
    # unlocked so far) while the denominator is len(state.plots) (all 722,
    # locked or not) -- an inconsistent scope on its face. It reads correctly
    # today only because a locked plot can never be anything but STAGE_SEED
    # during live play: open_practice() refuses to open a plot outside
    # is_row_unlocked(), which is the only path that ever advances a stage
    # (schedule_after_review()), so filtering the numerator down to
    # available_plots() can never actually exclude a non-seed plot -- the
    # count would come out identical scoped over state.plots directly.
    # That said, load_state() sets plot.stage straight from a save record
    # per plot_id, independent of that plot's row's current unlock status;
    # a save that is missing or resets an earlier row's records (an old/
    # edited/incompatible save code) while still recording a later row's
    # plot as grown could in principle reload into exactly the locked-but-
    # growing state this scope mismatch assumes can't happen -- the same
    # general class of stale-save-reload skew audited and fixed elsewhere
    # in this repo (see Aftermath's highest-awarded-run guard). Left as-is
    # rather than silently changed, since which scope is "correct" for the
    # player-facing number here isn't a confident call either way; flagging
    # for whoever next touches save compatibility for this game.
    available = state.available_plots()
    growing = sum(1 for p in available if p.stage != STAGE_SEED)
    automated = sum(1 for p in available if p.stage == STAGE_AUTOMATED)
    _element("progress-display").innerText = (
        f"{growing} of {len(state.plots)} plots growing · {automated} automated"
    )
    # L8 -- an always-visible bar for how much of the whole farm is automated.
    automated_share = automated / len(state.plots) if state.plots else 0.0
    _element("automated-bar").style.width = f"{automated_share * 100:.1f}%"
    _element("automated-meter").title = f"{automated} of {len(state.plots)} plots automated"

    render_practice_score()
    render_study_buddy()
    _element("golden-display").innerText = golden_text()
    _element("quest-display").innerText = quest_summary_text()
    _element("farm-filter-count").innerText = farm_filter_count_text()

    unlocked = sum(1 for r in state.rows if state.is_row_unlocked(r.sequence))
    _element("row-summary-display").innerText = f"{unlocked} of {len(state.rows)} rows open"

    # Combo bonus (Improvement Ideas §2): only worth a line once it's an
    # actual moment, not a running scoreboard -- a fresh session or one that
    # just broke its combo shows nothing here, matching the farm's existing
    # "calm, not a scoreboard" stance rather than a 0-in-a-row counter.
    combo_display = _element("combo-display")
    if runstate.combo_count >= 2:
        combo_display.innerText = f"{runstate.combo_count} correct in a row — nice pace."
        combo_display.hidden = False
    else:
        combo_display.innerText = ""
        combo_display.hidden = True

    water_next = _element("water-next-button")
    water_next.disabled = not due
    water_next.innerText = "Water the next plot" if due else "All watered"
