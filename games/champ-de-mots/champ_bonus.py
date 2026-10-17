"""Bonus sentence sections: order the tiles, translate each tile, translate the whole sentence; their report buttons and the
panel's drawing.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_catalog import CATALOG
from champ_model import state
from champ_grading import TIER_LENIENT, TIER_STRICT, check_answer, generate_accepted_variants
from champ_labels import (
    BONUS_SENTENCE_REPORT_TOPIC_TYPE, BONUS_TILE_REPORT_TOPIC_TYPE, FEEDBACK,
    PRONUNCIATION_REPORT_BUTTON_LABEL, PRONUNCIATION_REPORT_MARKER, PRONUNCIATION_REPORT_SENT_LABEL,
    PRONUNCIATION_REPORT_TOPIC_TYPE, REPORT_BUTTON_LABEL, REPORT_GAME_ID, REPORT_SENT_LABEL,
)
from champ_util import _element
from champ_points import record_practice
from champ_reportlog import _record_report_log_entry
from champ_reports import _dispatch_report


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


# --- Milestone 13: bonus sentence-building section state (design doc §14.6) -
#
# Purely informational like Review and the proficiency test — nothing here
# ever touches a plot's SRS state or row-unlock state. Three tasks per
# sentence: order the tiles, translate each tile (STRICT), translate the
# whole sentence (LENIENT) — see CLAUDE.md's Milestone 13 build note for why
# those two tiers are fixed by task rather than decided by grading_tier().

BONUS_RNG = random.Random()


BONUS_ORDER_CORRECT = "That's the right order."
BONUS_ORDER_INCORRECT = "Not quite — the sentence is: {sentence}"
BONUS_SUMMARY_MESSAGE = "Bonus section complete — {correct}/{total} correct."


def _make_bonus_handler(sequence):
    def handler(event=None):
        start_bonus_section(sequence)
    return handler


# ===========================================================================
# Milestone 13 — bonus sentence-building sections (design doc §14.6)
# ===========================================================================
#
# One original sentence per week (built only from that week's own vocab and
# grammar — see CLAUDE.md's Milestone 13 build note for the exact sourcing
# policy), three tasks each: order the word tiles, translate each tile on
# its own (STRICT — an explicit per-task tier assignment from §14.6, not the
# auto-decided grading_tier() the main farm/Review/proficiency paths use),
# then translate the whole assembled sentence (LENIENT). Purely informational
# like Milestones 11-12: nothing here ever touches a plot's SRS state.

bonus_pool_proxies = []


def _destroy_bonus_pool_proxies():
    for proxy in bonus_pool_proxies:
        proxy.destroy()
    bonus_pool_proxies.clear()


def bonus_sentences_for(sequence):
    for week in CATALOG["weeks"]:
        if week["sequence"] == sequence:
            return week.get("bonus_sentences", [])
    return []


def is_bonus_section_available(sequence):
    """Same posture as the proficiency test (§14.5's build note): only
    offered for an already-unlocked week, so it can't preview a week's
    content ahead of §7's pacing gate."""
    return state.is_row_unlocked(sequence) and bool(bonus_sentences_for(sequence))


def _current_bonus_sentence():
    if runstate.bonus_index >= len(runstate.bonus_queue):
        return None
    return runstate.bonus_queue[runstate.bonus_index]


def _begin_bonus_sentence():
    """Reset every per-sentence tracking field and roll a fresh shuffled tile
    pool for whichever sentence `bonus_index` now points at (or close the
    session out if the queue is exhausted)."""

    sentence = _current_bonus_sentence()
    runstate.bonus_placed = []
    runstate.bonus_order_correct = None
    runstate.bonus_tile_index = 0
    runstate.bonus_tile_result = None
    runstate.bonus_tile_score = {"correct": 0, "total": 0}
    runstate.bonus_sentence_result = None
    # Both tasks' report state (correctness report + pronunciation report,
    # Milestone 26) is per-sentence just like the typed-answer inputs below,
    # so it's reset here in the same shared spot rather than separately at
    # each task's own entry point.
    runstate.bonus_tile_submitted_answer = None
    runstate.bonus_tile_report_sent = False
    runstate.bonus_tile_pronunciation_report_sent = False
    runstate.bonus_sentence_submitted_answer = None
    runstate.bonus_sentence_report_sent = False
    runstate.bonus_sentence_pronunciation_report_sent = False
    # A fresh sentence starts at the "order" task, but both typed-answer
    # inputs further along (task 2's tile box, task 3's sentence box) can
    # still be holding text from a *previous* sentence's session — cleared
    # here, once, rather than only when each task is separately entered.
    _element("bonus-tile-answer-input").value = ""
    _element("bonus-sentence-answer-input").value = ""

    if sentence is None:
        runstate.bonus_task = None
        runstate.bonus_tile_pool = []
        return

    pool = list(sentence["tiles"])
    BONUS_RNG.shuffle(pool)
    # A shuffle landing back on the original order would make the ordering
    # task trivially already-solved; nudge it once if that happens.
    if len(pool) > 1 and [t["fr"] for t in pool] == [t["fr"] for t in sentence["tiles"]]:
        pool.reverse()
    runstate.bonus_tile_pool = pool
    runstate.bonus_task = "order"


def start_bonus_section(sequence, event=None):
    if not is_bonus_section_available(sequence):
        return None

    runstate.bonus_sequence = sequence
    runstate.bonus_queue = bonus_sentences_for(sequence)
    runstate.bonus_index = 0
    runstate.bonus_score = {"correct": 0, "total": 0}
    runstate.bonus_mode = True
    _begin_bonus_sentence()
    render()
    return runstate.bonus_queue


def place_bonus_tile(pool_index):
    """Task 1: move one tile from the pool to the end of the placed list.
    Once the pool empties, the placed order is checked against the
    sentence's real order — a whole-sentence pass/fail, not per-tile."""

    if runstate.bonus_task != "order" or not (0 <= pool_index < len(runstate.bonus_tile_pool)):
        return None
    tile = runstate.bonus_tile_pool.pop(pool_index)
    runstate.bonus_placed.append(tile)
    if not runstate.bonus_tile_pool:
        sentence = _current_bonus_sentence()
        runstate.bonus_order_correct = [t["fr"] for t in runstate.bonus_placed] == [
            t["fr"] for t in sentence["tiles"]
        ]
        runstate.bonus_score["total"] += 1
        if runstate.bonus_order_correct:
            runstate.bonus_score["correct"] += 1
        record_practice("bonus", runstate.bonus_order_correct)
    render()
    return runstate.bonus_order_correct


def advance_from_order(event=None):
    """Move on to task 2 once task 1 has a result — right or wrong, §3's
    no-punishment stance means an incorrect order still lets you continue
    (and the correct order becomes obvious once task 2 shows each tile in
    its real place)."""

    if runstate.bonus_task != "order" or runstate.bonus_order_correct is None:
        return None
    runstate.bonus_task = "translate_tiles"
    render()


def submit_bonus_tile_translation(given):
    """Task 2, one tile at a time, in the sentence's real order. STRICT by
    explicit task assignment (§14.6) — not decided by grading_tier()."""

    if runstate.bonus_task != "translate_tiles" or runstate.bonus_tile_result is not None:
        return None
    sentence = _current_bonus_sentence()
    if sentence is None or runstate.bonus_tile_index >= len(sentence["tiles"]):
        return None
    tile = sentence["tiles"][runstate.bonus_tile_index]
    runstate.bonus_tile_submitted_answer = str(given).strip()
    question = {
        "mode": "typed", "answer": tile["en"], "choices": [],
        "lang": "en", "accepted": tile.get("accepted_en") or [],
    }
    runstate.bonus_tile_result = check_answer(
        question, given, tier=TIER_STRICT, accent_sensitive=runstate.ACCENT_SENSITIVE
    )
    runstate.bonus_tile_score["total"] += 1
    runstate.bonus_score["total"] += 1
    record_practice("bonus", runstate.bonus_tile_result)
    if runstate.bonus_tile_result:
        runstate.bonus_tile_score["correct"] += 1
        runstate.bonus_score["correct"] += 1
    render()
    return runstate.bonus_tile_result


def next_bonus_tile(event=None):
    """Advance to the next tile, or into task 3 once every tile has been
    translated."""

    if runstate.bonus_task != "translate_tiles":
        return None
    sentence = _current_bonus_sentence()
    runstate.bonus_tile_index += 1
    runstate.bonus_tile_result = None
    runstate.bonus_tile_submitted_answer = None
    runstate.bonus_tile_report_sent = False
    runstate.bonus_tile_pronunciation_report_sent = False
    _element("bonus-tile-answer-input").value = ""
    if sentence is None or runstate.bonus_tile_index >= len(sentence["tiles"]):
        runstate.bonus_task = "translate_sentence"
    render()


def submit_bonus_sentence_translation(given):
    """Task 3: the whole sentence, LENIENT — explicit task assignment (§14.6),
    same reasoning as task 2's STRICT."""

    if runstate.bonus_task != "translate_sentence" or runstate.bonus_sentence_result is not None:
        return None
    sentence = _current_bonus_sentence()
    if sentence is None:
        return None
    runstate.bonus_sentence_submitted_answer = str(given).strip()
    question = {
        "mode": "typed", "answer": sentence["en"], "choices": [],
        "lang": "en", "accepted": sentence.get("accepted_en") or [],
    }
    runstate.bonus_sentence_result = check_answer(
        question, given, tier=TIER_LENIENT, accent_sensitive=runstate.ACCENT_SENSITIVE
    )
    runstate.bonus_score["total"] += 1
    if runstate.bonus_sentence_result:
        runstate.bonus_score["correct"] += 1
    record_practice("bonus", runstate.bonus_sentence_result)
    render()
    return runstate.bonus_sentence_result


def next_bonus_sentence(event=None):
    """Move to the next sentence in this week's queue, or end the session
    (bonus_task becomes None) once the queue is exhausted."""

    if runstate.bonus_task != "translate_sentence" or runstate.bonus_sentence_result is None:
        return None
    runstate.bonus_index += 1
    _begin_bonus_sentence()
    render()


def close_bonus_section(event=None):
    runstate.bonus_mode = False
    runstate.bonus_sequence = None
    runstate.bonus_queue = []
    runstate.bonus_index = 0
    runstate.bonus_task = None
    runstate.bonus_tile_pool = []
    runstate.bonus_placed = []
    runstate.bonus_order_correct = None
    runstate.bonus_tile_index = 0
    runstate.bonus_tile_result = None
    runstate.bonus_tile_score = {"correct": 0, "total": 0}
    runstate.bonus_sentence_result = None
    runstate.bonus_score = {"correct": 0, "total": 0}
    runstate.bonus_tile_submitted_answer = None
    runstate.bonus_tile_report_sent = False
    runstate.bonus_tile_pronunciation_report_sent = False
    runstate.bonus_sentence_submitted_answer = None
    runstate.bonus_sentence_report_sent = False
    runstate.bonus_sentence_pronunciation_report_sent = False
    render()


# --- Milestone 26: report buttons, extended into Bonus's tasks 2 and 3 -----
#
# Task 1 (tile ordering) has no typed answer and gets neither button, same
# rule that already keeps a wrong multiple-choice pick report-free elsewhere.
# Bonus sentences are hand-authored (§14.6), not plot-backed, so these build
# their own payload shape rather than calling `_typed_wrong_report_payload()`/
# `_plot_pronunciation_report_payload()` — there is no plot or catalog item
# behind a bonus sentence for those to look up. `item_id` instead names the
# sentence (and, for a tile, which tile within it); `topic_type` is a fixed
# marker (`BONUS_TILE_REPORT_TOPIC_TYPE`/`BONUS_SENTENCE_REPORT_TOPIC_TYPE`)
# so a human triaging the queue can tell these apart from plot-backed reports,
# same idea as Milestone 24's "pronunciation" topic_type marker.


def _bonus_tile_report_payload():
    if runstate.bonus_task != "translate_tiles" or runstate.bonus_tile_result is not False:
        return None
    sentence = _current_bonus_sentence()
    if sentence is None or runstate.bonus_tile_index >= len(sentence["tiles"]):
        return None
    tile = sentence["tiles"][runstate.bonus_tile_index]
    return {
        "game_id": REPORT_GAME_ID,
        "item_id": f"{sentence['id']}-tile-{runstate.bonus_tile_index}",
        "submitted_answer": runstate.bonus_tile_submitted_answer or "",
        "marked_correct_answer": generate_accepted_variants(tile["en"]) + [
            e for e in (tile.get("accepted_en") or []) if e not in generate_accepted_variants(tile["en"])
        ],
        "topic_type": BONUS_TILE_REPORT_TOPIC_TYPE,
    }


def submit_bonus_tile_report(event=None):
    if runstate.bonus_tile_report_sent:
        return None
    payload = _bonus_tile_report_payload()
    if payload is None:
        return None
    runstate.bonus_tile_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _bonus_tile_pronunciation_report_payload():
    if runstate.bonus_task != "translate_tiles":
        return None
    sentence = _current_bonus_sentence()
    if sentence is None or runstate.bonus_tile_index >= len(sentence["tiles"]):
        return None
    tile = sentence["tiles"][runstate.bonus_tile_index]
    return {
        "game_id": REPORT_GAME_ID,
        "item_id": f"{sentence['id']}-tile-{runstate.bonus_tile_index}",
        "submitted_answer": PRONUNCIATION_REPORT_MARKER,
        "marked_correct_answer": [tile["fr"]],
        "topic_type": PRONUNCIATION_REPORT_TOPIC_TYPE,
    }


def submit_bonus_tile_pronunciation_report(event=None):
    if runstate.bonus_tile_pronunciation_report_sent:
        return None
    payload = _bonus_tile_pronunciation_report_payload()
    if payload is None:
        return None
    runstate.bonus_tile_pronunciation_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _bonus_sentence_report_payload():
    if runstate.bonus_task != "translate_sentence" or runstate.bonus_sentence_result is not False:
        return None
    sentence = _current_bonus_sentence()
    if sentence is None:
        return None
    return {
        "game_id": REPORT_GAME_ID,
        "item_id": sentence["id"],
        "submitted_answer": runstate.bonus_sentence_submitted_answer or "",
        "marked_correct_answer": generate_accepted_variants(sentence["en"]),
        "topic_type": BONUS_SENTENCE_REPORT_TOPIC_TYPE,
    }


def submit_bonus_sentence_report(event=None):
    if runstate.bonus_sentence_report_sent:
        return None
    payload = _bonus_sentence_report_payload()
    if payload is None:
        return None
    runstate.bonus_sentence_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _bonus_sentence_pronunciation_report_payload():
    if runstate.bonus_task != "translate_sentence":
        return None
    sentence = _current_bonus_sentence()
    if sentence is None:
        return None
    return {
        "game_id": REPORT_GAME_ID,
        "item_id": sentence["id"],
        "submitted_answer": PRONUNCIATION_REPORT_MARKER,
        "marked_correct_answer": [sentence["fr"]],
        "topic_type": PRONUNCIATION_REPORT_TOPIC_TYPE,
    }


def submit_bonus_sentence_pronunciation_report(event=None):
    if runstate.bonus_sentence_pronunciation_report_sent:
        return None
    payload = _bonus_sentence_pronunciation_report_payload()
    if payload is None:
        return None
    runstate.bonus_sentence_pronunciation_report_sent = True
    _dispatch_report(payload)
    _record_report_log_entry(payload)
    render()
    return payload


def _make_bonus_pool_handler(index):
    def handler(event=None):
        place_bonus_tile(index)
    return handler


def on_bonus_tile_submit_typed(event=None):
    submit_bonus_tile_translation(_element("bonus-tile-answer-input").value)


def on_bonus_tile_answer_keydown(event=None):
    if event is not None and getattr(event, "key", None) == "Enter":
        event.preventDefault()
        on_bonus_tile_submit_typed()


def on_bonus_sentence_submit_typed(event=None):
    submit_bonus_sentence_translation(_element("bonus-sentence-answer-input").value)


def on_bonus_sentence_answer_keydown(event=None):
    if event is not None and getattr(event, "key", None) == "Enter":
        event.preventDefault()
        on_bonus_sentence_submit_typed()


def render_bonus():
    panel = _element("bonus-panel")
    pool_box = _element("bonus-tile-pool")
    placed_box = _element("bonus-tile-placed")

    _destroy_bonus_pool_proxies()

    if not runstate.bonus_mode:
        panel.hidden = True
        pool_box.innerHTML = ""
        placed_box.innerHTML = ""
        _element("bonus-tile-report-button").hidden = True
        _element("bonus-tile-pronunciation-report-button").hidden = True
        _element("bonus-sentence-report-button").hidden = True
        _element("bonus-sentence-pronunciation-report-button").hidden = True
        return

    panel.hidden = False
    sentence = _current_bonus_sentence()

    order_section = _element("bonus-order-section")
    tiles_section = _element("bonus-tiles-section")
    sentence_section = _element("bonus-sentence-section")
    summary = _element("bonus-summary")

    if sentence is None:
        # Every sentence in the week's queue is done.
        order_section.hidden = True
        tiles_section.hidden = True
        sentence_section.hidden = True
        summary.hidden = False
        summary.innerText = BONUS_SUMMARY_MESSAGE.format(**runstate.bonus_score)
        pool_box.innerHTML = ""
        placed_box.innerHTML = ""
        _element("bonus-tile-report-button").hidden = True
        _element("bonus-tile-pronunciation-report-button").hidden = True
        _element("bonus-sentence-report-button").hidden = True
        _element("bonus-sentence-pronunciation-report-button").hidden = True
        return

    summary.hidden = True
    _element("bonus-progress").innerText = f"Sentence {runstate.bonus_index + 1} of {len(runstate.bonus_queue)}"

    if runstate.bonus_task == "order":
        order_section.hidden = False
        tiles_section.hidden = True
        sentence_section.hidden = True

        pool_box.innerHTML = ""
        for index, tile in enumerate(runstate.bonus_tile_pool):
            button = document.createElement("button")
            button.id = f"bonus-pool-tile-{index}"
            button.innerText = tile["fr"]
            button.className = "bonus-tile"
            proxy = create_proxy(_make_bonus_pool_handler(index))
            button.addEventListener("click", proxy)
            bonus_pool_proxies.append(proxy)
            pool_box.appendChild(button)

        placed_box.innerHTML = ""
        for tile in runstate.bonus_placed:
            span = document.createElement("span")
            span.className = "bonus-tile bonus-tile--placed"
            span.innerText = tile["fr"]
            placed_box.appendChild(span)

        continue_button = _element("bonus-order-continue-button")
        continue_button.hidden = runstate.bonus_order_correct is None
        feedback = _element("bonus-order-feedback")
        if runstate.bonus_order_correct is None:
            feedback.innerText = ""
        else:
            feedback.innerText = BONUS_ORDER_CORRECT if runstate.bonus_order_correct else (
                BONUS_ORDER_INCORRECT.format(sentence=sentence["fr"])
            )
        # Task 1 has no typed answer, so neither report button ever applies
        # to it -- same rule that keeps a wrong multiple-choice pick
        # report-free everywhere else.
        _element("bonus-tile-report-button").hidden = True
        _element("bonus-tile-pronunciation-report-button").hidden = True
        _element("bonus-sentence-report-button").hidden = True
        _element("bonus-sentence-pronunciation-report-button").hidden = True
        return

    pool_box.innerHTML = ""
    placed_box.innerHTML = ""

    if runstate.bonus_task == "translate_tiles":
        order_section.hidden = True
        tiles_section.hidden = False
        sentence_section.hidden = True

        tile = sentence["tiles"][runstate.bonus_tile_index]
        _element("bonus-tile-progress").innerText = (
            f"Tile {runstate.bonus_tile_index + 1} of {len(sentence['tiles'])}"
        )
        _element("bonus-tile-prompt").innerText = tile["fr"]

        answered = runstate.bonus_tile_result is not None
        answer_input = _element("bonus-tile-answer-input")
        submit = _element("bonus-tile-submit-button")
        next_button = _element("bonus-tile-next-button")
        answer_input.hidden = False
        submit.hidden = False
        submit.disabled = answered
        next_button.hidden = not answered

        feedback = _element("bonus-tile-feedback")
        if answered:
            template = FEEDBACK["correct" if runstate.bonus_tile_result else "incorrect"]
            feedback.innerText = template.format(answer=tile["en"])
        else:
            feedback.innerText = ""

        # Milestone 26: same two-button pattern as the main practice panel.
        report_button = _element("bonus-tile-report-button")
        show_report = answered and runstate.bonus_tile_result is False
        report_button.hidden = not show_report
        if show_report:
            report_button.disabled = runstate.bonus_tile_report_sent
            report_button.innerText = (
                REPORT_SENT_LABEL if runstate.bonus_tile_report_sent else REPORT_BUTTON_LABEL
            )
        pronunciation_button = _element("bonus-tile-pronunciation-report-button")
        pronunciation_button.hidden = False
        pronunciation_button.disabled = runstate.bonus_tile_pronunciation_report_sent
        pronunciation_button.innerText = (
            PRONUNCIATION_REPORT_SENT_LABEL
            if runstate.bonus_tile_pronunciation_report_sent
            else PRONUNCIATION_REPORT_BUTTON_LABEL
        )
        _element("bonus-sentence-report-button").hidden = True
        _element("bonus-sentence-pronunciation-report-button").hidden = True
        return

    if runstate.bonus_task == "translate_sentence":
        order_section.hidden = True
        tiles_section.hidden = True
        sentence_section.hidden = False

        _element("bonus-sentence-prompt").innerText = sentence["fr"]
        answered = runstate.bonus_sentence_result is not None
        answer_input = _element("bonus-sentence-answer-input")
        submit = _element("bonus-sentence-submit-button")
        next_button = _element("bonus-sentence-next-button")
        answer_input.hidden = False
        submit.hidden = False
        submit.disabled = answered
        next_button.hidden = not answered

        feedback = _element("bonus-sentence-feedback")
        if answered:
            template = FEEDBACK["correct" if runstate.bonus_sentence_result else "incorrect"]
            feedback.innerText = template.format(answer=sentence["en"])
        else:
            feedback.innerText = ""

        # Milestone 26: same two-button pattern as the main practice panel.
        _element("bonus-tile-report-button").hidden = True
        _element("bonus-tile-pronunciation-report-button").hidden = True
        report_button = _element("bonus-sentence-report-button")
        show_report = answered and runstate.bonus_sentence_result is False
        report_button.hidden = not show_report
        if show_report:
            report_button.disabled = runstate.bonus_sentence_report_sent
            report_button.innerText = (
                REPORT_SENT_LABEL if runstate.bonus_sentence_report_sent else REPORT_BUTTON_LABEL
            )
        pronunciation_button = _element("bonus-sentence-pronunciation-report-button")
        pronunciation_button.hidden = False
        pronunciation_button.disabled = runstate.bonus_sentence_pronunciation_report_sent
        pronunciation_button.innerText = (
            PRONUNCIATION_REPORT_SENT_LABEL
            if runstate.bonus_sentence_pronunciation_report_sent
            else PRONUNCIATION_REPORT_BUTTON_LABEL
        )
