"""Dead Reckoning -- two ships on one chart (milestone 7). Pure Python, no DOM, deterministic.

A two-ship chart is an ordinary chart (its top-level start, dest, speeds, deadline and arrival radius describe Ship A) with one extra
key, `ship2`, holding Ship B's own `start, dest, speeds, deadline, arrival_radius, waypoints, par_wait` (and optionally `naive_fails`,
`fair_ok`). Both ships sail the SAME sea: the same land, hazards, streams, wind, compass error, tide clock and fog.

The ships never push each other, so each sails exactly as it would alone (`sim.sail` on that ship's own view of the chart) and the two
true tracks are then compared on a shared clock:

    The rule, stated on screen: keep the two ships at least SEPARATION nm apart while both are under way. A closer approach costs one
    star (never the first) and is reported as an event; it never ends the passage, and a retry is always free.

The sail is still a pure function of (chart, both plans, seed): Ship B uses the seed stepped by SEED_STEP so the two ships' gusts differ.
"""

import math

import sim

SEPARATION = 1.0              # nm: closer than this, while both ships are under way, costs one star
TAGS = ("A", "B")
SEED_STEP = 7919
SHIP_KEYS = ("start", "dest", "speeds", "deadline", "arrival_radius", "waypoints", "par_wait", "naive_fails", "fair_ok")


def is_two(chart):
    return isinstance(chart, dict) and isinstance(chart.get("ship2"), dict)


def ship_chart(chart, index):
    """The chart as one ship sees it: Ship A is the chart itself, Ship B a copy with its own start, flag, speeds and deadline."""
    if index == 0 or not is_two(chart):
        return chart
    out = dict(chart)
    own = out.pop("ship2")
    out["id"] = chart["id"] + "~B"
    for key in SHIP_KEYS:
        if key in own:
            out[key] = own[key]
    return out


def ships(chart):
    return [ship_chart(chart, i) for i in range(2 if is_two(chart) else 1)]


def ship_seed(seed, index):
    return seed + SEED_STEP * index


def rule_text():
    return ("Keep the two ships at least %g nm apart while both are under way. A closer approach costs one star; it never ends the passage."
            % SEPARATION)


# --- the closest approach ----------------------------------------------------------------------
def _at(track, t):
    """A track's position at time t (linear between recorded points; held at its ends)."""
    prev = track[0]
    if t <= prev[0]:
        return (prev[1], prev[2])
    for cur in track[1:]:
        if t <= cur[0] + 1e-9:
            span = cur[0] - prev[0]
            f = 0.0 if span <= 1e-12 else (t - prev[0]) / span
            return (prev[1] + (cur[1] - prev[1]) * f, prev[2] + (cur[2] - prev[2]) * f)
        prev = cur
    return (prev[1], prev[2])


def closest_approach(track_a, track_b):
    """How near the two ships come while BOTH are under way (the common stretch of their clocks).

    Returns {dist, t, a, b, too_close, breach_t, overlap}: the smallest separation (0.01 nm), the hour it happens, the two positions
    then, whether it is under SEPARATION, and the first hour the ships were under SEPARATION (None when they never were).
    Each track is [[t, x, y, ...], ...]; the true tracks, or the player's two plots (which is how the planner warns in advance)."""
    end = min(track_a[-1][0], track_b[-1][0])
    times = sorted({round(p[0], 6) for p in list(track_a) + list(track_b) if p[0] <= end + 1e-9} | {round(end, 6)})
    best = None            # (distance, t)
    breach = None
    prev = None
    for t in times:
        pa, pb = _at(track_a, t), _at(track_b, t)
        rel = (pb[0] - pa[0], pb[1] - pa[1])
        if prev is not None:
            t0, r0 = prev
            dv = (rel[0] - r0[0], rel[1] - r0[1])
            a = dv[0] * dv[0] + dv[1] * dv[1]
            s = 0.0 if a < 1e-12 else max(0.0, min(1.0, -(r0[0] * dv[0] + r0[1] * dv[1]) / a))
            d = math.hypot(r0[0] + dv[0] * s, r0[1] + dv[1] * s)
            if best is None or d < best[0] - 1e-9:
                best = (d, t0 + s * (t - t0))
            if breach is None and d < SEPARATION:
                if math.hypot(r0[0], r0[1]) < SEPARATION:
                    breach = t0
                else:
                    b = r0[0] * dv[0] + r0[1] * dv[1]
                    c = r0[0] * r0[0] + r0[1] * r0[1] - SEPARATION * SEPARATION
                    disc = b * b - a * c
                    root = (-b - math.sqrt(disc)) / a if a >= 1e-12 and disc >= 0 else s
                    breach = t0 + max(0.0, min(1.0, root)) * (t - t0)
        else:
            d0 = math.hypot(rel[0], rel[1])
            best = (d0, t)
            if d0 < SEPARATION:
                breach = t
        prev = (t, rel)
    d, t = best
    pa, pb = _at(track_a, t), _at(track_b, t)
    shown = round(d, 2)
    too_close = shown < SEPARATION
    if too_close and breach is None:
        breach = t
    return {"dist": shown, "t": sim.rnd(t), "a": [sim.rnd(pa[0]), sim.rnd(pa[1])], "b": [sim.rnd(pb[0]), sim.rnd(pb[1])],
            "too_close": too_close, "breach_t": sim.rnd(breach) if too_close else None, "overlap": sim.rnd(end)}


