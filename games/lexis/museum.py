"""Lexis -- Glyph Museum: a collector's wall showing all signs and filling in meanings as they are confirmed."""

from pulse import PULSE
from compound import COMPONENTS
from bridge import MARKERS


def get_museum_data(state):
    """Return a list of museum entries for the given game state."""
    items = []

    # Planet 1: Pulse words
    for word in PULSE.words:
        guess = state.notebook.entries.get(word.form) or ""
        confirmed = guess == word.meaning
        items.append({
            "planet": "pulse",
            "form": word.form,
            "meaning": word.meaning,
            "confirmed": confirmed,
        })

    # Planet 2: Compound components
    for letter, (meaning, slot) in COMPONENTS.items():
        guess = state.compound_notebook.entries.get(letter) or ""
        confirmed = guess == meaning
        items.append({
            "planet": "compound",
            "form": letter,
            "meaning": meaning,
            "confirmed": confirmed,
        })

    # Planet 3: Bridge markers
    for letter, meaning in MARKERS.items():
        guess = state.bridge_notebook.entries.get(letter) or ""
        confirmed = guess == meaning
        items.append({
            "planet": "bridge",
            "form": letter,
            "meaning": meaning,
            "confirmed": confirmed,
        })

    return items
