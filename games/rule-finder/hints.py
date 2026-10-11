"""Rule Finder -- the hint ladder. Three rungs per case, all free, all on request only (each rung opens only when the player presses
for it), none touching a medal or a named case:

  1 a nudge: which KIND of property to look at (sums, order, repeats, ...), never which clause or how they are joined;
  2 a hint: one test item worth sending next (the first item of the shortest path not seen yet), shown as a ghost tile;
  3 the answer: the rule written out, with a button that puts it into the Rule Builder (the player still presses Name it).

Everything is derived from the case and what has been seen, so it is the same every time."""

import lang


def nudge_text(case):
    fams = [lang.FAMILIES[f][1] for f in lang.families(case.kind, case.rule)]
    if case.size == 1:
        return "Look at %s." % fams[0]
    if len(fams) == 1:
        return "The gate looks at %d things about one kind of property: %s." % (case.size, fams[0])
    listed = ", then ".join(fams) if len(fams) > 2 else " and ".join(fams)
    return "The gate looks at %d things. Look at %s." % (case.size, listed)


def next_item(case, seen):
    """The first item of the shortest path that has not been seen, or None when the player has seen enough."""
    for key in case.shortest:
        if key not in seen:
            return key
    return None


def hint_view(case, seen):
    key = next_item(case, seen)
    if key is None:
        return {"text": "You have seen enough: every other rule of this size or shorter is already ruled out. Check your rule against the log.",
                "item": "", "label": ""}
    return {"text": "Try sending this one next. It is a good test: its answer rules a lot out.", "item": key, "label": lang.item_words(case.kind, key)}


def view(case, rung, seen):
    out = {"rung": rung, "nudge": "", "hint": None, "answer": None}
    if rung >= 1:
        out["nudge"] = nudge_text(case)
    if rung >= 2:
        out["hint"] = hint_view(case, seen)
    if rung >= 3:
        out["answer"] = {"words": case.words, "rule": lang.rule_json(case.rule)}
    return out
