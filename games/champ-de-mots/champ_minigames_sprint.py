"""Passé Composé Sprint (weeks 21-23): a timed fill-the-gap game with lives and a combo.
Part of the split of the old single-file minigames.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from pyodide.ffi import create_proxy

import champ_minigames_runstate as runstate
from champ_minigames_rules import (
    SPRINT_BASE_POINTS, SPRINT_COMBO_BONUS_PER_STEP, SPRINT_COMBO_STEP, SPRINT_DURATION_SECONDS,
    SPRINT_MAX_COMBO_STEPS, SPRINT_STARTING_LIVES,
)
from champ_minigames_core import (
    DIFFICULTY_LABELS, _build_answer_area, _check, _credit, _element, _lock_reason, _range_fully_unlocked,
    _record, _render_difficulty, _reset_credit, _setup_difficulty, _unlocked_range_plots, _with_growth,
    answer_note, context_line, difficulty_points, get_difficulty, plot_label, waters_text,
)
from champ_minigames_blitz import VARIANT_BLANK_WORD, VARIANT_CONJUGATION_SWAP
from champ_minigames_cafe import CAFE_PASSE_COMPOSE_TOPIC_IDS


# render() is defined in champ_minigames_registry, which comes later in the module list; that module puts it here when
# it loads (see the end of champ_minigames_registry.py). Calls below find it at run time.
render = None


# ===========================================================================
# L1 -- "Passé Composé Sprint" (sequence 21-23): the fifth arcade minigame
# ===========================================================================
#
# Every sequence already has an arcade home (Blitz 1-11, Racer 12-15,
# Boutique 16-18, Cafe Rush 19-23), so this one is not a new range but a new
# shape for the hardest stretch: the same 60-second, three-lives, combo-
# multiplier rapid-fire as Blitz, but drawing ONLY on the passe compose
# grammar topics (regular avoir verbs, time-marker adverbs, irregular
# participles, etre verbs, reflexives) and only their fill-in-the-blank and
# conjugation-swap prompts, so it drills the tense rather than vocabulary.
# Built as a deliberate parallel of the Blitz block above: same lock rule (the
# whole range must be unlocked), same JS-driven one-second tick, same "only
# rebuild the buttons when the question changed" render guard. Every answer
# feeds the practice ledger as "sprint", so it visibly counts toward the
# headline practice score like every other minigame (the Z-extra principle).

SPRINT_LO, SPRINT_HI = 21, 23


SPRINT_VARIANTS = {VARIANT_BLANK_WORD, VARIANT_CONJUGATION_SWAP}

SPRINT_END_TIME = "time"
SPRINT_END_LIVES = "lives"
SPRINT_DIFFICULTY = {
    "slower": {"seconds": 90, "lives": 5},
    "normal": {"seconds": SPRINT_DURATION_SECONDS, "lives": SPRINT_STARTING_LIVES},
    "faster": {"seconds": 45, "lives": 2},
}


sprint_choice_proxies = []


SPRINT_RNG = random.Random()


def _sprint_params():
    return SPRINT_DIFFICULTY[get_difficulty("sprint")]


def _sprint_describe(level):
    p = SPRINT_DIFFICULTY[level]
    return f"{DIFFICULTY_LABELS[level]}: {p['seconds']} seconds and {p['lives']} lives."


def _destroy_sprint_choice_proxies():
    for proxy in sprint_choice_proxies:
        proxy.destroy()
    sprint_choice_proxies.clear()


def sprint_available():
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
    moment a round actually starts, in _sprint_candidate_plots() below."""
    return _range_fully_unlocked(SPRINT_LO, SPRINT_HI)


def sprint_lock_reason():
    return None if _range_fully_unlocked(SPRINT_LO, SPRINT_HI) else _lock_reason(SPRINT_HI)


