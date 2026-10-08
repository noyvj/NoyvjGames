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
_credit_plot_id = None
_credit_item = None
_credit_reset = None
_credit_text = None
_plot_for_fr = None
_pref_get = None
_pref_set = None
_check_answer = None


def _credit(question, mode):
    """A correct answer on a real plot: hand it to game.py's plot-growth
    credit (water_plot: the first correct answer for a plot each in-game day
    waters it, a later one nudges it; see game.py's "Watering versus
    nudging"). Returns "full", "nudge" or None. A no-op standalone."""
    if _credit_plot_id is not None and question is not None:
        return _credit_plot_id(question.get("plot_id"), mode)
    return None


def _credit_fr(fr_texts, mode):
    """Credit every plot behind a list of French texts; returns the list of
    results ("full" / "nudge" / None, one per text)."""
    results = []
    if _credit_item is not None:
        for fr in fr_texts:
            results.append(_credit_item(fr, mode))
    return results


def _reset_credit(mode):
    if _credit_reset is not None:
        _credit_reset(mode)


def _with_growth(message, mode):
    if _credit_text is None:
        return message
    return f"{message} {_credit_text(mode)}"


def _record(mode, correct):
    """Feed one answered question into game.py's practice-progress ledger
    (see game.py's "practice progress" build note). A no-op when nothing was
    wired in, so the module stays usable standalone."""
    if _record_practice is not None:
        _record_practice(mode, bool(correct))


def configure(
    farm,
    generate_question_fn,
    variants_for_fn,
    record_practice_fn=None,
    credit_plot_fn=None,
    credit_item_fn=None,
    credit_reset_fn=None,
    credit_text_fn=None,
    plot_for_fr_fn=None,
    pref_get_fn=None,
    pref_set_fn=None,
    check_answer_fn=None,
):
    """Called once from game.py's setup(): hands in the live FarmState plus
    the two question-generation functions every minigame reuses rather than
    re-deriving vocab/distractor selection from scratch (per the brief)."""
    global _farm, _generate_question, _variants_for, _record_practice
    global _credit_plot_id, _credit_item, _credit_reset, _credit_text
    global _plot_for_fr, _pref_get, _pref_set, _check_answer
    _record_practice = record_practice_fn
    _credit_plot_id = credit_plot_fn
    _credit_item = credit_item_fn
    _credit_reset = credit_reset_fn
    _credit_text = credit_text_fn
    _plot_for_fr = plot_for_fr_fn
    _pref_get = pref_get_fn
    _pref_set = pref_set_fn
    _check_answer = check_answer_fn
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


# --- shared arcade infrastructure (2026-10-08) -------------------------------
# Difficulty, the "waters: <plot>" line and the typed-answer box are shared by
# every minigame, old and new.

# Difficulty. Every minigame has a Slower / Normal / Faster setting (a drop-down
# in its panel, remembered per game in this browser through game.py's pref
# helpers). It changes only the pressure: timer length, number of lives, the
# rival's pace or the patience clock. The WATERING rule never changes with
# difficulty, and neither do the practice-ledger points (1 per correct answer,
# with the same daily and lifetime caps, at every level, so Faster cannot be
# farmed and Slower is not penalised). Only the game's own score is scaled a
# little (DIFFICULTY_SCORE_PERCENT) so a harder run reads as worth more.
DIFFICULTY_LEVELS = ("slower", "normal", "faster")
DIFFICULTY_LABELS = {"slower": "Slower", "normal": "Normal", "faster": "Faster"}
DIFFICULTY_SCORE_PERCENT = {"slower": 80, "normal": 100, "faster": 125}
PREF_DIFFICULTY_PREFIX = "champ-difficulty-"
_difficulty = {}


def get_difficulty(key):
    value = _difficulty.get(key)
    if value is None:
        stored = _pref_get(PREF_DIFFICULTY_PREFIX + key) if _pref_get is not None else None
        value = stored if stored in DIFFICULTY_LEVELS else "normal"
        _difficulty[key] = value
    return value


def set_difficulty(key, value):
    if value not in DIFFICULTY_LEVELS:
        return get_difficulty(key)
    _difficulty[key] = value
    if _pref_set is not None:
        _pref_set(PREF_DIFFICULTY_PREFIX + key, value)
    render()
    return value


def difficulty_points(key, points):
    """A game-score award scaled by the difficulty (ledger points are not)."""
    return round(points * DIFFICULTY_SCORE_PERCENT[get_difficulty(key)] / 100)


def _make_difficulty_handler(key):
    def handler(event=None):
        set_difficulty(key, _element(f"{key}-difficulty-select").value)
    return handler


def _setup_difficulty(key):
    select = _element(f"{key}-difficulty-select")
    select.innerHTML = ""
    for level in DIFFICULTY_LEVELS:
        option = document.createElement("option")
        option.value = level
        option.innerText = DIFFICULTY_LABELS[level]
        select.appendChild(option)
    select.value = get_difficulty(key)
    select.addEventListener("change", create_proxy(_make_difficulty_handler(key)))


def _render_difficulty(key, running, describe):
    """Show the chosen level and what it means; it cannot change mid-run."""
    level = get_difficulty(key)
    select = _element(f"{key}-difficulty-select")
    select.value = level
    select.disabled = bool(running)
    _element(f"{key}-difficulty-note").innerText = describe(level)


# "waters: <plot>" -- which plot an answer waters, shown under every question
# before it is answered, then what the answer did.
def plot_label(plot_id):
    plot = _farm.plots_by_id.get(plot_id) if _farm is not None else None
    return plot.label if plot is not None else ""


def context_line(question):
    """The small line above a prompt: where the plot is from and what to do."""
    instruction = question.get("instruction")
    return f"{question['context']} · {instruction}" if instruction else question["context"]


def labels_for_fr(fr_texts):
    """Plot labels behind a list of French texts (the shop games' orders)."""
    labels = []
    if _plot_for_fr is not None:
        for fr in fr_texts:
            plot = _plot_for_fr(fr)
            if plot is not None and plot.label not in labels:
                labels.append(plot.label)
    return labels


def waters_text(labels):
    labels = [label for label in labels if label]
    return "Waters: " + " + ".join(labels) if labels else ""


def _kind_word(kind):
    return {"full": "watered", "nudge": "nudged"}.get(kind, "already done today")


def answer_note(label, correct, kinds):
    """One line about what the last answer did to its plot(s): `kinds` is the
    list of water results ("full" / "nudge" / None) for the credited plots."""
    if correct is False:
        return f"Missed: {label} is unchanged." if label else "Missed: nothing changes."
    words = sorted({_kind_word(k) for k in kinds}) if kinds else []
    if not words:
        return ""
    return f"{label}: {' and '.join(words)}." if label else f"{' and '.join(words).capitalize()}."


def _check(question, given):
    """Grade an answer: multiple choice is exact, a typed answer goes through
    game.py's normal grading (tiers, accents setting)."""
    if _check_answer is not None:
        return bool(_check_answer(question, given))
    return given == question["answer"]


def _is_typed(question):
    return question is not None and question.get("mode") == "typed"


def _format_arg(question_format=None):
    return question_format


def _build_answer_area(key, question, box, proxies, submit):
    """Fill `box` with the answer controls for a generated question: four
    choice buttons, or (for a plot that has grown, see game.py's progressive
    format) a text box and a Check button. `submit(given)` takes the choice
    text or the typed text."""
    box.innerHTML = ""
    if _is_typed(question):
        field = document.createElement("input")
        field.id = f"{key}-typed-input"
        field.className = "practice-input"
        field.setAttribute("type", "text")
        field.setAttribute("autocomplete", "off")
        field.setAttribute("autocapitalize", "none")
        field.setAttribute("spellcheck", "false")
        field.setAttribute("placeholder", "Type your answer")
        check = document.createElement("button")
        check.id = f"{key}-typed-submit"
        check.className = "secondary"
        check.innerText = "Check"

        def go(event=None):
            submit(field.value)

        def on_key(event=None):
            if event is not None and getattr(event, "key", None) == "Enter":
                try:
                    event.preventDefault()
                except Exception:
                    pass
                go()

        for element, name, handler in ((check, "click", go), (field, "keydown", on_key)):
            proxy = create_proxy(handler)
            element.addEventListener(name, proxy)
            proxies.append(proxy)
        box.appendChild(field)
        box.appendChild(check)
        try:
            field.focus()
        except Exception:
            pass
        return
    for index, choice in enumerate(question["choices"]):
        button = document.createElement("button")
        button.id = f"{key}-choice-{index}"
        button.innerText = choice
        button.className = "choice"
        proxy = create_proxy(_make_choice_submit(submit, choice))
        button.addEventListener("click", proxy)
        proxies.append(proxy)
        box.appendChild(button)


def _make_choice_submit(submit, choice):
    def handler(event=None):
        submit(choice)
    return handler


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
    render_sprint()
    for game in NEW_GAMES:
        game.render()


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
    _setup_sprint()
    for game in NEW_GAMES:
        game.setup()
    # Faux Amis: show the last read list straight away (it feeds the farm's false-friend
    # badges) and read the live page again in the background when there is none or it is old.
    load_amis_cache()
    if amis_status != "ready" or amis_cache_is_stale():
        fetch_amis()


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
# Slower / Normal / Faster: how long the run lasts and how many lives you get.
BLITZ_DIFFICULTY = {
    "slower": {"seconds": 90, "lives": 5},
    "normal": {"seconds": BLITZ_DURATION_SECONDS, "lives": BLITZ_STARTING_LIVES},
    "faster": {"seconds": 45, "lives": 2},
}

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
blitz_note = ""  # what the last answer did to its plot
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
    global blitz_time_remaining, blitz_end_reason, blitz_open, blitz_note

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
    blitz_lives = _blitz_params()["lives"]
    blitz_combo = 0
    blitz_time_remaining = _blitz_params()["seconds"]
    blitz_end_reason = None
    blitz_note = ""
    _reset_credit("blitz")
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
    global blitz_score, blitz_combo, blitz_lives, blitz_note

    if not blitz_active or blitz_question is None:
        return None
    correct = _check(blitz_question, given)
    _record("blitz", correct)
    label = plot_label(blitz_question["plot_id"])
    if correct:
        kind = _credit(blitz_question, "blitz")
        blitz_note = answer_note(label, True, [kind])
        blitz_combo += 1
        blitz_score += difficulty_points("blitz", round(BLITZ_BASE_POINTS * _blitz_multiplier(blitz_combo)))
    else:
        blitz_note = answer_note(label, False, [])
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
    global blitz_open, blitz_active, blitz_question, blitz_end_reason, blitz_note
    blitz_open = False
    blitz_active = False
    blitz_question = None
    blitz_end_reason = None
    blitz_note = ""
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

    _render_difficulty("blitz", blitz_active, _blitz_describe)
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
        _element("blitz-waters").innerText = ""
        start_button.hidden = reason is not None
        start_button.innerText = "Play again" if blitz_end_reason is not None else f"Start ({_blitz_params()['seconds']}s)"
        summary.hidden = blitz_end_reason is None
        if blitz_end_reason == BLITZ_END_TIME:
            summary.innerText = _with_growth(BLITZ_SUMMARY_MESSAGE.format(score=blitz_score, best=blitz_best_score), "blitz")
        elif blitz_end_reason == BLITZ_END_LIVES:
            summary.innerText = _with_growth(BLITZ_LIVES_MESSAGE.format(score=blitz_score, best=blitz_best_score), "blitz")
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
        _element("blitz-context").innerText = context_line(blitz_question)
        _element("blitz-prompt").innerText = blitz_question["prompt"]
        _element("blitz-feedback").innerText = blitz_note
        _element("blitz-waters").innerText = waters_text([plot_label(blitz_question["plot_id"])])
        _build_answer_area("blitz", blitz_question, choices_box, blitz_choice_proxies, submit_blitz_choice)
        _blitz_rendered_question = blitz_question


