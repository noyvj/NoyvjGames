"""Verb Racer (weeks 12-15): pick the right verb form to outrun a rival.
Part of the split of the old single-file minigames.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from pyodide.ffi import create_proxy

import champ_minigames_runstate as runstate
from champ_minigames_rules import RACER_RIVAL_TICKS_PER_STEP, RACER_TOTAL_STEPS
from champ_minigames_core import (
    DIFFICULTY_LABELS, _build_answer_area, _check, _credit, _element, _lock_reason, _range_fully_unlocked,
    _record, _render_difficulty, _reset_credit, _setup_difficulty, _unlocked_range_plots, _with_growth,
    answer_note, context_line, get_difficulty, plot_label, waters_text,
)
from champ_minigames_blitz import VARIANT_BLANK_ENDING, VARIANT_BLANK_WORD, VARIANT_CONJUGATION_SWAP


# render() is defined in champ_minigames_registry, which comes later in the module list; that module puts it here when
# it loads (see the end of champ_minigames_registry.py). Calls below find it at run time.
render = None


# ===========================================================================
# Milestone 28 — "Verb Racer" (sequence 12-15)
# ===========================================================================
#
# FREN152 Bridge + Ch.5: numbers/time revision, daily routine, reflexives,
# comparative/superlative -- a grammar-heavy stretch. A lane-race visual:
# pick the correctly conjugated verb form (multiple choice, reusing the
# existing conjugation/blank-word question generation for grammar plots in
# this range -- exactly the same variant-selection bias Grammar Review
# already established, see game.py's own _review_variant_for()) to advance
# one discrete step. A fixed-pace rival advances on its own every few real
# seconds regardless of the player's answers -- not adaptive, not reacting
# to how well the player is doing, just a steady metronome to race against.
#
# **Discrete, step-based movement, not smooth animation** -- a deliberate
# visual-treatment call. A verb-conjugation question is answered in a few
# seconds at most, so a continuously-animated racer would spend almost all
# its time barely moving between one answer and the next; a clean step per
# correct answer reads as immediate, legible progress instead. minigames.css
# still gives the marker a short CSS transition on its `left` position so a
# step doesn't teleport, but the *game logic* here only ever thinks in whole
# steps -- there is no interpolated position anywhere in this file.
#
# A wrong answer doesn't advance the player that turn (per the brief), and
# -- matching Blitz's own "reroll every attempt" call -- a fresh question is
# rolled either way, right or wrong, since retrying the identical prompt
# immediately would be a worse test of recall than a fresh one from the
# same plot pool.

RACER_LO, RACER_HI = 12, 15


# The same non-typed-variant filter Blitz needs, generalized: Racer is
# multiple-choice only ("pick the correctly conjugated verb form"), and a
# grammar plot can also offer a typed variant (V_FR_EN_TYPED etc.) whenever
# its items are short enough to type -- those must never be rolled here.
RACER_TYPED_VARIANTS = {
    "fr_to_en_typed",
    "en_to_fr_typed",
    "symbol_to_name_typed",
    "name_to_symbol_typed",
}
# Grammar Review's own bias (game.py's GRAMMAR_REVIEW_PREFERRED_VARIANTS),
# duplicated for the same circular-import reason as Blitz's variant
# constants above -- "conjugated verb form" is best served by these three
# when a plot can offer one.
RACER_PREFERRED_VARIANTS = {
    VARIANT_CONJUGATION_SWAP,
    VARIANT_BLANK_ENDING,
    VARIANT_BLANK_WORD,
}

# Slower / Normal / Faster: how often the rival steps (real seconds per step).
RACER_DIFFICULTY = {
    "slower": {"rival_ticks": 5},
    "normal": {"rival_ticks": RACER_RIVAL_TICKS_PER_STEP},
    "faster": {"rival_ticks": 2},
}


def _racer_describe(level):
    ticks = RACER_DIFFICULTY[level]["rival_ticks"]
    return f"{DIFFICULTY_LABELS[level]}: the rival takes a step every {ticks} seconds."


RACER_END_PLAYER = "player"  # the player reached the finish line first
RACER_END_RIVAL = "rival"  # the rival did


racer_choice_proxies = []


RACER_RNG = random.Random()


def _destroy_racer_choice_proxies():
    for proxy in racer_choice_proxies:
        proxy.destroy()
    racer_choice_proxies.clear()


def racer_available():
    """Cheap on purpose, same reasoning as blitz_available()'s own note:
    row-unlock state only, never the full candidate-plot scan below."""
    return _range_fully_unlocked(RACER_LO, RACER_HI)


def racer_lock_reason():
    return None if _range_fully_unlocked(RACER_LO, RACER_HI) else _lock_reason(RACER_HI)


def _racer_variant_for(plot):
    """Prefer a conjugation/blank variant when this plot can offer one
    (Grammar Review's own bias, reused); otherwise fall back to any other
    non-typed variant it has (e.g. a grammar plot whose only choice-mode
    variant is a plain example translation). None if it has no eligible
    variant at all (a typed-only plot, or one with nothing to offer)."""
    preferred = [v for v in runstate._variants_for(plot) if v in RACER_PREFERRED_VARIANTS]
    if preferred:
        return RACER_RNG.choice(preferred)
    fallback = [v for v in runstate._variants_for(plot) if v not in RACER_TYPED_VARIANTS]
    return RACER_RNG.choice(fallback) if fallback else None


def _racer_candidate_plots():
    """Lazy and memoized -- see blitz_available()'s build note on why this
    must never run eagerly on a passive render()."""
    if runstate._racer_candidates_cache is None:
        runstate._racer_candidates_cache = [
            p
            for p in _unlocked_range_plots(RACER_LO, RACER_HI)
            if p.topic_type == "grammar" and _racer_variant_for(p) is not None
        ]
    return runstate._racer_candidates_cache


def _roll_racer_question():
    plot = RACER_RNG.choice(_racer_candidate_plots())
    runstate.racer_question = runstate._generate_question(plot, RACER_RNG, variant=_racer_variant_for(plot))


def start_racer(event=None):
    if not racer_available() or not _racer_candidate_plots():
        return None
    runstate.racer_open = True
    runstate.racer_active = True
    runstate.racer_player_position = 0
    runstate.racer_rival_position = 0
    runstate.racer_tick_count = 0
    runstate.racer_result = None
    runstate.racer_end_reason = None
    runstate.racer_note = ""
    _reset_credit("racer")
    _roll_racer_question()
    render()
    return runstate.racer_question


def _end_racer(reason):
    runstate.racer_active = False
    runstate.racer_end_reason = reason
    runstate.racer_question = None


def submit_racer_choice(given):
    if not runstate.racer_active or runstate.racer_question is None:
        return None
    runstate.racer_result = _check(runstate.racer_question, given)
    _record("racer", runstate.racer_result)
    label = plot_label(runstate.racer_question["plot_id"])
    if runstate.racer_result:
        kind = _credit(runstate.racer_question, "racer")
        runstate.racer_note = answer_note(label, True, [kind])
        runstate.racer_player_position += 1
        if runstate.racer_player_position >= RACER_TOTAL_STEPS:
            _end_racer(RACER_END_PLAYER)
            render()
            return runstate.racer_result
    else:
        runstate.racer_note = answer_note(label, False, [])
    _roll_racer_question()
    render()
    return runstate.racer_result


def racer_tick(event=None):
    """JS-driven: the rival's fixed pace, one step every
    RACER_RIVAL_TICKS_PER_STEP real seconds -- see the module docstring's
    "the timer is JS-driven, not a Python clock" note. A no-op whenever no
    race is active."""
    if not runstate.racer_active:
        return None
    runstate.racer_tick_count += 1
    if runstate.racer_tick_count >= RACER_DIFFICULTY[get_difficulty("racer")]["rival_ticks"]:
        runstate.racer_tick_count = 0
        runstate.racer_rival_position += 1
        if runstate.racer_rival_position >= RACER_TOTAL_STEPS:
            _end_racer(RACER_END_RIVAL)
    render()
    return runstate.racer_rival_position


def close_racer(event=None):
    runstate.racer_note = ""
    runstate.racer_open = False
    runstate.racer_active = False
    runstate.racer_question = None
    runstate.racer_result = None
    runstate.racer_end_reason = None
    render()


def on_toggle_racer(event=None):
    if runstate.racer_open:
        close_racer()
    else:
        runstate.racer_open = True
        render()


def _make_racer_choice_handler(choice):
    def handler(event=None):
        submit_racer_choice(choice)
    return handler


RACER_PLAYER_WIN_MESSAGE = "You crossed the line first! {player} of {total} steps."
RACER_RIVAL_WIN_MESSAGE = "Not this time — the rival crossed first. You reached {player} of {total}."


def _racer_marker_position(position):
    """0-100, how far along the track a marker sits -- discrete steps only
    (see the module note above), read by both the fake-DOM tests and the
    real page's CSS `left` positioning."""
    return round((position / RACER_TOTAL_STEPS) * 100)


def render_racer():
    toggle = _element("racer-toggle-button")
    panel = _element("racer-panel")
    choices_box = _element("racer-choices")

    available = racer_available()
    toggle.disabled = not runstate.racer_open and not available
    toggle.innerText = "Close Verb Racer" if runstate.racer_open else "🏁 Verb Racer"

    if not runstate.racer_open:
        panel.hidden = True
        _destroy_racer_choice_proxies()
        choices_box.innerHTML = ""
        runstate._racer_rendered_question = None
        return

    panel.hidden = False
    lock_message = _element("racer-lock-message")
    reason = racer_lock_reason()
    lock_message.hidden = reason is None
    lock_message.innerText = reason or ""

    start_button = _element("racer-start-button")
    summary = _element("racer-summary")

    _render_difficulty("racer", runstate.racer_active, _racer_describe)
    _element("racer-player-marker").style.left = f"{_racer_marker_position(runstate.racer_player_position)}%"
    _element("racer-rival-marker").style.left = f"{_racer_marker_position(runstate.racer_rival_position)}%"
    _element("racer-progress-display").innerText = (
        f"You: {runstate.racer_player_position} of {RACER_TOTAL_STEPS} · "
        f"Rival: {runstate.racer_rival_position} of {RACER_TOTAL_STEPS}"
    )

    if not runstate.racer_active:
        _destroy_racer_choice_proxies()
        choices_box.innerHTML = ""
        runstate._racer_rendered_question = None
        _element("racer-context").innerText = ""
        _element("racer-prompt").innerText = ""
        _element("racer-feedback").innerText = ""
        _element("racer-waters").innerText = ""
        start_button.hidden = reason is not None
        start_button.innerText = "Race again" if runstate.racer_end_reason is not None else "Start the race"
        summary.hidden = runstate.racer_end_reason is None
        if runstate.racer_end_reason == RACER_END_PLAYER:
            summary.innerText = _with_growth(RACER_PLAYER_WIN_MESSAGE.format(
                player=runstate.racer_player_position, total=RACER_TOTAL_STEPS
            ), "racer")
        elif runstate.racer_end_reason == RACER_END_RIVAL:
            summary.innerText = _with_growth(RACER_RIVAL_WIN_MESSAGE.format(
                player=runstate.racer_player_position, total=RACER_TOTAL_STEPS
            ), "racer")
        return

    start_button.hidden = True
    summary.hidden = True

    if runstate.racer_result is False:
        _element("racer-feedback").innerText = "Not this turn — try the next one. " + runstate.racer_note
    else:
        _element("racer-feedback").innerText = runstate.racer_note

    # Same identity-based rebuild-only-on-change fix Blitz's own live
    # verification found necessary -- see that milestone's build note.
    if runstate.racer_question is not runstate._racer_rendered_question:
        _destroy_racer_choice_proxies()
        _element("racer-context").innerText = context_line(runstate.racer_question)
        _element("racer-prompt").innerText = runstate.racer_question["prompt"]
        _element("racer-waters").innerText = waters_text([plot_label(runstate.racer_question["plot_id"])])
        _build_answer_area("racer", runstate.racer_question, choices_box, racer_choice_proxies, submit_racer_choice)
        runstate._racer_rendered_question = runstate.racer_question


def _setup_racer():
    _setup_difficulty("racer")
    _element("racer-toggle-button").addEventListener("click", create_proxy(on_toggle_racer))
    _element("racer-start-button").addEventListener("click", create_proxy(start_racer))
    _element("racer-close-button").addEventListener("click", create_proxy(close_racer))
