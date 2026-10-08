"""Pocket Bazaar -- the goods: five families of five tiers each, plus the wildcard.

A good is a plain tuple (family, tier). Two identical goods merge into the next tier; a tier-5 good is a
showpiece and does not merge further. Prices live here so the board, the customers and the shop agree.
Families differ by glyph shape AND letter (never colour alone), and tiers by a number of pips.
"""

MAX_TIER = 5
WILD = "wild"           # the wildcard family marker; a wildcard good is (WILD, 1)

FAMILIES = ("produce", "textiles", "ceramics", "spices", "sweets")

FAMILY_INFO = {
    "produce": {"name": "Produce", "letter": "P", "shape": "circle",
                "tiers": ("Berry", "Plum", "Pear", "Melon", "Orchard basket")},
    "textiles": {"name": "Textiles", "letter": "T", "shape": "triangle",
                 "tiers": ("Thread", "Ribbon", "Scarf", "Shawl", "Tapestry")},
    "ceramics": {"name": "Ceramics", "letter": "C", "shape": "square",
                 "tiers": ("Clay bead", "Cup", "Bowl", "Vase", "Painted urn")},
    "spices": {"name": "Spices", "letter": "S", "shape": "diamond",
               "tiers": ("Bay leaf", "Cinnamon stick", "Saffron pinch", "Spice jar", "Spice chest")},
    "sweets": {"name": "Sweets", "letter": "D", "shape": "hexagon",
               "tiers": ("Sugar drop", "Toffee", "Cookie", "Cupcake", "Celebration cake")},
}

LETTER_TO_FAMILY = {info["letter"]: fam for fam, info in FAMILY_INFO.items()}

# What a good of each tier is worth when a customer pays for it, and when it is sold off the board. Selling is
# never zero (the no-soft-lock rule) and always pays less than a customer would.
VALUE = (0, 4, 10, 24, 56, 130)
SELL = (0, 1, 2, 6, 14, 32)


def is_wild(good):
    return good is not None and good[0] == WILD


def valid_good(good):
    """True for (family, tier) with a known family and a tier in range, or the wildcard."""
    try:
        family, tier = good
    except (TypeError, ValueError):
        return False
    if isinstance(tier, bool) or not isinstance(tier, int):
        return False
    if family == WILD:
        return tier == 1
    return family in FAMILY_INFO and 1 <= tier <= MAX_TIER


def good_name(good):
    if is_wild(good):
        return "Wildcard"
    family, tier = good
    return FAMILY_INFO[family]["tiers"][tier - 1]


def good_label(good):
    """A short plain label such as 'Cup (tier 2)'; used by screen readers and the text board."""
    if is_wild(good):
        return "Wildcard"
    return f"{good_name(good)} (tier {good[1]})"


def good_code(good):
    """Two characters: family letter plus tier digit ('C2'); '**' for the wildcard; '..' for nothing."""
    if good is None:
        return ".."
    if is_wild(good):
        return "**"
    return FAMILY_INFO[good[0]]["letter"] + str(good[1])


def parse_code(code):
    """Inverse of good_code. Raises ValueError for anything else."""
    if code == "..":
        return None
    if code == "**":
        return (WILD, 1)
    if len(code) == 2 and code[0] in LETTER_TO_FAMILY and code[1] in "12345":
        return (LETTER_TO_FAMILY[code[0]], int(code[1]))
    raise ValueError(f"not a good: {code!r}")


def good_value(good):
    return 0 if is_wild(good) else VALUE[good[1]]


def sell_value(good):
    return 1 if is_wild(good) else SELL[good[1]]


def crate_beats(tier):
    """Beats (crate taps plus merges) to build one good of this tier from scratch with no help:
    2**(t-1) taps and 2**(t-1) - 1 merges."""
    return 2 ** tier - 1


def cells_needed(tier):
    """Board cells you must be able to hold at once to build one good of this tier (a binary counter)."""
    return tier


def next_tier_name(good):
    if good is None or is_wild(good) or good[1] >= MAX_TIER:
        return None
    return good_name((good[0], good[1] + 1))
