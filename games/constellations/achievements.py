"""Constellations -- achievements (the hub-wide framework: a static manifest `achievements.json` plus `achievements_earned` in the save).

Everything is computed from facts about the player's progress (the finished set, the hint record and the tally of lines drawn), never
stored separately, so a loaded save and a played one can never disagree and the saved list is a write-only projection that load never
reads back. All fourteen are reachable by plain play on any difficulty (the level only changes how the suggestion ladder opens and no
achievement reads it), none is hidden, none is timed or luck-based, and every one shows a number so the player can see how close they
are. The one that is about asking for no help ("No Hints Needed") counts finished charts whose record holds no suggestion at all, and
is earned simply by finishing ten charts without pressing the suggestion button. The season names and sizes are read from the chart
set that really exists, so the achievements always match the 40 charts and 5 seasons in the game.

Names stay hidden (core constraint 7): a chart's name and meaning appear only once it is finished, and the achievement list is part of the
view, so the three achievements about particular constellations are worded by what the player will see, never by name. The plan called
them "The Hunter" (Orion), "The Bears" (Ursa Major and Minor) and "Southern Cross" (Crux): "The Hunter" is Orion's meaning and "Southern
Cross" gives Crux away, so they are "Belt and Sword" and "Smallest of All" (Crux is the smallest of the 88), and "The Bears" stays. The ids
keep the plan's names. A test checks that no achievement text names, or gives the meaning of, any constellation. Nothing here reads a
clock or a random source.
"""

import charts

TOTAL = len(charts.ORDER)
SEASON_SIZE = [len(s["charts"]) for s in charts.SEASONS]
SEASON_NAME = [s["name"] for s in charts.SEASONS]
CLEAN_NEED = 10
LINES_NEED = 500
BEARS = ("ursa-major", "ursa-minor")          # the Great Bear and the Little Bear
HUNTER = "orion"
CROSS = "crux"                                # the Southern Cross

# (id, label, description, fact, need). A season fact is "sea<index>", counting the charts found in that season.
ACHIEVEMENTS = (
    ("first_figure", "First Figure", "Find your first constellation.", "found", 1),
    ("ten_figures", "Ten Figures", "Find 10 constellations.", "found", 10),
    ("twenty_figures", "Twenty Figures", "Find 20 constellations.", "found", 20),
    ("forty_figures", "Forty Figures", "Find every constellation.", "found", TOTAL),
    ("winter_done", "Winter Done", "Find all %d constellations in %s." % (SEASON_SIZE[0], SEASON_NAME[0]), "sea0", SEASON_SIZE[0]),
    ("spring_done", "Spring Done", "Find all %d constellations in %s." % (SEASON_SIZE[1], SEASON_NAME[1]), "sea1", SEASON_SIZE[1]),
    ("summer_done", "Summer Done", "Find all %d constellations in %s." % (SEASON_SIZE[2], SEASON_NAME[2]), "sea2", SEASON_SIZE[2]),
    ("autumn_done", "Autumn Done", "Find all %d constellations in %s." % (SEASON_SIZE[3], SEASON_NAME[3]), "sea3", SEASON_SIZE[3]),
    ("southern_done", "Southern Done", "Find all %d constellations in %s." % (SEASON_SIZE[4], SEASON_NAME[4]), "sea4", SEASON_SIZE[4]),
    ("the_hunter", "Belt and Sword", "Find the winter constellation with a belt of three bright stars in a row.", "hunter", 1),
    ("the_bears", "The Bears", "Find both bears of the spring sky, one large and one small.", "bears", len(BEARS)),
    ("southern_cross", "Smallest of All", "Find the smallest constellation of all, a cross of four stars low in the southern sky.", "cross", 1),
    ("no_hints_needed", "No Hints Needed", "Find %d constellations without asking for a suggestion." % CLEAN_NEED, "clean", CLEAN_NEED),
    ("long_night", "Long Night", "Draw %d lines." % LINES_NEED, "lines", LINES_NEED),
)

IDS = tuple(a[0] for a in ACHIEVEMENTS)
FACTS = ("found", "hunter", "bears", "cross", "clean", "lines") + tuple("sea%d" % s for s in range(len(SEASON_SIZE)))


def facts_of(solved, hinted, draws):
    """The numbers the achievements read: `solved` (finished chart ids), `hinted` (chart id -> highest rung asked while it was first being
    solved) and `draws`, the tally of lines the player drew."""
    out = {"found": len(solved), "lines": draws, "hunter": 1 if HUNTER in solved else 0, "cross": 1 if CROSS in solved else 0}
    out["bears"] = sum(1 for cid in BEARS if cid in solved)
    out["clean"] = sum(1 for cid in solved if not hinted.get(cid))
    for s in range(len(SEASON_SIZE)):
        out["sea%d" % s] = charts.season_done(solved, s)
    return out


def earned(facts):
    """The ids earned right now, in manifest order."""
    return [i for i, _l, _d, fact, need in ACHIEVEMENTS if facts.get(fact, 0) >= need]


def view(facts):
    out = []
    for i, label, description, fact, need in ACHIEVEMENTS:
        have = min(facts.get(fact, 0), need)
        out.append({"id": i, "label": label, "description": description, "earned": have >= need, "have": have, "need": need})
    return out
