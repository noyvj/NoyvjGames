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
_record_practice = None


def _record(mode, correct):
    """Feed one answered question into game.py's practice-progress ledger
    (see game.py's "practice progress" build note). A no-op when nothing was
    wired in, so the module stays usable standalone."""
    if _record_practice is not None:
        _record_practice(mode, bool(correct))


def configure(farm, generate_question_fn, variants_for_fn, record_practice_fn=None):
    """Called once from game.py's setup(): hands in the live FarmState plus
    the two question-generation functions every minigame reuses rather than
    re-deriving vocab/distractor selection from scratch (per the brief)."""
    global _farm, _generate_question, _variants_for, _record_practice
    _record_practice = record_practice_fn
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

_LEADING_ARTICLES = ("a ", "an ", "the ")


def _strip_leading_article(text):
    """Mechanical prefix strip only (Boutique Dash's own need: combining a
    catalog colour word with a catalog garment word into one order
    description reads far better as "black shirt" than "black a shirt").
    Not `answer_alternatives()`'s `ARTICLE_PREFIXES` -- that lives in
    game.py and importing it back would recreate the circular-import problem
    the module docstring already rules out, so this is a small local mirror
    of the same idea, same posture as the V_* variant-name mirrors above."""
    lowered = text.lower()
    for article in _LEADING_ARTICLES:
        if lowered.startswith(article):
            return text[len(article):]
    return text


def render():
    """Called once per repaint from game.py's own render(), same as every
    other secondary mode's render_<mode>() call. Milestone 27 ships only
    Blitz; each later milestone (28-30) adds its own render_<mode>() call
    here as that minigame lands, same incremental pattern as game.py's own
    render() growing one line per milestone."""
    render_blitz()
    render_racer()
    render_boutique()
    render_cafe()


def setup():
    """Called once from game.py's setup(), after configure(). Wires every
    DOM listener this file needs -- fully self-contained, so game.py never
    reaches into this module's internals beyond configure()/setup()/render()
    and the handful of tick functions JS calls directly (aliased at the
    bottom of game.py). Grows one _setup_<mode>() call per milestone, same
    as render() above."""
    _setup_blitz()
    _setup_racer()
    _setup_boutique()
    _setup_cafe()


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
    _record("blitz", correct)
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
    _record("racer", racer_result)
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


# ===========================================================================
# Milestone 29 — "Boutique Dash" (sequence 16-18)
# ===========================================================================
#
# FREN152 Ch.6: shopping for clothes, colours, demonstratives -- a shop-rush
# game. A customer's order is a genuine colour + garment combination built
# from real catalog items (never invented text), the player picks the
# matching item from a small display of options before that customer's
# patience runs out. 15 customers per session, ending in a final tally --
# no per-customer retry, matching the brief's "a miss or timeout loses a
# customer" framing (one shot each, not a forgiving reroll).
#
# **Building a genuine colour+garment combo without inventing any French,**
# the one piece of real design work this milestone needed. A garment item's
# own fr text already tells you its gender via its article ("un pull" is
# masc, "une jupe" is fem); a colour item's fr text already stores both
# gendered forms side by side ("noir / noire"). Picking whichever half
# matches the garment's own article and gluing the two catalog strings
# together with a space is exactly the same kind of mechanical recombination
# §5's runtime question generator already relies on everywhere else (the
# conjugation pronoun-swap is the closest cousin) -- nothing here is authored
# prose, every word is a verbatim catalog string, and the result is real,
# correctly-agreed French ("un sac noir", "une montre beige"). A plural
# garment ("des chaussettes") is deliberately excluded from the pool
# instead: the catalog only ever stores a colour's masc/fem singular forms,
# never a plural, and gluing "noir" onto a plural noun with no catalog
# plural form to reach for would mean fabricating "noirs"/"noires" out of
# nothing -- exactly the kind of invented text §5 rules out. Same reasoning
# for any garment record that packs two real items into one string via " / "
# ("un sac à main / un sac à dos") -- there is no single garment to attach a
# colour to there, so it's skipped rather than gluing a colour onto both
# halves at once.
#
# **Garment and colour pools each draw from more than one topic across the
# full 16-18 range**, not just row 16's own dedicated "Clothing"/"Colours"
# topics -- row 17's "un sac"/"un chapeau" and row 18's accessories
# ("une montre", "une crème solaire", and the like) are genuine boutique
# stock too, and row 17's "Extra materials & sizes" topic quietly holds two
# more invariable colours (bordeaux, beige) alongside its material/size
# vocabulary. Picking those two out relies on the catalog's own
# "(invariable colour)" annotation on exactly those two items' `en` text,
# rather than a hand-picked id list that would silently go stale if the
# catalog ever grows another one.

