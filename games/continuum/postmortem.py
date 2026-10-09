"""Continuum -- K-14: the post-mortem report.

An auto-generated retrospective for the settlement so far, in the plain
language of an engineering post-mortem: what went well, what went wrong, the
root cause of the biggest livability drop, and three decisions to redo.

Continuum has no forced end (see `summary.py`), so "after any run" means the
report can be opened at any time from the Civilization Summary, and is written
from whatever the settlement has recorded up to that moment.

Where the facts come from (nothing is invented):

- the livability-vs-population record (`state.trajectory`, the same points the
  scatter chart draws) finds WHEN livability fell furthest;
- the per-season stat history (`statlog.py`) says WHY: which basic provision
  (food, shelter, gathering places, habitat layout) fell most in that season,
  with the real numbers;
- the Council Minutes (`minutes.py`, the policy log) supply the decisions made
  just before the drop, to look at again.

A "redo" hint is a prompt to think about, never a verdict: it says what to
check first, not what would certainly have worked. Every line is plain text, a
pure function of saved data, so the report cannot change the simulation, and
bad or missing data degrades to a shorter report.
"""

import minutes
import sim
import statlog
import summary
import sustainability
import trajectory

SEASONS_PER_YEAR = 4
SEASON_NAMES = ["Spring", "Summer", "Autumn", "Winter"]

MIN_SEASONS = 3          # fewer recorded seasons than this: "not enough yet"
DROP_NOTABLE = 3.0       # a livability fall smaller than this (points) is not a "drop"
MAX_LINES = 4
REDO_COUNT = 3

# What each provision is, in the words used for the root cause and the hints.
CAUSES = {
    "fed_pct": ("Food security", "food for everyone"),
    "shelter_pct": ("Shelter", "shelter for everyone"),
    "social_pct": ("Gathering places", "gathering places for everyone"),
    "habitat_pct": ("Habitat layout", "a habitat layout that works for everyone"),
}


def when(season):
    """'Year 3, Autumn' for a season number."""
    index = max(1, int(season)) - 1
    return f"Year {index // SEASONS_PER_YEAR + 1}, {SEASON_NAMES[index % SEASONS_PER_YEAR]}"


def _progress(campaign):
    """(state-like city values, trajectory points) of the REAL forward
    progress, correct even during a Look Back (the live state is then a past
    snapshot and the real one is parked)."""
    parked = summary._live_progress_city(campaign)
    if parked is not None:
        season = parked.get("season") if isinstance(parked.get("season"), (int, float)) else campaign.state.season
        points = trajectory.clean_points(parked.get("trajectory"))
        peak = parked.get("peak_score") if isinstance(parked.get("peak_score"), (int, float)) else None
        lowest = parked.get("lowest_score_seen") if isinstance(parked.get("lowest_score_seen"), (int, float)) else None
        return int(season), points, peak, lowest
    state = campaign.state
    return int(state.season), trajectory.clean_points(state.trajectory), state.peak_score, state.lowest_score_seen


def livability_series(campaign):
    """[(season, livability 0..100, population)] for the recorded seasons."""
    season, points, _peak, _lowest = _progress(campaign)
    last = season - 1
    n = len(points)
    return [(last - (n - 1 - i), p[3], int(p[2])) for i, p in enumerate(points) if last - (n - 1 - i) >= 1]


def biggest_drop(series):
    """(drop_points, index into series) of the largest one-season livability
    fall, or None with fewer than two points."""
    best = None
    for i in range(1, len(series)):
        fall = series[i - 1][1] - series[i][1]
        if best is None or fall > best[0]:
            best = (fall, i)
    return best


def _row_for(history, season):
    for row in history:
        if int(statlog.value(row, "season")) == season:
            return row
    return None


