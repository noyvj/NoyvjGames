"""The real calendar day (study_today), the study-days record and the study calendar panel.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import calendar as _calendar
import re

from js import document

import champ_runstate as runstate
from champ_util import _element


# ===========================================================================
# L7a/L7b: a real calendar-day concept and a lightweight study calendar.
# `state.current_day` is the SRS's own in-game day counter (advanced by the
# player), so it says nothing about real dates. This records which REAL
# calendar days had any study activity, as {"YYYY-MM-DD": answers}. The date
# itself comes from a JS hook (window.studyToday, in index.html) because this
# file may not touch any clock API (Milestone 7's tested constraint). No
# streak counter, no missed-day marker: the calendar only ever shows what you
# DID, matching this game's no-guilt stance (section 3).
# ===========================================================================
STUDY_DAY_LIMIT = 400  # newest days kept, so the save stays small
STUDY_COUNT_LIMIT = 9999
CALENDAR_MONTHS_BACK = 36
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


_today_override = None  # tests only


def _parse_iso_date(text):
    """(year, month, day) for a real 'YYYY-MM-DD' date, else None."""
    if not isinstance(text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    year, month, day = int(text[0:4]), int(text[5:7]), int(text[8:10])
    if year < 1970 or year > 2200 or month < 1 or month > 12:
        return None
    if day < 1 or day > _calendar.monthrange(year, month)[1]:
        return None
    return year, month, day


def study_today():
    """Today's real date as 'YYYY-MM-DD', or None when there's no clock."""
    if _today_override is not None:
        return _today_override
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return None
    hook = getattr(window, "studyToday", None)
    if hook is None:
        return None
    value = hook()
    return value if _parse_iso_date(value) else None


def note_study_answer():
    """Count one answered question against today's real date."""
    day = study_today()
    if day is None:
        return
    runstate.study_days[day] = min(runstate.study_days.get(day, 0) + 1, STUDY_COUNT_LIMIT)
    if len(runstate.study_days) > STUDY_DAY_LIMIT:
        for old in sorted(runstate.study_days)[: len(runstate.study_days) - STUDY_DAY_LIMIT]:
            del runstate.study_days[old]


def _validated_study_days(raw):
    if not isinstance(raw, dict):
        return {}
    clean = {}
    for key, count in raw.items():
        if _parse_iso_date(key) is None:
            continue
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            continue
        clean[key] = min(count, STUDY_COUNT_LIMIT)
    for old in sorted(clean)[: max(0, len(clean) - STUDY_DAY_LIMIT)]:
        del clean[old]
    return clean


def calendar_month_days(year, month):
    """Weeks of the month, Monday first: [[day-or-0 x 7], ...]."""
    return _calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)


def calendar_current_view():
    if runstate.calendar_view is not None:
        return runstate.calendar_view
    today = _parse_iso_date(study_today())
    if today is not None:
        return today[0], today[1]
    if runstate.study_days:
        latest = _parse_iso_date(max(runstate.study_days))
        return latest[0], latest[1]
    return None


def _shift_month(view, delta):
    year, month = view
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def _calendar_view_allowed(view):
    today = _parse_iso_date(study_today())
    if today is None:
        return True
    now = today[0] * 12 + today[1] - 1
    shown = view[0] * 12 + view[1] - 1
    return now - CALENDAR_MONTHS_BACK <= shown <= now


def on_toggle_calendar(event=None):
    runstate.calendar_open = not runstate.calendar_open
    if not runstate.calendar_open:
        runstate.calendar_view = None
    render_calendar()


def _on_calendar_shift(delta):
    view = calendar_current_view()
    if view is None:
        return
    target = _shift_month(view, delta)
    if _calendar_view_allowed(target):
        runstate.calendar_view = target
    render_calendar()


def on_calendar_prev(event=None):
    _on_calendar_shift(-1)


def on_calendar_next(event=None):
    _on_calendar_shift(1)


def render_calendar():
    panel = _element("calendar-panel")
    toggle = _element("calendar-toggle-button")
    toggle.innerText = "Hide study calendar" if runstate.calendar_open else "🗓️ Study calendar"
    panel.hidden = not runstate.calendar_open
    if not runstate.calendar_open:
        return
    grid = _element("calendar-grid")
    grid.innerHTML = ""
    view = calendar_current_view()
    if view is None:
        _element("calendar-month-label").innerText = ""
        _element("calendar-summary").innerText = (
            "Nothing to show yet. Answer a question and today will appear here."
        )
        return
    year, month = view
    _element("calendar-month-label").innerText = f"{MONTH_NAMES[month - 1]} {year}"
    _element("calendar-prev-button").disabled = not _calendar_view_allowed(_shift_month(view, -1))
    _element("calendar-next-button").disabled = not _calendar_view_allowed(_shift_month(view, 1))
    today = _parse_iso_date(study_today())
    for name in WEEKDAY_NAMES:
        head = document.createElement("span")
        head.className = "calendar-weekday"
        head.innerText = name
        grid.appendChild(head)
    studied_here = 0
    for week in calendar_month_days(year, month):
        for day in week:
            cell = document.createElement("span")
            if day == 0:
                cell.className = "calendar-cell calendar-cell--blank"
                grid.appendChild(cell)
                continue
            iso = f"{year:04d}-{month:02d}-{day:02d}"
            answers = runstate.study_days.get(iso, 0)
            is_today = today == (year, month, day)
            cell.className = "calendar-cell"
            if answers:
                studied_here += 1
                cell.className += " calendar-cell--studied"
            if is_today:
                cell.className += " calendar-cell--today"
            label = f"{day} {MONTH_NAMES[month - 1]}"
            if answers:
                label += f": {answers} answer{'s' if answers != 1 else ''}"
            if is_today:
                label += " (today)"
            cell.setAttribute("aria-label", label)
            cell.title = label
            number = document.createElement("span")
            number.className = "calendar-day-number"
            number.innerText = str(day)
            cell.appendChild(number)
            if answers:
                count = document.createElement("span")
                count.className = "calendar-day-count"
                count.innerText = f"\u00b7{answers}"
                cell.appendChild(count)
            grid.appendChild(cell)
    if studied_here:
        noun = "day" if studied_here == 1 else "days"
        summary = f"You studied on {studied_here} {noun} this month."
    else:
        summary = "No study days recorded this month. Nothing here ever expires."
    _element("calendar-summary").innerText = summary