BOUTIQUE_LO, BOUTIQUE_HI = 16, 18
BOUTIQUE_TOTAL_CUSTOMERS = 15
BOUTIQUE_STARTING_PATIENCE = 12  # seconds for the first customer
BOUTIQUE_MIN_PATIENCE = 6  # the pace never speeds up past this floor
BOUTIQUE_PATIENCE_STEP = 1  # shaved off the patience clock per correct sale
BOUTIQUE_OPTION_COUNT = 4
BOUTIQUE_BASE_POINTS = 10

BOUTIQUE_GARMENT_TOPIC_IDS = (
    "fren152-w6-vocab001",  # Clothing
    "fren152-w7-vocab001",  # Materials and accessories ("un sac", "un chapeau")
    "fren152-w8-vocab001",  # Accessories & toiletries
)
BOUTIQUE_COLOUR_TOPIC_IDS = (
    "fren152-w6-vocab002",        # Colours -- masc/fem pairs
    "fren152-w7-vocab-slide001",  # Extra materials & sizes -- 2 invariable colours live here too
)

boutique_open = False
boutique_active = False
boutique_served = 0
boutique_missed = 0
boutique_score = 0
boutique_patience_max = BOUTIQUE_STARTING_PATIENCE
boutique_patience_remaining = BOUTIQUE_STARTING_PATIENCE
boutique_order = None  # {"order_en", "answer", "choices"} | None
boutique_last_result = None  # None | True | False -- last customer, transient UI flash
boutique_choice_proxies = []
BOUTIQUE_RNG = random.Random()


def _destroy_boutique_choice_proxies():
    for proxy in boutique_choice_proxies:
        proxy.destroy()
    boutique_choice_proxies.clear()


def boutique_available():
    """Cheap on purpose, same reasoning as blitz_available()'s own note:
    row-unlock state only, never the full garment/colour pool scan below."""
    return _range_fully_unlocked(BOUTIQUE_LO, BOUTIQUE_HI)


def boutique_lock_reason():
    return None if _range_fully_unlocked(BOUTIQUE_LO, BOUTIQUE_HI) else _lock_reason(BOUTIQUE_HI)


_boutique_garments_cache = None
_boutique_colours_cache = None


def _boutique_garment_entries():
    """Lazy and memoized -- see blitz_available()'s build note on why this
    must never run eagerly on a passive render(). Each entry is
    (garment_fr, garment_en, gender), gender being "m"/"f" read straight off
    the item's own article."""
    global _boutique_garments_cache
    if _boutique_garments_cache is None:
        entries = []
        for topic_id in BOUTIQUE_GARMENT_TOPIC_IDS:
            sequence, items = _topic_items_by_id(topic_id)
            if sequence is None or not _farm.is_row_unlocked(sequence):
                continue
            for item in items:
                fr = _strip_parens(item["fr"])
                en = _strip_parens(item["en"])
                if " / " in fr:
                    continue  # two real garments packed into one record -- see module note
                if fr.startswith("une "):
                    entries.append((fr, en, "f"))
                elif fr.startswith("un "):
                    entries.append((fr, en, "m"))
        _boutique_garments_cache = entries
    return _boutique_garments_cache


def _boutique_colour_entries():
    """Lazy and memoized. Each entry is (masc_fr, fem_fr, colour_en) -- an
    invariable colour (rose, orange, bordeaux, ...) simply repeats the same
    form for both, so the caller never has to special-case it."""
    global _boutique_colours_cache
    if _boutique_colours_cache is None:
        entries = []
        for topic_id in BOUTIQUE_COLOUR_TOPIC_IDS:
            sequence, items = _topic_items_by_id(topic_id)
            if sequence is None or not _farm.is_row_unlocked(sequence):
                continue
            for item in items:
                fr = item["fr"]
                en = _strip_parens(item["en"])
                if " / " in fr:
                    masc, fem = (part.strip() for part in fr.split(" / ", 1))
                    entries.append((masc, fem, en))
                elif "invariable colour" in item["en"].lower():
                    entries.append((fr, fr, en))
        _boutique_colours_cache = entries
    return _boutique_colours_cache


