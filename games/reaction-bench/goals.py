"""Reaction Bench -- the goals queue behind the always-visible "three goals" strip (shared/goals-panel.js shows the first three that are
not done, in any order the player likes). Every goal reads a number the page already shows: orders shelved per chapter, compounds
shelved in all, elements found, dial turns. Nothing here is timed, random or hidden, and a goal that is done stays done (the numbers
only ever go up).

The queue lists the goals still to do first, one category after another in a fixed rhythm (the next chapter to open, the next table
milestone, the chapter in hand, the next shelf milestone, the next dial-turn milestone), then the finished ones.
"""

import reactions

ELEMENT_STEPS = (5, 10)
SHELF_STEPS = (10, 20, 30)
TURN_STEPS = (100, 500, 2000)


def _goal(gid, label, current, target, reward=""):
    out = {"id": gid, "label": label, "current": min(current, target), "target": target, "done": current >= target}
    if reward:
        out["reward"] = reward
    return out


def queue(shelf, elements_found, turns):
    """The whole ordered queue (dicts: id, label, current, target, done, reward?) for the shelf, the elements lit and the dial turns."""
    total = len(reactions.ALL)
    bench = len(reactions.BENCH_ELEMENTS)
    unlock, finish = [], []
    for ci, chapter in enumerate(reactions.CHAPTERS):
        if ci > 0 and reactions.chapter_open(shelf, ci - 1):
            prev = reactions.CHAPTERS[ci - 1]
            need = reactions.chapter_need(ci - 1)
            unlock.append(_goal("open-" + chapter["id"], "Shelve %d orders in %s" % (need, prev["name"]),
                                reactions.chapter_shelved(shelf, ci - 1), need, "Opens " + chapter["name"]))
        if reactions.chapter_open(shelf, ci):
            n = len(chapter["reactions"])
            finish.append(_goal("finish-" + chapter["id"], "Shelve all %d orders in %s" % (n, chapter["name"]),
                                reactions.chapter_shelved(shelf, ci), n))
    tiles = [_goal("tiles-%d" % step, "Light %d tiles of the periodic table" % step, elements_found, step) for step in ELEMENT_STEPS if step < bench]
    tiles.append(_goal("tiles-all", "Light all %d bench tiles" % bench, elements_found, bench))
    shelved = [_goal("shelved-%d" % step, "Shelve %d compounds" % step, len(shelf), step) for step in SHELF_STEPS if step < total]
    shelved.append(_goal("shelved-all", "Shelve all %d compounds" % total, len(shelf), total))
    turned = [_goal("turns-%d" % step, "Turn the dials %s times" % format(step, ","), turns, step) for step in TURN_STEPS]
    lists = [unlock, tiles, finish, shelved, turned]
    todo = [[g for g in lst if not g["done"]] for lst in lists]
    done = [g for lst in lists for g in lst if g["done"]]
    out = []
    for rank in range(max(len(t) for t in todo)):
        for t in todo:
            if rank < len(t):
                out.append(t[rank])
    return out + done