def root_cause(series, drop, history):
    """The root-cause block for the biggest drop: a dict with `headline`,
    `lines` (what changed, with numbers) and `cause` (a CAUSES key or None)."""
    fall, i = drop
    season, liv_now, pop_now = series[i]
    _prev_season, liv_before, pop_before = series[i - 1]
    headline = (
        f"Livability fell {fall:.0f} points in one season, from {liv_before:.0f} to {liv_now:.0f}, "
        f"in {when(season)}."
    )
    lines = []
    cause = None
    after = _row_for(history, season)
    before = _row_for(history, season - 1)
    if after is not None and before is not None:
        falls = {
            key: statlog.value(before, key) - statlog.value(after, key) for key in CAUSES
            if key != "habitat_pct" or int(statlog.value(after, "era")) >= sim.era_index("space")
        }
        key = max(falls, key=lambda k: falls[k])
        if falls[key] > 0.5:
            cause = key
            name, _need = CAUSES[key]
            lines.append(
                f"The provision that fell furthest was {name.lower()}: "
                f"{statlog.value(before, key):.0f}% met before, {statlog.value(after, key):.0f}% after."
            )
            pop = int(statlog.value(after, "population"))
            if key == "fed_pct":
                gathered = statlog.value(after, "food_gathered")
                needed = pop * sim.FOOD_PER_PERSON
                lines.append(
                    f"That season the settlement gathered {gathered:.0f} food for {pop} people who needed "
                    f"{needed:.0f}."
                )
                lost = int(statlog.value(after, "deaths"))
                if lost:
                    lines.append(f"{lost} {'person' if lost == 1 else 'people'} were lost.")
            elif key == "shelter_pct":
                lines.append(
                    f"There were {pop} people and shelter for {statlog.value(after, 'housing'):.0f} "
                    f"(population was {int(statlog.value(before, 'population'))} the season before)."
                )
            elif key == "social_pct":
                lines.append(f"There were {pop} people, up from {int(statlog.value(before, 'population'))}.")
            else:
                lines.append(
                    f"The habitat layout covered {statlog.value(after, 'habitat_layout'):.0f}% of {pop} people."
                )
    if cause is None:
        lines.append(
            f"Population went from {pop_before} to {pop_now} over that season. The detailed record of what "
            "each provision did that season is not available (it was before the stat history began, or "
            "the fall had no single provision behind it)."
        )
    return {"headline": headline, "lines": lines, "cause": cause}


def _redo_hint(kind, cause):
    need = CAUSES[cause][1] if cause in CAUSES else "everyone's basic needs"
    if kind == "build":
        return f"Before building this, check there is {need}. What else could the materials have done?"
    if kind == "research":
        return f"Before studying this, check there is {need}. Is there a discovery that would help sooner?"
    return f"Before moving on, check there is {need}. Is the settlement ready for what comes next?"


def decisions_to_redo(ui, pivot_season, cause):
    """Up to three of the player's last Council Minutes decisions made at or
    before `pivot_season`, each with a prompt. Newest first."""
    entries = [e for e in minutes.entries(ui) if e["season"] <= pivot_season and e["kind"] != "order"]
    out = []
    for entry in reversed(entries[-REDO_COUNT:]):
        out.append(
            {
                "when": f"{when(entry['season'])} ({sim.ERA_LABEL[entry['era']]})",
                "decision": entry["text"],
                "hint": _redo_hint(entry["kind"], cause),
            }
        )
    return out


def _went_well(campaign, history, series, peak_score):
    lines = []
    state = campaign.state
    if peak_score is not None:
        hard = sustainability.is_hard_mode(state)
        lines.append(
            f"Sustainability peaked at {peak_score:.0f} out of 100 "
            f"({sustainability.score_label(peak_score, hard)})."
        )
    if history:
        streak = int(max(statlog.value(r, "calm") for r in history))
        if streak >= 3:
            lines.append(f"Longest calm run: {streak} seasons in a row with everyone fed and nobody lost.")
        fed = sum(1 for r in history if statlog.value(r, "fed_pct") >= 99.5)
        if fed / len(history) >= 0.8:
            lines.append(f"Everyone was fed in {fed} of the last {len(history)} recorded seasons.")
    if series:
        first, peak = series[0][2], max(p for _, _, p in series)
        if peak > first:
            lines.append(f"Population grew from {first} to a peak of {peak}.")
    done = summary.summary(campaign)
    if done["eras_completed"]:
        lines.append(f"{done['eras_completed']} era(s) completed; the furthest reached is the {done['furthest_era_label']} era.")
    researched = len(campaign.tree.researched)
    if researched:
        lines.append(f"{researched} discoveries studied.")
    return lines[:MAX_LINES]


