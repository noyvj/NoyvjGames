"""Slingshot -- the flight engine: a fixed-step integrator inside one body's gravity, and patched-conic passes through the spheres of influence.

How a flight works (the rules the About page tells in plain words):

* A SCENE has one central body (the Sun, Earth or Mars, say) and a few bodies that orbit it on circles. The probe is a point that feels the
  central body's gravity only, integrated with the velocity-Verlet (leapfrog) method at a FIXED time step: no random numbers, no clock, no
  adaptive step, so the same plan always gives the same path to the last digit. Stated tolerances (tests/test_orbit.py): a circular orbit
  keeps its radius to 5e-4 over a whole orbit, the energy of a free-flying probe drifts by less than 5e-5 of its size over a year, and a
  planet's period matches its source to 0.3 percent.
* Burns are instant. A burn is (when, direction, strength): when is a step number (optionally "at the next periapsis/apoapsis after step n"),
  direction is an angle from the probe's own velocity (0 = straight ahead, 180 = backwards, 90 = to the left), strength in km/s.
* When the probe comes inside a body's sphere of influence (SOI) it stops being integrated and the pass is solved exactly as a conic around
  that body (patched conics): the exit is the mirror image of the entry about the closest approach, which is how a gravity assist bends
  a path and changes the probe's speed around the central body. The plan may carry one "closest-approach burn" per body: a burn along the
  velocity at the closest approach (negative = slow down) that can turn a flyby into a capture or a stronger assist.
* A body too small to have a real sphere of influence (Phobos, Deimos) is reached by RENDEZVOUS: come within a stated distance at a
  stated relative speed.
"""

import math

import bodies

TWO_PI = 2.0 * math.pi
MAX_BURNS = 8
_SCENES = {}


# ---- conic helpers -------------------------------------------------------------------------------------------------
def elements(mu, x, y, vx, vy):
    """Orbital elements of the two-body orbit through a state: h (signed angular momentum), e, p, the periapsis direction angle phi."""
    r = math.hypot(x, y)
    v2 = vx * vx + vy * vy
    h = x * vy - y * vx
    rv = x * vx + y * vy
    ex = ((v2 - mu / r) * x - rv * vx) / mu
    ey = ((v2 - mu / r) * y - rv * vy) / mu
    e = math.hypot(ex, ey)
    return {"r": r, "h": h, "e": e, "p": h * h / mu, "phi": math.atan2(ey, ex) if e > 1e-12 else math.atan2(y, x),
            "rv": rv, "energy": v2 / 2.0 - mu / r}


def time_since_periapsis(mu, p, e, nu):
    """Seconds from periapsis to true anomaly nu (negative before periapsis) on an ellipse or hyperbola."""
    if e < 1.0:
        big_e = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0), math.sqrt(1.0 + e) * math.cos(nu / 2.0))
        a = p / (1.0 - e * e)
        return (big_e - e * math.sin(big_e)) * math.sqrt(a ** 3 / mu)
    f = 2.0 * math.atanh(math.sqrt((e - 1.0) / (e + 1.0)) * math.tan(nu / 2.0))
    a = p / (e * e - 1.0)
    return (e * math.sinh(f) - f) * math.sqrt(a ** 3 / mu)


def state_at(mu, p, e, h_abs, phi, sense, nu):
    """Position and velocity at true anomaly nu on the orbit with periapsis direction phi (sense +1 counter-clockwise, -1 clockwise)."""
    r = p / (1.0 + e * math.cos(nu))
    alpha = phi + sense * nu
    ca, sa = math.cos(alpha), math.sin(alpha)
    vr = mu / h_abs * e * math.sin(nu)
    vt = mu / h_abs * (1.0 + e * math.cos(nu))
    return (r * ca, r * sa, vr * ca - sense * vt * sa, vr * sa + sense * vt * ca)


def conic_points(mu, p, e, h_abs, phi, sense, nu_from, nu_to, count):
    """Points (x, y) along one conic from true anomaly nu_from to nu_to, relative to the body."""
    pts = []
    for i in range(count + 1):
        nu = nu_from + (nu_to - nu_from) * i / count
        s = state_at(mu, p, e, h_abs, phi, sense, nu)
        pts.append([round(s[0], 1), round(s[1], 1)])
    return pts


