"""Read-only counts over the farm: row mastery, weakest topics, days since last touch, stage distribution, automated plot
counts and the topic/plot lookups the review and proficiency modes share.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from champ_rules import STAGE_AUTOMATED, STAGE_ORDER, STAGE_RANK
from champ_catalog import CATALOG
from champ_model import state


# Improvement Ideas §5: a progress dashboard, deliberately its own separate
# screen rather than more numbers crammed into the calm main status line --
# per-row mastery, the weakest touched topics, and how long it's been since
# anything was watered at all. Purely a read-out: nothing here mutates SRS
# state, same posture as the Review tab's own informational pieces.
DASHBOARD_WEAKEST_TOPIC_COUNT = 5


def dashboard_row_mastery(sequence):
    """0-100: how far a row's plots have grown on average, scaled by the
    highest reachable stage rank -- not just "% Automated," so partial
    progress (a row full of Sprouts) still reads as real progress."""
    plots = state.row_plots(sequence)
    if not plots:
        return 0.0
    max_rank = len(STAGE_ORDER) - 1
    return sum(STAGE_RANK[p.stage] for p in plots) / (len(plots) * max_rank) * 100


def dashboard_weakest_topics(limit=DASHBOARD_WEAKEST_TOPIC_COUNT):
    """The lowest-average-stage topics among ones you've actually touched at
    least once -- an untouched topic isn't "weak," it's just not started
    yet, so it's excluded rather than tying every fresh row for last place."""
    scored = []
    for record in state.topic_records:
        if not state.is_row_unlocked(record["sequence"]):
            continue
        plots = _topic_plots(record["topic"])
        touched = [p for p in plots if p.last_reviewed is not None]
        if not touched:
            continue
        avg_rank = sum(STAGE_RANK[p.stage] for p in touched) / len(touched)
        scored.append(
            {
                "topic_id": record["topic"]["id"],
                "title": record["topic"]["title"],
                "sequence": record["sequence"],
                "avg_rank": avg_rank,
            }
        )
    scored.sort(key=lambda entry: entry["avg_rank"])
    return scored[:limit]


def dashboard_days_since_last_touch():
    """None if nothing has ever been watered; otherwise how many in-game
    days have passed since the most recently touched plot."""
    touched_days = [p.last_reviewed for p in state.plots if p.last_reviewed is not None]
    if not touched_days:
        return None
    return state.current_day - max(touched_days)


def dashboard_stage_distribution():
    """L27 -- how the whole farm's plots split across the five growth
    stages: [(stage, count, percent)] in STAGE_ORDER. Purely a count of
    existing plot.stage values, no new state."""
    total = len(state.plots)
    counts = {stage: 0 for stage in STAGE_ORDER}
    for plot in state.plots:
        counts[plot.stage] += 1
    return [(stage, counts[stage], (100 * counts[stage] / total) if total else 0.0) for stage in STAGE_ORDER]


def automated_plot_count():
    return sum(1 for plot in state.plots if plot.stage == STAGE_AUTOMATED)


def fully_automated_row_count():
    count = 0
    for row in state.rows:
        plots = state.row_plots(row.sequence)
        if plots and all(plot.stage == STAGE_AUTOMATED for plot in plots):
            count += 1
    return count


# ===========================================================================
# Milestone 12 — weekly proficiency tests (design doc §14.5)
# ===========================================================================
#
# One test per `sequence` entry (per taught week), covering every topic in
# that week regardless of any plot's current SRS state, purely informational
# — score plus a per-topic breakdown, no gating of anything. Unlike Review
# (Milestone 11), a proficiency test never touches a plot's schedule at all;
# it only reads the catalog and reuses generate_question().


def proficiency_test_topics(sequence):
    """Every topic in one week entry, catalog order, regardless of any
    plot's current SRS state (§14.5, literally)."""
    for week in CATALOG["weeks"]:
        if week["sequence"] == sequence:
            return week["topics"]
    return []


def _topic_plots(topic):
    """Every plot that belongs to one catalog topic. A grammar topic is a
    single plot (Milestone 2's granularity call); everything else is one
    plot per item, so this is every item's plot in catalog order."""
    if topic["topic_type"] == "grammar":
        plot = state.plots_by_id.get(topic["id"])
        return [plot] if plot is not None else []
    plots = []
    for index in range(len(topic["items"])):
        plot = state.plots_by_id.get(f"{topic['id']}-i{index:02d}")
        if plot is not None:
            plots.append(plot)
    return plots
