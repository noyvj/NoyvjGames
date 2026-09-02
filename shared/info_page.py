"""Shared "The Real Story" info-page widget.

Used by all 8 climate-quartet games (canopy, grid, tide, aftermath, herd,
thaw, loop, drift) — an optional, player-triggered panel with curated
real-world sources backing that game's mechanics. Before this module
existed, each game's game.py carried a byte-for-byte identical
render_info_page()/on_toggle_info_page() pair (~25+4 lines); only the
content differed. See the "REVIEW(reuse)" comment this replaced in each
game's game.py, and planning/SAVE-BUTTON-INTEGRATION.md for the shared-file
pattern this follows (shared/save-widget.js).

Loaded the same way as a game's own game.py: each game's index.html fetches
this file's source and writes it into Pyodide's virtual filesystem (as
"info_page.py", so `import info_page` resolves normally) *before* fetching
and running the game's own game.py. See any of the 8 games' index.html
boot script for the exact fetch/write.

Each game keeps its own module-level `info_page_open` boolean — it's part
of that game's get_state()/load_state() save contract, so it deliberately
stays local to the game rather than moving in here — and its own
INFO_PAGE dict (the actual framing text, mechanic tie-in, and sources
list, which is what's supposed to differ per game). This module only
holds the DOM read/write logic that used to be duplicated.
"""

from js import document


def render(info_page_data, is_open):
    """Renders the info-page panel against the standard element ids
    (#info-page-panel, #info-page-toggle-button, #info-page-framing,
    #info-page-tie-in, #info-page-sources), using the calling game's own
    INFO_PAGE-shaped dict and its current open/closed state.

    A game's render_info_page() becomes just:

        def render_info_page():
            info_page.render(INFO_PAGE, info_page_open)
    """
    panel = document.getElementById("info-page-panel")
    panel.hidden = not is_open
    toggle_button = document.getElementById("info-page-toggle-button")
    toggle_button.innerText = "Hide The Real Story" if is_open else "The Real Story"
    if not is_open:
        return
    document.getElementById("info-page-framing").innerText = info_page_data["framing"]
    document.getElementById("info-page-tie-in").innerText = info_page_data["mechanic_tie_in"]
    list_el = document.getElementById("info-page-sources")
    list_el.innerHTML = ""
    for source in info_page_data["sources"]:
        item = document.createElement("li")
        item.className = "info-page-source"
        link = document.createElement("a")
        link.href = source["url"]
        link.target = "_blank"
        link.rel = "noopener noreferrer"
        link.innerText = source["label"]
        item.appendChild(link)
        note = document.createElement("p")
        note.className = "info-page-source-note"
        note.innerText = source["note"]
        item.appendChild(note)
        list_el.appendChild(item)


def toggle(is_open):
    """Returns the new open/closed state. Just `not is_open` — exists so
    every game calls through the same seam rather than half of them doing
    this delegation and half inlining `not info_page_open` directly.

    A game's on_toggle_info_page() becomes just:

        def on_toggle_info_page(event=None):
            global info_page_open
            info_page_open = info_page.toggle(info_page_open)
            render_info_page()
    """
    return not is_open
