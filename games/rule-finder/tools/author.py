"""Rule Finder -- authoring helper: pick starting examples for a rule and measure the case (a dev tool).

`choose` tries a fixed number of seeded draws of examples from the rule's accepted and rejected items and keeps the draw whose
par set is largest (a case worth playing), preferring draws that leave a SHORTER wrong rule alive (a decoy, the 2-4-6 trap) when the
hidden rule has more than one clause. A seeded `random.Random` is used here only to FIND examples: the answer is frozen into
the cases files, and the engine itself never uses randomness.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import finder  # noqa: E402
import lang  # noqa: E402


def friendly(kind):
    """Items worth showing as starting examples (everything else is still fine to test)."""
    dom = lang.domain(kind)
    if kind == lang.NUM:
        return {k for k in dom.items if 2 <= int(k) <= 98}
    if kind == lang.SHAPE:
        return {k for k in dom.items if len(k) <= 4}
    return {k for k in dom.items if 2 <= k.count("#") <= 7}


def _order(kind):
    dom = lang.domain(kind)
    return dom.index.__getitem__


def split(kind, rule, pool=None):
    dom = lang.domain(kind)
    table = lang.rule_table(kind, lang.parse_rule(kind, rule))
    pool = pool if pool is not None else friendly(kind)
    yes = [k for i, k in enumerate(dom.items) if table >> i & 1 and k in pool]
    no = [k for i, k in enumerate(dom.items) if not table >> i & 1 and k in pool]
    return yes, no


def measure(kind, rule, size, yes, no):
    case = {"domain": kind, "rule": rule, "size": size, "yes": list(yes), "no": list(no)}
    out = finder.analyse(case)
    dom = lang.domain(kind)
    decoys = 0
    if size > 1:
        decoys = len(finder.competitors(kind, out["table"], size - 1, yes, no))
    out["decoys"] = decoys
    out["order"] = sorted(out["par"], key=lambda k: dom.index[k])
    return out


def choose(kind, rule, size, ny, nn, tries=150, pool=None, want_decoy=None, par_cap=99, par_floor=0):
    """Best of `tries` seeded draws. Returns (measure dict, yes, no)."""
    ys, ns = split(kind, rule, pool)
    if len(ys) < ny or len(ns) < nn:
        ys, ns = split(kind, rule, set(lang.domain(kind).items))
    if want_decoy is None:
        want_decoy = size > 1
    best = None
    for seed in range(tries):
        rnd = random.Random(seed * 7919 + len(rule))
        yes, no = sorted(rnd.sample(ys, ny), key=_order(kind)), sorted(rnd.sample(ns, nn), key=_order(kind))
        m = measure(kind, rule, size, yes, no)
        if not m["examples_consistent"] or not m["competitors"] or len(m["par"]) < par_floor:
            continue
        score = (1 if (m["decoys"] > 0 or not want_decoy) else 0, min(len(m["par"]), par_cap), m["competitors"], seed)
        if best is None or score > best[0]:
            best = (score, m, yes, no)
    if best is None:
        return None
    return best[1], best[2], best[3]
