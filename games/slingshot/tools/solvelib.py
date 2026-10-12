"""Slingshot -- dev tool: small helpers for finding plans (never run by the game).

The reference plans that tests/ fly are found here with plain Python: a Nelder-Mead minimiser and a few scans over the real engine, so every
plan is checked by the same code the game uses. Nothing here is random: the scans are grids and the minimiser is deterministic.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import orbit  # noqa: E402

AU = 149597870.7


def nelder_mead(f, x0, steps, iters=200, tol=1e-10):
    """Minimise f over len(x0) numbers from x0, with an initial simplex of the given step sizes. Returns (x, f(x))."""
    n = len(x0)
    pts = [list(x0)]
    for i in range(n):
        p = list(x0)
        p[i] += steps[i]
        pts.append(p)
    vals = [f(p) for p in pts]
    for _ in range(iters):
        order = sorted(range(n + 1), key=lambda i: vals[i])
        pts = [pts[i] for i in order]
        vals = [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < tol:
            break
        cen = [sum(pts[i][j] for i in range(n)) / n for j in range(n)]
        worst = pts[-1]
        refl = [cen[j] + (cen[j] - worst[j]) for j in range(n)]
        fr = f(refl)
        if fr < vals[0]:
            exp = [cen[j] + 2.0 * (cen[j] - worst[j]) for j in range(n)]
            fe = f(exp)
            pts[-1], vals[-1] = (exp, fe) if fe < fr else (refl, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = refl, fr
        else:
            con = [cen[j] + 0.5 * (worst[j] - cen[j]) for j in range(n)] if fr >= vals[-1] else [cen[j] + 0.5 * (refl[j] - cen[j]) for j in range(n)]
            fc = f(con)
            if fc < min(fr, vals[-1]):
                pts[-1], vals[-1] = con, fc
            else:
                for i in range(1, n + 1):
                    pts[i] = [pts[0][j] + 0.5 * (pts[i][j] - pts[0][j]) for j in range(n)]
                    vals[i] = f(pts[i])
    best = min(range(n + 1), key=lambda i: vals[i])
    return pts[best], vals[best]


def burn(t, head, dv, at="time"):
    return {"t": int(t), "at": at, "head": round(head, 1), "dv": round(dv, 3)}


def snap(plan):
    """Round a plan to the grid a player can type: heading to 0.1 degree, strength to 1 m/s."""
    return {"burns": [{"t": int(b["t"]), "at": b.get("at", "time"), "head": round(b["head"], 1), "dv": round(b["dv"], 3)} for b in plan["burns"]],
            "pass": {k: round(v, 3) for k, v in plan.get("pass", {}).items() if round(v, 3)}}


def capture_dv(mu, rp, vp, big_q):
    """The closest-approach burn (negative) that leaves a bound orbit with its low point at rp and its high point at big_q."""
    vp2 = math.sqrt(2.0 * mu * (1.0 / rp - 1.0 / (rp + big_q)))
    return vp2 - vp


def run(scene, goal, plan, record=False):
    return orbit.fly(scene, plan, goal, record=record)


def budget_for(cost):
    """Reference cost plus a quarter, rounded up to 0.05 km/s."""
    return math.ceil(cost * 1.25 / 0.05 - 1e-9) * 0.05
