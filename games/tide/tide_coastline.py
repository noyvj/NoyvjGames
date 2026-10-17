"""Damage messages, the coastline grid renderers (current, mini, before/now) and the season scrubber (D-4)."""

from js import document

import tide_runstate as runstate
from tide_coasts import _is_seawall_row, coastline_grid, heritage_sites, row_flood_threshold, tile_row_state
from tide_rules import (
    COASTLINE_COLS, COASTLINE_ROWS, FLOODED, HERITAGE_COL, HERITAGE_LOST, HERITAGE_PROTECTED,
    HERITAGE_UPKEEP,
)


def damage_saved_message(saved):
    if saved <= 0:
        return "No adaptation investment yet — every season of sea-level rise is hitting at full force."
    return (
        f"Adaptation has saved you {saved:.0f} in cumulative damage compared to "
        f"no investment at all — the sea kept rising, but you're weathering it better."
    )


def damage_trend_message(trend):
    if trend is None:
        return "Not enough seasons yet to show a trend."
    first_half_avg, second_half_avg = trend
    if second_half_avg < first_half_avg:
        return (
            f"Your damage curve is flattening ({first_half_avg:.1f}/season → "
            f"{second_half_avg:.1f}/season) — early adaptation is paying off."
        )
    if second_half_avg > first_half_avg:
        return (
            f"Your damage curve is steepening ({first_half_avg:.1f}/season → "
            f"{second_half_avg:.1f}/season)."
        )
    return f"Your damage rate has held steady at {second_half_avg:.1f}/season."


def _resync_previous_flooded_rows():
    """Recomputes _previous_flooded_rows straight from live sea_level,
    so the next render_coastline() call doesn't mistake already-flooded
    rows (from a fresh load, or a fresh game) for newly-flooded ones."""
    runstate._previous_flooded_rows = {
        row for row in range(COASTLINE_ROWS) if tile_row_state(row, runstate.state.sea_level) == FLOODED
    }


def heritage_site_at(row, col):
    if col != HERITAGE_COL:
        return None
    for site in heritage_sites():
        if site["row"] == row:
            return site
    return None


def heritage_status_text(site):
    status = runstate.state.heritage.get(site["id"])
    if status == HERITAGE_PROTECTED:
        return f"{site['emoji']} {site['name']}: protected (upkeep {HERITAGE_UPKEEP}/season)."
    if status == HERITAGE_LOST:
        return f"✖ {site['name']}: lost to the sea."
    return f"{site['emoji']} {site['name']}: unprotected — floods with row {site['row'] + 1}. Protect for {site['cost']}."


def render_coastline():
    grid_el = document.getElementById("coastline-grid")
    # D-4: while the season scrubber is on an earlier season, draw that season read-only
    # (no flash, no tide, no tooltip about "the current pace") and leave the flash tracker alone.
    scrubbed = scrub_view()
    live = scrubbed is None
    view = runstate.state.coast_view() if live else scrubbed
    # D-7: a re-render replaces every tile, so remember which one had keyboard
    # focus and give it back afterwards (otherwise Tab order restarts).
    focused = getattr(document, "activeElement", None)
    focused_id = getattr(focused, "id", "") if focused is not None else ""
    grid_el.innerHTML = ""
    grid_el.className = "coastline-grid" + ("" if live else " coastline-grid--scrubbed")
    tier_index = view["tier"]
    retreat_rows = view["retreat_rows"]
    current_flooded_rows = set()
    tidal_rows = view.get("tidal", [])
    for row_index, row in enumerate(coastline_grid(view["sea_level"])):
        tile_state = row[0]  # every column in a row shares the same state
        threshold = row_flood_threshold(row_index)
        # D1: a row given up by managed retreat is drawn flooded, with its
        # own class (diagonal hatch in CSS) so it reads as chosen.
        retreated = row_index in retreat_rows
        if retreated:
            tile_state = FLOODED
        if tile_state == FLOODED:
            current_flooded_rows.add(row_index)
        # D8: flash any row flooding for the first time this render --
        # compared against last render's snapshot, not against "flooded
        # right now", so the flash fires exactly once, at the moment of
        # crossing, not on every subsequent re-render while still flooded.
        just_flooded = live and tile_state == FLOODED and row_index not in runstate._previous_flooded_rows
        for col_index in range(COASTLINE_COLS):
            tile = document.createElement("div")
            tile.id = f"coastline-tile-{row_index}-{col_index}"
            tile.className = f"coastline-tile coastline-{tile_state}"
            if _is_seawall_row(row_index, tier_index):
                # D28: per-tier class -> a distinct texture per tier, so
                # tiers are told apart without relying on colour.
                tile.className += f" coastline-seawall coastline-seawall--t{tier_index}"
            if retreated:
                tile.className += " coastline-retreated"
            if just_flooded:
                tile.className += " coastline-flash"
            site = heritage_site_at(row_index, col_index)
            if site is not None:
                status = view["heritage"].get(site["id"])
                tile.innerText = site["emoji"] if status != HERITAGE_LOST else "✖"
                tile.className += f" coastline-heritage coastline-heritage--{status}"
            # D8: dry rows the current tide reaches get a dashed edge
            # (a shape cue, not a hue one) and a title note.
            tidal = row_index in tidal_rows
            if tidal:
                tile.className += " coastline-tidal"
            # D19: a native hover/tap tooltip naming this row's flood
            # threshold -- zero extra markup, works identically for mouse
            # hover and (on most mobile browsers) a long-press/tap.
            if not live:
                base_title = (
                    "Cleared by managed retreat." if retreated
                    else "Flooded." if tile_state == FLOODED else "Dry."
                ) + f" Earlier view: Season {scrubbed['season']} (read-only)."
            else:
                base_title = (
                    "Managed retreat — this row was cleared on purpose and its people rehoused inland."
                    if retreated
                    else f"Flooded — this row floods once sea level reaches {threshold:.0f}."
                    if tile_state == FLOODED
                    else f"Floods once sea level reaches {threshold:.0f} "
                    f"(about {runstate.state.seasons_until_flood(row_index)} season(s) at the current pace)."
                    + (" This season's tide is washing over it." if tidal else "")
                )
            if site is not None:
                status = view["heritage"].get(site["id"])
                heritage_line = (
                    heritage_status_text(site) if live
                    else f"{site['emoji']} {site['name']}: {status}."
                )
                tile.title = heritage_line + " " + base_title
            else:
                tile.title = base_title
            # D-7: one Tab stop per row (column 0), but every tile is a labelled, focusable
            # target so Left/Right and Up/Down (ui.js) can walk the grid column by column.
            tile.tabIndex = 0 if col_index == 0 else -1
            tile.setAttribute("role", "img")
            tile.setAttribute(
                "aria-label",
                runstate.state.coastline_row_description(row_index, view)
                if col_index == 0
                else runstate.state.coastline_row_description(row_index, view, col_index),
            )
            grid_el.appendChild(tile)
    if live:
        runstate._previous_flooded_rows = current_flooded_rows
    grid_el.setAttribute("role", "group")
    grid_el.setAttribute(
        "aria-label",
        "Coastline, one Tab stop per row. Use the arrow keys to move between rows and columns.",
    )
    description = document.getElementById("coastline-description")
    if description is not None:
        description.innerText = (
            runstate.state.coastline_description() if live
            else f"Season {scrubbed['season']} (earlier, read-only). " + runstate.state.scrub_text(scrubbed)
        )
    if focused_id.startswith("coastline-tile-"):
        refocus = document.getElementById(focused_id)
        if refocus is not None:
            refocus.focus()


