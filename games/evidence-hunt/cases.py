"""Evidence Hunt -- the 40 authored cases, grouped into chapters. The chapter files hold the data; this module indexes them."""

import cases_1
import cases_2
import cases_3
import cases_4
import cases_5

CHAPTER_DATA = (
    ("first-visits", "First Visits", "Houses that grow from three rooms to seven. Read the sheet, walk the rooms, pick a bag and name the spirit.", cases_1.CASES),
    ("misleading", "Misleading Readings", "A room's own feature can make a reading look positive. Trust the room the house does not fool.", cases_2.CASES),
    ("two-presences", "Two Presences", "Two spirits, each in a room of its own. Name both.", cases_3.CASES),
    ("keepsakes", "Keepsakes", "A keepsake swamps every reading in its room, and looking at it gives one more line of testimony.", cases_4.CASES),
    ("big-houses", "The Big Houses", "Ten to fourteen rooms and a bag of four. Everything together.", cases_5.CASES),
)

ALL = []
for _index, (_cid, _name, _blurb, _cases) in enumerate(CHAPTER_DATA):
    for _case in _cases:
        _case["chapter"] = _index
        ALL.append(_case)
