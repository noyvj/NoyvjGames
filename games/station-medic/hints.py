"""Station Medic -- the hint ladder: nudge, hint, answer. All three come from the solver's next careful action for the state on
screen, so they are always right for what has already been done. Hints are free and never touch a seal."""

import lexicon as lx
import solver as sv


def next_action(case, st, solver):
    return sv.next_hint(case, st, solver)


def _conds(case, p, st):
    from shift import READ
    cands = case.candidates(p, st[1][p][READ])
    return [" and ".join(lx.COND[case.pool[i]]["name"] for i in combo) for combo in cands]


def describe(case, st, act):
    """{kind, nudge, hint, answer, label} for an action (or None: no clean finish is left from this state)."""
    if act is None:
        return {"kind": "restore", "label": "Restore the shift",
                "nudge": "A clean finish is no longer possible from here: something was spent that the rest of the shift needed.",
                "hint": "You can finish with a cost, or restore the shift to its start and try a different plan.",
                "answer": "Restore the shift and start again. The sheet and the shelf are the same every time."}
    kind = act[0]
    p = act[1] if len(act) > 1 else 0
    who = case.patients[p].first if len(act) > 1 else ""
    if kind == "scan":
        test = lx.TEST_BY_ID[case.tests[act[2]]]
        look = _conds(case, p, st)
        return {"kind": kind, "label": "Run the %s on %s" % (test["name"], who),
                "nudge": "%s's signs fit more than one condition on the sheet. A scan could tell them apart." % who,
                "hint": "%s could be %s. The %s reads differently for them." % (who, " or ".join(look), test["name"]),
                "answer": "Run the %s on %s." % (test["name"], who)}
    if kind == "treat":
        tx = lx.TX_BY_ID[case.tx[act[2]]]
        look = _conds(case, p, st)
        return {"kind": kind, "label": "Give %s the %s" % (who, tx["name"]),
                "nudge": "%s can be treated now: the sheet leaves one answer, or one treatment that fits every match." % who,
                "hint": "%s fits %s. Look at what cures it, then at the chart note and the shelf." % (who, " or ".join(look)),
                "answer": "Give %s the %s." % (who, tx["name"])}
    if kind in ("band", "robot"):
        how = "a steadying band" if kind == "band" else "Tally"
        return {"kind": kind, "label": "Steady %s with %s" % (who, how),
                "nudge": "%s is shaking too hard to take a scan or a treatment yet." % who,
                "hint": "Steady %s first, with a steadying band or with Tally if %s is on the shift." % (who, "Tally" if case.robots else "no one else"),
                "answer": "Steady %s with %s." % (who, how)}
    if kind == "isolate":
        return {"kind": kind, "label": "Move %s to the cold room" % who,
                "nudge": "%s shows spore flecks and might be catching. Think about the cold room before anything else." % who,
                "hint": "Anything that fits %s could spread. Move %s to the cold room bed before a scan or a treatment." % (who, who),
                "answer": "Move %s to the cold room." % who}
    return None
