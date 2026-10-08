"""Dead Reckoning -- the save contract: what is stored, and how a loaded blob is cleaned.

Nothing here knows about the simulation's truth. A save holds the plan (legs), the mode and a few counters; a passage is never
saved mid-sail, and the true track is always recomputed from (chart, legs, seed), so a loaded save and a played one cannot
disagree. Keys are only written when they differ from the default, and every field of a loaded blob is validated one by one:
one bad entry never costs the good ones.
"""

import math

from sim import clean_legs

SCHEMA = 1
MAX_LEGS = 12
MODES = ("plan", "watch")
PHASES = ("plan", "reveal")
HELPERS = ("naive", "current", "par")
# Irreversible facts that achievements are built from (achievements.py). Anything else in a loaded save is dropped.
FLAGS = ("landfall", "dead_on", "trusted", "around_rocks", "set_and_drift", "first_fix", "fog_clear", "riding_tide",
         "two_ships", "aground", "long_way")
LONG_WAY_NM = 60.0
CHART_ID_LIMIT = 80


def new_meta():
    return {"charts": {}, "practice_seeds_played": 0, "flags": [], "best": {"smallest_final_error_nm": None, "longest_route_nm": 0.0}}


def new_record():
    return {"best_error_nm": None, "stars": 0, "attempts": 0, "discovered": [], "par_seen": False, "trusted": False}


def _int(v, lo, hi, default=0):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return default
    return int(max(lo, min(hi, v)))


def _float(v, lo, hi, default=None):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return default
    return round(float(max(lo, min(hi, v))), 2)


def clean_record(data, hazard_ids=None):
    """A per-chart record from an untrusted blob. `hazard_ids` (when known) limits `discovered` to real hazards."""
    rec = new_record()
    if not isinstance(data, dict):
        return rec
    rec["best_error_nm"] = _float(data.get("best_error_nm"), 0.0, 1000.0, None)
    rec["stars"] = _int(data.get("stars"), 0, 3)
    rec["attempts"] = _int(data.get("attempts"), 0, 100000)
    found = data.get("discovered")
    if isinstance(found, list):
        ids = []
        for h in found[:50]:
            if isinstance(h, str) and h not in ids and (hazard_ids is None or h in hazard_ids):
                ids.append(h)
        rec["discovered"] = ids
    rec["par_seen"] = data.get("par_seen") is True
    rec["trusted"] = data.get("trusted") is True
    return rec


def clean_meta(data, known_charts):
    """`known_charts` maps chart id -> the set of its hazard ids; records for unknown charts are dropped."""
    meta = new_meta()
    if not isinstance(data, dict):
        return meta
    charts = data.get("charts")
    if isinstance(charts, dict):
        for cid, rec in list(charts.items())[:500]:
            if isinstance(cid, str) and cid in known_charts:
                meta["charts"][cid] = clean_record(rec, known_charts[cid])
    meta["practice_seeds_played"] = _int(data.get("practice_seeds_played"), 0, 1000000)
    flags = data.get("flags")
    if isinstance(flags, list):
        meta["flags"] = [f for f in FLAGS if f in flags]
    best = data.get("best")
    if isinstance(best, dict):
        meta["best"]["smallest_final_error_nm"] = _float(best.get("smallest_final_error_nm"), 0.0, 1000.0, None)
        meta["best"]["longest_route_nm"] = _float(best.get("longest_route_nm"), 0.0, 100000.0, 0.0)
    return meta


def merge_record(a, b):
    """The better of two records for one chart (commutative: the order of two saves never matters)."""
    out = new_record()
    errs = [e for e in (a["best_error_nm"], b["best_error_nm"]) if e is not None]
    out["best_error_nm"] = min(errs) if errs else None
    out["stars"] = max(a["stars"], b["stars"])
    out["attempts"] = max(a["attempts"], b["attempts"])
    out["discovered"] = sorted(set(a["discovered"]) | set(b["discovered"]))
    out["par_seen"] = a["par_seen"] or b["par_seen"]
    out["trusted"] = a["trusted"] or b["trusted"]
    return out


