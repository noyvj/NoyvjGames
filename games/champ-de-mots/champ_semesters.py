"""Semester bands on the farm: grouping the weeks under FREN151 and FREN152 headings, their progress and collapsing.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_rules import STAGE_AUTOMATED, STAGE_SEED
from champ_model import is_due, state
from champ_util import _element, pref_get, pref_set


# ===========================================================================
# LM-1: semester bands on the farm
# ===========================================================================
#
# FREN151 and FREN152 are still ONE continuous sequence (state.rows, the review
# order, the unlock chain and the save are all untouched). The bands are only a
# wrapper the weeks sit in while the sort is "Syllabus order": a heading with the
# course name, a divider, a progress line and meter of its own, and a Hide/Show
# weeks button. Which bands there are is read from the rows' own `course`, so a
# new week of either course lands in the right band with no change here (LM-3).
# Collapsed bands are a per-browser preference (like Always multiple choice), never
# part of the save. Any other sort mixes the semesters on purpose ("weakest first"
# across the whole farm), so there the bands step aside and a note says why.

PREF_SEMESTERS_COLLAPSED = "champ-semesters-collapsed"
SEMESTER_SUBTITLE = "{weeks} weeks · {chapters}"
SEMESTER_PROGRESS = "{open} of {weeks} weeks open · {growing} of {total} plots growing · {automated} automated"
SEMESTER_PROGRESS_DUE = " · {due} ready for water"
SEMESTER_CHIP = "{name} · {course}: {percent}% growing · {automated} automated"
SEMESTER_SORTED_NOTE = "Sorted view: weeks from both semesters are mixed. Choose Syllabus order to see the semester bands."
SEMESTER_HIDE_LABEL = "Hide weeks"
SEMESTER_SHOW_LABEL = "Show weeks"
semester_collapsed = set()  # course codes the player folded away; never saved
_semester_cache = {}
_last_row_shown = {}  # sequence -> plots of that row passing the L-24 filter, from render_farm()


def semester_bands():
    """The farm's semesters in syllabus order, read from the rows' own course:
    [{index, course, name, heading, sequences, weeks, chapters}]."""
    order = []
    by_course = {}
    for row in state.rows:
        if row.course not in by_course:
            by_course[row.course] = []
            order.append(row.course)
        by_course[row.course].append(row)
    bands = []
    for index, course in enumerate(order, start=1):
        rows = by_course[course]
        titles = []
        for row in rows:
            if row.chapter_title and row.chapter_title not in titles:
                titles.append(row.chapter_title)
        if len(titles) > 1:
            chapters = f"{titles[0]} to {titles[-1]}"
        else:
            chapters = titles[0] if titles else course
        bands.append({
            "index": index,
            "course": course,
            "name": f"Semester {index}",
            "heading": f"Semester {index} · {course}",
            "sequences": [row.sequence for row in rows],
            "weeks": len(rows),
            "chapters": chapters,
        })
    return bands


def semester_stats(band):
    """Counts for one band, over the whole band whatever the farm filter hides."""
    total = growing = automated = due = open_weeks = 0
    for sequence in band["sequences"]:
        plots = state.row_plots(sequence)
        unlocked = state.is_row_unlocked(sequence)
        open_weeks += 1 if unlocked else 0
        total += len(plots)
        for plot in plots:
            if plot.stage != STAGE_SEED:
                growing += 1
            if plot.stage == STAGE_AUTOMATED:
                automated += 1
            if unlocked and is_due(plot, state.current_day):
                due += 1
    return {
        "weeks": band["weeks"], "open": open_weeks, "total": total,
        "growing": growing, "automated": automated, "due": due,
    }


def semester_progress_text(stats):
    text = SEMESTER_PROGRESS.format(**stats)
    if stats["due"]:
        text += SEMESTER_PROGRESS_DUE.format(due=stats["due"])
    return text


def _make_semester_handler(course):
    def handler(event=None):
        toggle_semester(course)
    return handler


def _build_semester_band(band, farm):
    """One band's markup; returns the element the band's rows are appended to."""
    i = band["index"]
    wrapper = document.createElement("section")
    wrapper.id = f"semester-{i}"
    wrapper.className = "semester"

    head = document.createElement("div")
    head.id = f"semester-head-{i}"
    head.className = "row semester-head"

    top = document.createElement("div")
    top.className = "semester-top"
    title = document.createElement("h2")
    title.id = f"semester-title-{i}"
    title.className = "row-label semester-title"
    title.innerText = band["heading"]
    top.appendChild(title)
    toggle = document.createElement("button")
    toggle.id = f"semester-toggle-{i}"
    toggle.className = "secondary semester-toggle"
    toggle.setAttribute("type", "button")
    toggle.setAttribute("aria-controls", f"semester-rows-{i}")
    toggle.innerText = SEMESTER_HIDE_LABEL
    toggle.addEventListener("click", create_proxy(_make_semester_handler(band["course"])))
    top.appendChild(toggle)
    head.appendChild(top)

    sub = document.createElement("span")
    sub.id = f"semester-sub-{i}"
    sub.className = "row-chapter semester-sub"
    sub.innerText = SEMESTER_SUBTITLE.format(weeks=band["weeks"], chapters=band["chapters"])
    head.appendChild(sub)

    progress = document.createElement("span")
    progress.id = f"semester-progress-{i}"
    progress.className = "row-progress semester-progress"
    head.appendChild(progress)

    meter = document.createElement("div")
    meter.id = f"semester-meter-{i}"
    meter.className = "automated-meter semester-meter"
    meter.setAttribute("role", "img")
    bar = document.createElement("div")
    bar.id = f"semester-bar-{i}"
    bar.className = "automated-bar"
    meter.appendChild(bar)
    head.appendChild(meter)
    wrapper.appendChild(head)

    rows = document.createElement("div")
    rows.id = f"semester-rows-{i}"
    rows.className = "semester-rows"
    rows.setAttribute("role", "group")
    rows.setAttribute("aria-labelledby", f"semester-title-{i}")
    wrapper.appendChild(rows)
    farm.appendChild(wrapper)
    return rows


def toggle_semester(course, collapse=None):
    """Fold or unfold one semester's weeks. Remembered in this browser only."""
    if course not in {band["course"] for band in semester_bands()}:
        return False
    fold = (course not in semester_collapsed) if collapse is None else bool(collapse)
    if fold:
        semester_collapsed.add(course)
    else:
        semester_collapsed.discard(course)
    pref_set(PREF_SEMESTERS_COLLAPSED, ",".join(sorted(semester_collapsed)))
    render_semesters()
    return fold


