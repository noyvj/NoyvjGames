"""Dead Reckoning -- achievements (the hub-wide framework: a static manifest `achievements.json` plus `achievements_earned` in the
save). Everything is computed from the saved record, never stored separately, so a loaded save and a played one cannot disagree.
All are reachable without luck and none is hidden (easy to 100%).

The plan's ninth achievement, "Two at Once" (complete a two-ship chart), waits for the deferred Two ships milestone; "Patient
Navigator" takes its place so the list stays at 14 and every one can be earned today."""

PRACTICE_SEEDS = 10

ACHIEVEMENTS = (
    ("first_landfall", "First Landfall", "Reach a destination."),
    ("dead_on", "Dead On", "Make landfall with the ship ending within half a nautical mile of where your own plot said she would."),
    ("trust_the_numbers", "Trust the Numbers", "Earn three stars on a chart without using any steer-to helper or the par plan."),
    ("around_the_rocks", "Around the Rocks", "Make landfall on a chart with three hazards on the direct line."),
    ("set_and_drift", "Set and Drift", "Make landfall on a chart with a current, beating the naive plan by at least half."),
    ("first_fix", "First Fix", "Take a landmark fix in Watch-by-watch."),
    ("fog_of_war_ish", "Fog of War-ish", "Make landfall on a fog chart."),
    ("riding_the_tide", "Riding the Tide", "Make landfall with the tidal stream fair for most of the time you spent in it."),
    ("patient_navigator", "Patient Navigator", "Lie at anchor to wait for the tide, then make landfall."),
    ("aground", "Aground", "Run aground once. Everyone does."),
    ("long_way_round", "Long Way Round", "Make landfall on a plan of more than 60 nautical miles through the water."),
    ("chapter_closer", "Chapter Closer", "Make landfall on every chart in a chapter."),
    ("practice_makes", "Practice Makes", "Sail 10 practice charts."),
    ("all_stars", "All Stars", "Earn three stars on every campaign chart."),
)

FLAG_OF = {"first_landfall": "landfall", "dead_on": "dead_on", "trust_the_numbers": "trusted", "around_the_rocks": "around_rocks",
           "set_and_drift": "set_and_drift", "first_fix": "first_fix", "fog_of_war_ish": "fog_clear", "riding_the_tide": "riding_tide",
           "patient_navigator": "waited", "aground": "aground", "long_way_round": "long_way"}


def earned(meta, chapters):
    """The ids earned right now, in manifest order. `chapters` is a list of lists of chart ids (the campaign, by chapter)."""
    flags = set(meta["flags"])
    records = meta["charts"]
    got = {aid for aid, flag in FLAG_OF.items() if flag in flags}
    if any(all(records.get(cid, {}).get("stars", 0) >= 1 for cid in ids) for ids in chapters if ids):
        got.add("chapter_closer")
    if meta["practice_seeds_played"] >= PRACTICE_SEEDS:
        got.add("practice_makes")
    every = [cid for ids in chapters for cid in ids]
    if every and all(records.get(cid, {}).get("stars", 0) >= 3 for cid in every):
        got.add("all_stars")
    return [a[0] for a in ACHIEVEMENTS if a[0] in got]


def view(meta, chapters):
    have = set(earned(meta, chapters))
    return [{"id": i, "label": label, "description": desc, "earned": i in have} for i, label, desc in ACHIEVEMENTS]
