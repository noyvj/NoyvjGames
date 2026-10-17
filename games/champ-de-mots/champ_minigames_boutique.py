"""Boutique Dash (weeks 16-18): serve clothing orders before the customer's patience runs out.
Part of the split of the old single-file minigames.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from js import document
from pyodide.ffi import create_proxy

import champ_minigames_runstate as runstate
from champ_minigames_rules import (
    BOUTIQUE_BASE_POINTS, BOUTIQUE_MIN_PATIENCE, BOUTIQUE_OPTION_COUNT, BOUTIQUE_PATIENCE_STEP,
    BOUTIQUE_STARTING_PATIENCE, BOUTIQUE_TOTAL_CUSTOMERS,
)
from champ_minigames_core import (
    DIFFICULTY_LABELS, _credit_fr, _element, _lock_reason, _range_fully_unlocked, _record, _render_difficulty,
    _reset_credit, _setup_difficulty, _strip_leading_article, _strip_parens, _topic_items_by_id, _with_growth,
    answer_note, difficulty_points, get_difficulty, labels_for_fr, waters_text,
)


# render() is defined in champ_minigames_registry, which comes later in the module list; that module puts it here when
# it loads (see the end of champ_minigames_registry.py). Calls below find it at run time.
render = None


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


BOUTIQUE_GARMENT_TOPIC_IDS = (
    "fren152-w6-vocab001",  # Clothing
    "fren152-w7-vocab001",  # Materials and accessories ("un sac", "un chapeau")
    "fren152-w8-vocab001",  # Accessories & toiletries
)
BOUTIQUE_COLOUR_TOPIC_IDS = (
    "fren152-w6-vocab002",        # Colours -- masc/fem pairs
    "fren152-w7-vocab-slide001",  # Extra materials & sizes -- 2 invariable colours live here too
)


boutique_choice_proxies = []


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


def _boutique_garment_entries():
    """Lazy and memoized -- see blitz_available()'s build note on why this
    must never run eagerly on a passive render(). Each entry is
    (garment_fr, garment_en, gender), gender being "m"/"f" read straight off
    the item's own article."""
    if runstate._boutique_garments_cache is None:
        entries = []
        for topic_id in BOUTIQUE_GARMENT_TOPIC_IDS:
            sequence, items = _topic_items_by_id(topic_id)
            if sequence is None or not runstate._farm.is_row_unlocked(sequence):
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
        runstate._boutique_garments_cache = entries
    return runstate._boutique_garments_cache


def _boutique_colour_entries():
    """Lazy and memoized. Each entry is (masc_fr, fem_fr, colour_en) -- an
    invariable colour (rose, orange, bordeaux, ...) simply repeats the same
    form for both, so the caller never has to special-case it."""
    if runstate._boutique_colours_cache is None:
        entries = []
        for topic_id in BOUTIQUE_COLOUR_TOPIC_IDS:
            sequence, items = _topic_items_by_id(topic_id)
            if sequence is None or not runstate._farm.is_row_unlocked(sequence):
                continue
            for item in items:
                fr = item["fr"]
                en = _strip_parens(item["en"])
                if " / " in fr:
                    masc, fem = (part.strip() for part in fr.split(" / ", 1))
                    entries.append((masc, fem, en))
                elif "invariable colour" in item["en"].lower():
                    entries.append((fr, fr, en))
        runstate._boutique_colours_cache = entries
    return runstate._boutique_colours_cache


def _roll_boutique_order():
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
    runstate.boutique_order = {
        "order_en": order_en,
        "answer": answer,
        "choices": choices,
        "credit_fr": [garment_fr, colour_masc],
    }


def start_boutique(event=None):
    if not boutique_available() or not _boutique_garment_entries() or not _boutique_colour_entries():
        return None
    runstate.boutique_open = True
    runstate.boutique_active = True
    runstate.boutique_served = 0
    runstate.boutique_missed = 0
    runstate.boutique_score = 0
    runstate.boutique_patience_max = _boutique_params()["start"]
    runstate.boutique_patience_remaining = runstate.boutique_patience_max
    runstate.boutique_last_result = None
    runstate.boutique_note = ""
    _reset_credit("boutique")
    _roll_boutique_order()
    render()
    return runstate.boutique_order


def _resolve_boutique_customer(served):
    """Shared by a submitted choice and a timeout (boutique_tick()) -- either
    way, this customer's outcome is exactly the same shape: served or not,
    tally it, maybe speed up, then either end the shift or bring in the
    next customer."""

    runstate.boutique_last_result = served
    _record("boutique", served)
    labels = labels_for_fr(runstate.boutique_order.get("credit_fr", ())) if runstate.boutique_order is not None else []
    if served:
        kinds = []
        if runstate.boutique_order is not None:
            kinds = _credit_fr(runstate.boutique_order.get("credit_fr", ()), "boutique")
        runstate.boutique_note = answer_note(" + ".join(labels), True, kinds)
        runstate.boutique_served += 1
        runstate.boutique_score += difficulty_points("boutique", BOUTIQUE_BASE_POINTS)
        runstate.boutique_patience_max = max(_boutique_params()["min"], runstate.boutique_patience_max - BOUTIQUE_PATIENCE_STEP)
    else:
        runstate.boutique_note = answer_note(" + ".join(labels), False, [])
        runstate.boutique_missed += 1

    if runstate.boutique_served + runstate.boutique_missed >= BOUTIQUE_TOTAL_CUSTOMERS:
        runstate.boutique_active = False
        runstate.boutique_order = None
    else:
        runstate.boutique_patience_remaining = runstate.boutique_patience_max
        _roll_boutique_order()


