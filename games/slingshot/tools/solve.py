#!/usr/bin/env python3
"""Slingshot -- dev tool: find the reference plan of every mission with the real engine and write refplans.py.

Usage:  python3 tools/solve.py [mission-id ...] [--write]
Without --write it prints what it found (plan, fuel, how many neighbouring plans also succeed). With --write it merges the answers into
refplans.py (GENERATED; the tests fly every plan in it). Nothing is random: scans are grids and the minimiser is Nelder-Mead.

Each plan is found by the same steps a player would take, with the engine as judge:
  1. scan the first burn over a window of start times and strengths until the path reaches the target body's sphere of influence;
  2. fix the aim (course-correction burn) until the closest approach sits in the middle of what the goal allows;
  3. choose the closest-approach burn that leaves the orbit the goal asks for (closed form from the pass);
  4. round everything to the grid a player can type (heading 0.1 degree, strength 1 m/s) and fly it again.
Then robust_fraction() flies the plan's neighbours (each number one grid step either side) and reports how many still succeed, which the tests
use to show that the answer is a region and not a needle.
"""

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import orbit  # noqa: E402
import solvelib as S  # noqa: E402
import missions  # noqa: E402

AU = S.AU


def setup(mid):
    m = missions.BY_ID[mid]
    return m, orbit.make_scene(m["scene"]), m["goal"]


def ok(scene, goal, plan, budget=1e9):
    r = orbit.fly(scene, plan, goal, record=False)
    return orbit.judge(r, budget) == "success", r


def neighbours(plan):
    """The plans one grid step away from `plan` in a single number: a burn's step +-1 (timed burns), its strength +-0.001 km/s, its heading
    +-0.1 degree, a closest-approach burn +-0.001 km/s. When a plan has several burns the first (the departure) is left alone: the later burns are
    the fine aim, and the departure is only the coarse one."""
    variants = []
    for i, b in enumerate(plan["burns"]):
        if i == 0 and len(plan["burns"]) > 1:
            continue
        for key, delta in (("t", -1), ("t", 1), ("dv", -0.001), ("dv", 0.001), ("head", -0.1), ("head", 0.1)):
            if key == "t" and b.get("at", "time") != "time":
                continue
            nb = [dict(x) for x in plan["burns"]]
            nb[i][key] = round(nb[i][key] + delta, 3) if key != "t" else nb[i][key] + delta
            if nb[i]["dv"] < 0:
                continue
            variants.append({"burns": nb, "pass": dict(plan.get("pass", {}))})
    for cid, v in plan.get("pass", {}).items():
        for delta in (-0.001, 0.001):
            p = dict(plan["pass"])
            p[cid] = round(v + delta, 3)
            variants.append({"burns": [dict(x) for x in plan["burns"]], "pass": p})
    return variants


def robust_fraction(scene, goal, plan, budget=1e9):
    """Fly every neighbour of a plan (see neighbours). Returns (successes, tries)."""
    wins = tries = 0
    variants = neighbours(plan)
    for v in variants:
        tries += 1
        good, _ = ok(scene, goal, v, budget)
        wins += 1 if good else 0
    return wins, tries




# ---- building blocks -----------------------------------------------------------------------------------------------------------
def first_pass(scene, plan, child, index=0):
    """Fly the plan up to its first pass of `child` and return that pass (or None) -- the pass dict from orbit.pass_through."""
    goal = {"kind": "flyby", "body": child, "within": 1e15, "min": 0.0}
    r = orbit.fly(scene, plan, goal, record=False)
    found = [p for p in r["passes"] if p["child"] == child]
    return (found[index] if len(found) > index else None), r


def pass_with_exit(scene, plan, child):
    """Like first_pass but the flight goes on past the pass (so the pass has its exit step k_out)."""
    goal = {"kind": "flyby", "body": child, "within": 1.0, "min": 0.0}
    r = orbit.fly(scene, plan, goal, record=False)
    found = [p for p in r["passes"] if p["child"] == child]
    return (found[0] if found else None), r


