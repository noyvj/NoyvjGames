"""Slingshot -- the plan: a list of burns plus one optional closest-approach burn per body.

A plan is {"burns": [{"t", "at", "head", "dv"}, ...], "pass": {body: dv}}:
  t     the step the burn happens at (the unit depends on the mission: hours, minutes or days; the page converts)
  at    "time" (exactly at step t), "peri" or "apo" (at the first periapsis / apoapsis of the probe's path at or after step t)
  head  the direction, in degrees from the probe's own velocity: 0 straight ahead, 180 backwards, 90 left, -90 right (one decimal)
  dv    the strength in km/s, 0 or more (three decimals, i.e. whole metres per second)
  pass  per body: a burn along the velocity at the closest approach, in km/s, negative to slow down (three decimals)
Burns happen in order of t. The fuel a plan spends is the sum of every burn that actually happens plus the closest-approach burns that were used.
"""

MAX_BURNS = 8
AT_KINDS = ("time", "peri", "apo")
DV_MAX = 20.0


def _num(value, low, high, digits):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")) or not low <= value <= high:
        return None
    return round(value, digits)


def clean_burn(raw, steps):
    """One burn, checked field by field; None if it is not a burn."""
    if not isinstance(raw, dict):
        return None
    t = raw.get("t")
    if isinstance(t, bool) or not isinstance(t, (int, float)) or t != t or not 0 <= t <= steps:
        return None
    at = raw.get("at", "time")
    if at not in AT_KINDS:
        at = "time"
    head = _num(raw.get("head", 0.0), -180.0, 180.0, 1)
    dv = _num(raw.get("dv", 0.0), 0.0, DV_MAX, 3)
    if head is None or dv is None:
        return None
    return {"t": int(round(t)), "at": at, "head": head, "dv": dv}


def clean_plan(raw, steps, children=()):
    """A plan from untrusted data: only real burns, at most MAX_BURNS, only known bodies in pass, every number clamped or dropped."""
    raw = raw if isinstance(raw, dict) else {}
    burns = []
    for item in (raw.get("burns") if isinstance(raw.get("burns"), list) else [])[:MAX_BURNS]:
        b = clean_burn(item, steps)
        if b is not None:
            burns.append(b)
    passes = {}
    if isinstance(raw.get("pass"), dict):
        for cid, dv in raw["pass"].items():
            if cid in children:
                value = _num(dv, -DV_MAX, DV_MAX, 3)
                if value:
                    passes[cid] = value
    return {"burns": burns, "pass": passes}


def empty():
    return {"burns": [], "pass": {}}


def fuel_of(plan):
    """The most a plan can spend: every burn plus every closest-approach burn (the flight reports what was actually used)."""
    return round(sum(b["dv"] for b in plan["burns"]) + sum(abs(v) for v in plan["pass"].values()), 6)


def is_empty(plan):
    return not plan["burns"] and not plan["pass"]