def _roll_boutique_order():
    global boutique_order
    garments = _boutique_garment_entries()
    colours = _boutique_colour_entries()
    garment_fr, garment_en, gender = BOUTIQUE_RNG.choice(garments)
    colour_masc, colour_fem, colour_en = BOUTIQUE_RNG.choice(colours)
    colour_fr = colour_masc if gender == "m" else colour_fem
    answer = f"{garment_fr} {colour_fr}"
    order_en = f"{colour_en} {_strip_leading_article(garment_en)}"

    choices = {answer}
    attempts = 0
    while len(choices) < BOUTIQUE_OPTION_COUNT and attempts < 50:
        other_garment_fr, _, other_gender = BOUTIQUE_RNG.choice(garments)
        other_masc, other_fem, _ = BOUTIQUE_RNG.choice(colours)
        other_colour_fr = other_masc if other_gender == "m" else other_fem
        choices.add(f"{other_garment_fr} {other_colour_fr}")
        attempts += 1
    choices = list(choices)
    BOUTIQUE_RNG.shuffle(choices)
    boutique_order = {"order_en": order_en, "answer": answer, "choices": choices}


def start_boutique(event=None):
    global boutique_open, boutique_active, boutique_served, boutique_missed
    global boutique_score, boutique_patience_max, boutique_patience_remaining
    global boutique_last_result

    if not boutique_available() or not _boutique_garment_entries() or not _boutique_colour_entries():
        return None
    boutique_open = True
    boutique_active = True
    boutique_served = 0
    boutique_missed = 0
    boutique_score = 0
    boutique_patience_max = BOUTIQUE_STARTING_PATIENCE
    boutique_patience_remaining = BOUTIQUE_STARTING_PATIENCE
    boutique_last_result = None
    _roll_boutique_order()
    render()
    return boutique_order


def _resolve_boutique_customer(served):
    """Shared by a submitted choice and a timeout (boutique_tick()) -- either
    way, this customer's outcome is exactly the same shape: served or not,
    tally it, maybe speed up, then either end the shift or bring in the
    next customer."""
    global boutique_served, boutique_missed, boutique_score, boutique_patience_max
    global boutique_active, boutique_order, boutique_patience_remaining, boutique_last_result

    boutique_last_result = served
    _record("boutique", served)
    if served:
        boutique_served += 1
        boutique_score += BOUTIQUE_BASE_POINTS
        boutique_patience_max = max(BOUTIQUE_MIN_PATIENCE, boutique_patience_max - BOUTIQUE_PATIENCE_STEP)
    else:
        boutique_missed += 1

    if boutique_served + boutique_missed >= BOUTIQUE_TOTAL_CUSTOMERS:
        boutique_active = False
        boutique_order = None
    else:
        boutique_patience_remaining = boutique_patience_max
        _roll_boutique_order()


def submit_boutique_choice(given):
    if not boutique_active or boutique_order is None:
        return None
    correct = given == boutique_order["answer"]
    _resolve_boutique_customer(correct)
    render()
    return correct


def boutique_tick(event=None):
    """JS-driven countdown tick -- see the module docstring's "the timer is
    JS-driven, not a Python clock" note. A no-op whenever no shift is
    active."""
    global boutique_patience_remaining
    if not boutique_active:
        return None
    boutique_patience_remaining -= 1
    if boutique_patience_remaining <= 0:
        boutique_patience_remaining = 0
        _resolve_boutique_customer(False)
    render()
    return boutique_patience_remaining


def close_boutique(event=None):
    global boutique_open, boutique_active, boutique_order, boutique_last_result
    boutique_open = False
    boutique_active = False
    boutique_order = None
    boutique_last_result = None
    render()


def on_toggle_boutique(event=None):
    global boutique_open
    if boutique_open:
        close_boutique()
    else:
        boutique_open = True
        render()


def _make_boutique_choice_handler(choice):
    def handler(event=None):
        submit_boutique_choice(choice)
    return handler


BOUTIQUE_SUMMARY_MESSAGE = (
    "Shift complete! Served {served} of {total} customers (missed {missed}) · Score: {score}."
)


_boutique_rendered_order = None  # identity tracker -- see Blitz's own build note on why


