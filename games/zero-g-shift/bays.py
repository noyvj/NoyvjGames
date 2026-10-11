"""Zero-G Shift -- the 48 bays of the freight hauler Marrow, in six decks of eight. Every deck and every bay is open from
the start, in any order. The rows, par and one stored shortest line live in bays_<deck>.py (found and proved by
tools/build_bays.py and the tests); this file only gathers them in order and names the decks."""

import bays_cargo
import rules

DECK_DEFS = (
    ("cargo", "Cargo Floor", bays_cargo,
     "Open floor and a single crate. Drift is the whole idea: thrust off a wall and you glide until something stops you.",
     "Thrust and glide. You slide until something stops you. Slide into a loose crate and it keeps going while you stay put. A dock pad catches a crate of its own kind."),
)

DECK_LIST = []
ALL_BAYS = []
BY_ID = {}
for _index, (_id, _name, _module, _blurb, _new) in enumerate(DECK_DEFS):
    _ids = []
    for _number, _spec in enumerate(_module.BAYS, start=1):
        _bay = rules.Bay(_spec)
        _bay.deck, _bay.number = _index, _number
        ALL_BAYS.append(_bay)
        BY_ID[_bay.id] = _bay
        _ids.append(_bay.id)
    DECK_LIST.append({"id": _id, "name": _name, "blurb": _blurb, "new": _new, "bays": _ids})
ORDER = [b.id for b in ALL_BAYS]
