"""Café Rush (weeks 19-23): serve food orders, with a passé composé twist every few customers.
Part of the split of the old single-file minigames.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from js import document
from pyodide.ffi import create_proxy

import champ_minigames_runstate as runstate
from champ_minigames_rules import (
    CAFE_BASE_POINTS, CAFE_MIN_PATIENCE, CAFE_OPTION_COUNT, CAFE_PATIENCE_STEP, CAFE_STAGE_PICK,
    CAFE_STAGE_TWIST, CAFE_STARTING_PATIENCE, CAFE_TOTAL_CUSTOMERS, CAFE_TWIST_BONUS_POINTS,
    CAFE_TWIST_INTERVAL,
)
from champ_minigames_core import (
    DIFFICULTY_LABELS, _build_answer_area, _check, _credit, _credit_fr, _element, _expand_slash_variants,
    _lock_reason, _range_fully_unlocked, _record, _render_difficulty, _reset_credit, _setup_difficulty,
    _topic_items_by_id, _with_growth, answer_note, context_line, difficulty_points, get_difficulty,
    labels_for_fr, plot_label, waters_text,
)
from champ_minigames_blitz import VARIANT_BLANK_WORD, VARIANT_CONJUGATION_SWAP


# render() is defined in champ_minigames_registry, which comes later in the module list; that module puts it here when
# it loads (see the end of champ_minigames_registry.py). Calls below find it at run time.
render = None


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


cafe_choice_proxies = []
cafe_twist_choice_proxies = []


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


def _cafe_food_entries():
    """Lazy and memoized -- see blitz_available()'s build note on why this
    must never run eagerly on a passive render(). Each entry is (fr, en),
    already expanded through _expand_slash_variants() so a multi-fact
    record contributes each of its real facts separately."""
    if runstate._cafe_food_cache is None:
        entries = []
        for topic_id in CAFE_FOOD_TOPIC_IDS:
            sequence, items = _topic_items_by_id(topic_id)
            if sequence is None or not runstate._farm.is_row_unlocked(sequence):
                continue
            for item in items:
                entries.extend(_expand_slash_variants(item))
        runstate._cafe_food_cache = entries
    return runstate._cafe_food_cache


def _cafe_twist_variant(plot):
    """None if this plot can't offer a blank/conjugation question at all --
    the same "not every candidate id actually qualifies" posture Racer's own
    _racer_variant_for() takes, just narrower (blank/conjugation only, no
    translate-choice fallback, since the whole point of the twist is a
    fill-in-the-blank passé composé prompt, not any old question about the
    same plot)."""
    eligible = [v for v in runstate._variants_for(plot) if v in CAFE_TWIST_VARIANTS]
    return CAFE_RNG.choice(eligible) if eligible else None


def _cafe_twist_candidate_plots():
    """Lazy and memoized. Walks the passé-composé topic ids directly rather
    than every plot in range -- Café Rush's twist is deliberately scoped to
    this range's passé-composé content specifically, not its full grammar
    docket (partitive, y/en, futur proche stay out, per the module note
    above)."""
    if runstate._cafe_twist_candidates_cache is None:
        candidates = []
        for sequence in range(CAFE_LO, CAFE_HI + 1):
            if not runstate._farm.is_row_unlocked(sequence):
                continue
            for plot in runstate._farm.row_plots(sequence):
                if plot.topic_id in CAFE_PASSE_COMPOSE_TOPIC_IDS and _cafe_twist_variant(plot) is not None:
                    candidates.append(plot)
        runstate._cafe_twist_candidates_cache = candidates
    return runstate._cafe_twist_candidates_cache


def _roll_cafe_order():
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
    runstate.cafe_order = {"order_en": answer_en, "answer": answer_fr, "choices": choices, "credit_fr": [answer_fr]}


def _roll_cafe_customer():
    runstate.cafe_customer_index += 1
    twist_pool = _cafe_twist_candidate_plots()
    runstate.cafe_is_twist_round = bool(twist_pool) and runstate.cafe_customer_index % CAFE_TWIST_INTERVAL == 0
    runstate.cafe_stage = CAFE_STAGE_PICK
    runstate.cafe_twist_question = None
    runstate.cafe_patience_remaining = runstate.cafe_patience_max
    _roll_cafe_order()


def start_cafe(event=None):
    if not cafe_available() or not _cafe_food_entries():
        return None
    runstate.cafe_open = True
    runstate.cafe_active = True
    runstate.cafe_served = 0
    runstate.cafe_missed = 0
    runstate.cafe_score = 0
    runstate.cafe_patience_max = _cafe_params()["start"]
    runstate.cafe_customer_index = 0
    runstate.cafe_last_result = None
    runstate.cafe_note = ""
    _reset_credit("cafe")
    _roll_cafe_customer()
    render()
    return runstate.cafe_order


def _resolve_cafe_customer(served, speed_up):
    """Shared by every way a customer's round can end -- a correct/wrong
    item pick with no twist, a correct/wrong twist confirmation, or a
    timeout at either stage. `speed_up` is deliberately a separate flag from
    `served`: it's False for a miss (per the brief, only a *correct sale*
    speeds the pace up), matching Boutique Dash's own rule."""

    runstate.cafe_last_result = served
    _record("cafe", served)
    if served:
        runstate.cafe_served += 1
        runstate.cafe_score += difficulty_points(
            "cafe", CAFE_BASE_POINTS + (CAFE_TWIST_BONUS_POINTS if runstate.cafe_stage == CAFE_STAGE_TWIST else 0)
        )
    else:
        runstate.cafe_missed += 1
    if speed_up:
        runstate.cafe_patience_max = max(_cafe_params()["min"], runstate.cafe_patience_max - CAFE_PATIENCE_STEP)

    if runstate.cafe_served + runstate.cafe_missed >= CAFE_TOTAL_CUSTOMERS:
        runstate.cafe_active = False
        runstate.cafe_order = None
        runstate.cafe_stage = CAFE_STAGE_PICK
        runstate.cafe_twist_question = None
    else:
        _roll_cafe_customer()


