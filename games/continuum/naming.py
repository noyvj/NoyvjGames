"""Continuum -- K-24: naming the settlement.

An era-flavoured name generator plus a free-text option. The name is a
keepsake, not a game input: it never changes a number in the sim. It shows on
the founding plaque (and the Desktop HUD), the Civilization Summary's opening
statement, the settlement archive and the shareable card.

Storage is `campaign.ui["settlement_name"]`, a plain string inside the
existing `ui` dict, so there is no save-schema change. Every read goes
through `clean()` (a hand-edited or junk value reads as "no name") and every
write through `sanitise()`: the free-text option accepts letters, digits,
spaces and a few joining marks only, so no markup, control or invisible
characters ever reach the page, a spreadsheet or the card image. The cap is
`MAX_LEN` characters.

Pure functions only (no DOM, no storage): `game.py` does the I/O.
"""

import random
import re

import sim

KEY = "settlement_name"
MAX_LEN = 28
_JOINERS = " '’-."
_TAG = re.compile(r"<[^>]{0,200}>")


def sanitise(raw):
    """A safe, tidy name from whatever was typed, or '' when nothing usable is left.

    Keeps letters and digits (any script), spaces and the marks ' ’ - . ; every
    other character (markup, control and invisible characters, emoji, quotes,
    slashes) is dropped. Runs of whitespace collapse to one space, leading and
    trailing joining marks are trimmed, and the result is cut to `MAX_LEN`.
    """
    if not isinstance(raw, str):
        return ""
    raw = _TAG.sub(" ", raw)  # a typed <b>...</b> is dropped whole, not left as stray letters
    kept = []
    for ch in raw:
        if ch.isalpha() or ch.isdigit() or ch in "'’-.":
            kept.append(ch)
        elif ch.isspace() and ch.isprintable():
            kept.append(" ")
        elif ch in "\t\n\r":
            kept.append(" ")
    text = " ".join("".join(kept).split())
    text = text.strip(_JOINERS)[:MAX_LEN].strip(_JOINERS)
    return text


def clean(value):
    """The stored name as it will be shown: sanitised, '' for junk."""
    return sanitise(value)


def get(ui):
    """The settlement's name from `campaign.ui`, or ''."""
    return clean(ui.get(KEY)) if isinstance(ui, dict) else ""


def set_name(ui, raw):
    """Stores the sanitised name (an empty result clears it); returns what was stored."""
    name = sanitise(raw)
    if name:
        ui[KEY] = name
    else:
        ui.pop(KEY, None)
    return name


# Two word lists per era, joined as "<First> <Second>". The words are invented
# combinations in each era's own register, not claims about real places.
_WORDS = {
    "tribal": (
        ["Ash", "Reed", "Stone", "Willow", "Fern", "Otter", "Heron", "Cairn", "Ember", "Moss", "Red", "Swift", "Birch", "Elk"],
        ["Hollow", "Ford", "Camp", "Hearth", "Bend", "Crossing", "Glen", "Shore", "Rock", "Clearing", "Spring", "Fire"],
    ),
    "agrarian": (
        ["Barley", "Millet", "Harvest", "Furrow", "Meadow", "Golden", "Long", "Sheaf", "Orchard", "Clay", "Wheat", "Flax"],
        ["field", "Acre", "Ridge", "Mead", "Stead", "Garth", "Vale", "Fold", "Row", "Barrow", "Terrace", "Green"],
    ),
    "classical": (
        ["Marble", "Olive", "Aqueduct", "Laurel", "Amphora", "Cypress", "Mosaic", "Colonnade", "Forum", "Vine", "Granite", "Stoa"],
        ["Agora", "Heights", "Rise", "Harbour", "Gate", "Court", "Walk", "Quarter", "Basin", "Sanctum", "Bridge", "Landing"],
    ),
    "medieval": (
        ["Raven", "Oak", "Abbey", "Guild", "Wolf", "Bridge", "Castle", "Market", "Lantern", "Tallow", "Falcon", "Bell"],
        ["Keep", "Gate", "Moot", "Cross", "Haven", "Wick", "Hythe", "Minster", "Green", "Court", "Tower", "Fold"],
    ),
    "industrial": (
        ["Smoke", "Iron", "Foundry", "Coal", "Mill", "Steam", "Canal", "Brick", "Copper", "Rail", "Forge", "Tin"],
        ["Works", "Yard", "Row", "End", "Reach", "Wharf", "Junction", "Bank", "Side", "Quay", "Lane", "Terrace"],
    ),
    "digital": (
        ["Node", "Signal", "Fibre", "Cloud", "Pixel", "Mesh", "Open", "Data", "Vector", "Cache", "Packet", "Binary"],
        ["Commons", "Heights", "Exchange", "Quarter", "Loop", "Point", "Park", "Hub", "Yards", "Terrace", "Stack", "Gateway"],
    ),
    "space": (
        ["Aster", "Halo", "Nova", "Vesper", "Zenith", "Lumen", "Orbit", "Comet", "Solstice", "Perihelion", "Aphelion", "Quasar"],
        ["Ring", "Station", "Reach", "Anchor", "Drift", "Spindle", "Harbour", "Light", "Deck", "Arc", "Spire", "Cradle"],
    ),
    "relay": (
        ["Far", "Outer", "Lantern", "Tether", "Beacon", "Span", "Horizon", "Meridian", "Threshold", "Waypoint", "Distant", "Kindled"],
        ["Link", "Reach", "Hold", "Crossing", "Light", "Verge", "Landing", "Lattice", "Passage", "Chain", "Wake", "Haven"],
    ),
}


def suggest(era, seed):
    """An era-flavoured name for `era`, the same one for the same `seed`.

    An unknown era falls back to the first era's words and a non-integer seed
    to 0, so the caller never has to guard it.
    """
    words = _WORDS.get(era) or _WORDS[sim.ERA_ORDER[0]]
    if isinstance(seed, bool) or not isinstance(seed, int):
        seed = 0
    rng = random.Random(seed)
    first, second = rng.choice(words[0]), rng.choice(words[1])
    if second[0].islower():
        return sanitise(first + second)  # "Barley" + "field" -> "Barleyfield"
    return sanitise(f"{first} {second}")


def title(name):
    """The name as a heading line, or the game's own name when there is none."""
    return name or "Continuum"


def with_name(name, text):
    """`text` prefixed by the settlement's name when it has one ("Reed Ford: ...")."""
    return f"{name}: {text}" if name else text
