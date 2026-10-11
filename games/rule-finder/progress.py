"""Rule Finder -- progress is a function of the named cases; nothing here counts time.

`named` is a dict case id -> {"t": best test count, "r": the rule that named it, "m": 1 if a near miss came before}."""

import cases


def drawer_named(named, drawer):
    return sum(1 for c in drawer["cases"] if c.id in named)


def drawer_named_by_id(named, key):
    """How many cases of the drawer with this id are named."""
    return sum(drawer_named(named, d) for d in cases.DRAWER_LIST if d["id"] == key)


def drawer_clean(named, drawer):
    return sum(1 for c in drawer["cases"] if c.id in named and named[c.id]["t"] <= c.par)


def drawer_open(index):
    """Every drawer that has cases is open from the start. Kept as a function so the view and the tests have one place to ask."""
    return 0 <= index < len(cases.DRAWER_LIST) and bool(cases.DRAWER_LIST[index]["cases"])


def case_open(cid):
    return cid in cases.BY_ID


def totals(named):
    done = [c for c in cases.ALL_CASES if c.id in named]
    drawers_closed = sum(1 for d in cases.DRAWER_LIST if d["cases"] and drawer_named(named, d) == len(d["cases"]))
    return {"cases": len(cases.ALL_CASES), "named": len(done), "clean": sum(1 for c in done if named[c.id]["t"] <= c.par),
            "drawers": len(cases.DRAWER_LIST), "drawers_closed": drawers_closed}


def next_case(named, cid):
    """The next case to play after `cid`: the first one not yet named going round, else None when every case is named."""
    order = cases.ORDER
    if cid not in order:
        return None
    start = order.index(cid)
    for other in order[start + 1:] + order[:start]:
        if other not in named:
            return other
    return None