def bracket_roots(fun, lo, hi, n, refine=36):
    """x values in [lo, hi] where fun changes sign between neighbouring scan points (fun returns None where it is not defined)."""
    out = []
    prev = None
    for i in range(n + 1):
        x = lo + (hi - lo) * i / n
        f = fun(x)
        if f is None:
            prev = None
            continue
        if prev is not None and (prev[1] > 0) != (f > 0) and abs(f - prev[1]) < 1e30:
            a, fa, b = prev[0], prev[1], x
            good = True
            for _ in range(refine):
                mid = 0.5 * (a + b)
                fm = fun(mid)
                if fm is None:
                    good = False
                    break
                if (fm > 0) == (fa > 0):
                    a, fa = mid, fm
                else:
                    b = mid
            if good:
                out.append(0.5 * (a + b))
        prev = (x, f)
    return out


def rp_fun(scene, base, child, target, extra_burn=None, sense=None, vary="dv0"):
    """A function of one number returning (closest approach of `child` - target), or None when the plan does not reach it properly."""
    def fun(x):
        plan = {"burns": [dict(b) for b in base["burns"]], "pass": {}}
        if vary == "dv0":
            plan["burns"][0]["dv"] = x
        else:
            eb = dict(extra_burn)
            eb["dv"] = x
            plan["burns"].append(eb)
        p, _ = first_pass(scene, plan, child)
        if p is None or p.get("impact") or (sense is not None and p["sense"] != sense):
            return None
        return p["rp"] - target
    return fun


def tcm_options(scene, base, child, t_tcm, target_rp, sense=None, heads=(90.0, -90.0, 0.0, 180.0), dv_max=0.08, n=80):
    """Small course-correction burns at step t_tcm that put the closest approach of `child` at target_rp: [(dv, head), ...] sorted by strength."""
    found = []
    for head in heads:
        eb = S.burn(t_tcm, head, 0.0)
        fun = rp_fun(scene, base, child, target_rp, extra_burn=eb, sense=sense, vary="tcm")
        for dv in bracket_roots(fun, 0.0005, dv_max, n):
            found.append((round(dv, 3), head))
    found.sort()
    return found


def with_pass_burn(scene, goal, plan, child, mu, big_q):
    """Add the closest-approach burn that leaves an orbit with its high point at big_q (closed form from the pass the plan makes)."""
    p, _ = first_pass(scene, plan, child)
    if p is None or p.get("impact"):
        return None
    out = {"burns": [dict(b) for b in plan["burns"]], "pass": dict(plan.get("pass", {}))}
    out["pass"][child] = round(S.capture_dv(mu, p["rp"], p["vp"], big_q), 3)
    return S.snap(out)


# ---- chapter 1: Earth and the Moon -----------------------------------------------------------------------------------------------
def solve_c1(mid, window=(0, 480), stride=6, limit=12, max_k_in=1800):
    """Departure scan, then an aim burn half-way, then the closest-approach burn. Returns [(fuel, plan), ...] sorted by fuel."""
    m, scene, goal = setup(mid)
    mu = scene["by_id"]["moon"]["gm"]
    kind = goal["kind"]
    sense = -1 if goal.get("sense") == "retro" else (1 if goal.get("sense") == "pro" else None)
    if kind == "flyby":
        lo, hi = goal.get("min", 1900.0), goal["within"]
        target = (lo + hi) / 2.0 if "min" in goal else goal["within"] * 0.6
    else:
        lo, hi = goal["q"]
        target = (lo + hi) / 2.0 if hi < 3.0 * lo else lo + 0.3 * (hi - lo)
    aim_first = 30000.0 if hi - lo < 4000.0 or sense is not None else None
    r0 = m["scene"]["start"]["orbit"]["r"]
    d1 = orbit.hohmann(scene["central"]["gm"], r0, scene["by_id"]["moon"]["a"])[0]
    dv_lo, dv_hi = d1 - 0.06, d1 + 0.12
    out = []
    for t0 in range(window[0], window[1], stride):
        t_aim = aim_first if aim_first is not None else target
        fun = lambda dv, t0=t0: _first_rp(scene, t0, dv, t_aim)
        for dv0 in bracket_roots(fun, dv_lo, dv_hi, 40):
            base = {"burns": [S.burn(t0, 0.0, dv0)], "pass": {}}
            options = [(None, None)]
            if aim_first is not None:
                options = tcm_options(scene, base, "moon", t0 + 600, target, sense)[:3]
            for opt in options:
                plan = {"burns": [dict(b) for b in base["burns"]], "pass": {}}
                if opt != (None, None):
                    plan["burns"].append(S.burn(t0 + 600, opt[1], opt[0]))
                if kind == "capture":
                    plan = with_pass_burn(scene, goal, plan, "moon", mu, goal["big_q"] * 0.7)
                    if plan is None:
                        continue
                plan = S.snap(plan)
                good, r = ok(scene, goal, plan)
                if good:
                    out.append((r["fuel"], plan))
        if len(out) > 400:
            break
    out.sort(key=lambda a: (round(a[0], 3), a[1]["burns"][0]["t"]))
    return out