# --- sailing both ships --------------------------------------------------------------------------
def sail_fleet(chart, legs_a, legs_b, seed=0, known=()):
    """Sail both plans. Returns a result that reads like sim.sail's for the parts the engine shares (close, aground, events, hours) plus
    `ships` (each ship's own sim.sail result), `approach` (see closest_approach) and `groundings` (every grounding, either ship)."""
    chart_a, chart_b = ship_chart(chart, 0), ship_chart(chart, 1)
    res_a = sim.sail(chart_a, legs_a, seed=seed, known=known)
    res_b = sim.sail(chart_b, legs_b, seed=ship_seed(seed, 1), known=known)
    approach = closest_approach(res_a["track"], res_b["track"])
    events = []
    for i, res in enumerate((res_a, res_b)):
        for e in res["events"]:
            events.append(dict(e, ship=i, text="Ship %s: %s" % (TAGS[i], e["text"])))
    if approach["too_close"]:
        events.append({"t": approach["breach_t"], "kind": "apart", "public": True, "ship": None, "text":
                       "Hour %s: the ships were closer than %g nm to each other (the closest was %.1f nm, at hour %s)."
                       % (sim._fmt_hour(approach["breach_t"]), SEPARATION, approach["dist"], sim._fmt_hour(approach["t"]))})
    events.sort(key=lambda e: e["t"])
    close = list(res_a["close"]) + [h for h in res_b["close"] if h not in res_a["close"]]
    groundings = [g for g in (res_a["aground"], res_b["aground"]) if g]
    tides = [r["tide_fair"] for r in (res_a, res_b) if r["tide_fair"] is not None]
    return {"ships": [res_a, res_b], "approach": approach, "events": events, "close": close, "groundings": groundings,
            "aground": min(groundings, key=lambda g: g["t"]) if groundings else None,
            "hours": max(res_a["hours"], res_b["hours"]), "end": res_a["end"], "tide_fair": min(tides) if tides else None}


def score_fleet(chart, legs_a, legs_b, result, known=(), used_helpers=False):
    """Judge a finished two-ship passage: each ship by the usual rules (the criteria are listed per ship, never a bare number), then the
    separation rule. Fleet stars = the lower of the two ships' stars, less one if the ships came too close (but never below the first
    star while both made landfall)."""
    chart_a, chart_b = ship_chart(chart, 0), ship_chart(chart, 1)
    sa = sim.score(chart_a, legs_a, result["ships"][0], known=known, used_helpers=used_helpers)
    sb = sim.score(chart_b, legs_b, result["ships"][1], known=known, used_helpers=used_helpers)
    ap = result["approach"]
    base = min(sa["stars"], sb["stars"])
    stars = base - 1 if (ap["too_close"] and base > 1) else base
    criteria = []
    for tag, s in zip(TAGS, (sa, sb)):
        for c in s["criteria"]:
            criteria.append({"id": "%s-%s" % (c["id"], tag.lower()), "ok": c["ok"], "text": "Ship %s - %s" % (tag, c["text"])})
    if ap["too_close"]:
        text = ("Apart: the ships came within %.1f nm of each other at hour %s, inside the %g nm rule. That costs one star."
                % (ap["dist"], sim._fmt_hour(ap["breach_t"]), SEPARATION))
    else:
        text = "Apart: the ships stayed at least %.1f nm apart (the rule is %g nm)." % (ap["dist"], SEPARATION)
    criteria.append({"id": "apart", "ok": not ap["too_close"], "text": text})
    beats = [s["beat_naive_pct"] for s in (sa, sb) if s["beat_naive_pct"] is not None]
    forecasts = [s["forecast_error_nm"] for s in (sa, sb)]
    tides = [s["tide_fair"] for s in (sa, sb) if s["tide_fair"] is not None]
    return {"arrived": sa["arrived"] and sb["arrived"], "miss_nm": max(sa["miss_nm"], sb["miss_nm"]),
            "aground": sa["aground"] or sb["aground"], "hours": max(sa["hours"], sb["hours"]),
            "late_h": max(sa["late_h"], sb["late_h"]), "on_time": sa["on_time"] and sb["on_time"], "clear": sa["clear"] and sb["clear"],
            "precise": sa["precise"] and sb["precise"], "apart": not ap["too_close"], "stars": stars, "criteria": criteria,
            "naive_miss_nm": max(sa["naive_miss_nm"], sb["naive_miss_nm"]), "beat_naive_pct": min(beats) if beats else None,
            "forecast_error_nm": None if None in forecasts else max(forecasts), "used_helpers": bool(used_helpers),
            "tide_fair": min(tides) if tides else None, "ships": [sa, sb], "approach": ap}