def render_boutique():
    global _boutique_rendered_order

    toggle = _element("boutique-toggle-button")
    panel = _element("boutique-panel")
    options_box = _element("boutique-options")

    available = boutique_available()
    toggle.disabled = not boutique_open and not available
    toggle.innerText = "Close Boutique Dash" if boutique_open else "👗 Boutique Dash"

    if not boutique_open:
        panel.hidden = True
        _destroy_boutique_choice_proxies()
        options_box.innerHTML = ""
        _boutique_rendered_order = None
        return

    panel.hidden = False
    lock_message = _element("boutique-lock-message")
    reason = boutique_lock_reason()
    lock_message.hidden = reason is None
    lock_message.innerText = reason or ""

    start_button = _element("boutique-start-button")
    summary = _element("boutique-summary")

    _element("boutique-served-display").innerText = f"Served: {boutique_served}"
    _element("boutique-missed-display").innerText = f"Missed: {boutique_missed}"
    _element("boutique-score-display").innerText = f"Score: {boutique_score}"

    completed = boutique_served + boutique_missed

    if not boutique_active:
        _destroy_boutique_choice_proxies()
        options_box.innerHTML = ""
        _boutique_rendered_order = None
        _element("boutique-order").innerText = ""
        _element("boutique-feedback").innerText = ""
        fill = _element("boutique-patience-fill")
        fill.style.width = "100%"
        fill.className = "shop-rush-patience-fill"
        start_button.hidden = reason is not None
        start_button.innerText = "Open again" if completed > 0 else "Open the shop"
        summary.hidden = completed < BOUTIQUE_TOTAL_CUSTOMERS
        if completed >= BOUTIQUE_TOTAL_CUSTOMERS:
            summary.innerText = BOUTIQUE_SUMMARY_MESSAGE.format(
                served=boutique_served, total=BOUTIQUE_TOTAL_CUSTOMERS,
                missed=boutique_missed, score=boutique_score,
            )
        return

    start_button.hidden = True
    summary.hidden = True

    pct = round((boutique_patience_remaining / boutique_patience_max) * 100) if boutique_patience_max else 0
    fill = _element("boutique-patience-fill")
    fill.style.width = f"{pct}%"
    low = boutique_patience_remaining <= max(2, round(boutique_patience_max * 0.3))
    fill.className = "shop-rush-patience-fill shop-rush-patience-fill--low" if low else "shop-rush-patience-fill"

    if boutique_last_result is False:
        _element("boutique-feedback").innerText = "Not this time — next customer, please."
    elif boutique_last_result is True:
        _element("boutique-feedback").innerText = "Sold!"
    else:
        _element("boutique-feedback").innerText = ""

    if boutique_order is not _boutique_rendered_order:
        _destroy_boutique_choice_proxies()
        _element("boutique-order").innerText = f"A customer wants: {boutique_order['order_en']}."
        options_box.innerHTML = ""
        for index, choice in enumerate(boutique_order["choices"]):
            button = document.createElement("button")
            button.id = f"boutique-choice-{index}"
            button.innerText = choice
            button.className = "choice"
            proxy = create_proxy(_make_boutique_choice_handler(choice))
            button.addEventListener("click", proxy)
            boutique_choice_proxies.append(proxy)
            options_box.appendChild(button)
        _boutique_rendered_order = boutique_order


def _setup_boutique():
    _element("boutique-toggle-button").addEventListener("click", create_proxy(on_toggle_boutique))
    _element("boutique-start-button").addEventListener("click", create_proxy(start_boutique))
    _element("boutique-close-button").addEventListener("click", create_proxy(close_boutique))


