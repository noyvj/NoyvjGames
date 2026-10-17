"""The placement test: a mixed test over the whole syllabus that suggests where to start, plus applying its plan.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_rules import STAGE_SEED, STAGE_SPROUT
from champ_model import state
from champ_questions import generate_question
from champ_grading import check_answer, grading_tier
from champ_util import _element
from champ_stats import _topic_plots, proficiency_test_topics
from champ_points import record_practice


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


# ===========================================================================
# L4b -- placement test. An opt-in, mixed test that samples every stretch of
# the syllabus in increasing difficulty (reusing generate_question() and
# check_answer(), and the proficiency test's topic/plot helpers) and, if the
# player confirms, fast-forwards the plots they demonstrably know to a modest
# starting stage. The rules that keep it safe:
#   * ONLY RAISES. A plot is touched only if it is still completely untouched
#     (a Seed never watered): anything already watered, wilting, in the weeds
#     or further along is left exactly as it is, so a placement can never lower
#     progress and can never be "undone" into a worse state.
#   * MODEST. Known plots become Sprouts (one correct answer's worth), never
#     higher, with a real due date 1..PLACEMENT_SPREAD_DAYS days out (spread
#     across the plots so they do not all fall due on one day), so ordinary
#     reviews still confirm the knowledge.
#   * CONFIRMED FIRST. The result screen states exactly what would change
#     ("You will start at week N; X plots move to Sprout") with Apply/Cancel;
#     nothing is written until Apply.
#   * CONSERVATIVE. The rows are cut into PLACEMENT_BAND_COUNT bands of
#     consecutive weeks; a band is passed with PLACEMENT_PASS_CORRECT right of
#     its PLACEMENT_QUESTIONS_PER_BAND questions (one question per row, cycling
#     back for a short band). The test stops the moment a band is failed (or
#     can no longer be passed), and only the leading passed bands are placed.
# A row's lock state is respected (only unlocked rows are probed or placed; the
# pacing gate itself was removed in L4a so today that is every row). The
# highest row ever placed through is saved as `placement_through` (only once
# non-zero). Every answer feeds the practice ledger as "placement".
# ===========================================================================
PLACEMENT_BAND_COUNT = 6
PLACEMENT_QUESTIONS_PER_BAND = 4
PLACEMENT_PASS_CORRECT = 3
PLACEMENT_START_STAGE = STAGE_SPROUT
PLACEMENT_SPREAD_DAYS = 6  # first due dates land 1..6 days out (< BLOOMING_INTERVAL_DAYS)
PLACEMENT_RNG = random.Random()
PLACEMENT_INTRO = (
    "Already know some French? This test samples every stretch of the course, easiest first, "
    "and stops when a stretch gets hard. You can then skip the weeks you know: those plots start "
    "as Sprouts and still come up for review, so nothing is taken on trust. It never lowers or "
    "locks anything you have already grown."
)
PLACEMENT_HINT = (
    "Coming back to this, or already know some French? Try the placement test to skip the weeks you know."
)
PLACEMENT_EMPTY_MESSAGE = "No weeks are unlocked, so there is nothing to place you in yet."
PLACEMENT_CORRECT = "Correct."
PLACEMENT_INCORRECT = "Not quite. The answer is: {answer}"
PLACEMENT_SUMMARY = "Placement test finished: {correct}/{total} right."
PLACEMENT_BAND_LINE = "Weeks {first}-{last}: {correct}/{total} ({outcome})"
PLACEMENT_NONE_MESSAGE = (
    "No placement: the first stretch was not solid yet, so you start at week {start}. "
    "Nothing has been changed."
)
PLACEMENT_NOTHING_MESSAGE = (
    "You will start at week {start}; none of those plots are untouched, so nothing needs to change."
)
PLACEMENT_PLAN_MESSAGE = (
    "You will start at week {start}; {count} plot{s} move{v} to {stage}. "
    "Plots you have already watered are left alone, and nothing is ever lowered."
)
PLACEMENT_PAST_END_MESSAGE = (
    "You will be placed past the last week; {count} plot{s} move{v} to {stage}. "
    "Plots you have already watered are left alone, and nothing is ever lowered."
)
PLACEMENT_APPLIED_MESSAGE = "Placement applied: {count} plot{s} now start as {stage} and will come up for review soon."
PLACEMENT_RECORD_MESSAGE = "You have already been placed through week {through}. A new test can only move you further."


placement_proxies = []


def _destroy_placement_proxies():
    for proxy in placement_proxies:
        proxy.destroy()
    placement_proxies.clear()


def placement_bands():
    """The unlocked rows' sequence numbers, in order, cut into at most
    PLACEMENT_BAND_COUNT near-equal groups of consecutive weeks (the first
    groups take the extra rows). 23 rows give bands of 4, 4, 4, 4, 4, 3."""
    sequences = sorted(row.sequence for row in state.rows if state.is_row_unlocked(row.sequence))
    if not sequences:
        return []
    count = min(PLACEMENT_BAND_COUNT, len(sequences))
    base, extra = divmod(len(sequences), count)
    bands = []
    cursor = 0
    for index in range(count):
        size = base + (1 if index < extra else 0)
        bands.append(sequences[cursor:cursor + size])
        cursor += size
    return bands


def _placement_pick(sequence, rng, used):
    """One (topic, plot) for a row: a random topic (so the row's grammar is not
    drowned by its many vocab plots), then a random plot in it, avoiding a plot
    already used in the same band when the row offers another."""
    options = [
        (topic, plot)
        for topic in proficiency_test_topics(sequence)
        for plot in _topic_plots(topic)
    ]
    if not options:
        return None
    fresh = [pair for pair in options if pair[1].plot_id not in used]
    topics = {pair[0]["id"]: pair[0] for pair in (fresh or options)}
    topic = topics[rng.choice(sorted(topics))]
    plots = [pair[1] for pair in (fresh or options) if pair[0]["id"] == topic["id"]]
    return topic, rng.choice(plots)


def build_placement_test(rng=None, bands=None):
    """The whole ladder up front: for each band, PLACEMENT_QUESTIONS_PER_BAND
    questions, one per row (cycling back for a short band). The session may
    end before the last band (see `_placement_band_outcome`)."""
    rng = PLACEMENT_RNG if rng is None else rng
    bands = placement_bands() if bands is None else bands
    queue = []
    for band_index, sequences in enumerate(bands):
        used = set()
        for slot in range(PLACEMENT_QUESTIONS_PER_BAND):
            picked = _placement_pick(sequences[slot % len(sequences)], rng, used)
            if picked is None:
                continue
            topic, plot = picked
            used.add(plot.plot_id)
            queue.append(
                {
                    "band": band_index,
                    "sequence": plot.sequence,
                    "topic_id": topic["id"],
                    "topic_title": topic["title"],
                    "question": generate_question(plot, rng),
                }
            )
    return queue


def _placement_band_outcome(band):
    """'pass', 'fail' (can no longer pass) or 'open' (still undecided)."""
    total = sum(1 for entry in runstate.placement_queue if entry["band"] == band)
    scored = runstate.placement_band_scores.get(band, {"correct": 0, "total": 0})
    needed = min(PLACEMENT_PASS_CORRECT, total)
    if scored["correct"] >= needed:
        return "pass"
    if scored["correct"] + (total - scored["total"]) < needed:
        return "fail"
    return "open"


def placement_passed_band_count():
    """Leading bands passed. The test stops at the first failed band, and every
    band before it has been asked in full, so this counts 'pass' bands until the
    first one that is not."""
    passed = 0
    for band in range(len(runstate.placement_bands_list)):
        if _placement_band_outcome(band) != "pass":
            break
        passed += 1
    return passed


def placement_through_from_results():
    """The last row of the last passed leading band (0 if the first band was
    not passed)."""
    passed = placement_passed_band_count()
    return runstate.placement_bands_list[passed - 1][-1] if passed else 0


def build_placement_plan(through):
    """What placing the player through row `through` WOULD do -- pure, it
    mutates nothing. Only plots that are still completely untouched (a Seed
    never watered, no streak, not in the weeds) in an unlocked row up to
    `through` are eligible; each gets a staggered first due offset."""
    eligible = [
        plot
        for row in state.rows
        if row.sequence <= through and state.is_row_unlocked(row.sequence)
        for plot in state.row_plots(row.sequence)
        if plot.stage == STAGE_SEED
        and plot.last_reviewed is None
        and plot.correct_streak == 0
        and not plot.in_weeds
    ]
    last_sequence = max((row.sequence for row in state.rows), default=0)
    return {
        "through": through,
        "start_sequence": through + 1 if through < last_sequence else None,
        "stage": PLACEMENT_START_STAGE,
        "plots": [
            (plot.plot_id, 1 + index % PLACEMENT_SPREAD_DAYS) for index, plot in enumerate(eligible)
        ],
    }


def placement_plan_text(plan):
    count = len(plan["plots"])
    stage = str(plan["stage"]).capitalize()
    if plan["through"] <= 0:
        return PLACEMENT_NONE_MESSAGE.format(start=1)
    if plan["start_sequence"] is None:
        return PLACEMENT_PAST_END_MESSAGE.format(
            count=count, s="" if count == 1 else "s", v="s" if count == 1 else "", stage=stage
        )
    if count == 0:
        return PLACEMENT_NOTHING_MESSAGE.format(start=plan["start_sequence"])
    return PLACEMENT_PLAN_MESSAGE.format(
        start=plan["start_sequence"], count=count, s="" if count == 1 else "s",
        v="s" if count == 1 else "", stage=stage,
    )


def apply_placement(plan=None):
    """Write a confirmed plan. Re-checks each plot is still untouched (so it
    can only ever raise), records the highest row placed through, and returns
    how many plots moved."""
    plan = runstate.placement_plan_data if plan is None else plan
    if plan is None:
        return 0
    moved = 0
    for plot_id, offset in plan["plots"]:
        plot = state.plots_by_id.get(plot_id)
        if (
            plot is None
            or plot.stage != STAGE_SEED
            or plot.last_reviewed is not None
            or plot.correct_streak != 0
            or plot.in_weeds
        ):
            continue
        plot.correct_streak = 1
        plot.interval_days = offset
        plot.last_reviewed = state.current_day
        plot.next_due = state.current_day + offset
        plot.stage = plan["stage"]
        moved += 1
    runstate.placement_through = max(runstate.placement_through, min(plan["through"], len(state.rows)))
    runstate.placement_applied = True
    state.invalidate_unlocks()
    render()
    return moved


def start_placement(event=None):
    runstate.placement_active = True
    runstate.placement_phase = "intro"
    runstate.placement_queue = []
    runstate.placement_bands_list = placement_bands()
    runstate.placement_index = 0
    runstate.placement_result = None
    runstate.placement_submitted_answer = None
    runstate.placement_band_scores = {}
    runstate.placement_plan_data = None
    runstate.placement_applied = False
    render()


def begin_placement_test(event=None):
    if not runstate.placement_active:
        return []
    runstate.placement_bands_list = placement_bands()
    runstate.placement_queue = build_placement_test(bands=runstate.placement_bands_list)
    runstate.placement_index = 0
    runstate.placement_result = None
    runstate.placement_submitted_answer = None
    runstate.placement_band_scores = {}
    runstate.placement_plan_data = None
    runstate.placement_applied = False
    runstate.placement_phase = "testing" if runstate.placement_queue else "intro"
    _element("placement-answer-input").value = ""
    render()
    return runstate.placement_queue


def _finish_placement():
    runstate.placement_phase = "summary"
    runstate.placement_plan_data = build_placement_plan(placement_through_from_results())


def submit_placement_answer(given):
    if (
        not runstate.placement_active
        or runstate.placement_phase != "testing"
        or runstate.placement_index >= len(runstate.placement_queue)
        or runstate.placement_result is not None
    ):
        return None
    entry = runstate.placement_queue[runstate.placement_index]
    question = entry["question"]
    typed_mode = question["mode"] == "typed"
    runstate.placement_submitted_answer = str(given).strip() if typed_mode else given
    tier = grading_tier(question["answer"]) if typed_mode else None
    runstate.placement_result = check_answer(question, given, tier=tier, accent_sensitive=runstate.ACCENT_SENSITIVE)
    score = runstate.placement_band_scores.setdefault(entry["band"], {"correct": 0, "total": 0})
    score["total"] += 1
    if runstate.placement_result:
        score["correct"] += 1
    record_practice("placement", runstate.placement_result)
    render()
    return runstate.placement_result


def next_placement_question(event=None):
    if not runstate.placement_active or runstate.placement_phase != "testing" or runstate.placement_result is None:
        return None
    band = runstate.placement_queue[runstate.placement_index]["band"]
    runstate.placement_index += 1
    runstate.placement_result = None
    runstate.placement_submitted_answer = None
    _element("placement-answer-input").value = ""
    if _placement_band_outcome(band) == "fail" or runstate.placement_index >= len(runstate.placement_queue):
        _finish_placement()
    render()
    return runstate.placement_phase


def on_apply_placement(event=None):
    if runstate.placement_phase != "summary" or runstate.placement_plan_data is None or runstate.placement_applied:
        return 0
    return apply_placement()


def close_placement(event=None):
    """Close (or Cancel) the panel. Nothing is written by closing."""
    runstate.placement_active = False
    runstate.placement_phase = "intro"
    runstate.placement_queue = []
    runstate.placement_bands_list = []
    runstate.placement_index = 0
    runstate.placement_result = None
    runstate.placement_submitted_answer = None
    runstate.placement_band_scores = {}
    runstate.placement_plan_data = None
    runstate.placement_applied = False
    render()


def _validated_placement_through(raw):
    if isinstance(raw, bool) or not isinstance(raw, int):
        return 0
    return max(0, min(len(state.rows), raw))


def _make_placement_choice_handler(choice):
    def handler(event=None):
        submit_placement_answer(choice)
    return handler


def on_placement_submit_typed(event=None):
    submit_placement_answer(_element("placement-answer-input").value)


def on_placement_answer_keydown(event=None):
    if event is not None and getattr(event, "key", None) == "Enter":
        on_placement_submit_typed()


def _farm_untouched():
    return all(plot.last_reviewed is None and plot.stage == STAGE_SEED for plot in state.plots)


def render_placement():
    hint = _element("placement-hint")
    hint.hidden = not (runstate.placement_through == 0 and _farm_untouched() and not runstate.placement_active)
    hint.innerText = PLACEMENT_HINT if not hint.hidden else ""
    panel = _element("placement-panel")
    choices_box = _element("placement-choices")
    _destroy_placement_proxies()
    choices_box.innerHTML = ""
    if not runstate.placement_active:
        panel.hidden = True
        return
    panel.hidden = False
    intro = _element("placement-intro")
    start = _element("placement-start-button")
    card = _element("placement-card")
    summary = _element("placement-summary")
    intro_shown = runstate.placement_phase == "intro"
    intro.hidden = not intro_shown
    intro.innerText = (
        (PLACEMENT_INTRO if runstate.placement_bands_list else PLACEMENT_EMPTY_MESSAGE)
        + (" " + PLACEMENT_RECORD_MESSAGE.format(through=runstate.placement_through) if runstate.placement_through else "")
    ) if intro_shown else ""
    start.hidden = not (intro_shown and runstate.placement_bands_list)
    card.hidden = runstate.placement_phase != "testing"
    summary.hidden = runstate.placement_phase != "summary"
    for element_id in ("placement-bands", "placement-plan", "placement-status"):
        _element(element_id).hidden = runstate.placement_phase != "summary"
    for element_id in ("placement-apply-button", "placement-cancel-button", "placement-retry-button"):
        _element(element_id).hidden = runstate.placement_phase != "summary"
    _element("placement-progress").innerText = ""

    if runstate.placement_phase == "summary":
        correct = sum(score["correct"] for score in runstate.placement_band_scores.values())
        total = sum(score["total"] for score in runstate.placement_band_scores.values())
        summary.innerText = PLACEMENT_SUMMARY.format(correct=correct, total=total)
        bands = _element("placement-bands")
        bands.innerHTML = ""
        for band, score in sorted(runstate.placement_band_scores.items()):
            line = document.createElement("p")
            line.className = "proficiency-topic-line"
            outcome = _placement_band_outcome(band)
            line.innerText = PLACEMENT_BAND_LINE.format(
                first=runstate.placement_bands_list[band][0],
                last=runstate.placement_bands_list[band][-1],
                correct=score["correct"],
                total=score["total"],
                outcome="passed" if outcome == "pass" else "not yet",
            )
            bands.appendChild(line)
        plan = runstate.placement_plan_data
        _element("placement-plan").innerText = placement_plan_text(plan)
        can_apply = (
            not runstate.placement_applied
            and plan["through"] > 0
            and (bool(plan["plots"]) or plan["through"] > runstate.placement_through)
        )
        _element("placement-apply-button").disabled = not can_apply
        _element("placement-apply-button").hidden = runstate.placement_applied or plan["through"] <= 0
        _element("placement-cancel-button").innerText = "Close" if runstate.placement_applied else "Cancel"
        status = _element("placement-status")
        status.innerText = (
            PLACEMENT_APPLIED_MESSAGE.format(
                count=len(plan["plots"]),
                s="" if len(plan["plots"]) == 1 else "s",
                stage=str(plan["stage"]).capitalize(),
            )
            if runstate.placement_applied
            else ""
        )
        _element("placement-retry-button").hidden = runstate.placement_applied
        return
    if runstate.placement_phase != "testing":
        return

    entry = runstate.placement_queue[runstate.placement_index]
    question = entry["question"]
    _element("placement-progress").innerText = f"{runstate.placement_index + 1} of up to {len(runstate.placement_queue)}"
    _element("placement-context").innerText = question["context"]
    _element("placement-instruction").innerText = question["instruction"]
    _element("placement-prompt").innerText = question["prompt"]
    note = _element("placement-note")
    note.innerText = question["note"] or ""
    note.hidden = not question["note"]
    answered = runstate.placement_result is not None
    answer_input = _element("placement-answer-input")
    submit = _element("placement-submit-button")
    if question["mode"] == "choice":
        answer_input.hidden = True
        submit.hidden = True
        for index, choice in enumerate(question["choices"]):
            button = document.createElement("button")
            button.id = f"placement-choice-{index}"
            button.innerText = choice
            button.disabled = answered
            button.className = "choice choice--answer" if answered and choice == question["answer"] else "choice"
            proxy = create_proxy(_make_placement_choice_handler(choice))
            button.addEventListener("click", proxy)
            placement_proxies.append(proxy)
            choices_box.appendChild(button)
    else:
        answer_input.hidden = False
        submit.hidden = False
        submit.disabled = answered
    _element("placement-next-button").hidden = not answered
    feedback = _element("placement-feedback")
    if not answered:
        feedback.innerText = ""
    else:
        feedback.innerText = (
            PLACEMENT_CORRECT if runstate.placement_result else PLACEMENT_INCORRECT.format(answer=question["answer"])
        )