def merge_meta(a, b):
    out = new_meta()
    for cid in sorted(set(a["charts"]) | set(b["charts"])):
        if cid in a["charts"] and cid in b["charts"]:
            out["charts"][cid] = merge_record(a["charts"][cid], b["charts"][cid])
        else:
            out["charts"][cid] = dict((a["charts"].get(cid) or b["charts"][cid]))
    out["practice_seeds_played"] = max(a["practice_seeds_played"], b["practice_seeds_played"])
    out["flags"] = [f for f in FLAGS if f in a["flags"] or f in b["flags"]]
    errs = [e for e in (a["best"]["smallest_final_error_nm"], b["best"]["smallest_final_error_nm"]) if e is not None]
    out["best"]["smallest_final_error_nm"] = min(errs) if errs else None
    out["best"]["longest_route_nm"] = max(a["best"]["longest_route_nm"], b["best"]["longest_route_nm"])
    return out


def new_run(chart_id, seed=0, mode="plan"):
    return {"chart_id": chart_id, "seed": seed, "mode": mode, "legs": [], "phase": "plan", "allow": True, "helpers": []}


def clean_run(data, get_chart):
    """A run from an untrusted blob, or None. `get_chart(id)` returns a chart dict or None."""
    if not isinstance(data, dict):
        return None
    cid = data.get("chart_id")
    if not isinstance(cid, str) or len(cid) > CHART_ID_LIMIT:
        return None
    chart = get_chart(cid)
    if chart is None:
        return None
    mode = data.get("mode") if data.get("mode") in MODES else "plan"
    phase = data.get("phase") if data.get("phase") in PHASES else "plan"
    run = new_run(cid, _int(data.get("seed"), 0, 2 ** 31 - 1), mode)
    run["legs"] = clean_legs(chart, data.get("legs"), limit=MAX_LEGS)
    run["phase"] = phase if run["legs"] else "plan"
    run["allow"] = data.get("allow") is not False
    helpers = data.get("helpers")
    if isinstance(helpers, list):
        run["helpers"] = [h for h in HELPERS if h in helpers]
    known = data.get("known")
    if run["phase"] == "reveal" and isinstance(known, list):
        run["known"] = [k for k in known[:50] if isinstance(k, str) and len(k) <= CHART_ID_LIMIT]
    return run


def run_to_dict(run):
    """The run as stored: defaults left out."""
    out = {"chart_id": run["chart_id"], "legs": [dict(leg) for leg in run["legs"]]}
    if run["seed"]:
        out["seed"] = run["seed"]
    if run["mode"] != "plan":
        out["mode"] = run["mode"]
    if run["phase"] != "plan":
        out["phase"] = run["phase"]
    if not run["allow"]:
        out["allow"] = False
    if run["helpers"]:
        out["helpers"] = list(run["helpers"])
    if run.get("known"):
        out["known"] = list(run["known"])
    return out


def record_to_dict(rec):
    """A chart record as stored: only what differs from a fresh record."""
    default = new_record()
    return {k: v for k, v in rec.items() if v != default[k]}


def meta_to_dict(meta):
    out = {}
    charts = {cid: record_to_dict(rec) for cid, rec in meta["charts"].items()}
    if charts:
        out["charts"] = charts
    if meta["practice_seeds_played"]:
        out["practice_seeds_played"] = meta["practice_seeds_played"]
    if meta["flags"]:
        out["flags"] = list(meta["flags"])
    best = {}
    if meta["best"]["smallest_final_error_nm"] is not None:
        best["smallest_final_error_nm"] = meta["best"]["smallest_final_error_nm"]
    if meta["best"]["longest_route_nm"]:
        best["longest_route_nm"] = meta["best"]["longest_route_nm"]
    if best:
        out["best"] = best
    return out