# ===========================================================================
# Milestone 30 — "Café Rush" (sequence 19-23)
# ===========================================================================
#
# FREN152 Ch.9: food & drink, partitive, passé composé -- the same
# order-rush structure as Boutique Dash (a customer's order, a patience
# clock, 15 customers, a final tally), themed to food/drink, with one
# content twist reflecting this range's other grammar focus: every third
# customer also asks the player to confirm the order in the passé composé,
# a multiple-choice fill-in-the-blank/conjugation-swap question pulled
# straight from a passé-composé grammar plot in this range, reusing
# generate_question() exactly the way Verb Racer already does rather than
# building a second question generator.
#
# **The food/drink pool leans entirely on `_expand_slash_variants()`**
# (defined in the shared-helpers section above, built for exactly this
# milestone) -- catalog items like "du thé / du café" -> "tea / coffee" or
# "un poisson / du thon / du saumon" -> "fish / tuna / salmon" are really
# several separate real facts sharing one record, and splitting them gives
# the order pool genuine variety without inventing a single word. An item
# whose fr/en sides don't split evenly ("de la soupe / du potage" -> "soup",
# both names for the one dish) is left alone by that same function, which is
# exactly right here too: presenting a whole "de la soupe / du potage" as
# one order is honest about it being one dish with two acceptable names,
# rather than incorrectly forcing a split that would silently create a
# second, fabricated distinct answer.
#
# **The twist is deliberately a fixed cadence, not a random chance.** A
# coin-flip "some rounds" would make an already-short 15-customer session's
# actual twist frequency vary a lot run to run, including runs that never
# hit one at all -- CAFE_TWIST_INTERVAL fixes it at exactly every third
# customer, which is simple, testable, and guarantees every full session
# sees the twist at least a few times, per the brief's own framing of it as
# a content addition to this minigame rather than a rare surprise.
#
# **A twist round only fully "sells" once both steps are right.** The brief
# reads the twist as something the player does *in addition to* picking the
# right item, not a softer alternative to it -- so getting the item right
# but the passé composé confirmation wrong still counts as a missed
# customer (no double penalty beyond that: the miss is exactly as neutral,
# "not this time," as any other). The shared per-customer patience clock
# keeps ticking through both steps of a twist round, the same single timer
# Boutique Dash uses for its own one clock per customer.

CAFE_LO, CAFE_HI = 19, 23
CAFE_TOTAL_CUSTOMERS = 15
CAFE_STARTING_PATIENCE = 12
CAFE_MIN_PATIENCE = 6
CAFE_PATIENCE_STEP = 1
CAFE_OPTION_COUNT = 4
CAFE_BASE_POINTS = 10
CAFE_TWIST_BONUS_POINTS = 5
CAFE_TWIST_INTERVAL = 3  # every Nth customer also gets the passé composé twist

CAFE_FOOD_TOPIC_IDS = (
    "fren152-w9-vocab001",  # Breakfast foods
    "fren152-w9-vocab002",  # Drinks
    "fren152-w9-vocab003",  # Lunch, dinner & mains
)
# The passé-composé topics this range actually teaches -- not every grammar
# topic in 19-23 (the partitive, y/en, futur proche and the like stay out of
# this twist on purpose; the brief names passé composé specifically as the
# content this twist should reflect). Not every one of these ends up
# offering a blank/conjugation variant (être-governed verbs' own example
# sentences turn out too irregular for either), which is fine -- the
# eligibility filter below reads that from variants_for() itself rather than
# assuming every id here qualifies.
CAFE_PASSE_COMPOSE_TOPIC_IDS = (
    "fren152-w11-grammar001",  # regular passé composé -- avoir verbs
    "fren152-w11-grammar002",  # passé composé -- adverbs as time markers
    "fren152-w12-grammar001",  # irregular past participles
    "fren152-w13-grammar001",  # passé composé -- être-governed verbs
    "fren152-w13-grammar002",  # reflexive verbs in the passé composé
)
CAFE_TWIST_VARIANTS = {VARIANT_BLANK_WORD, VARIANT_CONJUGATION_SWAP}

CAFE_STAGE_PICK = "pick"
CAFE_STAGE_TWIST = "twist"

cafe_open = False
cafe_active = False
cafe_served = 0
cafe_missed = 0
cafe_score = 0
cafe_patience_max = CAFE_STARTING_PATIENCE
cafe_patience_remaining = CAFE_STARTING_PATIENCE
cafe_customer_index = 0  # 1-based count of customers seen this session so far
cafe_stage = CAFE_STAGE_PICK  # CAFE_STAGE_PICK | CAFE_STAGE_TWIST
cafe_is_twist_round = False
cafe_order = None  # {"order_en", "answer", "choices"} | None
cafe_twist_question = None  # generate_question() output | None
cafe_last_result = None  # None | True | False -- last customer, transient UI flash
cafe_choice_proxies = []
cafe_twist_choice_proxies = []
CAFE_RNG = random.Random()


def _destroy_cafe_choice_proxies():
    for proxy in cafe_choice_proxies:
        proxy.destroy()
    cafe_choice_proxies.clear()


def _destroy_cafe_twist_proxies():
    for proxy in cafe_twist_choice_proxies:
        proxy.destroy()
    cafe_twist_choice_proxies.clear()


def cafe_available():
    """Cheap on purpose, same reasoning as blitz_available()'s own note:
    row-unlock state only, never the full food-pool/twist-pool scan below."""
    return _range_fully_unlocked(CAFE_LO, CAFE_HI)


