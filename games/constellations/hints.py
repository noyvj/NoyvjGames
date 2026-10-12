"""Constellations -- the hint ladder. Every suggestion is a line-logic deduction (sky.propagate), so it is always justified and never a guess.

Three rungs, each opened only when the player asks ("Would you like a suggestion?"), never shown on its own:
  1 the nudge    which star has a line that is certain (no line named)
  2 the hint     that line, drawn as a dotted ghost on the chart, and the reasoning that forces it
  3 the answer   the whole figure as ghost lines, and a "Draw it" button that draws it (one undo step)

The reasoning is worked out from what the player has drawn and is RIGHT: a line that is not part of the figure is ignored when working
out what is certain (it is never named until nothing else is left to suggest), so a hint cannot be led astray by a mistake. It reads
the chart's stored `logic` field: a chart marked 1 is finished by plain line logic, so a suggestion never needs more; a chart marked 2
may need one what-if step, and the hint says so in words. Chosen deterministically (the first certain line, in the order the logic found
it): pure functions of the chart and the lines drawn, no clock, no randomness.
"""

import sky

KINDS = ("forced", "bridge", "what-if", "remove")

_WHY_OUT = {
    "cross": "it would cross a line that is certain",
    "full": "that star already has all its lines",
    "close": "it would shut the figure before every numbered star is in it",
}


def _name(letters, k, rules):
    a, b = rules.edges[k]
    return "%s-%s" % (letters[a], letters[b])


def _first_certain(rules, trail, drawn, only_what_if=False):
    """The first line the logic found to be IN that the player has not drawn: (rule, line, source star) or None."""
    for rule, k, value, source in trail:
        if value != sky.IN or k in drawn:
            continue
        if only_what_if and rule != "what-if":
            continue
        return rule, k, source
    return None


def _excluded_at(rules, trail, star, letters):
    """Why the other joins at `star` are out, from the trail: a list of (other star letter, short reason)."""
    out = []
    for rule, k, value, source in trail:
        if value != sky.OUT or star not in rules.edges[k]:
            continue
        other = rules.edges[k][0] if rules.edges[k][1] == star else rules.edges[k][1]
        why = _WHY_OUT.get(rule)
        if rule == "cross" and source is not None:
            why = "it would cross the line %s" % _name(letters, source, rules)
        elif rule == "full" and source is not None and source != star:
            why = "%s already has all its lines" % letters[source]
        elif rule == "full":
            continue
        if why and letters[other] not in [o for o, _w in out]:
            out.append((letters[other], why))
    return out


def pick(chart, rules, drawn, letters):
    """The suggestion to offer for the lines `drawn` (given lines included), or None when the figure is already complete.
    `chart` is the chart's data dict (its stored figure and `logic` field). Returns a dict: kind, line (index), star (the nudge star),
    nudge, detail, plus `missing` (figure lines not drawn) and `wrong` (drawn lines that do not belong), both sorted line indices."""
    figure = {rules.index[tuple(e)] for e in chart["figure"]}
    drawn = set(drawn)
    missing = sorted(figure - drawn)
    wrong = sorted(drawn - figure)
    if not missing and not wrong:
        return None
    known = {k: sky.IN for k in drawn & figure}
    state, trail = sky.propagate(rules, known)
    found = _first_certain(rules, trail, drawn) if state is not None else None
    if found is None and chart.get("logic") == 2:
        state, trail = sky.propagate(rules, known, lookahead=True)
        if state is not None:
            found = _first_certain(rules, trail, drawn, only_what_if=True) or _first_certain(rules, trail, drawn)
    if found is None and missing:
        # the logic is exhausted by what the player drew (it cannot be, for a chart that is finished by line logic), so name the first line honestly
        k = missing[0]
        found = ("forced", k, None)
    if found is None:
        k = wrong[0]
        a, b = rules.edges[k]
        return {"kind": "remove", "line": k, "star": a, "missing": missing, "wrong": wrong,
                "nudge": "One of the lines you drew does not belong to the figure. Every line the figure needs is already there.",
                "detail": "The line %s is not part of the figure. Erase it." % _name(letters, k, rules)}
    rule, k, source = found
    a, b = rules.edges[k]
    star = source if (rule == "forced" and source is not None) else a
    nudge = "Star %s has a line that is certain. No guessing is needed there." % letters[star] if rule == "forced" else \
            "Star %s is at one end of a line that is certain. No guessing is needed there." % letters[star]
    line = _name(letters, k, rules)
    if rule == "forced" and source is not None:
        need = rules.need.get(source)
        out = _excluded_at(rules, trail, source, letters)
        plural = "" if need == 1 else "s"
        if out:
            text = "The line %s. Star %s needs %d line%s, and only that many joins are still possible at it: %s. So every join that is left is a line." % (
                line, letters[source], need, plural, "; ".join("%s-%s is out because %s" % (letters[source], o, w) for o, w in out[:3]))
        else:
            text = "The line %s. Star %s needs %d line%s, and it has exactly that many joins it could make, so each of them is a line." % (line, letters[source], need, plural)
    elif rule == "bridge":
        text = ("The line %s. Without it, the stars the figure has to reach could not all be joined into one piece, so it has to be drawn." % line)
    elif rule == "what-if":
        text = ("The line %s. Try leaving it out: a number would break, or the figure could no longer be finished. That is the one what-if step "
                "this chart needs, and it shows the line has to be drawn." % line)
    else:
        text = "The line %s is one the figure needs." % line
    return {"kind": rule if rule in KINDS else "forced", "line": k, "star": star, "missing": missing, "wrong": wrong, "nudge": nudge, "detail": text}


def answer_text(rules, letters, missing, wrong):
    """Words for the third rung."""
    parts = []
    if missing:
        parts.append("Lines to draw: %s." % ", ".join(_name(letters, k, rules) for k in missing))
    if wrong:
        parts.append("Lines to erase: %s." % ", ".join(_name(letters, k, rules) for k in wrong))
    return " ".join(parts)
