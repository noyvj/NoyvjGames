"""The 'I think this should count' and pronunciation-concern reports for the practice panel, and the helpers every other
mode's report buttons reuse (payload shapes and the dispatch to the page).
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import json

import champ_runstate as runstate
from champ_model import state
from champ_grading import _lookup_accepted
from champ_labels import PRONUNCIATION_REPORT_MARKER, PRONUNCIATION_REPORT_TOPIC_TYPE, REPORT_GAME_ID
from champ_reportlog import _record_report_log_entry


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


def _typed_wrong_report_payload(question, submitted_answer):
    """Shared §14.2.4 payload shape behind every mode's own "I think this
    should count" report button. Originally just `_report_payload()`'s own
    body; factored out at Milestone 26 once Review, Proficiency, and Bonus's
    tile/sentence tasks all needed the identical shape for a plot-backed
    `question` dict (one produced by `generate_question()`, carrying its own
    "plot_id"/"topic_type"/"answer"). Bonus's hand-authored sentences aren't
    plot-backed, so Bonus builds its payload directly instead of calling
    this — see `_bonus_tile_report_payload()`/`_bonus_sentence_report_payload()`.
    The caller is responsible for the "answered, wrong, typed" gate; that
    part differs in variable name per mode, not in meaning."""
    accepted = _lookup_accepted(question) or []
    marked_correct_answer = [question["answer"]]
    for alt in accepted:
        if alt not in marked_correct_answer:
            marked_correct_answer.append(alt)
    return {
        "game_id": REPORT_GAME_ID,
        "item_id": question["plot_id"],
        "submitted_answer": submitted_answer or "",
        "marked_correct_answer": marked_correct_answer,
        "topic_type": question["topic_type"],
    }


def _plot_pronunciation_report_payload(question):
    """Shared Milestone 24 payload shape for a plot-backed question — the
    main practice panel, Review, and Proficiency all generate their
    questions from a real plot via `generate_question()`. Bonus's
    hand-authored sentences aren't plot-backed, so Bonus builds its own
    version instead of calling this one (see
    `_bonus_tile_pronunciation_report_payload()`/
    `_bonus_sentence_pronunciation_report_payload()`)."""
    if question is None:
        return None
    plot = state.plots_by_id.get(question.get("plot_id"))
    if plot is None:
        return None
    return {
        "game_id": REPORT_GAME_ID,
        "item_id": question["plot_id"],
        "submitted_answer": PRONUNCIATION_REPORT_MARKER,
        "marked_correct_answer": [plot.items[0]["fr"]],
        "topic_type": PRONUNCIATION_REPORT_TOPIC_TYPE,
    }


def _report_payload():
    """The §14.2.4 payload for the currently-open question, or None if
    there's nothing to report (no question, not yet answered, or answered
    correctly). The timestamp is deliberately not built here — the backend's
    own `created_at` covers it, keeping this file free of the wall-clock
    dependency the Milestone 7 audit forbids (see CLAUDE.md's Milestone 9
    build note)."""
    if runstate.current_question is None or runstate.current_result is not False:
        return None
    if runstate.current_question["mode"] != "typed":
        return None
    return _typed_wrong_report_payload(runstate.current_question, runstate.current_submitted_answer)


def _notify_visual_style_context(context):
    """L2 (planning/TODO.md): tells visual-style.js which per-context
    preset (farm/review) should be live, whenever that context actually
    changes. Same Python-computes/JS-owns-the-one-external-thing split as
    _dispatch_report() below -- a no-op under the pytest harness (no
    js.window) or a page without visual-style.js loaded."""
    try:
        from js import window  # noqa: PLC0415 — Pyodide-only, deliberately lazy
    except ImportError:
        return
    api = getattr(window, "ChampDeMotsVisualStyle", None)
    if api is not None:
        api.setContext(context)


def _dispatch_report(payload):
    """Hands the payload to a JS-side sender, same split as the shared save
    widget: Python computes state, JS owns the actual fetch() call (see
    index.html). Safe to call from plain CPython (this file's own test
    harness, or any future non-browser context) since a missing `js.window`
    or sender function is simply a no-op rather than a crash — the same
    defensive-import pattern `_read_catalog_json()` already uses."""
    try:
        from js import window  # noqa: PLC0415 — Pyodide-only, deliberately lazy
    except ImportError:
        return
    sender = getattr(window, "submitAnswerReport", None)
    if sender is not None:
        sender(json.dumps(payload))


def submit_report(event=None):
    """Send the currently-open question's report, once. A second click (or
    a call with nothing to report) is a no-op — there is nothing new to say."""

    if runstate.report_sent:
        return None
    payload = _report_payload()
    if payload is None:
        return None
    runstate.report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _pronunciation_report_payload():
    """The Milestone 24 payload for the currently-open question's own item,
    or None if there's no question open. Unlike `_report_payload()`, this
    doesn't care whether the answer was right or wrong, typed or chosen --
    a pronunciation concern is about the catalog text itself, not about how
    this particular attempt went."""
    return _plot_pronunciation_report_payload(runstate.current_question)


def submit_pronunciation_report(event=None):
    """Send a pronunciation-concern report for the currently-open question's
    item, once. Reuses `_dispatch_report()` unchanged -- same endpoint, same
    payload shape, just a different `topic_type` for a human triaging the
    queue to filter on."""

    if runstate.pronunciation_report_sent:
        return None
    payload = _pronunciation_report_payload()
    if payload is None:
        return None
    runstate.pronunciation_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload
