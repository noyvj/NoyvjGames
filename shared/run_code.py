"""shared/run_code.py: the compact run code (planning/TODO.md FY-7), Python side.

A run code lets one player hand a friend a short text that says "this seed, this mode, this result":

    RUN-TIDE-K7F2Q-8XZ4A-... -CCC     (readable header, packed body, checksum)

    RUN        fixed word
    TIDE       the seed prefix of the game (shared/seed.py ``prefix_for``: "trade-empire" -> "TRADEEMPIRE")
    body       the packed run, base 32 (see below), written in groups of 5
    CCC        3-character checksum over the prefix and the body

The body holds only: a format version, the seed's 5-character code, a mode token (up to 8 characters
of a-z and 0-9, for example "hard"), and an optional result: a score and up to two more whole numbers
("stats"; the game knows what they mean, for example storms survived). Nothing else can be put in it,
so a code never contains a name, an account, an address or any text a player typed. Whole numbers are
limited to 0 .. MAX_VALUE (2**48 - 1); a game with decimals scales them (store tenths as integers).

A decoded code is DATA TO DISPLAY. It is never executed, never saved as the viewer's own progress and
never a verified score: the checksum only catches typing mistakes (anyone can make a code with any
score), so every result carries ``verified: False`` and the UI says so. A friend may show a "ghost
summary" ("Their run: 4,210 pts, 3 storms") or start the same seed; that is all.

``shared/run-code.js`` implements the SAME algorithm; ``shared/tests/test_run_code_browser.py`` pins
the two together over many inputs. A deliberate change to the format must bump ``FORMAT_VERSION``
(and re-pin the values in both tests), because shared codes would otherwise change meaning.

Pure functions, no I/O, no clock, no randomness. Needs ``seed.py`` next to it (seed alphabet, prefix
rule, FNV-1a hash), exactly as games already write ``seed.py`` into Pyodide's file system.
"""

import re

try:  # next to each other on disk or in Pyodide's file system
    import seed as _seed
except ImportError:  # pragma: no cover - when imported as shared.run_code
    from . import seed as _seed

FORMAT_VERSION = 1
HEADER = "RUN"
B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"   # Crockford base 32: no I, L, O or U
CHECK_LEN = 3                               # 15 bits
GROUP = 5                                   # body characters per group when written out
MAX_VALUE = (1 << 48) - 1
MAX_STATS = 2
MAX_MODE = 8
MAX_COMPACT_LEN = 80                        # longest valid code with no dashes: RUN + 12 + body + 3
MAX_INPUT_LEN = 400                         # longer pasted text is refused without reading it
SEED_CODE_LEN = _seed.CODE_LEN
SEED_BASE = len(_seed.ALPHABET)             # 31
SEED_LIMIT = SEED_BASE ** SEED_CODE_LEN     # 28,629,151, fits in 4 bytes

_DASHES = re.compile("[‐‑‒–—−_]")
_SPACE = re.compile("[ \t\r\n\f\v  -​  　﻿]+")
_MODE_OK = re.compile(r"^[a-z0-9]{1,%d}$" % MAX_MODE)
_PREFIX_OK = re.compile(r"^[A-Z0-9]{%d,%d}$" % (_seed.PREFIX_MIN, _seed.PREFIX_MAX))
_ALIASES = {"O": "0", "I": "1", "L": "1"}   # Crockford: the look-alikes mean 0 and 1

MESSAGES = {
    "empty": "Paste a run code first.",
    "too-long": "That is too long to be a run code.",
    "format": "That does not look like a run code. Run codes start with RUN and use letters and digits.",
    "version": "That run code was made by a newer version of the game. Update and try again.",
    "checksum": "That run code has a typing mistake: check each character and try again.",
    "wrong-game": "That run code is for {other}, not this game.",
}


class RunCodeError(ValueError):
    """Raised by ``encode``. ``reason`` is one of game, seed, wrong-game, mode, score, stats."""

    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


# -- small pieces ----------------------------------------------------------------------------------
def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _is_value(x):
    return _is_int(x) and 0 <= x <= MAX_VALUE


def _varint(n):
    out = []
    while True:
        low, n = n % 128, n // 128
        out.append(low | 128 if n else low)
        if not n:
            return out


def _read_varint(data, pos):
    """(value, next position) or None for a truncated, over-long or non-canonical number."""
    value, scale = 0, 1
    for i in range(7):
        if pos + i >= len(data):
            return None
        byte = data[pos + i]
        value += (byte % 128) * scale
        scale *= 128
        if byte < 128:
            if i > 0 and byte == 0:
                return None  # a canonical varint never ends in a zero group
            return value, pos + i + 1
    return None


def _to_b32(data):
    bits = "".join("{:08b}".format(b) for b in data)
    bits += "0" * (-len(bits) % 5)
    return "".join(B32[int(bits[i:i + 5], 2)] for i in range(0, len(bits), 5))


def _from_b32(text):
    """Bytes from base-32 text, or None when the leftover padding bits are not all zero."""
    bits = "".join("{:05b}".format(B32.index(c)) for c in text)
    whole = len(bits) // 8 * 8
    if "1" in bits[whole:]:
        return None
    return [int(bits[i:i + 8], 2) for i in range(0, whole, 8)]


def _checksum(prefix, body):
    h = _seed.fnv1a64("run-code-v%d|%s|%s" % (FORMAT_VERSION, prefix, body))
    v = (h ^ (h >> 32)) & 0x7FFF
    return B32[v >> 10] + B32[(v >> 5) & 31] + B32[v & 31]


def _seed_to_int(code):
    n = 0
    for ch in code:
        n = n * SEED_BASE + _seed.ALPHABET.index(ch)
    return n


def _int_to_seed(n):
    chars = []
    for _ in range(SEED_CODE_LEN):
        n, r = divmod(n, SEED_BASE)
        chars.append(_seed.ALPHABET[r])
    return "".join(reversed(chars))


def _group(body):
    return "-".join(body[i:i + GROUP] for i in range(0, len(body), GROUP))


# -- encode ----------------------------------------------------------------------------------------
def encode(fields):
    """Make a run code from ``{"game", "seed", "mode", "score", "stats"}``; raises ``RunCodeError``.

    game   the game slug (required), for example "tide"
    seed   optional: that game's seed ("TIDE-K7F2Q"; loose typing is fine)
    mode   optional: a-z and 0-9, up to 8 characters ("hard"); stored in lower case
    score  optional whole number 0 .. MAX_VALUE; needed when ``stats`` is given
    stats  optional list of up to two whole numbers, in a fixed order the game defines
    """
    f = fields if isinstance(fields, dict) else {}
    game = f.get("game")
    if not isinstance(game, str):
        raise RunCodeError("game", "A run code needs the game's id.")
    try:
        prefix = _seed.prefix_for(game)
    except ValueError:
        raise RunCodeError("game", "That game id is too short to make a run code.")

    flags = FORMAT_VERSION << 5
    out = []

    seed_text = f.get("seed")
    seed_int = None
    if seed_text not in (None, ""):
        norm = _seed.normalize(seed_text, game) if isinstance(seed_text, str) else ""
        if not norm:
            raise RunCodeError("seed", "That is not a valid seed.")
        if norm.split("-")[0] != prefix:
            raise RunCodeError("wrong-game", "That seed is for %s, not %s." % (norm.split("-")[0], prefix))
        seed_int = _seed_to_int(norm.split("-")[1])
        flags |= 0x10

    mode = f.get("mode")
    mode = "" if mode is None else mode
    if not isinstance(mode, str):
        raise RunCodeError("mode", "The mode must be text.")
    mode = mode.lower()
    if mode and not _MODE_OK.match(mode):
        raise RunCodeError("mode", "The mode may use a-z and 0-9, up to %d characters." % MAX_MODE)

    score = f.get("score")
    stats = f.get("stats")
    stats = [] if stats is None else stats
    if not isinstance(stats, (list, tuple)) or len(stats) > MAX_STATS:
        raise RunCodeError("stats", "At most %d stats fit in a run code." % MAX_STATS)
    if score is None and stats:
        raise RunCodeError("score", "Stats need a score to go with them.")
    if score is not None:
        if not _is_value(score):
            raise RunCodeError("score", "The score must be a whole number from 0 to %d." % MAX_VALUE)
        for s in stats:
            if not _is_value(s):
                raise RunCodeError("stats", "Each stat must be a whole number from 0 to %d." % MAX_VALUE)
        flags |= 0x08 | (len(stats) << 1)

    out.append(flags)
    if seed_int is not None:
        out.extend(seed_int.to_bytes(4, "big"))
    out.append(len(mode))
    out.extend(mode.encode("ascii"))
    if score is not None:
        out.extend(_varint(score))
        for s in stats:
            out.extend(_varint(s))

    body = _to_b32(out)
    return "%s-%s-%s-%s" % (HEADER, prefix, _group(body), _checksum(prefix, body))


# -- decode ----------------------------------------------------------------------------------------
def _fail(error, **fmt):
    return {"ok": False, "error": error, "message": MESSAGES[error].format(**fmt), "code": "", "game": "",
            "seed": "", "mode": "", "score": None, "stats": [], "has_result": False, "verified": False}


def _clean(text):
    return _SPACE.sub("", _DASHES.sub("-", text)).upper()


def _split(s, game):
    """(prefix, rest) from a cleaned code, or (None, error)."""
    if not s.startswith(HEADER):
        return None, "format"
    parts = s.split("-")
    if parts[0] == HEADER and len(parts) >= 3:
        return parts[1], "".join(parts[2:])
    if game is not None:
        lead = HEADER + _seed.prefix_for(game)
        t = s.replace("-", "")
        if t.startswith(lead):
            return _seed.prefix_for(game), t[len(lead):]
    return None, "format"


