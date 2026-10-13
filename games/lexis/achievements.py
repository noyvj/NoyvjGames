"""Lexis -- achievements (the hub-wide framework: a static manifest `achievements.json` plus
`achievements_earned` in the save). Everything is computed from the state, never stored separately, so a
loaded save and a played one can never disagree. All are reachable without luck and none is hidden
(easy to 100%)."""

from bridge import MARKERS
from compound import COMPONENTS

ACHIEVEMENTS = (
    ("first_signal", "First Signal", "Send a signal the station understands.", "A spark in the dark, the first hello."),
    ("lamp_keeper", "Lamp Keeper", "Light all seven lamps on planet 1.", "Seven eyes open, the station wakes."),
    ("first_words", "First Words", "Write your first notebook entry.", "The first guess takes root in silent soil."),
    ("learning_from_static", "Learning From Static", "Send a signal the station cannot understand, and keep going.", "When words turn to noise, patience speaks louder."),
    ("sharp_ear", "Sharp Ear", "Check three or more notebook entries and have every one right.", "Three guesses, one truth, and a quiet mind."),
    ("first_contact", "First Contact", "Make contact with planet 1.", "The bridge is built, the voice is heard."),
    ("unseen_sign", "Never Shown", "Send a sign on planet 2 that no transmission ever showed you.", "A shape never shown, yet understood."),
    ("second_contact", "Second Contact", "Make contact with planet 2.", "Two worlds speak, the ship listens."),
    ("full_glossary", "Full Glossary", "Have every part of planet 2's signs written down correctly.", "Every part named, the puzzle completes."),
    ("patient_listener", "Patient Listener", "Receive every transmission on both planets.", "Six scenes and four more, all received."),
    ("third_contact", "Third Contact", "Make contact with planet 3.", "Three planets answered, the journey deepens."),
    ("markers_known", "Small Signs", "Have all three of planet 3's small signs written down correctly.", "Three small signs, three big changes."),
)

SCENES_PULSE = 6
SCENES_COMPOUND = 4
SHOWN_GLYPHS = {"ko", "mo", "mu", "to"}


def earned(state, station, tray):
    """The ids earned right now, in manifest order."""
    got = set()
    if state.spoken or state.compound_spoken or state.bridge_spoken:
        if state.flags.get("understood"):
            got.add("first_signal")
    if station.lamps == 7 or state.flags.get("all_lamps"):
        got.add("lamp_keeper")
    if state.notebook.entries or state.compound_notebook.entries:
        got.add("first_words")
    if state.flags.get("misunderstood"):
        got.add("learning_from_static")
    if state.flags.get("perfect_check"):
        got.add("sharp_ear")
    if state.contact.get("pulse"):
        got.add("first_contact")
    if state.flags.get("understood_unseen"):        # a one-way flag: the spoken list is a rolling window
        got.add("unseen_sign")
    if state.contact.get("compound"):
        got.add("second_contact")
    if all(state.compound_notebook.entries.get(code) == meaning for code, (meaning, _s) in COMPONENTS.items()):
        got.add("full_glossary")
    if state.contact.get("bridge"):
        got.add("third_contact")
    if all(state.bridge_notebook.entries.get(letter) == role for letter, role in MARKERS.items()):
        got.add("markers_known")
    if state.scenes_seen >= SCENES_PULSE and state.compound_scenes_seen >= SCENES_COMPOUND:
        got.add("patient_listener")
    return [a[0] for a in ACHIEVEMENTS if a[0] in got]


def view(state, station, tray):
    have = set(earned(state, station, tray))
    return [{"id": i, "label": label, "description": desc, "riddle": riddle, "earned": i in have} for i, label, desc, riddle in ACHIEVEMENTS]
