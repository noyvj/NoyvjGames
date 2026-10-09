"""Logic Gates -- the 14 achievements (the hub-wide framework: a static manifest `achievements.json` plus `achievements_earned` in the
save). Each is a number, have of need, computed from the saved record, so a loaded save and a played one cannot disagree. All are
reachable, none is timed or hidden."""

import levels

# id, label, description, need
ACHIEVEMENTS = (
    ("first_light", "First Light", "Solve a level.", 1),
    ("gate_keeper", "Gate Keeper", "Solve every level in Switches and Lamps.", 8),
    ("mix_and_match", "Mix and Match", "Solve every level in Combining Gates.", 9),
    ("remember_me", "Remember Me", "Solve every level in Memory.", 7),
    ("carry_the_one", "Carry the One", "Solve every level in Adders.", 7),
    ("station_awake", "Wake the Station", "Solve the last level and wake the station.", 1),
    ("forty_for_forty", "Forty for Forty", "Solve all 40 levels.", 40),
    ("tidy_ten", "Tidy Ten", "Reach par (no more chips than the reference) on 10 levels.", 10),
    ("full_par", "Full Par", "Reach par on all 40 levels.", 40),
    ("on_your_own", "On Your Own", "Solve 15 levels without asking for a hint.", 15),
    ("asked_nicely", "Asked Nicely", "Ask for a hint once. It is what they are for.", 1),
    ("the_sixteen", "The Sixteen", "Find all 16 two-input functions in the sandbox.", 16),
    ("hundred_chips", "Hundred Chips", "Place 100 chips, anywhere.", 100),
    ("switch_flipper", "Switch Flipper", "Flip 100 switches to see what a circuit does.", 100),
)


def sixteen_found(found):
    """How many of the 16 two-input functions are in the found list. A 3-input table code is a 2-input function when its rows come in
    equal pairs (the output does not depend on C)."""
    return sum(1 for c in found if is_two_input(c))


def is_two_input(code):
    return all(((code >> (2 * k)) & 1) == ((code >> (2 * k + 1)) & 1) for k in range(4))


def progress(meta):
    """{id: have}, uncapped."""
    recs = meta["levels"]
    solved = {lid for lid, r in recs.items() if r["solved"]}
    ch = {c: sum(1 for lv in levels.LEVELS if lv["chapter"] == c and lv["id"] in solved) for c in range(1, 6)}
    have = {
        "first_light": len(solved),
        "gate_keeper": ch[1], "mix_and_match": ch[2], "remember_me": ch[3], "carry_the_one": ch[4],
        "station_awake": 1 if "wake-the-station" in solved else 0,
        "forty_for_forty": len(solved),
        "tidy_ten": sum(1 for r in recs.values() if r["par"]),
        "full_par": sum(1 for r in recs.values() if r["par"]),
        "on_your_own": sum(1 for r in recs.values() if r["solved"] and not r["hints"] and not r["answer"]),
        "asked_nicely": 1 if any(r["hints"] for r in recs.values()) else 0,
        "the_sixteen": sixteen_found(meta["found"]),
        "hundred_chips": meta["stats"]["chips"],
        "switch_flipper": meta["stats"]["flips"],
    }
    return have


def view(meta):
    have = progress(meta)
    out = []
    for aid, label, desc, need in ACHIEVEMENTS:
        h = min(have[aid], need)
        out.append({"id": aid, "label": label, "description": desc, "have": h, "need": need, "earned": h >= need})
    return out


def earned(meta):
    return [a["id"] for a in view(meta) if a["earned"]]


def goals(meta, count=3):
    """The unearned achievements closest to done (most complete first, manifest order breaks ties)."""
    open_ones = [(a["have"] / a["need"], -i, a) for i, a in enumerate(view(meta)) if not a["earned"]]
    open_ones.sort(key=lambda t: (-t[0], -t[1]))
    return [t[2] for t in open_ones[:count]]