def _render_mini_coastline(container_id, sea_level, tier_index=0):
    grid_el = document.getElementById(container_id)
    grid_el.innerHTML = ""
    for row_index, row in enumerate(coastline_grid(sea_level)):
        for tile_state in row:
            tile = document.createElement("div")
            tile.className = f"coastline-tile coastline-{tile_state}"
            if _is_seawall_row(row_index, tier_index):
                tile.className += " coastline-seawall"
            grid_el.appendChild(tile)


def render_coastline_comparison():
    """Iteration-pass addition: a small before/now side-by-side, so the
    hope-angle payoff (adaptation buys visibly less coastline loss) has
    a direct visual, not just the damage_saved() number.

    D18: "before" reads state.baseline_sea_level rather than a hardcoded
    0.0 -- defaults to the real Season 1 start, but set_comparison_
    baseline() can move it to any later checkpoint the player chooses.
    The before-grid's seawall overlay is always drawn at tier_index=0
    regardless of baseline, a deliberate simplification: Tide doesn't
    keep a season-by-season tier history to draw the *actual* tier that
    was active at an arbitrary past checkpoint, and the flood/land state
    itself (the part the comparison is really about) depends only on
    sea level, never on tier."""
    _render_mini_coastline("coastline-before-grid", runstate.state.baseline_sea_level, tier_index=0)
    _render_mini_coastline("coastline-now-grid", runstate.state.sea_level, tier_index=runstate.state.current_tier_index())
    before_label = document.getElementById("coastline-before-label")
    if before_label is not None:
        before_label.innerText = f"Season {runstate.state.baseline_season}"
    document.getElementById("coastline-now-label").innerText = f"Season {runstate.state.season}"


# ---- D-4 season scrubber -----------------------------------------------


def _state_stamp():
    """Anything the player can change that should end a read-only look back."""
    return (
        runstate.state.season, round(runstate.state.funds, 1), sum(runstate.state.capacity.values()),
        len(runstate.state.ticker_full_history), len(runstate.state.chronicle), runstate.state.output_mix,
        runstate.state.hard_lag_mode, runstate.state.sea_scenario,
    )


def scrub_view():
    """The scrubbed season as a coastline view dict, or None while viewing the live run.
    Any change to the live run (invest, advance, load, ...) quietly ends the look back."""
    if runstate.scrub_season is None:
        return None
    snap = runstate.state.scrub_snapshot(runstate.scrub_season) if runstate._scrub_stamp == _state_stamp() else None
    if snap is None:
        runstate.scrub_season = None
        return None
    snap = dict(snap)
    snap["tidal"] = []
    return snap


def scrub_to(position):
    if runstate.state.scrub_snapshot(position) is None:
        runstate.scrub_season = None
    else:
        runstate.scrub_season = position
        runstate._scrub_stamp = _state_stamp()
    render_coastline()
    render_scrubber()


def render_scrubber():
    section = document.getElementById("scrub-section")
    if section is None:
        return
    positions = runstate.state.scrub_positions()
    section.hidden = not positions
    if not positions:
        return
    view = scrub_view()
    slider = document.getElementById("scrub-slider")
    if slider is not None:
        slider.setAttribute("min", str(positions[0]))
        slider.setAttribute("max", str(runstate.state.season))
        slider.value = str(view["season"] if view else runstate.state.season)
        slider.setAttribute(
            "aria-valuetext",
            f"Season {view['season']}, earlier and read-only" if view else f"Season {runstate.state.season}, the live run",
        )
    readout = document.getElementById("scrub-readout")
    if readout is not None:
        readout.innerText = (
            runstate.state.scrub_text(view) if view
            else f"Season {runstate.state.season} (live). Drag the slider back to look at an earlier season; nothing you do there changes your run."
        )
    live_button = document.getElementById("scrub-live-button")
    if live_button is not None:
        live_button.hidden = view is None