def moon_pass(scene, t, dv, head=0.0):
    plan = {"burns": [S.burn(t, head, dv)], "pass": {}}
    p, r = first_pass(scene, plan, "moon")
    return p, r


def _first_rp(scene, t, dv, target):
    p, _ = moon_pass(scene, t, dv)
    if p is None or p.get("impact"):
        return None
    return p["rp"] - target


def solve_c1m7():
    m, scene, goal = setup("c1m7")
    best = []
    for t in range(0, 288, 2):
        for i in range(0, 41):
            dv = 1.08 + 0.00225 * i
            plan = S.snap({"burns": [S.burn(t, 0.0, dv)], "pass": {}})
            r = orbit.fly(scene, plan, goal, record=False)
            if r["ended"] == "success":
                best.append((r["fuel"], plan))
    best.sort(key=lambda a: (a[0], a[1]["burns"][0]["t"]))
    return best


# ---- chapter 2/3: planets, seen from the Sun ------------------------------------------------------------------------------------------
GUESS = {"mars": (0.0, 2.94, (2.88, 3.10)), "venus": (180.0, 2.5, (2.35, 2.85))}


def band_target(goal):
    """Where inside what the goal allows to aim: the middle of a flyby band, or a quarter of the way up a capture band."""
    if goal["kind"] == "flyby":
        return (goal["min"] + goal["within"]) / 2.0 if "min" in goal else goal["within"] * 0.5
    lo, hi = goal["q"]
    return (lo + hi) / 2.0 if hi < 3.0 * lo else lo + 0.3 * (hi - lo)


def window_candidates(scene, body, head, dv, t_hi, stride=4, near=4.0e6):
    """Start steps (a coarse scan) at which a burn of strength dv puts the probe within `near` km of the body."""
    goal = {"kind": "flyby", "body": body, "within": 1e15, "min": 0.0}
    out = []
    for t0 in range(0, t_hi, stride):
        r = orbit.fly(scene, {"burns": [S.burn(t0, head, dv)], "pass": {}}, goal, record=False)
        c = r["closest"].get(body)
        if c and c["dist"] < near:
            out.append((c["dist"], t0))
    return out


def solve_sun(mid, t_hi=None, tcm_lead=48, max_windows=6):
    m, scene, goal = setup(mid)
    kind = goal["kind"]
    if kind == "reach":
        return solve_reach(mid)
    body = goal["body"]
    head0, dv_guess, (dlo, dhi) = GUESS[body]
    mu = scene["by_id"][body]["gm"]
    if "by" in goal:
        dlo, dhi = dv_guess + 0.45, dv_guess + 2.8
    target = band_target(goal)
    t_hi = t_hi or (scene["steps"] - 1200)
    cands = window_candidates(scene, body, head0, dv_guess if "by" not in goal else dv_guess + 0.9, t_hi, stride=4 if t_hi < 700 else 8)
    cands.sort()
    out = []
    aim0 = min(250000.0, max(40000.0, target * 2.0)) if goal["kind"] == "capture" or goal.get("min") else goal["within"] * 0.4
    for _, t0 in cands[:(10 if 'by' in goal else max_windows * 6)]:
        for fine in (-2, 0, 2):
            t = t0 + fine
            if t < 0:
                continue
            fun = lambda dv, t=t: _sun_rp(scene, body, head0, t, dv, aim0)
            for dv0 in bracket_roots(fun, dlo, dhi, 260 if "by" not in goal else 900):
                base = {"burns": [S.burn(t, head0, dv0)], "pass": {}}
                p, r = first_pass(scene, base, body)
                if p is None:
                    continue
                options = [(None, None)]
                if kind == "capture" or goal.get("min"):
                    k_in = p["k_in"]
                    options = tcm_options(scene, base, body, max(t + 1, k_in - tcm_lead), target, None, dv_max=0.15, n=100)[:2]
                for opt in options:
                    plan = {"burns": [dict(b) for b in base["burns"]], "pass": {}}
                    if opt != (None, None):
                        plan["burns"].append(S.burn(max(t + 1, p["k_in"] - tcm_lead), opt[1], opt[0]))
                    if kind == "capture":
                        plan = with_pass_burn(scene, goal, plan, body, mu, goal["big_q"] * 0.7)
                        if plan is None:
                            continue
                    plan = S.snap(plan)
                    good, rr = ok(scene, goal, plan)
                    if good:
                        out.append((rr["fuel"], plan))
        if len(out) >= (10 if 'by' in goal else 60):
            break
    out.sort(key=lambda a: (round(a[0], 3), a[1]["burns"][0]["t"]))
    return out


