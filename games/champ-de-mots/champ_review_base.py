"""The Review tab's settings and candidate lists: random word, grammar, marathon, cram and weak-spot candidates.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from js import document

from champ_rules import STAGE_AUTOMATED, STAGE_ORDER, STAGE_RANK, STAGE_SEED
from champ_model import is_due, state
from champ_qbuild import V_BLANK_ENDING, V_BLANK_WORD, V_CONJUGATION_SWAP
from champ_util import _element
from champ_stats import _topic_plots, dashboard_weakest_topics


review_choice_proxies = []


REVIEW_RNG = random.Random()


def _destroy_review_choice_proxies():
    for proxy in review_choice_proxies:
        proxy.destroy()
    review_choice_proxies.clear()


# ===========================================================================
# L19: a personal phrasebook -- bookmark any plot into a custom list that
# cuts across the syllabus rows, and practise just that list. Saved as a list
# of plot ids (validated against the real farm on load), newest last.
# ===========================================================================
PHRASEBOOK_LIMIT = 200
PHRASEBOOK_SESSION_MAX = 40
PHRASEBOOK_MODE = "phrasebook"
PHRASEBOOK_EMPTY_MESSAGE = "Your phrasebook is empty. Use the star while you practise to save an item here."


# ===========================================================================
# Milestone 11 — the Review tab (design doc §14.4)
# ===========================================================================
#
# Two opt-in cross-section modes, reusing Milestone 3's own generator rather
# than inventing a second one: Random Word Review samples vocab/phrase plots
# from any unlocked week, Grammar Review the same but grammar-only and
# biased toward fill-in-the-blank/conjugation prompts. Neither ever grows a
# plot's stage or touches row-unlock state — only the daily watering loop
# does that — so Review can't be used to route around §7's pacing gate. A
# correct answer still nudges that plot's interval a little further out
# rather than being untracked entirely (§14.4's own wording).

DEFAULT_REVIEW_COUNT = 10
MIN_REVIEW_COUNT = 1
MAX_REVIEW_COUNT = 25


GRAMMAR_REVIEW_PREFERRED_VARIANTS = (V_BLANK_WORD, V_CONJUGATION_SWAP, V_BLANK_ENDING)

# L17 -- the mixed review marathon: a long session across the whole farm
# (every topic type, any row), pulling plots that are due. Plots that have
# been watered before come first, most overdue at the top; plots that were
# never watered fill any remaining slots, so a mature farm gets a genuine
# catch-up session and a brand-new farm still gets something to do.
MARATHON_MODE = "marathon"
MARATHON_COUNT = 40
MARATHON_EMPTY_MESSAGE = (
    "Nothing is due for a marathon right now — come back once more plots are ready "
    "for water, or use a Random Word or Grammar Review."
)


def marathon_candidates(farm=None, day=None):
    farm = state if farm is None else farm
    day = farm.current_day if day is None else day
    due = [p for p in farm.plots if is_due(p, day)]
    watered = sorted((p for p in due if p.last_reviewed is not None), key=lambda p: p.next_due)
    never = [p for p in due if p.last_reviewed is None]
    return (watered + never)[:MARATHON_COUNT]


# L29 -- "quick water": the lightest possible session, ONE question on the
# single most overdue plot, for a very short study break. It is an ordinary
# review under the hood (a correct answer waters the plot exactly as any Review
# does), and every answer also lands in the practice ledger as "quick", so it
# always visibly counts toward the headline practice score and the study streak.
QUICK_WATER_MODE = "quick"
QUICK_WATER_EMPTY_MESSAGE = (
    "Nothing is due for a quick water right now. Come back once a plot is ready "
    "for water, or use a Random Word or Grammar Review."
)


# L3: weak-spot drill -- a session built only from what the game already
# flags as shaky: plots sitting in the weeds (known mix-ups the error-pattern
# digest classifies) and the touched plots of the dashboard's weakest topics.
WEAK_SPOT_MODE = "weakspots"
WEAK_SPOT_SESSION_MAX = 20
WEAK_SPOT_TOPIC_COUNT = 5
WEAK_SPOT_EMPTY_MESSAGE = (
    "Nothing is flagged as a weak spot yet. Mix-ups and low-growth topics show up "
    "here once you have practised a little."
)


def weak_spot_candidates(farm=None):
    """Weeds first (the known mix-ups), then the lowest-ease touched plots of
    the weakest topics that are not already Automated. At most
    WEAK_SPOT_SESSION_MAX, no duplicates."""
    farm = state if farm is None else farm
    chosen, seen = [], set()
    for plot in farm.plots:
        if plot.in_weeds and plot.plot_id not in seen:
            chosen.append(plot)
            seen.add(plot.plot_id)
    for entry in dashboard_weakest_topics(WEAK_SPOT_TOPIC_COUNT):
        record = farm.topic_records[farm.topic_pos[entry["topic_id"]]]
        shaky = [
            p for p in _topic_plots(record["topic"])
            if p.last_reviewed is not None and p.stage != STAGE_AUTOMATED and p.plot_id not in seen
        ]
        shaky.sort(key=lambda p: (p.ease_factor, STAGE_RANK[p.stage]))
        for plot in shaky:
            chosen.append(plot)
            seen.add(plot.plot_id)
    return chosen[:WEAK_SPOT_SESSION_MAX]


# L25: exam cram -- a dense session over a chosen range of weeks (say, the
# chapters an exam covers), weakest material first, whatever its schedule.
CRAM_MODE = "cram"
CRAM_SESSION_MAX = 60


def cram_range(first, last):
    """(low, high) week sequence numbers, in order, clamped to the farm."""
    sequences = [row.sequence for row in state.rows]
    low_bound, high_bound = min(sequences), max(sequences)
    try:
        a, b = int(first), int(last)
    except (TypeError, ValueError):
        a, b = low_bound, high_bound
    a, b = max(low_bound, min(high_bound, a)), max(low_bound, min(high_bound, b))
    return (a, b) if a <= b else (b, a)


def cram_candidates(first, last, farm=None):
    """Every plot in weeks first..last, weakest (lowest stage, lowest ease)
    first, capped at CRAM_SESSION_MAX, then interleaved by stage so the
    session doesn't run as one blocked stretch of a single stage."""
    farm = state if farm is None else farm
    low, high = cram_range(first, last)
    pool = [p for p in farm.plots if low <= p.sequence <= high]
    # Shuffle first so the stable sort below breaks ties at random: on a fresh
    # farm everything is a Seed at default ease, and a plot-id tie-break would
    # fill the whole cap from the earliest weeks of the range.
    REVIEW_RNG.shuffle(pool)
    pool.sort(key=lambda p: (STAGE_RANK[p.stage], p.ease_factor))
    return _interleave_by_stage(pool[:CRAM_SESSION_MAX], REVIEW_RNG)


