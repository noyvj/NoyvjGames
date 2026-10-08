"""Pocket Bazaar -- decorations: purely cosmetic things for the stall front, the coin sink for a player who has
everything else. They change nothing about play. One of each slot is put out at a time; owning them all is a
collection, not a requirement.
"""

SLOTS = (("awning", "Awning"), ("sign", "Sign"), ("cat", "Shop cat"), ("banner", "Banner"), ("plant", "Plant"),
         ("lantern", "Lantern"))

# (id, slot, name, cost)
DECORATIONS = (
    ("awning_striped", "awning", "Striped awning", 40), ("awning_scalloped", "awning", "Scalloped awning", 80),
    ("awning_patchwork", "awning", "Patchwork awning", 120), ("awning_sailcloth", "awning", "Sailcloth awning", 160),
    ("awning_fringed", "awning", "Fringed awning", 200), ("awning_checked", "awning", "Checked awning", 240),
    ("awning_moonlit", "awning", "Moonlit awning", 300), ("awning_gilded", "awning", "Gilded awning", 400),
    ("sign_plain", "sign", "Painted sign", 30), ("sign_carved", "sign", "Carved sign", 70),
    ("sign_hanging", "sign", "Hanging sign", 110), ("sign_brass", "sign", "Brass plaque", 150),
    ("sign_chalk", "sign", "Chalkboard sign", 190), ("sign_neon", "sign", "Glass-tube sign", 260),
    ("sign_mosaic", "sign", "Mosaic sign", 340),
    ("cat_tabby", "cat", "Tabby cat", 60), ("cat_black", "cat", "Black cat", 100), ("cat_ginger", "cat", "Ginger cat", 140),
    ("cat_grey", "cat", "Grey cat", 180), ("cat_spotted", "cat", "Spotted cat", 230), ("cat_fluffy", "cat", "Very fluffy cat", 300),
    ("banner_pennants", "banner", "Pennant string", 30), ("banner_ribbons", "banner", "Ribbon banner", 70),
    ("banner_paper", "banner", "Paper garland", 100), ("banner_flags", "banner", "Little flags", 140),
    ("banner_bunting", "banner", "Bunting", 180), ("banner_tassels", "banner", "Tassel banner", 220),
    ("banner_silk", "banner", "Silk banner", 320),
    ("plant_fern", "plant", "Potted fern", 40), ("plant_herbs", "plant", "Herb box", 80), ("plant_lemon", "plant", "Lemon tree", 130),
    ("plant_ivy", "plant", "Trailing ivy", 170), ("plant_bonsai", "plant", "Bonsai", 250), ("plant_orchid", "plant", "Orchid", 330),
    ("lantern_paper", "lantern", "Paper lantern", 40), ("lantern_tin", "lantern", "Tin lantern", 90),
    ("lantern_glass", "lantern", "Glass lantern", 150), ("lantern_string", "lantern", "String lights", 200),
    ("lantern_star", "lantern", "Star lantern", 270), ("lantern_moon", "lantern", "Moon lantern", 360),
)

BY_ID = {d[0]: d for d in DECORATIONS}
SLOT_IDS = tuple(s[0] for s in SLOTS)


def ids():
    return [d[0] for d in DECORATIONS]


def view(owned, put, coins):
    slots = []
    for slot, label in SLOTS:
        items = [{"id": i, "name": n, "cost": c, "owned": i in owned, "put": put.get(slot) == i, "affordable": coins >= c}
                 for i, s, n, c in DECORATIONS if s == slot]
        slots.append({"slot": slot, "label": label, "put": put.get(slot), "items": items})
    return slots


def can_buy(owned, decor_id, coins):
    if decor_id not in BY_ID:
        return False, "There is no such decoration."
    if decor_id in owned:
        return False, "You already own that."
    cost = BY_ID[decor_id][3]
    if coins < cost:
        return False, f"That costs {cost} coins and you have {coins}."
    return True, ""