def submit_cafe_item_choice(given):
    if not runstate.cafe_active or runstate.cafe_order is None or runstate.cafe_stage != CAFE_STAGE_PICK:
        return None
    correct = given == runstate.cafe_order["answer"]
    labels = labels_for_fr(runstate.cafe_order.get("credit_fr", ()))
    if not correct:
        runstate.cafe_note = answer_note(" + ".join(labels), False, [])
        _resolve_cafe_customer(served=False, speed_up=False)
        render()
        return False
    kinds = _credit_fr(runstate.cafe_order.get("credit_fr", ()), "cafe")
    runstate.cafe_note = answer_note(" + ".join(labels), True, kinds)

    twist_pool = _cafe_twist_candidate_plots()
    if runstate.cafe_is_twist_round and twist_pool:
        runstate.cafe_stage = CAFE_STAGE_TWIST
        plot = CAFE_RNG.choice(twist_pool)
        runstate.cafe_twist_question = runstate._generate_question(plot, CAFE_RNG, variant=_cafe_twist_variant(plot))
        render()
        return True

    _resolve_cafe_customer(served=True, speed_up=True)
    render()
    return True


def submit_cafe_twist_choice(given):
    if not runstate.cafe_active or runstate.cafe_stage != CAFE_STAGE_TWIST or runstate.cafe_twist_question is None:
        return None
    correct = _check(runstate.cafe_twist_question, given)
    twist_label = plot_label(runstate.cafe_twist_question["plot_id"])
    if correct:
        kind = _credit(runstate.cafe_twist_question, "cafe")
        runstate.cafe_note = (runstate.cafe_note + " " + answer_note(twist_label, True, [kind])).strip()
    else:
        runstate.cafe_note = (runstate.cafe_note + " " + answer_note(twist_label, False, [])).strip()
    _resolve_cafe_customer(served=correct, speed_up=correct)
    render()
    return correct


def cafe_tick(event=None):
    """JS-driven countdown tick -- see the module docstring's "the timer is
    JS-driven, not a Python clock" note. A no-op whenever no shift is
    active. One shared clock covers both stages of a twist round, exactly
    the module note above describes."""
    if not runstate.cafe_active:
        return None
    runstate.cafe_patience_remaining -= 1
    if runstate.cafe_patience_remaining <= 0:
        runstate.cafe_patience_remaining = 0
        _resolve_cafe_customer(served=False, speed_up=False)
    render()
    return runstate.cafe_patience_remaining


def close_cafe(event=None):
    runstate.cafe_note = ""
    runstate.cafe_open = False
    runstate.cafe_active = False
    runstate.cafe_order = None
    runstate.cafe_stage = CAFE_STAGE_PICK
    runstate.cafe_twist_question = None
    runstate.cafe_last_result = None
    render()


def on_toggle_cafe(event=None):
    if runstate.cafe_open:
        close_cafe()
    else:
        runstate.cafe_open = True
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


