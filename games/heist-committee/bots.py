"""Heist Committee -- plan builders used by the text harness, the balance tests and the bot playtests.
Nothing here is shown to the player: the player always builds their own plan."""

from engine import LANES, empty_plan, roll


def _skill(content, crew_id, skill):
    return content.crew[crew_id]["skills"].get(skill, 0)


def _free(plan, lane, start, dur):
    return all(plan["lanes"][lane][b] is None for b in range(start, start + dur))


def _best_lane(content, crew_ids, skill, taken, plan, start, dur):
    best, best_score = None, None
    for lane in range(LANES):
        if lane in taken or not _free(plan, lane, start, dur):
            continue
        score = _skill(content, crew_ids[lane], skill)
        if best is None or score > best_score:
            best, best_score = lane, score
    return best


def scouted_kinds(content, target_id, limit=3):
    """The kinds of trouble scouting reveals first: the heaviest-weighted complications in the target's pool."""
    target = content.targets[target_id]
    pool = sorted((content.complications[c] for c in target["pool"]), key=lambda c: -c.get("weight", 1))
    kinds = []
    for comp in pool:
        for kind in comp.get("kinds", []):
            if kind in target["cover_options"] and kind not in kinds:
                kinds.append(kind)
    return kinds[:limit]


def greedy_plan(content, target_id, crew_ids, standby=True, optional=False, kinds=None):
    """Fill the plan requirement by requirement with the best-skilled free crew member; a Lookout covers every
    action that needs a clear corridor; leftover lanes stand by for the target's scouted kinds."""
    target = content.targets[target_id]
    n = len(target["beats"])
    plan = empty_plan(n)
    done_at = {}
    for req in target["requirements"]:
        if req.get("optional") and not optional:
            continue
        lo, hi = req["window"]
        start = max(lo - 1, max([done_at[d] + 1 for d in req.get("needs_done", []) if d in done_at] or [0]))
        placed = False
        for action_id in req["actions"]:
            action = content.actions[action_id]
            dur = action["duration"]
            for s in range(start, hi):
                if s + dur > n:
                    break
                lane = _best_lane(content, crew_ids, action["skill"], set(), plan, s, dur)
                if lane is None:
                    continue
                helper = None
                if action.get("needs"):
                    helper = _best_lane(content, crew_ids, "watch", {lane}, plan, s, 1)
                    if helper is None:
                        continue
                plan["lanes"][lane][s] = action_id
                if helper is not None:
                    for k in range(dur):
                        if _free(plan, helper, s + k, 1):
                            plan["lanes"][helper][s + k] = "lookout"
                done_at[req["id"]] = s + dur - 1
                placed = True
                break
            if placed:
                break
    if standby:
        kinds = list(kinds or target.get("cover_options", []))[:3]
        for lane in range(LANES):
            for b in range(n):
                if plan["lanes"][lane][b] is None and kinds and b >= 1:
                    plan["lanes"][lane][b] = "standby:" + kinds[(lane + b) % len(kinds)]
    return plan


def random_plan(content, target_id, crew_ids, seed):
    """A plan made by dice: every cell is a random action (or empty)."""
    target = content.targets[target_id]
    n = len(target["beats"])
    plan = empty_plan(n)
    options = [a for a in content.actions if a not in ("wait", "standby")] + [None, None, None]
    for lane in range(LANES):
        for b in range(n):
            pick = options[int(roll(seed, "rp", lane, b) * len(options))]
            plan["lanes"][lane][b] = pick
    return plan
