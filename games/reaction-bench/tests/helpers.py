"""Shared helpers for the game-level tests."""

import json

import game
import reactions


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def solve(rid):
    """Play an order the way a person would: choose the right list if it is a round, set every dial, run."""
    r = reactions.BY_ID[rid]
    call(action="pick", reaction=rid)
    if r.is_round:
        call(action="choose", option=r.right)
    for i, c in enumerate(r.answer):
        call(action="dial", index=i, value=c)
    return call(action="run")


def open_chapter(ci):
    for c in range(ci):
        for r in reactions.CHAPTERS[c]["reactions"][:reactions.chapter_need(c)]:
            solve(r.id)
