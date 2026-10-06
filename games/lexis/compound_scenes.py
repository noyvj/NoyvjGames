"""Lexis -- the Compound language's evidence. Produced by running the real world, like the Pulse scenes.

The order is the teaching:
  1 ko: a small water arrives (a thing the player cannot yet split into parts)
  2 mo: a small grain arrives (the SECOND part is shared: something is the same across both)
  3 mu: a big grain arrives (the FIRST part is shared with scene 2; the second part is what changed: u is not o)
  4 to: a small fire arrives (a third thing, same second part as scenes 1 and 2)
Four scenes settle the whole language: the player has never been shown ku, tu or any big water or big fire.
"""

from dataclasses import dataclass

from compound import Tray, react


@dataclass(frozen=True)
class CompoundScene:
    id: str
    glyph: str
    before: Tray
    after: Tray

    def to_dict(self):
        return {"id": self.id, "glyph": self.glyph, "before": self.before.to_dict(), "after": self.after.to_dict()}


COMPOUND_SCRIPT = (("ko", "ko"), ("mo", "mo"), ("mu", "mu"), ("to", "to"))


def compound_scenes():
    tray = Tray()
    scenes = []
    for scene_id, glyph in COMPOUND_SCRIPT:
        reaction = react(glyph, tray)
        assert reaction.understood, scene_id
        scenes.append(CompoundScene(scene_id, glyph, tray, reaction.tray))
        tray = reaction.tray
    return tuple(scenes)
