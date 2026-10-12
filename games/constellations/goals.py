"""Constellations -- the goals queue behind the always-visible "three goals" strip (shared/goals-panel.js shows the first three that
are not done, in any order the player likes). Every goal reads something the game already measures and shows: constellations found per
season, constellations found in all, lines drawn. Nothing here is timed, random or hidden, and a goal that is done stays done (the
numbers only ever go up).

The queue lists the goals still to do first, one category after another in a fixed rhythm (the next season to open, the next
lines-drawn milestone, the season in hand, the next total-found milestone), then the finished ones, so the three on show are always a
mix of "open the next page", "keep drawing" and "finish this page".
"""

import charts

LINE_STEPS = (50, 250, 1000, 2500, 5000)
FOUND_STEPS = (10, 25)


def _goal(gid, label, current, target, reward=""):
    out = {"id": gid, "label": label, "current": min(current, target), "target": target, "done": current >= target}
    if reward:
        out["reward"] = reward
    return out


def queue(solved, draws):
    """The whole ordered queue (a list of dicts: id, label, current, target, done, reward?) for the finished set and lines drawn."""
    total = len(charts.ORDER)
    unlock, finish = [], []
    for s, season in enumerate(charts.SEASONS):
        if s > 0 and charts.season_open(solved, s - 1):
            prev = charts.SEASONS[s - 1]
            need = charts.season_need(s)
            unlock.append(_goal("open-" + season["id"], "Find %d constellations in %s" % (need, prev["name"]),
                                charts.season_done(solved, s - 1), need, "Opens " + season["name"]))
        if charts.season_open(solved, s):
            finish.append(_goal("finish-" + season["id"], "Find all %d in %s" % (len(season["charts"]), season["name"]),
                                charts.season_done(solved, s), len(season["charts"])))
    line_goals = [_goal("lines-%d" % step, "Draw %s lines" % format(step, ","), draws, step) for step in LINE_STEPS]
    found_goals = [_goal("found-%d" % step, "Find %d constellations" % step, len(solved), step) for step in FOUND_STEPS if step < total]
    found_goals.append(_goal("found-%d" % total, "Find all %d constellations" % total, len(solved), total))
    lists = [unlock, line_goals, finish, found_goals]
    todo = [[g for g in lst if not g["done"]] for lst in lists]
    done = [g for lst in lists for g in lst if g["done"]]
    out = []
    for rank in range(max(len(t) for t in todo)):
        for t in todo:
            if rank < len(t):
                out.append(t[rank])
    return out + done