def pass_through(mu, radius, state, dv_pass, r_exit=None, want_arc=False):
    """The patched-conic pass of a body's sphere of influence, from an entry state relative to the body (x, y, vx, vy).

    Returns a dict. Always: rp (closest approach distance from the centre), vp (speed there before the burn), t_in (seconds from the entry to
    the closest approach), sense. Then one of: impact=True (the path or the burnt orbit touches the surface), captured=True (bound after the
    burn: q, big_q = lowest and highest distance, period) or the exit state (exit = (x, y, vx, vy) relative to the body, t_out, seconds from
    the closest approach to the exit). With want_arc a list of points (the close-up path) is added as arc."""
    x, y, vx, vy = state
    el = elements(mu, x, y, vx, vy)
    r_in = el["r"]
    r_exit = r_in if r_exit is None else r_exit
    e, p, h = el["e"], el["p"], el["h"]
    sense = 1 if h > 0 else -1
    h_abs = abs(h)
    out = {"sense": sense, "r_in": r_in, "e": e}
    if e < 1e-9 or h_abs < 1e-9:
        out.update({"impact": True, "rp": 0.0, "vp": 0.0, "t_in": 0.0})
        return out
    rp = p / (1.0 + e)
    vp = h_abs / rp
    cos_nu = max(-1.0, min(1.0, (p / r_in - 1.0) / e))
    nu_in = -math.acos(cos_nu) if el["rv"] < 0 else math.acos(cos_nu)
    t_in = -time_since_periapsis(mu, p, e, nu_in)               # seconds still to go before periapsis (0 if already past it)
    out.update({"rp": rp, "vp": vp, "t_in": max(0.0, t_in), "nu_in": nu_in, "phi": el["phi"],
                "v_inf": math.sqrt(2.0 * el["energy"]) if el["energy"] > 0 else 0.0})
    if rp <= radius:
        out["impact"] = True
        return out
    vp2 = vp + dv_pass
    out["vp_after"] = vp2
    if vp2 <= 0.0:
        out["impact"] = True
        return out
    h2 = rp * vp2
    energy2 = vp2 * vp2 / 2.0 - mu / rp
    arc = None
    if want_arc:
        arc = conic_points(mu, p, e, h_abs, el["phi"], sense, nu_in, 0.0, 16)
    if energy2 < 0.0:                                          # bound: the probe stays and goes round the body
        a2 = -mu / (2.0 * energy2)
        e2 = math.sqrt(max(0.0, 1.0 + 2.0 * energy2 * h2 * h2 / (mu * mu)))
        q, big_q = a2 * (1.0 - e2), a2 * (1.0 + e2)
        out.update({"captured": True, "q": q, "big_q": big_q, "a": a2, "e2": e2, "period": TWO_PI * math.sqrt(a2 ** 3 / mu), "energy_after": energy2})
        if q <= radius:
            out["impact"] = True
        if want_arc:
            p2 = h2 * h2 / mu
            if vp2 >= math.sqrt(mu / rp):
                arc += conic_points(mu, p2, e2, h2, el["phi"], sense, 0.0, TWO_PI, 48)
            else:
                arc += conic_points(mu, p2, e2, h2, el["phi"] + math.pi, sense, math.pi, math.pi + TWO_PI, 48)
            out["arc"] = arc
        return out
    p2 = h2 * h2 / mu
    e2 = math.sqrt(max(1.0, 1.0 + 2.0 * energy2 * h2 * h2 / (mu * mu)))
    cos_x = max(-1.0, min(1.0, (p2 / r_exit - 1.0) / e2))
    nu_x = math.acos(cos_x)
    out["t_out"] = time_since_periapsis(mu, p2, e2, nu_x)
    out["exit"] = state_at(mu, p2, e2, h2, el["phi"], sense, nu_x)
    out["e2"] = e2
    out["v_inf_after"] = math.sqrt(2.0 * energy2)
    out["turn_deg"] = math.degrees(2.0 * math.asin(min(1.0, 1.0 / e2)))
    if want_arc:
        out["arc"] = arc + conic_points(mu, p2, e2, h2, el["phi"], sense, 0.0, nu_x, 16)
    return out


def pass_satisfies(goal, res):
    """Does one pass of a body meet a flyby or capture goal?"""
    if res.get("impact") or goal.get("body") != res.get("child") or res.get("k_in", 0) > goal.get("by", 10 ** 9):
        return False
    kind = goal["kind"]
    if kind == "flyby":
        return goal.get("min", 0.0) <= res["rp"] <= goal["within"]
    if kind == "capture":
        if not res.get("captured"):
            return False
        if not (goal["q"][0] <= res["q"] <= goal["q"][1] and res["big_q"] <= goal["big_q"]):
            return False
        if goal.get("sense") == "retro":
            return res["sense"] == -1
        if goal.get("sense") == "pro":
            return res["sense"] == 1
        return True
    return False