def _went_wrong(campaign, history, series, lowest_score):
    lines = []
    state = campaign.state
    hard = sustainability.is_hard_mode(state)
    if lowest_score is not None and lowest_score < 70:
        lines.append(
            f"Sustainability dropped as low as {lowest_score:.0f} out of 100 "
            f"({sustainability.score_label(lowest_score, hard)})."
        )
    if history:
        deaths = int(sum(statlog.value(r, "deaths") for r in history))
        hungry = sum(1 for r in history if statlog.value(r, "fed_pct") < 99.5)
        if deaths:
            lines.append(f"{deaths} people were lost across {hungry} hungry seasons.")
        crowded = sum(1 for r in history if statlog.value(r, "shelter_pct") < 99.5)
        if crowded >= 3:
            lines.append(f"Shelter fell short of the population in {crowded} of {len(history)} recorded seasons.")
        gathered = sum(statlog.value(r, "food_gathered") for r in history)
        spoiled = sum(statlog.value(r, "spoiled") for r in history)
        if gathered > 0 and spoiled / gathered >= 0.15:
            lines.append(f"{spoiled:.0f} of {gathered:.0f} food gathered ({spoiled / gathered * 100:.0f}%) spoiled over the storage limit.")
        low_land = min(statlog.value(r, "land") for r in history)
        if low_land < 60:
            lines.append(f"Land health fell as low as {low_land:.0f}%.")
        for key, label in (("pollution", "Pollution"), ("sprawl", "Sprawl")):
            worst = max(statlog.value(r, key) for r in history)
            if worst >= 40:
                lines.append(f"{label} reached {worst:.0f}%.")
    return lines[:MAX_LINES]


def build(campaign):
    """The whole report as a plain dict. Never raises on odd saved data."""
    ui = campaign.ui if isinstance(campaign.ui, dict) else {}
    history = statlog.rows(ui)
    series = livability_series(campaign)
    season, _points, peak, lowest = _progress(campaign)
    seasons_played = max(0, season - 1)
    report = {
        "ready": seasons_played >= MIN_SEASONS and len(series) >= 2,
        "seasons": seasons_played,
        "went_well": [],
        "went_wrong": [],
        "root_cause": None,
        "redo": [],
        "notes": [],
    }
    if not report["ready"]:
        report["notes"].append(
            f"Play at least {MIN_SEASONS} seasons first. A post-mortem needs something to look back on "
            f"(so far: {seasons_played})."
        )
        return report
    report["went_well"] = _went_well(campaign, history, series, peak)
    report["went_wrong"] = _went_wrong(campaign, history, series, lowest)
    drop = biggest_drop(series)
    pivot = None
    cause = None
    if drop is not None and drop[0] >= DROP_NOTABLE:
        block = root_cause(series, drop, history)
        report["root_cause"] = block
        cause = block["cause"]
        pivot = series[drop[1]][0]
    else:
        worst = drop[0] if drop is not None else 0.0
        report["root_cause"] = {
            "headline": f"No major livability drop. The worst single-season fall was {max(worst, 0.0):.1f} points.",
            "lines": [],
            "cause": None,
        }
        if history:
            pivot = int(statlog.value(min(history, key=lambda r: statlog.value(r, "score")), "season"))
    if pivot is not None:
        report["redo"] = decisions_to_redo(ui, pivot, cause)
    if not report["redo"]:
        report["notes"].append(
            "No decisions were minuted before that point, so there is nothing to look at again. Research and "
            "building choices are minuted in the Council Minutes."
        )
    if history and len(history) >= statlog.MAX_ROWS:
        report["notes"].append(f"The stat history keeps the latest {statlog.MAX_ROWS} seasons, so earlier ones are not in this report.")
    elif not history:
        report["notes"].append("This settlement has no per-season stat history (it predates it), so the root cause is less detailed.")
    return report


def lines(report):
    """The report as plain text lines (also what a screen reader hears)."""
    if not isinstance(report, dict):
        return []
    out = ["Post-mortem"]
    if not report.get("ready"):
        return out + list(report.get("notes", []))
    out.append("What went well")
    out.extend(report["went_well"] or ["Nothing stood out yet."])
    out.append("What went wrong")
    out.extend(report["went_wrong"] or ["Nothing went badly wrong."])
    out.append("Root cause of the biggest livability drop")
    block = report["root_cause"]
    if block:
        out.append(block["headline"])
        out.extend(block["lines"])
    out.append("Three decisions to redo")
    if report["redo"]:
        for item in report["redo"]:
            out.append(f"{item['when']}: {item['decision']} {item['hint']}")
    else:
        out.append("None to show.")
    out.extend(report["notes"])
    return out
