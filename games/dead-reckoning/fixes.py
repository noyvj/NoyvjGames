"""Dead Reckoning -- landmark fixes (Watch-by-watch). A fix is a bearing and a distance off a known landmark, each with a small
stated error. It never reveals the true position: the player reads the numbers and the game moves their PLOT to where the
numbers put the ship (the landmark, minus the distance along the bearing), which is close to the truth but not exactly it.

The errors are repeatable (a hash of the chart, the landmark and the watch), bounded by the stated errors, and need no random
module, so the same watch always gives the same readings."""

from geom import bearing, dist, norm_deg, unit
from sim import unit_noise

BEARING_ERR_DEG = 2.0       # a bearing is good to this many degrees either way
RANGE_ERR_SHARE = 0.05      # a distance is good to this share either way


def _hash(*parts):
    h = 2166136261
    for ch in "|".join(str(p) for p in parts):
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def in_sight(chart, true_pos):
    """The landmarks the ship can see from where she really is. Fog hides them all."""
    if chart.get("fog"):
        return []
    return [m for m in chart.get("landmarks", ()) if dist(true_pos, (m["x"], m["y"])) <= m["visible"]]


def readings(chart, true_pos, watch):
    """One reading per landmark in sight: the bearing TO it (whole degrees) and the distance (0.1 nm), with their errors."""
    out = []
    for m in in_sight(chart, true_pos):
        seed = _hash(chart["id"], m["id"], watch)
        true_b = bearing(true_pos, (m["x"], m["y"]))
        true_d = dist(true_pos, (m["x"], m["y"]))
        b = int(round(norm_deg(true_b + unit_noise(seed, 1) * BEARING_ERR_DEG))) % 360
        d = round(max(0.1, true_d * (1.0 + unit_noise(seed, 2) * RANGE_ERR_SHARE)), 1)
        out.append({"id": m["id"], "name": m["name"], "kind": m["kind"], "bearing": b, "range": d,
                    "bearing_err": BEARING_ERR_DEG, "range_err_pct": int(RANGE_ERR_SHARE * 100)})
    return out


def position_from(chart, landmark_id, brg, rng):
    """Where the numbers put the ship: the landmark's position, minus the range along the bearing."""
    for m in chart.get("landmarks", ()):
        if m["id"] == landmark_id:
            ux, uy = unit(brg)
            return (round(m["x"] - rng * ux, 2), round(m["y"] - rng * uy, 2))
    return None
