"""Dead Reckoning -- the practice chart generator's CORE: share codes, chart ids and the few constants the rest of the game needs
at boot. A practice chart is a pure function of (difficulty, seed): the same code always makes the same chart, so a code such as
DR3-1K9X2 can be shared and replayed.

The generator itself (laying out a sea, solving it by rejection, the two-ship option) lives in genmake.py, which the page loads as
the lazy pack "practice" the first time a practice or daily chart is opened (see modules.json). Everything the generator offers
(make_chart, from_id, plan_route, Rng, ...) is still reachable as `gen.<name>`: this module forwards unknown names to genmake, so
callers and tests do not care which file a name lives in. When genmake is not on the page (its pack has not loaded) `ready()` is
False, `make_chart` and `from_id` return None, and any other forwarded name raises AttributeError."""

import re

DIFFICULTIES = (1, 2, 3, 4, 5)
NAMES = {1: "Easy water", 2: "A stream", 3: "Wind and land", 4: "Tides and compass", 5: "Fog and everything"}
SEED_LIMIT = 36 ** 6
CODE_RE = re.compile(r"^DR([1-5])(T?)-([0-9A-Z]{1,6})$")
ID_RE = re.compile(r"^practice-([1-5])(t?)-([0-9a-z]{1,6})$")


# --- codes ---------------------------------------------------------------------------------------
def to_base36(n):
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while n:
        n, r = divmod(n, 36)
        out = digits[r] + out
    return out or "0"


def chart_id(difficulty, seed, two=False):
    return "practice-%d%s-%s" % (difficulty, "t" if two else "", to_base36(seed))


def code_of(difficulty, seed, two=False):
    """DR3-1K9X2; a two-ship chart carries a T after the level (DR3T-1K9X2), so every earlier code keeps meaning what it did."""
    return ("DR%d%s-%s" % (difficulty, "T" if two else "", to_base36(seed))).upper()


def parse_ex(text):
    """(difficulty, seed, two) from a share code (any case, surrounding spaces ignored) or a chart id, or None."""
    if not isinstance(text, str):
        return None
    t = text.strip()
    m = CODE_RE.match(t.upper()) or ID_RE.match(t.lower())
    if not m:
        return None
    seed = int(m.group(3), 36)
    return (int(m.group(1)), seed, bool(m.group(2))) if seed < SEED_LIMIT else None


def parse(text):
    """(difficulty, seed) from a ONE-ship share code or chart id, or None (a two-ship code is read by parse_ex)."""
    parsed = parse_ex(text)
    return parsed[:2] if parsed and not parsed[2] else None


def is_practice_id(text):
    return isinstance(text, str) and ID_RE.match(text) is not None


def next_seed(played, difficulty, nonce=0):
    """A fresh-looking seed for the next practice chart: repeatable from what the player has done, never a clock."""
    return (played * 7919 + difficulty * 104729 + nonce * 15485863 + 12345) % SEED_LIMIT


# --- the generator (lazy pack "practice") ---------------------------------------------------------
def _genmake():
    """The genmake module, or None when its pack is not on the page."""
    try:
        import genmake
        return genmake
    except ImportError:
        return None


def ready():
    return _genmake() is not None


def make_chart(difficulty, seed, two=False):
    """The practice chart for (difficulty, seed), or None (no solvable chart came out, or the generator is not loaded: see ready())."""
    maker = _genmake()
    return maker.make_chart(difficulty, seed, two) if maker is not None else None


def from_id(text):
    """The chart for a practice chart id or share code, or None."""
    parsed = parse_ex(text)
    return make_chart(*parsed) if parsed else None


def __getattr__(name):
    maker = None if name.startswith("__") else _genmake()
    if maker is not None and hasattr(maker, name):
        return getattr(maker, name)
    raise AttributeError("module 'gen' has no attribute %r" % name)