def _load_semester_prefs():
    known = {band["course"] for band in semester_bands()}
    raw = pref_get(PREF_SEMESTERS_COLLAPSED, "") or ""
    semester_collapsed.clear()
    semester_collapsed.update(code for code in raw.split(",") if code in known)


def render_semesters():
    syllabus = runstate.farm_sort == "syllabus"
    chips = []
    for band in semester_bands():
        i = band["index"]
        stats = semester_stats(band)
        shown = any(_last_row_shown.get(sequence, 0) > 0 for sequence in band["sequences"])
        collapsed = band["course"] in semester_collapsed
        percent = round(100 * stats["growing"] / stats["total"]) if stats["total"] else 0
        chips.append(SEMESTER_CHIP.format(
            name=band["name"], course=band["course"], percent=percent, automated=stats["automated"]
        ))
        values = (tuple(stats.values()), syllabus and shown, collapsed)
        if _semester_cache.get(i) == values:
            continue
        _semester_cache[i] = values
        _element(f"semester-{i}").hidden = not (syllabus and shown)
        _element(f"semester-{i}").className = "semester semester--collapsed" if collapsed else "semester"
        _element(f"semester-rows-{i}").hidden = collapsed
        toggle = _element(f"semester-toggle-{i}")
        toggle.innerText = SEMESTER_SHOW_LABEL if collapsed else SEMESTER_HIDE_LABEL
        toggle.setAttribute("aria-expanded", "false" if collapsed else "true")
        toggle.setAttribute(
            "aria-label", f"{SEMESTER_SHOW_LABEL if collapsed else SEMESTER_HIDE_LABEL}: {band['heading']}"
        )
        _element(f"semester-progress-{i}").innerText = semester_progress_text(stats)
        share = stats["growing"] / stats["total"] if stats["total"] else 0.0
        _element(f"semester-bar-{i}").style.width = f"{share * 100:.1f}%"
        meter = _element(f"semester-meter-{i}")
        meter.title = f"{stats['growing']} of {stats['total']} plots growing in {band['heading']}"
        meter.setAttribute("aria-label", meter.title)

    summary_values = (tuple(chips), syllabus)
    if _semester_cache.get("summary") != summary_values:
        _semester_cache["summary"] = summary_values
        summary = _element("semester-summary")
        summary.innerHTML = ""
        for text in chips:
            chip = document.createElement("span")
            chip.className = "semester-chip"
            chip.innerText = text
            summary.appendChild(chip)
        if not syllabus:
            note = document.createElement("span")
            note.className = "semester-note"
            note.innerText = SEMESTER_SORTED_NOTE
            summary.appendChild(note)