def cafe_lock_reason():
    return None if _range_fully_unlocked(CAFE_LO, CAFE_HI) else _lock_reason(CAFE_HI)


_cafe_food_cache = None
_cafe_twist_candidates_cache = None


def _cafe_food_entries():
    """Lazy and memoized -- see blitz_available()'s build note on why this
    must never run eagerly on a passive render(). Each entry is (fr, en),
    already expanded through _expand_slash_variants() so a multi-fact
    record contributes each of its real facts separately."""
    global _cafe_food_cache
    if _cafe_food_cache is None:
        entries = []
        for topic_id in CAFE_FOOD_TOPIC_IDS:
            sequence, items = _topic_items_by_id(topic_id)
            if sequence is None or not _farm.is_row_unlocked(sequence):
                continue
            for item in items:
                entries.extend(_expand_slash_variants(item))
        _cafe_food_cache = entries
    return _cafe_food_cache


def _cafe_twist_variant(plot):
    """None if this plot can't offer a blank/conjugation question at all --
    the same "not every candidate id actually qualifies" posture Racer's own
    _racer_variant_for() takes, just narrower (blank/conjugation only, no
    translate-choice fallback, since the whole point of the twist is a
    fill-in-the-blank passé composé prompt, not any old question about the
    same plot)."""
    eligible = [v for v in _variants_for(plot) if v in CAFE_TWIST_VARIANTS]
    return CAFE_RNG.choice(eligible) if eligible else None


def _cafe_twist_candidate_plots():
    """Lazy and memoized. Walks the passé-composé topic ids directly rather
    than every plot in range -- Café Rush's twist is deliberately scoped to
    this range's passé-composé content specifically, not its full grammar
    docket (partitive, y/en, futur proche stay out, per the module note
    above)."""
    global _cafe_twist_candidates_cache
    if _cafe_twist_candidates_cache is None:
        candidates = []
        for sequence in range(CAFE_LO, CAFE_HI + 1):
            if not _farm.is_row_unlocked(sequence):
                continue
            for plot in _farm.row_plots(sequence):
                if plot.topic_id in CAFE_PASSE_COMPOSE_TOPIC_IDS and _cafe_twist_variant(plot) is not None:
                    candidates.append(plot)
        _cafe_twist_candidates_cache = candidates
    return _cafe_twist_candidates_cache


def _roll_cafe_order():
    global cafe_order
    foods = _cafe_food_entries()
    answer_fr, answer_en = CAFE_RNG.choice(foods)

    choices = {answer_fr}
    attempts = 0
    while len(choices) < CAFE_OPTION_COUNT and attempts < 50:
        other_fr, other_en = CAFE_RNG.choice(foods)
        # Skip a distractor whose English happens to mean the same dish as
        # the answer under a different French name (e.g. "de la soupe" vs
        # "du potage" both meaning "soup") -- two buttons that would both be
        # a legitimate answer to the same English order is a genuine
        # ambiguity, not a fair distractor.
        if other_en.lower() != answer_en.lower():
            choices.add(other_fr)
        attempts += 1
    choices = list(choices)
    CAFE_RNG.shuffle(choices)
    cafe_order = {"order_en": answer_en, "answer": answer_fr, "choices": choices}


def _roll_cafe_customer():
    global cafe_customer_index, cafe_is_twist_round, cafe_stage
    global cafe_patience_remaining, cafe_twist_question
    cafe_customer_index += 1
    twist_pool = _cafe_twist_candidate_plots()
    cafe_is_twist_round = bool(twist_pool) and cafe_customer_index % CAFE_TWIST_INTERVAL == 0
    cafe_stage = CAFE_STAGE_PICK
    cafe_twist_question = None
    cafe_patience_remaining = cafe_patience_max
    _roll_cafe_order()


def start_cafe(event=None):
    global cafe_open, cafe_active, cafe_served, cafe_missed, cafe_score
    global cafe_patience_max, cafe_customer_index, cafe_last_result

    if not cafe_available() or not _cafe_food_entries():
        return None
    cafe_open = True
    cafe_active = True
    cafe_served = 0
    cafe_missed = 0
    cafe_score = 0
    cafe_patience_max = CAFE_STARTING_PATIENCE
    cafe_customer_index = 0
    cafe_last_result = None
    _roll_cafe_customer()
    render()
    return cafe_order


