"""Chronicle -- achievements: the hub-wide framework (static manifest `achievements.json` plus
`achievements_earned` in the save). Every id is COMPUTED from the progress state, never stored on its own, so
a loaded save and a played one cannot disagree. None is hidden or luck-gated; all are reachable by playing
any one set to the end (easy to 100%): the cause web and Myth or record ones need a set that has those chapters.

The whose-account, decision-point and review ones need a set with those parts (the review ones need only a learned fact).

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
    ("first_thread", "First Thread", "Confirm a cause link on the cause web."),
    ("clean_web", "Clean Web", "Finish a cause web puzzle without a single unconfirmed thread."),
    ("whole_web", "Whole Web", "Confirm every cause link in a set."),
    ("first_sort", "First Sort", "Sort a claim correctly in Myth or record."),
    ("myth_spotter", "Myth Spotter", "Sort a traditional-but-doubtful claim correctly."),
    ("straight_sort", "Straight Sort", "Sort a Myth or record puzzle with a single check."),
    ("fair_judge", "Fair Judge", "Sort every claim of a set correctly."),
    ("first_source", "First Source Weighed", "Judge a source correctly in Whose account?."),
    ("both_kinds", "Primary and Secondary", "Judge one primary and one secondary source correctly."),
    ("careful_reader", "Careful Reader", "Judge a source with a single check."),
    ("every_account", "Every Account", "Judge every source of a set."),
    ("first_decision", "In Their Shoes", "Make your choice at a decision point."),
    ("every_crossroads", "Every Crossroads", "Make a choice at every decision point of a set."),
    ("first_recall", "First Recall", "Answer a review question correctly."),
    ("long_memory", "Long Memory", "Bring one fact all the way to the longest gap in Review."),
)

IDS = [a[0] for a in ACHIEVEMENTS]
LADDER_LENGTH = 5          # the review ladder has five rungs (review.LADDER); an item at step 5 has reached the longest gap


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
        threads = helpers.threads(set_id)
        if threads:
            got.add("first_thread")
        if any(rec.get("misses") == 0 for rec in helpers.web_records(set_id).values()):
            got.add("clean_web")
        reachable_threads = set(cset.web_relation_ids())
        if reachable_threads and reachable_threads <= threads:
            got.add("whole_web")
        done = helpers.sorted_claims(set_id)
        if done:
            got.add("first_sort")
        if any(cset.claims[c]["confidence"] == "traditional-but-doubtful" for c in done if c in cset.claims):
            got.add("myth_spotter")
        if any(rec.get("checks") == 1 for rec in helpers.myth_records(set_id).values()):
            got.add("straight_sort")
        reachable_claims = set(cset.myth_claim_ids())
        if reachable_claims and reachable_claims <= done:
            got.add("fair_judge")
        judged = helpers.judged(set_id)
        if judged:
            got.add("first_source")
            kinds = {cset.passage(*k.split("/", 1))["kind"] for k in judged if cset.passage(*k.split("/", 1))}
            if {"primary", "secondary"} <= kinds:
                got.add("both_kinds")
        if any(rec.get("checks") == 1 for rec in helpers.account_records(set_id).values()):
            got.add("careful_reader")
        all_passages = set(cset.passage_keys())
        if all_passages and all_passages <= judged:
            got.add("every_account")
        decided = helpers.decided(set_id)
        if decided:
            got.add("first_decision")
        if cset.decisions and set(cset.decision_ids()) <= set(decided):
            got.add("every_crossroads")
        records = helpers.review_records(set_id)
        if any(rec.get("right", 0) >= 1 for rec in records.values()):
            got.add("first_recall")
        if any(rec.get("step", 0) >= LADDER_LENGTH for rec in records.values()):
            got.add("long_memory")
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
