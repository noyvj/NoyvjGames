"""The skeletons of the 40 authored cases: house, truth, restless rooms, features, keepsake, kit, sheet size, number of account
lines and the smallest bag that must be needed. design.py fills in the sheet and the account."""

R = lambda *rooms: tuple(rooms)  # noqa: E731


def S(cid, layout, truth, restless, pool, acc, min_kit, kit=3, features=None, keepsake=None):
    return {"id": cid, "layout": layout, "truth": (truth,) if isinstance(truth, str) else tuple(truth), "restless": tuple(restless),
            "pool": pool, "accounts": acc, "min_kit": min_kit, "kit": kit, "features": features or {}, "keepsake": keepsake}


SPECS = [
    # chapter 1: First Visits (more rooms each time)
    S("1-1", "cottage", "hearthkeeper", [R("parlour")], 3, 0, 1),
    S("1-2", "lodge", "scrivener", [R("den")], 3, 0, 1),
    S("1-3", "bungalow", "draughtling", [R("bedroom")], 4, 1, 1),
    S("1-4", "flat", "glimmer", [R("parlour", "pantry")], 4, 0, 2),
    S("1-5", "terrace", "candlewick", [R("nursery")], 4, 1, 1),
    S("1-6", "schoolhouse", "pacer", [R("classroom", "boiler")], 5, 1, 2),
    S("1-7", "farmhouse", "tangle", [R("dairy", "attic")], 5, 1, 2),
    S("1-8", "vicarage", "lullwisp", [R("cellar", "landing", "bedroom")], 5, 1, 2),
    # chapter 2: Misleading Readings (features fool one reading)
    S("2-1", "terrace", "mothlight", [R("bedroom", "kitchen")], 5, 1, 2, features={"bedroom": "draught", "nursery": "wiring"}),
    S("2-2", "shop", "ledger", [R("store")], 5, 1, 2, features={"store": "wiring", "shop": "damp"}),
    S("2-3", "schoolhouse", "hushling", [R("classroom", "cloaks")], 5, 1, 2, features={"classroom": "draught", "cloaks": "damp"}),
    S("2-4", "farmhouse", "spindle", [R("parlour")], 5, 0, 2, features={"parlour": "desk", "dairy": "draught"}),
    S("2-5", "villa", "draughtling", [R("bedroom", "bathroom")], 6, 1, 2, features={"bedroom": "wiring", "bathroom": "damp"}),
    S("2-6", "manor", "glimmer", [R("nursery", "landing")], 6, 1, 2, features={"nursery": "paint", "landing": "streetlamp"}),
    S("2-7", "inn", "scrivener", [R("room2")], 6, 1, 2, features={"room2": "desk", "cellar": "damp"}),
    S("2-8", "vicarage", "tangle", [R("study", "dining")], 6, 1, 2, features={"study": "wiring", "dining": "streetlamp", "cellar": "paint"}),
    # chapter 3: Two Presences
    S("3-1", "vicarage", ("hearthkeeper", "draughtling"), [R("cellar"), R("bedroom")], 5, 2, 2),
    S("3-2", "shop", ("scrivener", "candlewick"), [R("store"), R("parlour")], 5, 2, 2),
    S("3-3", "villa", ("tangle", "ledger"), [R("library"), R("bedroom")], 6, 2, 2, features={"library": "desk", "bedroom": "wiring"}),
    S("3-4", "manor", ("hushling", "spindle"), [R("nursery"), R("study")], 6, 2, 2, features={"nursery": "draught"}),
    S("3-5", "inn", ("hearthkeeper", "scrivener"), [R("taproom"), R("room1")], 6, 2, 2, features={"taproom": "wiring", "room1": "streetlamp"}),
    S("3-6", "farmhouse", ("draughtling", "tangle"), [R("dairy"), R("attic")], 6, 2, 3, features={"dairy": "damp"}),
    S("3-7", "terrace", ("candlewick", "hushling"), [R("kitchen"), R("nursery")], 5, 2, 2, features={"nursery": "draught"}),
    S("3-8", "mill", ("ledger", "spindle"), [R("workshop"), R("loft")], 7, 2, 3, features={"workshop": "paint", "loft": "desk"}),
    # chapter 4: Keepsakes
    S("4-1", "villa", "glimmer", [R("conservatory", "bedroom")], 5, 0, 2, keepsake=("bedroom", "handmirror", "curious")),
    S("4-2", "manor", "tangle", [R("nursery", "parlour")], 5, 0, 2, keepsake=("nursery", "musicbox", "mover")),
    S("4-3", "inn", "lullwisp", [R("room1", "room2", "attic")], 6, 0, 2, keepsake=("room1", "thimble", "tidy")),
    S("4-4", "mill", "pacer", [R("workshop", "store")], 6, 0, 2, keepsake=("workshop", "brasskey", "mover")),
    S("4-5", "vicarage", "scrivener", [R("study", "bedroom")], 6, 0, 2, features={"bedroom": "desk"}, keepsake=("study", "paperweight", "tidy")),
    S("4-6", "shop", "mothlight", [R("shop", "parlour")], 6, 0, 2, features={"shop": "streetlamp"}, keepsake=("parlour", "teacup", "shy")),
    S("4-7", "farmhouse", "draughtling", [R("kitchen", "dairy")], 6, 1, 2, features={"kitchen": "draught"}, keepsake=("dairy", "buttontin", "shy")),
    S("4-8", "hotel", "hushling", [R("bedroom", "gallery")], 7, 0, 3, features={"gallery": "paint"}, keepsake=("bedroom", "woolbasket", "curious")),
    # chapter 5: The Big Houses (a bag of four)
    S("5-1", "mill", "ledger", [R("hall", "workshop", "loft")], 7, 1, 3, kit=4, features={"hall": "wiring", "loft": "desk", "boiler": "draught"}),
    S("5-2", "abbey", "glimmer", [R("chapel", "tower", "study")], 7, 1, 3, kit=4, features={"chapel": "streetlamp", "tower": "paint", "cellar": "damp"}),
    S("5-3", "hotel", ("hearthkeeper", "tangle"), [R("ballroom"), R("bedroom")], 7, 2, 3, kit=4, features={"ballroom": "draught", "bedroom": "wiring"}),
    S("5-4", "theatre", "lullwisp", [R("ballroom", "loft", "gallery")], 8, 0, 3, kit=4, features={"ballroom": "streetlamp", "gallery": "draught"}, keepsake=("loft", "musicbox", "tidy")),
    S("5-5", "estate", "draughtling", [R("music", "nursery", "attic")], 8, 0, 3, kit=4, features={"music": "wiring", "nursery": "damp", "attic": "draught"}, keepsake=("attic", "teacup", "shy")),
    S("5-6", "grand", ("spindle", "hushling"), [R("music"), R("chapel")], 8, 2, 3, kit=4, features={"music": "desk", "chapel": "damp"}),
    S("5-7", "estate", "pacer", [R("library", "kitchen", "study", "scullery")], 8, 1, 3, kit=4, features={"library": "desk", "kitchen": "wiring", "study": "paint"}),
    S("5-8", "grand", "scrivener", [R("gallery", "library", "attic")], 8, 1, 3, kit=4, features={"gallery": "streetlamp", "library": "desk", "attic": "paint"}, keepsake=("attic", "handmirror", "curious")),
]
