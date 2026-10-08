"""Lighthouse -- achievements (the hub-wide framework: a static manifest `achievements.json` plus
`achievements_earned` in the save). Each one is computed from the keep's meta counters and state, and once earned
it is remembered in meta so it stays earned. None is luck-gated and none can be lost.

The first group needs only the keeping of the light (Quiet mode reaches all of it); the second needs the story
layer. `STORY` marks the second group so a Quiet-mode player's 100% is the first group alone.
"""

# (id, label, description, story)
ACHIEVEMENTS = (
    ("first_light", "First Light", "Keep the light through your first night.", False),
    ("quiet_night", "Quiet Night", "End a night with no trouble at all: no incident, no damage, no ship turned back.", False),
    ("fog_bank", "Fog Bank", "Bring every ship through a night of long fog.", False),
    ("storm_warden", "Storm Warden", "Come through a storm with every part of the station above half.", False),
    ("tidy", "Tidy", "Repair every part of the station in a single day.", False),
    ("frugal", "Frugal", "Finish a season with the oil never below 20.", False),
    ("year_at_the_rock", "Year at the Rock", "Complete a year.", False),
    ("wound_tight", "Wound Tight", "Keep the clockwork turning for seven nights in a row.", False),
    ("fog_bell", "Fog Bell", "Build the fog bell.", False),
    ("nothing_happened", "Nothing Happened", "End a night with nothing in the log at all.", False),
    ("keeper_for_life", "Keeper for Life", "Keep the light on after the first year.", False),
)


def _checks(keep):
    m = keep.meta
    c = m["counters"]
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
    }


def refresh(keep):
    """Remember anything newly earned. Returns the ids that are new."""
    have = set(keep.meta["achievements_earned"])
    new = [a[0] for a in ACHIEVEMENTS if _checks(keep).get(a[0]) and a[0] not in have]
    keep.meta["achievements_earned"].extend(new)
    return new


def earned_ids(keep):
    have = set(keep.meta["achievements_earned"])
    return [a[0] for a in ACHIEVEMENTS if a[0] in have]


def view(keep):
    have = set(keep.meta["achievements_earned"])
    return [{"id": i, "label": label, "description": desc, "earned": i in have, "story": story}
            for i, label, desc, story in ACHIEVEMENTS]