def _resolve_cafe_customer(served, speed_up):
    """Shared by every way a customer's round can end -- a correct/wrong
    item pick with no twist, a correct/wrong twist confirmation, or a
    timeout at either stage. `speed_up` is deliberately a separate flag from
    `served`: it's False for a miss (per the brief, only a *correct sale*
    speeds the pace up), matching Boutique Dash's own rule."""
    global cafe_served, cafe_missed, cafe_score, cafe_patience_max
    global cafe_active, cafe_order, cafe_stage, cafe_twist_question, cafe_last_result

    cafe_last_result = served
    _record("cafe", served)
    if served:
        cafe_served += 1
        cafe_score += CAFE_BASE_POINTS + (CAFE_TWIST_BONUS_POINTS if cafe_stage == CAFE_STAGE_TWIST else 0)
    else:
        cafe_missed += 1
    if speed_up:
        cafe_patience_max = max(CAFE_MIN_PATIENCE, cafe_patience_max - CAFE_PATIENCE_STEP)

    if cafe_served + cafe_missed >= CAFE_TOTAL_CUSTOMERS:
        cafe_active = False
        cafe_order = None
        cafe_stage = CAFE_STAGE_PICK
        cafe_twist_question = None
    else:
        _roll_cafe_customer()


def submit_cafe_item_choice(given):
    global cafe_stage, cafe_twist_question

    if not cafe_active or cafe_order is None or cafe_stage != CAFE_STAGE_PICK:
        return None
    correct = given == cafe_order["answer"]
    if not correct:
        _resolve_cafe_customer(served=False, speed_up=False)
        render()
        return False

    twist_pool = _cafe_twist_candidate_plots()
    if cafe_is_twist_round and twist_pool:
        cafe_stage = CAFE_STAGE_TWIST
        plot = CAFE_RNG.choice(twist_pool)
        cafe_twist_question = _generate_question(plot, CAFE_RNG, variant=_cafe_twist_variant(plot))
        render()
        return True

    _resolve_cafe_customer(served=True, speed_up=True)
    render()
    return True


def submit_cafe_twist_choice(given):
    if not cafe_active or cafe_stage != CAFE_STAGE_TWIST or cafe_twist_question is None:
        return None
    correct = given == cafe_twist_question["answer"]
    _resolve_cafe_customer(served=correct, speed_up=correct)
    render()
    return correct


def cafe_tick(event=None):
    """JS-driven countdown tick -- see the module docstring's "the timer is
    JS-driven, not a Python clock" note. A no-op whenever no shift is
    active. One shared clock covers both stages of a twist round, exactly
    the module note above describes."""
    global cafe_patience_remaining
    if not cafe_active:
        return None
    cafe_patience_remaining -= 1
    if cafe_patience_remaining <= 0:
        cafe_patience_remaining = 0
        _resolve_cafe_customer(served=False, speed_up=False)
    render()
    return cafe_patience_remaining


def close_cafe(event=None):
    global cafe_open, cafe_active, cafe_order, cafe_stage, cafe_twist_question, cafe_last_result
    cafe_open = False
    cafe_active = False
    cafe_order = None
    cafe_stage = CAFE_STAGE_PICK
    cafe_twist_question = None
    cafe_last_result = None
    render()


def on_toggle_cafe(event=None):
    global cafe_open
    if cafe_open:
        close_cafe()
    else:
        cafe_open = True
        render()


def _make_cafe_item_choice_handler(choice):
    def handler(event=None):
        submit_cafe_item_choice(choice)
    return handler


def _make_cafe_twist_choice_handler(choice):
    def handler(event=None):
        submit_cafe_twist_choice(choice)
    return handler


CAFE_SUMMARY_MESSAGE = (
    "Service is over! Served {served} of {total} customers (missed {missed}) · Score: {score}."
)


_cafe_rendered_order = None  # identity tracker -- see Blitz's own build note on why
_cafe_rendered_twist = None


