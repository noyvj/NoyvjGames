"""Dead Reckoning -- what a finished passage changes in the player's record (and which achievement facts it proves).

`record_outcome` is pure over plain dicts: it updates the meta record in place and returns the flags newly earned, so the
tests can drive it without a page."""

import fleet
from geom import seg_point_dist
from sim import plan_distance
from state import FLAGS, LONG_WAY_NM, new_record

DEAD_ON_NM = 0.5
FAIR_STREAM_SHARE = 0.6
ROCKS_ON_THE_LINE = 3
LINE_MARGIN = 0.5


def hazards_on_the_line(chart):
    """How many hazards lie on (or within half a mile of) the straight line from the start to the flag."""
    n = 0
    for hz in chart.get("hazards", ()):
        if seg_point_dist(tuple(chart["start"]), tuple(chart["dest"]), (hz["x"], hz["y"])) <= hz["r"] + LINE_MARGIN:
            n += 1
    return n


def has_tide(chart):
    return any(z.get("tide") for z in chart.get("currents", ()))


def record_outcome(meta, chart, run, res, sc, scored=True, fix_taken=False):
    """Apply one finished passage. `scored` False (practice) skips the per-chart record. Returns the new flags.
    On a two-ship chart `res` and `sc` are the fleet's (fleet.sail_fleet / fleet.score_fleet): landfall means both ships, and the
    distance facts use the longer of the two plans."""
    before = set(meta["flags"])
    two = fleet.is_two(chart)
    plans = [run["legs"], run["legs2"]] if two else [run["legs"]]
    groundings = res.get("groundings") if two else ([res["aground"]] if res["aground"] else [])
    flags = set(before)
    if scored:
        rec = meta["charts"].setdefault(chart["id"], new_record())
        rec["attempts"] += 1
        rec["stars"] = max(rec["stars"], sc["stars"])
        if sc["arrived"] and (rec["best_error_nm"] is None or sc["miss_nm"] < rec["best_error_nm"]):
            rec["best_error_nm"] = sc["miss_nm"]
        known = {h["id"] for h in chart.get("hazards", ()) if h.get("charted", True)}
        found = set(rec["discovered"])
        for hid in list(res["close"]) + [g["hazard"] for g in groundings]:
            if hid not in known and any(h["id"] == hid for h in chart.get("hazards", ())):
                found.add(hid)
        rec["discovered"] = sorted(found)
        if sc["stars"] == 3 and not run["helpers"]:
            rec["trusted"] = True
    if sc["arrived"]:
        flags.add("landfall")
        best = meta["best"]
        if best["smallest_final_error_nm"] is None or sc["miss_nm"] < best["smallest_final_error_nm"]:
            best["smallest_final_error_nm"] = sc["miss_nm"]
        distance = max(plan_distance(p) for p in plans)
        if distance > best["longest_route_nm"]:
            best["longest_route_nm"] = round(distance, 2)
        if sc["forecast_error_nm"] is not None and sc["forecast_error_nm"] <= DEAD_ON_NM:
            flags.add("dead_on")
        if chart.get("currents") and sc["naive_miss_nm"] >= 2.0 and (sc["beat_naive_pct"] or 0) >= 50:
            flags.add("set_and_drift")
        if max(hazards_on_the_line(c) for c in fleet.ships(chart)) >= ROCKS_ON_THE_LINE:
            flags.add("around_rocks")
        if chart.get("fog"):
            flags.add("fog_clear")
        if has_tide(chart) and (sc["tide_fair"] or 0.0) >= FAIR_STREAM_SHARE:
            flags.add("riding_tide")
        if any(leg["speed"] <= 0 for p in plans for leg in p):
            flags.add("waited")
        if distance > LONG_WAY_NM:
            flags.add("long_way")
        if sc["stars"] == 3 and not run["helpers"]:
            flags.add("trusted")
        if two:
            flags.add("two_ships")
    if sc["aground"]:
        flags.add("aground")
    if fix_taken:
        flags.add("first_fix")
    meta["flags"] = [f for f in FLAGS if f in flags]
    return sorted(flags - before)
