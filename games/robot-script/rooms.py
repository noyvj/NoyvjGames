"""Robot Script -- the 40 authored rooms, in order, with their chapters.

Each room is data: an id, a name, the chapter, the drawing, what the toolbox holds (`allow`), a reference solution
(`ref`, in the text form of dsl.py) and its length (`par`), a nudge (one plain sentence), and an intro line. The reference
is the proof the room can be cleared at par; the tests run it for every room. Rooms live in the rooms_<chapter>.py
modules; this module only gathers them.
"""

import dsl
from room import Layout

import rooms_branches
import rooms_capstone
import rooms_loops
import rooms_moving
import rooms_routines
import rooms_turning

CHAPTERS = (
    ("moving", "Moving", "Straight corridors: count your steps, light a switch, carry a part.", rooms_moving),
    ("turning", "Turning", "Left and right: corners, detours and two trips with one pair of hands.", rooms_turning),
    ("loops", "Loops", "Repeat blocks: say it once, do it many times.", rooms_loops),
    ("routines", "Sub-routines", "Save a few steps under a name and call them wherever they are needed.", rooms_routines),
    ("branches", "Conditionals", "Until and if: let the robot look at where it is and decide.", rooms_branches),
    ("shift", "The Long Shift", "Everything at once. The last room clears the deck.", rooms_capstone),
)


class Room:
    def __init__(self, chapter, number, data):
        self.chapter = chapter
        self.number = number                # 1-based within the chapter
        self.id = data["id"]
        self.name = data["name"]
        self.rows = tuple(data["rows"])
        self.allow = data["allow"]
        self.ref_text = data["ref"]
        self.par = int(data["par"])
        self.nudge = data["nudge"]
        self.intro = data.get("intro", "")
        self.layout = Layout(self.rows)
        self.ref = dsl.from_text(self.ref_text)

    @property
    def silver(self):
        return silver_limit(self.par)

    def toolbox(self):
        return dsl.allowed_ops(self.allow)


def silver_limit(par):
    return par + max(2, par // 3)


def medal(par, size):
    """3 gold (at or under par), 2 silver (within a third more, at least 2), 1 bronze (cleared)."""
    if size <= par:
        return 3
    if size <= silver_limit(par):
        return 2
    return 1


def _build():
    rooms = []
    chapters = []
    for index, (cid, name, blurb, module) in enumerate(CHAPTERS):
        ids = []
        for number, data in enumerate(module.ROOMS, start=1):
            rooms.append(Room(index, number, data))
            ids.append(data["id"])
        chapters.append({"id": cid, "name": name, "blurb": blurb, "index": index, "rooms": ids})
    return rooms, chapters


ALL_ROOMS, CHAPTER_LIST = _build()
BY_ID = {r.id: r for r in ALL_ROOMS}
ORDER = [r.id for r in ALL_ROOMS]
