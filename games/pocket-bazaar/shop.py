"""Pocket Bazaar -- the shop: permanent stall upgrades bought with coins.

Coins are earned only by playing and there is one currency. Every upgrade is small and permanent; none is needed to
finish a day (the first day is fine on a bare stall) and none can be bought with anything but coins.
"""

UPGRADES = (
    {"id": "preview", "name": "Queue preview", "cost": 150,
     "blurb": "Shows who is next in line, and what they will ask for, before they step up."},
    {"id": "broom", "name": "Broom polish", "cost": 120,
     "blurb": "A swept good gives back one coin."},
    {"id": "tipjar", "name": "Tip jar", "cost": 200,
     "blurb": "Tips for quick service are a half bigger."},
    {"id": "shelf", "name": "Display shelf", "cost": 250,
     "blurb": "One extra cell beside the counter that keeps its good from day to day."},
    {"id": "scales", "name": "Fine scales", "cost": 300,
     "blurb": "Goods of tier 3 and above are worth a tenth more to customers."},
    {"id": "counter", "name": "Wider counter", "cost": 400,
     "blurb": "A sixth column on the counter."},
)

BY_ID = {u["id"]: u for u in UPGRADES}


def ids():
    return [u["id"] for u in UPGRADES]


def view(owned, coins):
    return [{"id": u["id"], "name": u["name"], "cost": u["cost"], "blurb": u["blurb"],
             "owned": u["id"] in owned, "affordable": coins >= u["cost"]} for u in UPGRADES]


def can_buy(owned, upgrade_id, coins):
    """(True, "") or (False, a plain reason)."""
    if upgrade_id not in BY_ID:
        return False, "There is no such upgrade."
    if upgrade_id in owned:
        return False, "You already have that."
    if coins < BY_ID[upgrade_id]["cost"]:
        return False, f"That costs {BY_ID[upgrade_id]['cost']} coins and you have {coins}."
    return True, ""


def rules_from(owned):
    """The Day rules the owned upgrades switch on."""
    rules = {}
    if "scales" in owned:
        rules["scales"] = True
    if "broom" in owned:
        rules["broom_refund"] = 1
    if "tipjar" in owned:
        rules["tip_pct"] = 40
    return rules
