"""Lexis -- the Bridge language's evidence, produced by the real world.

The order is the teaching (the player already reads nouns from planet 2 and numbers from planet 1, so only
the three markers are new):
  1 "ku": one big water arrives (a plain noun, as on planet 2: nothing new, a baseline)
  2 "ku p 0011": big water goes from 1 to 4 (a new sign, and the number after it says how many MORE)
  3 "mo p 0010": two small grain arrive (the same sign again, a different noun and number: it is the sign, not the noun)
  4 "ku n": the big water vanishes (a second new sign: all of it goes)
  5 "mo q": nothing changes on the counter but the station says how many small grain there are (the third new sign)
"""

from dataclasses import dataclass

from bridge import Stock, react


@dataclass(frozen=True)
class BridgeScene:
    id: str
    message: str
    before: Stock
    after: Stock
    reply: str

    def to_dict(self):
        return {"id": self.id, "message": self.message, "before": self.before.to_dict(),
                "after": self.after.to_dict(), "reply": self.reply}


BRIDGE_SCRIPT = (("ku", "ku"), ("ku-p-3", "ku p 0011"), ("mo-p-2", "mo p 0010"), ("ku-n", "ku n"), ("mo-q", "mo q"))


def bridge_scenes():
    stock = Stock()
    scenes = []
    for scene_id, message in BRIDGE_SCRIPT:
        reaction = react(message, stock)
        assert reaction.understood, (scene_id, reaction.reason)
        scenes.append(BridgeScene(scene_id, message, stock, reaction.stock, reaction.reply))
        stock = reaction.stock
    return tuple(scenes)
