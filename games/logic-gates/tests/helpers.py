"""Builders shared by the tests: drive the engine only through handle(), like the page does."""

import json

import game
import levels


def call(action, **fields):
    return json.loads(game.handle(json.dumps(dict(fields, action=action))))


def fresh():
    call("reset")
    return call("open")


def build(circuit):
    """Put a circuit on the open board with add/wire actions. Chip ids are handed out 1, 2, 3 ... in order."""
    for chip in circuit["chips"]:
        v = call("add", type=chip["type"])
        assert not v["note"], v["note"]
    for dest, src in circuit["wires"].items():
        v = call("wire", dest=dest, src=src)
        assert "loop" not in v["note"] and "exist" not in v["note"], (dest, src, v["note"])
    return call("open")


def solve(level_id):
    """Open a level and build its reference solution. Returns the view."""
    v = call("start", level=level_id)
    assert v["level"]["id"] == level_id, v["note"]
    lv = levels.BY_ID[level_id]
    call("clear")
    return build(lv["ref"])


def solve_all():
    solved = set()
    while len(solved) < 40:
        progress = False
        for lv in levels.LEVELS:
            if lv["id"] in solved:
                continue
            if not levels.is_open(lv, solved):
                continue
            v = solve(lv["id"])
            assert v["table"]["ok"], (lv["id"], v["table"]["message"])
            solved.add(lv["id"])
            progress = True
        assert progress
    return call("open")
