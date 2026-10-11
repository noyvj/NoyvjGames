"""Rule Finder -- the fairness prover (a dev tool; the page never loads it, the tests do).

For a case (a domain, a hidden rule and its starting examples) it answers, by exhaustive enumeration of the whole rule
language up to the hidden rule's size:

  * the hidden rule is as short as it can be: no shorter rule has the same table;
  * COMPETITORS: every other table (size <= the hidden size) that still agrees with the starting examples. A case is a game
    only if there is at least one;
  * a PAR TEST SET: a smallest list of items whose answers (with the examples) separate the hidden rule from every
    competitor. It is a hitting set over the competitors' difference masks, found greedy first, then improved by an exact
    search while that stays cheap.

A TABLE is the int described in lang.py; a competitor's DIFF is table ^ hidden, whose set bits are the items that would tell
the two apart. Nothing here reads a clock or a random source, and ties always go to the lowest item index.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lang  # noqa: E402

_CACHE = {}


def popcount(x):
    return bin(x).count("1")


def literals(kind):
    """[(table, (clause id, negated))] for every clause and its negation, one entry per distinct table."""
    dom = lang.domain(kind)
    seen, out = set(), []
    for cid in dom.clause_ids:
        t = dom.table(cid)
        for table, neg in ((t, 0), (dom.full ^ t, 1)):
            if table not in seen:
                seen.add(table)
                out.append((table, (cid, neg)))
    return out


def level_two(kind):
    """Every table made of exactly two literals: {table: Rule}. Cached per domain."""
    key = ("two", kind)
    if key not in _CACHE:
        lits = literals(kind)
        out = {}
        for i, (ta, la) in enumerate(lits):
            for tb, lb in lits[i:]:
                for op, table in (("and", ta & tb), ("or", ta | tb)):
                    if table not in out:
                        out[table] = lang.Rule((la, lb), (op,))
        _CACHE[key] = out
    return _CACHE[key]


def level_one(kind):
    key = ("one", kind)
    if key not in _CACHE:
        _CACHE[key] = {t: lang.Rule((lit,), ()) for t, lit in literals(kind)}
    return _CACHE[key]


def min_size(kind, table):
    """1, 2 or 3: the fewest clauses of any rule with this table. 3 means 'needs three (or cannot be written in three)'
    and is only trusted for tables that a three-clause rule really produces."""
    if table in level_one(kind):
        return 1
    if table in level_two(kind):
        return 2
    return 3


def competitors(kind, hidden, size, yes, no):
    """Every table of size <= `size` (other than the hidden table) that agrees with the examples.
    `yes` and `no` are lists of item keys. Returns a set of tables."""
    dom = lang.domain(kind)
    ym = 0
    for key in yes:
        ym |= 1 << dom.index[key]
    nm = 0
    for key in no:
        nm |= 1 << dom.index[key]
    found = set()
    ones = list(level_one(kind))
    for t in ones:
        if t & ym == ym and not t & nm:
            found.add(t)
    if size >= 2:
        for t in level_two(kind):
            if t & ym == ym and not t & nm:
                found.add(t)
    if size >= 3:
        lits = [t for t, _l in literals(kind)]
        twos = list(level_two(kind)) + ones
        and_l = [t for t in lits if t & ym == ym]
        and_t = [t for t in twos if t & ym == ym]
        for t in and_t:
            for lt in and_l:
                r = t & lt
                if not r & nm:
                    found.add(r)
        or_l = [t for t in lits if not t & nm]
        or_t = [t for t in twos if not t & nm]
        for t in or_t:
            for lt in or_l:
                r = t | lt
                if r & ym == ym:
                    found.add(r)
    found.discard(hidden)
    return found


def bits_of(x):
    out = []
    while x:
        low = x & -x
        out.append(low.bit_length() - 1)
        x ^= low
    return out


def minimal_diffs(diffs, cap=60000):
    """The distinct diffs that no other diff is a subset of (hitting those hits all the rest), fewest bits first.
    Above `cap` distinct diffs the reduction is skipped (greedy only is then trusted)."""
    ordered = sorted(set(diffs), key=lambda d: (popcount(d), d))
    if len(ordered) > cap:
        return ordered, False
    kept = []
    for d in ordered:
        for m in kept:
            if m & d == m:
                break
        else:
            kept.append(d)
    return kept, True


def columns(diffs):
    """[(cover mask over diffs, item index)] for the useful items: items with the same cover are one (the lowest index), and an
    item whose cover is inside another's is dropped."""
    cols = {}
    for j, d in enumerate(diffs):
        for i in bits_of(d):
            cols[i] = cols.get(i, 0) | (1 << j)
    unique = {}
    for i in sorted(cols):
        unique.setdefault(cols[i], i)
    kept = []
    for cover, i in sorted(unique.items(), key=lambda kv: (-popcount(kv[0]), kv[1])):
        if not any(cover & k == cover for k, _i in kept):
            kept.append((cover, i))
    return kept


