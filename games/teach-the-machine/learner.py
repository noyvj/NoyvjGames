"""Teach the Machine -- Pip's learner: a small decision tree of depth at most 3, trained by information gain.

Pure and deterministic: no clock, no random source. The same cases and the same switched-on features always give the same tree.

A FEATURE is {"id", "label", "kind", ...} with kind "yes_no" (value 1 or 0), "number" (a whole number, "lo".."hi", optional "unit") or
"kind" (one of the words in "values"). A CASE is {"id", "name", "v": {feature id: value}, "label": bin index}.

A TEST asks one question about one feature: {"f": id, "op": "yes"} (the value is yes), {"f": id, "op": "ge", "arg": m} (the number is m
or more) or {"f": id, "op": "eq", "arg": word} (the word is this one). A tree is a nested dict:
  leaf   {"leaf": 1, "label": bin, "counts": [per bin], "n": cases}
  split  {"leaf": 0, "test": {...}, "yes": node, "no": node, "counts": [...], "n": cases, "gain": float}

How it chooses (the fixed tie-breaks): the question with the highest information gain (the drop in entropy, rounded to 9 places, and only
if it is above 0); a tie goes to the feature that comes first in the lesson's feature order, then (for numbers) the lower threshold, then
(for words) the word that comes first in the feature's list. A threshold between two neighbouring values a < b sits at (a + b + 1) // 2.
A group stops growing when it is pure, when it is 3 questions deep, or when no question has any gain; a leaf answers its majority bin, and
a tie goes to the lowest bin number.
"""

import math

MAX_DEPTH = 3
EPS = 1e-9


def fmt_value(feature, value):
    kind = feature["kind"]
    if kind == "yes_no":
        return "yes" if value else "no"
    if kind == "number":
        unit = feature.get("unit", "")
        return "%d%s" % (value, (" " + unit) if unit else "")
    return str(value)


def chip_text(feature, value):
    return "%s: %s" % (feature["label"], fmt_value(feature, value))


def question(feature, test):
    """The test as a question in words."""
    op = test["op"]
    if op == "yes":
        return "%s: yes?" % feature["label"]
    if op == "ge":
        unit = feature.get("unit", "")
        return "%s %d%s or more?" % (feature["label"], test["arg"], (" " + unit) if unit else "")
    return "%s is %s?" % (feature["label"], test["arg"])


def holds(test, value):
    op = test["op"]
    if op == "yes":
        return bool(value)
    if op == "ge":
        return value >= test["arg"]
    return value == test["arg"]


def entropy(counts):
    n = sum(counts)
    if not n:
        return 0.0
    total = 0.0
    for c in counts:
        if c:
            p = c / float(n)
            total -= p * math.log(p, 2)
    return total


def _counts(cases, n_bins):
    out = [0] * n_bins
    for c in cases:
        out[c["label"]] += 1
    return out


def _majority(counts):
    best = 0
    for i, c in enumerate(counts):
        if c > counts[best]:
            best = i
    return best


def candidates(feature, cases):
    """Every question worth asking about this feature on these cases, in the fixed order."""
    kind = feature["kind"]
    fid = feature["id"]
    values = [c["v"][fid] for c in cases]
    if kind == "yes_no":
        return [{"f": fid, "op": "yes"}]
    if kind == "number":
        distinct = sorted(set(values))
        return [{"f": fid, "op": "ge", "arg": (a + b + 1) // 2} for a, b in zip(distinct, distinct[1:])]
    present = set(values)
    return [{"f": fid, "op": "eq", "arg": w} for w in feature["values"] if w in present]


def _split(cases, test):
    yes, no = [], []
    for c in cases:
        (yes if holds(test, c["v"][test["f"]]) else no).append(c)
    return yes, no


def train(features, on, cases, n_bins, depth=0):
    """Grow Pip's tree from `cases` using only the features whose ids are in `on`."""
    counts = _counts(cases, n_bins)
    n = len(cases)
    leaf = {"leaf": 1, "label": _majority(counts), "counts": counts, "n": n}
    if depth >= MAX_DEPTH or sum(1 for c in counts if c) <= 1:
        return leaf
    parent = entropy(counts)
    best, best_gain = None, EPS
    for feature in features:
        if feature["id"] not in on:
            continue
        for test in candidates(feature, cases):
            yes, no = _split(cases, test)
            if not yes or not no:
                continue
            after = len(yes) / float(n) * entropy(_counts(yes, n_bins)) + len(no) / float(n) * entropy(_counts(no, n_bins))
            gain = round(parent - after, 9)
            if gain > best_gain + EPS:
                best, best_gain = test, gain
    if best is None:
        return leaf
    yes, no = _split(cases, best)
    return {"leaf": 0, "test": best, "yes": train(features, on, yes, n_bins, depth + 1), "no": train(features, on, no, n_bins, depth + 1),
            "counts": counts, "n": n, "gain": best_gain}


def predict(tree, case):
    """The bin Pip answers for a case (a plain walk down the tree)."""
    node = tree
    while not node["leaf"]:
        node = node["yes"] if holds(node["test"], case["v"][node["test"]["f"]]) else node["no"]
    return node["label"]


def trace(tree, features_by_id, case):
    """The path a case takes: a list of steps, each {"test", "question", "value", "answer"}, and the leaf it ends in. The Why panel shows this."""
    steps = []
    node = tree
    while not node["leaf"]:
        test = node["test"]
        feature = features_by_id[test["f"]]
        value = case["v"][test["f"]]
        answer = holds(test, value)
        steps.append({"test": test, "question": question(feature, test), "value": chip_text(feature, value), "answer": "yes" if answer else "no"})
        node = node["yes"] if answer else node["no"]
    return steps, node


def leaf_key(steps):
    return "".join("y" if s["answer"] == "yes" else "n" for s in steps)


def tree_lines(tree, features_by_id, bins):
    """The tree in words, one line per branch: [{"d": depth, "text": ...}]."""
    lines = []

    def leaf_text(node):
        return "%s (%d of the %d seen)" % (bins[node["label"]], node["counts"][node["label"]], node["n"])

    def walk(node, depth, prefix):
        if node["leaf"]:
            lines.append({"d": depth, "text": prefix + leaf_text(node)})
            return
        test = node["test"]
        lines.append({"d": depth, "text": prefix + "ask: " + question(features_by_id[test["f"]], test)})
        for answer in ("yes", "no"):
            child = node[answer]
            if child["leaf"]:
                lines.append({"d": depth + 1, "text": answer + ": " + leaf_text(child)})
            else:
                walk(child, depth + 1, answer + ", then ")

    walk(tree, 0, "first ")
    return lines


def tree_size(tree):
    return 1 if tree["leaf"] else 1 + tree_size(tree["yes"]) + tree_size(tree["no"])


def tree_depth(tree):
    return 0 if tree["leaf"] else 1 + max(tree_depth(tree["yes"]), tree_depth(tree["no"]))


def used_features(tree):
    if tree["leaf"]:
        return set()
    return {tree["test"]["f"]} | used_features(tree["yes"]) | used_features(tree["no"])


def distance(features, on, a, b):
    """How different two cases look to Pip: over the switched-on features, 0 (same) to 1 each."""
    total = 0.0
    for f in features:
        if f["id"] not in on:
            continue
        x, y = a["v"][f["id"]], b["v"][f["id"]]
        if f["kind"] == "number":
            span = max(1, f["hi"] - f["lo"])
            total += abs(x - y) / float(span)
        else:
            total += 0.0 if x == y else 1.0
    return round(total, 6)
