"""shared/seed.py: the seeded-run module (planning/TODO.md Z-1) and the daily seed (Z-5).

A run's randomness comes from one short, shareable seed string such as ``TIDE-K7F2Q``:

    PREFIX - CODE
    PREFIX  the game's slug, upper-cased with every character that is not a letter or digit removed
            ("trade-empire" -> "TRADEEMPIRE"), 2 to 12 characters
    CODE    5 characters from ALPHABET (31 symbols, no 0, 1, I, L or O so a seed read aloud or copied
            by eye is hard to get wrong)

``Rng(seed)`` is a splitmix64 generator whose state starts at the FNV-1a hash of the seed text,
exactly like ``games/chronicle/puzzle.py``. Nothing here uses ``random``, the clock or the platform,
and ``shared/seed.js`` implements the same algorithm bit for bit, so a seed gives the same run in
Python (Pyodide or CPython) and in JavaScript. ``shared/tests/test_seed.py`` pins known values and
``test_seed_browser.py`` proves the two languages agree on many seeds. A deliberate change to the
algorithm must bump ``ALGORITHM_VERSION`` and re-pin those values.

Pure functions, no I/O. The only non-deterministic call is ``new_seed`` (it needs entropy), and it
takes an ``entropy`` argument so tests can fix it.
"""

import re
import secrets
from datetime import date as _date

ALGORITHM_VERSION = "v1"
MASK = (1 << 64) - 1
ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CODE_LEN = 5
PREFIX_MIN = 2
PREFIX_MAX = 12
_TWO53 = float(1 << 53)

_DASHES = re.compile("[‐‑‒–—−_]")
_SPACE = re.compile("[ \t\r\n\f\v\u00a0\u2000-\u200b\u202f\u205f\u3000\ufeff]+")
_PREFIX_OK = re.compile(r"^[A-Z0-9]{%d,%d}$" % (PREFIX_MIN, PREFIX_MAX))
_DATE_OK = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def fnv1a64(text):
    h = 0xCBF29CE484222325
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * 0x100000001B3) & MASK
    return h


class Rng:
    """splitmix64 with the usual draws. Fully deterministic for a given seed text."""

    def __init__(self, seed_text):
        self.seed = str(seed_text)
        self.state = fnv1a64(self.seed)

    # -- raw ----------------------------------------------------------------
    def next(self):
        """Next 64-bit unsigned integer."""
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        return z ^ (z >> 31)

    def below(self, n):
        """Unbiased integer in [0, n)."""
        if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
            raise ValueError("below(n) needs an integer n >= 1")
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            v = self.next()
            if v < limit:
                return v % n

    # -- the usual draws ------------------------------------------------------
    def random(self):
        """Float in [0, 1) with 53 random bits (exactly the same number in JavaScript)."""
        return (self.next() >> 11) / _TWO53

    def randint(self, a, b):
        """Integer in [a, b], both ends included."""
        if b < a:
            raise ValueError("randint(a, b) needs b >= a")
        return a + self.below(b - a + 1)

    def uniform(self, a, b):
        return a + (b - a) * self.random()

    def chance(self, p):
        """True with probability p (0 never, 1 always)."""
        return self.random() < p

    def choice(self, items):
        items = list(items)
        if not items:
            raise IndexError("choice() from an empty sequence")
        return items[self.below(len(items))]

    def shuffle(self, items):
        """Shuffle a list IN PLACE (Fisher-Yates, back to front) and return it."""
        for i in range(len(items) - 1, 0, -1):
            j = self.below(i + 1)
            items[i], items[j] = items[j], items[i]
        return items

    def shuffled(self, items):
        """A shuffled copy; the argument is untouched."""
        return self.shuffle(list(items))

    def sample(self, items, k):
        """k distinct items, without replacement, in draw order."""
        items = list(items)
        if k < 0 or k > len(items):
            raise ValueError("sample larger than the population")
        out = []
        for _ in range(k):
            out.append(items.pop(self.below(len(items))))
        return out

    def weighted_choice(self, items, weights):
        """One item, chosen with probability proportional to its non-negative weight."""
        items = list(items)
        weights = list(weights)
        if not items or len(items) != len(weights):
            raise ValueError("weighted_choice needs equal, non-empty items and weights")
        total = 0.0
        for w in weights:
            if w < 0:
                raise ValueError("weights must not be negative")
            total += w
        if total <= 0:
            raise ValueError("weights must add up to more than zero")
        r = self.random() * total
        acc = 0.0
        for item, w in zip(items, weights):
            acc += w
            if r < acc:
                return item
        return items[-1]

    # -- streams and saving ---------------------------------------------------
    def fork(self, label):
        """An independent generator for one purpose ("loot", "weather"): it depends only on the seed
        and the label, never on how many numbers the parent has drawn, so adding a draw in one place
        does not shift every other stream."""
        return Rng("%s#%s" % (self.seed, label))

    def get_state(self):
        """The generator's position as a decimal string (JSON-safe, identical in JavaScript)."""
        return str(self.state)

    def set_state(self, text):
        value = int(text)
        if value < 0 or value > MASK:
            raise ValueError("state out of range")
        self.state = value


