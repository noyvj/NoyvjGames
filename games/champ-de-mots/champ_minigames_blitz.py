"""Greetings & Basics Blitz (weeks 1-11): a 60-second rapid-fire translation game with lives and a combo.
Part of the split of the old single-file minigames.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from pyodide.ffi import create_proxy

import champ_minigames_runstate as runstate
from champ_minigames_rules import (
    BLITZ_BASE_POINTS, BLITZ_COMBO_BONUS_PER_STEP, BLITZ_COMBO_STEP, BLITZ_DURATION_SECONDS,
    BLITZ_MAX_COMBO_STEPS, BLITZ_STARTING_LIVES,
)
from champ_minigames_core import (
    DIFFICULTY_LABELS, _build_answer_area, _check, _credit, _element, _lock_reason, _range_fully_unlocked,
    _record, _render_difficulty, _reset_credit, _setup_difficulty, _unlocked_range_plots, _with_growth,
    answer_note, context_line, difficulty_points, get_difficulty, plot_label, waters_text,
)


# render() is defined in champ_minigames_registry, which comes later in the module list; that module puts it here when
# it loads (see the end of champ_minigames_registry.py). Calls below find it at run time.
render = None


# ===========================================================================
# Milestone 27 — "Greetings & Basics Blitz" (sequence 1-11)
# ===========================================================================
#
# FREN151 Ch.1-4: greetings, family, description -- the catalog's permanently
# -open "catch-up zone" (Milestone 6), so this minigame's range is always
# playable in practice, but the lock-check machinery still runs uniformly
# (documentation/consistency, and it's ready the day that ever changes).
#
# A 60-second beat-the-clock rapid-fire vocab match: a continuous stream of
# translation prompts, reusing generate_question()'s existing FR-EN/EN-FR
# (and phonetic/grammar-example) choice generation rather than reinventing
# distractor logic, restricted to *choice*-mode "translate" variants only --
# no typed answers here, since typing is the wrong shape for "rapid-fire".
#
# **3 lives, not a time penalty** (a deliberate choice the brief left open):
# a time penalty would compound the pressure of an already-ticking clock --
# every wrong answer would shrink the one resource the whole game is about,
# which reads as punishing in exactly the way this game's wellbeing stance
# (§3) tries to avoid even inside an arcade wrapper. Three lives is a fixed,
# legible budget a player can see and plan around independent of the clock,
# and running out reads as "that's the round" rather than "the clock just
# got meaner because you slipped" -- gentler framing for the same underlying
# stakes. See CLAUDE.md's Milestone 27 build note for the fuller reasoning.

BLITZ_LO, BLITZ_HI = 1, 11


# Variant name strings, mirrored from game.py's own V_* constants rather than
# imported (avoids the circular import noted in the module docstring) --
# these are stable string identifiers already returned in every
# generate_question() result's "variant" key, so matching by literal value
# is safe. test_minigames_variant_constants_match_game.py pins them against
# game.py's real constants so a future rename in game.py can't drift here
# unnoticed.
VARIANT_FR_EN_CHOICE = "fr_to_en_choice"
VARIANT_EN_FR_CHOICE = "en_to_fr_choice"
VARIANT_SYMBOL_NAME_CHOICE = "symbol_to_name_choice"
VARIANT_NAME_SYMBOL_CHOICE = "name_to_symbol_choice"
VARIANT_EXAMPLE_FR_EN = "example_fr_to_en"
VARIANT_EXAMPLE_EN_FR = "example_en_to_fr"
VARIANT_BLANK_WORD = "blank_word"
VARIANT_BLANK_ENDING = "blank_ending"
VARIANT_CONJUGATION_SWAP = "conjugation_swap"

BLITZ_TRANSLATE_VARIANTS = {
    VARIANT_FR_EN_CHOICE,
    VARIANT_EN_FR_CHOICE,
    VARIANT_SYMBOL_NAME_CHOICE,
    VARIANT_NAME_SYMBOL_CHOICE,
    VARIANT_EXAMPLE_FR_EN,
    VARIANT_EXAMPLE_EN_FR,
}

BLITZ_END_TIME = "time"
BLITZ_END_LIVES = "lives"
# Slower / Normal / Faster: how long the run lasts and how many lives you get.
BLITZ_DIFFICULTY = {
    "slower": {"seconds": 90, "lives": 5},
    "normal": {"seconds": BLITZ_DURATION_SECONDS, "lives": BLITZ_STARTING_LIVES},
    "faster": {"seconds": 45, "lives": 2},
}


blitz_choice_proxies = []


BLITZ_RNG = random.Random()


def _blitz_params():
    return BLITZ_DIFFICULTY[get_difficulty("blitz")]


def _blitz_describe(level):
    p = BLITZ_DIFFICULTY[level]
    return f"{DIFFICULTY_LABELS[level]}: {p['seconds']} seconds and {p['lives']} lives."


def _destroy_blitz_choice_proxies():
    for proxy in blitz_choice_proxies:
        proxy.destroy()
    blitz_choice_proxies.clear()


def blitz_available():
    """Deliberately cheap: it does *not* force the full candidate-pool scan
    below. Measured cost of doing so: calling variants_for() (cold cache)
    across every one of range 1-11's ~500 plots on *every* passive render()
    -- including render() calls this test suite's own game_env fixture
    triggers on every single test's module load -- turned into a real
    slowdown (roughly 6x the whole suite's runtime) for a button's disabled
    state that only ever needs a yes/no. Rows 1-11 realistically always
    offer at least one translate-capable vocab plot, so the row-unlock
    check alone is a safe, fast proxy for "is there anything to play" --
    the real candidate list is still computed (once, then cached) the
    moment a round actually starts, in _blitz_candidate_plots() below."""
    return _range_fully_unlocked(BLITZ_LO, BLITZ_HI)


def blitz_lock_reason():
    return None if _range_fully_unlocked(BLITZ_LO, BLITZ_HI) else _lock_reason(BLITZ_HI)


def _blitz_candidate_plots():
    """Computed once per session (this module's own lifetime -- a fresh
    farm/fresh module in the test harness naturally gets a fresh cache) and
    memoized, since the *set* of plots capable of a translate variant is an
    intrinsic catalog property that doesn't change as the farm grows (see
    blitz_available()'s note on why this must stay lazy, never eager)."""
    if runstate._blitz_candidates_cache is None:
        runstate._blitz_candidates_cache = [
            p
            for p in _unlocked_range_plots(BLITZ_LO, BLITZ_HI)
            if any(v in BLITZ_TRANSLATE_VARIANTS for v in runstate._variants_for(p))
        ]
    return runstate._blitz_candidates_cache


def _blitz_multiplier(combo):
    steps = min(combo // BLITZ_COMBO_STEP, BLITZ_MAX_COMBO_STEPS)
    return 1.0 + steps * BLITZ_COMBO_BONUS_PER_STEP


def _roll_blitz_question():
    candidates = _blitz_candidate_plots()
    plot = BLITZ_RNG.choice(candidates)
    variants = [v for v in runstate._variants_for(plot) if v in BLITZ_TRANSLATE_VARIANTS]
    variant = BLITZ_RNG.choice(variants)
    runstate.blitz_question = runstate._generate_question(plot, BLITZ_RNG, variant=variant)


def start_blitz(event=None):
    # blitz_available() is a cheap row-unlock-only proxy (see its own
    # docstring); the real candidate pool is only actually computed here,
    # so this is also where an edge case with genuinely zero eligible plots
    # (never observed in practice, but not provably impossible) is caught
    # rather than crashing on BLITZ_RNG.choice([]).
    if not blitz_available() or not _blitz_candidate_plots():
        return None
    runstate.blitz_open = True
    runstate.blitz_active = True
    runstate.blitz_score = 0
    runstate.blitz_lives = _blitz_params()["lives"]
    runstate.blitz_combo = 0
    runstate.blitz_time_remaining = _blitz_params()["seconds"]
    runstate.blitz_end_reason = None
    runstate.blitz_note = ""
    _reset_credit("blitz")
    _roll_blitz_question()
    render()
    return runstate.blitz_question


def _end_blitz(reason):
    runstate.blitz_active = False
    runstate.blitz_end_reason = reason
    runstate.blitz_best_score = max(runstate.blitz_best_score, runstate.blitz_score)
    runstate.blitz_question = None


def submit_blitz_choice(given):
    if not runstate.blitz_active or runstate.blitz_question is None:
        return None
    correct = _check(runstate.blitz_question, given)
    _record("blitz", correct)
    label = plot_label(runstate.blitz_question["plot_id"])
    if correct:
        kind = _credit(runstate.blitz_question, "blitz")
        runstate.blitz_note = answer_note(label, True, [kind])
        runstate.blitz_combo += 1
        runstate.blitz_score += difficulty_points("blitz", round(BLITZ_BASE_POINTS * _blitz_multiplier(runstate.blitz_combo)))
    else:
        runstate.blitz_note = answer_note(label, False, [])
        runstate.blitz_combo = 0
        runstate.blitz_lives -= 1
    if runstate.blitz_lives <= 0:
        _end_blitz(BLITZ_END_LIVES)
    else:
        _roll_blitz_question()
    render()
    return correct


def blitz_tick(event=None):
    """JS-driven countdown tick -- see the module docstring's "the timer is
    JS-driven, not a Python clock" note. Called once per second from
    index.html's own setInterval while the Blitz panel is open; a no-op
    whenever a run isn't actually active, so JS doesn't need to know that
    state itself."""
    if not runstate.blitz_active:
        return None
    runstate.blitz_time_remaining -= 1
    if runstate.blitz_time_remaining <= 0:
        runstate.blitz_time_remaining = 0
        _end_blitz(BLITZ_END_TIME)
    render()
    return runstate.blitz_time_remaining


def close_blitz(event=None):
    runstate.blitz_open = False
    runstate.blitz_active = False
    runstate.blitz_question = None
    runstate.blitz_end_reason = None
    runstate.blitz_note = ""
    render()


def on_toggle_blitz(event=None):
    if runstate.blitz_open:
        close_blitz()
    else:
        runstate.blitz_open = True
        render()


def _make_blitz_choice_handler(choice):
    def handler(event=None):
        submit_blitz_choice(choice)
    return handler


BLITZ_SUMMARY_MESSAGE = "Time's up! Score: {score} (best this session: {best})."
BLITZ_LIVES_MESSAGE = "Out of lives for this round. Score: {score} (best this session: {best})."


def render_blitz():
    toggle = _element("blitz-toggle-button")
    panel = _element("blitz-panel")
    choices_box = _element("blitz-choices")

    available = blitz_available()
    toggle.disabled = not runstate.blitz_open and not available
    toggle.innerText = "Close Blitz" if runstate.blitz_open else "⚡ Greetings & Basics Blitz"

    if not runstate.blitz_open:
        panel.hidden = True
        _destroy_blitz_choice_proxies()
        choices_box.innerHTML = ""
        runstate._blitz_rendered_question = None
        return

    panel.hidden = False
    lock_message = _element("blitz-lock-message")
    reason = blitz_lock_reason()
    lock_message.hidden = reason is None
    lock_message.innerText = reason or ""

    start_button = _element("blitz-start-button")
    summary = _element("blitz-summary")

    _render_difficulty("blitz", runstate.blitz_active, _blitz_describe)
    _element("blitz-time-display").innerText = f"{runstate.blitz_time_remaining}s"
    _element("blitz-lives-display").innerText = "❤" * max(runstate.blitz_lives, 0) or "0 lives"
    _element("blitz-score-display").innerText = f"Score: {runstate.blitz_score}"
    _element("blitz-combo-display").innerText = (
        f"Combo x{_blitz_multiplier(runstate.blitz_combo):.1f}" if runstate.blitz_combo >= BLITZ_COMBO_STEP else ""
    )

    if not runstate.blitz_active:
        _destroy_blitz_choice_proxies()
        choices_box.innerHTML = ""
        runstate._blitz_rendered_question = None
        _element("blitz-context").innerText = ""
        _element("blitz-prompt").innerText = ""
        _element("blitz-feedback").innerText = ""
        _element("blitz-waters").innerText = ""
        start_button.hidden = reason is not None
        start_button.innerText = "Play again" if runstate.blitz_end_reason is not None else f"Start ({_blitz_params()['seconds']}s)"
        summary.hidden = runstate.blitz_end_reason is None
        if runstate.blitz_end_reason == BLITZ_END_TIME:
            summary.innerText = _with_growth(BLITZ_SUMMARY_MESSAGE.format(score=runstate.blitz_score, best=runstate.blitz_best_score), "blitz")
        elif runstate.blitz_end_reason == BLITZ_END_LIVES:
            summary.innerText = _with_growth(BLITZ_LIVES_MESSAGE.format(score=runstate.blitz_score, best=runstate.blitz_best_score), "blitz")
        return

    start_button.hidden = True
    summary.hidden = True

    # The choice buttons (and their click proxies) are only rebuilt when the
    # question itself actually changed. blitz_tick() re-renders once a
    # second purely to refresh the timer display -- destroying and
    # recreating live buttons/proxies on every one of those ticks (found
    # live in a real browser: an in-flight click could land on a button
    # that had just been replaced, or a proxy that had just been destroyed)
    # is exactly the kind of flakiness a fast-paced game can least afford.
    if runstate.blitz_question is not runstate._blitz_rendered_question:
        _destroy_blitz_choice_proxies()
        _element("blitz-context").innerText = context_line(runstate.blitz_question)
        _element("blitz-prompt").innerText = runstate.blitz_question["prompt"]
        _element("blitz-feedback").innerText = runstate.blitz_note
        _element("blitz-waters").innerText = waters_text([plot_label(runstate.blitz_question["plot_id"])])
        _build_answer_area("blitz", runstate.blitz_question, choices_box, blitz_choice_proxies, submit_blitz_choice)
        runstate._blitz_rendered_question = runstate.blitz_question


def _setup_blitz():
    _setup_difficulty("blitz")
    _element("blitz-toggle-button").addEventListener("click", create_proxy(on_toggle_blitz))
    _element("blitz-start-button").addEventListener("click", create_proxy(start_blitz))
    _element("blitz-close-button").addEventListener("click", create_proxy(close_blitz))