def hohmann(mu, r1, r2):
    """(first burn, second burn, half-period seconds) of the two-burn transfer between circular orbits r1 and r2."""
    a = (r1 + r2) / 2.0
    v1 = math.sqrt(mu / r1)
    v2 = math.sqrt(mu / r2)
    vt1 = math.sqrt(mu * (2.0 / r1 - 1.0 / a))
    vt2 = math.sqrt(mu * (2.0 / r2 - 1.0 / a))
    return vt1 - v1, v2 - vt2, math.pi * math.sqrt(a ** 3 / mu)


# ---- scenes --------------------------------------------------------------------------------------------------------
def make_scene(spec):
    """Build (and cache) a scene from a mission's scene spec: the central body, the children with their precomputed positions per step, the start state."""
    key = repr(sorted((k, repr(v)) for k, v in spec.items()))
    cached = _SCENES.get(key)
    if cached is not None:
        return cached
    central = bodies.body(spec["central"])
    dt = float(spec["dt"])
    steps = int(spec["steps"])
    jd = None
    if spec.get("epoch"):
        jd = bodies.julian_date(*spec["epoch"])
    rendezvous = set(spec.get("rendezvous", ()))
    children = []
    for cid in spec["children"]:
        b = bodies.body(cid)
        if central["id"] == "sun":
            th0 = bodies.planet_angle(cid, jd)
        else:
            th0 = math.radians(spec["phases"][cid])
        direction = -1.0 if cid in spec.get("retrograde_bodies", ()) else 1.0
        n = b["n"] * direction
        cx = [0.0] * (steps + 2)
        cy = [0.0] * (steps + 2)
        a = b["a"]
        for k in range(steps + 2):
            ang = th0 + n * k * dt
            cx[k] = a * math.cos(ang)
            cy[k] = a * math.sin(ang)
        children.append({"id": cid, "gm": b["gm"], "radius": b["radius"], "a": a, "n": n, "th0": th0, "soi": None if cid in rendezvous else b["soi"],
                         "rendezvous": cid in rendezvous, "cx": cx, "cy": cy})
    start = spec["start"]
    if "orbit" in start:
        o = start["orbit"]
        th = math.radians(o.get("theta", 0.0))
        r0 = float(o["r"])
        v0 = math.sqrt(central["gm"] / r0) * (1.0 if o.get("dir", 1) >= 0 else -1.0)
        state = (r0 * math.cos(th), r0 * math.sin(th), -v0 * math.sin(th), v0 * math.cos(th))
        locked = ()
    else:
        c = [ch for ch in children if ch["id"] == start["comove"]][0]
        state = (c["cx"][0], c["cy"][0], -c["n"] * c["cy"][0], c["n"] * c["cx"][0])
        locked = (c["id"],)
    scene = {"central": central, "dt": dt, "steps": steps, "stride": int(spec.get("stride", 1)), "children": children, "start": state, "locked": locked,
             "by_id": {c["id"]: c for c in children}, "jd": jd, "spec": spec}
    _SCENES[key] = scene
    return scene


def child_state(scene, cid, k):
    c = scene["by_id"][cid]
    k = max(0, min(scene["steps"] + 1, k))
    x, y = c["cx"][k], c["cy"][k]
    return x, y, -c["n"] * y, c["n"] * x