def greedy_cover(count, cols):
    unc = (1 << count) - 1
    chosen = []
    while unc:
        cover, i = max(cols, key=lambda c: (popcount(c[0] & unc), -c[1]))
        chosen.append((cover, i))
        unc &= ~cover
    return chosen


def exact_cover(count, cols, bound, node_limit=200000):
    """A cover of all `count` diffs by at most `bound` columns, or None. The second value says whether the search finished
    (None with True proves that no cover that small exists)."""
    cands = [[] for _ in range(count)]
    for n, (cover, _i) in enumerate(cols):
        for j in bits_of(cover):
            cands[j].append(n)
    nodes = [0]
    complete = [True]
    biggest = max(popcount(c[0]) for c in cols)

    def rec(unc, budget, chosen):
        if not unc:
            return chosen
        if budget == 0 or popcount(unc) > budget * biggest:
            return None
        nodes[0] += 1
        if nodes[0] > node_limit:
            complete[0] = False
            return None
        j = min(bits_of(unc), key=lambda b: len(cands[b]))
        for n in sorted(cands[j], key=lambda n: (-popcount(cols[n][0] & unc), cols[n][1])):
            found = rec(unc & ~cols[n][0], budget - 1, chosen + [n])
            if found is not None:
                return found
            if not complete[0]:
                return None
        return None

    found = rec((1 << count) - 1, bound, [])
    return found, complete[0]


def par_set(diffs, node_limit=200000):
    """(item indexes, proved minimal?) for a list of diff masks."""
    reduced, _full = minimal_diffs(diffs)
    if not reduced:
        return [], True
    cols = columns(reduced)
    best = [i for _c, i in greedy_cover(len(reduced), cols)]
    proved = len(best) == 1
    while len(best) > 1:
        found, complete = exact_cover(len(reduced), cols, len(best) - 1, node_limit)
        if found is None:
            proved = complete
            break
        best = [cols[n][1] for n in found]
    return sorted(best), proved


def analyse(case, node_limit=200000):
    """Run the whole proof for one case. `case` needs: domain, rule (encoded), size, yes, no.
    Returns a dict of facts; 'par' is the list of item keys of a smallest separating set."""
    kind = case["domain"]
    dom = lang.domain(kind)
    rule = lang.parse_rule(kind, case["rule"])
    hidden = lang.rule_table(kind, rule)
    out = {"min_size": min_size(kind, hidden), "table": hidden}
    consistent = all(lang.rule_accepts(kind, rule, k) for k in case["yes"]) and not any(lang.rule_accepts(kind, rule, k) for k in case["no"])
    out["examples_consistent"] = consistent
    comps = competitors(kind, hidden, case["size"], case["yes"], case["no"])
    out["competitors"] = len(comps)
    diffs = [t ^ hidden for t in comps]
    idx, proved = par_set(diffs, node_limit)
    out["par"] = [dom.items[i] for i in idx]
    out["proved"] = proved
    return out


def check_par(kind, rule_text, size, yes, no, par, node_limit=60000):
    """Re-verify a frozen par set. Returns facts: competitors (how many tables survive the examples), sufficient (the par answers
    leave no competitor), redundant (par items that could be dropped), smaller (None: a smaller set was not found and the search
    finished; True: a smaller set exists; False: the search was cut off)."""
    dom = lang.domain(kind)
    rule = lang.parse_rule(kind, rule_text)
    hidden = lang.rule_table(kind, rule)
    comps = competitors(kind, hidden, size, yes, no)
    diffs = [t ^ hidden for t in comps]
    mask = 0
    for key in par:
        mask |= 1 << dom.index[key]
    out = {"competitors": len(comps), "sufficient": all(d & mask for d in diffs), "redundant": []}
    for key in par:
        rest = mask & ~(1 << dom.index[key])
        if all(d & rest for d in diffs):
            out["redundant"].append(key)
    reduced, _full = minimal_diffs(diffs)
    if len(par) <= 1 or not reduced:
        out["smaller"] = None
        return out
    cols = columns(reduced)
    found, complete = exact_cover(len(reduced), cols, len(par) - 1, node_limit)
    out["smaller"] = True if found is not None else (None if complete else False)
    return out
