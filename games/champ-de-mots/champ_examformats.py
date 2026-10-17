"""The exam practice formats panel (clock reading, true or false, rewriting, pronoun answers, reciprocal pronouns, pair
questions). The questions themselves come from formats.py.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from js import document
from pyodide.ffi import create_proxy

import formats
import champ_runstate as runstate
from champ_qbuild import normalize_answer
from champ_util import _element
from champ_points import record_practice


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


formats_proxies = []
FORMATS_RNG = random.Random()
FORMATS_SUMMARY = "{label} complete: {correct}/{total} right."


def _destroy_formats_proxies():
    for proxy in formats_proxies:
        proxy.destroy()
    formats_proxies.clear()


def start_formats(format_id=None):
    """Opens the panel; with a format id it starts that format's session straight away."""
    runstate.formats_active = True
    runstate.formats_result = None
    runstate.formats_given = None
    runstate.formats_score = {"correct": 0, "total": 0}
    runstate.formats_index = 0
    if format_id in formats.FORMATS:
        runstate.formats_format = format_id
        runstate.formats_queue = formats.make_session(format_id, FORMATS_RNG)
    else:
        runstate.formats_format = None
        runstate.formats_queue = []
    try:
        _element("formats-input").value = ""
    except KeyError:
        pass
    render()
    return runstate.formats_queue


def on_open_formats(event=None):
    start_formats(None)


def on_pick_format(format_id):
    def handler(event=None):
        start_formats(format_id)
    return handler


def submit_formats_answer(given):
    """Grades one answer with the game's own normaliser; True/False, or None when nothing is open."""
    if not runstate.formats_active or runstate.formats_format is None or runstate.formats_result is not None or runstate.formats_index >= len(runstate.formats_queue):
        return None
    question = runstate.formats_queue[runstate.formats_index]
    if question["typed"] and not str(given).strip():
        return None
    runstate.formats_given = str(given)
    runstate.formats_result = formats.check(question, given, lambda text: normalize_answer(text, fold_accents=not runstate.ACCENT_SENSITIVE))
    runstate.formats_score["total"] += 1
    if runstate.formats_result:
        runstate.formats_score["correct"] += 1
    record_practice(formats.FORMATS[runstate.formats_format]["mode"], runstate.formats_result)
    render()
    return runstate.formats_result


def next_formats_question(event=None):
    if not runstate.formats_active or runstate.formats_result is None:
        return None
    runstate.formats_index += 1
    runstate.formats_result = None
    runstate.formats_given = None
    _element("formats-input").value = ""
    render()
    return runstate.formats_index < len(runstate.formats_queue)


def close_formats(event=None):
    runstate.formats_active = False
    runstate.formats_format = None
    runstate.formats_queue = []
    runstate.formats_index = 0
    runstate.formats_result = None
    runstate.formats_given = None
    render()


def _make_formats_choice_handler(choice):
    def handler(event=None):
        submit_formats_answer(choice)
    return handler


def on_formats_submit(event=None):
    submit_formats_answer(_element("formats-input").value)


def on_formats_keydown(event=None):
    if getattr(event, "key", None) == "Enter":
        on_formats_submit()


def render_formats():
    panel = _element("formats-panel")
    picker = _element("formats-picker")
    choices_box = _element("formats-choices")
    _destroy_formats_proxies()
    choices_box.innerHTML = ""
    picker.innerHTML = ""
    if not runstate.formats_active:
        panel.hidden = True
        return
    panel.hidden = False
    for format_id in formats.FORMAT_ORDER:
        entry = formats.FORMATS[format_id]
        button = document.createElement("button")
        button.id = f"formats-pick-{format_id}"
        button.className = "secondary" + (" selected" if format_id == runstate.formats_format else "")
        button.innerText = entry["label"]
        button.setAttribute("aria-pressed", "true" if format_id == runstate.formats_format else "false")
        proxy = create_proxy(on_pick_format(format_id))
        button.addEventListener("click", proxy)
        formats_proxies.append(proxy)
        picker.appendChild(button)
    card, summary = _element("formats-card"), _element("formats-summary")
    if runstate.formats_format is None:
        card.hidden = True
        summary.hidden = True
        _element("formats-progress").innerText = "Pick a format to practise."
        return
    entry = formats.FORMATS[runstate.formats_format]
    if runstate.formats_index >= len(runstate.formats_queue):
        card.hidden = True
        summary.hidden = False
        summary.innerText = FORMATS_SUMMARY.format(label=entry["label"], **runstate.formats_score)
        _element("formats-progress").innerText = ""
        return
    card.hidden = False
    summary.hidden = True
    question = runstate.formats_queue[runstate.formats_index]
    _element("formats-progress").innerText = f"{entry['label']}: question {runstate.formats_index + 1} of {len(runstate.formats_queue)}"
    _element("formats-instruction").innerText = entry["instruction"]
    _element("formats-context").innerText = question.get("context", "")
    _element("formats-clock").innerHTML = question.get("svg", "")
    _element("formats-prompt").innerText = question["prompt"]
    typed = bool(question["typed"])
    _element("formats-typed-row").hidden = not typed
    _element("formats-input").disabled = runstate.formats_result is not None
    _element("formats-submit-button").disabled = runstate.formats_result is not None
    if not typed:
        for index, choice in enumerate(question["choices"]):
            button = document.createElement("button")
            button.id = f"formats-choice-{index}"
            button.className = "secondary"
            button.innerText = choice
            button.disabled = runstate.formats_result is not None
            proxy = create_proxy(_make_formats_choice_handler(choice))
            button.addEventListener("click", proxy)
            formats_proxies.append(proxy)
            choices_box.appendChild(button)
    feedback = _element("formats-feedback")
    if runstate.formats_result is None:
        feedback.innerText = ""
    elif runstate.formats_result:
        feedback.innerText = "Yes. " + question["explain"]
    else:
        feedback.innerText = "Not quite. " + question["explain"]
    _element("formats-next-button").hidden = runstate.formats_result is None
