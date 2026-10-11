"""Mirror Lab -- the benches in play order, grouped in chapters of eight. Chapter n+1 opens when 5 of chapter n are cleared."""

import benches_ch1
import benches_ch2
import benches_ch3
from bench import Bench

OPEN_AT = 5                       # benches cleared in a chapter to open the next one

CHAPTER_INFO = (
    {"number": 1, "name": "Flat Mirrors", "blurb": "One beam, a few mirrors. Tap a placed mirror to flip it between / and \\."},
    {"number": 2, "name": "Splitters", "blurb": "A splitter lets the beam go on and sends a copy off to the left of its travel."},
    {"number": 3, "name": "Prisms", "blurb": "A prism splits white light into a short (S) and a long (L) beam, one to each side. Tap it to swap the sides."},
)
_DATA = (benches_ch1.BENCHES, benches_ch2.BENCHES, benches_ch3.BENCHES)

CHAPTERS = []
ALL_BENCHES = []
for _index, _items in enumerate(_DATA):
    _info = CHAPTER_INFO[_index]
    _list = [Bench(d, _info["number"], i + 1) for i, d in enumerate(_items)]
    CHAPTERS.append({"number": _info["number"], "name": _info["name"], "blurb": _info["blurb"], "benches": _list})
    ALL_BENCHES.extend(_list)

BY_ID = {b.id: b for b in ALL_BENCHES}
ORDER = [b.id for b in ALL_BENCHES]


def chapter_of(bench):
    return CHAPTERS[bench.chapter - 1]
