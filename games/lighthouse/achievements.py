"""Lighthouse -- achievements (the hub-wide framework: a static manifest `achievements.json` plus
`achievements_earned` in the save). Each one is computed from the keep's meta counters and state, and once earned
it is remembered in meta so it stays earned. None is luck-gated and none can be lost.

The first group needs only the keeping of the light (Quiet mode reaches all of it); the second needs the story
layer. `STORY` marks the second group so a Quiet-mode player's 100% is the first group alone.
"""

import data
import lore
import mysteries

# (id, label, description, story, hidden): `hidden` ones show only "A mystery" until they are earned.
ACHIEVEMENTS = (
    ("first_light", "First Light", "Keep the light through your first night.", False, False),
    ("quiet_night", "Quiet Night", "End a night with no trouble at all: no incident, no damage, no ship turned back.", False, False),
    ("fog_bank", "Fog Bank", "Bring every ship through a night of long fog.", False, False),
    ("storm_warden", "Storm Warden", "Come through a storm with every part of the station above half.", False, False),
    ("tidy", "Tidy", "Repair every part of the station in a single day.", False, False),
    ("frugal", "Frugal", "Finish a season with the oil never below 20.", False, False),
    ("year_at_the_rock", "Year at the Rock", "Complete a year.", False, False),
    ("wound_tight", "Wound Tight", "Keep the clockwork turning for seven nights in a row.", False, False),
    ("fog_bell", "Fog Bell", "Build the fog bell.", False, False),
    ("nothing_happened", "Nothing Happened", "End a night with nothing in the log at all.", False, False),
    ("keeper_for_life", "Keeper for Life", "Keep the light on after the first year.", False, False),
    ("reading_by_lamplight", "Reading by Lamplight", "Read five letters.", True, False),
    ("whole_cast", "The Whole Cast", "Meet all ten of the people who write to the light.", True, False),
    ("good_neighbour", "A Good Neighbour", "Receive ten gifts.", True, False),
    ("bravery_optional", "Bravery is Optional", "Keep the light for a whole year with Eerie details switched off.", True, False),
    ("second_light", "Second Light", "Find out who kept the second light on the water.", True, True),
    ("square_to_the_floor", "Square to the Floor", "Find out why the chair kept turning.", True, True),
    ("the_drummer", "The Drummer", "Find out who was knocking at the cistern.", True, True),
    ("two_cups", "Two Cups", "Find out who left the second cup.", True, True),
    ("return_to_sender", "Return to Sender", "Find out who wrote the unsigned letters.", True, True),
    ("twelve_windows", "Twelve Windows", "Find out about the ship that is not on any chart.", True, True),
)
MYSTERY_ACHIEVEMENTS = {"second_light": "second_light", "chair": "square_to_the_floor", "cistern": "the_drummer", "extra_cup": "two_cups",
                        "unsigned": "return_to_sender", "wrong_ship": "twelve_windows"}


def _solved(keep, mid):
    final = mysteries.MYSTERIES[mid]["beats"][-1]["id"]
    return final in {b[0] for b in keep.story["beats"]} or mid in keep.meta["story"].get("solved", [])


def _checks(keep):
    m = keep.meta
    c = m["counters"]
    ever = m["story"]
    return {
        "first_light": m["nights_kept"] >= 1,
        "quiet_night": c.get("quiet_nights", 0) >= 1,
        "fog_bank": c.get("fog_clears", 0) >= 1,
        "storm_warden": c.get("storm_wardens", 0) >= 1,
        "tidy": c.get("tidy_days", 0) >= 1,
        "frugal": c.get("frugal_seasons", 0) >= 1,
        "year_at_the_rock": m["years"] >= 1,
        "wound_tight": c.get("best_wound_streak", 0) >= 7,
        "fog_bell": keep.has("bell"),
        "nothing_happened": c.get("empty_nights", 0) >= 1,
        "keeper_for_life": keep.mode == "endless",
        "reading_by_lamplight": len(ever["letters"]) >= 5,
        "whole_cast": len(ever["met"]) >= len(lore.SAILORS),
        "good_neighbour": len(ever["gifts"]) >= 10,
        "bravery_optional": c.get("eerie_off_streak", 0) >= data.NIGHTS_PER_YEAR,
        **{ach: mid in ever["mysteries"] and _solved(keep, mid) for mid, ach in MYSTERY_ACHIEVEMENTS.items()},
    }


def refresh(keep):
    """Remember anything newly earned. Returns the ids that are new."""
    have = set(keep.meta["achievements_earned"])
    checks = _checks(keep)
    new = [a[0] for a in ACHIEVEMENTS if checks.get(a[0]) and a[0] not in have]
    keep.meta["achievements_earned"].extend(new)
    return new


def earned_ids(keep):
    have = set(keep.meta["achievements_earned"])
    return [a[0] for a in ACHIEVEMENTS if a[0] in have]


def view(keep):
    have = set(keep.meta["achievements_earned"])
    out = []
    for i, label, desc, story, hidden in ACHIEVEMENTS:
        earned = i in have
        if hidden and not earned:
            label, desc = "A mystery", "Solve one of the odd happenings. Which one is for you to find out."
        out.append({"id": i, "label": label, "description": desc, "earned": earned, "story": story, "hidden": hidden and not earned})
    return out


def manifest():
    return {"achievements": [{"id": i, "label": label, "description": desc} for i, label, desc, _s, _h in ACHIEVEMENTS]}
