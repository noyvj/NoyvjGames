"""Hull Repair -- the forty boards, grouped into five decks (chapters). Each board's stored `sol` is its one restored
layout; tests prove it is the only one. A deck opens once OPEN_AT boards of the deck before it are patched."""

import boards_crew
import boards_dock
import boards_engineering
import boards_life
import rules

CHAPTER_DEFS = (
    {"id": "dock", "name": "Docking Ring", "data": boards_dock.DOCK,
     "blurb": "The ring where ships used to arrive. Plain lines between matching ports: join every pair, and keep lines out of each other's way.",
     "new": ""},
    {"id": "crew", "name": "Crew Deck", "data": boards_crew.CREW,
     "blurb": "Where people slept and ate. Parts of the hull are gone here, so the rooms are no longer square.",
     "new": "Holes: cells with no hull. Nothing can be laid there."},
    {"id": "engineering", "name": "Engineering", "data": boards_engineering.ENGINEERING,
     "blurb": "Pumps, cables and cabinets. Lines need to cross, and this deck has the parts for it.",
     "new": "Bridges: two lines may cross in a bridge cell, one straight across and one straight up and down."},
    {"id": "life", "name": "Life Support", "data": boards_life.LIFE,
     "blurb": "Air, water and waste, and the valves that keep them going the right way.",
     "new": "Valves: a line goes straight through, the way the arrow points, travelling from its source (solid) to its sink (ringed)."},
    {"id": "core", "name": "The Core", "data": [],
     "blurb": "Power and control. Everything you have learned, and the last new part.",
     "new": "Mixers: two named lines both end in the mixer, one from each side."},
)
OPEN_AT = 5

CHAPTER_LIST = []
BY_ID = {}
ORDER = []
for _index, _deck in enumerate(CHAPTER_DEFS):
    _ids = []
    for _n, _spec in enumerate(_deck["data"], start=1):
        _board = rules.Board(_spec)
        _board.chapter, _board.number = _index, _n
        _board.solution = rules.decode(_board, _spec["sol"])
        BY_ID[_board.id] = _board
        ORDER.append(_board.id)
        _ids.append(_board.id)
    CHAPTER_LIST.append({"index": _index, "id": _deck["id"], "name": _deck["name"], "blurb": _deck["blurb"], "new": _deck["new"], "rooms": _ids})
ALL_BOARDS = [BY_ID[i] for i in ORDER]
