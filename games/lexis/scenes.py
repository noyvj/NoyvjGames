"""Lexis -- the evidence the player watches (rung 1).

A scene is one signal received at the station and what the station did. Scenes are NOT written by hand:
they are produced by running the real world (`world.react`) on a short script of messages, so what the
player sees can never disagree with what the language actually means. The curriculum is ordered; the
game reveals them one at a time, and deduce.py proves that the revealed prefix is enough.
"""

from dataclasses import dataclass

from pulse import PULSE, say_door, say_lamps
from world import Station, react


@dataclass(frozen=True)
class Scene:
    id: str
    marks: str
    before: Station
    after: Station

    def to_dict(self):
        return {"id": self.id, "marks": self.marks, "before": self.before.to_dict(), "after": self.after.to_dict()}


# The script for the Pulse curriculum. The ORDER is the teaching:
#   1 a single lamp: something happens when the signal arrives, and a number seems to matter
#   2 two lamps: the number is not "count the marks"; 0010 has one mark and lit two lamps
#   3 five lamps: a number the player has not seen before, spelled by the pattern they have been learning
#   4 the door opens: a different thing, a different word
#   5 the door shuts: the other word, and the same thing again
#   6 no lamps: zero is a number too
PULSE_SCRIPT = (
    ("lamp-1", say_lamps(1)),
    ("lamp-2", say_lamps(2)),
    ("lamp-5", say_lamps(5)),
    ("door-open", say_door("open")),
    ("door-shut", say_door("shut")),
    ("lamp-0", say_lamps(0)),
)


def pulse_scenes():
    """The scenes of the Pulse curriculum, each starting from where the previous one ended."""
    station = Station(0, "shut")
    scenes = []
    for scene_id, marks in PULSE_SCRIPT:
        reaction = react(marks, station, PULSE)
        assert reaction.understood, (scene_id, reaction.reason)   # the script is the true language
        scenes.append(Scene(scene_id, marks, station, reaction.station))
        station = reaction.station
    return tuple(scenes)
