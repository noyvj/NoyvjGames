"""The sortable fleet overview (C-14).
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document

import grid_runstate as runstate
from grid_rules import GENERATION_TYPES, PLANT_ICON, PLANT_LABEL, PLANT_TYPES, WEAR_TIER_GLYPH


# ---- C-14 sortable fleet overview ---------------------------------------------------------------------------------
# One row per plant type: units standing, wear, aging-breakdown risk, when the auto-maintain schedule next fires and
# what the type earns per round. A pure read of existing numbers (wear_percent, breakdown_risk_probability,
# maintenance_schedule, the revenue share used by the plant-mix hover). The sort is a this-session view choice.
FLEET_COLUMNS = (
    ("plant", "Plant"),
    ("count", "Units"),
    ("wear", "Wear"),
    ("risk", "Breakdown risk"),
    ("next", "Next maintenance"),
    ("revenue", "Revenue per round"),
)


def rounds_until_scheduled_maintenance(plant_type):
    """Rounds until this type's auto-maintain pass next fires (0 = in the round about to be played), or None
    for manual-only or nothing standing."""
    interval = runstate.state.maintenance_schedule[plant_type]
    if interval <= 0 or runstate.state.plant_counts[plant_type] <= 0:
        return None
    return (-runstate.state.round_number) % interval


def fleet_rows():
    paid_units = min(runstate.state.total_capacity(), runstate.state.demand)
    rows = []
    for plant_type in PLANT_TYPES:
        count = runstate.state.plant_counts[plant_type]
        generating = plant_type in GENERATION_TYPES
        revenue = runstate.state.capacity_share(plant_type) * paid_units * runstate.state.revenue_per_unit if generating else 0.0
        rows.append({
            "type": plant_type,
            "plant": PLANT_LABEL[plant_type],
            "count": count,
            "wear": runstate.state.wear_percent(plant_type) if count > 0 else 0,
            "wear_class": runstate.state.wear_class(plant_type) if count > 0 else "",
            "risk": runstate.state.breakdown_risk_probability(plant_type) * 100 if count > 0 else 0.0,
            "next": rounds_until_scheduled_maintenance(plant_type),
            "revenue": revenue,
            "generating": generating,
        })
    return rows


def sort_fleet_rows(rows, key, reverse):
    """Stable sort by one column; 'plant' sorts by name, manual-only (no next maintenance) sorts last when
    ascending."""
    if key == "plant":
        return sorted(rows, key=lambda r: r["plant"], reverse=reverse)
    if key == "next":
        return sorted(rows, key=lambda r: (r["next"] is None, r["next"] or 0), reverse=reverse)
    return sorted(rows, key=lambda r: r[key], reverse=reverse)


def _fleet_next_text(row):
    if row["count"] <= 0:
        return "none standing"
    if row["next"] is None:
        return "manual only"
    return "this round" if row["next"] == 0 else f"in {row['next']} round(s)"


def fleet_table_body_html(rows):
    out = []
    for row in rows:
        wear = f"{WEAR_TIER_GLYPH[row['wear_class']]} {row['wear']}%" if row["count"] > 0 else "-"
        risk = f"{row['risk']:.0f}%" if row["count"] > 0 else "-"
        revenue = f"about {row['revenue']:.0f}" if row["generating"] and row["count"] > 0 else "-"
        out.append(
            f'<tr><th scope="row">{PLANT_ICON[row["type"]]} {row["plant"]}</th><td>{row["count"]}</td>'
            f"<td>{wear}</td><td>{risk}</td><td>{_fleet_next_text(row)}</td><td>{revenue}</td></tr>"
        )
    return "".join(out)


def set_fleet_sort(key):
    """Click a header: a new column sorts high to low (names low to high); the same column flips."""
    if key not in dict(FLEET_COLUMNS):
        return False
    if key == runstate.fleet_sort_key:
        runstate.fleet_sort_reverse = not runstate.fleet_sort_reverse
    else:
        runstate.fleet_sort_key = key
        runstate.fleet_sort_reverse = key != "plant"
    return True


def render_fleet_overview():
    rows = sort_fleet_rows(fleet_rows(), runstate.fleet_sort_key, runstate.fleet_sort_reverse)
    document.getElementById("fleet-body").innerHTML = fleet_table_body_html(rows)
    for key, label in FLEET_COLUMNS:
        button = document.getElementById(f"fleet-sort-{key}")
        if key == runstate.fleet_sort_key:
            arrow = "▼" if runstate.fleet_sort_reverse else "▲"
            word = "high to low" if runstate.fleet_sort_reverse else "low to high"
            if key == "plant":
                word = "Z to A" if runstate.fleet_sort_reverse else "A to Z"
            button.innerText = f"{label} {arrow}"
            button.title = f"Sorted {word}. Press to reverse."
        else:
            button.innerText = label
            button.title = f"Sort by {label.lower()}."
