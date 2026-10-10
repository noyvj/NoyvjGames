"""Robot Script -- achievements (the hub-wide framework: a static manifest `achievements.json` plus `achievements_earned`
in the save). Everything is computed from facts about the player's progress, never stored separately, so a loaded save and a
played one can never disagree. All are reachable without luck, none is hidden, and none rewards time or how often you
come back. Every one has a number so the player can see how close they are.
"""

import rooms

TOTAL_ROOMS = len(rooms.ORDER)
TOTAL_CHAPTERS = len(rooms.CHAPTER_LIST)

# (id, label, description, fact, need, gate). Every room is open from the start, so the only gate left is SANDBOX: the
# "Tinkerer" goal is offered once the free sandbox is open. The gate is "" for every other achievement.
SANDBOX = "sandbox"
ACHIEVEMENTS = (
    ("first_light", "First Light", "Clear your first room.", "rooms", 1, ""),
    ("ten_down", "Ten Down", "Clear 10 rooms.", "rooms", 10, ""),
    ("chapter_closed", "Chapter Closed", "Clear every room of one chapter.", "chapters_done", 1, ""),
    ("halfway_there", "Halfway There", "Clear every room of 3 chapters.", "chapters_done", 3, ""),
    ("shift_done", "Shift Done", "Clear every room of every chapter.", "chapters_done", TOTAL_CHAPTERS, ""),
    ("fine_work", "Fine Work", "Earn 5 gold medals.", "gold", 5, ""),
    ("clockwork", "Clockwork", "Earn 20 gold medals.", "gold", 20, ""),
    ("perfect_script", "Perfect Script", "Earn a gold medal in every room.", "gold", TOTAL_ROOMS, ""),
    ("loop_the_loop", "Loop the Loop", "Clear a room with a repeat block.", "flag_rep", 1, ""),
    ("phone_a_friend", "Phone a Friend", "Clear a room by calling a routine.", "flag_call", 1, ""),
    ("two_minds", "Two Minds", "Clear a room with an if or until block.", "flag_branch", 1, ""),
    ("learned_from_a_bump", "Learned From a Bump", "Clear a room after a run that stopped short.", "flag_comeback", 1, ""),
    ("second_opinion", "Second Opinion", "Climb the whole hint ladder in one room: nudge, hint, answer.", "rung3", 1, ""),
    ("tinkerer", "Tinkerer", "Run 10 lists in the sandbox.", "sbx", 10, SANDBOX),
)

IDS = tuple(a[0] for a in ACHIEVEMENTS)


def earned(facts):
    """The ids earned right now, in manifest order."""
    return [i for i, _l, _d, fact, need, _c in ACHIEVEMENTS if facts.get(fact, 0) >= need]


def view(facts):
    out = []
    for i, label, description, fact, need, gate in ACHIEVEMENTS:
        have = min(facts.get(fact, 0), need)
        out.append({"id": i, "label": label, "description": description, "earned": have >= need,
                    "have": have, "need": need, "gate": gate})
    return out


def goals(facts, count=3, sandbox=False):
    """The next few achievements still to earn that can be worked on now (all of them, bar the sandbox one until the sandbox
    is open), in manifest order: the always-visible 'what to do next' list. They can be done in any order."""
    return [a for a in view(facts) if not a["earned"] and (sandbox or a["gate"] != SANDBOX)][:count]
