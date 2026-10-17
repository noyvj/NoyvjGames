"""The exam planner: the exam date, minutes a day, the projection of how many plots will be automated, and the header
countdown.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import calendar as _calendar
import heapq

import champ_runstate as runstate
from champ_rules import (
    EXAM_DEFAULT_DATE, EXAM_DEFAULT_NOTE, PLANNER_DEFAULT_MINUTES, PLANNER_MAX_DAYS, PLANNER_MAX_MINUTES,
    PLANNER_MIN_MINUTES, PLANNER_MISS_EVERY, PLANNER_STEP_MINUTES, PLANNER_TARGET_PERCENT, STAGE_AUTOMATED,
)
from champ_model import schedule_after_review, state
from champ_util import _element
from champ_stats import automated_plot_count
from champ_calendar import _parse_iso_date, study_today
from champ_points import STUDY_BUDDY_SECONDS_PER_REVIEW


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


_planner_cache = {}


def _day_number(iso):
    """Whole days since 1970-01-01 for a valid 'YYYY-MM-DD', else None."""
    parsed = _parse_iso_date(iso)
    if parsed is None:
        return None
    return _calendar.timegm((parsed[0], parsed[1], parsed[2], 0, 0, 0)) // 86400


def exam_days_left():
    """Days from today to the exam date (0 = today, negative = passed), or
    None when there is no date or no clock."""
    if runstate.exam_date is None:
        return None
    today = _day_number(study_today())
    target = _day_number(runstate.exam_date)
    if today is None or target is None:
        return None
    return target - today


def _clamp_minutes(value):
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return PLANNER_DEFAULT_MINUTES
    minutes = max(PLANNER_MIN_MINUTES, min(PLANNER_MAX_MINUTES, minutes))
    return round(minutes / PLANNER_STEP_MINUTES) * PLANNER_STEP_MINUTES


class _SimPlot:
    """Just the scheduling fields schedule_after_review() reads and writes."""

    __slots__ = ("ease_factor", "interval_days", "last_reviewed", "next_due", "correct_streak", "stage")

    def __init__(self, plot):
        self.ease_factor = plot.ease_factor
        self.interval_days = plot.interval_days
        self.last_reviewed = plot.last_reviewed
        self.next_due = plot.next_due
        self.correct_streak = plot.correct_streak
        self.stage = plot.stage


def reviews_per_day(minutes):
    return max(0, int(minutes * 60 // STUDY_BUDDY_SECONDS_PER_REVIEW))


def simulate_harvest(days, minutes, miss_every=0):
    """How many plots would be Automated after `days` days of `minutes` a
    day, replaying the real scheduler on copies (no real plot is touched).
    `miss_every` > 0 makes every n-th answer wrong. Returns
    {"automated", "total", "percent"}."""
    sims = [_SimPlot(plot) for plot in state.plots]
    first_day = state.current_day
    queue = [
        (sim.next_due if isinstance(sim.next_due, int) else first_day, index)
        for index, sim in enumerate(sims)
        if sim.last_reviewed is not None
    ]
    heapq.heapify(queue)
    unplanted = [index for index, sim in enumerate(sims) if sim.last_reviewed is None]
    planted = 0
    capacity = reviews_per_day(minutes)
    answered = 0
    for offset in range(max(0, min(days, PLANNER_MAX_DAYS))):
        day = first_day + offset
        room = capacity
        while room and queue and queue[0][0] <= day:
            _due, index = heapq.heappop(queue)
            answered += 1
            correct = not (miss_every and answered % miss_every == 0)
            schedule_after_review(sims[index], correct, day)
            heapq.heappush(queue, (sims[index].next_due, index))
            room -= 1
        while room and planted < len(unplanted):
            index = unplanted[planted]
            planted += 1
            answered += 1
            correct = not (miss_every and answered % miss_every == 0)
            schedule_after_review(sims[index], correct, day)
            heapq.heappush(queue, (sims[index].next_due, index))
            room -= 1
    automated = sum(1 for sim in sims if sim.stage == STAGE_AUTOMATED)
    total = len(sims)
    return {"automated": automated, "total": total, "percent": (100.0 * automated / total) if total else 0.0}


def _farm_signature():
    """A cheap fingerprint of every plot's scheduling state, so a cached
    projection is reused until something that matters changes."""
    return hash(
        tuple((p.interval_days, p.next_due, p.correct_streak, p.last_reviewed, p.stage) for p in state.plots)
    )


def current_automated_percent():
    total = len(state.plots)
    return (100.0 * automated_plot_count() / total) if total else 0.0


def planner_projection(minutes=None):
    """{"days", "minutes", "cautious", "best", "current"} for the saved exam
    date, or None when there is no usable date. Cached on the inputs."""
    days = exam_days_left()
    if days is None or days <= 0:
        return None
    minutes = runstate.exam_minutes if minutes is None else _clamp_minutes(minutes)
    key = ("proj", runstate.exam_date, days, minutes, state.current_day, _farm_signature())
    cached = _planner_cache.get(key)
    if cached is not None:
        return cached
    result = {
        "days": days,
        "minutes": minutes,
        "reviews": reviews_per_day(minutes),
        "cautious": simulate_harvest(days, minutes, PLANNER_MISS_EVERY)["percent"],
        "best": simulate_harvest(days, minutes, 0)["percent"],
        "current": current_automated_percent(),
    }
    _planner_cache.clear()
    _planner_cache[key] = result
    return result


def planner_minimum_minutes():
    """The smallest daily effort (in PLANNER_STEP_MINUTES steps) whose
    cautious projection reaches PLANNER_TARGET_PERCENT: ("already", None)
    when the farm is there now, ("minutes", n), or ("unreachable", best
    percent at the maximum effort). None when there is no usable date."""
    days = exam_days_left()
    if days is None or days <= 0:
        return None
    key = ("min", runstate.exam_date, days, state.current_day, _farm_signature())
    cached = _planner_cache.get(key)
    if cached is not None:
        return cached
    if current_automated_percent() >= PLANNER_TARGET_PERCENT:
        result = ("already", None)
    else:
        steps = list(range(PLANNER_MIN_MINUTES, PLANNER_MAX_MINUTES + 1, PLANNER_STEP_MINUTES))

        def reaches(minutes):
            return simulate_harvest(days, minutes, PLANNER_MISS_EVERY)["percent"] >= PLANNER_TARGET_PERCENT

        if not reaches(steps[-1]):
            best = simulate_harvest(days, steps[-1], PLANNER_MISS_EVERY)["percent"]
            result = ("unreachable", best)
        else:
            low, high = 0, len(steps) - 1
            while low < high:
                middle = (low + high) // 2
                if reaches(steps[middle]):
                    high = middle
                else:
                    low = middle + 1
            result = ("minutes", steps[low])
    _planner_cache[key] = result
    return result


def exam_countdown_text():
    """The header chip: days to go plus the projected coverage at the saved
    daily effort. Empty (so the chip hides) with no date, no clock, or a date
    that has already passed."""
    days = exam_days_left()
    if days is None or days < 0:
        return ""
    if days == 0:
        return "Exam today"
    projection = planner_projection()
    when = f"Exam in {days} day{'s' if days != 1 else ''}"
    if projection is None:
        return when
    return f"{when} · about {projection['cautious']:.0f}% automated by then"


def set_exam_date(value):
    """Store (or clear, with an empty/invalid value) the exam date. Returns
    True when a valid date is now set."""
    text = str(value or "").strip()
    runstate.exam_date = text if _parse_iso_date(text) is not None else None
    _planner_cache.clear()
    render()
    return runstate.exam_date is not None


def set_exam_minutes(value):
    runstate.exam_minutes = _clamp_minutes(value)
    render()
    return runstate.exam_minutes


def on_toggle_planner(event=None):
    runstate.planner_open = not runstate.planner_open
    render()


def on_planner_date_change(event=None):
    set_exam_date(_element("planner-date-input").value)


def on_planner_minutes_change(event=None):
    set_exam_minutes(_element("planner-minutes-input").value)


def on_planner_default(event=None):
    """FS-23: one click to use the outline's exam date."""
    set_exam_date(EXAM_DEFAULT_DATE)


