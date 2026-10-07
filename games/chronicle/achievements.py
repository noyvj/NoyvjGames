"""Chronicle -- achievements: the hub-wide framework (static manifest `achievements.json` plus
`achievements_earned` in the save). Every id is COMPUTED from the progress state, never stored on its own, so
a loaded save and a played one cannot disagree. None is hidden or luck-gated; all are reachable by playing
any one set to the end (easy to 100%).

Each rule is evaluated per set and earned if it holds in ANY loaded set, so a new set never needs engine
changes and can never take an earned achievement away.
"""

ACHIEVEMENTS = (
    ("first_card", "First Card", "Place a card in its right place."),
    ("first_timeline", "First Timeline", "Solve a timeline puzzle."),
    ("straight_line", "Straight Line", "Solve a puzzle with a single check."),
    ("five_timelines", "Five Timelines", "Solve five timeline puzzles."),
    ("first_section", "First Section", "Clear the first section of a set."),
    ("all_sections", "Whole Story", "Clear every section of a set."),
    ("wider_world", "The Wider World", "Find every 'elsewhere' event in a set."),
    ("all_people", "Faces and Names", "Find every person in a set."),
    ("all_places", "On the Map", "Find every place in a set."),
    ("fine_print", "Fine Print", "Open the sources of five different claims."),
    ("doubting_reader", "Doubting Reader", "Open the sources of a claim marked disputed or doubtful."),
    ("complete_archive", "Complete Archive", "Fill the archive of a set to 100%."),
)

IDS = [a[0] for a in ACHIEVEMENTS]


def earned(state, sets, helpers):
    """Ids earned right now, in manifest order. `helpers` supplies per-set derived facts (see game.py)."""
    got = set()
    solved_total = 0
    for set_id, cset in sets.items():
        prog = state["sets"].get(set_id)
        if not prog:
            continue
        learned = helpers.learned(set_id)
        solved = prog["solved"]
        if learned:
            got.add("first_card")
        solved_total += len(solved)
        if solved:
            got.add("first_timeline")
        if any(rec.get("checks") == 1 for rec in solved.values()):
            got.add("straight_line")
        cleared = [helpers.cleared(set_id, sid) for sid in cset.section_ids]
        if cleared and cleared[0]:
            got.add("first_section")
        if cleared and all(cleared):
            got.add("all_sections")
        context = set(cset.event_ids("context"))
        if context and context <= learned:
            got.add("wider_world")
        people = helpers.people_found(set_id)
        if cset.people and len(people) == len(cset.people):
            got.add("all_people")
        places = helpers.places_found(set_id)
        if cset.places and len(places) == len(cset.places):
            got.add("all_places")
        if helpers.percent(set_id) == 100:
            got.add("complete_archive")
    if solved_total >= 5:
        got.add("five_timelines")
    viewed = state["viewed"]
    if len(viewed) >= 5:
        got.add("fine_print")
    for key in viewed:
        set_id, _, claim_id = key.partition("/")
        cset = sets.get(set_id)
        claim = cset.claims.get(claim_id) if cset else None
        if claim and claim["confidence"] != "documented":
            got.add("doubting_reader")
    return [i for i in IDS if i in got]
