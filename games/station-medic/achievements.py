"""Station Medic -- achievements (the hub-wide framework: a static manifest `achievements.json` plus `achievements_earned` in the
save). Everything is computed from facts about the player's progress, never stored separately, so a loaded save and a played one
can never disagree. All are reachable without luck, none is hidden, and none rewards time or how often you come back. Every one
has a number so the player can see how close they are."""

import codex
import progress

TOTAL = len(progress.ORDER)
CHAPTERS = len(progress.CHAPTERS)
RECORD_TOTAL = codex.counts([], [], [], {})[1]

# (id, label, description, fact, need, chapter that must be open before it can be a goal)
ACHIEVEMENTS = (
    ("first_shift", "First Shift", "Finish your first shift.", "done", 1, 0),
    ("ten_shifts", "Ten Shifts", "Finish 10 shifts.", "done", 10, 0),
    ("chapter_closed", "Chapter Closed", "Finish every shift of one chapter.", "chapters_done", 1, 0),
    ("halfway_round", "Halfway Round", "Finish every shift of 4 chapters.", "chapters_done", min(4, CHAPTERS), 0),
    ("long_night", "The Long Night", "Finish every shift.", "done", TOTAL, 0),
    ("clean_hands", "Clean Hands", "Earn 5 Clean seals.", "clean", 5, 0),
    ("steady_work", "Steady Work", "Earn 25 Clean seals.", "clean", min(25, TOTAL), 0),
    ("spotless_ward", "Spotless Ward", "Earn a Clean seal on every shift.", "clean", TOTAL, 0),
    ("careful_eyes", "Careful Eyes", "Run 20 scans.", "scans", 20, 1),
    ("door_closed", "Door Closed", "Earn 3 Clean seals on shifts that use the cold room.", "cold_clean", 3, 4),
    ("tallys_friend", "Tally's Friend", "Earn 5 Clean seals on shifts where Tally is on duty.", "tally_clean", 5, 5),
    ("pages_filled", "Pages Filled", "File half of the Record.", "records", RECORD_TOTAL // 2, 0),
    ("whole_record", "The Whole Record", "File every page of the Record.", "records", RECORD_TOTAL, 0),
    ("quiet_company", "Quiet Company", "Hear every crew story to its last page.", "crew_told", codex.crew_total(), 0),
)
IDS = tuple(a[0] for a in ACHIEVEMENTS)


def earned(facts):
    """The ids earned right now, in manifest order."""
    return [i for i, _l, _d, fact, need, _c in ACHIEVEMENTS if need > 0 and facts.get(fact, 0) >= need]


def view(facts):
    out = []
    for i, label, description, fact, need, chapter in ACHIEVEMENTS:
        have = min(facts.get(fact, 0), need)
        out.append({"id": i, "label": label, "description": description, "earned": have >= need,
                    "have": have, "need": need, "chapter": chapter})
    return out


def goals(facts, open_chapters, count=3):
    """The next few achievements still to earn that can be worked on now (their chapter is open), in manifest order: the
    always-visible 'what to do next' list. They can be done in any order."""
    return [a for a in view(facts) if not a["earned"] and a["chapter"] < open_chapters][:count]