def render_cafe():
    global _cafe_rendered_order, _cafe_rendered_twist

    toggle = _element("cafe-toggle-button")
    panel = _element("cafe-panel")
    options_box = _element("cafe-options")
    twist_panel = _element("cafe-twist-panel")
    twist_choices_box = _element("cafe-twist-choices")

    available = cafe_available()
    toggle.disabled = not cafe_open and not available
    toggle.innerText = "Close Café Rush" if cafe_open else "☕ Café Rush"

    if not cafe_open:
        panel.hidden = True
        _destroy_cafe_choice_proxies()
        _destroy_cafe_twist_proxies()
        options_box.innerHTML = ""
        twist_choices_box.innerHTML = ""
        _cafe_rendered_order = None
        _cafe_rendered_twist = None
        return

    panel.hidden = False
    lock_message = _element("cafe-lock-message")
    reason = cafe_lock_reason()
    lock_message.hidden = reason is None
    lock_message.innerText = reason or ""

    start_button = _element("cafe-start-button")
    summary = _element("cafe-summary")

    _element("cafe-served-display").innerText = f"Served: {cafe_served}"
    _element("cafe-missed-display").innerText = f"Missed: {cafe_missed}"
    _element("cafe-score-display").innerText = f"Score: {cafe_score}"

    completed = cafe_served + cafe_missed

    if not cafe_active:
        _destroy_cafe_choice_proxies()
        _destroy_cafe_twist_proxies()
        options_box.innerHTML = ""
        twist_choices_box.innerHTML = ""
        _cafe_rendered_order = None
        _cafe_rendered_twist = None
        _element("cafe-order").innerText = ""
        _element("cafe-feedback").innerText = ""
        twist_panel.hidden = True
        fill = _element("cafe-patience-fill")
        fill.style.width = "100%"
        fill.className = "shop-rush-patience-fill"
        start_button.hidden = reason is not None
        start_button.innerText = "Open again" if completed > 0 else "Open the café"
        summary.hidden = completed < CAFE_TOTAL_CUSTOMERS
        if completed >= CAFE_TOTAL_CUSTOMERS:
            summary.innerText = CAFE_SUMMARY_MESSAGE.format(
                served=cafe_served, total=CAFE_TOTAL_CUSTOMERS,
                missed=cafe_missed, score=cafe_score,
            )
        return

    start_button.hidden = True
    summary.hidden = True

    pct = round((cafe_patience_remaining / cafe_patience_max) * 100) if cafe_patience_max else 0
    fill = _element("cafe-patience-fill")
    fill.style.width = f"{pct}%"
    low = cafe_patience_remaining <= max(2, round(cafe_patience_max * 0.3))
    fill.className = "shop-rush-patience-fill shop-rush-patience-fill--low" if low else "shop-rush-patience-fill"

    if cafe_last_result is False:
        _element("cafe-feedback").innerText = "Not this time — next customer, please."
    elif cafe_last_result is True:
        _element("cafe-feedback").innerText = "Sold!"
    else:
        _element("cafe-feedback").innerText = ""

    if cafe_order is not _cafe_rendered_order:
        _destroy_cafe_choice_proxies()
        _element("cafe-order").innerText = f"A customer wants: {cafe_order['order_en']}."
        options_box.innerHTML = ""
        for index, choice in enumerate(cafe_order["choices"]):
            button = document.createElement("button")
            button.id = f"cafe-choice-{index}"
            button.innerText = choice
            button.className = "choice"
            proxy = create_proxy(_make_cafe_item_choice_handler(choice))
            button.addEventListener("click", proxy)
            cafe_choice_proxies.append(proxy)
            options_box.appendChild(button)
        _cafe_rendered_order = cafe_order

    if cafe_stage == CAFE_STAGE_TWIST and cafe_twist_question is not None:
        twist_panel.hidden = False
        options_box.innerHTML = ""  # the item choice is already made -- only the twist remains
        if cafe_twist_question is not _cafe_rendered_twist:
            _destroy_cafe_twist_proxies()
            _element("cafe-twist-context").innerText = cafe_twist_question["context"]
            _element("cafe-twist-prompt").innerText = cafe_twist_question["prompt"]
            twist_choices_box.innerHTML = ""
            for index, choice in enumerate(cafe_twist_question["choices"]):
                button = document.createElement("button")
                button.id = f"cafe-twist-choice-{index}"
                button.innerText = choice
                button.className = "choice"
                proxy = create_proxy(_make_cafe_twist_choice_handler(choice))
                button.addEventListener("click", proxy)
                cafe_twist_choice_proxies.append(proxy)
                twist_choices_box.appendChild(button)
            _cafe_rendered_twist = cafe_twist_question
    else:
        twist_panel.hidden = True
        _destroy_cafe_twist_proxies()
        twist_choices_box.innerHTML = ""
        _cafe_rendered_twist = None


def _setup_cafe():
    _element("cafe-toggle-button").addEventListener("click", create_proxy(on_toggle_cafe))
    _element("cafe-start-button").addEventListener("click", create_proxy(start_cafe))
    _element("cafe-close-button").addEventListener("click", create_proxy(close_cafe))
