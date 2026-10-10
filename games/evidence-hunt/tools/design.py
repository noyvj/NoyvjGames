"""Authoring aid: given a skeleton for a case (house, truth, restless rooms, features, kit) find a sheet (pool) and an account that
make it fair and make the tools matter. Prints the pieces to paste into a chapter file.

    python3 tools/design.py            # design every skeleton in SPECS and print JSON
"""

import sys
import zlib
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import casework as cw  # noqa: E402
import lexicon as lx  # noqa: E402
import solver  # noqa: E402


def skeleton(spec, pool, accounts):
    return {"id": spec["id"], "title": "t", "layout": spec["layout"], "truth": spec["truth"], "pool": pool, "restless": spec["restless"],
            "kit": spec.get("kit", 3), "accounts": accounts, "features": spec.get("features", {}), "keepsake": spec.get("keepsake")}


def account_options(spec):
    """Candidate accounts: behaviours true of the truth, tied to a room when there are two presences."""
    truth = spec["truth"]
    opts = []
    for s, kind in enumerate(truth):
        room = spec["restless"][s][0] if len(truth) == 2 else None
        for b in sorted(lx.KIND_BEHAVIOURS[kind]):
            if b in ("fond", "roamer"):
                continue
            opts.append((b, room))
    return opts


def design(spec):
    n_acc = spec.get("accounts", 0)
    size = spec["pool"]
    others = [k for k in lx.KIND_IDS if k not in spec["truth"]]
    best = None
    opts = account_options(spec)
    if n_acc == 0:
        acc_sets = [()]
    elif len(spec["truth"]) == 2 and n_acc == 2:
        per = [[o for o in opts if o[1] == spec["restless"][s][0]] for s in range(2)]
        acc_sets = [(a, b) for a in per[0] for b in per[1]]
    else:
        acc_sets = list(combinations(opts, n_acc))
    want = spec.get("min_kit", 1)
    for acc in acc_sets:
        pools = list(combinations(others, size - len(spec["truth"])))
        pools.sort(key=lambda p: zlib.crc32((spec["id"] + "|".join(p) + str(acc)).encode()))
        for extra in pools:
            pool = tuple(spec["truth"]) + extra
            data = skeleton(spec, pool, acc)
            if solver.validate(data):
                continue
            case = cw.Case(data)
            info = solver.analyse(case)
            statics = max(len(c) for c in info["cands"])
            score = (abs(info["min_kit"] - want), 0 if statics >= 2 else 1)
            if score[0] == 0 and score[1] == 0:
                return pool, acc, info["min_kit"], [len(c) for c in info["cands"]]
            if best is None or score < best[0]:
                best = (score, pool, acc, info["min_kit"], [len(c) for c in info["cands"]])
    return (best[1], best[2], best[3], best[4]) if best else None
