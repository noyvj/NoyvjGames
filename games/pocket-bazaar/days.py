"""Pocket Bazaar -- what each market day asks of you.

The first ten days are hand-tuned; later days (Free Stall) follow the same curve, slowly harder, capped at 16
customers and tier 5. `slack_pct` is how generous patience is (300 = three times the order's build cost): it is
shown nowhere as a hidden dial, it simply decides how long the customers in this day wait.
"""

CAMPAIGN_DAYS = 10
MAX_CUSTOMERS = 16
WINDOW = 3                    # customers waiting at the stall at once

# customers, max_tier, max_items, item weights (1,2,3 items), archetype weights, slack_pct
_TABLE = {
    1: (6, 2, 1, (1,), (("regular", 1),), 450),
    2: (7, 2, 2, (3, 1), (("regular", 4), ("haggler", 1)), 420),
    3: (8, 3, 2, (3, 2), (("regular", 4), ("haggler", 1), ("bulk", 1)), 400),
    4: (8, 3, 2, (2, 2), (("regular", 4), ("haggler", 1), ("bulk", 1), ("critic", 1)), 380),
    5: (9, 3, 3, (3, 3, 1), (("regular", 4), ("haggler", 1), ("bulk", 1), ("critic", 2)), 360),
    6: (9, 4, 3, (3, 3, 1), (("regular", 4), ("haggler", 2), ("bulk", 1), ("critic", 2)), 350),
    7: (10, 4, 3, (2, 3, 2), (("regular", 4), ("haggler", 2), ("bulk", 2), ("critic", 2)), 340),
    8: (10, 4, 3, (2, 3, 2), (("regular", 3), ("haggler", 2), ("bulk", 2), ("critic", 2)), 330),
    9: (11, 4, 3, (2, 3, 2), (("regular", 3), ("haggler", 2), ("bulk", 2), ("critic", 3)), 320),
    10: (12, 5, 3, (2, 3, 2), (("regular", 3), ("haggler", 2), ("bulk", 2), ("critic", 3)), 320),
}


def spec(number, unlocked_archetypes=None):
    """The day's recipe as a plain dict."""
    if number < 1:
        raise ValueError("day numbers start at 1")
    key = min(number, CAMPAIGN_DAYS)
    customers, max_tier, max_items, item_weights, archetypes, slack = _TABLE[key]
    if number > CAMPAIGN_DAYS:                     # Free Stall: a gentle climb past the campaign
        extra = number - CAMPAIGN_DAYS
        customers = min(MAX_CUSTOMERS, customers + extra // 2)
        slack = max(280, slack - extra)
    if unlocked_archetypes is not None:
        archetypes = tuple(a for a in archetypes if a[0] in unlocked_archetypes) or (("regular", 1),)
    return {"number": number, "customers": customers, "max_tier": max_tier, "max_items": max_items,
            "item_weights": item_weights, "archetypes": archetypes, "slack_pct": slack}