def _sun_rp(scene, body, head, t, dv, target):
    p, _ = first_pass(scene, {"burns": [S.burn(t, head, dv)], "pass": {}}, body)
    if p is None or p.get("impact"):
        return None
    return p["rp"] - target


def solve_reach(mid, margin=0.96):
    """Venus pass, then maybe one backward burn at the high point of the new orbit (anchored: the first apoapsis after the pass). The departure puts the
    probe near Venus, a small aim burn sets the closest approach (the lower, the bigger the bend), and the result must beat the goal radius by a margin."""
    m, scene, goal = setup(mid)
    R = goal["radius"]
    goal_m = dict(goal, radius=margin * R)           # the flight stops at the first success, so the margin is asked of the goal itself
    head0, dv_guess, (dlo, dhi) = GUESS["venus"]
    cands = window_candidates(scene, "venus", head0, dv_guess, scene["steps"] - 1000, stride=4, near=4.0e6)
    cands.sort()
    out = []
    for _, t0 in cands[:8]:
        fun = lambda dv, t=t0: _sun_rp(scene, "venus", head0, t, dv, 40000.0)
        for dv0 in bracket_roots(fun, dlo, dhi, 300)[:2]:
            base = {"burns": [S.burn(t0, head0, dv0)], "pass": {}}
            p0, _ = first_pass(scene, base, "venus")
            if p0 is None:
                continue
            t_tcm = max(t0 + 1, p0["k_in"] - 48)
            for target_rp in (7000.0, 8000.0, 9500.0, 12000.0):
                for dv_t, head_t in tcm_options(scene, base, "venus", t_tcm, target_rp, None, dv_max=0.15, n=100)[:2]:
                    plan1 = S.snap({"burns": [dict(base["burns"][0]), S.burn(t_tcm, head_t, dv_t)], "pass": {}})
                    p, r = pass_with_exit(scene, plan1, "venus")
                    if p is None or p.get("impact"):
                        continue
                    full = orbit.fly(scene, plan1, goal_m, record=False)
                    if full["ended"] == "success":
                        out.append((full["fuel"], plan1))
                        continue
                    k_out = p.get("k_out") or 0
                    for i in range(1, 160):
                        dv2 = 0.02 * i
                        plan2 = {"burns": [dict(b) for b in plan1["burns"]] + [S.burn(k_out + 1, 180.0, dv2, at="apo")], "pass": {}}
                        rr = orbit.fly(scene, plan2, goal_m, record=False)
                        if rr["ended"] == "success":
                            lo, hi = dv2 - 0.02, dv2
                            for _ in range(12):
                                mid_ = 0.5 * (lo + hi)
                                pm = {"burns": [dict(b) for b in plan1["burns"]] + [S.burn(k_out + 1, 180.0, mid_, at="apo")], "pass": {}}
                                r3 = orbit.fly(scene, S.snap(pm), goal_m, record=False)
                                if r3["ended"] == "success":
                                    hi = mid_
                                else:
                                    lo = mid_
                            final = S.snap({"burns": [dict(b) for b in plan1["burns"]] + [S.burn(k_out + 1, 180.0, hi + 0.001, at="apo")], "pass": {}})
                            good, r4 = ok(scene, goal, final)
                            if good:
                                out.append((r4["fuel"], final))
                            break
    out.sort(key=lambda a: (round(a[0], 3), a[1]["burns"][0]["t"]))
    return out