def _rotate(ux, uy, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    return ux * ca - uy * sa, ux * sa + uy * ca


# ---- the flight ----------------------------------------------------------------------------------------------------
def fly(scene, plan, goal, record=True):
    """Fly a plan {"burns": [{"t", "at", "head", "dv"}], "pass": {child: dv}} against a goal and return everything the page and the tests need.

    "ended" says how the flight stopped: "success" (the goal was met), "crash" (the probe struck a body), "captured" (bound to a body but not
    in the orbit the goal asks for) or None (it ran to the end of the time the mission allows)."""
    central = scene["central"]
    mu = central["gm"]
    cr2 = central["radius"] ** 2
    dt = scene["dt"]
    steps = scene["steps"]
    stride = scene["stride"]
    children = scene["children"]
    x, y, vx, vy = scene["start"]
    locked = set(scene["locked"])
    burns = sorted(plan.get("burns", ())[:MAX_BURNS], key=lambda b: b["t"])
    pass_dv = plan.get("pass", {})
    goal_kind = goal["kind"]
    goal_body = goal.get("body")
    target = scene["by_id"].get(goal_body) if goal_body else None
    reach2 = goal.get("radius", 0.0) ** 2 if goal_kind == "reach" else 0.0
    outward = goal.get("dir") == "out"
    need_pass = goal.get("after")
    hdt = 0.5 * dt

    samples = []              # [k, x, y, speed, frame]: frame is None in the central frame, or a child's id during a pass
    events = []
    burns_done = []
    passes = []
    closest = {}
    fuel = 0.0
    nb = 0
    ev = None
    ended = None
    pass_count = {}
    r2 = x * x + y * y
    r3inv = 1.0 / (r2 * math.sqrt(r2))
    ax, ay = -mu * x * r3inv, -mu * y * r3inv
    rv_old = x * vx + y * vy
    k = 0
    if record:
        samples.append([0, x, y, math.hypot(vx, vy), None])
    tgt_d2 = None
    rmin2 = rmax2 = rpost_min2 = r2
    rpost_max2 = 0.0
    npass = 0
    rpost_min2 = 1e30
    while k < steps:
        # ---- burns due now
        while nb < len(burns):
            b = burns[nb]
            at = b.get("at", "time")
            if b["t"] > k or (at != "time" and ev != at):
                break
            speed = math.hypot(vx, vy)
            if speed > 0.0:
                ux, uy = _rotate(vx / speed, vy / speed, b["head"])
                vx += b["dv"] * ux
                vy += b["dv"] * uy
                fuel += abs(b["dv"])
                burns_done.append({"i": nb, "k": k, "x": x, "y": y, "head": b["head"], "dv": b["dv"], "at": at})
                events.append({"k": k, "kind": "burn", "i": nb})
            nb += 1
        ev = None
        # ---- one velocity-Verlet step
        px, py = x, y
        vhx, vhy = vx + hdt * ax, vy + hdt * ay
        x += dt * vhx
        y += dt * vhy
        r2 = x * x + y * y
        r3inv = 1.0 / (r2 * math.sqrt(r2))
        ax, ay = -mu * x * r3inv, -mu * y * r3inv
        vx, vy = vhx + hdt * ax, vhy + hdt * ay
        k += 1
        rv = x * vx + y * vy
        if rv_old < 0.0 <= rv:
            ev = "peri"
        elif rv_old > 0.0 >= rv:
            ev = "apo"
        rv_old = rv
        if r2 < rmin2:
            rmin2 = r2
        elif r2 > rmax2:
            rmax2 = r2
        if npass:
            if r2 < rpost_min2:
                rpost_min2 = r2
            if r2 > rpost_max2:
                rpost_max2 = r2
        # ---- the central body's surface
        if r2 < cr2:
            events.append({"k": k, "kind": "crash", "body": central["id"], "speed": math.hypot(vx, vy)})
            ended = "crash"
            break
        # ---- the children
        jumped = False
        for c in children:
            cid = c["id"]
            ck_x, ck_y = c["cx"][k], c["cy"][k]
            dx, dy = x - ck_x, y - ck_y
            d2 = dx * dx + dy * dy
            cvx, cvy = -c["n"] * ck_y, c["n"] * ck_x
            if target is c and cid not in locked and (tgt_d2 is None or d2 < tgt_d2) and (not need_pass or pass_count.get(need_pass)):
                tgt_d2 = d2
                closest[cid] = {"dist": math.sqrt(d2), "k": k, "speed": math.hypot(vx - cvx, vy - cvy)}
            if c["rendezvous"]:
                if goal_kind == "rendezvous" and goal_body == cid and d2 <= goal["radius"] ** 2:
                    relv = math.hypot(vx - cvx, vy - cvy)
                    if relv <= goal["speed"]:
                        events.append({"k": k, "kind": "rendezvous", "body": cid, "dist": math.sqrt(d2), "speed": relv})
                        ended = "success"
                        break
                continue
            soi = c["soi"]
            soi2 = soi * soi
            if cid in locked:
                if d2 >= soi2:
                    locked.discard(cid)
                continue
            entry = None
            if d2 < soi2:
                ex, ey, evx, evy = dx, dy, vx - cvx, vy - cvy
                if ex * evx + ey * evy < 0.0:
                    entry = (ex, ey, evx, evy)
            elif d2 < (soi + 25.0 * dt) ** 2:
                # a fast step can cross a small sphere between two samples: look at the straight piece of relative path
                sx, sy = px - c["cx"][k - 1], py - c["cy"][k - 1]
                ddx, ddy = dx - sx, dy - sy
                dd = ddx * ddx + ddy * ddy
                if dd > 0.0:
                    s = -(sx * ddx + sy * ddy) / dd
                    if 0.0 < s < 1.0:
                        mx, my = sx + s * ddx, sy + s * ddy
                        if mx * mx + my * my < soi2:
                            entry = (mx, my, vx - cvx, vy - cvy)
            if entry is None:
                continue
            res = pass_through(c["gm"], c["radius"], entry, pass_dv.get(cid, 0.0), math.hypot(entry[0], entry[1]), want_arc=record)
            res["child"] = cid
            res["k_in"] = k
            res["entry_dist"] = math.hypot(entry[0], entry[1])
            passes.append(res)
            npass += 1
            pass_count[cid] = pass_count.get(cid, 0) + 1
            used = abs(pass_dv.get(cid, 0.0)) if "vp_after" in res else 0.0
            fuel += used
            res["fuel"] = used
            if cid not in closest or res["rp"] < closest[cid]["dist"]:
                closest[cid] = {"dist": res["rp"], "k": k, "speed": res.get("vp")}
            events.append({"k": k, "kind": "pass", "body": cid, "i": len(passes) - 1})
            if res.get("impact"):
                ended = "crash"
                events.append({"k": k, "kind": "crash", "body": cid, "speed": res.get("vp", 0.0)})
                break
            if pass_satisfies(goal, res) and (not goal.get("after") or pass_count.get(goal["after"])):
                ended = "success"
                break
            if res.get("captured"):
                ended = "captured"
                break
            k_exit = min(steps, k + max(1, int(round((res["t_in"] + res["t_out"]) / dt))))
            res["k_out"] = k_exit
            if record:
                for kk in range(k + 1, k_exit + 1):
                    if kk % stride == 0:
                        samples.append([kk, c["cx"][kk], c["cy"][kk], math.hypot(vx, vy), cid])
            ox, oy, ovx, ovy = res["exit"]
            x = c["cx"][k_exit] + ox
            y = c["cy"][k_exit] + oy
            vx = ovx - c["n"] * c["cy"][k_exit]
            vy = ovy + c["n"] * c["cx"][k_exit]
            k = k_exit
            r2 = x * x + y * y
            r3inv = 1.0 / (r2 * math.sqrt(r2))
            ax, ay = -mu * x * r3inv, -mu * y * r3inv
            rv_old = x * vx + y * vy
            ev = None
            locked.add(cid)
            jumped = True
            break
        if ended is not None:
            if record:
                samples.append([k, x, y, math.hypot(vx, vy), None])
            break
        if jumped and r2 < cr2:
            events.append({"k": k, "kind": "crash", "body": central["id"], "speed": math.hypot(vx, vy)})
            ended = "crash"
            break
        if goal_kind == "reach" and (r2 >= reach2 if outward else r2 <= reach2) and k <= goal.get("by", 10 ** 9) and (not need_pass or pass_count.get(need_pass)):
            events.append({"k": k, "kind": "reach", "dist": math.sqrt(r2)})
            ended = "success"
            if record:
                samples.append([k, x, y, math.hypot(vx, vy), None])
            break
        if record and k % stride == 0:
            samples.append([k, x, y, math.hypot(vx, vy), None])
    return {"ended": ended, "k_end": k, "fuel": fuel, "burns_done": burns_done, "passes": passes, "events": events, "closest": closest,
            "samples": samples, "pass_count": pass_count, "final": (x, y, vx, vy), "unused_burns": len(burns) - nb,
            "r_min": math.sqrt(rmin2), "r_max": math.sqrt(rmax2), "r_min_post": math.sqrt(rpost_min2) if npass else None,
            "r_max_post": math.sqrt(rpost_max2) if npass else None}


def judge(result, budget):
    """The outcome of a flown plan: success, over_budget (the goal was met but the plan spends more than the budget), crash or miss."""
    ended = result["ended"]
    if ended == "success":
        return "over_budget" if result["fuel"] > budget + 1e-9 else "success"
    return "crash" if ended == "crash" else "miss"
