"""Heist Committee -- the payout write-up: a short funny paragraph and a title, assembled from the event log and
the phrase fragments in content/writeups.json. Deterministic: the same heist always reads the same."""

import engine


def _pick(options, seed, *keys):
    if not options:
        return ""
    return options[int(engine.roll(seed, "writeup", *keys) * len(options)) % len(options)]


def outcome_class(outcome):
    if outcome["escaped"] and not outcome["alarm"]:
        return "clean"
    if outcome["escaped"]:
        return "loud"
    if outcome.get("stranded"):
        return "stranded"
    return "bust"


def short_event(text, limit=84):
    first = text.split(". ")[0].rstrip(".")
    if len(first) > limit:
        first = first[:limit - 1].rstrip() + "..."
    return first


def join_names(names):
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def plural(n, word):
    return "%d %s" % (n, word if n == 1 else word + "s")


def build(content, target_id, result, crew_ids, seed):
    """Returns {title, text, chain:[...], cls}. `result` is engine.simulate's return value."""
    W = content.writeups
    target = content.targets[target_id]
    out = result["outcome"]
    events = result["events"]
    cls = outcome_class(out)
    short = target.get("short", target["name"])
    short_title = short[0].upper() + short[1:] if short else target["name"]
    for article in ("the ", "The "):
        if short_title.startswith(article):
            short_title = short_title[len(article):]
    names = [content.crew[c]["short"] for c in crew_ids]
    fill = {"target": short, "short_title": short_title, "crew_a": _pick(names, seed, "a"), "crew_b": _pick(names, seed, "b")}

    if out["chain_links"] >= 4 and W.get("titles", {}).get("chain"):
        title = _pick(W["titles"]["chain"], seed, "t").format(**fill)
    elif cls in ("stranded", "bust") and W.get("titles", {}).get(cls):
        title = _pick(W["titles"][cls], seed, "t").format(**fill)
    else:
        title = _pick(target.get("titles", ["The Job"]), seed, "t")

    opener = _pick(W.get("openers", {}).get(cls, []), seed, "o").format(**fill)
    parts = [opener[:1].upper() + opener[1:]]
    chain = [events[i] for i in out["chain_path"]]
    if out["chain_links"] >= 3:
        parts.append(_pick(W["starts"], seed, "s").format(first=short_event(chain[0]["text"])))
        parts.append(_pick(W["chain"], seed, "c").format(n=out["chain_links"]))
    else:
        parts.append(_pick(W["no_chain"], seed, "n"))
    absorbers = sorted({content.crew[e["crew"]]["short"] for e in events if e["type"] == "absorb" and e["crew"]})
    if out["absorbed"] and absorbers:
        parts.append(_pick(W["absorbed"], seed, "ab").format(names=join_names(absorbers), n=plural(out["absorbed"], "problem")))
    souvenir = [e for e in events if e["type"] == "trait" and "souvenir" in e["text"].lower()]
    if souvenir:
        parts.append(_pick(W["souvenir"], seed, "sv").format(crew=content.crew[souvenir[0]["crew"]]["short"]))
    parts.append(_pick(W.get("closers", {}).get(cls, []), seed, "cl"))
    chain_view = [{"i": e["i"], "beat": e["beat"], "type": e["type"], "icon": e["icon"], "text": short_event(e["text"]),
                   "crew": e["crew"]} for e in chain]
    return {"title": title, "text": " ".join(p for p in parts if p), "chain": chain_view, "cls": cls}
