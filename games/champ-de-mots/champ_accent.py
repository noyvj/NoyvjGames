"""The on-screen accent bar under each typed-answer box.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_util import _element


# ===========================================================================
# L-20: an on-screen accent bar beside every typed answer box
# ===========================================================================
#
# One row of letter buttons (e with its accents, the cedilla, the oe ligature,
# and so on) under each typed-answer box, so a phone or a keyboard without
# French accents can still type an accent-checked answer. Pressing a key puts
# the letter at the caret and keeps the box focused (mousedown is cancelled so
# a phone keeps its keyboard up). The keys stay out of the tab order (a typist
# already has the box) but carry names for a screen reader. A bar is shown
# exactly when its box is shown, and it stays quietly dimmed while the accent
# check is off ("accents optional"), working with the existing toggle rather
# than replacing it. Built once at boot; nothing here is saved or timed.
ACCENT_CHARS = [
    ("é", "e acute"), ("è", "e grave"), ("ê", "e circumflex"), ("ë", "e diaeresis"),
    ("à", "a grave"), ("â", "a circumflex"), ("î", "i circumflex"), ("ï", "i diaeresis"),
    ("ô", "o circumflex"), ("ù", "u grave"), ("û", "u circumflex"), ("ü", "u diaeresis"),
    ("ç", "c cedilla"), ("œ", "o e ligature"), ("æ", "a e ligature"), ("ÿ", "y diaeresis"),
]
ACCENT_BARS = {
    "accent-bar-practice": "practice-answer-input",
    "accent-bar-review": "review-answer-input",
    "accent-bar-proficiency": "proficiency-answer-input",
    "accent-bar-placement": "placement-answer-input",
    "accent-bar-bonus-tile": "bonus-tile-answer-input",
    "accent-bar-bonus-sentence": "bonus-sentence-answer-input",
}
ACCENT_BAR_OPTIONAL_NOTE = "Accents are optional right now (the accent check is off)."


def accent_sensitive_now():
    """Whether typed answers are being checked for accents right now."""
    return runstate.ACCENT_SENSITIVE


def insert_accent(input_id, char):
    """Put `char` at the caret (replacing any selection) in the named box and
    return the new text. With no caret information the letter goes on the end."""
    box = _element(input_id)
    value = str(box.value or "")
    start = getattr(box, "selectionStart", None)
    end = getattr(box, "selectionEnd", None)
    if isinstance(start, bool) or not isinstance(start, int):
        start = len(value)
    if isinstance(end, bool) or not isinstance(end, int):
        end = start
    start = max(0, min(start, len(value)))
    end = max(start, min(end, len(value)))
    box.value = value[:start] + char + value[end:]
    caret = start + len(char)
    try:
        box.setSelectionRange(caret, caret)
        box.focus()
    except Exception:
        pass  # a missing caret API must never lose the letter
    return box.value


def _make_accent_handler(input_id, char):
    def handler(event=None):
        insert_accent(input_id, char)
    return handler


def _keep_input_focus(event=None):
    if event is not None and hasattr(event, "preventDefault"):
        event.preventDefault()


def build_accent_bars():
    for bar_id, input_id in ACCENT_BARS.items():
        bar = _element(bar_id)
        bar.innerHTML = ""
        for char, name in ACCENT_CHARS:
            key = document.createElement("button")
            key.type = "button"
            key.className = "secondary accent-key"
            key.innerText = char
            key.setAttribute("aria-label", f"{char}, {name}")
            key.setAttribute("tabindex", "-1")
            key.title = name
            key.addEventListener("mousedown", create_proxy(_keep_input_focus))
            key.addEventListener("click", create_proxy(_make_accent_handler(input_id, char)))
            bar.appendChild(key)


def render_accent_bars():
    optional = not accent_sensitive_now()
    for bar_id, input_id in ACCENT_BARS.items():
        bar = _element(bar_id)
        bar.hidden = bool(_element(input_id).hidden)
        bar.className = "accent-bar accent-bar--optional" if optional else "accent-bar"
        bar.title = ACCENT_BAR_OPTIONAL_NOTE if optional else ""
