"""Stranded -- exploring the graph: what can be reached at all (proved by search over every state), the route to a scene using
only choices already tried, the nearest loose end, and the what-if peek. All pure functions of the walker."""

import kit
import story
import walker


def _exact_stats():
    """Stats that some condition tests with 'below' (a ceiling): those must be tracked exactly. The others are only ever tested
    with 'at least', so a state with higher values of them can do everything a lower one can (the search keeps only the best)."""
    out = set()
    for scene in story.SCENES.values():
        conds = [c["need"] for c in scene["choices"]] + [cond for c in scene["choices"] for cond, _t in c["to"]]
        conds += [cond for cond, _t in scene["lines"]] + [cond for c in scene["choices"] for cond, _t in c["reply"]]
        for cond in conds:
            if cond:
                out.update(kit.STATS.index(s) for s in cond["max"])
    return out


EXACT = _exact_stats()
LOOSE = [i for i in range(3) if i not in EXACT]


def search(allowed=None, limit=400000):
    """Breadth-first search over (scene, stats, flags) from the start. `allowed` is a set of (scene, choice, target) edges the
    search may use (None = every edge). A state is skipped when another state with the same scene, flags and exact stats has at least as
    much of every other stat (it could do anything the skipped one could). Returns {'parent': {state: (previous state, choice
    number)}, 'order': [states]}; each state's path from the start is recovered by walking `parent`."""
    start, _found = walker.initial()
    parent = {start: None}
    order = [start]
    best = {}
    head = 0

    def fresh(state):
        key = (state[0], state[2], tuple(state[1][i] for i in EXACT))
        mine = tuple(state[1][i] for i in LOOSE)
        frontier = best.setdefault(key, [])
        for other in frontier:
            if all(a >= b for a, b in zip(other, mine)):
                return False
        frontier[:] = [o for o in frontier if not all(a >= b for a, b in zip(mine, o))] + [mine]
        return True

    fresh(start)
    while head < len(order) and len(order) < limit:
        state = order[head]
        head += 1
        scene = story.SCENES[state[0]]
        for i in range(len(scene["choices"])):
            nxt, _info = walker.step(state, i)
            if nxt is None or nxt in parent:
                continue
            if allowed is not None and (state[0], i, nxt[0]) not in allowed:
                continue
            if not fresh(nxt):
                continue
            parent[nxt] = (state, i)
            order.append(nxt)
    return {"parent": parent, "order": order}


def path_of(result, state):
    out = []
    parent = result["parent"]
    while parent[state] is not None:
        state, i = parent[state]
        out.append(str(i))
    return "".join(reversed(out))


def reach_all():
    """Everything the story can ever show: scenes, choices that can be taken, endings, collectables, with one witness path each."""
    result = search()
    scenes, edges, found = {}, {}, {}
    for state in result["order"]:
        scenes.setdefault(state[0], state)
        scene = story.SCENES[state[0]]
        for i in range(len(scene["choices"])):
            if walker.available(state, i)[0]:
                edges.setdefault((state[0], i, walker.destination(state, i)), state)
    for sid, state in scenes.items():
        steps = walker.replay(path_of(result, state))
        for item in steps[2]:
            found.setdefault(item, path_of(result, state))
    for edge, state in edges.items():
        path = path_of(result, state) + str(edge[1])
        for item in walker.replay(path)[2]:
            found.setdefault(item, path)
    endings = {story.SCENES[s]["end"]: path_of(result, st) for s, st in scenes.items() if story.SCENES[s]["end"]}
    return {"scenes": {s: path_of(result, st) for s, st in scenes.items()},
            "edges": {e: path_of(result, st) for e, st in edges.items()},
            "endings": endings, "found": found, "states": len(result["order"])}


def route_to(taken, target):
    """A path of choice numbers from the start that reaches scene `target` using only edges in `taken` (a set of (scene,
    choice, target) triples). None when there is none."""
    result = search(allowed=set(taken))
    for state in result["order"]:
        if state[0] == target:
            return path_of(result, state)
    return None


def _tried_choices(taken):
    return {(e[0], e[1]) for e in taken}


def loose_end(taken, path):
    """The nearest untried edge. First along the current run (newest first), so rewinding is enough; then anywhere reachable
    through edges already tried. Returns None when every edge that can be walked has been, else
    {'kind': 'rewind', 'step': n, 'scene': id, 'choice': i} or {'kind': 'route', 'path': str, 'scene': id, 'choice': i} or
    {'kind': 'locked', 'scene': id, 'choice': i, 'path': str, 'why': text} (a reply that is shut in every state reached so far)."""
    steps = walker.replay(path)
    steps = steps[0] if steps else []
    states = [s["before"] for s in steps]
    final = steps[-1]["after"] if steps else walker.initial()[0]
    states.append(final)
    for n in range(len(states) - 1, -1, -1):
        state = states[n]
        for i in range(len(story.SCENES[state[0]]["choices"])):
            if walker.available(state, i)[0] and (state[0], i, walker.destination(state, i)) not in taken:
                return {"kind": "rewind", "step": n, "scene": state[0], "choice": i}
    result = search(allowed=set(taken))
    tried = _tried_choices(taken)
    locked = None
    for state in result["order"]:
        for i in range(len(story.SCENES[state[0]]["choices"])):
            ok, why = walker.available(state, i)
            if ok:
                if (state[0], i, walker.destination(state, i)) not in taken:
                    return {"kind": "route", "path": path_of(result, state), "scene": state[0], "choice": i}
            elif (state[0], i) not in tried and locked is None:
                locked = {"kind": "locked", "scene": state[0], "choice": i, "path": path_of(result, state), "why": why}
    return locked


def peek(state, taken):
    """The what-if peek for the scene the player is in. Open once two different choices of this scene have been tried. For each
    choice: where it would lead from this exact state (day and title; an ending is only called 'an ending') or why it is locked."""
    scene = story.SCENES[state[0]]
    done = _tried_choices(taken)
    tried = [i for i in range(len(scene["choices"])) if (state[0], i) in done]
    if len(tried) < 2:
        return {"open": False, "need": 2 - len(tried), "rows": []}
    rows = []
    for i, choice in enumerate(scene["choices"]):
        ok, why = walker.available(state, i)
        if not ok:
            rows.append({"i": i, "tried": i in tried, "locked": why, "to": ""})
            continue
        target = story.SCENES[walker.destination(state, i)]
        label = "an ending" if target["end"] else "Day %d: %s" % (target["day"], target["title"])
        rows.append({"i": i, "tried": i in tried, "locked": "", "to": label})
    return {"open": True, "need": 0, "rows": rows}