def _setup_blitz():
    _setup_difficulty("blitz")
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

racer_open = False
racer_active = False
racer_player_position = 0
racer_rival_position = 0
racer_tick_count = 0  # ticks since the rival's last step
racer_question = None
racer_result = None  # None | True | False -- last attempt, transient UI flash
racer_end_reason = None  # None | RACER_END_PLAYER | RACER_END_RIVAL
racer_choice_proxies = []
racer_note = ""  # what the last answer did to its plot
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
    global racer_tick_count, racer_result, racer_end_reason, racer_note

    if not racer_available() or not _racer_candidate_plots():
        return None
    racer_open = True
    racer_active = True
    racer_player_position = 0
    racer_rival_position = 0
    racer_tick_count = 0
    racer_result = None
    racer_end_reason = None
    racer_note = ""
    _reset_credit("racer")
    _roll_racer_question()
    render()
    return racer_question


def _end_racer(reason):
    global racer_active, racer_end_reason, racer_question
    racer_active = False
    racer_end_reason = reason
    racer_question = None


def submit_racer_choice(given):
    global racer_player_position, racer_result, racer_note

    if not racer_active or racer_question is None:
        return None
    racer_result = _check(racer_question, given)
    _record("racer", racer_result)
    label = plot_label(racer_question["plot_id"])
    if racer_result:
        kind = _credit(racer_question, "racer")
        racer_note = answer_note(label, True, [kind])
        racer_player_position += 1
        if racer_player_position >= RACER_TOTAL_STEPS:
            _end_racer(RACER_END_PLAYER)
            render()
            return racer_result
    else:
        racer_note = answer_note(label, False, [])
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
    if racer_tick_count >= RACER_DIFFICULTY[get_difficulty("racer")]["rival_ticks"]:
        racer_tick_count = 0
        racer_rival_position += 1
        if racer_rival_position >= RACER_TOTAL_STEPS:
            _end_racer(RACER_END_RIVAL)
    render()
    return racer_rival_position


def close_racer(event=None):
    global racer_open, racer_active, racer_question, racer_result, racer_end_reason, racer_note
    racer_note = ""
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

    _render_difficulty("racer", racer_active, _racer_describe)
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
        _element("racer-waters").innerText = ""
        start_button.hidden = reason is not None
        start_button.innerText = "Race again" if racer_end_reason is not None else "Start the race"
        summary.hidden = racer_end_reason is None
        if racer_end_reason == RACER_END_PLAYER:
            summary.innerText = _with_growth(RACER_PLAYER_WIN_MESSAGE.format(
                player=racer_player_position, total=RACER_TOTAL_STEPS
            ), "racer")
        elif racer_end_reason == RACER_END_RIVAL:
            summary.innerText = _with_growth(RACER_RIVAL_WIN_MESSAGE.format(
                player=racer_player_position, total=RACER_TOTAL_STEPS
            ), "racer")
        return

    start_button.hidden = True
    summary.hidden = True

    if racer_result is False:
        _element("racer-feedback").innerText = "Not this turn — try the next one. " + racer_note
    else:
        _element("racer-feedback").innerText = racer_note

    # Same identity-based rebuild-only-on-change fix Blitz's own live
    # verification found necessary -- see that milestone's build note.
    if racer_question is not _racer_rendered_question:
        _destroy_racer_choice_proxies()
        _element("racer-context").innerText = context_line(racer_question)
        _element("racer-prompt").innerText = racer_question["prompt"]
        _element("racer-waters").innerText = waters_text([plot_label(racer_question["plot_id"])])
        _build_answer_area("racer", racer_question, choices_box, racer_choice_proxies, submit_racer_choice)
        _racer_rendered_question = racer_question


def _setup_racer():
    _setup_difficulty("racer")
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
boutique_note = ""  # what the last sale did to its plots
BOUTIQUE_RNG = random.Random()
# Slower / Normal / Faster: how long a customer waits (seconds) at the start of
# the shift and the shortest the wait ever gets as sales speed the pace up.
BOUTIQUE_DIFFICULTY = {
    "slower": {"start": 18, "min": 9},
    "normal": {"start": BOUTIQUE_STARTING_PATIENCE, "min": BOUTIQUE_MIN_PATIENCE},
    "faster": {"start": 8, "min": 4},
}


def _boutique_params():
    return BOUTIQUE_DIFFICULTY[get_difficulty("boutique")]


def _boutique_describe(level):
    p = BOUTIQUE_DIFFICULTY[level]
    return f"{DIFFICULTY_LABELS[level]}: customers wait {p['start']} seconds, never less than {p['min']}."


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
    boutique_order = {
        "order_en": order_en,
        "answer": answer,
        "choices": choices,
        "credit_fr": [garment_fr, colour_masc],
    }


def start_boutique(event=None):
    global boutique_open, boutique_active, boutique_served, boutique_missed
    global boutique_score, boutique_patience_max, boutique_patience_remaining
    global boutique_last_result, boutique_note

    if not boutique_available() or not _boutique_garment_entries() or not _boutique_colour_entries():
        return None
    boutique_open = True
    boutique_active = True
    boutique_served = 0
    boutique_missed = 0
    boutique_score = 0
    boutique_patience_max = _boutique_params()["start"]
    boutique_patience_remaining = boutique_patience_max
    boutique_last_result = None
    boutique_note = ""
    _reset_credit("boutique")
    _roll_boutique_order()
    render()
    return boutique_order


def _resolve_boutique_customer(served):
    """Shared by a submitted choice and a timeout (boutique_tick()) -- either
    way, this customer's outcome is exactly the same shape: served or not,
    tally it, maybe speed up, then either end the shift or bring in the
    next customer."""
    global boutique_served, boutique_missed, boutique_score, boutique_patience_max
    global boutique_active, boutique_order, boutique_patience_remaining, boutique_last_result, boutique_note

    boutique_last_result = served
    _record("boutique", served)
    labels = labels_for_fr(boutique_order.get("credit_fr", ())) if boutique_order is not None else []
    if served:
        kinds = []
        if boutique_order is not None:
            kinds = _credit_fr(boutique_order.get("credit_fr", ()), "boutique")
        boutique_note = answer_note(" + ".join(labels), True, kinds)
        boutique_served += 1
        boutique_score += difficulty_points("boutique", BOUTIQUE_BASE_POINTS)
        boutique_patience_max = max(_boutique_params()["min"], boutique_patience_max - BOUTIQUE_PATIENCE_STEP)
    else:
        boutique_note = answer_note(" + ".join(labels), False, [])
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
    global boutique_open, boutique_active, boutique_order, boutique_last_result, boutique_note
    boutique_note = ""
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

    _render_difficulty("boutique", boutique_active, _boutique_describe)
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
        _element("boutique-waters").innerText = ""
        fill = _element("boutique-patience-fill")
        fill.style.width = "100%"
        fill.className = "shop-rush-patience-fill"
        start_button.hidden = reason is not None
        start_button.innerText = "Open again" if completed > 0 else "Open the shop"
        summary.hidden = completed < BOUTIQUE_TOTAL_CUSTOMERS
        if completed >= BOUTIQUE_TOTAL_CUSTOMERS:
            summary.innerText = _with_growth(BOUTIQUE_SUMMARY_MESSAGE.format(
                served=boutique_served, total=BOUTIQUE_TOTAL_CUSTOMERS,
                missed=boutique_missed, score=boutique_score,
            ), "boutique")
        return

    start_button.hidden = True
    summary.hidden = True

    pct = round((boutique_patience_remaining / boutique_patience_max) * 100) if boutique_patience_max else 0
    fill = _element("boutique-patience-fill")
    fill.style.width = f"{pct}%"
    low = boutique_patience_remaining <= max(2, round(boutique_patience_max * 0.3))
    fill.className = "shop-rush-patience-fill shop-rush-patience-fill--low" if low else "shop-rush-patience-fill"

    if boutique_last_result is False:
        _element("boutique-feedback").innerText = "Not this time — next customer, please. " + boutique_note
    elif boutique_last_result is True:
        _element("boutique-feedback").innerText = "Sold! " + boutique_note
    else:
        _element("boutique-feedback").innerText = ""

    if boutique_order is not _boutique_rendered_order:
        _destroy_boutique_choice_proxies()
        _element("boutique-order").innerText = f"A customer wants: {boutique_order['order_en']}."
        _element("boutique-waters").innerText = waters_text(labels_for_fr(boutique_order.get("credit_fr", ())))
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
    _setup_difficulty("boutique")
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
cafe_note = ""  # what the last customer's order did to its plots
CAFE_RNG = random.Random()
CAFE_DIFFICULTY = {
    "slower": {"start": 18, "min": 9},
    "normal": {"start": CAFE_STARTING_PATIENCE, "min": CAFE_MIN_PATIENCE},
    "faster": {"start": 8, "min": 4},
}


def _cafe_params():
    return CAFE_DIFFICULTY[get_difficulty("cafe")]


