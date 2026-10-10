"""Stranded -- the walker: a pure, deterministic graph walker. A state is (scene id, (trust, supplies, hope), sorted flags);
a step takes one choice number and returns the next state plus what happened. There is no clock and no random source, so the
same list of choice numbers always gives the same state: that is what makes rewinding exact."""

import kit
import story

START = story.START


def initial():
    """The state at the very start, with the first scene's own arrival effects applied. Returns (state, found)."""
    return _arrive(("", kit.START_STATS, ()), story.SCENES[START])


def holds(cond, state):
    if cond is None:
        return True
    stats, flags = state[1], state[2]
    for name in cond["all"]:
        if name not in flags:
            return False
    for name in cond["none"]:
        if name in flags:
            return False
    for stat, need in cond["min"].items():
        if stats[kit.STATS.index(stat)] < need:
            return False
    for stat, limit in cond["max"].items():
        if stats[kit.STATS.index(stat)] >= limit:
            return False
    return True


def reason(cond, state):
    """Why a choice is locked, in words the player sees (empty when it is open)."""
    if cond is None or holds(cond, state):
        return ""
    stats, flags = state[1], state[2]
    bits = []
    for name in cond["all"]:
        if name not in flags:
            bits.append(story.FLAG_NEED.get(name, "Needs " + name))
    for name in cond["none"]:
        if name in flags:
            bits.append(story.FLAG_NOT.get(name, "Not after " + name))
    for stat, need in cond["min"].items():
        have = stats[kit.STATS.index(stat)]
        if have < need:
            bits.append("Needs %s %d (you have %d)" % (stat.capitalize(), need, have))
    for stat, limit in cond["max"].items():
        have = stats[kit.STATS.index(stat)]
        if have >= limit:
            bits.append("Only when %s is below %d (you have %d)" % (stat.capitalize(), limit, have))
    return "; ".join(bits)


def visible(lines, state):
    """The lines of a scene or a reply that show for this state, as plain strings."""
    return [text for cond, text in lines if holds(cond, state)]


def _clamp(value):
    return max(kit.LOW, min(kit.HIGH, value))


def _apply(state, fx, set_, get_, found):
    stats = tuple(_clamp(s + d) for s, d in zip(state[1], fx))
    flags = tuple(sorted(set(state[2]) | set(set_)))
    for item in get_:
        if item not in found:
            found.append(item)
    return (state[0], stats, flags)


def _arrive(state, scene):
    found = []
    state = (scene["id"], state[1], state[2])
    state = _apply(state, scene["fx"], scene["set"], scene["get"], found)
    return state, found


def scene_of(state):
    return story.SCENES[state[0]]


def available(state, idx):
    """-> (ok, why). Out of range, or locked by a stat or flag."""
    choices = scene_of(state)["choices"]
    if not isinstance(idx, int) or isinstance(idx, bool) or not 0 <= idx < len(choices):
        return False, "There is no such reply."
    why = reason(choices[idx]["need"], state)
    return (not why), why


def destination(state, idx):
    """The scene id choice idx leads to from this state (after its own effects), without changing anything."""
    choice = scene_of(state)["choices"][idx]
    after = _apply(state, choice["fx"], choice["set"], (), [])
    for cond, target in choice["to"]:
        if holds(cond, after):
            return target
    return choice["to"][-1][1]


def step(state, idx):
    """Take choice idx. Returns (new state, info) or (None, info) when it is not allowed."""
    ok, why = available(state, idx)
    if not ok:
        return None, {"why": why}
    choice = scene_of(state)["choices"][idx]
    found = []
    mid = _apply(state, choice["fx"], choice["set"], choice["get"], found)
    target = choice["to"][-1][1]
    for cond, tgt in choice["to"]:
        if holds(cond, mid):
            target = tgt
            break
    reply = visible(choice["reply"], mid)
    after, found2 = _arrive(mid, story.SCENES[target])
    delta = tuple(b - a for a, b in zip(state[1], after[1]))
    return after, {"reply": reply, "found": found + found2, "from": state[0], "choice": idx, "delta": delta}


def replay(path):
    """Replay a string of choice numbers from the start. Returns (steps, final state, found-per-run) or None when any step is
    not allowed. steps[i] = {'before': state, 'idx': n, 'info': {...}, 'after': state}."""
    state, found = initial()
    steps = []
    got = list(found)
    for ch in path:
        if not ch.isdigit():
            return None
        nxt, info = step(state, int(ch))
        if nxt is None:
            return None
        steps.append({"before": state, "idx": int(ch), "info": info, "after": nxt})
        got += info["found"]
        state = nxt
    return steps, state, got