def _populate_cram_selects():
    for select_id, default_last in (("review-cram-from-select", False), ("review-cram-to-select", True)):
        select = _element(select_id)
        select.innerHTML = ""
        rows = state.rows
        for row in rows:
            option = document.createElement("option")
            option.value = str(row.sequence)
            title = f": {row.chapter_title}" if row.chapter_title else ""
            option.innerText = f"Week {row.sequence}{title}"
            select.appendChild(option)
        select.value = str(rows[-1].sequence if default_last else rows[0].sequence)


REVIEW_SUMMARY_MESSAGE = "Review complete — {correct}/{total} correct."
REVIEW_EMPTY_MESSAGE = (
    "Nothing matches those filters yet — try a lower minimum stage, "
    "or check back once more plots have grown."
)


def review_candidates(topic_types, min_stage=STAGE_SEED, farm=None):
    """Every plot eligible for a Review session: the right `topic_type`, in
    an unlocked row (locked rows are off-limits to Review exactly as they
    are to the farm itself), at or above the minimum growth stage."""
    farm = state if farm is None else farm
    threshold = STAGE_RANK[min_stage]
    return [
        p
        for p in farm.plots
        if p.topic_type in topic_types
        and farm.is_row_unlocked(p.sequence)
        and STAGE_RANK[p.stage] >= threshold
    ]


def _interleave_by_stage(candidates, rng):
    """Improvement Ideas §3: deliberate interleaving, not a default newest-
    first (or, here, a plain shuffle that could still cluster by chance) --
    review sessions should mix old (well-established) and new (recently
    planted) material throughout, since interleaved practice beats blocked
    practice for retention. Groups candidates by growth stage, shuffles
    within each stage bucket, then round-robins across buckets so the
    resulting order alternates stage-to-stage rather than leaving the mix
    to chance. Once the game has many more mature plots than fresh ones (the
    common case later in a session), a plain random sample would still be
    dominated by whichever stage has the most candidates; round-robining
    guarantees every present stage gets an early turn instead."""
    buckets = {stage: [] for stage in STAGE_ORDER}
    for plot in candidates:
        buckets[plot.stage].append(plot)
    for bucket in buckets.values():
        rng.shuffle(bucket)
    present = [stage for stage in STAGE_ORDER if buckets[stage]]
    interleaved = []
    cursors = {stage: 0 for stage in present}
    while True:
        progressed = False
        for stage in present:
            i = cursors[stage]
            if i < len(buckets[stage]):
                interleaved.append(buckets[stage][i])
                cursors[stage] = i + 1
                progressed = True
        if not progressed:
            break
    return interleaved
