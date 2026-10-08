"""Dead Reckoning -- small constructors so a chart file reads like a chart, not like a pile of dicts."""


def reef(hid, name, x, y, r, charted=True):
    return {"id": hid, "kind": "reef", "name": name, "x": x, "y": y, "r": r, "charted": charted}


def shoal(hid, name, x, y, r, charted=True):
    return {"id": hid, "kind": "shoal", "name": name, "x": x, "y": y, "r": r, "charted": charted}


def rock(hid, name, x, y, r, charted=True):
    return {"id": hid, "kind": "rock", "name": name, "x": x, "y": y, "r": r, "charted": charted}


def land(lid, name, poly):
    return {"id": lid, "name": name, "poly": [list(p) for p in poly]}


def stream(zid, name, rect, set_deg, drift_range, true_set, true_drift, tide=None):
    """A current zone. `set_deg` and `drift_range` are what the chart prints; `true_set` and `true_drift` are what the sea does."""
    zone = {"id": zid, "name": name, "rect": list(rect), "set": set_deg, "drift_range": list(drift_range),
            "true_set": true_set, "true_drift": true_drift}
    if tide:
        zone["tide"] = dict(tide)
    return zone


def wind(from_deg, rng, true):
    return {"from": from_deg, "range": list(rng), "true": true}


def light(lid, name, x, y, visible=9.0):
    return {"id": lid, "name": name, "kind": "lighthouse", "x": x, "y": y, "visible": visible}


def headland(lid, name, x, y, visible=8.0):
    return {"id": lid, "name": name, "kind": "headland", "x": x, "y": y, "visible": visible}


def buoy(lid, name, x, y, visible=5.0):
    return {"id": lid, "name": name, "kind": "buoy", "x": x, "y": y, "visible": visible}


def chart(cid, name, chapter, **fields):
    """A chart with the defaults every chart shares; `waypoints` is the authored route the par plan is shot along."""
    base = {"id": cid, "name": name, "chapter": chapter, "size": 20, "arrival_radius": 1.5, "speeds": [3.0, 7.0], "start_hour": 0.0,
            "land": [], "hazards": [], "currents": [], "landmarks": [], "naive_fails": False, "waypoints": [], "intro": "", "log": {}}
    base.update(fields)
    if not base["waypoints"]:
        base["waypoints"] = [base["start"], base["dest"]]
    return base
