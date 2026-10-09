"""Robot Script -- the interpreter.

`run(layout, prog)` is a pure function: the same layout and program always give the same Result. It never reads a clock or
a random source. It walks the program, applying room.step() for each action, and records one frame per action so the
page can play the run back, step it, or jump to the end.

A frame is a tuple (x, y, d, carry, parts, sockets, switches, at): the state tuple plus `at`, the address of the
instruction that made it (for example "main/2" or "main/1/2/0"), "" for the first frame.

Statuses: "cleared" (the list ended and every goal is met), "short" (the list ended, goals remain), "halt" (an action
could not be done; the robot stays where it was), "loop" (a safety stop after ACTION_LIMIT actions or TICK_LIMIT
control steps: it protects the page from a list that never ends and is not a resource the player spends).
"""

import dsl
import room

ACTION_LIMIT = 2000
TICK_LIMIT = 20000


class Result:
    def __init__(self, layout):
        self.layout = layout
        self.status = "short"
        self.message = ""
        self.frames = []
        self.actions = 0
        self.at = ""                 # the instruction that halted the run, when it halted
        self.state = layout.initial()
        self.goals = []

    @property
    def cleared(self):
        return self.status == "cleared"

    def final_goals(self):
        return room.goals(self.layout, self.state)


class _Stop(Exception):
    def __init__(self, status, message, at=""):
        Exception.__init__(self, message)
        self.status, self.message, self.at = status, message, at


def _address(path):
    return "/".join(str(p) for p in path)


def run(layout, prog, action_limit=ACTION_LIMIT):
    result = Result(layout)
    state = layout.initial()
    result.frames.append(state + ("",))
    ticks = [0]
    holder = [state]

    def tick():
        ticks[0] += 1
        if ticks[0] > TICK_LIMIT:
            raise _Stop("loop", "That list never finishes, so the robot stopped to be safe. Nothing is lost: change it and run again.")

    def do(action, path):
        tick()
        if result.actions >= action_limit:
            raise _Stop("loop", "That list kept going for %d actions without ending, so the robot stopped to be safe. Nothing is lost: change it and run again." % action_limit)
        result.actions += 1
        new, reason = room.step(layout, holder[0], action)
        if reason:
            raise _Stop("halt", "Step %d, %s: %s" % (result.actions, dsl.ACTION_NAMES[action].lower(), reason), _address(path))
        holder[0] = new
        result.frames.append(new + (_address(path),))

    def walk(items, path, routine):
        for index, stmt in enumerate(items):
            here = path + [index]
            if isinstance(stmt, str):
                do(stmt, here)
                continue
            kind = stmt[0]
            tick()
            if kind == "rep":
                for _ in range(stmt[1]):
                    walk(stmt[2], here + [2], routine)
            elif kind == "until":
                while not room.cond_holds(layout, holder[0], stmt[1]):
                    tick()
                    walk(stmt[2], here + [2], routine)
            elif kind == "if":
                if room.cond_holds(layout, holder[0], stmt[1]):
                    walk(stmt[2], here + [2], routine)
                else:
                    walk(stmt[3], here + [3], routine)
            else:
                name = stmt[1]
                walk(prog.get(name, []), [name], name)

    try:
        walk(prog.get("main", []), ["main"], "main")
        result.status = "cleared" if room.goals_met(layout, holder[0]) else "short"
    except _Stop as stop:
        result.status, result.message, result.at = stop.status, stop.message, stop.at
    result.state = holder[0]
    result.goals = room.goals(layout, holder[0])
    if result.status == "short":
        left = [g["label"] for g in result.goals if not g["met"]]
        result.message = "The list ended with the room unfinished. Still to do: " + "; ".join(x[0].lower() + x[1:] for x in left) + "."
    elif result.status == "cleared":
        result.message = "Room cleared."
    return result
