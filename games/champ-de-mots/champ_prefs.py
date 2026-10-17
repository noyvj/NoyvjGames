"""The two settings toggles: accent sensitivity and 'Always multiple choice' (plus the plain-words format schedule).
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import champ_runstate as runstate
from champ_util import _element, pref_set


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


def on_toggle_accent_sensitivity(event=None):
    """§14.2: one global toggle, default ON. Flips on every click rather than
    reading a `checked` property, so the fake-DOM harness (which has no real
    checkbox semantics) can drive it the same way a real click would."""
    runstate.ACCENT_SENSITIVE = not runstate.ACCENT_SENSITIVE
    _element("accent-toggle-checkbox").checked = runstate.ACCENT_SENSITIVE
    render()


PREF_ALWAYS_MC = "champ-always-multiple-choice"


def on_toggle_always_mc(event=None):
    """Progressive format off-switch: with this on, every question is multiple
    choice wherever the plot has one (see question_format_percent())."""
    runstate.ALWAYS_MULTIPLE_CHOICE = not runstate.ALWAYS_MULTIPLE_CHOICE
    _element("always-mc-checkbox").checked = runstate.ALWAYS_MULTIPLE_CHOICE
    pref_set(PREF_ALWAYS_MC, "1" if runstate.ALWAYS_MULTIPLE_CHOICE else "0")
    render()


def format_schedule_lines():
    """The plain-words schedule shown in Settings."""
    return [
        "Seed (never watered): multiple choice only.",
        "Sprout: about 1 question in 5 is typed. Budding: about 2 in 5.",
        "Blooming: about 7 in 10. Automated: about 9 in 10.",
        "A longer run of correct answers and a higher ease nudge the share up; a plot you just missed leans back toward multiple choice.",
    ]
