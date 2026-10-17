"""The geography panel: seed, new map, off switch."""

from js import document

import challengerun
import consulting
import founding
import geography

import continuum_runstate as runstate
from continuum_base import _geo_seed
from continuum_dynasty import _seed_hint

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# --- K-12 generated map with biomes -------------------------------------------------------------------------


def _geo_editable():
    return (
        runstate.campaign.revisiting is None
        and consulting.get(runstate.campaign.ui) is None
        and challengerun.get(runstate.campaign.ui) is None
        and founding.is_pristine(runstate.campaign)
    )


def on_toggle_geography(event=None):
    runstate.geography_open = not runstate.geography_open
    update_geography_panel()


def _geo_set(seed, message):
    if not _geo_editable():
        runstate.geography_status = "The map can only be chosen before the first season of a fresh settlement."
        update_geography_panel()
        return
    geography.set_seed(runstate.campaign.ui, seed)
    runstate.geography_status = message
    render()


def on_geography_new(event=None):
    seed = _seed_hint() % geography.SEED_MAX or 1
    current = geography.chosen_seed(runstate.campaign.ui)
    if seed == current:
        seed = seed % (geography.SEED_MAX - 1) + 1
    _geo_set(seed, f"A new map was drawn (seed {seed}).")


def on_geography_off(event=None):
    _geo_set(None, "Back to open land: no map.")


def on_geography_use_seed(event=None):
    raw = document.getElementById("geography-seed-input").value
    try:
        seed = int(str(raw).strip())
    except (TypeError, ValueError):
        seed = None
    if geography.clean_seed(seed) is None:
        runstate.geography_status = "Type a whole number from 1 to 2147483647."
        update_geography_panel()
        return
    _geo_set(seed, f"Map for seed {seed}.")


def update_geography_panel():
    toggle = document.getElementById("geography-toggle-button")
    toggle.innerText = "Hide Geography" if runstate.geography_open else "🗺 Geography"
    panel = document.getElementById("geography-panel")
    panel.hidden = not runstate.geography_open
    if not runstate.geography_open:
        return
    seed = _geo_seed()
    grid = geography.generate(seed)
    case = consulting.get(runstate.campaign.ui)
    editable = _geo_editable()
    note = document.getElementById("geography-note")
    if case is not None:
        note.innerText = "This consulting case comes with its own inherited ground, so the map is fixed."
    elif challengerun.get(runstate.campaign.ui) is not None:
        note.innerText = "Challenge runs are played on open land so their scores stay comparable."
    elif not editable:
        note.innerText = "The map is fixed once the first season has begun (or while looking back)."
    else:
        note.innerText = (
            "Optional. Draw a map for this settlement before its first season: each biome gives a small boon and a "
            "small price. Share the seed number and someone else gets the same ground."
        )
    document.getElementById("geography-seed").innerText = (
        f"Seed {seed}: {geography.summary_text(grid)}." if grid else "Open land: no map (every number as usual)."
    )
    document.getElementById("geography-map").innerHTML = geography.map_svg(grid)
    holder = document.getElementById("geography-list")
    holder.innerHTML = ""
    for line in geography.describe(grid):
        node = document.createElement("p")
        node.className = "row-blurb"
        node.innerText = line
        holder.appendChild(node)
    document.getElementById("geography-new-button").disabled = not editable
    document.getElementById("geography-new-button").innerText = "New map" if grid else "Draw a map"
    document.getElementById("geography-off-button").disabled = not editable or not grid
    document.getElementById("geography-use-seed-button").disabled = not editable
    document.getElementById("geography-seed-input").disabled = not editable
    document.getElementById("geography-status").innerText = runstate.geography_status
