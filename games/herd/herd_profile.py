"""Beginner / Standard / Expert play styles (F-11) and the next-best-lever hint.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from js import document

import herd_runstate as runstate
from herd_rules import DECOUPLING_MEASURES, MIN_COUPLING_RATIO
from herd_util import _read_local_storage_item


# ---- F-11 Beginner / Standard / Expert profiles ------------------------------------------
# A player's own choice in Settings (localStorage["herd-profile"], never in a save). Beginner adds a
# next-best-lever hint chip; Expert hides the previews, per-lever efficiency lines and the "i" notes
# (settings.js sets html[data-profile], style.css does the hiding). Standard is the game as it was.
PROFILE_KEY = "herd-profile"
PROFILES = ("beginner", "standard", "expert")
HINT_LEVERS = ("feed", "caps", "capture")


def current_profile():
    raw = _read_local_storage_item(PROFILE_KEY)
    return raw if raw in PROFILES else "standard"


def next_lever_hint():
    """A plain suggestion for what to do next. The affordable decoupling lever that saves the most methane per
    fund wins; with none affordable it says to grow or advance. Pure reading: it buys nothing."""
    best = None
    for key in HINT_LEVERS:
        cost = runstate.farm.decoupling_cost(key)
        if runstate.farm.funds < cost or runstate.farm._efficiency_coupling_ratio() <= MIN_COUPLING_RATIO + 1e-9:
            continue
        saved = runstate.farm.methane_saved_by(key)
        if saved <= 0:
            continue
        score = saved / cost
        if best is None or score > best[0]:
            best = (score, key, saved, cost)
    if best is not None:
        _score, key, saved, cost = best
        return (
            f"Suggestion: {DECOUPLING_MEASURES[key]['label']} ({cost:g} funds) would cut about {saved:.2f} "
            "methane per round, the most for the money right now."
        )
    if runstate.farm.herd_size == 0:
        return f"Suggestion: Grow Herd ({runstate.farm.grow_herd_cost():.0f} funds) to start earning."
    if runstate.farm.funds >= runstate.farm.grow_herd_cost():
        return "Suggestion: grow the herd, or press Advance Round to collect this round's income."
    return "Suggestion: press Advance Round to collect this round's income."


def render_profile():
    profile = current_profile()
    hint = document.getElementById("next-lever-hint")
    hint.hidden = profile != "beginner"
    hint.innerText = next_lever_hint() if profile == "beginner" else ""
    document.getElementById("profile-select").value = profile
