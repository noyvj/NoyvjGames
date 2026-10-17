"""The personal phrasebook: bookmark plots, practise just that list.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_model import state
from champ_util import _element
from champ_review_base import PHRASEBOOK_EMPTY_MESSAGE, PHRASEBOOK_LIMIT, PHRASEBOOK_MODE
from champ_review import start_review


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


phrasebook_proxies = []


def in_phrasebook(plot_id):
    return plot_id in runstate.phrasebook


def toggle_phrasebook(plot_id):
    """Add or remove `plot_id`; returns True if it is now in the phrasebook."""
    if plot_id not in state.plots_by_id:
        return False
    if plot_id in runstate.phrasebook:
        runstate.phrasebook.remove(plot_id)
        return False
    if len(runstate.phrasebook) >= PHRASEBOOK_LIMIT:
        return False
    runstate.phrasebook.append(plot_id)
    return True


def _validated_phrasebook(raw):
    if not isinstance(raw, list):
        return []
    clean = []
    for plot_id in raw:
        if isinstance(plot_id, str) and plot_id in state.plots_by_id and plot_id not in clean:
            clean.append(plot_id)
    return clean[:PHRASEBOOK_LIMIT]


def phrasebook_entry_text(plot):
    """One readable line for a saved plot: the French and its meaning."""
    if plot.topic_type == "grammar":
        return f"{plot.label}: {plot.rule}" if plot.rule else str(plot.label)
    return f"{plot.label} \u2014 {plot.items[0]['en']}"


def _destroy_phrasebook_proxies():
    for proxy in phrasebook_proxies:
        proxy.destroy()
    phrasebook_proxies.clear()


def _make_phrasebook_remove_handler(plot_id):
    def handler(event=None):
        if plot_id in runstate.phrasebook:
            runstate.phrasebook.remove(plot_id)
        render()
    return handler


def on_toggle_phrasebook_panel(event=None):
    runstate.phrasebook_open = not runstate.phrasebook_open
    render()


def on_bookmark_practice(event=None):
    if runstate.current_question is not None:
        toggle_phrasebook(runstate.current_question["plot_id"])
        render()


def on_bookmark_review(event=None):
    if runstate.review_question is not None:
        toggle_phrasebook(runstate.review_question["plot_id"])
        render()


def on_start_phrasebook_review(event=None):
    start_review(PHRASEBOOK_MODE)


def _render_bookmark_button(button_id, question):
    button = _element(button_id)
    if question is None:
        button.hidden = True
        return
    button.hidden = False
    saved = in_phrasebook(question["plot_id"])
    button.innerText = "\u2605 In your phrasebook (remove)" if saved else "\u2606 Save to phrasebook"
    button.setAttribute("aria-pressed", "true" if saved else "false")


def render_phrasebook():
    _render_bookmark_button("practice-bookmark-button", runstate.current_question if runstate.practice_open else None)
    _render_bookmark_button("review-bookmark-button", runstate.review_question if runstate.review_mode is not None else None)
    _destroy_phrasebook_proxies()
    toggle = _element("phrasebook-toggle-button")
    toggle.innerText = (
        "Hide phrasebook" if runstate.phrasebook_open else f"\U0001F4D2 My phrasebook ({len(runstate.phrasebook)})"
    )
    panel = _element("phrasebook-panel")
    panel.hidden = not runstate.phrasebook_open
    if not runstate.phrasebook_open:
        return
    listing = _element("phrasebook-list")
    listing.innerHTML = ""
    _element("phrasebook-practice-button").disabled = not runstate.phrasebook
    if not runstate.phrasebook:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = PHRASEBOOK_EMPTY_MESSAGE
        listing.appendChild(empty)
        return
    for plot_id in runstate.phrasebook:
        plot = state.plots_by_id[plot_id]
        row = document.createElement("div")
        row.className = "phrasebook-row"
        text = document.createElement("span")
        text.className = "phrasebook-text"
        text.innerText = phrasebook_entry_text(plot)
        remove = document.createElement("button")
        remove.className = "secondary phrasebook-remove"
        remove.type = "button"
        remove.innerText = "Remove"
        remove.setAttribute("aria-label", f"Remove {plot.label} from your phrasebook")
        proxy = create_proxy(_make_phrasebook_remove_handler(plot_id))
        phrasebook_proxies.append(proxy)
        remove.addEventListener("click", proxy)
        row.appendChild(text)
        row.appendChild(remove)
        listing.appendChild(row)
