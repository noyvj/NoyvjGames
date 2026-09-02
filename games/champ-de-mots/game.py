"""Le Champ de Mots — a French-syllabus farming game.

Runs in-browser via Pyodide, per the hub's default stack. Milestone 2: the
plant-state data model and the spaced-repetition scheduler underneath it
(design doc §6). Plots are built straight from the combined FREN151/FREN152
catalog and laid out as one continuous run of rows, sequence 1-23, with no
season break between the two courses.

Design doc §3's wellbeing constraint is enforced here rather than only in the
UI: a plot's visible growth stage only ever moves *up*. An incorrect recall
reschedules the plot sooner (it "needs water again") but never demotes the
plant, never removes it, and never produces a failure state.
"""

import json

CATALOG_FILENAME = "fren_combined_catalog.json"

# --- Spaced repetition constants (design doc §6) ---------------------------
# Lightweight SM-2-flavoured scheduling: simplicity over academic rigour.
DEFAULT_EASE = 2.5
MIN_EASE = 1.3
MAX_EASE = 3.0
EASE_CORRECT_BONUS = 0.1
EASE_INCORRECT_PENALTY = 0.2

FIRST_INTERVAL_DAYS = 1
SECOND_INTERVAL_DAYS = 3
RESET_INTERVAL_DAYS = 1
BLOOMING_INTERVAL_DAYS = 7
AUTOMATION_INTERVAL_DAYS = 14

# --- Growth stages (design doc §3) -----------------------------------------
STAGE_SEED = "seed"
STAGE_SPROUT = "sprout"
STAGE_BUDDING = "budding"
STAGE_BLOOMING = "blooming"
STAGE_AUTOMATED = "automated"

STAGE_ORDER = [STAGE_SEED, STAGE_SPROUT, STAGE_BUDDING, STAGE_BLOOMING, STAGE_AUTOMATED]
STAGE_RANK = {stage: index for index, stage in enumerate(STAGE_ORDER)}

# FREN151 is already finished in real life, so its 11 rows are a catch-up
# zone that is open from the start (design doc §7). Used from Milestone 6.
CATCH_UP_MAX_SEQUENCE = 11


def _read_catalog_json():
    """The page's boot script fetches the catalog and hands it to Python as a
    window global (`CATALOG_JSON`) before running this file; the pytest
    harness sets the same attribute on its fake `js` module. A filesystem
    fallback keeps the module importable outside both."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "CATALOG_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CATALOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


CATALOG = json.loads(_read_catalog_json())

CHAPTER_TITLES = {str(c["number"]): c["title"] for c in CATALOG.get("chapters", [])}


class Plot:
    """One plot of the farm: a single fact you are trying to grow.

    Granularity follows the design doc's own wording — "a new unit unlocks a
    batch of plots (vocab words, a conjugation pattern, a grammar rule)". So
    vocab/phrase/phonetic get one plot per item, while a grammar topic is a
    single plot whose example items feed its question variants (§5).
    """

    def __init__(self, plot_id, topic, week, items, label):
        self.plot_id = plot_id
        self.topic_id = topic["id"]
        self.topic_type = topic["topic_type"]
        self.topic_title = topic["title"]
        self.rule = topic.get("rule")
        self.items = items
        self.label = label

        self.sequence = week["sequence"]
        self.course = week["course"]
        self.week = week["week"]
        self.chapter = week["chapter"]

        # SRS state (§6)
        self.ease_factor = DEFAULT_EASE
        self.interval_days = 0
        self.last_reviewed = None
        self.next_due = None
        self.correct_streak = 0
        self.stage = STAGE_SEED

    @property
    def is_grammar_rule(self):
        return self.topic_type == "grammar"


class Row:
    """One row of the farm — one syllabus week, keyed by its sequence number."""

    def __init__(self, week, plot_ids):
        self.sequence = week["sequence"]
        self.course = week["course"]
        self.week = week["week"]
        self.chapter = week["chapter"]
        self.chapter_title = CHAPTER_TITLES.get(str(week["chapter"]), "")
        self.plot_ids = plot_ids

    @property
    def chapter_label(self):
        chapter = self.chapter
        prefix = "Bridge" if str(chapter) == "Bridge" else f"Ch. {chapter}"
        return f"{prefix} — {self.chapter_title}" if self.chapter_title else prefix

    @property
    def label(self):
        return f"{self.sequence}. {self.course} wk {self.week}"


def candidate_stage(plot):
    """The stage the plot's current scheduling state would justify."""
    if plot.last_reviewed is None or plot.correct_streak == 0:
        return STAGE_SEED
    if plot.interval_days >= AUTOMATION_INTERVAL_DAYS:
        return STAGE_AUTOMATED
    if plot.interval_days >= BLOOMING_INTERVAL_DAYS:
        return STAGE_BLOOMING
    if plot.correct_streak >= 2:
        return STAGE_BUDDING
    return STAGE_SPROUT


