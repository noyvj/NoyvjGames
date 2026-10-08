"""Heist Committee -- achievements (the hub-wide framework: a static manifest `achievements.json` plus
`achievements_earned` in the save). Everything is computed from the career meta, never stored on its own, so a loaded
save and a played one can never disagree. All fourteen are reachable without luck and none is hidden (easy to 100%)."""

ACHIEVEMENTS = (
    ("first_job", "First Job", "Finish any heist."),
    ("nobody_saw", "Nobody Saw Anything", "Finish a job without setting off an alarm."),
    ("chain_reaction", "Chain Reaction", "See a chain of five events, each caused by the last."),
    ("absorbed", "Absorbed", "Absorb three pieces of trouble in a single job, with Standby, skills, gear or traits."),
    ("old_rivals", "Old Rivals", "Make friends of two crew members who started out as rivals."),
    ("everyone_home", "Everyone Home", "Get away with the prize and nobody sidelined."),
    ("full_house", "Full House", "Finish a job with one of each role in the crew."),
    ("cat_job", "The Cat Job", "Meet the cat on every target."),
    ("paid_in_cheese", "Paid in Cheese", "Get away with the Grand Reserve wheel."),
    ("over_planner", "Over-Planner", "Finish a job with every cell of the timeline filled."),
    ("minimalist", "Minimalist", "Get away with the prize with no more than three people working in any one beat."),
    ("fifth_time_lucky", "Fifth Time Lucky", "Retry the same job five times."),
    ("rich_and_infamous", "Rich and Infamous", "Reach a reputation of 20."),
    ("committee_meeting", "Committee Meeting", "Meet twenty different kinds of trouble."),
)

CAT_COMPLICATION = "cat_in_gallery"
RICH_REPUTATION = 20
MEETING_COMPLICATIONS = 20
CHEESE_TARGET = "the_affineur"


def earned(meta, content):
    """The ids earned right now, in manifest order."""
    got = set()
    flags = set(meta.get("flags", []))
    if meta.get("jobs_done", 0) >= 1:
        got.add("first_job")
    if meta.get("jobs_clean", 0) >= 1:
        got.add("nobody_saw")
    if meta.get("best", {}).get("chain_links", 0) >= 5:
        got.add("chain_reaction")
    if meta.get("best", {}).get("absorbed", 0) >= 3:
        got.add("absorbed")
    for key, kind in meta.get("relationships", {}).items():
        a, b = key.split("|")
        if kind == "friends" and a in content.crew and b in content.crew:
            if b in content.crew[a].get("rival_of", []) or a in content.crew[b].get("rival_of", []):
                got.add("old_rivals")
    for flag, ach in (("everyone_home", "everyone_home"), ("full_house", "full_house"), ("over_planner", "over_planner"),
                      ("minimalist", "minimalist")):
        if flag in flags:
            got.add(ach)
    if set(content.target_order) <= set(meta.get("cat_targets", [])):
        got.add("cat_job")
    if CHEESE_TARGET in meta.get("finished_targets", []):
        got.add("paid_in_cheese")
    if max(list(meta.get("retries", {}).values()) or [0]) >= 5:
        got.add("fifth_time_lucky")
    if meta.get("reputation", 0) >= RICH_REPUTATION:
        got.add("rich_and_infamous")
    if len(meta.get("seen_complications", [])) >= MEETING_COMPLICATIONS:
        got.add("committee_meeting")
    return [a[0] for a in ACHIEVEMENTS if a[0] in got]


def view(meta, content):
    have = set(earned(meta, content))
    return [{"id": i, "label": label, "description": desc, "earned": i in have} for i, label, desc in ACHIEVEMENTS]


def job_flags(content, crew_ids, outcome):
    """Which one-off flags a finished job earns (stored in meta.flags)."""
    flags = []
    if len({content.crew[c]["role"] for c in crew_ids}) == 5:
        flags.append("full_house")
    if outcome["cells_used"] == outcome["cells_total"]:
        flags.append("over_planner")
    if outcome["escaped"] and outcome["max_actions_in_a_beat"] <= 3:
        flags.append("minimalist")
    if outcome["escaped"] and not outcome["sidelined"]:
        flags.append("everyone_home")
    return flags
