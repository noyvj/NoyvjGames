"""Dead Reckoning -- chart content. A chart is a plain dict; see sim.py for what the simulation reads and CLAUDE.md
for the whole schema. Charts are content, not state: the save never contains one, only the id of the chart played."""

DEMO_CHART = {
    "id": "demo", "name": "Gull Sound", "chapter": "open", "size": 20,
    "start": [3.0, 3.0], "dest": [17.0, 16.0], "arrival_radius": 1.5, "deadline": 10.0,
    "speeds": [3.0, 7.0], "start_hour": 0.0,
    "land": [{"id": "gull-island", "name": "Gull Island", "poly": [[13, 1], [18.5, 1], [18.5, 5], [15, 6.2], [13, 4]]}],
    "hazards": [
        {"id": "pike-reef", "kind": "reef", "name": "Pike Reef", "x": 10.0, "y": 9.2, "r": 1.2, "charted": True},
        {"id": "dog-shoal", "kind": "shoal", "name": "Dog Shoal", "x": 6.0, "y": 13.0, "r": 1.5, "charted": True},
        {"id": "needle", "kind": "rock", "name": "The Needle", "x": 14.5, "y": 13.0, "r": 0.5, "charted": True},
    ],
    "currents": [
        {"id": "east-set", "rect": [6, 0, 20, 12], "set": 80, "drift_range": [0.8, 1.4], "true_set": 85, "true_drift": 1.1},
    ],
    "landmarks": [{"id": "north-light", "name": "North Light", "kind": "lighthouse", "x": 12.0, "y": 18.0, "visible": 9.0}],
}


CHARTS = {DEMO_CHART["id"]: DEMO_CHART}


def get_chart(chart_id):
    return CHARTS.get(chart_id)


def all_charts():
    return list(CHARTS.values())


def hazard_ids():
    """chart id -> the ids of its hazards (used to validate a loaded save's `discovered` lists)."""
    return {cid: {h["id"] for h in c.get("hazards", ())} for cid, c in CHARTS.items()}
