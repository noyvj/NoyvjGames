"""Weekly proficiency tests: building a test for a week, answering it, its report buttons and the panel's drawing.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_model import state
from champ_questions import generate_question
from champ_grading import check_answer, grading_tier
from champ_labels import (
    FEEDBACK, PRONUNCIATION_REPORT_BUTTON_LABEL, PRONUNCIATION_REPORT_SENT_LABEL, REPORT_BUTTON_LABEL,
    REPORT_SENT_LABEL,
)
from champ_util import _element
from champ_stats import _topic_plots, proficiency_test_topics
from champ_points import record_practice
from champ_reportlog import _record_report_log_entry
from champ_growth import credit_review_plot, reset_growth_credit
from champ_reports import _dispatch_report, _plot_pronunciation_report_payload, _typed_wrong_report_payload
from champ_leech import _with_highlights
from champ_review import _with_growth


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


# --- Milestone 12: weekly proficiency test state (design doc §14.5) --------
#
# Purely informational, like Review — but unlike Review, it never touches SRS
# state at all (no nudge, nothing), since §14.5 explicitly frames this as
# "regardless of what's currently planted/watered", not a practice mode.

PROFICIENCY_TEST_LENGTH = 18
PROFICIENCY_RNG = random.Random()
PROFICIENCY_SUMMARY_MESSAGE = "Score: {correct}/{total}."
PROFICIENCY_TOPIC_LINE = "{title}: {correct}/{total}"


proficiency_choice_proxies = []


def _destroy_proficiency_choice_proxies():
    for proxy in proficiency_choice_proxies:
        proxy.destroy()
    proficiency_choice_proxies.clear()


def _make_proficiency_handler(sequence):
    def handler(event=None):
        start_proficiency_test(sequence)
    return handler


def is_proficiency_test_available(sequence):
    """A proficiency test is only offered for an unlocked week — §14.5 says
    nothing about bypassing §7's row-unlock gate, and letting a test preview
    a locked week's content would do exactly that even though the test
    itself doesn't gate anything (see CLAUDE.md's Milestone 12 build note)."""
    return state.is_row_unlocked(sequence)


def build_proficiency_test(sequence, rng=None, length=PROFICIENCY_TEST_LENGTH):
    """A fixed-length (~15-20 question) session covering every topic in the
    week at least once, then filling the rest of the target length by
    cycling back through the topics. If a week has more topics than the
    target length (none currently do), full topic coverage wins over the
    soft length target."""
    rng = PROFICIENCY_RNG if rng is None else rng
    topic_plots = [
        (topic, plots)
        for topic in proficiency_test_topics(sequence)
        for plots in [_topic_plots(topic)]
        if plots
    ]
    if not topic_plots:
        return []

    target_length = max(length, len(topic_plots))
    entries = [(topic, rng.choice(plots)) for topic, plots in topic_plots]
    cursor = 0
    while len(entries) < target_length:
        topic, plots = topic_plots[cursor % len(topic_plots)]
        entries.append((topic, rng.choice(plots)))
        cursor += 1

    return [
        {
            "topic_id": topic["id"],
            "topic_title": topic["title"],
            "topic_type": topic["topic_type"],
            "question": generate_question(plot, rng),
        }
        for topic, plot in entries[:target_length]
    ]


def start_proficiency_test(sequence, event=None):
    if not is_proficiency_test_available(sequence):
        return None

    runstate.proficiency_sequence = sequence
    runstate.proficiency_questions = build_proficiency_test(sequence, PROFICIENCY_RNG)
    runstate.proficiency_index = 0
    runstate.proficiency_result = None
    runstate.proficiency_score = {"correct": 0, "total": 0}
    runstate.proficiency_topic_scores = {
        topic["id"]: {"title": topic["title"], "correct": 0, "total": 0}
        for topic in proficiency_test_topics(sequence)
    }
    runstate.proficiency_mode = True
    runstate.proficiency_submitted_answer = None
    runstate.proficiency_report_sent = False
    runstate.proficiency_pronunciation_report_sent = False
    reset_growth_credit("proficiency")
    _element("proficiency-answer-input").value = ""
    render()
    return runstate.proficiency_questions


def submit_proficiency_answer(given):
    if runstate.proficiency_index >= len(runstate.proficiency_questions) or runstate.proficiency_result is not None:
        return None
    entry = runstate.proficiency_questions[runstate.proficiency_index]
    question = entry["question"]
    typed_mode = question["mode"] == "typed"
    runstate.proficiency_submitted_answer = str(given).strip() if typed_mode else given
    tier = grading_tier(question["answer"]) if typed_mode else None
    runstate.proficiency_result = check_answer(
        question, given, tier=tier, accent_sensitive=runstate.ACCENT_SENSITIVE
    )
    runstate.proficiency_score["total"] += 1
    record_practice("proficiency", runstate.proficiency_result)
    topic_score = runstate.proficiency_topic_scores[entry["topic_id"]]
    topic_score["total"] += 1
    if runstate.proficiency_result:
        runstate.proficiency_score["correct"] += 1
        topic_score["correct"] += 1
        plot = state.plots_by_id.get(question.get("plot_id"))
        if plot is not None:
            credit_review_plot(plot, "proficiency")
    render()
    return runstate.proficiency_result


def next_proficiency_question(event=None):
    if not runstate.proficiency_mode:
        return None
    runstate.proficiency_index += 1
    runstate.proficiency_result = None
    runstate.proficiency_submitted_answer = None
    runstate.proficiency_report_sent = False
    runstate.proficiency_pronunciation_report_sent = False
    _element("proficiency-answer-input").value = ""
    render()
    return runstate.proficiency_index


def close_proficiency_test(event=None):
    runstate.proficiency_mode = False
    runstate.proficiency_sequence = None
    runstate.proficiency_questions = []
    runstate.proficiency_index = 0
    runstate.proficiency_result = None
    runstate.proficiency_score = {"correct": 0, "total": 0}
    runstate.proficiency_topic_scores = {}
    runstate.proficiency_submitted_answer = None
    runstate.proficiency_report_sent = False
    runstate.proficiency_pronunciation_report_sent = False
    render()


def _current_proficiency_question():
    if runstate.proficiency_index >= len(runstate.proficiency_questions):
        return None
    return runstate.proficiency_questions[runstate.proficiency_index]["question"]


# --- Milestone 26: report buttons, extended into Proficiency ---------------
#
# Same reasoning and mechanism as Review's own copy above -- Proficiency's
# questions come from generate_question() the same way Review's do, so they
# carry the same "plot_id"/"topic_type" shape _typed_wrong_report_payload()/
# _plot_pronunciation_report_payload() already expect.


def _proficiency_report_payload():
    question = _current_proficiency_question()
    if question is None or runstate.proficiency_result is not False:
        return None
    if question["mode"] != "typed":
        return None
    return _typed_wrong_report_payload(question, runstate.proficiency_submitted_answer)


def submit_proficiency_report(event=None):
    if runstate.proficiency_report_sent:
        return None
    payload = _proficiency_report_payload()
    if payload is None:
        return None
    runstate.proficiency_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _proficiency_pronunciation_report_payload():
    return _plot_pronunciation_report_payload(_current_proficiency_question())


def submit_proficiency_pronunciation_report(event=None):
    if runstate.proficiency_pronunciation_report_sent:
        return None
    payload = _proficiency_pronunciation_report_payload()
    if payload is None:
        return None
    runstate.proficiency_pronunciation_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _make_proficiency_choice_handler(choice):
    def handler(event=None):
        submit_proficiency_answer(choice)
    return handler


def on_proficiency_submit_typed(event=None):
    submit_proficiency_answer(_element("proficiency-answer-input").value)


def on_proficiency_answer_keydown(event=None):
    if event is not None and getattr(event, "key", None) == "Enter":
        event.preventDefault()
        on_proficiency_submit_typed()


def render_proficiency():
    panel = _element("proficiency-panel")
    choices_box = _element("proficiency-choices")

    _destroy_proficiency_choice_proxies()

    if not runstate.proficiency_mode:
        panel.hidden = True
        choices_box.innerHTML = ""
        _element("proficiency-report-button").hidden = True
        _element("proficiency-pronunciation-report-button").hidden = True
        return

    panel.hidden = False
    complete = runstate.proficiency_index >= len(runstate.proficiency_questions)
    summary = _element("proficiency-summary")
    breakdown = _element("proficiency-topic-breakdown")

    if complete:
        choices_box.innerHTML = ""
        summary.hidden = False
        summary.innerText = _with_growth(_with_highlights(PROFICIENCY_SUMMARY_MESSAGE.format(**runstate.proficiency_score)), "proficiency")
        breakdown.innerHTML = ""
        for topic_score in runstate.proficiency_topic_scores.values():
            line = document.createElement("p")
            line.className = "proficiency-topic-line"
            line.innerText = PROFICIENCY_TOPIC_LINE.format(**topic_score)
            breakdown.appendChild(line)
        _element("proficiency-progress").innerText = ""
        _element("proficiency-context").innerText = ""
        _element("proficiency-instruction").innerText = ""
        _element("proficiency-prompt").innerText = ""
        _element("proficiency-note").hidden = True
        _element("proficiency-answer-input").hidden = True
        _element("proficiency-submit-button").hidden = True
        _element("proficiency-next-button").hidden = True
        _element("proficiency-feedback").innerText = ""
        _element("proficiency-report-button").hidden = True
        _element("proficiency-pronunciation-report-button").hidden = True
        return

    summary.hidden = True
    breakdown.innerHTML = ""
    entry = runstate.proficiency_questions[runstate.proficiency_index]
    question = entry["question"]

    _element("proficiency-progress").innerText = (
        f"{runstate.proficiency_index + 1} of {len(runstate.proficiency_questions)}"
    )
    _element("proficiency-context").innerText = question["context"]
    _element("proficiency-instruction").innerText = question["instruction"]
    _element("proficiency-prompt").innerText = question["prompt"]

    note = _element("proficiency-note")
    note.innerText = question["note"] or ""
    note.hidden = not question["note"]

    answered = runstate.proficiency_result is not None
    answer_input = _element("proficiency-answer-input")
    submit = _element("proficiency-submit-button")
    next_button = _element("proficiency-next-button")

    choices_box.innerHTML = ""
    if question["mode"] == "choice":
        answer_input.hidden = True
        submit.hidden = True
        for index, choice in enumerate(question["choices"]):
            button = document.createElement("button")
            button.id = f"proficiency-choice-{index}"
            button.innerText = choice
            button.disabled = answered
            button.className = "choice"
            if answered and choice == question["answer"]:
                button.className = "choice choice--answer"
            proxy = create_proxy(_make_proficiency_choice_handler(choice))
            button.addEventListener("click", proxy)
            proficiency_choice_proxies.append(proxy)
            choices_box.appendChild(button)
    else:
        answer_input.hidden = False
        submit.hidden = False
        submit.disabled = answered

    next_button.hidden = not answered

    if answered:
        template = FEEDBACK["correct" if runstate.proficiency_result else "incorrect"]
        _element("proficiency-feedback").innerText = template.format(answer=question["answer"])
    else:
        _element("proficiency-feedback").innerText = ""

    # Milestone 26: same two-button pattern as the main practice panel and
    # Review, above.
    report_button = _element("proficiency-report-button")
    show_report = answered and runstate.proficiency_result is False and question["mode"] == "typed"
    report_button.hidden = not show_report
    if show_report:
        report_button.disabled = runstate.proficiency_report_sent
        report_button.innerText = (
            REPORT_SENT_LABEL if runstate.proficiency_report_sent else REPORT_BUTTON_LABEL
        )

    pronunciation_button = _element("proficiency-pronunciation-report-button")
    pronunciation_button.hidden = False
    pronunciation_button.disabled = runstate.proficiency_pronunciation_report_sent
    pronunciation_button.innerText = (
        PRONUNCIATION_REPORT_SENT_LABEL
        if runstate.proficiency_pronunciation_report_sent
        else PRONUNCIATION_REPORT_BUTTON_LABEL
    )
