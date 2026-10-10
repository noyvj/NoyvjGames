"""Stranded -- achievements (the hub-wide framework: a static manifest `achievements.json` plus `achievements_earned` in the
save). Everything is computed from facts about what the player has found, never stored separately, so a loaded save and a
played one can never disagree. None is hidden, timed or luck-based, and each has a number so the player can see how close it is."""

import lore
import story

SCENES = len(story.SCENES)
EDGES = len(story.EDGES)
ENDINGS = len(story.ENDING_IDS)
LOGS = sum(1 for c in lore.COLLECT if c[1] == "log")
ITEMS = sum(1 for c in lore.COLLECT if c[1] == "item")
RECS = sum(1 for c in lore.COLLECT if c[1] == "rec")

# (id, label, description, fact, need)
ACHIEVEMENTS = (
    ("first_words", "First Words", "Send your first reply.", "sent", 1),
    ("three_days", "Three Days In", "Reach day 3.", "max_day", 3),
    ("all_days", "All Twelve Days", "Reach day 12.", "max_day", 12),
    ("someone_comes", "Someone Comes", "Reach an ending.", "endings", 1),
    ("four_ways", "Four Ways Home", "Reach 4 different endings.", "endings", 4),
    ("every_road", "Every Road Home", "Reach every ending.", "endings", ENDINGS),
    ("second_thoughts", "Second Thoughts", "Rewind to an earlier choice.", "rewinds", 1),
    ("a_look_ahead", "A Look Ahead", "Use What if on a scene.", "peeks", 1),
    ("half_the_map", "Half the Map", "Walk half of all the paths on the branch map.", "tried", (EDGES + 1) // 2),
    ("every_path", "Every Path", "Walk every path on the branch map.", "tried", EDGES),
    ("every_place", "Every Place", "See every scene.", "scenes", SCENES),
    ("log_keeper", "Log Keeper", "Collect every log entry.", "logs", LOGS),
    ("pocket_full", "Pocket Full", "Collect every found item.", "items", ITEMS),
    ("her_voice", "Her Voice", "Collect every recording.", "recs", RECS),
)
IDS = tuple(a[0] for a in ACHIEVEMENTS)


def earned(facts):
    """The ids earned right now, in manifest order."""
    return [i for i, _l, _d, fact, need in ACHIEVEMENTS if need > 0 and facts.get(fact, 0) >= need]


def view(facts):
    out = []
    for i, label, description, fact, need in ACHIEVEMENTS:
        have = min(facts.get(fact, 0), need)
        out.append({"id": i, "label": label, "description": description, "earned": have >= need, "have": have, "need": need})
    return out


def goals(facts, count=3):
    """The three goals always in view: the unearned achievements that are closest to done (ties keep manifest order). Any order."""
    open_ = [a for a in view(facts) if not a["earned"]]
    open_.sort(key=lambda a: -a["have"] / a["need"])
    return open_[:count]
