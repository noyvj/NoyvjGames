"""Mirror Lab -- the three-goals strip: the next three goals not yet done, from a fixed list, in any order, each with a bar. Every goal is a
number the player can already see on the page (benches cleared in a chapter, fewest-piece tags, shelf pages), so playing always counts toward
something visible. Pure functions of the cleared benches and the shelf pages used; nothing is timed and nothing can be missed."""

import benches
import logbook
import progress


def _chapter_goal(number, need, label, description):
    return ("ch%d-%d" % (number, need), label, description, lambda cleared, used: progress.chapter_cleared(cleared, number), need)


# (id, label, description, have(cleared, used), need): the order is the order they come up in.
GOALS = (
    _chapter_goal(1, 5, "Open Splitters", "Clear 5 benches in Flat Mirrors"),
    ("benches-10", "Ten benches", "Clear 10 benches", lambda cleared, used: len(cleared), 10),
    ("shelf-5", "Fill the shelf", "Use every kind of piece once", lambda cleared, used: len(used), len(logbook.SHELF)),
    _chapter_goal(1, 8, "Finish Flat Mirrors", "Clear all 8 benches in Flat Mirrors"),
    ("fewest-5", "Five tags", "Earn 5 Fewest pieces tags", lambda cleared, used: progress.fewest_tags(cleared), 5),
    _chapter_goal(2, 5, "Open Prisms", "Clear 5 benches in Splitters"),
    _chapter_goal(2, 8, "Finish Splitters", "Clear all 8 benches in Splitters"),
    ("benches-20", "Twenty benches", "Clear 20 benches", lambda cleared, used: len(cleared), 20),
    _chapter_goal(3, 5, "Open Filters and Decoys", "Clear 5 benches in Prisms"),
    _chapter_goal(3, 8, "Finish Prisms", "Clear all 8 benches in Prisms"),
    _chapter_goal(4, 5, "Open The Long Run", "Clear 5 benches in Filters and Decoys"),
    ("fewest-20", "Twenty tags", "Earn 20 Fewest pieces tags", lambda cleared, used: progress.fewest_tags(cleared), 20),
    _chapter_goal(4, 8, "Finish Filters and Decoys", "Clear all 8 benches in Filters and Decoys"),
    _chapter_goal(5, 8, "Finish The Long Run", "Clear all 8 benches in The Long Run"),
    ("benches-40", "Every bench", "Clear all %d benches" % len(benches.ALL_BENCHES), lambda cleared, used: len(cleared), len(benches.ALL_BENCHES)),
    ("fewest-40", "Every tag", "Earn the Fewest pieces tag on every bench", lambda cleared, used: progress.fewest_tags(cleared), len(benches.ALL_BENCHES)),
)
GOAL_IDS = tuple(g[0] for g in GOALS)


def all_goals(cleared, used):
    out = []
    for gid, label, description, have, need in GOALS:
        n = min(have(cleared, used), need)
        out.append({"id": gid, "label": label, "description": description, "have": n, "need": need, "done": n >= need})
    return out


def next_goals(cleared, used, count=3):
    """The first `count` goals not yet done, in list order. They can be worked on in any order."""
    return [g for g in all_goals(cleared, used) if not g["done"]][:count]


def summary(cleared, used):
    goals = all_goals(cleared, used)
    return {"done": sum(1 for g in goals if g["done"]), "total": len(goals)}
