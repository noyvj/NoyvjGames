"""Shared pieces of every minigame: the wiring game.py hands in (configure), growth credit and ledger helpers, the row-unlock
checks, the difficulty setting, labels and the answer-area builder.
Part of the split of the old single-file minigames.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random
import re

from js import document
from pyodide.ffi import create_proxy

import champ_minigames_runstate as runstate


# render() is defined in champ_minigames_registry, which comes later in the module list; that module puts it here when
# it loads (see the end of champ_minigames_registry.py). Calls below find it at run time.
render = None


def _credit(question, mode):
    """A correct answer on a real plot: hand it to game.py's plot-growth
    credit (water_plot: the first correct answer for a plot each in-game day
    waters it, a later one nudges it; see game.py's "Watering versus
    nudging"). Returns "full", "nudge" or None. A no-op standalone."""
    if runstate._credit_plot_id is not None and question is not None:
        return runstate._credit_plot_id(question.get("plot_id"), mode)
    return None


def _credit_fr(fr_texts, mode):
    """Credit every plot behind a list of French texts; returns the list of
    results ("full" / "nudge" / None, one per text)."""
    results = []
    if runstate._credit_item is not None:
        for fr in fr_texts:
            results.append(runstate._credit_item(fr, mode))
    return results


def _reset_credit(mode):
    if runstate._credit_reset is not None:
        runstate._credit_reset(mode)


def _with_growth(message, mode):
    if runstate._credit_text is None:
        return message
    return f"{message} {runstate._credit_text(mode)}"


def _record(mode, correct):
    """Feed one answered question into game.py's practice-progress ledger
    (see game.py's "practice progress" build note). A no-op when nothing was
    wired in, so the module stays usable standalone."""
    if runstate._record_practice is not None:
        runstate._record_practice(mode, bool(correct))


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
    runstate._record_practice = record_practice_fn
    runstate._credit_plot_id = credit_plot_fn
    runstate._credit_item = credit_item_fn
    runstate._credit_reset = credit_reset_fn
    runstate._credit_text = credit_text_fn
    runstate._plot_for_fr = plot_for_fr_fn
    runstate._pref_get = pref_get_fn
    runstate._pref_set = pref_set_fn
    runstate._check_answer = check_answer_fn
    runstate._farm = farm
    runstate._generate_question = generate_question_fn
    runstate._variants_for = variants_for_fn


def _element(element_id):
    return document.getElementById(element_id)


# --- shared helpers ----------------------------------------------------


def _unlocked_range_plots(lo, hi):
    """Every plot in [lo, hi] whose row is currently unlocked -- locked rows
    contribute nothing, so a minigame can never preview content ahead of
    §7's pacing gate."""
    plots = []
    for sequence in range(lo, hi + 1):
        if runstate._farm.is_row_unlocked(sequence):
            plots.extend(runstate._farm.row_plots(sequence))
    return plots


def _range_fully_unlocked(lo, hi):
    """A minigame's target range counts as playable only once *every* row in
    it is unlocked -- unlike Liaison's "any eligible row" posture, a partial
    range here would mean an arcade session with suspiciously thin content,
    and the brief explicitly asks for "visibly present but disabled" over
    that half-open state."""
    return all(runstate._farm.is_row_unlocked(sequence) for sequence in range(lo, hi + 1))


def _lock_reason(hi):
    """Same wording style as a locked farm row's own tooltip (Milestone 6)."""
    return f"Unlocks once every plot through row {hi} has sprouted."


def _topic_items_by_id(topic_id):
    """Read a topic's raw catalog items directly (not through the Plot
    model) -- Boutique Dash and Café Rush build bespoke shop-order content
    from specific vocab topics rather than from generate_question(), so they
    need the catalog's own items list, not a farm plot."""
    for week in runstate._farm.catalog["weeks"]:
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
        stored = runstate._pref_get(PREF_DIFFICULTY_PREFIX + key) if runstate._pref_get is not None else None
        value = stored if stored in DIFFICULTY_LEVELS else "normal"
        _difficulty[key] = value
    return value


def set_difficulty(key, value):
    if value not in DIFFICULTY_LEVELS:
        return get_difficulty(key)
    _difficulty[key] = value
    if runstate._pref_set is not None:
        runstate._pref_set(PREF_DIFFICULTY_PREFIX + key, value)
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
    plot = runstate._farm.plots_by_id.get(plot_id) if runstate._farm is not None else None
    return plot.label if plot is not None else ""


def context_line(question):
    """The small line above a prompt: where the plot is from and what to do."""
    instruction = question.get("instruction")
    return f"{question['context']} · {instruction}" if instruction else question["context"]


def labels_for_fr(fr_texts):
    """Plot labels behind a list of French texts (the shop games' orders)."""
    labels = []
    if runstate._plot_for_fr is not None:
        for fr in fr_texts:
            plot = runstate._plot_for_fr(fr)
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
    if runstate._check_answer is not None:
        return bool(runstate._check_answer(question, given))
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
