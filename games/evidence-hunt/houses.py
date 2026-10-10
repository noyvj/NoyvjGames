"""Evidence Hunt -- the house layouts. A layout is a list of rooms: (id, room type, floor, column, row, name or None). The floor
plan the player sees is each floor drawn as a small grid, cellar at the bottom. Layouts are reused by many cases and by the
sandbox generator, each with its own features and its own restless rooms, so a layout is only a building."""

import lexicon as lx

FLOOR_NAME = {-1: "Cellar level", 0: "Ground floor", 1: "First floor", 2: "Top floor"}

LAYOUTS = {
    "cottage": ("Cottage", [("hall", "hall", 0, 0, 0, None), ("kitchen", "kitchen", 0, 1, 0, None), ("parlour", "parlour", 0, 0, 1, None)]),
    "lodge": ("Lodge", [("porch", "porch", 0, 0, 0, None), ("den", "den", 0, 1, 0, None), ("bedroom", "bedroom", 0, 1, 1, None)]),
    "bungalow": ("Bungalow", [("hall", "hall", 0, 0, 0, None), ("kitchen", "kitchen", 0, 1, 0, None), ("bedroom", "bedroom", 0, 0, 1, None),
                              ("bathroom", "bathroom", 0, 1, 1, None)]),
    "flat": ("Flat", [("hall", "hall", 0, 0, 0, None), ("parlour", "parlour", 0, 1, 0, None), ("bedroom", "bedroom", 0, 0, 1, None),
                      ("pantry", "pantry", 0, 1, 1, None)]),
    "terrace": ("Terrace house", [("hall", "hall", 0, 0, 0, None), ("parlour", "parlour", 0, 1, 0, None), ("kitchen", "kitchen", 0, 0, 1, None),
                                  ("bedroom", "bedroom", 1, 0, 0, None), ("nursery", "nursery", 1, 1, 0, None)]),
    "schoolhouse": ("Schoolhouse", [("cloaks", "cloaks", 0, 0, 0, None), ("classroom", "classroom", 0, 1, 0, None), ("study", "study", 0, 2, 0, "Teacher's study"),
                                    ("loft", "loft", 1, 1, 0, None), ("boiler", "boiler", -1, 1, 0, None)]),
    "farmhouse": ("Farmhouse", [("hall", "hall", 0, 0, 0, None), ("kitchen", "kitchen", 0, 1, 0, None), ("dairy", "dairy", 0, 2, 0, None),
                                ("parlour", "parlour", 0, 0, 1, None), ("bedroom", "bedroom", 1, 0, 0, None), ("attic", "attic", 1, 1, 0, None)]),
    "vicarage": ("Vicarage", [("hall", "hall", 0, 0, 0, None), ("study", "study", 0, 1, 0, None), ("dining", "dining", 0, 0, 1, None),
                              ("kitchen", "kitchen", 0, 1, 1, None), ("landing", "landing", 1, 0, 0, None), ("bedroom", "bedroom", 1, 1, 0, None),
                              ("cellar", "cellar", -1, 0, 0, None)]),
    "shop": ("Corner shop", [("shop", "shop", 0, 0, 0, None), ("store", "store", 0, 1, 0, None), ("hallway", "hallway", 0, 2, 0, None),
                             ("landing", "landing", 1, 0, 0, None), ("parlour", "parlour", 1, 1, 0, "Flat above"), ("bedroom", "bedroom", 1, 2, 0, None)]),
    "villa": ("Villa", [("hall", "hall", 0, 0, 0, None), ("library", "library", 0, 1, 0, None), ("dining", "dining", 0, 2, 0, None),
                        ("conservatory", "conservatory", 0, 0, 1, None), ("kitchen", "kitchen", 0, 1, 1, None), ("landing", "landing", 1, 0, 0, None),
                        ("bedroom", "bedroom", 1, 1, 0, None), ("bathroom", "bathroom", 1, 2, 0, None)]),
    "manor": ("Manor", [("hall", "hall", 0, 0, 0, None), ("parlour", "parlour", 0, 1, 0, None), ("dining", "dining", 0, 2, 0, None),
                        ("study", "study", 0, 0, 1, None), ("kitchen", "kitchen", 0, 1, 1, None), ("scullery", "scullery", 0, 2, 1, None),
                        ("landing", "landing", 1, 0, 0, None), ("bedroom", "bedroom", 1, 1, 0, None), ("nursery", "nursery", 1, 2, 0, None)]),
    "inn": ("Coaching inn", [("taproom", "smoking", 0, 0, 0, "Taproom"), ("dining", "dining", 0, 1, 0, None), ("kitchen", "kitchen", 0, 2, 0, None),
                             ("store", "store", 0, 3, 0, None), ("cellar", "cellar", -1, 1, 0, "Beer cellar"), ("landing", "landing", 1, 0, 0, None),
                             ("room1", "bedroom", 1, 1, 0, "Room one"), ("room2", "bedroom", 1, 2, 0, "Room two"), ("attic", "attic", 2, 1, 0, None)]),
    "mill": ("Old mill", [("cellar", "cellar", -1, 0, 0, "Wheel pit"), ("boiler", "boiler", -1, 1, 0, None), ("hall", "hall", 0, 0, 0, "Mill floor"),
                          ("workshop", "workshop", 0, 1, 0, None), ("store", "store", 0, 2, 0, "Grain store"), ("kitchen", "kitchen", 0, 3, 0, None),
                          ("landing", "landing", 1, 0, 0, None), ("bedroom", "bedroom", 1, 1, 0, None), ("study", "study", 1, 2, 0, "Miller's office"),
                          ("loft", "loft", 2, 1, 0, None)]),
    "abbey": ("Abbey house", [("hall", "hall", 0, 0, 0, None), ("chapel", "chapel", 0, 1, 0, None), ("library", "library", 0, 2, 0, None),
                              ("dining", "dining", 0, 0, 1, "Refectory"), ("kitchen", "kitchen", 0, 1, 1, None), ("laundry", "laundry", -1, 0, 0, None),
                              ("cellar", "cellar", -1, 1, 0, None), ("landing", "landing", 1, 0, 0, None), ("bedroom", "bedroom", 1, 1, 0, "Cell one"),
                              ("study", "study", 1, 2, 0, "Scriptorium"), ("tower", "tower", 2, 1, 0, "Bell loft")]),
    "hotel": ("Seaside hotel", [("hall", "hall", 0, 0, 0, "Lobby"), ("dining", "dining", 0, 1, 0, None), ("ballroom", "ballroom", 0, 2, 0, None),
                                ("smoking", "smoking", 0, 0, 1, None), ("kitchen", "kitchen", 0, 1, 1, None), ("laundry", "laundry", -1, 0, 0, None),
                                ("boiler", "boiler", -1, 1, 0, None), ("landing", "landing", 1, 0, 0, None), ("bedroom", "bedroom", 1, 1, 0, "Suite"),
                                ("gallery", "gallery", 1, 2, 0, None), ("bathroom", "bathroom", 1, 3, 0, None), ("tower", "tower", 2, 1, 0, "Lookout")]),
    "theatre": ("Little theatre", [("porch", "porch", 0, 0, 0, "Foyer"), ("hall", "hall", 0, 1, 0, "Stalls"), ("ballroom", "ballroom", 0, 2, 0, "Stage"),
                                   ("cloaks", "cloaks", 0, 0, 1, "Cloakroom"), ("store", "store", 0, 1, 1, "Prop store"), ("workshop", "workshop", 0, 2, 1, "Scenery shop"),
                                   ("boiler", "boiler", -1, 1, 0, None), ("cellar", "cellar", -1, 2, 0, "Trap room"), ("landing", "landing", 1, 0, 0, "Circle stairs"),
                                   ("gallery", "gallery", 1, 1, 0, "Dress circle"), ("music", "music", 1, 2, 0, "Orchestra room"), ("loft", "loft", 2, 1, 0, "Fly loft")]),
    "estate": ("Country estate", [("hall", "hall", 0, 0, 0, None), ("library", "library", 0, 1, 0, None), ("music", "music", 0, 2, 0, None),
                                  ("dining", "dining", 0, 0, 1, None), ("conservatory", "conservatory", 0, 1, 1, None), ("kitchen", "kitchen", 0, 2, 1, None),
                                  ("scullery", "scullery", 0, 3, 1, None), ("cellar", "cellar", -1, 1, 0, None), ("landing", "landing", 1, 0, 0, None),
                                  ("bedroom", "bedroom", 1, 1, 0, None), ("nursery", "nursery", 1, 2, 0, None), ("study", "study", 1, 3, 0, None),
                                  ("attic", "attic", 2, 1, 0, None)]),
    "grand": ("Grand house", [("porch", "porch", 0, 0, 0, None), ("hall", "hall", 0, 1, 0, None), ("ballroom", "ballroom", 0, 2, 0, None),
                              ("gallery", "gallery", 0, 3, 0, None), ("dining", "dining", 0, 0, 1, None), ("kitchen", "kitchen", 0, 1, 1, None),
                              ("chapel", "chapel", 0, 2, 1, None), ("cellar", "cellar", -1, 1, 0, None), ("boiler", "boiler", -1, 2, 0, None),
                              ("landing", "landing", 1, 0, 0, None), ("bedroom", "bedroom", 1, 1, 0, None), ("library", "library", 1, 2, 0, None),
                              ("music", "music", 1, 3, 0, None), ("attic", "attic", 2, 1, 0, None)]),
}
LAYOUT_ORDER = tuple(LAYOUTS)


def rooms_of(layout):
    """The rooms of a layout as dicts, in layout order (the room index is the position in this list)."""
    out = []
    for rid, rtype, floor, col, row, name in LAYOUTS[layout][1]:
        default, text = lx.ROOM_TYPES[rtype]
        out.append({"id": rid, "type": rtype, "name": name or default, "floor": floor, "col": col, "row": row, "text": text})
    return out


def size_of(layout):
    return len(LAYOUTS[layout][1])


def floors_of(rooms):
    """Floor numbers present, highest first (the plan draws the top floor at the top)."""
    return sorted({r["floor"] for r in rooms}, reverse=True)
