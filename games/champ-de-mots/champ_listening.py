"""Listening practice: the browser's own voice reads a French sentence, the player picks what it means.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_util import _element, speak_french, speech_available
from champ_points import record_practice
from champ_builder import builder_sentences


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


# ===========================================================================
# L9 -- listening comprehension. The browser's own speech synthesis reads a
# French sentence aloud (no audio files, no network) and you pick what it
# means from three English options. Sentences are the bonus sentences of the
# unlocked weeks, so it never previews a locked week. It needs a browser with
# speech synthesis (the page's `champSpeak` hook); without one the panel says so
# instead of starting. Answers land in the practice ledger as "listening".
# ===========================================================================
LISTENING_SESSION_LENGTH = 8
LISTENING_RNG = random.Random()
LISTENING_UNAVAILABLE_MESSAGE = (
    "Your browser has no speech voices available, so listening practice cannot start here."
)
LISTENING_EMPTY_MESSAGE = "No sentences are unlocked yet. Each unlocked week brings its own sentence."
LISTENING_CORRECT = "Yes, that is what it says."
LISTENING_INCORRECT = "Not quite. It says: {fr} ({en})"
LISTENING_SUMMARY = "Listening practice complete: {correct}/{total} understood."


listening_proxies = []


def _destroy_listening_proxies():
    for proxy in listening_proxies:
        proxy.destroy()
    listening_proxies.clear()


def _begin_listening_question(speak=True):
    runstate.listening_result = None
    if runstate.listening_index >= len(runstate.listening_queue):
        runstate.listening_choices = []
        return
    sentence = runstate.listening_queue[runstate.listening_index]
    others = [s["en"] for s in builder_sentences() if s["en"] != sentence["en"]]
    LISTENING_RNG.shuffle(others)
    choices = [sentence["en"]] + others[:2]
    LISTENING_RNG.shuffle(choices)
    runstate.listening_choices = choices
    if speak:
        speak_french(sentence["fr"])


def start_listening(event=None):
    runstate.listening_active = True
    runstate.listening_available = speech_available()
    runstate.listening_index = 0
    runstate.listening_score = {"correct": 0, "total": 0}
    sentences = builder_sentences()
    LISTENING_RNG.shuffle(sentences)
    runstate.listening_queue = sentences[:LISTENING_SESSION_LENGTH] if runstate.listening_available else []
    _begin_listening_question()
    render()
    return runstate.listening_queue


def replay_listening(slow=False):
    if not runstate.listening_active or runstate.listening_index >= len(runstate.listening_queue):
        return False
    return speak_french(runstate.listening_queue[runstate.listening_index]["fr"], slow=slow)


def on_listening_play(event=None):
    replay_listening(False)


def on_listening_slow(event=None):
    replay_listening(True)


def pick_listening_answer(index):
    if not runstate.listening_active or runstate.listening_result is not None or runstate.listening_index >= len(runstate.listening_queue):
        return None
    if not (0 <= index < len(runstate.listening_choices)):
        return None
    sentence = runstate.listening_queue[runstate.listening_index]
    runstate.listening_result = runstate.listening_choices[index] == sentence["en"]
    runstate.listening_score["total"] += 1
    if runstate.listening_result:
        runstate.listening_score["correct"] += 1
    record_practice("listening", runstate.listening_result)
    render()
    return runstate.listening_result


def next_listening_question(event=None):
    if not runstate.listening_active or runstate.listening_result is None:
        return None
    runstate.listening_index += 1
    _begin_listening_question()
    render()
    return runstate.listening_index < len(runstate.listening_queue)


def close_listening(event=None):
    runstate.listening_active = False
    runstate.listening_queue = []
    runstate.listening_index = 0
    runstate.listening_choices = []
    runstate.listening_result = None
    render()


def _make_listening_handler(index):
    def handler(event=None):
        pick_listening_answer(index)
    return handler


def render_listening():
    panel = _element("listening-panel")
    choices_box = _element("listening-choices")
    _destroy_listening_proxies()
    choices_box.innerHTML = ""
    if not runstate.listening_active:
        panel.hidden = True
        return
    panel.hidden = False
    empty = _element("listening-empty-message")
    summary = _element("listening-summary")
    card = _element("listening-card")
    if not runstate.listening_queue:
        empty.hidden = False
        empty.innerText = LISTENING_EMPTY_MESSAGE if runstate.listening_available else LISTENING_UNAVAILABLE_MESSAGE
        summary.hidden = True
        card.hidden = True
        _element("listening-progress").innerText = ""
        return
    empty.hidden = True
    if runstate.listening_index >= len(runstate.listening_queue):
        card.hidden = True
        summary.hidden = False
        summary.innerText = LISTENING_SUMMARY.format(**runstate.listening_score)
        _element("listening-progress").innerText = ""
        return
    card.hidden = False
    summary.hidden = True
    sentence = runstate.listening_queue[runstate.listening_index]
    _element("listening-progress").innerText = f"Sentence {runstate.listening_index + 1} of {len(runstate.listening_queue)}"
    for index, choice in enumerate(runstate.listening_choices):
        button = document.createElement("button")
        button.id = f"listening-choice-{index}"
        button.className = "secondary"
        button.innerText = choice
        button.disabled = runstate.listening_result is not None
        proxy = create_proxy(_make_listening_handler(index))
        button.addEventListener("click", proxy)
        listening_proxies.append(proxy)
        choices_box.appendChild(button)
    feedback = _element("listening-feedback")
    if runstate.listening_result is None:
        feedback.innerText = ""
    else:
        feedback.innerText = LISTENING_CORRECT if runstate.listening_result else LISTENING_INCORRECT.format(
            fr=sentence["fr"], en=sentence["en"]
        )
    _element("listening-next-button").hidden = runstate.listening_result is None
