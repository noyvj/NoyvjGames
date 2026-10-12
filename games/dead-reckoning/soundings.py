"""Dead Reckoning -- depth soundings, the plan's second kind of fix. A sounding is the depth under the ship in fathoms. Unlike a
landmark bearing it can be read in fog, but it never gives a position by itself: the navigator matches the number against the
depths printed on the chart, and more than one place can fit.

A chart may list depth areas (`chartkit.depth_area`, under the chart's "depths"); anywhere else is open water at the chart's
"open_depth" (OPEN_DEPTH when it has none). Readings carry a small stated error that is repeatable (a hash of the chart and the
watch) and needs no random module, so the same watch always gives the same sounding.

Engine only: no chart has depth areas yet and the page does not offer soundings. Wiring them into Watch-by-watch is left for later."""

from geom import dist
from sim import unit_noise

OPEN_DEPTH = 40             # fathoms of open water away from any charted depth area
SOUNDING_ERR_SHARE = 0.10   # a sounding is good to this share either way


def _hash(*parts):
    h = 2166136261
    for ch in "|".join(str(p) for p in parts):
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def depth_at(chart, pos):
    """The true depth at pos: the shallowest depth area covering it, otherwise the chart's open water."""
    covering = [a["fathoms"] for a in chart.get("depths", ()) if dist(pos, (a["x"], a["y"])) <= a["r"]]
    return min(covering) if covering else chart.get("open_depth", OPEN_DEPTH)


def sounding(chart, true_pos, watch):
    """One sounding at the ship's true position, in whole fathoms, with its stated error. Fog does not stop it."""
    true_depth = depth_at(chart, true_pos)
    seed = _hash(chart["id"], "sounding", watch)
    depth = int(round(max(1.0, true_depth * (1.0 + unit_noise(seed, 3) * SOUNDING_ERR_SHARE))))
    return {"depth": depth, "err_pct": int(SOUNDING_ERR_SHARE * 100)}


def _fits(charted, depth, share):
    return abs(charted - depth) <= charted * share + 1          # +1: a reading is rounded to whole fathoms


def matching_areas(chart, depth, share=SOUNDING_ERR_SHARE):
    """The ids of the depth areas a reading could have come from, in chart order, then "open" if open water fits too."""
    found = [a["id"] for a in chart.get("depths", ()) if _fits(a["fathoms"], depth, share)]
    if _fits(chart.get("open_depth", OPEN_DEPTH), depth, share):
        found.append("open")
    return found
