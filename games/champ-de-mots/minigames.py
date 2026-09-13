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
    render_racer()


def setup():
    """Called once from game.py's setup(), after configure(). Wires every
    DOM listener this file needs -- fully self-contained, so game.py never
    reaches into this module's internals beyond configure()/setup()/render()
    and the handful of tick functions JS calls directly (aliased at the
    bottom of game.py). Grows one _setup_<mode>() call per milestone, same
    as render() above."""
    _setup_blitz()
    _setup_racer()


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
RACER_TOTAL_STEPS = 10
RACER_RIVAL_TICKS_PER_STEP = 3  # the rival's fixed pace: 1 step every 3 real seconds

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

RACER_END_PLAYER = "player"  # the player reached the finish line first
RACER_END_RIVAL = "rival"  # the rival did

racer_open = False
racer_active = False
racer_player_position = 0
racer_rival_position = 0
racer_tick_count = 0  # ticks since the rival's last step
racer_question = None
racer_result = None  # None | True | False -- last attempt, transient UI flash
racer_end_reason = None  # None | RACER_END_PLAYER | RACER_END_RIVAL
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
    preferred = [v for v in _variants_for(plot) if v in RACER_PREFERRED_VARIANTS]
    if preferred:
        return RACER_RNG.choice(preferred)
    fallback = [v for v in _variants_for(plot) if v not in RACER_TYPED_VARIANTS]
    return RACER_RNG.choice(fallback) if fallback else None


_racer_candidates_cache = None


def _racer_candidate_plots():
    """Lazy and memoized -- see blitz_available()'s build note on why this
    must never run eagerly on a passive render()."""
    global _racer_candidates_cache
    if _racer_candidates_cache is None:
        _racer_candidates_cache = [
            p
            for p in _unlocked_range_plots(RACER_LO, RACER_HI)
            if p.topic_type == "grammar" and _racer_variant_for(p) is not None
        ]
    return _racer_candidates_cache


def _roll_racer_question():
    global racer_question
    plot = RACER_RNG.choice(_racer_candidate_plots())
    racer_question = _generate_question(plot, RACER_RNG, variant=_racer_variant_for(plot))


def start_racer(event=None):
    global racer_open, racer_active, racer_player_position, racer_rival_position
    global racer_tick_count, racer_result, racer_end_reason

    if not racer_available() or not _racer_candidate_plots():
        return None
    racer_open = True
    racer_active = True
    racer_player_position = 0
    racer_rival_position = 0
    racer_tick_count = 0
    racer_result = None
    racer_end_reason = None
    _roll_racer_question()
    render()
    return racer_question


def _end_racer(reason):
    global racer_active, racer_end_reason, racer_question
    racer_active = False
    racer_end_reason = reason
    racer_question = None


def submit_racer_choice(given):
    global racer_player_position, racer_result

    if not racer_active or racer_question is None:
        return None
    racer_result = given == racer_question["answer"]
    if racer_result:
        racer_player_position += 1
        if racer_player_position >= RACER_TOTAL_STEPS:
            _end_racer(RACER_END_PLAYER)
            render()
            return racer_result
    _roll_racer_question()
    render()
    return racer_result


def racer_tick(event=None):
    """JS-driven: the rival's fixed pace, one step every
    RACER_RIVAL_TICKS_PER_STEP real seconds -- see the module docstring's
    "the timer is JS-driven, not a Python clock" note. A no-op whenever no
    race is active."""
    global racer_tick_count, racer_rival_position
    if not racer_active:
        return None
    racer_tick_count += 1
    if racer_tick_count >= RACER_RIVAL_TICKS_PER_STEP:
        racer_tick_count = 0
        racer_rival_position += 1
        if racer_rival_position >= RACER_TOTAL_STEPS:
            _end_racer(RACER_END_RIVAL)
    render()
    return racer_rival_position


def close_racer(event=None):
    global racer_open, racer_active, racer_question, racer_result, racer_end_reason
    racer_open = False
    racer_active = False
    racer_question = None
    racer_result = None
    racer_end_reason = None
    render()


def on_toggle_racer(event=None):
    global racer_open
    if racer_open:
        close_racer()
    else:
        racer_open = True
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


_racer_rendered_question = None  # identity tracker, same fix Blitz needed


def render_racer():
    global _racer_rendered_question

    toggle = _element("racer-toggle-button")
    panel = _element("racer-panel")
    choices_box = _element("racer-choices")

    available = racer_available()
    toggle.disabled = not racer_open and not available
    toggle.innerText = "Close Verb Racer" if racer_open else "🏁 Verb Racer"

    if not racer_open:
        panel.hidden = True
        _destroy_racer_choice_proxies()
        choices_box.innerHTML = ""
        _racer_rendered_question = None
        return

    panel.hidden = False
    lock_message = _element("racer-lock-message")
    reason = racer_lock_reason()
    lock_message.hidden = reason is None
    lock_message.innerText = reason or ""

    start_button = _element("racer-start-button")
    summary = _element("racer-summary")

    _element("racer-player-marker").style.left = f"{_racer_marker_position(racer_player_position)}%"
    _element("racer-rival-marker").style.left = f"{_racer_marker_position(racer_rival_position)}%"
    _element("racer-progress-display").innerText = (
        f"You: {racer_player_position} of {RACER_TOTAL_STEPS} · "
        f"Rival: {racer_rival_position} of {RACER_TOTAL_STEPS}"
    )

    if not racer_active:
        _destroy_racer_choice_proxies()
        choices_box.innerHTML = ""
        _racer_rendered_question = None
        _element("racer-context").innerText = ""
        _element("racer-prompt").innerText = ""
        _element("racer-feedback").innerText = ""
        start_button.hidden = reason is not None
        start_button.innerText = "Race again" if racer_end_reason is not None else "Start the race"
        summary.hidden = racer_end_reason is None
        if racer_end_reason == RACER_END_PLAYER:
            summary.innerText = RACER_PLAYER_WIN_MESSAGE.format(
                player=racer_player_position, total=RACER_TOTAL_STEPS
            )
        elif racer_end_reason == RACER_END_RIVAL:
            summary.innerText = RACER_RIVAL_WIN_MESSAGE.format(
                player=racer_player_position, total=RACER_TOTAL_STEPS
            )
        return

    start_button.hidden = True
    summary.hidden = True

    if racer_result is False:
        _element("racer-feedback").innerText = "Not this turn — try the next one."
    else:
        _element("racer-feedback").innerText = ""

    # Same identity-based rebuild-only-on-change fix Blitz's own live
    # verification found necessary -- see that milestone's build note.
    if racer_question is not _racer_rendered_question:
        _destroy_racer_choice_proxies()
        _element("racer-context").innerText = racer_question["context"]
        _element("racer-prompt").innerText = racer_question["prompt"]
        choices_box.innerHTML = ""
        for index, choice in enumerate(racer_question["choices"]):
            button = document.createElement("button")
            button.id = f"racer-choice-{index}"
            button.innerText = choice
            button.className = "choice"
            proxy = create_proxy(_make_racer_choice_handler(choice))
            button.addEventListener("click", proxy)
            racer_choice_proxies.append(proxy)
            choices_box.appendChild(button)
        _racer_rendered_question = racer_question


def _setup_racer():
    _element("racer-toggle-button").addEventListener("click", create_proxy(on_toggle_racer))
    _element("racer-start-button").addEventListener("click", create_proxy(start_racer))
    _element("racer-close-button").addEventListener("click", create_proxy(close_racer))
