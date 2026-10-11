"""Picture Grid -- the goals queue behind the always-visible "three goals" strip (shared/goals-panel.js shows the first three
that are not done, in any order the player likes). Every goal reads something the game already measures and shows: pictures hung
per gallery, pictures hung in all, cells filled. Nothing here is timed, random or hidden, and a goal that is done stays done
(the numbers only ever go up).

The queue lists the goals still to do first, one category after another in a fixed rhythm (the next gallery to open, the next
cell milestone, the gallery in hand, the next hung-total milestone), then the finished ones, so the three on show are always a
mix of "open the next gallery", "keep filling" and "finish this wall".
"""

import pictures

CELL_STEPS = (100, 500, 1000, 2500, 5000, 10000)
HANG_STEPS = (10, 30, 60)


def _goal(gid, label, current, target, reward=""):
    out = {"id": gid, "label": label, "current": min(current, target), "target": target, "done": current >= target}
    if reward:
        out["reward"] = reward
    return out


def queue(solved, cells):
    """The whole ordered queue (a list of dicts: id, label, current, target, done, reward?) for the hung set and cells filled."""
    total = len(pictures.ORDER)
    unlock, finish = [], []
    for g, gallery in enumerate(pictures.GALLERIES):
        if g > 0 and pictures.gallery_open(solved, g - 1):
            prev = pictures.GALLERIES[g - 1]
            need = min(pictures.OPEN_AT, len(prev["pictures"]))
            unlock.append(_goal("open-" + gallery["id"], "Hang %d pictures in %s" % (need, prev["name"]),
                                pictures.gallery_hung(solved, g - 1), need, "Opens " + gallery["name"]))
        if pictures.gallery_open(solved, g):
            finish.append(_goal("finish-" + gallery["id"], "Hang all %d pictures in %s" % (len(gallery["pictures"]), gallery["name"]),
                                pictures.gallery_hung(solved, g), len(gallery["pictures"])))
    cell_goals = [_goal("cells-%d" % step, "Fill %s cells" % format(step, ","), cells, step) for step in CELL_STEPS]
    hang_goals = [_goal("hung-%d" % step, "Hang %d pictures" % step, len(solved), step) for step in HANG_STEPS if step <= total]
    if total not in HANG_STEPS:
        hang_goals.append(_goal("hung-%d" % total, "Hang all %d pictures" % total, len(solved), total))
    lists = [unlock, cell_goals, finish, hang_goals]
    todo = [[g for g in lst if not g["done"]] for lst in lists]
    done = [g for lst in lists for g in lst if g["done"]]
    out = []
    for rank in range(max(len(t) for t in todo)):
        for t in todo:
            if rank < len(t):
                out.append(t[rank])
    return out + done