def _sprint_candidate_plots():
    """Computed once per session (this module's own lifetime -- a fresh
    farm/fresh module in the test harness naturally gets a fresh cache) and
    memoized, since the *set* of plots capable of a translate variant is an
    intrinsic catalog property that doesn't change as the farm grows (see
    sprint_available()'s note on why this must stay lazy, never eager)."""
    if runstate._sprint_candidates_cache is None:
        runstate._sprint_candidates_cache = [
            p
            for p in _unlocked_range_plots(SPRINT_LO, SPRINT_HI)
            if p.topic_id in CAFE_PASSE_COMPOSE_TOPIC_IDS and any(v in SPRINT_VARIANTS for v in runstate._variants_for(p))
        ]
    return runstate._sprint_candidates_cache


def _sprint_multiplier(combo):
    steps = min(combo // SPRINT_COMBO_STEP, SPRINT_MAX_COMBO_STEPS)
    return 1.0 + steps * SPRINT_COMBO_BONUS_PER_STEP


def _roll_sprint_question():
    candidates = _sprint_candidate_plots()
    plot = SPRINT_RNG.choice(candidates)
    variants = [v for v in runstate._variants_for(plot) if v in SPRINT_VARIANTS]
    variant = SPRINT_RNG.choice(variants)
    runstate.sprint_question = runstate._generate_question(plot, SPRINT_RNG, variant=variant)


def start_sprint(event=None):
    # sprint_available() is a cheap row-unlock-only proxy (see its own
    # docstring); the real candidate pool is only actually computed here,
    # so this is also where an edge case with genuinely zero eligible plots
    # (never observed in practice, but not provably impossible) is caught
    # rather than crashing on SPRINT_RNG.choice([]).
    if not sprint_available() or not _sprint_candidate_plots():
        return None
    runstate.sprint_open = True
    runstate.sprint_active = True
    runstate.sprint_score = 0
    runstate.sprint_lives = _sprint_params()["lives"]
    runstate.sprint_combo = 0
    runstate.sprint_time_remaining = _sprint_params()["seconds"]
    runstate.sprint_end_reason = None
    runstate.sprint_note = ""
    _reset_credit("sprint")
    _roll_sprint_question()
    render()
    return runstate.sprint_question


def _end_sprint(reason):
    runstate.sprint_active = False
    runstate.sprint_end_reason = reason
    runstate.sprint_best_score = max(runstate.sprint_best_score, runstate.sprint_score)
    runstate.sprint_question = None


def submit_sprint_choice(given):
    if not runstate.sprint_active or runstate.sprint_question is None:
        return None
    correct = _check(runstate.sprint_question, given)
    _record("sprint", correct)
    label = plot_label(runstate.sprint_question["plot_id"])
    if correct:
        kind = _credit(runstate.sprint_question, "sprint")
        runstate.sprint_note = answer_note(label, True, [kind])
        runstate.sprint_combo += 1
        runstate.sprint_score += difficulty_points("sprint", round(SPRINT_BASE_POINTS * _sprint_multiplier(runstate.sprint_combo)))
    else:
        runstate.sprint_note = answer_note(label, False, [])
        runstate.sprint_combo = 0
        runstate.sprint_lives -= 1
    if runstate.sprint_lives <= 0:
        _end_sprint(SPRINT_END_LIVES)
    else:
        _roll_sprint_question()
    render()
    return correct


def sprint_tick(event=None):
    """JS-driven countdown tick -- see the module docstring's "the timer is
    JS-driven, not a Python clock" note. Called once per second from
    index.html's own setInterval while the Sprint panel is open; a no-op
    whenever a run isn't actually active, so JS doesn't need to know that
    state itself."""
    if not runstate.sprint_active:
        return None
    runstate.sprint_time_remaining -= 1
    if runstate.sprint_time_remaining <= 0:
        runstate.sprint_time_remaining = 0
        _end_sprint(SPRINT_END_TIME)
    render()
    return runstate.sprint_time_remaining


def close_sprint(event=None):
    runstate.sprint_note = ""
    runstate.sprint_open = False
    runstate.sprint_active = False
    runstate.sprint_question = None
    runstate.sprint_end_reason = None
    render()


def on_toggle_sprint(event=None):
    if runstate.sprint_open:
        close_sprint()
    else:
        runstate.sprint_open = True
        render()


def _make_sprint_choice_handler(choice):
    def handler(event=None):
        submit_sprint_choice(choice)
    return handler


SPRINT_SUMMARY_MESSAGE = "Time's up! Score: {score} (best this session: {best})."
SPRINT_LIVES_MESSAGE = "Out of lives for this round. Score: {score} (best this session: {best})."


def render_sprint():
    toggle = _element("sprint-toggle-button")
    panel = _element("sprint-panel")
    choices_box = _element("sprint-choices")

    available = sprint_available()
    toggle.disabled = not runstate.sprint_open and not available
    toggle.innerText = "Close Sprint" if runstate.sprint_open else "⏪ Passé Composé Sprint"

    if not runstate.sprint_open:
        panel.hidden = True
        _destroy_sprint_choice_proxies()
        choices_box.innerHTML = ""
        runstate._sprint_rendered_question = None
        return

    panel.hidden = False
    lock_message = _element("sprint-lock-message")
    reason = sprint_lock_reason()
    lock_message.hidden = reason is None
    lock_message.innerText = reason or ""

    start_button = _element("sprint-start-button")
    summary = _element("sprint-summary")

    _render_difficulty("sprint", runstate.sprint_active, _sprint_describe)
    _element("sprint-time-display").innerText = f"{runstate.sprint_time_remaining}s"
    _element("sprint-lives-display").innerText = "❤" * max(runstate.sprint_lives, 0) or "0 lives"
    _element("sprint-score-display").innerText = f"Score: {runstate.sprint_score}"
    _element("sprint-combo-display").innerText = (
        f"Combo x{_sprint_multiplier(runstate.sprint_combo):.1f}" if runstate.sprint_combo >= SPRINT_COMBO_STEP else ""
    )

    if not runstate.sprint_active:
        _destroy_sprint_choice_proxies()
        choices_box.innerHTML = ""
        runstate._sprint_rendered_question = None
        _element("sprint-context").innerText = ""
        _element("sprint-prompt").innerText = ""
        _element("sprint-feedback").innerText = ""
        _element("sprint-waters").innerText = ""
        start_button.hidden = reason is not None
        start_button.innerText = "Play again" if runstate.sprint_end_reason is not None else f"Start ({_sprint_params()['seconds']}s)"
        summary.hidden = runstate.sprint_end_reason is None
        if runstate.sprint_end_reason == SPRINT_END_TIME:
            summary.innerText = _with_growth(SPRINT_SUMMARY_MESSAGE.format(score=runstate.sprint_score, best=runstate.sprint_best_score), "sprint")
        elif runstate.sprint_end_reason == SPRINT_END_LIVES:
            summary.innerText = _with_growth(SPRINT_LIVES_MESSAGE.format(score=runstate.sprint_score, best=runstate.sprint_best_score), "sprint")
        return

    start_button.hidden = True
    summary.hidden = True

    # The choice buttons (and their click proxies) are only rebuilt when the
    # question itself actually changed. sprint_tick() re-renders once a
    # second purely to refresh the timer display -- destroying and
    # recreating live buttons/proxies on every one of those ticks (found
    # live in a real browser: an in-flight click could land on a button
    # that had just been replaced, or a proxy that had just been destroyed)
    # is exactly the kind of flakiness a fast-paced game can least afford.
    if runstate.sprint_question is not runstate._sprint_rendered_question:
        _destroy_sprint_choice_proxies()
        _element("sprint-context").innerText = context_line(runstate.sprint_question)
        _element("sprint-prompt").innerText = runstate.sprint_question["prompt"]
        _element("sprint-feedback").innerText = runstate.sprint_note
        _element("sprint-waters").innerText = waters_text([plot_label(runstate.sprint_question["plot_id"])])
        _build_answer_area("sprint", runstate.sprint_question, choices_box, sprint_choice_proxies, submit_sprint_choice)
        runstate._sprint_rendered_question = runstate.sprint_question


def _setup_sprint():
    _setup_difficulty("sprint")
    _element("sprint-toggle-button").addEventListener("click", create_proxy(on_toggle_sprint))
    _element("sprint-start-button").addEventListener("click", create_proxy(start_sprint))
    _element("sprint-close-button").addEventListener("click", create_proxy(close_sprint))