def render_cafe():
    toggle = _element("cafe-toggle-button")
    panel = _element("cafe-panel")
    options_box = _element("cafe-options")
    twist_panel = _element("cafe-twist-panel")
    twist_choices_box = _element("cafe-twist-choices")

    available = cafe_available()
    toggle.disabled = not runstate.cafe_open and not available
    toggle.innerText = "Close Café Rush" if runstate.cafe_open else "☕ Café Rush"

    if not runstate.cafe_open:
        panel.hidden = True
        _destroy_cafe_choice_proxies()
        _destroy_cafe_twist_proxies()
        options_box.innerHTML = ""
        twist_choices_box.innerHTML = ""
        runstate._cafe_rendered_order = None
        runstate._cafe_rendered_twist = None
        return

    panel.hidden = False
    lock_message = _element("cafe-lock-message")
    reason = cafe_lock_reason()
    lock_message.hidden = reason is None
    lock_message.innerText = reason or ""

    start_button = _element("cafe-start-button")
    summary = _element("cafe-summary")

    _render_difficulty("cafe", runstate.cafe_active, _cafe_describe)
    _element("cafe-served-display").innerText = f"Served: {runstate.cafe_served}"
    _element("cafe-missed-display").innerText = f"Missed: {runstate.cafe_missed}"
    _element("cafe-score-display").innerText = f"Score: {runstate.cafe_score}"

    completed = runstate.cafe_served + runstate.cafe_missed

    if not runstate.cafe_active:
        _destroy_cafe_choice_proxies()
        _destroy_cafe_twist_proxies()
        options_box.innerHTML = ""
        twist_choices_box.innerHTML = ""
        runstate._cafe_rendered_order = None
        runstate._cafe_rendered_twist = None
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
                served=runstate.cafe_served, total=CAFE_TOTAL_CUSTOMERS,
                missed=runstate.cafe_missed, score=runstate.cafe_score,
            ), "cafe")
        return

    start_button.hidden = True
    summary.hidden = True

    pct = round((runstate.cafe_patience_remaining / runstate.cafe_patience_max) * 100) if runstate.cafe_patience_max else 0
    fill = _element("cafe-patience-fill")
    fill.style.width = f"{pct}%"
    low = runstate.cafe_patience_remaining <= max(2, round(runstate.cafe_patience_max * 0.3))
    fill.className = "shop-rush-patience-fill shop-rush-patience-fill--low" if low else "shop-rush-patience-fill"

    if runstate.cafe_last_result is False:
        _element("cafe-feedback").innerText = "Not this time — next customer, please. " + runstate.cafe_note
    elif runstate.cafe_last_result is True:
        _element("cafe-feedback").innerText = "Sold! " + runstate.cafe_note
    else:
        _element("cafe-feedback").innerText = ""

    if runstate.cafe_order is not runstate._cafe_rendered_order:
        _destroy_cafe_choice_proxies()
        _element("cafe-order").innerText = f"A customer wants: {runstate.cafe_order['order_en']}."
        _element("cafe-waters").innerText = waters_text(labels_for_fr(runstate.cafe_order.get("credit_fr", ())))
        options_box.innerHTML = ""
        for index, choice in enumerate(runstate.cafe_order["choices"]):
            button = document.createElement("button")
            button.id = f"cafe-choice-{index}"
            button.innerText = choice
            button.className = "choice"
            proxy = create_proxy(_make_cafe_item_choice_handler(choice))
            button.addEventListener("click", proxy)
            cafe_choice_proxies.append(proxy)
            options_box.appendChild(button)
        runstate._cafe_rendered_order = runstate.cafe_order

    if runstate.cafe_stage == CAFE_STAGE_TWIST and runstate.cafe_twist_question is not None:
        twist_panel.hidden = False
        options_box.innerHTML = ""  # the item choice is already made -- only the twist remains
        if runstate.cafe_twist_question is not runstate._cafe_rendered_twist:
            _destroy_cafe_twist_proxies()
            _element("cafe-twist-context").innerText = context_line(runstate.cafe_twist_question)
            _element("cafe-twist-prompt").innerText = runstate.cafe_twist_question["prompt"]
            _element("cafe-twist-waters").innerText = waters_text([plot_label(runstate.cafe_twist_question["plot_id"])])
            _build_answer_area(
                "cafe-twist", runstate.cafe_twist_question, twist_choices_box, cafe_twist_choice_proxies, submit_cafe_twist_choice
            )
            runstate._cafe_rendered_twist = runstate.cafe_twist_question
    else:
        twist_panel.hidden = True
        _destroy_cafe_twist_proxies()
        twist_choices_box.innerHTML = ""
        runstate._cafe_rendered_twist = None


def _setup_cafe():
    _setup_difficulty("cafe")
    _element("cafe-toggle-button").addEventListener("click", create_proxy(on_toggle_cafe))
    _element("cafe-start-button").addEventListener("click", create_proxy(start_cafe))
    _element("cafe-close-button").addEventListener("click", create_proxy(close_cafe))
