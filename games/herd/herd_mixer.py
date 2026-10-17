"""The feed-mixer timing minigame readouts (GF-25).
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from js import document

import herd_runstate as runstate
from herd_rules import MIXER_AUTO_QUALITY, MIXER_BONUS_FRACTION, MIXER_BONUS_MAX, MIXER_PERFECT_QUALITY


def mixer_stats_message():
    if runstate.farm.mixer_blends == 0:
        return "Mixer tally: no blends yet."
    return (
        f"Mixer tally: {runstate.farm.mixer_blends} blend{'s' if runstate.farm.mixer_blends != 1 else ''}, {runstate.farm.mixer_perfects} perfect, "
        f"+{runstate.farm.mixer_bonus_total:.1f} funds earned in total."
    )


def mixer_status_message():
    if runstate.farm.decoupling_investment["feed"] < 1:
        return "The mixer unlocks with your first Feed Additives unit."
    if runstate.farm.mixer_round == runstate.farm.round_number:
        return "You have blended this round. The mixer is ready again after Advance Round."
    return (
        f"Ready: a blend pays up to {runstate.farm.mixer_bonus_for(1.0):.1f} funds now "
        f"({MIXER_BONUS_FRACTION * 100:.0f}% of your funds, at most {MIXER_BONUS_MAX:.0f}). "
        f"Auto-blend pays {runstate.farm.mixer_bonus_for(MIXER_AUTO_QUALITY):.1f}."
    )


def mixer_quality_word(quality):
    if quality >= MIXER_PERFECT_QUALITY:
        return "Perfect blend"
    if quality >= 0.5:
        return "Good blend"
    return "Rough blend"


def mixer_blend(quality, auto=False):
    """Applies a blend and sets the message. Returns the bonus, or None when it was not allowed."""
    bonus = runstate.farm.blend(quality)
    if bonus is None:
        runstate.mixer_message = "No blend right now."
        return None
    word = "Auto-blend" if auto else mixer_quality_word(quality)
    runstate.mixer_message = f"{word}: +{bonus:.1f} funds."
    return bonus


def render_mixer():
    ready = runstate.farm.mixer_available()
    document.getElementById("mixer-start-button").disabled = not ready
    document.getElementById("mixer-auto-button").disabled = not ready
    document.getElementById("mixer-status").innerText = mixer_status_message()
    document.getElementById("mixer-stats").innerText = mixer_stats_message()
    document.getElementById("mixer-note").innerText = runstate.mixer_message
