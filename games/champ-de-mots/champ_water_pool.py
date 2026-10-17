"""Which plots each 'Water options' choice can water right now (next, week, topic, wilting, multiple choice, typed, listening)
and the constants those sessions use.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import champ_runstate as runstate
from champ_model import is_due, is_wilting, state
from champ_qbuild import V_FR_EN_CHOICE, V_SYMBOL_NAME_CHOICE, variants_for
from champ_questions import TYPED_BLANK_VARIANTS, TYPED_VARIANTS
from champ_util import speech_available
from champ_watering import can_water_now


# ===========================================================================
# Water options (2026-10-08): more ways to water than "Water the next plot"
# ===========================================================================
# A short chooser (the "Water options" button next to "Water the next plot")
# lists every way to pick what to water, each with how many plots it can water
# RIGHT NOW (a plot that has already had its full watering today is not
# counted: it can only be nudged). Every option uses the one watering rule
# (water_plot): the first correct answer for a plot each in-game day waters it,
# a later one nudges it, a wrong answer changes nothing.
#
#   Water next plot            the farm's own most-overdue-first button
#   Water a chosen week        any one row of the farm
#   Water by topic             vocabulary / phrases / grammar / pronunciation
#   Water the wilting plots    the plots that are most overdue, longest first
#   Quick multiple-choice      5 plots, multiple choice only, low effort
#   Typing water               5 plots, typed answers only
#   Listening water            5 plots, hear the French and pick the English
#   Water by minigame          each arcade game, saying which plots it waters
#
# The sessions run in the Review panel (same grading, report buttons and
# end-of-session "watered N plots, nudged M" line).
WATER_ROW_MODE = "waterrow"
WATER_TOPIC_MODE = "watertopic"
WATER_WILTING_MODE = "waterwilting"
WATER_MC_MODE = "watermc"
WATER_TYPED_MODE = "watertyped"
WATER_LISTEN_MODE = "waterlisten"
WATER_MODES = (
    WATER_ROW_MODE, WATER_TOPIC_MODE, WATER_WILTING_MODE, WATER_MC_MODE, WATER_TYPED_MODE, WATER_LISTEN_MODE,
)
WATER_MODE_FORMAT = {WATER_MC_MODE: "choice", WATER_TYPED_MODE: "typed", WATER_LISTEN_MODE: "choice"}
WATER_LISTEN_VARIANTS = (V_FR_EN_CHOICE, V_SYMBOL_NAME_CHOICE)
WATER_SESSION_MAX = 10
WATER_QUICK_COUNT = 5
WATER_TOPICS = (
    ("vocab", "Vocabulary"),
    ("phrase", "Phrases"),
    ("grammar", "Grammar"),
    ("pronunciation", "Pronunciation (letters and accents)"),
)
WATER_EMPTY_MESSAGE = (
    "Nothing in that group can be watered right now: every plot in it has already been watered "
    "today (or there is nothing of that kind). Move the day on, or try another option."
)
LISTEN_HIDDEN_PROMPT = "🔊 Listen, then pick what it means."


water_option_proxies = []


def _water_order(plots):
    """Most overdue watered plots first, then plots never watered, then watered
    plots that are not due yet; ties keep farm order."""
    day = state.current_day

    def key(plot):
        if plot.next_due is None:
            return (1, 0)
        if plot.next_due <= day:
            return (0, plot.next_due)
        return (2, plot.next_due)

    return sorted(plots, key=key)


def _is_typed_capable(plot):
    return any(v in TYPED_VARIANTS or v in TYPED_BLANK_VARIANTS for v in variants_for(plot))


def _is_listen_capable(plot):
    return plot.topic_type != "grammar" and any(v in WATER_LISTEN_VARIANTS for v in variants_for(plot))


def _topic_match(plot, topic):
    if topic == "pronunciation":
        return plot.topic_type == "phonetic"
    return plot.topic_type == topic


def water_pool(kind, arg=None):
    """Every plot an option could water right now (not yet watered today), in
    the order a session would ask about them. `kind` is "next", "row",
    "topic", "wilting", "mc", "typed" or "listen"."""
    day = state.current_day
    plots = [p for p in state.available_plots() if can_water_now(p)]
    if kind == "next":
        return _water_order([p for p in plots if is_due(p, day)])
    if kind == "row":
        try:
            sequence = int(arg)
        except (TypeError, ValueError):
            return []
        return _water_order([p for p in plots if p.sequence == sequence])
    if kind == "topic":
        return _water_order([p for p in plots if _topic_match(p, arg)])
    if kind == "wilting":
        return sorted((p for p in plots if is_wilting(p, day)), key=lambda p: p.next_due)
    if kind == "mc":
        return _water_order(plots)
    if kind == "typed":
        return _water_order([p for p in plots if _is_typed_capable(p)])
    if kind == "listen":
        return _water_order([p for p in plots if _is_listen_capable(p)])
    return []


_WATER_MODE_KIND = {
    WATER_ROW_MODE: "row",
    WATER_TOPIC_MODE: "topic",
    WATER_WILTING_MODE: "wilting",
    WATER_MC_MODE: "mc",
    WATER_TYPED_MODE: "typed",
    WATER_LISTEN_MODE: "listen",
}
_WATER_MODE_LIMIT = {
    WATER_ROW_MODE: WATER_SESSION_MAX,
    WATER_TOPIC_MODE: WATER_SESSION_MAX,
    WATER_WILTING_MODE: WATER_SESSION_MAX,
    WATER_MC_MODE: WATER_QUICK_COUNT,
    WATER_TYPED_MODE: WATER_QUICK_COUNT,
    WATER_LISTEN_MODE: WATER_QUICK_COUNT,
}


def water_session_plots(mode, arg=None):
    """The plots one chooser session asks about (capped: 10, or 5 for the
    quick options)."""
    return water_pool(_WATER_MODE_KIND[mode], arg)[: _WATER_MODE_LIMIT[mode]]


def water_option_counts():
    """How many plots each option can water right now (uncapped)."""
    return {
        "next": len(water_pool("next")),
        "row": len(water_pool("row", runstate.water_row_choice)),
        "topic": len(water_pool("topic", runstate.water_topic_choice)),
        "wilting": len(water_pool("wilting")),
        "mc": len(water_pool("mc")),
        "typed": len(water_pool("typed")),
        "listen": len(water_pool("listen")) if speech_available() else 0,
    }
