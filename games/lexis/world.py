"""Lexis -- the station the signals act on (rung 1).

A tiny deterministic world: seven lamps and a door. A signal either changes it or it does not. The same
`react` function produces the scenes the player watches (scenes.py) and the replies to what the player
says, so what is observed and what is tested can never disagree.
"""

from dataclasses import dataclass

from parse import SignalError, parse
from pulse import MAX_NUMBER


@dataclass(frozen=True)
class Station:
    lamps: int = 0
    door: str = "shut"

    def to_dict(self):
        return {"lamps": self.lamps, "door": self.door}

    @staticmethod
    def from_dict(data):
        return Station(int(data["lamps"]), str(data["door"]))


@dataclass(frozen=True)
class Reaction:
    """What the station did. `understood` is False when the signal could not be parsed; then `station` is
    unchanged and `reason` / `text` say why in the world's own words."""

    understood: bool
    station: Station
    text: str
    reason: str = ""


def describe(station):
    lamps = "no lamps are lit" if station.lamps == 0 else (
        "1 lamp is lit" if station.lamps == 1 else f"{station.lamps} lamps are lit")
    return f"At the station, {lamps} and the door is {station.door}."


def react(marks, station, language):
    try:
        sentence = parse(marks, language)
    except SignalError as err:
        return Reaction(False, station, err.text, err.reason)
    if sentence.noun == "lamp":
        n = min(max(sentence.value, 0), MAX_NUMBER)
        after = Station(n, station.door)
    else:
        after = Station(station.lamps, sentence.value)
    return Reaction(True, after, describe(after))
