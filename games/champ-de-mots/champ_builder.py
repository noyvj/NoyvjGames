"""The freeform sentence builder: put the tiles of any unlocked week's bonus sentence in order.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_catalog import CATALOG
from champ_model import state
from champ_util import _element
from champ_points import record_practice


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


# ===========================================================================
# L11 -- the freeform sentence builder. Unlike a week's Bonus section (one
# sentence, three tasks, opened from that row), this can be opened at any time
# and mixes the bonus sentences of EVERY unlocked week: the English meaning is
# shown and you tap the French word tiles into order. It only ever draws on
# weeks the pacing gate has already unlocked, never touches a plot's SRS state,
# and every finished sentence lands in the practice ledger as "builder", so it
# visibly counts toward the headline practice score and the study streak.
# ===========================================================================
BUILDER_SESSION_LENGTH = 10
BUILDER_RNG = random.Random()
BUILDER_EMPTY_MESSAGE = (
    "No sentences are unlocked yet. Each unlocked week brings its own sentence into the builder."
)
BUILDER_CORRECT = "That's the right order."
BUILDER_INCORRECT = "Not quite. The sentence is: {sentence}"
BUILDER_SUMMARY = "Sentence builder complete: {correct}/{total} in the right order."


builder_proxies = []


def _destroy_builder_proxies():
    for proxy in builder_proxies:
        proxy.destroy()
    builder_proxies.clear()


def builder_sentences():
    """Every bonus sentence from every unlocked week."""
    return [
        sentence
        for week in CATALOG["weeks"]
        if state.is_row_unlocked(week["sequence"])
        for sentence in week.get("bonus_sentences", [])
    ]


def _begin_builder_sentence():
    runstate.builder_placed = []
    runstate.builder_result = None
    if runstate.builder_index >= len(runstate.builder_queue):
        runstate.builder_pool = []
        return
    sentence = runstate.builder_queue[runstate.builder_index]
    pool = list(sentence["tiles"])
    BUILDER_RNG.shuffle(pool)
    # A shuffle that lands on the answer would make the task trivial.
    if len(pool) > 1 and [t["fr"] for t in pool] == [t["fr"] for t in sentence["tiles"]]:
        pool.reverse()
    runstate.builder_pool = pool


def start_sentence_builder(event=None):
    sentences = builder_sentences()
    BUILDER_RNG.shuffle(sentences)
    runstate.builder_queue = sentences[:BUILDER_SESSION_LENGTH]
    runstate.builder_index = 0
    runstate.builder_score = {"correct": 0, "total": 0}
    runstate.builder_active = True
    _begin_builder_sentence()
    render()
    return runstate.builder_queue


def place_builder_tile(pool_index):
    """Moves one tile from the pool to the end of the sentence. When the pool
    empties the order is checked (a whole-sentence pass or fail)."""
    if not runstate.builder_active or runstate.builder_result is not None or not (0 <= pool_index < len(runstate.builder_pool)):
        return None
    runstate.builder_placed.append(runstate.builder_pool.pop(pool_index))
    if not runstate.builder_pool:
        sentence = runstate.builder_queue[runstate.builder_index]
        runstate.builder_result = [t["fr"] for t in runstate.builder_placed] == [t["fr"] for t in sentence["tiles"]]
        runstate.builder_score["total"] += 1
        if runstate.builder_result:
            runstate.builder_score["correct"] += 1
        record_practice("builder", runstate.builder_result)
    render()
    return runstate.builder_result


def undo_builder_tile(event=None):
    """Takes the last placed tile back (only before the sentence is checked)."""
    if not runstate.builder_active or runstate.builder_result is not None or not runstate.builder_placed:
        return False
    runstate.builder_pool.append(runstate.builder_placed.pop())
    render()
    return True


def next_builder_sentence(event=None):
    if not runstate.builder_active or runstate.builder_result is None:
        return None
    runstate.builder_index += 1
    _begin_builder_sentence()
    render()
    return runstate.builder_index < len(runstate.builder_queue)


def close_sentence_builder(event=None):
    runstate.builder_active = False
    runstate.builder_queue = []
    runstate.builder_index = 0
    runstate.builder_pool = []
    runstate.builder_placed = []
    runstate.builder_result = None
    render()


def _make_builder_pool_handler(index):
    def handler(event=None):
        place_builder_tile(index)
    return handler


def render_builder():
    panel = _element("builder-panel")
    pool_box = _element("builder-pool")
    placed_box = _element("builder-placed")
    _destroy_builder_proxies()
    pool_box.innerHTML = ""
    placed_box.innerHTML = ""
    if not runstate.builder_active:
        panel.hidden = True
        return
    panel.hidden = False
    empty = _element("builder-empty-message")
    summary = _element("builder-summary")
    card = _element("builder-card")
    if not runstate.builder_queue:
        empty.hidden = False
        empty.innerText = BUILDER_EMPTY_MESSAGE
        summary.hidden = True
        card.hidden = True
        return
    empty.hidden = True
    if runstate.builder_index >= len(runstate.builder_queue):
        card.hidden = True
        summary.hidden = False
        summary.innerText = BUILDER_SUMMARY.format(**runstate.builder_score)
        _element("builder-progress").innerText = ""
        return
    card.hidden = False
    summary.hidden = True
    sentence = runstate.builder_queue[runstate.builder_index]
    _element("builder-progress").innerText = f"Sentence {runstate.builder_index + 1} of {len(runstate.builder_queue)}"
    _element("builder-prompt").innerText = sentence["en"]
    for index, tile in enumerate(runstate.builder_pool):
        button = document.createElement("button")
        button.id = f"builder-pool-tile-{index}"
        button.innerText = tile["fr"]
        button.className = "bonus-tile"
        proxy = create_proxy(_make_builder_pool_handler(index))
        button.addEventListener("click", proxy)
        builder_proxies.append(proxy)
        pool_box.appendChild(button)
    for tile in runstate.builder_placed:
        span = document.createElement("span")
        span.className = "bonus-tile bonus-tile--placed"
        span.innerText = tile["fr"]
        placed_box.appendChild(span)
    _element("builder-undo-button").hidden = runstate.builder_result is not None or not runstate.builder_placed
    _element("builder-next-button").hidden = runstate.builder_result is None
    feedback = _element("builder-feedback")
    if runstate.builder_result is None:
        feedback.innerText = ""
    else:
        feedback.innerText = BUILDER_CORRECT if runstate.builder_result else BUILDER_INCORRECT.format(sentence=sentence["fr"])
