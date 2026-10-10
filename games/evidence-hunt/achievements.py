"""Evidence Hunt -- achievements (the hub-wide framework: a static manifest `achievements.json` plus `achievements_earned` in the
save). Everything is computed from facts about the player's progress, never stored separately, so a loaded save and a played one
can never disagree. All are reachable without luck, none is hidden, and none rewards time or how often you come back. Every one
has a number so the player can see how close they are."""

import codex
import lexicon as lx
import progress

TOTAL = len(progress.ORDER)
GUIDE_TOTAL = codex.total()

# (id, label, description, fact, need, chapter that must be open before it can be a goal)
ACHIEVEMENTS = (
    ("first_case", "First Case", "Solve your first case.", "done", 1, 0),
    ("ten_cases", "Ten Cases", "Solve 10 cases.", "done", 10, 0),
    ("chapter_closed", "Chapter Closed", "Solve every case of one chapter.", "chapters_done", 1, 0),
    ("three_chapters", "Three Chapters", "Solve every case of 3 chapters.", "chapters_done", 3, 0),
    ("last_house", "The Last House", "Solve every case.", "done", TOTAL, 0),
    ("clean_work", "Clean Work", "Earn 5 Clean seals.", "clean", 5, 0),
    ("spotless_book", "Spotless Book", "Earn a Clean seal on every case.", "clean", TOTAL, 0),
    ("careful_notes", "Careful Notes", "Take 60 readings.", "readings", 60, 0),
    ("every_spirit", "Every Spirit", "Complete the guide page of every kind of spirit.", "spirits_full", len(lx.KIND_IDS), 0),
    ("two_at_once", "Two at Once", "Solve 4 cases with two presences.", "two", 4, 2),
    ("keepsakes_home", "Keepsakes Home", "Return all 8 keepsakes.", "kept", len(lx.KS_IDS), 3),
    ("fresh_eyes", "Fresh Eyes", "Solve 3 practice cases from codes.", "sandbox", 3, 0),
    ("from_memory", "From Memory", "Solve 5 different cases with the sheet covered.", "mem", 5, 1),
    ("whole_guide", "The Whole Guide", "File every page of the field guide.", "pages", GUIDE_TOTAL, 0),
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
