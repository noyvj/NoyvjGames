"""Le Champ de Mots — arcade minigame family (Milestones 27-30).

Four fast-paced, opt-in arcade modes, each themed to a natural grouping of
syllabus weeks and reusing the real catalog content and question-generation
machinery from `game.py` -- but with genuinely different, high-energy
interaction patterns than the core farm's calm SRS drilling: timers,
scoring, streaks, visual motion.

**Why this is a separate file, not a new mode inside game.py:** the core
farm's daily habit-forming loop is a *deliberate* zero-clock-pressure design
(CLAUDE.md §3/§8, Milestone 7) -- no `setInterval`/`setTimeout`/
`requestAnimationFrame`/`datetime`/`time.time` anywhere in `game.py`, and no
`@keyframes`/`animation:`/`transition:` anywhere in `style.css`, both
enforced by literal substring-scanning tests in `tests/test_polish.py`
(`test_the_farm_has_no_animation`, `test_nothing_in_the_game_runs_on_a_timer`).
That constraint protects the farm's own no-guilt, no-pressure habit loop; it
was never meant to ban a *separate, opt-in* arcade mode from having real
timers and motion -- an arcade minigame with a countdown and a moving racer
is a genuinely different thing, the same way "per-game / per-mode styling is
free once you're inside it" already works elsewhere in this hub. Rather than
loosen or reinterpret the two farm tests, this file (and `minigames.css`)
sits entirely outside what they scan, so the wellbeing guarantee for the
farm's own loop stays exactly as strict as it always was, unchanged, while
this file is free to use real timers and CSS motion. `game.py` imports this
module and re-exports only the handful of tick functions JS needs to reach
by name (see the bottom of `game.py`); every other piece of DOM wiring is
self-contained here via this module's own `setup()`.

**No circular import.** `game.py` imports this module, so this module never
imports `game.py` back -- the catalog-access/question-generation machinery
it reuses (`generate_question()`, `variants_for()`, the live `FarmState`)
is handed in once via `configure()`, called from `game.py`'s own `setup()`.
`document`/`create_proxy` are imported directly here, the same way `game.py`
imports them -- both are already faked by the test harness (or provided by
Pyodide) by the time this module loads.

**The "timer" is JS-driven, not a Python clock.** Every countdown in this
file is a plain integer/float counter that some explicit function
decrements -- `blitz_tick()`, `racer_tick()`, `boutique_tick()`, and
`cafe_tick()` are the JS-callable entry points, called from a `setInterval`
in `index.html`. Python only ever *owns the state*; JS owns real-world
timing, exactly the same split-of-responsibility the shared save widget and
the answer-report sender already established for this game.

**Row-unlock gating applies here too.** Every minigame only ever draws
content from `farm.is_row_unlocked(sequence)` rows, the same spoiler-
avoidance rule every other secondary mode (Review, Proficiency, Bonus,
Liaison, Cultural Notes) already follows. If a minigame's target sequence
range isn't fully unlocked yet, its toggle button is visible but disabled,
with the same "opens when row N has all sprouted" visual language locked
rows already use elsewhere in this game.
"""

import random
import re

from js import document
from pyodide.ffi import create_proxy

# --- wiring from game.py (avoids the circular import noted above) ----------

_farm = None
_generate_question = None
_variants_for = None


def configure(farm, generate_question_fn, variants_for_fn):
    """Called once from game.py's setup(): hands in the live FarmState plus
    the two question-generation functions every minigame reuses rather than
    re-deriving vocab/distractor selection from scratch (per the brief)."""
    global _farm, _generate_question, _variants_for
    _farm = farm
    _generate_question = generate_question_fn
    _variants_for = variants_for_fn


def _element(element_id):
    return document.getElementById(element_id)


# --- shared helpers ----------------------------------------------------


def _unlocked_range_plots(lo, hi):
    """Every plot in [lo, hi] whose row is currently unlocked -- locked rows
    contribute nothing, so a minigame can never preview content ahead of
    §7's pacing gate."""
    plots = []
    for sequence in range(lo, hi + 1):
        if _farm.is_row_unlocked(sequence):
            plots.extend(_farm.row_plots(sequence))
    return plots


def _range_fully_unlocked(lo, hi):
    """A minigame's target range counts as playable only once *every* row in
    it is unlocked -- unlike Liaison's "any eligible row" posture, a partial
    range here would mean an arcade session with suspiciously thin content,
    and the brief explicitly asks for "visibly present but disabled" over
    that half-open state."""
    return all(_farm.is_row_unlocked(sequence) for sequence in range(lo, hi + 1))


def _lock_reason(hi):
    """Same wording style as a locked farm row's own tooltip (Milestone 6)."""
    return f"Unlocks once every plot through row {hi} has sprouted."


def _topic_items_by_id(topic_id):
    """Read a topic's raw catalog items directly (not through the Plot
    model) -- Boutique Dash and Café Rush build bespoke shop-order content
    from specific vocab topics rather than from generate_question(), so they
    need the catalog's own items list, not a farm plot."""
    for week in _farm.catalog["weeks"]:
        for topic in week["topics"]:
            if topic["id"] == topic_id:
                return week["sequence"], topic["items"]
    return None, []


