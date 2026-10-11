"""Zero-G Shift -- the search settings and bay names for tools/build_bays.py (authoring only; the game never loads this)."""

DECKS = [
    {
        "name": "Cargo Floor", "module": "cargo",
        "pars": [4, 5, 6, 7, 8, 9, 10, 12],
        "profiles": [
            {"params": dict(w=5, h=5, kinds=[0], segs=2), "seeds": 6000},
            {"params": dict(w=6, h=6, kinds=[0], segs=3), "seeds": 6000},
            {"params": dict(w=6, h=7, kinds=[0], segs=3), "seeds": 6000},
            {"params": dict(w=7, h=7, kinds=[0], segs=4), "seeds": 8000},
        ],
        "bays": [("first-pallet", "First Pallet"), ("dock-lane", "Dock Lane"), ("corner-stack", "The Corner Stack"),
                 ("short-haul", "Short Haul"), ("slow-drift", "Slow Drift"), ("elbow-room", "Elbow Room"),
                 ("cold-storage", "Cold Storage"), ("loose-freight", "Loose Freight")],
    },
    {
        "name": "Crates", "module": "crates",
        "pars": [6, 7, 8, 9, 10, 11, 12, 14],
        "profiles": [
            {"params": dict(w=6, h=6, kinds=[0, 1], segs=2, walls=2), "seeds": 12000},
            {"params": dict(w=7, h=7, kinds=[0, 1], segs=3, walls=2), "seeds": 12000},
            {"params": dict(w=7, h=7, kinds=[0, 1, 2], segs=3, walls=2), "seeds": 30000},
        ],
        "bays": [("matched-pair", "Matched Pair"), ("two-tags", "Two Tags"), ("sorting-floor", "Sorting Floor"),
                 ("manifest-mixup", "Manifest Mix-up"), ("ricochet", "Ricochet"), ("crossing-lanes", "Crossing Lanes"),
                 ("cross-dock", "Cross-Dock"), ("tag-team", "Tag Team")],
    },
    {
        "name": "Posts and Pads", "module": "posts", "pars": [8, 9, 10, 11, 12, 13, 14, 16],
        "profiles": [
            {"params": dict(w=7, h=7, kinds=[0, 1], segs=1, posts=5), "seeds": 20000, "feature": "pads"},
            {"params": dict(w=8, h=7, kinds=[0, 1], segs=1, posts=6), "seeds": 20000, "feature": "pads"},
            {"params": dict(w=8, h=8, kinds=[0, 1, 2], segs=1, posts=6), "seeds": 40000, "feature": "pads"},
            {"params": dict(w=7, h=7, kinds=[0, 0, 1], segs=1, posts=5), "seeds": 40000, "feature": "pads"},
        ],
        "bays": [("pillar-row", "Pillar Row"), ("stanchion-alley", "Stanchion Alley"), ("pad-garden", "Pad Garden"),
                 ("three-tags", "Three Tags"), ("twin-pads", "Twin Pads"), ("pad-matters", "The Pad Matters"),
                 ("slalom-bay", "Slalom Bay"), ("wrong-pad", "Wrong Pad")],
    },
    {
        "name": "Hatches", "module": "hatches", "pars": [7, 8, 9, 10, 11, 12, 14, 16],
        "profiles": [
            {"params": dict(w=7, h=7, kinds=[0], segs=2, posts=2, hatches=1), "seeds": 12000, "feature": "hatch"},
            {"params": dict(w=7, h=7, kinds=[0, 1], segs=2, posts=3, hatches=2), "seeds": 20000, "feature": "hatch"},
            {"params": dict(w=8, h=8, kinds=[0, 1], segs=2, posts=3, hatches=3), "seeds": 20000, "feature": "hatch"},
            {"params": dict(w=8, h=8, kinds=[0, 1, 2], segs=2, posts=3, hatches=3), "seeds": 40000, "feature": "hatch"},
        ],
        "bays": [("service-hatch", "Service Hatch"), ("pass-through", "Pass-Through"), ("chute", "Chute"),
                 ("slotted-floor", "Slotted Floor"), ("two-hatches", "Two Hatches"), ("mail-slot", "Mail Slot"),
                 ("letterbox", "Letterbox"), ("sluice", "Sluice")],
    },
    {
        "name": "Bumpers and Doors", "module": "doors", "pars": [6, 8, 10, 8, 10, 12, 14, 16],
        "profiles": [
            {"params": dict(w=7, h=7, kinds=[0], segs=2, posts=2, bumpers=2), "seeds": 12000, "feature": "bumper", "slot": "bumper"},
            {"params": dict(w=8, h=8, kinds=[0, 1], segs=2, posts=3, bumpers=3), "seeds": 20000, "feature": "bumper", "slot": "bumper"},
            {"params": dict(w=7, h=7, kinds=[0, 1], segs=2, posts=2, bumpers=1, door=True, door_cells=1), "seeds": 20000, "feature": "door", "slot": "door"},
            {"params": dict(w=8, h=8, kinds=[0, 1], segs=2, posts=2, bumpers=2, door=True, door_cells=2), "seeds": 30000, "feature": "door", "slot": "door"},
            {"params": dict(w=8, h=8, kinds=[0, 1, 2], segs=2, posts=2, bumpers=2, door=True, door_cells=2), "seeds": 40000, "feature": "door", "slot": "door"},
        ],
        "bays": [("soft-landing", "Soft Landing"), ("cushion-row", "Cushion Row"), ("bump-stop", "Bump Stop"),
                 ("airlock-four", "Airlock Four"), ("door-pad", "Door Pad"), ("keyed-lock", "Keyed Lock"),
                 ("pressure-door", "Pressure Door"), ("last-seal", "Last Seal")],
    },
    {
        "name": "The Long Hold", "module": "hold", "pars": [12, 13, 14, 15, 16, 18, 20, 22],
        "profiles": [
            {"params": dict(w=9, h=9, kinds=[0, 1], segs=3, posts=5, hatches=1, bumpers=1), "seeds": 20000},
            {"params": dict(w=10, h=9, kinds=[0, 1], segs=3, posts=5, hatches=2, bumpers=1), "seeds": 20000},
            {"params": dict(w=10, h=10, kinds=[0, 1, 2], segs=3, posts=6, hatches=1, bumpers=2), "seeds": 40000, "cap": 40000},
            {"params": dict(w=9, h=10, kinds=[0, 1, 2], segs=3, posts=5, hatches=2, bumpers=2, door=True, door_cells=2), "seeds": 40000, "cap": 40000},
        ],
        "bays": [("aft-hold", "Aft Hold"), ("long-hold", "Long Hold"), ("the-spine", "The Spine"),
                 ("deep-stack", "Deep Stack"), ("freight-canyon", "Freight Canyon"), ("marrow-run", "Marrow Run"),
                 ("the-long-way", "The Long Way"), ("last-berth", "Last Berth")],
    },
]
