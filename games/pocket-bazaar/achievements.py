"""Pocket Bazaar -- achievements (the hub-wide framework: a static manifest `achievements.json` plus
`achievements_earned` in the save). Everything is computed from facts about the stall, never stored separately, so a
loaded save and a played one can never disagree. All are reachable without luck, none is hidden, and none rewards time
spent or how often you come back (easy to 100%). Every one has a number so the player can see how close they are.
"""

# (id, label, description, fact, need)
ACHIEVEMENTS = (
    ("open_for_business", "Open for Business", "Finish your first market day.", "days_played", 1),
    ("satisfied_customer", "Satisfied Customer", "Fill 10 orders.", "orders", 10),
    ("chain_master", "Chain Master", "Make a 4-link chain, the longest the five tiers allow.", "best_chain", 4),
    ("full_combo", "Full Combo", "Get the order combo up to times three (four orders in a row).", "best_combo", 4),
    ("perfect_day", "Perfect Day", "Finish a day without a single customer leaving.", "flag_perfect", 1),
    ("showpiece", "Showpiece", "Make your first tier-5 good.", "flag_showpiece", 1),
    ("regular", "Regular", "Reach bond level 3 with any of the regulars.", "regular_level", 3),
    ("bargain_blitz", "Bargain Blitz", "Clear a Bargain Hunt day with nobody leaving.", "flag_bargain", 1),
    ("well_stocked", "Well Stocked", "Buy all six stall upgrades.", "upgrades", 6),
    ("decorator", "Decorator", "Own 10 decorations.", "decor", 10),
    ("twin_twins", "Twin Day Twins", "Get 5 free tier-1 goods from Twin Day in one day.", "flag_twin5", 1),
    ("all_festivals", "All Festivals", "Play a market day under each of the six festivals.", "festivals", 6),
    ("quiet_stall", "Quiet Stall", "Finish a Slow Market day without ever getting a combo going.", "flag_quiet", 1),
    ("thirty_days", "30 Market Days", "Finish 30 market days.", "days_played", 30),
)

IDS = tuple(a[0] for a in ACHIEVEMENTS)


def earned(facts):
    """The ids earned right now, in manifest order."""
    return [i for i, _l, _d, fact, need in ACHIEVEMENTS if facts.get(fact, 0) >= need]


def view(facts):
    out = []
    for i, label, description, fact, need in ACHIEVEMENTS:
        have = min(facts.get(fact, 0), need)
        out.append({"id": i, "label": label, "description": description, "earned": have >= need,
                    "have": have, "need": need})
    return out


def goals(facts, count=3):
    """The next few achievements still to earn, in manifest order: the always-visible 'what to do next' list. They can
    be done in any order."""
    return [a for a in view(facts) if not a["earned"]][:count]