def submit_boutique_choice(given):
    if not runstate.boutique_active or runstate.boutique_order is None:
        return None
    correct = given == runstate.boutique_order["answer"]
    _resolve_boutique_customer(correct)
    render()
    return correct


def boutique_tick(event=None):
    """JS-driven countdown tick -- see the module docstring's "the timer is
    JS-driven, not a Python clock" note. A no-op whenever no shift is
    active."""
    if not runstate.boutique_active:
        return None
    runstate.boutique_patience_remaining -= 1
    if runstate.boutique_patience_remaining <= 0:
        runstate.boutique_patience_remaining = 0
        _resolve_boutique_customer(False)
    render()
    return runstate.boutique_patience_remaining


def close_boutique(event=None):
    runstate.boutique_note = ""
    runstate.boutique_open = False
    runstate.boutique_active = False
    runstate.boutique_order = None
    runstate.boutique_last_result = None
    render()


def on_toggle_boutique(event=None):
    if runstate.boutique_open:
        close_boutique()
    else:
        runstate.boutique_open = True
        render()


def _make_boutique_choice_handler(choice):
    def handler(event=None):
        submit_boutique_choice(choice)
    return handler


BOUTIQUE_SUMMARY_MESSAGE = (
    "Shift complete! Served {served} of {total} customers (missed {missed}) · Score: {score}."
)


def render_boutique():
    toggle = _element("boutique-toggle-button")
    panel = _element("boutique-panel")
    options_box = _element("boutique-options")

    available = boutique_available()
    toggle.disabled = not runstate.boutique_open and not available
    toggle.innerText = "Close Boutique Dash" if runstate.boutique_open else "👗 Boutique Dash"

    if not runstate.boutique_open:
        panel.hidden = True
        _destroy_boutique_choice_proxies()
        options_box.innerHTML = ""
        runstate._boutique_rendered_order = None
        return

    panel.hidden = False
    lock_message = _element("boutique-lock-message")
    reason = boutique_lock_reason()
    lock_message.hidden = reason is None
    lock_message.innerText = reason or ""

    start_button = _element("boutique-start-button")
    summary = _element("boutique-summary")

    _render_difficulty("boutique", runstate.boutique_active, _boutique_describe)
    _element("boutique-served-display").innerText = f"Served: {runstate.boutique_served}"
    _element("boutique-missed-display").innerText = f"Missed: {runstate.boutique_missed}"
    _element("boutique-score-display").innerText = f"Score: {runstate.boutique_score}"

    completed = runstate.boutique_served + runstate.boutique_missed

    if not runstate.boutique_active:
        _destroy_boutique_choice_proxies()
        options_box.innerHTML = ""
        runstate._boutique_rendered_order = None
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
                served=runstate.boutique_served, total=BOUTIQUE_TOTAL_CUSTOMERS,
                missed=runstate.boutique_missed, score=runstate.boutique_score,
            ), "boutique")
        return

    start_button.hidden = True
    summary.hidden = True

    pct = round((runstate.boutique_patience_remaining / runstate.boutique_patience_max) * 100) if runstate.boutique_patience_max else 0
    fill = _element("boutique-patience-fill")
    fill.style.width = f"{pct}%"
    low = runstate.boutique_patience_remaining <= max(2, round(runstate.boutique_patience_max * 0.3))
    fill.className = "shop-rush-patience-fill shop-rush-patience-fill--low" if low else "shop-rush-patience-fill"

    if runstate.boutique_last_result is False:
        _element("boutique-feedback").innerText = "Not this time — next customer, please. " + runstate.boutique_note
    elif runstate.boutique_last_result is True:
        _element("boutique-feedback").innerText = "Sold! " + runstate.boutique_note
    else:
        _element("boutique-feedback").innerText = ""

    if runstate.boutique_order is not runstate._boutique_rendered_order:
        _destroy_boutique_choice_proxies()
        _element("boutique-order").innerText = f"A customer wants: {runstate.boutique_order['order_en']}."
        _element("boutique-waters").innerText = waters_text(labels_for_fr(runstate.boutique_order.get("credit_fr", ())))
        options_box.innerHTML = ""
        for index, choice in enumerate(runstate.boutique_order["choices"]):
            button = document.createElement("button")
            button.id = f"boutique-choice-{index}"
            button.innerText = choice
            button.className = "choice"
            proxy = create_proxy(_make_boutique_choice_handler(choice))
            button.addEventListener("click", proxy)
            boutique_choice_proxies.append(proxy)
            options_box.appendChild(button)
        runstate._boutique_rendered_order = runstate.boutique_order


def _setup_boutique():
    _setup_difficulty("boutique")
    _element("boutique-toggle-button").addEventListener("click", create_proxy(on_toggle_boutique))
    _element("boutique-start-button").addEventListener("click", create_proxy(start_boutique))
    _element("boutique-close-button").addEventListener("click", create_proxy(close_boutique))
