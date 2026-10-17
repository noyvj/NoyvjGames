"""The main practice panel: opening a plot, answering it, the Next plot and Next day buttons, slip forgiveness and the
panel's drawing.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_rules import DEFAULT_EASE, STAGE_RANK, STAGE_SEED
from champ_catalog import PRONUNCIATION_RISK_NOTES
from champ_model import _plot_record, state
from champ_qbuild import V_GENDER_TAG
from champ_questions import generate_question
from champ_grading import (
    ERROR_PATTERN_ACCENT, ERROR_PATTERN_CLOSE_TYPO, check_answer, classify_wrong_typed_answer, grading_tier,
    is_weed_confusion, record_error_pattern,
)
from champ_labels import (
    FEEDBACK, PRONUNCIATION_REPORT_BUTTON_LABEL, PRONUNCIATION_REPORT_SENT_LABEL, REPORT_BUTTON_LABEL,
    REPORT_SENT_LABEL, build_failure_blurb,
)
from champ_util import _element
from champ_calendar import note_study_answer
from champ_points import (
    _claim_golden, _quest_note, ensure_quests, gender_drill_accuracy_text, quest_state, record_practice,
)
from champ_watering import water_plot, water_result_text
from champ_practice_base import (
    QUESTION_RNG, _destroy_practice_choice_proxies, _track_row_session_answer, close_practice,
    confidence_stats_text, confidence_tally, practice_choice_proxies, row_session_correct,
    row_session_spoiled,
)
from champ_leech import (
    LEECH_FAIL_RUN_LIMIT, LEECH_REST_DAYS, _note_highlights, _validated_fail_run, _validated_last_watered,
    is_leech, leech_reteach_lines,
)
from champ_arrange import apply_farm_arrangement


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


def _make_choice_handler(choice):
    def handler(event=None):
        submit_answer(choice)
    return handler


# --- L-19: "that was a slip" -------------------------------------------------
# Once per session, a typed miss that is only a slip of the fingers (a missed
# accent, or one close to the answer) can be forgiven: the plot goes back to
# exactly what it was before the answer, the combo and the error digest are
# put back, and the same plot gets a fresh question. Session state only.
SLIP_PATTERNS = (ERROR_PATTERN_ACCENT, ERROR_PATTERN_CLOSE_TYPO)


def _restore_plot(plot, record):
    plot.ease_factor = record.get("ease_factor", DEFAULT_EASE)
    plot.interval_days = record.get("interval_days", 0)
    plot.last_reviewed = record.get("last_reviewed")
    plot.next_due = record.get("next_due")
    plot.correct_streak = record.get("correct_streak", 0)
    plot.stage = record.get("stage", STAGE_SEED)
    if plot.stage not in STAGE_RANK:
        plot.stage = STAGE_SEED
    plot.in_weeds = bool(record.get("in_weeds", False))
    plot.fail_run = _validated_fail_run(record.get("fail_run"))
    plot.last_watered = _validated_last_watered(record, plot)


def can_forgive_slip():
    return (
        not runstate.slip_used
        and runstate._slip_snapshot is not None
        and runstate.current_question is not None
        and runstate.current_result is False
        and runstate.current_question["mode"] == "typed"
        and runstate._slip_snapshot["plot_id"] == runstate.current_question["plot_id"]
        and runstate._slip_snapshot["pattern"] in SLIP_PATTERNS
    )


def forgive_slip(event=None):
    if not can_forgive_slip():
        return False
    snap = runstate._slip_snapshot
    plot = state.plots_by_id[snap["plot_id"]]
    _restore_plot(plot, snap["record"])
    runstate.combo_count = snap["combo"]
    pattern = snap["pattern"]
    if runstate.error_pattern_counts.get(pattern, 0) > 1:
        runstate.error_pattern_counts[pattern] -= 1
    else:
        runstate.error_pattern_counts.pop(pattern, None)
    if snap["confidence"] in confidence_tally:
        confidence_tally[snap["confidence"]][1] = max(0, confidence_tally[snap["confidence"]][1] - 1)
    sequence = plot.sequence
    if snap["spoiled"]:
        row_session_spoiled.add(sequence)
    else:
        row_session_spoiled.discard(sequence)
    if snap["row_correct"]:
        row_session_correct[sequence] = set(snap["row_correct"])
    else:
        row_session_correct.pop(sequence, None)
    quest_state["day"] = snap["quest"]["day"]
    quest_state["progress"] = dict(snap["quest"]["progress"])
    quest_state["done"] = list(snap["quest"]["done"])
    runstate.slip_used = True
    runstate._slip_snapshot = None
    open_practice(plot.plot_id)
    runstate.slip_note = "Slip forgiven: that answer was not counted. Same plot, fresh question."
    render()
    return True


def render_practice():
    panel = _element("practice-panel")
    choices_box = _element("practice-choices")
    answer_input = _element("practice-answer-input")
    submit = _element("practice-submit-button")

    # The previous batch of choice-button proxies belongs to whatever was on
    # screen before this repaint, closed panel or otherwise — destroy it here
    # so every path through this function (including the early return below)
    # retires its predecessors before anything new can replace it.
    _destroy_practice_choice_proxies()

    # L24: a static watering-can cursor over the farm while a plot is open.
    farm_el = _element("farm")
    if runstate.practice_open and runstate.current_question is not None:
        farm_el.classList.add("farm--watering")
    else:
        farm_el.classList.remove("farm--watering")

    if not runstate.practice_open or runstate.current_question is None:
        panel.hidden = True
        choices_box.innerHTML = ""
        _element("practice-report-button").hidden = True
        _element("practice-blurb").hidden = True
        _element("practice-pronunciation-note").hidden = True
        _element("practice-pronunciation-report-button").hidden = True
        _element("practice-next-button").hidden = True
        _element("practice-slip-button").hidden = True
        _element("practice-slip-note").hidden = True
        _element("practice-leech").hidden = True
        return

    panel.hidden = False
    _element("practice-context").innerText = runstate.current_question["context"]
    _element("practice-instruction").innerText = runstate.current_question["instruction"]
    _element("practice-prompt").innerText = runstate.current_question["prompt"]

    note = _element("practice-note")
    note.innerText = runstate.current_question["note"] or ""
    note.hidden = not runstate.current_question["note"]

    answered = runstate.current_result is not None

    # Optional pre-answer confidence tag. Hidden once answered -- it has
    # nothing left to weigh at that point (submit_answer() already read it).
    confidence_box = _element("practice-confidence")
    confidence_box.hidden = answered
    gender_text = gender_drill_accuracy_text() if runstate.current_question.get("variant") == V_GENDER_TAG else ""
    _element("gender-accuracy-display").innerText = gender_text
    _element("gender-accuracy-display").hidden = not gender_text
    stats_text = confidence_stats_text()
    _element("practice-confidence-stats").innerText = stats_text
    _element("practice-confidence-stats").hidden = not stats_text
    sure_button = _element("practice-confidence-sure-button")
    unsure_button = _element("practice-confidence-unsure-button")
    sure_button.className = "secondary" + (" selected" if runstate.current_confidence == "sure" else "")
    unsure_button.className = "secondary" + (" selected" if runstate.current_confidence == "unsure" else "")

    choices_box.innerHTML = ""
    if runstate.current_question["mode"] == "choice":
        answer_input.hidden = True
        submit.hidden = True
        for index, choice in enumerate(runstate.current_question["choices"]):
            button = document.createElement("button")
            button.id = f"practice-choice-{index}"
            button.innerText = choice
            button.disabled = answered
            button.className = "choice"
            if answered and choice == runstate.current_question["answer"]:
                button.className = "choice choice--answer"
            proxy = create_proxy(_make_choice_handler(choice))
            button.addEventListener("click", proxy)
            practice_choice_proxies.append(proxy)
            choices_box.appendChild(button)
    else:
        answer_input.hidden = False
        submit.hidden = False
        submit.disabled = answered

    if answered:
        template = FEEDBACK["correct" if runstate.current_result else "incorrect"]
        _element("practice-feedback").innerText = template.format(
            answer=runstate.current_question["answer"]
        )
    else:
        _element("practice-feedback").innerText = ""
    water_note = _element("practice-water-note")
    note_text = water_result_text(runstate.current_water_kind, plot_for_note=state.plots_by_id.get(runstate.current_question["plot_id"])) if (answered and runstate.current_result) else ""
    water_note.innerText = note_text
    water_note.hidden = not note_text

    # Direct user request: continuing to the next due plot used to mean
    # Close, then scroll back up to the farm-level "water next plot" button
    # -- real friction doing several plots in a row. Same visibility gating
    # as the report buttons below (answered = current_result is not None).
    _element("practice-next-button").hidden = not answered

    # §14.2.4: the report button only ever appears once a *written* answer
    # (typed, never multiple choice) has been marked wrong -- a wrong choice
    # isn't ambiguous the way a wrong typed answer can be.
    report_button = _element("practice-report-button")
    show_report = answered and runstate.current_result is False and runstate.current_question["mode"] == "typed"
    report_button.hidden = not show_report
    if show_report:
        report_button.disabled = runstate.report_sent
        report_button.innerText = REPORT_SENT_LABEL if runstate.report_sent else REPORT_BUTTON_LABEL

    # Milestone 24: independent of the above -- available for the whole
    # time a question is open, not gated by right/wrong or typed/choice,
    # since a pronunciation concern is about the catalog text itself, not
    # about how this attempt went. The note only shows for the handful of
    # items the TTS watchlist actually flags by name (see
    # PRONUNCIATION_RISK_NOTES); the report button is always available.
    pronunciation_note = _element("practice-pronunciation-note")
    pronunciation_button = _element("practice-pronunciation-report-button")
    plot = state.plots_by_id.get(runstate.current_question["plot_id"])
    risk_note = PRONUNCIATION_RISK_NOTES.get(plot.items[0]["fr"]) if plot else None
    pronunciation_note.hidden = risk_note is None
    if risk_note is not None:
        pronunciation_note.innerText = f"⚠ Known pronunciation risk: {risk_note}"
    pronunciation_button.hidden = False
    pronunciation_button.disabled = runstate.pronunciation_report_sent
    pronunciation_button.innerText = (
        PRONUNCIATION_REPORT_SENT_LABEL
        if runstate.pronunciation_report_sent
        else PRONUNCIATION_REPORT_BUTTON_LABEL
    )

    # §14.3: the failure blurb shows on *any* wrong answer, choice or typed
    # (unlike the report button above, which is written-answer-only).
    blurb_panel = _element("practice-blurb")
    show_blurb = answered and runstate.current_result is False
    blurb = build_failure_blurb(runstate.current_question) if show_blurb else None
    blurb_panel.hidden = blurb is None
    if blurb is not None:
        _element("practice-blurb-what").innerText = blurb["what_it_is"]
        _element("practice-blurb-tip").innerText = blurb["memory_tip"]
        _element("practice-blurb-why").innerText = blurb["why_it_matters"]

    # L-19: the once-a-session "that was a slip" button, and its confirmation.
    _element("practice-slip-button").hidden = not can_forgive_slip()
    slip_note_line = _element("practice-slip-note")
    slip_note_line.innerText = runstate.slip_note
    slip_note_line.hidden = not runstate.slip_note

    # L-18: a stubborn weed shows its re-teach card until it is answered.
    leech_box = _element("practice-leech")
    show_leech = (not answered) and plot is not None and is_leech(plot)
    leech_box.hidden = not show_leech
    if show_leech:
        what_line, pieces_line, hook_line = leech_reteach_lines(plot)
        _element("practice-leech-what").innerText = what_line
        _element("practice-leech-pieces").innerText = pieces_line
        _element("practice-leech-hook").innerText = hook_line
        _element("practice-leech-rest-button").innerText = f"Rest this plot for {LEECH_REST_DAYS} days"


# --- interactions ----------------------------------------------------------


def open_practice(plot_id, variant=None):
    """Water a plot: roll a fresh question for it (§5) and show the panel."""

    plot = state.plots_by_id.get(plot_id)
    if plot is None or not state.is_row_unlocked(plot.sequence):
        return None
    runstate.slip_note = ""

    runstate.current_question = generate_question(
        plot, QUESTION_RNG, variant=variant, exclude=getattr(plot, "last_variant", None)
    )
    plot.last_variant = runstate.current_question["variant"]
    runstate.current_result = None
    runstate.current_submitted_answer = None
    runstate.current_confidence = None
    runstate.current_water_kind = None
    runstate.report_sent = False
    runstate.pronunciation_report_sent = False
    runstate.practice_open = True
    runstate.deepdive_open = False
    _element("practice-answer-input").value = ""
    render()
    return runstate.current_question


def set_confidence(value):
    """Optional pre-answer confidence tag ("sure"/"unsure"), toggleable --
    clicking the already-selected one clears it back to unset rather than
    forcing a choice. Never blocks answering either way."""
    if runstate.current_question is None or runstate.current_result is not None:
        return runstate.current_confidence
    runstate.current_confidence = None if runstate.current_confidence == value else value
    render()
    return runstate.current_confidence


def submit_answer(given):
    if runstate.current_question is None or runstate.current_result is not None:
        return None
    typed_mode = runstate.current_question["mode"] == "typed"
    runstate.current_submitted_answer = str(given).strip() if typed_mode else given
    # §14.2: the tier is decided from the answer's own shape, only for typed
    # answers -- multiple choice is always an exact match regardless.
    tier = grading_tier(runstate.current_question["answer"]) if typed_mode else None
    plot = state.plots_by_id.get(runstate.current_question["plot_id"])
    ensure_quests()
    # L-19: what to put back if the player forgives this answer as a slip.
    runstate.slip_note = ""
    runstate._slip_snapshot = None
    if plot is not None:
        runstate._slip_snapshot = {
            "plot_id": plot.plot_id,
            "record": _plot_record(plot),
            "combo": runstate.combo_count,
            "confidence": runstate.current_confidence,
            "pattern": None,
            "spoiled": plot.sequence in row_session_spoiled,
            "row_correct": set(row_session_correct.get(plot.sequence, ())),
            "quest": {
                "day": quest_state["day"],
                "progress": dict(quest_state["progress"]),
                "done": list(quest_state["done"]),
            },
        }
    prior_fail_run = plot.fail_run if plot is not None else 0
    runstate.current_result = check_answer(
        runstate.current_question, given, tier=tier, accent_sensitive=runstate.ACCENT_SENSITIVE
    )
    runstate.combo_count = runstate.combo_count + 1 if runstate.current_result else 0
    if runstate.current_confidence in confidence_tally:
        confidence_tally[runstate.current_confidence][1] += 1
        confidence_tally[runstate.current_confidence][0] += 1 if runstate.current_result else 0
    if runstate.current_question.get("variant") == V_GENDER_TAG:
        record_practice("gender", runstate.current_result)  # also counts the study day
    else:
        note_study_answer()
    _quest_note("water")
    if plot is not None and plot.topic_type == "grammar":
        _quest_note("grammar")
    _quest_note("combo", runstate.combo_count, absolute=True)
    if plot is not None:
        if runstate.current_result:
            plot.in_weeds = False
            plot.fail_run = 0
        else:
            plot.fail_run = min(plot.fail_run + 1, LEECH_FAIL_RUN_LIMIT)
            if typed_mode and is_weed_confusion(runstate.current_question["answer"], given):
                plot.in_weeds = True
        _track_row_session_answer(plot, runstate.current_result)
        _claim_golden(plot.plot_id, runstate.current_result)
        _note_highlights(plot, runstate.current_result, prior_fail_run)
    if not runstate.current_result and typed_mode:
        pattern = classify_wrong_typed_answer(runstate.current_question, given, tier)
        record_error_pattern(pattern)
        if runstate._slip_snapshot is not None:
            runstate._slip_snapshot["pattern"] = pattern
    if runstate.current_result:
        # Watering rule: the first correct answer for a plot each day is a
        # full watering, a later one the same day only a nudge.
        runstate.current_water_kind = water_plot(plot, combo=runstate.combo_count, confidence=runstate.current_confidence)
    else:
        runstate.current_water_kind = None
        state.review(
            runstate.current_question["plot_id"],
            runstate.current_result,
            combo=runstate.combo_count,
            confidence=runstate.current_confidence,
        )
    render()
    return runstate.current_result


def on_submit_typed(event=None):
    submit_answer(_element("practice-answer-input").value)


def on_answer_keydown(event=None):
    if event is not None and getattr(event, "key", None) == "Enter":
        event.preventDefault()
        on_submit_typed()


def on_water_next(event=None):
    plot = state.next_due_plot()
    if plot is not None:
        open_practice(plot.plot_id)


def on_next_practice_plot(event=None):
    """The practice panel's own "Next plot" button, added on direct user
    request so watering several plots in a row doesn't mean Close, then
    scroll back up to the farm-level "water next plot" button each time.
    Reuses on_water_next()'s exact plot-selection logic (state.next_due_plot())
    rather than re-deriving it -- the only new behaviour is the fallback:
    on_water_next() simply does nothing when there's no next plot, which
    would leave this button visible over a stale answered question with a
    click that does nothing, so this closes the panel instead."""
    plot = state.next_due_plot()
    if plot is None:
        close_practice()
        return
    open_practice(plot.plot_id)


def on_next_day(event=None):
    state.advance_day()
    apply_farm_arrangement()
    render()