def rng(seed_text):
    return Rng(seed_text)


# -- seed strings -------------------------------------------------------------------------------
def prefix_for(game):
    """The seed prefix of a game slug: "tide" -> "TIDE", "trade-empire" -> "TRADEEMPIRE"."""
    p = re.sub(r"[^A-Z0-9]", "", str(game).upper())[:PREFIX_MAX]
    if len(p) < PREFIX_MIN:
        raise ValueError("game slug %r is too short to make a seed prefix" % (game,))
    return p


def example(game):
    """A syntactically valid seed for hints and placeholders ("TIDE-K7F2Q")."""
    return "%s-K7F2Q" % prefix_for(game)


def _random_code(below):
    return "".join(ALPHABET[below(len(ALPHABET))] for _ in range(CODE_LEN))


def new_seed(game, entropy=None):
    """A fresh random seed for `game`. `entropy`: None (the OS), a callable ``f(n) -> int in [0, n)``,
    or an object with a ``below(n)`` method (an ``Rng`` works, so tests can be deterministic)."""
    if entropy is None:
        below = secrets.randbelow
    elif callable(entropy):
        below = entropy
    else:
        below = entropy.below
    return "%s-%s" % (prefix_for(game), _random_code(below))


def daily_seed(game, date):
    """The one seed everybody gets for `game` on a UTC date (a "YYYY-MM-DD" string or a ``date``).
    Derived from the date string only, so it needs no server and agrees across devices."""
    if isinstance(date, _date):
        date = date.isoformat()
    if not isinstance(date, str) or not _DATE_OK.match(date):
        raise ValueError("daily_seed needs a YYYY-MM-DD date")
    try:
        _date.fromisoformat(date)
    except ValueError:
        raise ValueError("daily_seed needs a real calendar date")
    prefix = prefix_for(game)
    r = Rng("noyvj-daily-%s|%s|%s" % (ALGORITHM_VERSION, prefix, date))
    return "%s-%s" % (prefix, _random_code(r.below))


def normalize(text, game=None):
    """Clean a user-typed seed into canonical form, or return "" if it cannot be one.
    Forgives case, spaces, odd dashes, a missing dash ("tidek7f2q"), and, when `game` is given, a
    bare code ("k7f2q"). Does NOT check the prefix against `game` (see ``validate``)."""
    if not isinstance(text, str):
        return ""
    s = _SPACE.sub("", _DASHES.sub("-", text)).upper()
    if not s:
        return ""
    if "-" in s:
        head, _, code = s.rpartition("-")
        prefix = head.replace("-", "")
    elif game is not None and len(s) == CODE_LEN:
        prefix, code = prefix_for(game), s
    elif len(s) > CODE_LEN:
        prefix, code = s[:-CODE_LEN], s[-CODE_LEN:]
    else:
        return ""
    if game is not None and prefix == "":
        prefix = prefix_for(game)
    if not _PREFIX_OK.match(prefix):
        return ""
    if len(code) != CODE_LEN or any(c not in ALPHABET for c in code):
        return ""
    return "%s-%s" % (prefix, code)


def validate(text, game=None):
    """Check a user-entered seed. Returns ``{"ok", "seed", "error", "message"}``; `seed` is the
    canonical form when ok. `error` is "" or one of "empty", "format", "wrong-game"."""
    raw = text.strip() if isinstance(text, str) else ""
    if not raw:
        hint = " such as %s" % example(game) if game else ""
        return {"ok": False, "seed": "", "error": "empty", "message": "Enter a seed%s." % hint}
    seed = normalize(raw, game)
    if not seed:
        hint = " Seeds look like %s." % example(game) if game else ""
        return {"ok": False, "seed": "", "error": "format",
                "message": "That is not a seed: use letters and digits (no 0, 1, I, L or O).%s" % hint}
    if game is not None and seed.split("-")[0] != prefix_for(game):
        return {"ok": False, "seed": "", "error": "wrong-game",
                "message": "That seed is for %s, not this game." % seed.split("-")[0]}
    return {"ok": True, "seed": seed, "error": "", "message": ""}


def is_valid(text, game=None):
    return validate(text, game)["ok"]