def is_due(plot, day):
    """A plot needs water today if it has never been watered, or its interval
    has elapsed."""
    if plot.next_due is None:
        return True
    return day >= plot.next_due


def is_wilting(plot, day):
    """Overdue, not failing. A seed has no plant to droop, so it never wilts —
    it is simply waiting to be planted."""
    if plot.next_due is None or plot.last_reviewed is None:
        return False
    return day > plot.next_due


def schedule_after_review(plot, correct, day):
    """Apply one review outcome to a plot's SRS state (design doc §6)."""
    if correct:
        plot.correct_streak += 1
        if plot.correct_streak == 1:
            plot.interval_days = FIRST_INTERVAL_DAYS
        elif plot.correct_streak == 2:
            plot.interval_days = SECOND_INTERVAL_DAYS
        else:
            plot.interval_days = max(
                plot.interval_days + 1, int(round(plot.interval_days * plot.ease_factor))
            )
        plot.ease_factor = min(MAX_EASE, plot.ease_factor + EASE_CORRECT_BONUS)
    else:
        plot.correct_streak = 0
        plot.interval_days = RESET_INTERVAL_DAYS
        plot.ease_factor = max(MIN_EASE, plot.ease_factor - EASE_INCORRECT_PENALTY)

    plot.last_reviewed = day
    plot.next_due = day + plot.interval_days

    # Monotonic: a plant never visibly regresses (§3).
    candidate = candidate_stage(plot)
    if STAGE_RANK[candidate] > STAGE_RANK[plot.stage]:
        plot.stage = candidate
    return plot


class FarmState:
    """The whole farm: every plot, every row, and what day it is."""

    def __init__(self, catalog):
        self.catalog = catalog
        self.current_day = 0
        self.plots = []
        self.plots_by_id = {}
        self.rows = []
        self._build_farm()

    def _build_farm(self):
        for week in self.catalog["weeks"]:
            plot_ids = []
            for topic in week["topics"]:
                if topic["topic_type"] == "grammar":
                    plot = Plot(
                        plot_id=topic["id"],
                        topic=topic,
                        week=week,
                        items=list(topic["items"]),
                        label=topic["title"],
                    )
                    self._register(plot, plot_ids)
                else:
                    for index, item in enumerate(topic["items"]):
                        plot = Plot(
                            plot_id=f"{topic['id']}-i{index:02d}",
                            topic=topic,
                            week=week,
                            items=[item],
                            label=item["fr"],
                        )
                        self._register(plot, plot_ids)
            self.rows.append(Row(week, plot_ids))

    def _register(self, plot, plot_ids):
        self.plots.append(plot)
        self.plots_by_id[plot.plot_id] = plot
        plot_ids.append(plot.plot_id)

    # --- queries -----------------------------------------------------------
    def row_by_sequence(self, sequence):
        for row in self.rows:
            if row.sequence == sequence:
                return row
        return None

    def row_plots(self, sequence):
        row = self.row_by_sequence(sequence)
        if row is None:
            return []
        return [self.plots_by_id[pid] for pid in row.plot_ids]

    def is_row_unlocked(self, sequence):
        """Row-unlock pacing lands in Milestone 6; every row is open until then."""
        return True

    def available_plots(self):
        return [p for p in self.plots if self.is_row_unlocked(p.sequence)]

    def due_plots(self):
        return [p for p in self.available_plots() if is_due(p, self.current_day)]

    def next_due_plot(self):
        due = self.due_plots()
        if not due:
            return None
        # Longest-overdue first; unwatered seeds count as maximally overdue so
        # new plots get planted rather than starved by an endless review queue.
        return min(due, key=lambda p: (p.next_due if p.next_due is not None else -1))

    # --- mutations ---------------------------------------------------------
    def review(self, plot_id, correct, day=None):
        plot = self.plots_by_id.get(plot_id)
        if plot is None:
            return None
        return schedule_after_review(
            plot, correct, self.current_day if day is None else day
        )

    def advance_day(self, days=1):
        self.current_day += max(0, int(days))
        return self.current_day


state = FarmState(CATALOG)
