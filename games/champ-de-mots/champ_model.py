"""The farm itself: Plot, Row and FarmState (the plots, the spaced-repetition scheduler, the unlock chain), the one live
`state`, and the plot-record helpers the save code uses. Ask for this file to change how a plot grows or is scheduled.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from champ_rules import (
    AUTOMATION_INTERVAL_DAYS, BLOOMING_INTERVAL_DAYS, COMBO_BONUS_PER_STEP,
    CONFIDENT_WRONG_PENALTY_MULTIPLIER, DEFAULT_EASE, EASE_CORRECT_BONUS, EASE_INCORRECT_PENALTY,
    FIRST_INTERVAL_DAYS, MAX_COMBO_BONUS, MAX_EASE, MIN_EASE, RESET_INTERVAL_DAYS, SECOND_INTERVAL_DAYS,
    STAGE_AUTOMATED, STAGE_BLOOMING, STAGE_BUDDING, STAGE_RANK, STAGE_SEED, STAGE_SPROUT,
    UNSURE_WRONG_PENALTY_MULTIPLIER,
)
from champ_catalog import CATALOG, CHAPTER_TITLES


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

        # Improvement Ideas §2: "weeds" -- a specific-error overlay, not a
        # growth stage. Set the moment a wrong answer matches a known
        # commonly-confused counterpart (WEED_CONFUSIONS below), cleared on
        # the next correct answer, same "one watering brings it back" rule
        # wilting already follows. Independent of `stage`, which never
        # regresses.
        self.in_weeds = False
        # L-18: consecutive wrong answers on this plot (cleared by a correct
        # one). At LEECH_THRESHOLD it becomes a "stubborn weed" (see below).
        self.fail_run = 0
        # 2026-10-08 watering rule: the in-game day of this plot's last FULL
        # watering (the first correct answer for it on a day, from any
        # plot-linked activity), saved with the plot. `nudged_day` is the day
        # of its last nudge (a later correct answer the same day); it is
        # transient session state and never saved (see water_plot()).
        self.last_watered = None
        self.nudged_day = None

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


def schedule_after_review(plot, correct, day, combo=0, confidence=None):
    """Apply one review outcome to a plot's SRS state (design doc §6).

    `combo` (a session-wide consecutive-correct count, not this plot's own
    correct_streak) and `confidence` ("sure" | "unsure" | None) are both
    optional and default to no-ops, so every pre-existing call site keeps
    its exact prior behaviour."""
    if correct:
        plot.correct_streak += 1
        if plot.correct_streak == 1:
            plot.interval_days = FIRST_INTERVAL_DAYS
        elif plot.correct_streak == 2:
            plot.interval_days = SECOND_INTERVAL_DAYS
        else:
            grown = max(
                plot.interval_days + 1, int(round(plot.interval_days * plot.ease_factor))
            )
            combo_bonus = 1 + min(MAX_COMBO_BONUS, max(0, combo) * COMBO_BONUS_PER_STEP)
            plot.interval_days = max(plot.interval_days + 1, int(round(grown * combo_bonus)))
        plot.ease_factor = min(MAX_EASE, plot.ease_factor + EASE_CORRECT_BONUS)
    else:
        plot.correct_streak = 0
        plot.interval_days = RESET_INTERVAL_DAYS
        penalty = EASE_INCORRECT_PENALTY
        if confidence == "sure":
            penalty *= CONFIDENT_WRONG_PENALTY_MULTIPLIER
        elif confidence == "unsure":
            penalty *= UNSURE_WRONG_PENALTY_MULTIPLIER
        plot.ease_factor = max(MIN_EASE, plot.ease_factor - penalty)

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
        # Flat, syllabus-ordered index of every topic, used by the question
        # generator to reach "the same or a nearby topic" for distractors (§5).
        self.topic_records = []
        self.topic_pos = {}
        # Recomputed lazily — render() asks about the lock state once per plot,
        # 722 times a repaint, so it cannot be an O(rows) walk each time.
        self._unlocked_cache = None
        self._build_farm()

    def _build_farm(self):
        for week in self.catalog["weeks"]:
            plot_ids = []
            for topic in week["topics"]:
                self.topic_pos[topic["id"]] = len(self.topic_records)
                self.topic_records.append(
                    {"sequence": week["sequence"], "topic": topic, "items": topic["items"]}
                )
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
        """L4a (2026-09-20): the §7 pacing gate this method used to enforce —
        a row opened only once every plot in the row before it had reached at
        least Sprout — has been removed outright, not just loosened. A player
        joining weeks into the real course was being locked out of syllabus
        content their classmates already covered, which defeated the whole
        point of a study tool. Every row is unlocked from the very first day
        now, unconditionally.

        The method (and the cache/invalidation machinery below it) is kept
        exactly as it was rather than deleted, on purpose: well over a dozen
        call sites across this file and minigames.py ask "is this row's
        content available" as their one real question, and every one of them
        keeps working unchanged because the answer is just always "yes" now.
        See this file's own CLAUDE.md, the L4a build note, for the full
        reasoning and for what downstream UI (the lock note, `.row--locked`/
        `.plot--locked` CSS, the disabled proficiency/bonus buttons) this
        leaves permanently dormant rather than torn out.
        """
        if self._unlocked_cache is None:
            self._unlocked_cache = self._compute_unlocked()
        return sequence in self._unlocked_cache

    def _compute_unlocked(self):
        # L4a: no gate. Every row is open from the start, regardless of any
        # other row's stage — CATCH_UP_MAX_SEQUENCE stays defined below as a
        # content-boundary fact (FREN151 ends at sequence 11), it just no
        # longer does any gating work here.
        return {row.sequence for row in self.rows}

    def invalidate_unlocks(self):
        """Anything that can change a plot's stage has to drop the cache."""
        self._unlocked_cache = None

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
    def review(self, plot_id, correct, day=None, combo=0, confidence=None):
        plot = self.plots_by_id.get(plot_id)
        if plot is None:
            return None
        self.invalidate_unlocks()
        return schedule_after_review(
            plot,
            correct,
            self.current_day if day is None else day,
            combo=combo,
            confidence=confidence,
        )

    def advance_day(self, days=1):
        self.current_day += max(0, int(days))
        return self.current_day


state = FarmState(CATALOG)


def _plot_record(plot):
    return {
        "ease_factor": plot.ease_factor,
        "interval_days": plot.interval_days,
        "last_reviewed": plot.last_reviewed,
        "next_due": plot.next_due,
        "correct_streak": plot.correct_streak,
        "stage": plot.stage,
        "in_weeds": plot.in_weeds,
        # L-18: only written while a plot is on a losing run, so a normal
        # save is unchanged.
        **({"fail_run": plot.fail_run} if plot.fail_run else {}),
        # 2026-10-08: day of the last full watering, only once there is one.
        **({"last_watered": plot.last_watered} if plot.last_watered is not None else {}),
    }


def _reset_plot(plot):
    plot.ease_factor = DEFAULT_EASE
    plot.interval_days = 0
    plot.last_reviewed = None
    plot.next_due = None
    plot.correct_streak = 0
    plot.stage = STAGE_SEED
    plot.in_weeds = False
    plot.fail_run = 0
    plot.last_watered = None
    plot.nudged_day = None
