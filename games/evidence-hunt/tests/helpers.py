"""Shared by the whole-game tests: ways of playing a case through the engine's JSON entry point."""

import json

import casework as cw
import game
import lexicon as lx


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def solve_with_hints(limit=120):
    """Follow the hint ladder to the end of the current case."""
    for _ in range(limit):
        v = call(action="open")
        if v["result"]:
            return v
        for _i in range(3):
            call(action="hint")
        call(action="hint_do")
    raise AssertionError("did not finish")


def solve_thoroughly(cid):
    """A player who already knows who it is: pack the truth's own evidence, read it wherever the house does not fool it, then name it.
    This is how a guide page gets its evidence confirmed. Returns the final view."""
    call(action="pick", case=cid)
    call(action="restore")
    case = game.compiled(cid)
    for r in range(len(case.rooms)):
        call(action="go", room=r)
    if case.keep_room >= 0:
        call(action="go", room=case.keep_room)
        call(action="look")
    for s in range(case.n):
        if s:
            call(action="van")                       # a second trip for the second presence: it only lowers this replay's seal
        want = [e for e in sorted(lx.KIND_EVIDENCE[case.truth[s]]) if e in case.usable(s)][:case.kit_size]
        for e in want:
            call(action="pack", e=e)
        for r in case.slots[s]:
            call(action="go", room=r)
            for e in want:
                if case.reading(r, e) == cw.POSITIVE:
                    call(action="use", e=e)
    v = call(action="accuse", kinds=[lx.KIND_INDEX[k] for k in case.truth])
    assert v["result"], cid
    return v