_PAREN_RE = re.compile(r"\([^)]*\)")


def _strip_parens(text):
    """Mechanical cleanup only -- drops a parenthetical aside (e.g. "some
    water (before vowel)") the same way game.py's own strip_parentheticals()
    does, so a displayed order description doesn't carry grammar-note
    clutter meant for the farm's own practice panel, not a shop customer's
    mouth."""
    return re.sub(r"\s{2,}", " ", _PAREN_RE.sub("", text)).strip()


def _expand_slash_variants(item):
    """A catalog item whose fr/en both pack several literal alternatives
    behind " / " (e.g. "du thé / du café" -> "tea / coffee") is really
    several separate real facts sharing one record. Splitting them into
    independent (fr, en) pairs gives a minigame's content pool more real
    variety without inventing any text -- every resulting string is still a
    verbatim catalog substring. Falls back to the item unchanged when the
    two sides don't line up 1:1 (nothing to safely split)."""
    fr_parts = [p.strip() for p in re.split(r"\s*/\s*", _strip_parens(item["fr"]))]
    en_parts = [p.strip() for p in re.split(r"\s*/\s*", _strip_parens(item["en"]))]
    if len(fr_parts) == len(en_parts) and len(fr_parts) > 1:
        return list(zip(fr_parts, en_parts))
    return [(_strip_parens(item["fr"]), _strip_parens(item["en"]))]


_RNG = random.Random()


def render():
    """Called once per repaint from game.py's own render(), same as every
    other secondary mode's render_<mode>() call. Milestone 27 ships only
    Blitz; each later milestone (28-30) adds its own render_<mode>() call
    here as that minigame lands, same incremental pattern as game.py's own
    render() growing one line per milestone."""
    render_blitz()


def setup():
    """Called once from game.py's setup(), after configure(). Wires every
    DOM listener this file needs -- fully self-contained, so game.py never
    reaches into this module's internals beyond configure()/setup()/render()
    and the handful of tick functions JS calls directly (aliased at the
    bottom of game.py). Grows one _setup_<mode>() call per milestone, same
    as render() above."""
    _setup_blitz()


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
BLITZ_DURATION_SECONDS = 60
BLITZ_STARTING_LIVES = 3
BLITZ_BASE_POINTS = 10
BLITZ_COMBO_STEP = 3  # every N correct-in-a-row raises the multiplier once
BLITZ_COMBO_BONUS_PER_STEP = 0.5
BLITZ_MAX_COMBO_STEPS = 4  # multiplier caps at 1 + 4*0.5 = 3.0x

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

blitz_open = False  # panel toggled open, independent of a live run
blitz_active = False  # a 60s run is currently in progress
blitz_score = 0
blitz_best_score = 0  # best across runs *this page load* -- session-only
blitz_lives = BLITZ_STARTING_LIVES
blitz_combo = 0
blitz_time_remaining = BLITZ_DURATION_SECONDS
blitz_question = None
blitz_end_reason = None  # None | BLITZ_END_TIME | BLITZ_END_LIVES
blitz_choice_proxies = []
BLITZ_RNG = random.Random()


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


_blitz_candidates_cache = None


def _blitz_candidate_plots():
    """Computed once per session (this module's own lifetime -- a fresh
    farm/fresh module in the test harness naturally gets a fresh cache) and
    memoized, since the *set* of plots capable of a translate variant is an
    intrinsic catalog property that doesn't change as the farm grows (see
    blitz_available()'s note on why this must stay lazy, never eager)."""
    global _blitz_candidates_cache
    if _blitz_candidates_cache is None:
        _blitz_candidates_cache = [
            p
            for p in _unlocked_range_plots(BLITZ_LO, BLITZ_HI)
            if any(v in BLITZ_TRANSLATE_VARIANTS for v in _variants_for(p))
        ]
    return _blitz_candidates_cache


