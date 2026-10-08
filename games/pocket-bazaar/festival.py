"""Pocket Bazaar -- festivals: the one modifier each market day carries.

The festival for a day comes from the day number alone (day N uses the (N-1) mod len'th festival), so the order
rotates predictably, can be shown the day before, and needs no clock and no calendar. Each festival says plainly
what it changes and whether it makes the day easier or harder ("tone"); nothing about difficulty is hidden.
"""

FESTIVALS = {
    "slow": {"name": "Slow Market", "tone": "relaxed",
             "blurb": "Customers wait half again as long, and everyone pays a fifth less. A relaxed day.",
             "patience_pct": 150, "pay_pct": 80},
    "harvest": {"name": "Harvest Fair", "tone": "tricky",
                "blurb": "Produce crates give a tier-2 good half the time, and Critics turn up twice as often.",
                "crate_t2": {"produce": (1, 2)}, "critic_weight": 2},
    "twin": {"name": "Twin Day", "tone": "relaxed",
             "blurb": "Every merge that makes a tier-3 good also sets a free tier-1 good down beside it.",
             "twin": True},
}

ORDER = ("slow", "harvest", "twin")


def for_day(number):
    """The festival id for a day number (1-based)."""
    return ORDER[(number - 1) % len(ORDER)]


def info(festival_id):
    f = FESTIVALS[festival_id]
    return {"id": festival_id, "name": f["name"], "tone": f["tone"], "blurb": f["blurb"]}


def apply_spec(spec, festival_id):
    """The day's recipe after the festival has had its say (a new dict; the table is never changed)."""
    f = FESTIVALS[festival_id]
    out = dict(spec)
    if "patience_pct" in f:
        out["slack_pct"] = spec["slack_pct"] * f["patience_pct"] // 100
    if "critic_weight" in f:
        out["archetypes"] = tuple((a, w * f["critic_weight"] if a == "critic" else w) for a, w in spec["archetypes"])
    return out


def day_rules(festival_id):
    """The per-action rules the festival hands to the Day."""
    f = FESTIVALS[festival_id]
    rules = {}
    for key in ("twin", "pay_pct", "crate_t2"):
        if key in f:
            rules[key] = f[key]
    return rules
