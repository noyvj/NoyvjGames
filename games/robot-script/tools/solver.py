"""Dev-only breadth-first solver: the fewest actions (flat, no loops) that clear a layout.

Used by the tests to check that the par of every flat room is the true minimum, so that gold is honest. It shares
room.step with the interpreter, so the two cannot disagree. Not loaded by the page.
"""

import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import room  # noqa: E402

ACTIONS = ("F", "L", "R", "G", "P", "S")


def shortest(layout, allow=ACTIONS, limit=200000):
    """Return the shortest action string that clears the layout, or None."""
    start = layout.initial()
    if room.goals_met(layout, start):
        return ""
    seen = {start}
    queue = deque([(start, "")])
    while queue and len(seen) < limit:
        state, path = queue.popleft()
        for action in allow:
            new, reason = room.step(layout, state, action)
            if reason or new in seen:
                continue
            seen.add(new)
            if room.goals_met(layout, new):
                return path + action
            queue.append((new, path + action))
    return None
