"""The Review tab: running a review session (start, answer, next, close), its report buttons, the shareable result and the
Review panel's drawing.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import json

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_rules import STAGE_RANK, STAGE_SEED
from champ_model import state
from champ_qbuild import V_GENDER_TAG, variants_for
from champ_questions import TYPED_BLANK_VARIANTS, TYPED_VARIANTS, generate_question
from champ_grading import check_answer, grading_tier
from champ_labels import (
    FEEDBACK, PRONUNCIATION_REPORT_BUTTON_LABEL, PRONUNCIATION_REPORT_SENT_LABEL, REPORT_BUTTON_LABEL,
    REPORT_SENT_LABEL,
)
from champ_util import _element, speak_french, speech_available
from champ_stats import automated_plot_count
from champ_calendar import note_study_answer
from champ_points import _quest_note, practice_score, record_practice
from champ_reportlog import _record_report_log_entry
from champ_watering import water_result_text
from champ_growth import credit_review_plot, growth_credit_text, reset_growth_credit
from champ_practice_base import QUESTION_RNG
from champ_reports import (
    _dispatch_report, _notify_visual_style_context, _plot_pronunciation_report_payload,
    _typed_wrong_report_payload,
)
from champ_leech import _with_highlights
from champ_water_pool import (
    LISTEN_HIDDEN_PROMPT, WATER_EMPTY_MESSAGE, WATER_LISTEN_MODE, WATER_LISTEN_VARIANTS, WATER_MODES,
    WATER_MODE_FORMAT, WATER_TYPED_MODE, water_session_plots,
)
from champ_review_base import (
    CRAM_MODE, DEFAULT_REVIEW_COUNT, GRAMMAR_REVIEW_PREFERRED_VARIANTS, MARATHON_EMPTY_MESSAGE, MARATHON_MODE,
    MAX_REVIEW_COUNT, MIN_REVIEW_COUNT, PHRASEBOOK_EMPTY_MESSAGE, PHRASEBOOK_MODE, PHRASEBOOK_SESSION_MAX,
    QUICK_WATER_EMPTY_MESSAGE, QUICK_WATER_MODE, REVIEW_EMPTY_MESSAGE, REVIEW_RNG, REVIEW_SUMMARY_MESSAGE,
    WEAK_SPOT_EMPTY_MESSAGE, WEAK_SPOT_MODE, _destroy_review_choice_proxies, _interleave_by_stage,
    cram_candidates, marathon_candidates, review_candidates, review_choice_proxies, weak_spot_candidates,
)


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


def on_start_weak_spot_review(event=None):
    start_review(WEAK_SPOT_MODE)


def on_start_cram_review(event=None):
    start_review(CRAM_MODE)


def _with_growth(message, surface):
    return f"{message} {growth_credit_text(surface)}"


def _review_count_setting():
    raw = _element("review-count-input").value
    try:
        count = int(str(raw).strip())
    except (TypeError, ValueError):
        count = DEFAULT_REVIEW_COUNT
    return max(MIN_REVIEW_COUNT, min(MAX_REVIEW_COUNT, count))


def _review_min_stage_setting():
    raw = _element("review-min-stage-select").value
    return raw if raw in STAGE_RANK else STAGE_SEED


def _review_variant_for(plot, mode):
    """Grammar Review's bias (§14.4: "biased toward fill-in-the-blank/
    conjugation prompts"): if the plot can produce one of those variants,
    roll among just those; otherwise (word review, or a grammar plot that
    can't offer one) let generate_question() pick from its full pool."""
    if mode == WATER_LISTEN_MODE:
        heard = [v for v in variants_for(plot) if v in WATER_LISTEN_VARIANTS]
        return QUESTION_RNG.choice(heard) if heard else None
    if mode == WATER_TYPED_MODE:
        typed = [v for v in variants_for(plot) if v in TYPED_VARIANTS or v in TYPED_BLANK_VARIANTS]
        return QUESTION_RNG.choice(typed) if typed else None
    if mode != "grammar" and not (
        mode in (MARATHON_MODE, PHRASEBOOK_MODE, CRAM_MODE, WEAK_SPOT_MODE, QUICK_WATER_MODE)
        and plot.topic_type == "grammar"
    ):
        return None
    preferred = [v for v in variants_for(plot) if v in GRAMMAR_REVIEW_PREFERRED_VARIANTS]
    return QUESTION_RNG.choice(preferred) if preferred else None


def _advance_review_question():
    # Both report flags and the submitted-answer text are per-question, so
    # every path onto a new question (a fresh session via start_review(), or
    # next_review_question() mid-session) resets them here in one place.
    runstate.review_submitted_answer = None
    runstate.review_report_sent = False
    runstate.review_pronunciation_report_sent = False

    if runstate.review_index >= len(runstate.review_queue):
        runstate.review_question = None
        runstate.review_result = None
        return
    plot = state.plots_by_id[runstate.review_queue[runstate.review_index]]
    runstate.review_question = generate_question(
        plot,
        QUESTION_RNG,
        variant=_review_variant_for(plot, runstate.review_mode),
        format=WATER_MODE_FORMAT.get(runstate.review_mode),
    )
    runstate.review_result = None
    runstate.review_water_kind = None
    if runstate.review_mode == WATER_LISTEN_MODE:
        runstate.review_listen_revealed = False
        speak_french(runstate.review_question["prompt"])


def start_review(mode, event=None):
    """Roll a fresh Review session: mode is "word" (vocab/phrase) or
    "grammar", the count and minimum-stage filter come from the session's
    own in-page controls (§14.4: both configurable, not fixed)."""

    if mode == WEAK_SPOT_MODE:
        runstate.review_mode = mode
        queue = [p.plot_id for p in weak_spot_candidates()]
        REVIEW_RNG.shuffle(queue)
        runstate.review_queue = queue
    elif mode == CRAM_MODE:
        runstate.review_mode = mode
        runstate.review_queue = [
            p.plot_id
            for p in cram_candidates(
                _element("review-cram-from-select").value, _element("review-cram-to-select").value
            )
        ]
    elif mode == PHRASEBOOK_MODE:
        # L19: just the saved items, shuffled, whatever their stage or row.
        runstate.review_mode = mode
        queue = list(runstate.phrasebook)
        REVIEW_RNG.shuffle(queue)
        runstate.review_queue = queue[:PHRASEBOOK_SESSION_MAX]
    elif mode == QUICK_WATER_MODE:
        # L29: just the one most overdue plot (marathon_candidates() is already
        # ordered most overdue first, watered plots before never-watered ones).
        runstate.review_mode = mode
        runstate.review_queue = [p.plot_id for p in marathon_candidates()[:1]]
    elif mode in WATER_MODES:
        # The water chooser's sessions: only plots that can still be watered
        # today, picked by water_session_plots() for the chosen option.
        runstate.review_mode = mode
        runstate.review_queue = [p.plot_id for p in water_session_plots(mode, runstate.water_mode_arg)]
    elif mode == MARATHON_MODE:
        # Ignores the count and minimum-stage controls on purpose: the point
        # is "everything that's due", ordered by how overdue it is.
        runstate.review_mode = mode
        runstate.review_queue = [p.plot_id for p in marathon_candidates()]
    else:
        topic_types = {"vocab", "phrase"} if mode == "word" else {"grammar"}
        candidates = review_candidates(topic_types, _review_min_stage_setting())
        candidates = _interleave_by_stage(candidates, REVIEW_RNG)

        runstate.review_mode = mode
        runstate.review_queue = [p.plot_id for p in candidates[: _review_count_setting()]]
    runstate.review_index = 0
    runstate.review_score = {"correct": 0, "total": 0}
    reset_growth_credit("review")
    _advance_review_question()
    _element("review-answer-input").value = ""
    render()


def submit_review_answer(given):
    if runstate.review_question is None or runstate.review_result is not None:
        return None
    typed_mode = runstate.review_question["mode"] == "typed"
    runstate.review_submitted_answer = str(given).strip() if typed_mode else given
    tier = grading_tier(runstate.review_question["answer"]) if typed_mode else None
    runstate.review_result = check_answer(
        runstate.review_question, given, tier=tier, accent_sensitive=runstate.ACCENT_SENSITIVE
    )
    runstate.review_score["total"] += 1
    _quest_note("review")
    if runstate.review_question.get("variant") == V_GENDER_TAG:
        record_practice("gender", runstate.review_result)  # also counts the study day
    elif runstate.review_mode == QUICK_WATER_MODE:
        record_practice("quick", runstate.review_result)  # L29; also counts the study day
    elif runstate.review_mode in WATER_MODES:
        record_practice("wateropts", runstate.review_result)  # also counts the study day
    else:
        note_study_answer()
    runstate.review_water_kind = None
    if runstate.review_result:
        runstate.review_score["correct"] += 1
        plot = state.plots_by_id.get(runstate.review_question["plot_id"])
        if plot is not None:
            runstate.review_water_kind = credit_review_plot(plot, "review")
    render()
    return runstate.review_result


def next_review_question(event=None):
    if runstate.review_mode is None:
        return None
    runstate.review_index += 1
    _advance_review_question()
    _element("review-answer-input").value = ""
    render()
    return runstate.review_question


def close_review(event=None):
    runstate.review_mode = None
    runstate.review_queue = []
    runstate.review_index = 0
    runstate.review_question = None
    runstate.review_result = None
    runstate.review_score = {"correct": 0, "total": 0}
    runstate.review_submitted_answer = None
    runstate.review_report_sent = False
    runstate.review_pronunciation_report_sent = False
    render()


# --- Milestone 26: report buttons, extended into Review --------------------
#
# Same two mechanisms as the main practice panel (Milestone 9's correctness
# report, Milestone 24's pronunciation-concern report), reusing the exact
# same backend contract and `_dispatch_report()` sender — just reading from
# Review's own `review_question`/`review_result`/`review_submitted_answer`
# instead of the main panel's `current_*` globals. See CLAUDE.md's
# Milestone 26 build note for why this was originally scoped out (Milestone
# 11) and why that scope call was revisited.


def _review_report_payload():
    if runstate.review_question is None or runstate.review_result is not False:
        return None
    if runstate.review_question["mode"] != "typed":
        return None
    return _typed_wrong_report_payload(runstate.review_question, runstate.review_submitted_answer)


def submit_review_report(event=None):
    if runstate.review_report_sent:
        return None
    payload = _review_report_payload()
    if payload is None:
        return None
    runstate.review_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _review_pronunciation_report_payload():
    return _plot_pronunciation_report_payload(runstate.review_question)


def submit_review_pronunciation_report(event=None):
    if runstate.review_pronunciation_report_sent:
        return None
    payload = _review_pronunciation_report_payload()
    if payload is None:
        return None
    runstate.review_pronunciation_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def on_toggle_review(event=None):
    runstate.review_controls_open = not runstate.review_controls_open
    render()


def on_start_word_review(event=None):
    start_review("word")


def on_start_grammar_review(event=None):
    start_review("grammar")


def on_start_marathon_review(event=None):
    start_review(MARATHON_MODE)


def on_quick_water(event=None):
    """L29: one-click, one-question session on the most overdue plot."""
    start_review(QUICK_WATER_MODE)


def _make_review_choice_handler(choice):
    def handler(event=None):
        submit_review_answer(choice)
    return handler


def on_review_submit_typed(event=None):
    submit_review_answer(_element("review-answer-input").value)


def on_review_answer_keydown(event=None):
    if event is not None and getattr(event, "key", None) == "Enter":
        event.preventDefault()
        on_review_submit_typed()


def share_result():
    """JSON for shared/copy-result.js (Z-20): the figures a player would
    paste after a review session -- the session score, plots automated and
    the practice score. No seed text: this game has no seeds."""
    total = runstate.review_score["total"]
    stats = []
    if total:
        stats.append(f"{runstate.review_score['correct']}/{total} right")
    automated = automated_plot_count()
    stats.append({"n": automated, "one": "plot automated", "many": "plots automated"})
    stats.append(f"{practice_score()} practice points")
    return json.dumps({
        "game": "Le Champ de Mots",
        "score": f"day {state.current_day}",
        "stats": stats,
    })


def render_review():
    _notify_visual_style_context("review" if runstate.review_mode is not None else "farm")

    controls = _element("review-controls")
    controls.hidden = not runstate.review_controls_open

    panel = _element("review-panel")
    empty_message = _element("review-empty-message")
    summary = _element("review-summary")
    choices_box = _element("review-choices")

    _destroy_review_choice_proxies()
    _element("review-listen-button").hidden = True
    _element("review-listen-show-button").hidden = True
    _element("review-water-note").hidden = True

    # The Copy result button (Z-20) only belongs under the finished summary.
    _element("result-copy-review").hidden = True

    if runstate.review_mode is None:
        panel.hidden = True
        empty_message.hidden = True
        summary.hidden = True
        choices_box.innerHTML = ""
        _element("review-report-button").hidden = True
        _element("review-pronunciation-report-button").hidden = True
        return

    if runstate.review_question is None:
        choices_box.innerHTML = ""
        _element("review-report-button").hidden = True
        _element("review-pronunciation-report-button").hidden = True
        if not runstate.review_queue and runstate.review_score["total"] == 0:
            # Session started, but nothing matched the filters.
            panel.hidden = True
            empty_message.hidden = False
            empty_message.innerText = (
                MARATHON_EMPTY_MESSAGE if runstate.review_mode == MARATHON_MODE
                else QUICK_WATER_EMPTY_MESSAGE if runstate.review_mode == QUICK_WATER_MODE
                else PHRASEBOOK_EMPTY_MESSAGE if runstate.review_mode == PHRASEBOOK_MODE
                else WEAK_SPOT_EMPTY_MESSAGE if runstate.review_mode == WEAK_SPOT_MODE
                else WATER_EMPTY_MESSAGE if runstate.review_mode in WATER_MODES
                else REVIEW_EMPTY_MESSAGE
            )
            summary.hidden = True
            return
        # Queue exhausted -- show the score, nothing else.
        panel.hidden = False
        empty_message.hidden = True
        summary.hidden = False
        summary.innerText = _with_growth(_with_highlights(REVIEW_SUMMARY_MESSAGE.format(**runstate.review_score)), "review")
        _element("result-copy-review").hidden = False
        _element("review-progress").innerText = ""
        _element("review-context").innerText = ""
        _element("review-instruction").innerText = ""
        _element("review-prompt").innerText = ""
        _element("review-note").hidden = True
        _element("review-answer-input").hidden = True
        _element("review-submit-button").hidden = True
        _element("review-next-button").hidden = True
        _element("review-feedback").innerText = ""
        return

    panel.hidden = False
    empty_message.hidden = True
    summary.hidden = True
    _element("review-progress").innerText = f"{runstate.review_index + 1} of {len(runstate.review_queue)}"
    _element("review-context").innerText = runstate.review_question["context"]
    _element("review-instruction").innerText = runstate.review_question["instruction"]
    listening_hidden = (
        runstate.review_mode == WATER_LISTEN_MODE
        and speech_available()
        and not runstate.review_listen_revealed
        and runstate.review_result is None
    )
    _element("review-prompt").innerText = LISTEN_HIDDEN_PROMPT if listening_hidden else runstate.review_question["prompt"]
    listen_button = _element("review-listen-button")
    listen_button.hidden = runstate.review_mode != WATER_LISTEN_MODE or not speech_available()
    show_text_button = _element("review-listen-show-button")
    show_text_button.hidden = not listening_hidden

    note = _element("review-note")
    note.innerText = runstate.review_question["note"] or ""
    note.hidden = not runstate.review_question["note"]

    answered = runstate.review_result is not None
    answer_input = _element("review-answer-input")
    submit = _element("review-submit-button")
    next_button = _element("review-next-button")

    choices_box.innerHTML = ""
    if runstate.review_question["mode"] == "choice":
        answer_input.hidden = True
        submit.hidden = True
        for index, choice in enumerate(runstate.review_question["choices"]):
            button = document.createElement("button")
            button.id = f"review-choice-{index}"
            button.innerText = choice
            button.disabled = answered
            button.className = "choice"
            if answered and choice == runstate.review_question["answer"]:
                button.className = "choice choice--answer"
            proxy = create_proxy(_make_review_choice_handler(choice))
            button.addEventListener("click", proxy)
            review_choice_proxies.append(proxy)
            choices_box.appendChild(button)
    else:
        answer_input.hidden = False
        submit.hidden = False
        submit.disabled = answered

    next_button.hidden = not answered

    if answered:
        template = FEEDBACK["correct" if runstate.review_result else "incorrect"]
        _element("review-feedback").innerText = template.format(answer=runstate.review_question["answer"])
    else:
        _element("review-feedback").innerText = ""
    review_note = water_result_text(runstate.review_water_kind, state.plots_by_id.get(runstate.review_question["plot_id"])) if (answered and runstate.review_result) else ""
    _element("review-water-note").innerText = review_note
    _element("review-water-note").hidden = not review_note

    # Milestone 26: same gating as the main practice panel's own two report
    # buttons -- correctness report only for a wrong typed answer,
    # pronunciation-concern report available the whole time a question is
    # open, regardless of right/wrong or typed/choice.
    report_button = _element("review-report-button")
    show_report = answered and runstate.review_result is False and runstate.review_question["mode"] == "typed"
    report_button.hidden = not show_report
    if show_report:
        report_button.disabled = runstate.review_report_sent
        report_button.innerText = REPORT_SENT_LABEL if runstate.review_report_sent else REPORT_BUTTON_LABEL

    pronunciation_button = _element("review-pronunciation-report-button")
    pronunciation_button.hidden = False
    pronunciation_button.disabled = runstate.review_pronunciation_report_sent
    pronunciation_button.innerText = (
        PRONUNCIATION_REPORT_SENT_LABEL
        if runstate.review_pronunciation_report_sent
        else PRONUNCIATION_REPORT_BUTTON_LABEL
    )
