"""Rule Finder -- the Rule Codex: one page per case, filled when the case is named and read when the player opens it.

A page shows the rule in words, the family (or families) it belongs to and the SHORTEST PATH: the smallest set of tests that
would have proved the rule, with the answer to each. Everything is derived from the named cases and the list of pages read,
so a loaded save and a played one cannot disagree."""

import cases
import lang


def filled(named, cid):
    return cid in named


def summary(named, read):
    """The Codex index: one entry per case in order, filled or not, read or not."""
    out = []
    for d in cases.DRAWER_LIST:
        for c in d["cases"]:
            out.append({"id": c.id, "name": c.name, "drawer": d["name"], "number": c.number, "filled": c.id in named,
                        "read": c.id in named and c.id in read})
    return out


def page(case, named, read):
    """The full page for a filled case, or None for an empty one."""
    rec = named.get(case.id)
    if rec is None:
        return None
    kind = case.kind
    return {
        "id": case.id, "name": case.name, "drawer": cases.DRAWER_LIST[case.drawer]["name"], "number": case.number, "kind": kind,
        "words": case.words, "families": [lang.FAMILIES[f][0] for f in case.families], "clauses": case.size,
        "shortest": [{"item": k, "yes": case.accepts(k), "label": lang.item_words(kind, k)} for k in case.shortest],
        "par": case.par, "best": rec["t"], "medal": cases.medal_for(case, rec["t"]), "line": case.line, "read": case.id in read,
        "rule_used": lang.rule_words(kind, lang.parse_rule(kind, rec["r"])),
    }


def counts(named, read):
    return {"filled": len(named), "read": sum(1 for cid in named if cid in read), "total": len(cases.ORDER)}
