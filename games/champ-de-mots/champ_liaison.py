"""Liaison and elision practice: a short fixed quiz over hand-written questions.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_catalog import LIAISON_DRILL_QUESTIONS
from champ_model import state
from champ_util import _element
from champ_points import record_practice


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


# ===========================================================================
# Improvement Ideas addendum -- liaison/elision practice ("Liaison practice")
# ===========================================================================
#
# A short, fixed-length multiple-choice quiz over the hand-authored questions
# in LIAISON_DRILL_QUESTIONS above. Entirely stateless with respect to SRS
# and row-unlock caching -- same posture as the proficiency test and bonus
# sections (see their own build notes): no state.review(), no nudge, nothing
# written back to a plot. Gated to unlocked weeks only, same spoiler-avoidance
# rule cultural notes and the dashboard already use.

LIAISON_INSTRUCTION = "Pick the correct answer."
LIAISON_SUMMARY_MESSAGE = "{correct} of {total} correct."
# Its own feedback wording, not the farm's FEEDBACK dict -- "this plot is
# growing" makes no sense for a quiz that never touches a plot.
LIAISON_FEEDBACK = {
    "correct": "Yes — {answer}.",
    "incorrect": "Not quite — it was {answer}.",
}


LIAISON_RNG = random.Random()


def _destroy_liaison_choice_proxies():
    for proxy in runstate.liaison_choice_proxies:
        proxy.destroy()
    runstate.liaison_choice_proxies = []


def liaison_drill_available():
    return any(state.is_row_unlocked(entry["sequence"]) for entry in LIAISON_DRILL_QUESTIONS)


def build_liaison_drill(rng=None):
    rng = LIAISON_RNG if rng is None else rng
    eligible = [
        entry for entry in LIAISON_DRILL_QUESTIONS if state.is_row_unlocked(entry["sequence"])
    ]
    rng.shuffle(eligible)
    return eligible


def start_liaison_drill(event=None):
    runstate.liaison_questions = build_liaison_drill()
    if not runstate.liaison_questions:
        return None
    runstate.liaison_index = 0
    runstate.liaison_result = None
    runstate.liaison_score = {"correct": 0, "total": 0}
    runstate.liaison_mode = True
    render()
    return runstate.liaison_questions


def submit_liaison_answer(given):
    if runstate.liaison_index >= len(runstate.liaison_questions) or runstate.liaison_result is not None:
        return None
    entry = runstate.liaison_questions[runstate.liaison_index]
    runstate.liaison_result = given == entry["answer"]
    runstate.liaison_score["total"] += 1
    if runstate.liaison_result:
        runstate.liaison_score["correct"] += 1
    record_practice("liaison", runstate.liaison_result)
    render()
    return runstate.liaison_result


def next_liaison_question(event=None):
    if not runstate.liaison_mode:
        return None
    runstate.liaison_index += 1
    runstate.liaison_result = None
    render()
    return runstate.liaison_index


def close_liaison_drill(event=None):
    runstate.liaison_mode = False
    runstate.liaison_questions = []
    runstate.liaison_index = 0
    runstate.liaison_result = None
    runstate.liaison_score = {"correct": 0, "total": 0}
    render()


def on_toggle_liaison_drill(event=None):
    if runstate.liaison_mode:
        close_liaison_drill()
    else:
        start_liaison_drill()


def _make_liaison_choice_handler(choice):
    def handler(event=None):
        submit_liaison_answer(choice)
    return handler


# L26 -- a small sound legend for the bracketed sounds a liaison/elision
# question mentions ("[z]"). Data-driven: it lists only the symbols that
# actually appear in the current question's text, described with plain
# English comparisons, so a future question using [t] or [n] needs no code.
LIAISON_SOUND_LEGEND = {
    "z": "the 'z' sound, as in English 'zoo'",
    "t": "the 't' sound, as in English 'tea'",
    "n": "the 'n' sound, as in English 'no'",
    "ʁ": "the French 'r', made at the back of the throat",
    "p": "the 'p' sound, as in English 'pea'",
}


def liaison_legend_text(entry):
    import re  # noqa: PLC0415 -- only needed here

    text = " ".join([entry.get("prompt", ""), entry.get("explanation", ""), *entry.get("choices", [])])
    seen = []
    for symbol in re.findall(r"\[([^\]\s]{1,3})\]", text):
        if symbol in LIAISON_SOUND_LEGEND and symbol not in seen:
            seen.append(symbol)
    if not seen:
        return ""
    return "Sounds: " + "; ".join(f"[{s}] = {LIAISON_SOUND_LEGEND[s]}" for s in seen)


def render_liaison_drill():
    panel = _element("liaison-panel")
    toggle = _element("liaison-toggle-button")
    choices_box = _element("liaison-choices")

    _destroy_liaison_choice_proxies()

    toggle.disabled = not runstate.liaison_mode and not liaison_drill_available()
    toggle.innerText = "Close liaison practice" if runstate.liaison_mode else "🗣️ Liaison practice"

    if not runstate.liaison_mode:
        panel.hidden = True
        choices_box.innerHTML = ""
        return

    panel.hidden = False
    complete = runstate.liaison_index >= len(runstate.liaison_questions)
    summary = _element("liaison-summary")
    explanation = _element("liaison-explanation")

    if complete:
        choices_box.innerHTML = ""
        summary.hidden = False
        summary.innerText = LIAISON_SUMMARY_MESSAGE.format(**runstate.liaison_score)
        _element("liaison-progress").innerText = ""
        _element("liaison-context").innerText = ""
        _element("liaison-instruction").innerText = ""
        _element("liaison-prompt").innerText = ""
        _element("liaison-legend").hidden = True
        explanation.hidden = True
        _element("liaison-next-button").hidden = True
        _element("liaison-feedback").innerText = ""
        return

    summary.hidden = True
    entry = runstate.liaison_questions[runstate.liaison_index]

    _element("liaison-progress").innerText = f"{runstate.liaison_index + 1} of {len(runstate.liaison_questions)}"
    _element("liaison-context").innerText = entry["item"]
    _element("liaison-instruction").innerText = LIAISON_INSTRUCTION
    _element("liaison-prompt").innerText = entry["prompt"]
    legend = liaison_legend_text(entry)
    _element("liaison-legend").innerText = legend
    _element("liaison-legend").hidden = not legend

    answered = runstate.liaison_result is not None
    next_button = _element("liaison-next-button")

    choices_box.innerHTML = ""
    for index, choice in enumerate(entry["choices"]):
        button = document.createElement("button")
        button.id = f"liaison-choice-{index}"
        button.innerText = choice
        button.disabled = answered
        button.className = "choice"
        if answered and choice == entry["answer"]:
            button.className = "choice choice--answer"
        proxy = create_proxy(_make_liaison_choice_handler(choice))
        button.addEventListener("click", proxy)
        runstate.liaison_choice_proxies.append(proxy)
        choices_box.appendChild(button)

    next_button.hidden = not answered

    if answered:
        template = LIAISON_FEEDBACK["correct" if runstate.liaison_result else "incorrect"]
        _element("liaison-feedback").innerText = template.format(answer=entry["answer"])
        explanation.innerText = entry.get("explanation", "")
        explanation.hidden = not entry.get("explanation")
    else:
        _element("liaison-feedback").innerText = ""
        explanation.hidden = True
