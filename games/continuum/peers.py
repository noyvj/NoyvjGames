"""Continuum -- R-33 (the parked K30): the "another settlement" ghost.

An opt-in way to see ONE anonymous other settlement's per-season trajectory beside your own, so you can
see how a similar settlement went without anyone being ranked or named. Everything here is pure (no DOM,
no network); `game.py` draws the result and `peers.js` owns the fetch() calls, the Settings switch and
the buttons. The backend half is `app/ghosts.py`.

## What is shared

Only when the player turns on "Publish my settlement's trajectory" in Settings (off by default, and only
possible while signed in; the server refuses a publish that does not say `opt_in`): one compact row per
season, `[season, era index, people, sustainability score]`, read from the per-season stat history the
game already keeps (`statlog.py`). Never free text, the settlement's name, a username or the save. The
server stores one such series per account, replaced each time, removable with one button.

## What is read

Pressing "Show another settlement" fetches ONE random published series from a similar band (the same
starting scenario and hard-mode setting, and an era within one of yours), never your own. Until enough
other players have published, the server returns nothing and the panel says so. The series is kept in
memory only: it is never put in the save, and a page reload forgets it.

## Why a separate chart rather than a third line on "Your city vs. history"

That chart plots output per person on a log axis against a real-world curve. A published series carries
people and a sustainability score, which are different quantities on different scales, so a line for
them on that axis would be misleading. The ghost therefore gets its own small chart in the same
disclosure, with a switch between the two quantities, and every number is also written out as text.
"""

import json
import math

import statlog

GAME_ID = "continuum"
MIN_SEASONS = 5          # a series shorter than this is not worth sharing (matches the server)
MAX_SEASONS = 150        # the server's cap; statlog keeps at most 120
REPUBLISH_EVERY = 5      # while publishing is on, re-send after this many new seasons (or an era change)
ERA_TOP = 7
MAX_PEOPLE = 10_000_000.0
REPORT_REASONS = ("implausible", "offensive", "other")

METRICS = ("score", "people")
METRIC_LABEL = {"score": "Sustainability score", "people": "People"}

CHART_W, CHART_H, CHART_PAD = 320, 150, 14


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


# --- what is sent --------------------------------------------------------------------------------
def my_series(history):
    """[season, era, people, score] for every row of the stat history (rows from `statlog.rows`)."""
    series = []
    for row in history or []:
        series.append([
            int(statlog.value(row, "season")),
            int(statlog.value(row, "era")),
            int(round(statlog.value(row, "population"))),
            round(float(statlog.value(row, "score")), 1),
        ])
    return series[-MAX_SEASONS:]


def publish_payload(history, scenario, hard_mode):
    """The exact body sent to POST /ghosts, or None while there are fewer than MIN_SEASONS seasons.
    The only keys are the game id, the scenario id, the hard-mode flag, the series and `opt_in`."""
    series = my_series(history)
    if len(series) < MIN_SEASONS:
        return None
    return {
        "game": GAME_ID,
        "scenario": str(scenario),
        "hard": bool(hard_mode),
        "series": series,
        "opt_in": True,
    }


def publish_json(history, scenario, hard_mode):
    payload = publish_payload(history, scenario, hard_mode)
    return "" if payload is None else json.dumps(payload)


def peer_query(era_index, scenario, hard_mode, exclude=None):
    """The band to ask for: the same scenario and hard flag and the player's current era (0 to 7).
    `exclude` is the id of the ghost on screen, so "show another" tries for a different one."""
    try:
        era = min(max(int(era_index), 0), ERA_TOP)
    except (TypeError, ValueError):
        era = 0
    query = {"scenario": str(scenario), "era": era, "hard": bool(hard_mode)}
    if isinstance(exclude, str) and exclude:
        query["exclude"] = exclude
    return query


def due_to_publish(history, last_sent_season, last_sent_era):
    """True when a re-publish is worth sending: the first time past MIN_SEASONS, then every
    REPUBLISH_EVERY seasons or when the era changed (so a long run does not hit the server each season)."""
    series = my_series(history)
    if len(series) < MIN_SEASONS:
        return False
    if last_sent_season is None:
        return True
    season, era = series[-1][0], series[-1][1]
    return season < last_sent_season or season - last_sent_season >= REPUBLISH_EVERY or era != last_sent_era


