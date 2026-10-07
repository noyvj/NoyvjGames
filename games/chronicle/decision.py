"""Chronicle -- decision points: the choice a historical figure really faced, then what they chose and what followed.

A decision (`decisions.json`) exists only where the set's sources document the options, the choice and what followed:
each of those three parts is a claim with its own three sources. The player picks; nothing is graded (there is no
right answer, and the game never presents an alternative as what would have happened). Only the ORDER the options
are shown in is generated: a pure function of (set id, set version, decision id) from the shared splitmix64, so the
authored order (which might put the real choice last every time) never gives the answer away.
`tests/fixtures/decision_orders_v1.json` pins it; a deliberate change must bump SEED_VERSION and regenerate the fixture.
"""

from puzzle import Rng

SEED_VERSION = "v1"
PARTS = ("options", "choice", "after")


def option_order(cset, decision_id):
    d = cset.decision(decision_id)
    if d is None:
        raise ValueError("unknown decision %r" % (decision_id,))
    rng = Rng("chronicle-decision|%s|%s|%s|%s" % (SEED_VERSION, cset.id, cset.version, decision_id))
    return rng.shuffle([o["id"] for o in d["options"]])