def _cafe_describe(level):
    p = CAFE_DIFFICULTY[level]
    return f"{DIFFICULTY_LABELS[level]}: customers wait {p['start']} seconds, never less than {p['min']}."


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
    cafe_order = {"order_en": answer_en, "answer": answer_fr, "choices": choices, "credit_fr": [answer_fr]}


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
    global cafe_patience_max, cafe_customer_index, cafe_last_result, cafe_note

    if not cafe_available() or not _cafe_food_entries():
        return None
    cafe_open = True
    cafe_active = True
    cafe_served = 0
    cafe_missed = 0
    cafe_score = 0
    cafe_patience_max = _cafe_params()["start"]
    cafe_customer_index = 0
    cafe_last_result = None
    cafe_note = ""
    _reset_credit("cafe")
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
        cafe_score += difficulty_points(
            "cafe", CAFE_BASE_POINTS + (CAFE_TWIST_BONUS_POINTS if cafe_stage == CAFE_STAGE_TWIST else 0)
        )
    else:
        cafe_missed += 1
    if speed_up:
        cafe_patience_max = max(_cafe_params()["min"], cafe_patience_max - CAFE_PATIENCE_STEP)

    if cafe_served + cafe_missed >= CAFE_TOTAL_CUSTOMERS:
        cafe_active = False
        cafe_order = None
        cafe_stage = CAFE_STAGE_PICK
        cafe_twist_question = None
    else:
        _roll_cafe_customer()


def submit_cafe_item_choice(given):
    global cafe_stage, cafe_twist_question, cafe_note

    if not cafe_active or cafe_order is None or cafe_stage != CAFE_STAGE_PICK:
        return None
    correct = given == cafe_order["answer"]
    labels = labels_for_fr(cafe_order.get("credit_fr", ()))
    if not correct:
        cafe_note = answer_note(" + ".join(labels), False, [])
        _resolve_cafe_customer(served=False, speed_up=False)
        render()
        return False
    kinds = _credit_fr(cafe_order.get("credit_fr", ()), "cafe")
    cafe_note = answer_note(" + ".join(labels), True, kinds)

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
    global cafe_note
    if not cafe_active or cafe_stage != CAFE_STAGE_TWIST or cafe_twist_question is None:
        return None
    correct = _check(cafe_twist_question, given)
    twist_label = plot_label(cafe_twist_question["plot_id"])
    if correct:
        kind = _credit(cafe_twist_question, "cafe")
        cafe_note = (cafe_note + " " + answer_note(twist_label, True, [kind])).strip()
    else:
        cafe_note = (cafe_note + " " + answer_note(twist_label, False, [])).strip()
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
    global cafe_open, cafe_active, cafe_order, cafe_stage, cafe_twist_question, cafe_last_result, cafe_note
    cafe_note = ""
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

    _render_difficulty("cafe", cafe_active, _cafe_describe)
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
        _element("cafe-waters").innerText = ""
        twist_panel.hidden = True
        fill = _element("cafe-patience-fill")
        fill.style.width = "100%"
        fill.className = "shop-rush-patience-fill"
        start_button.hidden = reason is not None
        start_button.innerText = "Open again" if completed > 0 else "Open the café"
        summary.hidden = completed < CAFE_TOTAL_CUSTOMERS
        if completed >= CAFE_TOTAL_CUSTOMERS:
            summary.innerText = _with_growth(CAFE_SUMMARY_MESSAGE.format(
                served=cafe_served, total=CAFE_TOTAL_CUSTOMERS,
                missed=cafe_missed, score=cafe_score,
            ), "cafe")
        return

    start_button.hidden = True
    summary.hidden = True

    pct = round((cafe_patience_remaining / cafe_patience_max) * 100) if cafe_patience_max else 0
    fill = _element("cafe-patience-fill")
    fill.style.width = f"{pct}%"
    low = cafe_patience_remaining <= max(2, round(cafe_patience_max * 0.3))
    fill.className = "shop-rush-patience-fill shop-rush-patience-fill--low" if low else "shop-rush-patience-fill"

    if cafe_last_result is False:
        _element("cafe-feedback").innerText = "Not this time — next customer, please. " + cafe_note
    elif cafe_last_result is True:
        _element("cafe-feedback").innerText = "Sold! " + cafe_note
    else:
        _element("cafe-feedback").innerText = ""

    if cafe_order is not _cafe_rendered_order:
        _destroy_cafe_choice_proxies()
        _element("cafe-order").innerText = f"A customer wants: {cafe_order['order_en']}."
        _element("cafe-waters").innerText = waters_text(labels_for_fr(cafe_order.get("credit_fr", ())))
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
            _element("cafe-twist-context").innerText = context_line(cafe_twist_question)
            _element("cafe-twist-prompt").innerText = cafe_twist_question["prompt"]
            _element("cafe-twist-waters").innerText = waters_text([plot_label(cafe_twist_question["plot_id"])])
            _build_answer_area(
                "cafe-twist", cafe_twist_question, twist_choices_box, cafe_twist_choice_proxies, submit_cafe_twist_choice
            )
            _cafe_rendered_twist = cafe_twist_question
    else:
        twist_panel.hidden = True
        _destroy_cafe_twist_proxies()
        twist_choices_box.innerHTML = ""
        _cafe_rendered_twist = None


def _setup_cafe():
    _setup_difficulty("cafe")
    _element("cafe-toggle-button").addEventListener("click", create_proxy(on_toggle_cafe))
    _element("cafe-start-button").addEventListener("click", create_proxy(start_cafe))
    _element("cafe-close-button").addEventListener("click", create_proxy(close_cafe))


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
SPRINT_DURATION_SECONDS = 60
SPRINT_STARTING_LIVES = 3
SPRINT_BASE_POINTS = 10
SPRINT_COMBO_STEP = 3  # every N correct-in-a-row raises the multiplier once
SPRINT_COMBO_BONUS_PER_STEP = 0.5
SPRINT_MAX_COMBO_STEPS = 4  # multiplier caps at 1 + 4*0.5 = 3.0x

SPRINT_VARIANTS = {VARIANT_BLANK_WORD, VARIANT_CONJUGATION_SWAP}

SPRINT_END_TIME = "time"
SPRINT_END_LIVES = "lives"
SPRINT_DIFFICULTY = {
    "slower": {"seconds": 90, "lives": 5},
    "normal": {"seconds": SPRINT_DURATION_SECONDS, "lives": SPRINT_STARTING_LIVES},
    "faster": {"seconds": 45, "lives": 2},
}

sprint_open = False  # panel toggled open, independent of a live run
sprint_active = False  # a 60s run is currently in progress
sprint_score = 0
sprint_best_score = 0  # best across runs *this page load* -- session-only
sprint_lives = SPRINT_STARTING_LIVES
sprint_combo = 0
sprint_time_remaining = SPRINT_DURATION_SECONDS
sprint_question = None
sprint_end_reason = None  # None | SPRINT_END_TIME | SPRINT_END_LIVES
sprint_choice_proxies = []
sprint_note = ""  # what the last answer did to its plot
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


_sprint_candidates_cache = None


def _sprint_candidate_plots():
    """Computed once per session (this module's own lifetime -- a fresh
    farm/fresh module in the test harness naturally gets a fresh cache) and
    memoized, since the *set* of plots capable of a translate variant is an
    intrinsic catalog property that doesn't change as the farm grows (see
    sprint_available()'s note on why this must stay lazy, never eager)."""
    global _sprint_candidates_cache
    if _sprint_candidates_cache is None:
        _sprint_candidates_cache = [
            p
            for p in _unlocked_range_plots(SPRINT_LO, SPRINT_HI)
            if p.topic_id in CAFE_PASSE_COMPOSE_TOPIC_IDS and any(v in SPRINT_VARIANTS for v in _variants_for(p))
        ]
    return _sprint_candidates_cache


