"""Lighthouse -- the ships of a night, generated from the seed like the weather.

A ship is a plain dict: id, kind, name, arrive (tick), window (ticks it spends near the rock), need (the
effective reach it needs to pick the light out), rep and salvage (what a safe passage earns). Nothing here
knows about the keeper's plan; the sim measures the beam against `need` tick by tick.
"""

from clock import is_festival, night_len, season_of
from data import FIRST_MAIL_NIGHT, MAIL_NAME, SHIP_KINDS, SHIP_ORDER, SHIP_WEIGHTS, SHIPS_PER_NIGHT
from rng import pick, rint, weighted
from weather import severity

FIRST_WORDS = ("Brave", "Quiet", "Little", "Grey", "Kind", "Lucky", "Patient", "Salt", "Morning", "Slow",
               "Merry", "Steady", "Bright", "Old", "Green", "Narrow", "Fair", "Wild", "Hollow", "Tidy")
SECOND_WORDS = {
    "fisher": ("Wren", "Herring", "Pail", "Net", "Gull", "Cod", "Crab", "Lantern", "Hook", "Dory", "Skate", "Whelk"),
    "ferry": ("Crossing", "Bridge", "Ribbon", "Shuttle", "Spindle", "Lark", "Bell", "Mile", "Thread", "Heron", "Lane", "Tern"),
    "cargo": ("Dray", "Ledger", "Hauler", "Barrow", "Tally", "Anvil", "Cart", "Keel", "Granary", "Sack", "Bale", "Ballast"),
    "yacht": ("Whim", "Sonnet", "Kite", "Feather", "Sparrow", "Sundial", "Violet", "Pennant", "Ripple", "Muse", "Dandelion", "Fig"),
}

_cache = {}


def mail_nights_before(seed, night):
    """The scheduled mail-boat nights up to and including `night`, in order. The first is night 3, then every
    three to five nights. A late boat does not move the schedule; the sim keeps a separate 'still due' flag."""
    out = []
    n = FIRST_MAIL_NIGHT
    gap_index = 0
    while n <= night:
        out.append(n)
        n += rint(3, 5, seed, "mail-gap", gap_index)
        gap_index += 1
    return out


def mail_scheduled(seed, night):
    return night in mail_nights_before(seed, night)


def next_mail_night(seed, night):
    """The first scheduled mail night strictly after `night`."""
    n = FIRST_MAIL_NIGHT
    gap_index = 0
    while n <= night:
        n += rint(3, 5, seed, "mail-gap", gap_index)
        gap_index += 1
    return n


def _name(seed, night, index, kind):
    return "%s %s" % (pick(FIRST_WORDS, seed, "ship-a", night, index), pick(SECOND_WORDS[kind], seed, "ship-b", night, index))


def _ship(night, index, kind, arrive, name):
    base = SHIP_KINDS[kind]
    return {
        "id": "%d-%d" % (night, index), "kind": kind, "name": name, "arrive": arrive, "window": base["window"],
        "need": base["need"], "rep": base["rep"], "salvage": base["salvage"],
    }


def ships_for_night(seed, night, mail=False):
    """Every ship that passes on this night, ordered by arrival. `mail` adds the supply boat."""
    key = (seed, night, bool(mail))
    hit = _cache.get(key)
    if hit is not None:
        return [dict(s) for s in hit]
    length = night_len(night)
    ships = []
    if not is_festival(night):
        lo, hi = SHIPS_PER_NIGHT[severity(seed, night)]
        count = rint(lo, hi, seed, "ship-count", night)
        if night == 1:
            count = max(count, 2)      # the very first night always has company
        for i in range(count):
            kind = weighted(SHIP_ORDER, SHIP_WEIGHTS[season_of(night)], seed, "ship-kind", night, i)
            window = SHIP_KINDS[kind]["window"]
            arrive = rint(3, max(3, length - window - 1), seed, "ship-arrive", night, i)
            ships.append(_ship(night, i, kind, arrive, _name(seed, night, i, kind)))
    if mail:
        window = SHIP_KINDS["mail"]["window"]
        arrive = rint(length // 4, max(length // 4, length - window - 4), seed, "mail-arrive", night)
        ships.append(_ship(night, 9, "mail", arrive, MAIL_NAME))
    ships.sort(key=lambda s: (s["arrive"], s["id"]))
    if len(_cache) > 64:
        _cache.clear()
    _cache[key] = [dict(s) for s in ships]
    return ships


def block_of_arrival(night, ship):
    return min(2, ship["arrive"] * 3 // night_len(night))