# --- what is received ----------------------------------------------------------------------------
def clean_ghost(raw):
    """A validated ghost dict from the server's JSON (a string or an already-parsed dict), or None when
    anything is wrong. Mirrors the server's bounds, because a response is data, not instructions."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return None
    if not isinstance(raw, dict):
        return None
    rows = raw.get("series")
    if not isinstance(rows, list) or not (1 <= len(rows) <= MAX_SEASONS):
        return None
    cleaned = []
    last = 0
    for item in rows:
        if not isinstance(item, (list, tuple)) or len(item) != 4 or not all(_is_number(v) for v in item):
            return None
        season, era, people, score = item
        if season != int(season) or era != int(era) or int(season) <= last:
            return None
        if not (0 <= era <= ERA_TOP) or not (0 <= people <= MAX_PEOPLE) or not (0 <= score <= 100):
            return None
        last = int(season)
        cleaned.append([int(season), int(era), int(round(people)), round(float(score), 1)])
    ghost_id = raw.get("id")
    if not isinstance(ghost_id, str) or not (8 <= len(ghost_id) <= 64):
        return None
    return {"id": ghost_id, "series": cleaned}


def reason_text(reason):
    """A plain message for a 200 reply that carried no ghost."""
    if reason == "too_few":
        return "Not enough players have shared a settlement yet, so there is nothing to show. Check back later."
    if reason == "no_match":
        return "No shared settlement is close to yours yet (same starting scenario, mode and nearby era). Try again later."
    return "Nothing to show right now."


UNAVAILABLE_TEXT = "Another settlement is not available right now. Nothing is wrong with your game; try again later."
SHOWN_TEXT = "Showing one anonymous settlement. It is not saved with yours and nobody is ranked."


def message(kind):
    """The status line for a lookup outcome: 'too_few', 'no_match', 'shown' or anything else (unavailable)."""
    if kind == "shown":
        return SHOWN_TEXT
    if kind in ("too_few", "no_match"):
        return reason_text(kind)
    return UNAVAILABLE_TEXT


# --- the comparison -------------------------------------------------------------------------------
def row_at(series, season):
    """The latest row at or before `season`, or None when the series starts later."""
    found = None
    for row in series:
        if row[0] <= season:
            found = row
        else:
            break
    return found


def _people(n):
    return f"{n} person" if n == 1 else f"{n} people"


def _both(row):
    return f"{_people(row[2])} and a score of {row[3]:.0f}"


def comparison_line(mine, ghost):
    """One plain sentence, e.g. 'At season 30 they had 41 people and a score of 62; you have 38 people
    and a score of 57.' Never says better or worse: it is a comparison, not a ranking."""
    if not mine:
        return "Advance a season to compare your settlement with this one."
    if not ghost:
        return ""
    mine_last, ghost_last = mine[-1], ghost[-1]
    season = min(mine_last[0], ghost_last[0])
    theirs, yours = row_at(ghost, season), row_at(mine, season)
    if theirs is None or yours is None:
        return "These two records do not overlap yet, so there is nothing to line up."
    if season == mine_last[0]:
        return f"At season {season} they had {_both(theirs)}; you have {_both(yours)}."
    return (
        f"Their record ends at season {season}, when they had {_both(theirs)}; "
        f"at that season you had {_both(yours)}."
    )


def metric_values(series, metric):
    index = 3 if metric == "score" else 2
    return [row[index] for row in series]


def text_equivalent(mine, ghost, metric):
    """The chart as words, for screen readers and the note under it."""
    label = METRIC_LABEL[metric].lower()
    if not ghost:
        return ""
    ghost_vals, mine_vals = metric_values(ghost, metric), metric_values(mine, metric)
    parts = [
        f"Chart of {label} by season. The other settlement (anonymous, dashed line) ran for "
        f"{ghost[-1][0]} seasons, from {ghost_vals[0]:.0f} to {ghost_vals[-1]:.0f}, "
        f"peaking at {max(ghost_vals):.0f}."
    ]
    if mine:
        parts.append(
            f"Yours (solid line) has run {mine[-1][0]} seasons, from {mine_vals[0]:.0f} to {mine_vals[-1]:.0f}, "
            f"peaking at {max(mine_vals):.0f}."
        )
    return " ".join(parts)


def compare_svg(mine, ghost, metric="score", width=CHART_W, height=CHART_H):
    """Your series (solid) and the other settlement's (dashed) against the season. The two lines differ
    in dash pattern and end marker as well as colour, so the chart never relies on colour alone."""
    if not ghost or metric not in METRICS:
        return ""
    pad = CHART_PAD
    seasons = [row[0] for row in ghost] + [row[0] for row in mine]
    first, last = min(seasons), max(seasons)
    values = metric_values(ghost, metric) + metric_values(mine, metric)
    low, high = 0.0, (100.0 if metric == "score" else max(10.0, max(values) * 1.1))

    def point(season, value):
        x = pad + ((season - first) / (last - first if last > first else 1)) * (width - 2 * pad)
        y = height - pad - ((value - low) / (high - low)) * (height - 2 * pad)
        return x, y

    def line(series, css):
        pts = [point(row[0], metric_values([row], metric)[0]) for row in series]
        if not pts:
            return ""
        end_x, end_y = pts[-1]
        if len(pts) == 1:
            path = ""
        else:
            path = f'<polyline class="{css}" fill="none" points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}"/>'
        marker = f'<circle class="{css}-end" cx="{end_x:.1f}" cy="{end_y:.1f}" r="3.5"/>'
        return path + marker

    label = (
        f"{METRIC_LABEL[metric]} by season: your settlement (solid line) and another settlement, "
        f"anonymous (dashed line)"
    )
    top = f"{high:.0f}"
    return (
        f'<svg viewBox="0 0 {width} {height}" class="trajectory-svg peer-svg" role="img" aria-label="{label}">'
        f'<rect x="0" y="0" width="{width}" height="{height}" class="trajectory-bg"/>'
        f'<text x="{pad}" y="{pad - 3}" class="peer-axis">{top}</text>'
        f'<text x="{pad}" y="{height - 2}" class="peer-axis">season {first}</text>'
        f'<text x="{width - pad}" y="{height - 2}" class="peer-axis" text-anchor="end">season {last}</text>'
        + line(ghost, "peer-line peer-line--ghost")
        + line(mine, "peer-line peer-line--mine")
        + "</svg>"
    )


def metric_button_text(metric):
    other = "people" if metric == "score" else "score"
    return f"Chart: {METRIC_LABEL[metric].lower()} (switch to {other})"


def next_metric(metric):
    return "people" if metric == "score" else "score"
