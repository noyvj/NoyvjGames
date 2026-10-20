"""Real-grid comparison (C29) and the regional grid panel (C3).
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import json
import os

try:
    from js import document
except ImportError:
    document = None

import grid_runstate as runstate
from grid_rules import GENERATION_TYPES, PLANT_CAPACITY, PLANT_LABEL


# ===========================================================================
# C29 -- real-grid comparison: set your plant mix beside the published
# electricity-generation mix of a real region. The figures are read from
# public sources (below) and are the SHARE OF GENERATION in the stated year;
# your bars are the share of standing CAPACITY, which is what this game
# tracks, so a source with a low capacity factor (solar) shows a smaller real
# share than its capacity share would. The panel says so. "Clean" means
# nuclear, solar, wind and hydro, the same non-fossil idea the game's own score
# uses; the real regions' "other" (biomass, oil) is counted as neither.
# ===========================================================================
REAL_GRIDS = {
    "us": {
        "label": "United States", "year": 2025,
        "source": "U.S. Energy Information Administration, Electricity in the U.S. (utility-scale generation, rounded 'about' figures)",
        "shares": {"coal": 17.0, "gas": 41.0, "nuclear": 18.0, "solar": 7.0, "wind": 11.0, "hydro": 6.0, "other": 0.9},
    },
    "de": {
        "label": "Germany", "year": 2025,
        "source": "Net public generation as tabulated on Wikipedia's Energy in Germany (lignite 16.3% + hard coal 6.3% shown as coal; biomass 8.7% shown as other)",
        "shares": {"coal": 22.6, "gas": 13.0, "nuclear": 0.0, "solar": 17.0, "wind": 31.8, "hydro": 4.1, "other": 8.7},
    },
    "fr": {
        "label": "France", "year": 2020,
        "source": "Wikipedia's Electricity sector in France, 2020 production table (oil 0.43% + bioenergies 1.84% shown as other); the page carried no newer full-year table when this was added",
        "shares": {"coal": 0.3, "gas": 7.18, "nuclear": 70.58, "solar": 2.16, "wind": 6.34, "hydro": 11.16, "other": 2.27},
    },
}
REAL_GRID_CLEAN_TYPES = ("nuclear", "solar", "wind", "hydro")


def read_data_text(window_name, filename):
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, window_name, None) if _js is not None else None
    if raw is not None:
        return str(raw)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "data", filename), encoding="utf-8") as handle:
        return handle.read()


def read_data_json(window_name, filename):
    try:
        return json.loads(read_data_text(window_name, filename))
    except (ValueError, OSError):
        return None


def set_real_grid(choice):
    """Turns the comparison on for a known region, or off (None). Returns
    whether the value was accepted."""
    if choice is None:
        runstate.real_grid_choice = None
        return True
    if not isinstance(choice, str) or choice not in REAL_GRIDS:
        return False
    runstate.real_grid_choice = choice
    return True


def real_grid_clean_share(shares):
    return sum(shares.get(t, 0.0) for t in REAL_GRID_CLEAN_TYPES)


def real_grid_rows(choice=None):
    """None when off or the player has no capacity yet; otherwise
    (rows, verdict) where rows are (label, yours, theirs, difference) strings
    for each generation type plus other and the clean total."""
    choice = runstate.real_grid_choice if choice is None else choice
    if choice not in REAL_GRIDS:
        return None
    if runstate.state.total_capacity() <= 0:
        return None
    region = REAL_GRIDS[choice]
    theirs = region["shares"]
    mine = {t: runstate.state.capacity_share(t) * 100 for t in GENERATION_TYPES}
    rows = []
    for plant_type in GENERATION_TYPES:
        rows.append((
            PLANT_LABEL[plant_type], f"{mine[plant_type]:.0f}%", f"{theirs.get(plant_type, 0.0):.0f}%",
            f"{mine[plant_type] - theirs.get(plant_type, 0.0):+.0f}",
        ))
    rows.append(("Other (biomass, oil)", "0%", f"{theirs.get('other', 0.0):.0f}%", f"{-theirs.get('other', 0.0):+.0f}"))
    my_clean, their_clean = real_grid_clean_share(mine), real_grid_clean_share(theirs)
    rows.append(("Clean total", f"{my_clean:.0f}%", f"{their_clean:.0f}%", f"{my_clean - their_clean:+.0f}"))
    gap = my_clean - their_clean
    if abs(gap) < 0.5:
        verdict = f"Your clean share matches {region['label']} ({region['year']}) at about {their_clean:.0f}%."
    else:
        verdict = (
            f"Your grid is {abs(gap):.0f} points {'cleaner' if gap > 0 else 'dirtier'} than {region['label']}'s "
            f"real grid ({their_clean:.0f}% clean in {region['year']}, against your {my_clean:.0f}%)."
        )
    return rows, verdict


def render_real_grid():
    select = document.getElementById("real-grid-select")
    table = document.getElementById("real-grid-table")
    verdict_el = document.getElementById("real-grid-verdict")
    source_el = document.getElementById("real-grid-source")
    select.value = runstate.real_grid_choice or "off"
    table.innerHTML = ""
    if runstate.real_grid_choice is None:
        verdict_el.innerText = "Pick a real region to compare your plant mix against its published generation mix."
        source_el.hidden = True
        return
    region = REAL_GRIDS[runstate.real_grid_choice]
    source_el.hidden = False
    source_el.innerText = (
        f"Source: {region['source']}. Real figures are shares of generation; yours are shares of capacity, "
        "so low-capacity-factor sources such as solar read differently."
    )
    result = real_grid_rows()
    if result is None:
        verdict_el.innerText = "Build some generation to see how it compares."
        return
    rows, verdict = result
    verdict_el.innerText = verdict
    header = document.createElement("div")
    header.className = "shadow-row shadow-row--head"
    for text in ("", "You", f"{region['label']} {region['year']}", "Gap"):
        cell = document.createElement("span")
        cell.innerText = text
        header.appendChild(cell)
    table.appendChild(header)
    for label, yours, theirs, gap in rows:
        line = document.createElement("div")
        line.className = "shadow-row"
        for text in (label, yours, theirs, gap):
            cell = document.createElement("span")
            cell.innerText = text
            line.appendChild(cell)
        table.appendChild(line)


CAPACITY_FACTOR_LABEL = {
    "coal": "Coal",
    "gas": "Natural gas: combined cycle",
    "nuclear": "Nuclear",
    "solar": "Solar: photovoltaic",
    "wind": "Wind",
    "hydro": "Hydroelectric",
}


def load_capacity_factors():
    return read_data_json("CAPACITY_FACTORS_JSON", "capacity_factors.json")


def capacity_factor_rows(data):
    rows = []
    for plant_type in GENERATION_TYPES:
        label = CAPACITY_FACTOR_LABEL[plant_type]
        found = False
        for table in data.get("tables", []):
            for tech in table.get("technologies", []):
                if tech.get("label") == label:
                    annuals = tech.get("annual", [])
                    if annuals:
                        r = annuals[-1]
                        pct = r["capacity_factor_pct"]
                        rows.append({
                            "plant_type": plant_type,
                            "label": PLANT_LABEL[plant_type],
                            "nameplate": PLANT_CAPACITY[plant_type],
                            "pct": pct,
                            "average": round(PLANT_CAPACITY[plant_type] * pct / 100, 1),
                            "year": r["year"],
                        })
                    found = True
                    break
            if found:
                break
    return rows


def capacity_factor_note(data):
    return (
        "Source: U.S. Energy Information Administration, Electric Power Monthly Tables 6.07.A and 6.07.B, "
        f"data for {data['tables'][1]['data_for']}; a dated snapshot read on {data['read']}, "
        "because EIA pages cannot be read live from a browser."
    )


def render_regional_grid():
    button = document.getElementById("regional-grid-connect-button")
    display = document.getElementById("regional-grid-display")
    if runstate.state.regional_grid_connected:
        button.innerText = "Regional grid: connected"
        button.disabled = True
        display.hidden = False
        display.innerText = runstate.state.regional_grid_readout_text()
    else:
        button.innerText = "Connect a regional grid"
        button.disabled = False
        display.hidden = True