def decode(text, game=None):
    """Read a pasted run code. Never raises. Returns a dict:

    ok, error ("" or empty / too-long / format / version / checksum / wrong-game), message,
    code (canonical text), game (the seed prefix, "TIDE"), seed ("TIDE-K7F2Q" or ""), mode ("" or "hard"),
    score (int or None), stats (list of ints), has_result, verified (always False).

    Forgives case, spaces, odd dashes, missing dashes (when ``game`` is given) and the look-alikes
    O (for 0), I and L (for 1). Pass ``game`` to also refuse a code made for another game.
    """
    if not isinstance(text, str):
        return _fail("empty")
    if len(text) > MAX_INPUT_LEN:
        return _fail("too-long")
    s = _clean(text)
    if not s:
        return _fail("empty")
    if len(s.replace("-", "")) > MAX_COMPACT_LEN:
        return _fail("too-long")
    prefix, rest = _split(s, game)
    if prefix is None:
        return _fail(rest)
    if not _PREFIX_OK.match(prefix):
        return _fail("format")
    if game is not None and prefix != _seed.prefix_for(game):
        return _fail("wrong-game", other=prefix)
    rest = "".join(_ALIASES.get(c, c) for c in rest)
    if len(rest) <= CHECK_LEN or any(c not in B32 for c in rest):
        return _fail("format")
    body, check = rest[:-CHECK_LEN], rest[-CHECK_LEN:]
    if check != _checksum(prefix, body):
        return _fail("checksum")

    data = _from_b32(body)
    if not data:
        return _fail("format")
    flags = data[0]
    if flags >> 5 != FORMAT_VERSION:
        return _fail("version")
    has_seed, has_result, n_stats, reserved = bool(flags & 0x10), bool(flags & 0x08), (flags >> 1) & 3, flags & 1
    if reserved or n_stats > MAX_STATS or (n_stats and not has_result):
        return _fail("format")
    pos = 1
    seed_text = ""
    if has_seed:
        if pos + 4 > len(data):
            return _fail("format")
        n = int.from_bytes(bytes(data[pos:pos + 4]), "big")
        pos += 4
        if n >= SEED_LIMIT:
            return _fail("format")
        seed_text = "%s-%s" % (prefix, _int_to_seed(n))
    if pos >= len(data):
        return _fail("format")
    mlen = data[pos]
    pos += 1
    if mlen > MAX_MODE or pos + mlen > len(data):
        return _fail("format")
    mode = bytes(data[pos:pos + mlen]).decode("latin-1")
    pos += mlen
    if mode and not _MODE_OK.match(mode):
        return _fail("format")
    score, stats = None, []
    if has_result:
        r = _read_varint(data, pos)
        if r is None or r[0] > MAX_VALUE:
            return _fail("format")
        score, pos = r
        for _ in range(n_stats):
            r = _read_varint(data, pos)
            if r is None or r[0] > MAX_VALUE:
                return _fail("format")
            stats.append(r[0])
            pos = r[1]
    if pos != len(data):
        return _fail("format")
    return {"ok": True, "error": "", "message": "", "code": "%s-%s-%s-%s" % (HEADER, prefix, _group(body), check),
            "game": prefix, "seed": seed_text, "mode": mode, "score": score, "stats": stats,
            "has_result": has_result, "verified": False}


def validate(text, game=None):
    """``{"ok", "code", "error", "message"}``: the short form of ``decode`` (like ``seed.validate``)."""
    d = decode(text, game)
    return {"ok": d["ok"], "code": d["code"], "error": d["error"], "message": d["message"]}


def is_valid(text, game=None):
    return decode(text, game)["ok"]


def normalize(text, game=None):
    """The canonical spelling of a valid code, or "" when it is not one."""
    return decode(text, game)["code"]


# -- describing a decoded run --------------------------------------------------------------------
def _number(n):
    return "{:,}".format(n)


def describe(decoded, options=None):
    """One display line for a decoded run: "Their run: 4,210 pts, 3 storms, hard mode".

    options: ``prefix`` ("Their run"), ``unit`` ("pts"), ``stats`` (a list with one entry per stat:
    a string label such as "bonus", or ``{"one": "storm", "many": "storms"}``) and ``modes`` (a dict
    from mode token to display name, {"hard": "Hard"}). Unknown extras are ignored. Plain text, never markup.
    """
    o = options or {}
    d = decoded if isinstance(decoded, dict) and decoded.get("ok") else None
    if d is None:
        return ""
    parts = []
    if d["has_result"]:
        score = _number(d["score"])
        parts.append("%s %s" % (score, o["unit"]) if o.get("unit") else score)
        labels = o.get("stats") or []
        for i, value in enumerate(d["stats"]):
            label = labels[i] if i < len(labels) else None
            if isinstance(label, dict):
                label = label.get("one", "") if value == 1 else label.get("many", label.get("one", ""))
            parts.append("%s %s" % (_number(value), label) if label else _number(value))
    if d["mode"]:
        modes = o.get("modes") or {}
        parts.append("%s mode" % modes.get(d["mode"], d["mode"]))
    head = o.get("prefix", "Their run")
    if not parts:
        return head + (": seed %s" % d["seed"] if d["seed"] else "")
    return "%s: %s" % (head, ", ".join(parts))