def on_planner_clear(event=None):
    _element("planner-date-input").value = ""
    set_exam_date("")


def _validated_exam_plan(raw):
    """(date or None, minutes) from an untrusted save value."""
    if not isinstance(raw, dict):
        return None, PLANNER_DEFAULT_MINUTES
    date = raw.get("date")
    date = date if isinstance(date, str) and _parse_iso_date(date) is not None else None
    minutes = raw.get("minutes")
    if isinstance(minutes, bool) or not isinstance(minutes, int):
        minutes = PLANNER_DEFAULT_MINUTES
    return date, _clamp_minutes(minutes)


def render_planner():
    tile = _element("exam-countdown-tile")
    text = exam_countdown_text()
    _element("exam-countdown-display").innerText = text
    tile.hidden = not text

    toggle = _element("planner-toggle-button")
    toggle.innerText = "Hide exam planner" if runstate.planner_open else "📅 Exam planner"
    panel = _element("planner-panel")
    panel.hidden = not runstate.planner_open
    if not runstate.planner_open:
        return
    date_input = _element("planner-date-input")
    date_input.value = runstate.exam_date or ""
    minutes_input = _element("planner-minutes-input")
    minutes_input.value = str(runstate.exam_minutes)
    _element("planner-minutes-label").innerText = f"{runstate.exam_minutes} minutes a day"

    days = exam_days_left()
    summary, projection_line, suggestion = "", "", ""
    default_button = _element("planner-default-button")
    if default_button is not None:
        default_button.hidden = runstate.exam_date is not None
        default_button.innerText = f"Use the exam date from the subject outline ({EXAM_DEFAULT_NOTE})"
    if runstate.exam_date is None:
        summary = "Pick your exam date to see what a few minutes a day adds up to, or use the date from the subject outline."
    elif days is None:
        summary = "Today's date is not available here, so the countdown cannot be worked out."
    elif days < 0:
        summary = "That date has passed. Pick a new one, or clear it."
    elif days == 0:
        summary = "The exam is today. Whatever you have grown is what you take in."
    else:
        summary = f"{days} day{'s' if days != 1 else ''} to go (exam on {runstate.exam_date})."
        projection = planner_projection()
        projection_line = (
            f"At {projection['minutes']} minutes a day (about {projection['reviews']} answers a day), "
            f"roughly {projection['cautious']:.0f}% of the farm would be Automated by then, "
            f"or up to {projection['best']:.0f}% if every answer were right. "
            f"Right now: {projection['current']:.0f}%."
        )
        found = planner_minimum_minutes()
        if found is not None:
            kind, value = found
            if kind == "already":
                suggestion = f"The farm is already at {PLANNER_TARGET_PERCENT}% Automated or more. Keeping it watered is enough."
            elif kind == "minutes":
                suggestion = (
                    f"To reach {PLANNER_TARGET_PERCENT}% Automated by then, aim for at least {value} "
                    f"minute{'s' if value != 1 else ''} a day."
                )
            else:
                suggestion = (
                    f"{PLANNER_TARGET_PERCENT}% is out of reach in this time, even at {PLANNER_MAX_MINUTES} "
                    f"minutes a day (best about {value:.0f}%). A mock exam over the weeks it covers is a better use of the time."
                )
    _element("planner-summary").innerText = summary
    _element("planner-projection").innerText = projection_line
    _element("planner-projection").hidden = not projection_line
    _element("planner-suggestion").innerText = suggestion
    _element("planner-suggestion").hidden = not suggestion