def solve_mars_moon(mid):
    """Two-burn transfer between circular orbits (the Hohmann pair, the second burn anchored at the far or near point), scanned over the first burn's moment."""
    m, scene, goal = setup(mid)
    mu = scene["central"]["gm"]
    child = goal["body"]
    c = scene["by_id"][child]
    r0 = m["scene"]["start"]["orbit"]["r"]
    d1, d2, half = orbit.hohmann(mu, r0, c["a"])
    outward = c["a"] > r0
    head = 0.0 if outward else 180.0
    anchor = "apo" if outward else "peri"
    out = []
    steps = scene["steps"]
    for t1 in range(0, steps - int(half / scene["dt"]) - 30):
        plan = {"burns": [S.burn(t1, head, abs(d1)), S.burn(t1 + 1, head, abs(d2), at=anchor)], "pass": {}}
        plan = S.snap(plan)
        good, r = ok(scene, goal, plan)
        if good:
            out.append((r["fuel"], plan))
    out.sort(key=lambda a: (round(a[0], 3), a[1]["burns"][0]["t"]))
    return out


def choose(results, spread_steps=100):
    """The cheapest plan, and the cheapest plan whose first burn is at least spread_steps away (a different window) and that still fits the budget."""
    primary = results[0]
    budget = S.budget_for(primary[0])
    alt = None
    for fuel, plan in results[1:]:
        if abs(plan["burns"][0]["t"] - primary[1]["burns"][0]["t"]) >= spread_steps and fuel <= budget - 0.02:
            alt = (fuel, plan)
            break
    return primary, alt


SOLVED = HERE / "solved"


def save(mid, results, spread_steps=100):
    """Write tools/solved/<mid>.json with the chosen reference plan (and a second, different plan when there is one)."""
    m, scene, goal = setup(mid)
    primary, alt = choose(results, spread_steps)
    w, n = robust_fraction(scene, goal, primary[1])
    entry = {"ref": primary[1], "cost": round(primary[0], 3), "budget": round(S.budget_for(primary[0]), 2), "robust": [w, n]}
    if alt:
        entry["alt"] = alt[1]
        entry["alt_cost"] = round(alt[0], 3)
    SOLVED.mkdir(exist_ok=True)
    (SOLVED / (mid + ".json")).write_text(json.dumps(entry, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("saved", mid, entry["cost"], entry["budget"], "robust", w, "/", n, "alt" if alt else "no alt")


def assemble():
    """Write refplans.py from every tools/solved/*.json."""
    plans = {}
    for path in sorted(SOLVED.glob("*.json")):
        plans[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    lines = ['"""Slingshot -- the reference plans, GENERATED by tools/solve.py from tools/solved/*.json (do not edit by hand).',
             "",
             "For each mission: ref (a plan that reaches the goal), cost (the fuel it spends, km/s), budget (cost plus a quarter, rounded up to 0.05) and, where",
             'the search found one, alt (a second plan with a different first burn). tests/test_missions.py flies every one in the real engine."""',
             "", "PLANS = {"]
    for mid in sorted(plans):
        e = plans[mid]
        item = {"ref": e["ref"], "cost": e["cost"], "budget": e["budget"]}
        if e.get("alt"):
            item["alt"] = e["alt"]
        lines.append("    %r: %r," % (mid, item))
    lines += ["}", ""]
    (HERE.parent / "refplans.py").write_text("\n".join(lines), encoding="utf-8")
    print("wrote refplans.py with", len(plans), "missions")


def report(mid, results, limit=4):
    m, scene, goal = setup(mid)
    print("==", mid, m["name"], "-", len(results), "plans")
    shown = 0
    for fuel, plan in results:
        w, n = robust_fraction(scene, goal, plan)
        print("  fuel %.3f  robust %d/%d  %s" % (fuel, w, n, json.dumps(plan)))
        shown += 1
        if shown >= limit:
            break


def run_mission(mid):
    if mid == "c1m7":
        results = solve_c1m7()
    elif mid.startswith("c1"):
        results = solve_c1(mid)
    elif mid.startswith("c2m") and int(mid[3:]) >= 6:
        results = solve_mars_moon(mid)
    else:
        results = solve_sun(mid)
    if not results:
        print("NO PLAN for", mid)
        return
    report(mid, results)
    if "--save" in sys.argv:
        save(mid, results)


if __name__ == "__main__":
    if "--assemble" in sys.argv:
        assemble()
    for mid in [a for a in sys.argv[1:] if not a.startswith("--")]:
        run_mission(mid)