def _sprint_multiplier(combo):
    steps = min(combo // SPRINT_COMBO_STEP, SPRINT_MAX_COMBO_STEPS)
    return 1.0 + steps * SPRINT_COMBO_BONUS_PER_STEP


def _roll_sprint_question():
    global sprint_question
    candidates = _sprint_candidate_plots()
    plot = SPRINT_RNG.choice(candidates)
    variants = [v for v in _variants_for(plot) if v in SPRINT_VARIANTS]
    variant = SPRINT_RNG.choice(variants)
    sprint_question = _generate_question(plot, SPRINT_RNG, variant=variant)


def start_sprint(event=None):
    global sprint_active, sprint_score, sprint_lives, sprint_combo
    global sprint_time_remaining, sprint_end_reason, sprint_open, sprint_note

    # sprint_available() is a cheap row-unlock-only proxy (see its own
    # docstring); the real candidate pool is only actually computed here,
    # so this is also where an edge case with genuinely zero eligible plots
    # (never observed in practice, but not provably impossible) is caught
    # rather than crashing on SPRINT_RNG.choice([]).
    if not sprint_available() or not _sprint_candidate_plots():
        return None
    sprint_open = True
    sprint_active = True
    sprint_score = 0
    sprint_lives = _sprint_params()["lives"]
    sprint_combo = 0
    sprint_time_remaining = _sprint_params()["seconds"]
    sprint_end_reason = None
    sprint_note = ""
    _reset_credit("sprint")
    _roll_sprint_question()
    render()
    return sprint_question


def _end_sprint(reason):
    global sprint_active, sprint_end_reason, sprint_best_score, sprint_question
    sprint_active = False
    sprint_end_reason = reason
    sprint_best_score = max(sprint_best_score, sprint_score)
    sprint_question = None


def submit_sprint_choice(given):
    global sprint_score, sprint_combo, sprint_lives, sprint_note

    if not sprint_active or sprint_question is None:
        return None
    correct = _check(sprint_question, given)
    _record("sprint", correct)
    label = plot_label(sprint_question["plot_id"])
    if correct:
        kind = _credit(sprint_question, "sprint")
        sprint_note = answer_note(label, True, [kind])
        sprint_combo += 1
        sprint_score += difficulty_points("sprint", round(SPRINT_BASE_POINTS * _sprint_multiplier(sprint_combo)))
    else:
        sprint_note = answer_note(label, False, [])
        sprint_combo = 0
        sprint_lives -= 1
    if sprint_lives <= 0:
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
    global sprint_time_remaining
    if not sprint_active:
        return None
    sprint_time_remaining -= 1
    if sprint_time_remaining <= 0:
        sprint_time_remaining = 0
        _end_sprint(SPRINT_END_TIME)
    render()
    return sprint_time_remaining


def close_sprint(event=None):
    global sprint_open, sprint_active, sprint_question, sprint_end_reason, sprint_note
    sprint_note = ""
    sprint_open = False
    sprint_active = False
    sprint_question = None
    sprint_end_reason = None
    render()


def on_toggle_sprint(event=None):
    global sprint_open
    if sprint_open:
        close_sprint()
    else:
        sprint_open = True
        render()


def _make_sprint_choice_handler(choice):
    def handler(event=None):
        submit_sprint_choice(choice)
    return handler


SPRINT_SUMMARY_MESSAGE = "Time's up! Score: {score} (best this session: {best})."
SPRINT_LIVES_MESSAGE = "Out of lives for this round. Score: {score} (best this session: {best})."


_sprint_rendered_question = None  # identity tracker -- see the note below


def render_sprint():
    global _sprint_rendered_question

    toggle = _element("sprint-toggle-button")
    panel = _element("sprint-panel")
    choices_box = _element("sprint-choices")

    available = sprint_available()
    toggle.disabled = not sprint_open and not available
    toggle.innerText = "Close Sprint" if sprint_open else "⏪ Passé Composé Sprint"

    if not sprint_open:
        panel.hidden = True
        _destroy_sprint_choice_proxies()
        choices_box.innerHTML = ""
        _sprint_rendered_question = None
        return

    panel.hidden = False
    lock_message = _element("sprint-lock-message")
    reason = sprint_lock_reason()
    lock_message.hidden = reason is None
    lock_message.innerText = reason or ""

    start_button = _element("sprint-start-button")
    summary = _element("sprint-summary")

    _render_difficulty("sprint", sprint_active, _sprint_describe)
    _element("sprint-time-display").innerText = f"{sprint_time_remaining}s"
    _element("sprint-lives-display").innerText = "❤" * max(sprint_lives, 0) or "0 lives"
    _element("sprint-score-display").innerText = f"Score: {sprint_score}"
    _element("sprint-combo-display").innerText = (
        f"Combo x{_sprint_multiplier(sprint_combo):.1f}" if sprint_combo >= SPRINT_COMBO_STEP else ""
    )

    if not sprint_active:
        _destroy_sprint_choice_proxies()
        choices_box.innerHTML = ""
        _sprint_rendered_question = None
        _element("sprint-context").innerText = ""
        _element("sprint-prompt").innerText = ""
        _element("sprint-feedback").innerText = ""
        _element("sprint-waters").innerText = ""
        start_button.hidden = reason is not None
        start_button.innerText = "Play again" if sprint_end_reason is not None else f"Start ({_sprint_params()['seconds']}s)"
        summary.hidden = sprint_end_reason is None
        if sprint_end_reason == SPRINT_END_TIME:
            summary.innerText = _with_growth(SPRINT_SUMMARY_MESSAGE.format(score=sprint_score, best=sprint_best_score), "sprint")
        elif sprint_end_reason == SPRINT_END_LIVES:
            summary.innerText = _with_growth(SPRINT_LIVES_MESSAGE.format(score=sprint_score, best=sprint_best_score), "sprint")
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
    if sprint_question is not _sprint_rendered_question:
        _destroy_sprint_choice_proxies()
        _element("sprint-context").innerText = context_line(sprint_question)
        _element("sprint-prompt").innerText = sprint_question["prompt"]
        _element("sprint-feedback").innerText = sprint_note
        _element("sprint-waters").innerText = waters_text([plot_label(sprint_question["plot_id"])])
        _build_answer_area("sprint", sprint_question, choices_box, sprint_choice_proxies, submit_sprint_choice)
        _sprint_rendered_question = sprint_question


def _setup_sprint():
    _setup_difficulty("sprint")
    _element("sprint-toggle-button").addEventListener("click", create_proxy(on_toggle_sprint))
    _element("sprint-start-button").addEventListener("click", create_proxy(start_sprint))
    _element("sprint-close-button").addEventListener("click", create_proxy(close_sprint))


# ===========================================================================
# 2026-10-08 -- four new arcade games for the weeks the first five do not reach
# ===========================================================================
#
# Word Match (vocabulary and phrases, weeks 12-23), Grammar Gaps (fill the gap
# in the grammar of the weeks Blitz, Racer and the Sprint do not ask gaps
# about), Listening Pick (hear it, pick what it means; vocabulary, phrases and
# pronunciation items) and Word Order Race (put an example sentence's words in
# order). Each draws only on content already in the catalog, is row-unlock-
# gated like the others, waters real plots (the line under every question names
# them), feeds the practice ledger and has a Slower / Normal / Faster setting.
# The four share one small base class so each game is only its own rules.

_speak = None
_speech_ok = None


def configure_speech(speak_fn=None, speech_ok_fn=None):
    """game.py hands in its speak_french / speech_available (they use the
    page's own voices; both are quiet no-ops without them)."""
    global _speak, _speech_ok
    _speak = speak_fn
    _speech_ok = speech_ok_fn


def _can_hear():
    return bool(_speech_ok()) if _speech_ok is not None else False


def _say(text, slow=False):
    if _speak is not None:
        _speak(text, slow)


def _can_water(plot):
    return plot.last_watered != _farm.current_day


def _prefer_unwatered(plots, minimum):
    """Plots that can still be fully watered today, unless there are too few
    of them to build a round (then everything, so a game is always playable)."""
    fresh = [p for p in plots if _can_water(p)]
    return fresh if len(fresh) >= minimum else plots


class _Arcade:
    """The frame every new game shares: panel, start / close, timer and lives
    display, difficulty, summary, growth line. A subclass supplies its pool,
    how a round is built and drawn, and what an answer does."""

    key = ""
    lo, hi = 1, 23
    open_label = ""
    close_label = ""
    start_label = "Start"
    again_label = "Play again"
    difficulty_table = {}
    base_points = 10

    def __init__(self):
        self.open = False
        self.active = False
        self.score = 0
        self.best = 0
        self.lives = 0
        self.combo = 0
        self.time_remaining = 0
        self.end_reason = None
        self.note = ""
        self.round = None
        self.rendered = None
        self.proxies = []
        self.rng = random.Random()
        self._pool = None

    # --- hooks --------------------------------------------------------
    def build_pool(self):
        raise NotImplementedError

    def new_round(self):
        raise NotImplementedError

    def draw_round(self):
        raise NotImplementedError

    def clear_round_ui(self):
        pass

    def waters_labels(self):
        return []

    def describe(self, level):
        p = self.difficulty_table[level]
        return f"{DIFFICULTY_LABELS[level]}: {p['seconds']} seconds and {p['lives']} lives."

    def summary_text(self):
        return f"Time's up! Score: {self.score} (best this session: {self.best})."

    def lives_text(self):
        return f"Out of lives for this round. Score: {self.score} (best this session: {self.best})."

    def cleared_text(self):
        return f"Round complete! Score: {self.score} (best this session: {self.best})."

    # --- shared -------------------------------------------------------
    def el(self, suffix):
        return _element(f"{self.key}-{suffix}")

    def params(self):
        return self.difficulty_table[get_difficulty(self.key)]

    def pool(self):
        if self._pool is None:
            self._pool = self.build_pool()
        return self._pool

    def available(self):
        return _range_fully_unlocked(self.lo, self.hi)

    def lock_reason(self):
        return None if self.available() else _lock_reason(self.hi)

    def multiplier(self, combo):
        return 1.0 + min(combo // 3, 4) * 0.5

    def award(self, base=None):
        """Score for one right answer (combo multiplier, then difficulty)."""
        base = self.base_points if base is None else base
        return difficulty_points(self.key, round(base * self.multiplier(self.combo)))

    def start(self, event=None):
        if not self.available() or not self.pool():
            return None
        self.open = True
        self.active = True
        self.score = 0
        self.combo = 0
        self.lives = self.params().get("lives", 0)
        self.time_remaining = self.params().get("seconds", 0)
        self.end_reason = None
        self.note = ""
        self.rendered = None
        _reset_credit(self.key)
        self.begin()
        self.new_round()
        render()
        return self.round

    def begin(self):
        """Per-game reset at the start of a run."""

    def end(self, reason):
        self.active = False
        self.end_reason = reason
        self.best = max(self.best, self.score)
        self.round = None

    def tick(self, event=None):
        if not self.active:
            return None
        self.time_remaining -= 1
        if self.time_remaining <= 0:
            self.time_remaining = 0
            self.on_time_up()
        else:
            self.on_tick()
        render()
        return self.time_remaining

    def on_time_up(self):
        self.end("time")

    def on_tick(self):
        pass

    def close(self, event=None):
        self.open = False
        self.active = False
        self.round = None
        self.end_reason = None
        self.note = ""
        self.rendered = None
        render()

    def toggle(self, event=None):
        if self.open:
            self.close()
        else:
            self.open = True
            render()

    def open_panel(self):
        self.open = True
        render()

    def destroy_proxies(self):
        for proxy in self.proxies:
            proxy.destroy()
        self.proxies.clear()

    # stats line; subclasses override when they do not use a clock/lives
    def stats(self):
        return {
            "time": f"{self.time_remaining}s",
            "lives": "❤" * max(self.lives, 0) or "0 lives",
            "score": f"Score: {self.score}",
            "combo": f"Combo x{self.multiplier(self.combo):.1f}" if self.combo >= 3 else "",
        }

    def render(self):
        toggle = self.el("toggle-button")
        panel = self.el("panel")
        available = self.available()
        toggle.disabled = not self.open and not available
        toggle.innerText = self.close_label if self.open else self.open_label
        if not self.open:
            panel.hidden = True
            self.destroy_proxies()
            self.clear_round_ui()
            self.rendered = None
            return
        panel.hidden = False
        reason = self.lock_reason()
        lock = self.el("lock-message")
        lock.hidden = reason is None
        lock.innerText = reason or ""
        _render_difficulty(self.key, self.active, self.describe)
        values = self.stats()
        self.el("time-display").innerText = values["time"]
        self.el("lives-display").innerText = values["lives"]
        self.el("score-display").innerText = values["score"]
        self.el("combo-display").innerText = values["combo"]
        start = self.el("start-button")
        summary = self.el("summary")
        if not self.active:
            self.destroy_proxies()
            self.clear_round_ui()
            self.rendered = None
            self.el("feedback").innerText = ""
            self.el("waters").innerText = ""
            start.hidden = reason is not None
            start.innerText = self.again_label if self.end_reason is not None else self.start_label
            summary.hidden = self.end_reason is None
            if self.end_reason == "time":
                text = self.summary_text()
            elif self.end_reason == "lives":
                text = self.lives_text()
            elif self.end_reason == "cleared":
                text = self.cleared_text()
            else:
                text = ""
            summary.innerText = _with_growth(text, self.key) if text else ""
            return
        start.hidden = True
        summary.hidden = True
        if self.round is not self.rendered:
            self.destroy_proxies()
            self.el("feedback").innerText = self.note
            self.el("waters").innerText = waters_text(self.waters_labels())
            self.draw_round()
            self.rendered = self.round
        else:
            self.refresh_round()

    def refresh_round(self):
        """Light repaint on a clock tick (the round itself did not change)."""

    def setup(self):
        _setup_difficulty(self.key)
        self.el("toggle-button").addEventListener("click", create_proxy(self.toggle))
        self.el("start-button").addEventListener("click", create_proxy(self.start))
        self.el("close-button").addEventListener("click", create_proxy(self.close))
        self.setup_extra()

    def setup_extra(self):
        pass


# ---------------------------------------------------------------------------
# Word Match: pairs of French and English cards (vocabulary and phrases, 12-23)
# ---------------------------------------------------------------------------
PAIRS_LO, PAIRS_HI = 12, 23
PAIRS_PER_BOARD = 4
PAIRS_BOARDS = 3
PAIRS_MAX_FR = 22
PAIRS_MAX_EN = 30
PAIRS_BAD_CHARS = set("[]+/…{}<>")
PAIRS_DIFFICULTY = {
    "slower": {"seconds": 150, "lives": 6},
    "normal": {"seconds": 90, "lives": 3},
    "faster": {"seconds": 60, "lives": 2},
}


class _PairsGame(_Arcade):
    boards_done = 0
    selected = None
    key = "pairs"
    lo, hi = PAIRS_LO, PAIRS_HI
    open_label = "🔗 Word Match"
    close_label = "Close Word Match"
    start_label = "Start matching"
    again_label = "Match again"
    difficulty_table = PAIRS_DIFFICULTY

    def build_pool(self):
        plots = []
        for sequence in range(self.lo, self.hi + 1):
            if not _farm.is_row_unlocked(sequence):
                continue
            for plot in _farm.row_plots(sequence):
                if plot.topic_type not in ("vocab", "phrase") or len(plot.items) != 1:
                    continue
                fr = _strip_parens(plot.items[0]["fr"])
                en = _strip_parens(plot.items[0]["en"])
                if not fr or not en or len(fr) > PAIRS_MAX_FR or len(en) > PAIRS_MAX_EN:
                    continue
                if PAIRS_BAD_CHARS & set(plot.items[0]["fr"] + plot.items[0]["en"]):
                    continue
                plots.append(plot)
        return plots

    def begin(self):
        self.boards_done = 0
        self.selected = None

    def pick_plots(self):
        pool = _prefer_unwatered(self.pool(), PAIRS_PER_BOARD * 2)
        for _ in range(60):
            chosen = self.rng.sample(pool, PAIRS_PER_BOARD)
            frs = {_strip_parens(p.items[0]["fr"]).lower() for p in chosen}
            ens = {_strip_parens(p.items[0]["en"]).lower() for p in chosen}
            if len(frs) == PAIRS_PER_BOARD and len(ens) == PAIRS_PER_BOARD:
                return chosen
        return self.rng.sample(pool, PAIRS_PER_BOARD)

    def new_round(self):
        plots = self.pick_plots()
        cards = []
        for plot in plots:
            item = plot.items[0]
            cards.append({"side": "fr", "plot_id": plot.plot_id, "text": _strip_parens(item["fr"])})
            cards.append({"side": "en", "plot_id": plot.plot_id, "text": _strip_parens(item["en"])})
        self.rng.shuffle(cards)
        for index, card in enumerate(cards):
            card["id"] = index
            card["matched"] = False
        self.selected = None
        self.round = {"cards": cards, "plots": [p.plot_id for p in plots]}

    def waters_labels(self):
        return [plot_label(pid) for pid in self.round["plots"]] if self.round else []

    def select(self, card_id):
        """Tap a card. First tap selects, the second (on the other language)
        tries the pair. Returns True / False for a tried pair, None otherwise."""
        if not self.active or self.round is None:
            return None
        cards = self.round["cards"]
        if not 0 <= card_id < len(cards) or cards[card_id]["matched"]:
            return None
        card = cards[card_id]
        if self.selected is None or cards[self.selected]["side"] == card["side"]:
            self.selected = None if self.selected == card_id else card_id
            render()
            return None
        first = cards[self.selected]
        self.selected = None
        correct = first["plot_id"] == card["plot_id"]
        _record(self.key, correct)
        label = plot_label(card["plot_id"])
        if correct:
            first["matched"] = card["matched"] = True
            kind = _credit_plot_id(card["plot_id"], self.key) if _credit_plot_id is not None else None
            self.note = answer_note(label, True, [kind])
            self.combo += 1
            self.score += self.award()
            if all(c["matched"] for c in cards):
                self.boards_done += 1
                if self.boards_done >= PAIRS_BOARDS:
                    self.score += difficulty_points(self.key, max(0, self.time_remaining))
                    self.end("cleared")
                    render()
                    return True
                self.new_round()
        else:
            self.note = "Not a pair: nothing changes for either plot."
            self.combo = 0
            self.lives -= 1
            if self.lives <= 0:
                self.end("lives")
        render()
        return correct

    def clear_round_ui(self):
        self.el("board").innerHTML = ""

    def cleared_text(self):
        return (
            f"Board cleared! All {PAIRS_BOARDS} boards matched with {self.time_remaining}s to spare. "
            f"Score: {self.score} (best this session: {self.best})."
        )

    def draw_round(self):
        board = self.el("board")
        board.innerHTML = ""
        self.el("progress").innerText = f"Board {self.boards_done + 1} of {PAIRS_BOARDS}"
        for card in self.round["cards"]:
            button = document.createElement("button")
            button.id = f"pairs-card-{card['id']}"
            button.className = "choice pairs-card pairs-card--" + card["side"]
            button.innerText = card["text"]
            proxy = create_proxy(self.make_handler(card["id"]))
            button.addEventListener("click", proxy)
            self.proxies.append(proxy)
            board.appendChild(button)
        self.paint_cards()

    def make_handler(self, card_id):
        def handler(event=None):
            self.select(card_id)
        return handler

    def paint_cards(self):
        board = self.el("board")
        by_id = {c["id"]: c for c in self.round["cards"]}
        for button in board.children:
            try:
                card_id = int(button.id.rsplit("-", 1)[1])
            except (ValueError, IndexError):
                continue
            card = by_id[card_id]
            classes = "choice pairs-card pairs-card--" + card["side"]
            if card["matched"]:
                classes += " choice--answer"
                button.disabled = True
            elif self.selected == card_id:
                classes += " pairs-card--selected"
            button.className = classes
            button.setAttribute("aria-pressed", "true" if self.selected == card_id else "false")

    def refresh_round(self):
        self.el("feedback").innerText = self.note
        self.paint_cards()


# ---------------------------------------------------------------------------
# Grammar Gaps: timed fill-the-gap over the grammar the other games skip
# ---------------------------------------------------------------------------
GAPS_LO, GAPS_HI = 1, 23
GAPS_VARIANTS = {VARIANT_BLANK_WORD, VARIANT_BLANK_ENDING, VARIANT_CONJUGATION_SWAP}
# A rule that is only a list of forms ("je mets / tu mets / il met") has no gap
# to fill; it is asked as "which English matches this example?" instead, so that
# every grammar plot has an arcade game.
GAPS_FALLBACK_VARIANTS = {VARIANT_EXAMPLE_FR_EN, VARIANT_EXAMPLE_EN_FR}
GAPS_DIFFICULTY = {
    "slower": {"seconds": 90, "lives": 5},
    "normal": {"seconds": 60, "lives": 3},
    "faster": {"seconds": 45, "lives": 2},
}


class _GapsGame(_Arcade):
    key = "gaps"
    lo, hi = GAPS_LO, GAPS_HI
    open_label = "🧩 Grammar Gaps"
    close_label = "Close Grammar Gaps"
    start_label = "Start"
    difficulty_table = GAPS_DIFFICULTY

    def build_pool(self):
        plots = []
        for sequence in range(self.lo, self.hi + 1):
            if not _farm.is_row_unlocked(sequence) or RACER_LO <= sequence <= RACER_HI:
                continue
            for plot in _farm.row_plots(sequence):
                if plot.topic_type != "grammar":
                    continue
                # The passé composé has its own Sprint, unless a rule there has no gap for
                # the Sprint to ask (the être verbs are a list): then it is asked here.
                if plot.topic_id in CAFE_PASSE_COMPOSE_TOPIC_IDS and any(
                    v in SPRINT_VARIANTS for v in _variants_for(plot)
                ):
                    continue
                if self.variants_of(plot):
                    plots.append(plot)
        return plots

    def variants_of(self, plot):
        offered = _variants_for(plot)
        return [v for v in offered if v in GAPS_VARIANTS] or [v for v in offered if v in GAPS_FALLBACK_VARIANTS]

    def new_round(self):
        pool = _prefer_unwatered(self.pool(), 8)
        plot = self.rng.choice(pool)
        self.round = _generate_question(plot, self.rng, variant=self.rng.choice(self.variants_of(plot)))

    def waters_labels(self):
        return [plot_label(self.round["plot_id"])] if self.round else []

    def submit(self, given):
        if not self.active or self.round is None:
            return None
        question = self.round
        correct = _check(question, given)
        _record(self.key, correct)
        label = plot_label(question["plot_id"])
        if correct:
            kind = _credit(question, self.key)
            self.note = answer_note(label, True, [kind])
            self.combo += 1
            self.score += self.award()
        else:
            self.note = answer_note(label, False, [])
            self.combo = 0
            self.lives -= 1
        if self.lives <= 0:
            self.end("lives")
        else:
            self.new_round()
        render()
        return correct

    def clear_round_ui(self):
        self.el("choices").innerHTML = ""
        self.el("context").innerText = ""
        self.el("prompt").innerText = ""

    def draw_round(self):
        self.el("context").innerText = context_line(self.round)
        self.el("prompt").innerText = self.round["prompt"]
        _build_answer_area(self.key, self.round, self.el("choices"), self.proxies, self.submit)

    def refresh_round(self):
        pass


# ---------------------------------------------------------------------------
# Listening Pick: hear the French, pick what it means
# ---------------------------------------------------------------------------
LISTEN_LO, LISTEN_HI = 1, 23
LISTEN_QUESTIONS = 10
LISTEN_VARIANTS = (VARIANT_FR_EN_CHOICE, VARIANT_SYMBOL_NAME_CHOICE)
LISTEN_DIFFICULTY = {
    "slower": {"seconds": 25, "lives": 6},
    "normal": {"seconds": 15, "lives": 3},
    "faster": {"seconds": 9, "lives": 2},
}
LISTEN_HIDDEN_PROMPT = "🔊 Listen, then pick what it means."


class _ListenGame(_Arcade):
    asked = 0
    revealed = False
    key = "listenpick"
    lo, hi = LISTEN_LO, LISTEN_HI
    open_label = "🎧 Listening Pick"
    close_label = "Close Listening Pick"
    start_label = "Start listening"
    again_label = "Listen again"
    difficulty_table = LISTEN_DIFFICULTY

    def describe(self, level):
        p = self.difficulty_table[level]
        return f"{DIFFICULTY_LABELS[level]}: {p['seconds']} seconds to answer each of {LISTEN_QUESTIONS} questions, {p['lives']} lives."

    def build_pool(self):
        plots = []
        for sequence in range(self.lo, self.hi + 1):
            if not _farm.is_row_unlocked(sequence):
                continue
            for plot in _farm.row_plots(sequence):
                if plot.topic_type != "grammar" and any(v in LISTEN_VARIANTS for v in _variants_for(plot)):
                    plots.append(plot)
        return plots

    def begin(self):
        self.asked = 0
        self.revealed = False
        self.question_seconds = self.params()["seconds"]
        self.time_remaining = self.question_seconds

    def new_round(self):
        pool = _prefer_unwatered(self.pool(), 10)
        plot = self.rng.choice(pool)
        variant = self.rng.choice([v for v in _variants_for(plot) if v in LISTEN_VARIANTS])
        self.round = _generate_question(plot, self.rng, variant=variant)
        self.asked += 1
        self.revealed = False
        self.time_remaining = self.question_seconds
        _say(self.round["prompt"])

    def waters_labels(self):
        if not self.round:
            return []
        # The French text is the answer's giveaway, so while it is hidden the line only
        # says that a plot is being watered; the note after the answer names it.
        if self.hidden():
            return ["the word you are hearing"]
        return [plot_label(self.round["plot_id"])]

    def hidden(self):
        return _can_hear() and not self.revealed

    def stats(self):
        values = super().stats()
        values["combo"] = f"Question {min(self.asked, LISTEN_QUESTIONS)} of {LISTEN_QUESTIONS}"
        return values

    def on_time_up(self):
        # The clock for one question ran out: a miss, and on to the next.
        if self.round is not None:
            self.settle(False, timed_out=True)

    def settle(self, correct, timed_out=False):
        question = self.round
        label = plot_label(question["plot_id"])
        _record(self.key, correct)
        if correct:
            kind = _credit(question, self.key)
            self.note = answer_note(label, True, [kind])
            self.combo += 1
            self.score += self.award()
        else:
            reason = "Time ran out. " if timed_out else ""
            self.note = reason + answer_note(label, False, []) + f" It was: {question['prompt']} = {question['answer']}."
            self.combo = 0
            self.lives -= 1
        if self.lives <= 0:
            self.end("lives")
        elif self.asked >= LISTEN_QUESTIONS:
            self.end("cleared")
        else:
            self.new_round()

    def submit(self, given):
        if not self.active or self.round is None:
            return None
        correct = _check(self.round, given)
        self.settle(correct)
        render()
        return correct

    def cleared_text(self):
        return f"All {LISTEN_QUESTIONS} heard! Score: {self.score} (best this session: {self.best})."

    def clear_round_ui(self):
        self.el("choices").innerHTML = ""
        self.el("context").innerText = ""
        self.el("prompt").innerText = ""
        self.el("play-button").hidden = True
        self.el("slow-button").hidden = True
        self.el("show-button").hidden = True

    def draw_round(self):
        self.el("context").innerText = context_line(self.round)
        self.el("prompt").innerText = LISTEN_HIDDEN_PROMPT if self.hidden() else self.round["prompt"]
        can_hear = _can_hear()
        self.el("play-button").hidden = not can_hear
        self.el("slow-button").hidden = not can_hear
        self.el("show-button").hidden = not self.hidden()
        _build_answer_area(self.key, self.round, self.el("choices"), self.proxies, self.submit)

    def reveal(self, event=None):
        if self.round is None:
            return
        self.revealed = True
        self.el("prompt").innerText = self.round["prompt"]
        self.el("waters").innerText = waters_text(self.waters_labels())
        self.el("show-button").hidden = True

    def replay(self, event=None):
        if self.round is not None:
            _say(self.round["prompt"])

    def replay_slow(self, event=None):
        if self.round is not None:
            _say(self.round["prompt"], True)

    def setup_extra(self):
        self.el("play-button").addEventListener("click", create_proxy(self.replay))
        self.el("slow-button").addEventListener("click", create_proxy(self.replay_slow))
        self.el("show-button").addEventListener("click", create_proxy(self.reveal))


# ---------------------------------------------------------------------------
# Word Order Race: put an example sentence's words in order
# ---------------------------------------------------------------------------
ORDER_LO, ORDER_HI = 1, 23
ORDER_SENTENCES = 6
ORDER_MIN_WORDS, ORDER_MAX_WORDS = 3, 8
ORDER_BAD_CHARS = set("[]+/…{}()<>→")
ORDER_DIFFICULTY = {
    "slower": {"seconds": 60, "lives": 0},
    "normal": {"seconds": 40, "lives": 0},
    "faster": {"seconds": 25, "lives": 0},
}


class _OrderGame(_Arcade):
    done = 0
    painted = None
    key = "wordorder"
    lo, hi = ORDER_LO, ORDER_HI
    open_label = "🧱 Word Order Race"
    close_label = "Close Word Order Race"
    start_label = "Start the race"
    again_label = "Race again"
    difficulty_table = ORDER_DIFFICULTY
    base_points = 10

    def describe(self, level):
        p = self.difficulty_table[level]
        return f"{DIFFICULTY_LABELS[level]}: {p['seconds']} seconds for each of {ORDER_SENTENCES} sentences. A miss costs nothing but the points."

    def eligible_items(self, plot):
        items = []
        for item in plot.items:
            fr = item["fr"].strip()
            words = fr.split()
            if not ORDER_MIN_WORDS <= len(words) <= ORDER_MAX_WORDS:
                continue
            if ORDER_BAD_CHARS & set(fr) or not item.get("en"):
                continue
            if len(set(words)) < 2:
                continue
            items.append(item)
        return items

    def build_pool(self):
        plots = []
        for sequence in range(self.lo, self.hi + 1):
            if not _farm.is_row_unlocked(sequence):
                continue
            for plot in _farm.row_plots(sequence):
                if plot.topic_type == "grammar" and self.eligible_items(plot):
                    plots.append(plot)
        return plots

    def begin(self):
        self.done = 0
        self.placed = []
        self.painted = None
        self.used_plots = set()
        self.question_seconds = self.params()["seconds"]
        self.time_remaining = self.question_seconds

    def stats(self):
        values = super().stats()
        values["lives"] = ""
        values["combo"] = f"Sentence {min(self.done + 1, ORDER_SENTENCES)} of {ORDER_SENTENCES}"
        return values

    def new_round(self):
        pool = [p for p in self.pool() if p.plot_id not in self.used_plots] or self.pool()
        pool = _prefer_unwatered(pool, 4)
        plot = self.rng.choice(pool)
        self.used_plots.add(plot.plot_id)
        item = self.rng.choice(self.eligible_items(plot))
        words = item["fr"].strip().split()
        order = list(range(len(words)))
        for _ in range(12):
            self.rng.shuffle(order)
            if [words[i] for i in order] != words:
                break
        self.placed = []
        self.time_remaining = self.question_seconds
        self.round = {
            "plot_id": plot.plot_id,
            "answer": " ".join(words),
            "words": words,
            "order": order,
            "en": item["en"].strip(),
        }

    def waters_labels(self):
        return [plot_label(self.round["plot_id"])] if self.round else []

    def on_time_up(self):
        if self.round is not None:
            self.settle(False, timed_out=True)

    def settle(self, correct, timed_out=False):
        question = self.round
        label = plot_label(question["plot_id"])
        _record(self.key, correct)
        if correct:
            kind = _credit_plot_id(question["plot_id"], self.key) if _credit_plot_id is not None else None
            self.note = answer_note(label, True, [kind])
            self.combo += 1
            self.score += self.award(self.base_points + max(0, self.time_remaining) // 4)
        else:
            reason = "Time ran out. " if timed_out else ""
            self.note = reason + answer_note(label, False, []) + f" The sentence was: {question['answer']}"
            self.combo = 0
        self.done += 1
        if self.done >= ORDER_SENTENCES:
            self.end("cleared")
        else:
            self.new_round()

    def place(self, tile_index):
        """Tap a tile in the pool (an index into the shuffled order). When the
        last tile is placed the sentence is checked."""
        if not self.active or self.round is None or tile_index in self.placed:
            return None
        if not 0 <= tile_index < len(self.round["order"]):
            return None
        self.placed.append(tile_index)
        if len(self.placed) < len(self.round["order"]):
            render()
            return None
        built = [self.round["words"][self.round["order"][i]] for i in self.placed]
        correct = built == self.round["words"]
        self.settle(correct)
        render()
        return correct

    def undo(self, event=None):
        if self.active and self.placed:
            self.placed.pop()
            render()

    def cleared_text(self):
        return f"All {ORDER_SENTENCES} sentences done! Score: {self.score} (best this session: {self.best})."

    def clear_round_ui(self):
        self.el("pool").innerHTML = ""
        self.el("placed").innerHTML = ""
        self.el("prompt").innerText = ""
        self.el("undo-button").hidden = True

    def draw_round(self):
        self.el("prompt").innerText = self.round["en"]
        self.paint_tiles()

    def paint_tiles(self):
        self.destroy_proxies()
        self.painted = tuple(self.placed)
        pool, placed_box = self.el("pool"), self.el("placed")
        pool.innerHTML = ""
        placed_box.innerHTML = ""
        words, order = self.round["words"], self.round["order"]
        for tile_index in self.placed:
            chip = document.createElement("span")
            chip.className = "bonus-tile bonus-tile--placed"
            chip.innerText = words[order[tile_index]]
            placed_box.appendChild(chip)
        for tile_index, word_index in enumerate(order):
            if tile_index in self.placed:
                continue
            button = document.createElement("button")
            button.id = f"wordorder-tile-{tile_index}"
            button.className = "choice bonus-tile"
            button.innerText = words[word_index]
            proxy = create_proxy(self.make_handler(tile_index))
            button.addEventListener("click", proxy)
            self.proxies.append(proxy)
            pool.appendChild(button)
        self.el("undo-button").hidden = not self.placed

    def make_handler(self, tile_index):
        def handler(event=None):
            self.place(tile_index)
        return handler

    def refresh_round(self):
        # Repaint the tiles only when one was placed or taken back: a clock tick
        # must not rebuild buttons under a finger.
        if tuple(self.placed) != self.painted:
            self.paint_tiles()

    def setup_extra(self):
        self.el("undo-button").addEventListener("click", create_proxy(self.undo))


# ---------------------------------------------------------------------------
# Faux Amis: false friends, read live from a reputable list (TODO L-15, L-16)
# ---------------------------------------------------------------------------
# The list is the French Wiktionary's "Annexe:Faux-amis anglais-français"
# (CC BY-SA), read from the live page and named on screen. Nothing from it is
# bundled: the parsed entries are cached in this browser (never in the save
# code) so the farm badges (L-16) can show before the page is read again, and
# the game itself always asks for a fresh read when it is opened.
#
# Not plot-linked: the words come from the list, not from the player's farm, so
# the game says "Does not grow plots", and its answers feed the practice ledger
# (mode "amis"). Where a plot's French word is on the list, that plot carries a
# small "false friend" badge and tooltip instead (game.py asks amis_for_plot).
AMIS_PAGE_TITLE = "Annexe:Faux-amis anglais-français"
AMIS_PAGE_URL = "https://fr.wiktionary.org/wiki/Annexe:Faux-amis_anglais-fran%C3%A7ais"
AMIS_API_URL = (
    "https://fr.wiktionary.org/w/api.php?action=query&prop=revisions&rvprop=content&rvslots=main"
    "&format=json&formatversion=2&origin=*&titles=Annexe%3AFaux-amis%20anglais-fran%C3%A7ais"
)
AMIS_SOURCE_NAME = "French Wiktionary, “Annexe:Faux-amis anglais-français” (CC BY-SA)"
AMIS_CACHE_KEY = "champ-amis-cache"
AMIS_CACHE_DAYS = 7
AMIS_QUESTIONS = 10
AMIS_MIN_ENTRIES = 12
AMIS_DIFFICULTY = {
    "slower": {"seconds": 30, "lives": 6},
    "normal": {"seconds": 18, "lives": 3},
    "faster": {"seconds": 10, "lives": 2},
}
AMIS_WORD_RE = re.compile(r"^[a-zà-ÿœ'’-]{3,16}$")
_AMIS_ARTICLE_RE = re.compile(r"^(?:(?:le|la|les|un|une|des|du|de la)\s+|l'|de l')")

amis_entries = []  # [{"en", "fr", "means", "partial"}]
amis_status = "idle"  # idle, loading, ready, failed
amis_read_date = ""  # YYYY-MM-DD of the read the entries come from
amis_from_cache = False
amis_error = ""
_amis_by_word = {}
_amis_plot_cache = {}
on_amis_loaded = None  # game.py sets this to its render()


def parse_amis(text):
    """Entries from the page's wikitext: each "* ''english''" headline followed
    by "** fr : word (n m) : ''meaning''" lines. Keeps single-word pairs with a
    short plain meaning, drops anything that reads as commentary."""
    entries = []
    head, partial = None, False
    for line in str(text).splitlines():
        match = re.match(r"^\* ''([^'\n]+)''(.*)$", line)
        if match:
            head = match.group(1).strip().lower()
            partial = "fa p" in match.group(2)
            continue
        if head is None:
            continue
        match = re.match(r"^\*\* fr : (.+)$", line)
        if not match:
            continue
        body = match.group(1)
        if " : " not in body:
            continue
        before, tail = body.split(" : ", 1)
        before = re.sub(r"\([^)]*\)", " ", before).strip().lower()
        before = _AMIS_ARTICLE_RE.sub("", before).strip()
        if " " in before or not AMIS_WORD_RE.match(before) or not AMIS_WORD_RE.match(head):
            continue
        tail = tail.split(" mais ")[0]
        means = [m.strip() for m in re.findall(r"''([^'\n]+)''", tail)]
        means = [m for m in means if 2 <= len(m) <= 24 and "(" not in m and m.lower() != head]
        if not means:
            continue
        entries.append({"en": head, "fr": before, "means": means[:3], "partial": partial})
    return entries


def _amis_pack(entries):
    return [[e["en"], e["fr"], e["means"], 1 if e["partial"] else 0] for e in entries]


def _amis_unpack(rows):
    entries = []
    for row in rows if isinstance(rows, list) else []:
        if (
            isinstance(row, list) and len(row) == 4 and isinstance(row[0], str) and isinstance(row[1], str)
            and isinstance(row[2], list) and row[2] and all(isinstance(m, str) for m in row[2])
        ):
            entries.append({"en": row[0], "fr": row[1], "means": row[2][:3], "partial": bool(row[3])})
    return entries


def _amis_today():
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return ""
    hook = getattr(window, "studyToday", None)
    value = hook() if hook is not None else ""
    return value if isinstance(value, str) else ""


def _amis_days_between(older, newer):
    """Whole days between two YYYY-MM-DD strings (no datetime: see game.py)."""
    import calendar  # noqa: PLC0415

    def stamp(value):
        year, month, day = (int(part) for part in value.split("-"))
        return calendar.timegm((year, month, day, 0, 0, 0))

    try:
        return (stamp(newer) - stamp(older)) // 86400
    except (ValueError, TypeError):
        return 10 ** 6


def _amis_set(entries, date, cached):
    global amis_entries, amis_read_date, amis_from_cache, amis_status, _amis_by_word
    amis_entries = list(entries)
    amis_read_date = date
    amis_from_cache = cached
    amis_status = "ready" if len(amis_entries) >= AMIS_MIN_ENTRIES else "failed"
    _amis_by_word = {}
    for entry in amis_entries:
        _amis_by_word.setdefault(entry["fr"], entry)
    _amis_plot_cache.clear()
    AMIS.reset_pool()


def load_amis_cache():
    """Show what the last read found, until (or instead of) a fresh read."""
    if _pref_get is None:
        return False
    raw = _pref_get(AMIS_CACHE_KEY)
    if not raw:
        return False
    try:
        import json  # noqa: PLC0415
        data = json.loads(raw)
    except (TypeError, ValueError):
        return False
    entries = _amis_unpack(data.get("entries") if isinstance(data, dict) else None)
    date = data.get("date") if isinstance(data, dict) and isinstance(data.get("date"), str) else ""
    if len(entries) < AMIS_MIN_ENTRIES:
        return False
    _amis_set(entries, date, True)
    return True


def amis_cache_is_stale():
    today = _amis_today()
    if not amis_read_date or not today:
        return True
    return _amis_days_between(amis_read_date, today) >= AMIS_CACHE_DAYS


def fetch_amis(force=False):
    """Ask the page (window.championFetchText, see index.html) for the live
    list. Returns True when a request was started."""
    global amis_status, amis_error
    if amis_status == "loading":
        return False
    try:
        from js import window  # noqa: PLC0415
    except ImportError:
        return False
    hook = getattr(window, "championFetchText", None)
    if hook is None:
        return False
    amis_status = "loading" if not amis_entries else amis_status
    amis_error = ""

    def on_text(text):
        global amis_status, amis_error
        try:
            import json  # noqa: PLC0415
            content = json.loads(str(text))["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
            entries = parse_amis(content)
        except (KeyError, IndexError, TypeError, ValueError):
            entries = []
        if len(entries) < AMIS_MIN_ENTRIES:
            on_error("The list could not be read.")
            return
        date = _amis_today()
        _amis_set(entries, date, False)
        if _pref_set is not None:
            import json  # noqa: PLC0415
            _pref_set(AMIS_CACHE_KEY, json.dumps({"date": date, "entries": _amis_pack(entries)}))
        _amis_changed()

    def on_error(reason=None):
        global amis_status, amis_error
        amis_error = str(reason) if isinstance(reason, str) else "The list could not be reached."
        if not amis_entries:
            amis_status = "failed"
        _amis_changed()

    try:
        promise = hook(AMIS_API_URL)
        promise.then(create_proxy(on_text), create_proxy(on_error))
    except Exception:  # noqa: BLE001 -- a broken fetch hook must never break the page
        on_error("The list could not be reached.")
        return False
    return True


def _amis_changed():
    if on_amis_loaded is not None:
        on_amis_loaded()
    else:
        render()


def amis_source_line():
    """The line under the game's title: what it reads, from where, and when."""
    if amis_status == "loading":
        return f"Reading {AMIS_SOURCE_NAME} now..."
    if amis_status == "ready":
        if amis_from_cache:
            when = f"on {amis_read_date}" if amis_read_date else "earlier"
            extra = f" A fresh read failed ({amis_error})" if amis_error else ""
            return f"Source: {AMIS_SOURCE_NAME}. Showing the copy read {when}.{extra}"
        return f"Source: {AMIS_SOURCE_NAME}, read live on {amis_read_date or 'today'}."
    if amis_status == "failed":
        return f"Source: {AMIS_SOURCE_NAME}. It could not be read just now ({amis_error or 'no connection'}); try again later."
    return f"Source: {AMIS_SOURCE_NAME}, read live when this panel opens."


def amis_for_word(word):
    return _amis_by_word.get(str(word).strip().lower())


def _amis_plot_words(fr_text):
    words = []
    for piece in re.split(r"\s*/\s*", re.sub(r"\([^)]*\)", "", str(fr_text))):
        piece = _AMIS_ARTICLE_RE.sub("", piece.strip().lower()).strip(" .!?")
        if piece and " " not in piece:
            words.append(piece)
    return words


def amis_for_plot(plot):
    """The list entry for a plot's French word, or None (cached per plot)."""
    if not _amis_by_word or plot is None:
        return None
    key = plot.plot_id
    if key not in _amis_plot_cache:
        found = None
        for item in plot.items:
            for word in _amis_plot_words(item.get("fr", "")):
                entry = _amis_by_word.get(word)
                if entry is not None and not entry["partial"] and word != entry["means"][0].lower():
                    # the farm's own English already says the look-alike (a "chef" that is a chef):
                    # then there is nothing to warn about for this plot
                    english = " " + re.sub(r"[^a-z' ]", " ", str(item.get("en", "")).lower()) + " "
                    if f" {entry['en']} " in english:
                        continue
                    found = entry
                    break
            if found:
                break
        _amis_plot_cache[key] = found
    return _amis_plot_cache[key]


def amis_plot_note(plot):
    entry = amis_for_plot(plot)
    if entry is None:
        return ""
    means = " or ".join(entry["means"][:2])
    return f"false friend: “{entry['fr']}” looks like English “{entry['en']}” but means {means}"


def _amis_similarity(entry):
    import difflib  # noqa: PLC0415
    return difflib.SequenceMatcher(None, entry["fr"], entry["en"]).ratio()


class _AmisGame(_Arcade):
    key = "amis"
    open_label = "\U0001F575 Faux Amis"
    close_label = "Close Faux Amis"
    start_label = "Start Faux Amis"
    again_label = "Play again"
    difficulty_table = AMIS_DIFFICULTY
    asked = 0
    run = ()

    def describe(self, level):
        p = self.difficulty_table[level]
        return f"{DIFFICULTY_LABELS[level]}: {p['seconds']} seconds for each of {AMIS_QUESTIONS} questions, {p['lives']} lives."

    def reset_pool(self):
        self._pool = None

    def build_pool(self):
        return [e for e in amis_entries if not e["partial"] and e["en"] not in [m.lower() for m in e["means"]]]

    def available(self):
        return True

    def lock_reason(self):
        if amis_status == "ready":
            return None
        if amis_status == "loading":
            return "Reading the list now. This takes a moment."
        return "The list could not be read just now, so there is nothing to ask. Close this panel and open it again later."

    def toggle(self, event=None):
        opening = not self.open
        super().toggle(event)
        if opening:
            fetch_amis()

    def open_panel(self):
        super().open_panel()
        fetch_amis()

    def start(self, event=None):
        if amis_status != "ready" or len(self.pool()) < AMIS_MIN_ENTRIES:
            return None
        return super().start(event)

    def begin(self):
        entries = self.pool()
        picked = self.rng.sample(entries, min(AMIS_QUESTIONS, len(entries)))
        # increasingly sneaky: the pairs that look least alike first, the near-twins last
        picked.sort(key=_amis_similarity)
        self.run = picked
        self.asked = 0
        self.question_seconds = self.params()["seconds"]
        self.time_remaining = self.question_seconds

    def _distractors(self, entry, count):
        pool = self.pool()
        banned = {entry["en"].lower()} | {m.lower() for m in entry["means"]}
        options = []
        for other in self.rng.sample(pool, min(len(pool), 40)):
            meaning = other["means"][0]
            if meaning.lower() not in banned and meaning.lower() not in {o.lower() for o in options}:
                options.append(meaning)
            if len(options) == count:
                break
        return options

    def new_round(self):
        entry = self.run[self.asked]
        true_meaning = entry["means"][0]
        choices = [true_meaning, entry["en"]] + self._distractors(entry, 2)
        self.rng.shuffle(choices)
        self.round = {
            "mode": "choice",
            "plot_id": None,
            "variant": "amis",
            "context": f"Looks like the English “{entry['en']}”",
            "instruction": "What does this French word really mean?",
            "prompt": entry["fr"],
            "choices": choices,
            "answer": true_meaning,
            "entry": entry,
        }
        self.asked += 1
        self.time_remaining = self.question_seconds

    def waters_labels(self):
        return []

    def stats(self):
        values = super().stats()
        values["combo"] = f"Question {min(self.asked, AMIS_QUESTIONS)} of {len(self.run) or AMIS_QUESTIONS}"
        return values

    def on_time_up(self):
        if self.round is not None:
            self.settle(False, timed_out=True)

    def settle(self, correct, timed_out=False):
        question = self.round
        entry = question["entry"]
        _record(self.key, correct)
        said = f"“{entry['fr']}” means {question['answer']}, not “{entry['en']}”."
        if correct:
            self.note = "Yes: " + said
            self.combo += 1
            self.score += self.award()
        else:
            self.note = ("Time ran out. " if timed_out else "Not quite. ") + said
            self.combo = 0
            self.lives -= 1
        if self.lives <= 0:
            self.end("lives")
        elif self.asked >= len(self.run):
            self.end("cleared")
        else:
            self.new_round()

    def submit(self, given):
        if not self.active or self.round is None:
            return None
        correct = _check(self.round, given)
        self.settle(correct)
        render()
        return correct

    def cleared_text(self):
        return f"All {len(self.run)} asked! Score: {self.score} (best this session: {self.best})."

    def clear_round_ui(self):
        self.el("choices").innerHTML = ""
        self.el("context").innerText = ""
        self.el("prompt").innerText = ""

    def draw_round(self):
        self.el("context").innerText = context_line(self.round)
        self.el("prompt").innerText = self.round["prompt"]
        _build_answer_area(self.key, self.round, self.el("choices"), self.proxies, self.submit)

    def render(self):
        super().render()
        self.el("source").innerText = amis_source_line()


PAIRS = _PairsGame()
GAPS = _GapsGame()
LISTENPICK = _ListenGame()
WORDORDER = _OrderGame()
AMIS = _AmisGame()
NEW_GAMES = (PAIRS, GAPS, LISTENPICK, WORDORDER, AMIS)


def pairs_tick(event=None):
    return PAIRS.tick()


def gaps_tick(event=None):
    return GAPS.tick()


def listenpick_tick(event=None):
    return LISTENPICK.tick()


def wordorder_tick(event=None):
    return WORDORDER.tick()


def amis_tick(event=None):
    return AMIS.tick()


def any_timed_run_active():
    """True while any arcade minigame has a countdown running. The page's
    one-second JS timer asks this when the tab is hidden (shared/pause-hidden.js),
    so the "paused while the tab was hidden" note only shows when a run
    really was held. Reads state only; never moves a clock."""
    if blitz_active or racer_active or boutique_active or cafe_active or sprint_active:
        return True
    return any(game.active for game in NEW_GAMES)


def pairs_available():
    return PAIRS.available()


def start_pairs(event=None):
    return PAIRS.start()


def start_gaps(event=None):
    return GAPS.start()


def start_listenpick(event=None):
    return LISTENPICK.start()


def start_wordorder(event=None):
    return WORDORDER.start()


# ---------------------------------------------------------------------------
# "Water by minigame": what each game waters, for game.py's Water options
# ---------------------------------------------------------------------------
def _plots_for_fr_texts(fr_texts):
    seen, plots = set(), []
    for fr in fr_texts:
        plot = _plot_for_fr(fr) if _plot_for_fr is not None else None
        if plot is not None and plot.plot_id not in seen:
            seen.add(plot.plot_id)
            plots.append(plot)
    return plots


def _boutique_water_pool():
    frs = [g[0] for g in _boutique_garment_entries()] + [c[0] for c in _boutique_colour_entries()]
    return _plots_for_fr_texts(frs)


def _cafe_water_pool():
    plots = _plots_for_fr_texts([fr for fr, _en in _cafe_food_entries()])
    seen = {p.plot_id for p in plots}
    return plots + [p for p in _cafe_twist_candidate_plots() if p.plot_id not in seen]


def _open_blitz():
    global blitz_open
    blitz_open = True
    render()


def _open_racer():
    global racer_open
    racer_open = True
    render()


def _open_boutique():
    global boutique_open
    boutique_open = True
    render()


def _open_cafe():
    global cafe_open
    cafe_open = True
    render()


def _open_sprint():
    global sprint_open
    sprint_open = True
    render()


WATER_GAMES = [
    ("blitz", "Greetings & Basics Blitz", "vocabulary, phrases and examples from weeks 1-11",
     _blitz_candidate_plots, blitz_available, _open_blitz),
    ("racer", "Verb Racer", "grammar plots from weeks 12-15",
     _racer_candidate_plots, racer_available, _open_racer),
    ("boutique", "Boutique Dash", "clothing and colour plots from weeks 16-18",
     _boutique_water_pool, boutique_available, _open_boutique),
    ("cafe", "Café Rush", "food and drink plots, plus passé composé plots in the twist (weeks 19-23)",
     _cafe_water_pool, cafe_available, _open_cafe),
    ("sprint", "Passé Composé Sprint", "passé composé grammar plots from weeks 21-23",
     _sprint_candidate_plots, sprint_available, _open_sprint),
]
_WATER_NOTES = {
    "pairs": "vocabulary and phrase plots from weeks 12-23",
    "gaps": "grammar plots outside weeks 12-15 and the passé composé",
    "listenpick": "vocabulary, phrase and pronunciation plots from every week",
    "wordorder": "grammar plots that have a short example sentence, every week",
}
for _game in NEW_GAMES:
    if _game.key not in _WATER_NOTES:
        continue  # Faux Amis is about a live list, not the player's plots: it waters nothing
    _note = _WATER_NOTES[_game.key]
    WATER_GAMES.append((_game.key, _game.open_label.split(" ", 1)[1], _note, _game.pool, _game.available, _game.open_panel))


def game_pool(key):
    """Every plot a game can water (lazy; the same pools the games draw from)."""
    for entry in WATER_GAMES:
        if entry[0] == key:
            return list(entry[3]())
    return []


def water_game_rows():
    """One row per minigame for game.py's Water options panel: the title, what
    it waters, how many of those plots can still be watered today, whether it
    is open to play."""
    rows = []
    for key, title, note, pool_fn, available_fn, _open_fn in WATER_GAMES:
        available = bool(available_fn())
        count = sum(1 for p in pool_fn() if _can_water(p)) if available else 0
        rows.append({"key": key, "title": title, "note": note, "count": count, "available": available})
    return rows


def open_game(key):
    for entry in WATER_GAMES:
        if entry[0] == key:
            entry[5]()
            return True
    return False