def _blitz_multiplier(combo):
    steps = min(combo // BLITZ_COMBO_STEP, BLITZ_MAX_COMBO_STEPS)
    return 1.0 + steps * BLITZ_COMBO_BONUS_PER_STEP


def _roll_blitz_question():
    global blitz_question
    candidates = _blitz_candidate_plots()
    plot = BLITZ_RNG.choice(candidates)
    variants = [v for v in _variants_for(plot) if v in BLITZ_TRANSLATE_VARIANTS]
    variant = BLITZ_RNG.choice(variants)
    blitz_question = _generate_question(plot, BLITZ_RNG, variant=variant)


def start_blitz(event=None):
    global blitz_active, blitz_score, blitz_lives, blitz_combo
    global blitz_time_remaining, blitz_end_reason, blitz_open

    # blitz_available() is a cheap row-unlock-only proxy (see its own
    # docstring); the real candidate pool is only actually computed here,
    # so this is also where an edge case with genuinely zero eligible plots
    # (never observed in practice, but not provably impossible) is caught
    # rather than crashing on BLITZ_RNG.choice([]).
    if not blitz_available() or not _blitz_candidate_plots():
        return None
    blitz_open = True
    blitz_active = True
    blitz_score = 0
    blitz_lives = BLITZ_STARTING_LIVES
    blitz_combo = 0
    blitz_time_remaining = BLITZ_DURATION_SECONDS
    blitz_end_reason = None
    _roll_blitz_question()
    render()
    return blitz_question


def _end_blitz(reason):
    global blitz_active, blitz_end_reason, blitz_best_score, blitz_question
    blitz_active = False
    blitz_end_reason = reason
    blitz_best_score = max(blitz_best_score, blitz_score)
    blitz_question = None


def submit_blitz_choice(given):
    global blitz_score, blitz_combo, blitz_lives

    if not blitz_active or blitz_question is None:
        return None
    correct = given == blitz_question["answer"]
    if correct:
        blitz_combo += 1
        blitz_score += round(BLITZ_BASE_POINTS * _blitz_multiplier(blitz_combo))
    else:
        blitz_combo = 0
        blitz_lives -= 1
    if blitz_lives <= 0:
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
    global blitz_time_remaining
    if not blitz_active:
        return None
    blitz_time_remaining -= 1
    if blitz_time_remaining <= 0:
        blitz_time_remaining = 0
        _end_blitz(BLITZ_END_TIME)
    render()
    return blitz_time_remaining


def close_blitz(event=None):
    global blitz_open, blitz_active, blitz_question, blitz_end_reason
    blitz_open = False
    blitz_active = False
    blitz_question = None
    blitz_end_reason = None
    render()


def on_toggle_blitz(event=None):
    global blitz_open
    if blitz_open:
        close_blitz()
    else:
        blitz_open = True
        render()


def _make_blitz_choice_handler(choice):
    def handler(event=None):
        submit_blitz_choice(choice)
    return handler


BLITZ_SUMMARY_MESSAGE = "Time's up! Score: {score} (best this session: {best})."
BLITZ_LIVES_MESSAGE = "Out of lives for this round. Score: {score} (best this session: {best})."


_blitz_rendered_question = None  # identity tracker -- see the note below


def render_blitz():
    global _blitz_rendered_question

    toggle = _element("blitz-toggle-button")
    panel = _element("blitz-panel")
    choices_box = _element("blitz-choices")

    available = blitz_available()
    toggle.disabled = not blitz_open and not available
    toggle.innerText = "Close Blitz" if blitz_open else "⚡ Greetings & Basics Blitz"

    if not blitz_open:
        panel.hidden = True
        _destroy_blitz_choice_proxies()
        choices_box.innerHTML = ""
        _blitz_rendered_question = None
        return

    panel.hidden = False
    lock_message = _element("blitz-lock-message")
    reason = blitz_lock_reason()
    lock_message.hidden = reason is None
    lock_message.innerText = reason or ""

    start_button = _element("blitz-start-button")
    summary = _element("blitz-summary")

    _element("blitz-time-display").innerText = f"{blitz_time_remaining}s"
    _element("blitz-lives-display").innerText = "❤" * max(blitz_lives, 0) or "0 lives"
    _element("blitz-score-display").innerText = f"Score: {blitz_score}"
    _element("blitz-combo-display").innerText = (
        f"Combo x{_blitz_multiplier(blitz_combo):.1f}" if blitz_combo >= BLITZ_COMBO_STEP else ""
    )

    if not blitz_active:
        _destroy_blitz_choice_proxies()
        choices_box.innerHTML = ""
        _blitz_rendered_question = None
        _element("blitz-context").innerText = ""
        _element("blitz-prompt").innerText = ""
        _element("blitz-feedback").innerText = ""
        start_button.hidden = reason is not None
        start_button.innerText = "Play again" if blitz_end_reason is not None else "Start (60s)"
        summary.hidden = blitz_end_reason is None
        if blitz_end_reason == BLITZ_END_TIME:
            summary.innerText = BLITZ_SUMMARY_MESSAGE.format(score=blitz_score, best=blitz_best_score)
        elif blitz_end_reason == BLITZ_END_LIVES:
            summary.innerText = BLITZ_LIVES_MESSAGE.format(score=blitz_score, best=blitz_best_score)
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
    if blitz_question is not _blitz_rendered_question:
        _destroy_blitz_choice_proxies()
        _element("blitz-context").innerText = blitz_question["context"]
        _element("blitz-prompt").innerText = blitz_question["prompt"]
        _element("blitz-feedback").innerText = ""
        choices_box.innerHTML = ""
        for index, choice in enumerate(blitz_question["choices"]):
            button = document.createElement("button")
            button.id = f"blitz-choice-{index}"
            button.innerText = choice
            button.className = "choice"
            proxy = create_proxy(_make_blitz_choice_handler(choice))
            button.addEventListener("click", proxy)
            blitz_choice_proxies.append(proxy)
            choices_box.appendChild(button)
        _blitz_rendered_question = blitz_question


def _setup_blitz():
    _element("blitz-toggle-button").addEventListener("click", create_proxy(on_toggle_blitz))
    _element("blitz-start-button").addEventListener("click", create_proxy(start_blitz))
    _element("blitz-close-button").addEventListener("click", create_proxy(close_blitz))
