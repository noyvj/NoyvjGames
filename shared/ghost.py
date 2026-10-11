"""shared/ghost.py: the shared ghost-run trace (planning/TODO.md Z-3, item Z-3a).

A "ghost" is your best earlier run drawn faintly behind the live one. This module is the Python half:
it records ONE number per turn, keeps the trace small, cleans anything it loads and compares the live
run with a stored best trace. ``shared/ghost.js`` is the JavaScript twin (it reads the same trace,
gives the same comparison and draws the line over a game's SVG chart); ``shared/tests/test_ghost.py``
and ``test_ghost_browser.py`` pin that the two agree.

The stored trace is a small JSON-safe dict::

    {"v": 1, "turns": 40, "values": [0, 1.5, 3, ...], "label": "Run 3"}

    turns   how many turns the run really lasted (an integer, 0 to MAX_TURNS)
    values  at most MAX_LEN numbers. If turns <= len(values) it is one number per turn, point for point.
            A longer run was thinned evenly, so a turn is read by spreading it over the stored length
            (the same rule as Grid's ghost_value, GC-9).
    label   optional short text for the legend ("Run 3"), at most LABEL_MAX characters

Rules this module keeps (all tested):

* Pure and deterministic: no clock, no ``random``, no I/O. The same inputs give the same trace.
* Hard caps: MAX_LEN stored numbers, MAX_TURNS turns, values clamped to +/- MAX_ABS and rounded to
  DIGITS decimals. A trace that is bigger than that when loaded is thinned, never trusted.
* Sanitised on load: ``load`` and ``sanitise`` accept anything. Non-numbers (text, None, booleans,
  lists), NaN and infinity are dropped; a list longer than HARD_INPUT_LIMIT is refused outright
  (``load`` returns None); one between MAX_LEN and that limit is thinned evenly. A dict with the
  wrong shape, a bad ``turns`` or fewer than MIN_POINTS usable numbers gives None, so an old or
  tampered save simply has no ghost.
* Old saves load: a game that never recorded a trace has ``load(None)`` == None and loses nothing.

Direction: ``higher_is_better`` (default True) says whether a bigger number is "ahead" (funds, score,
clean share) or a smaller one is (emissions, debt, turns taken).
"""

import math
import re

TRACE_VERSION = 1
MAX_LEN = 120            # numbers stored per trace
MIN_POINTS = 2           # fewer usable numbers than this is no ghost
MAX_TURNS = 100000       # the longest run a trace can claim
HARD_INPUT_LIMIT = 5000  # a raw list longer than this is refused when loading
MAX_ABS = 1e12           # values are clamped to +/- this
DIGITS = 2               # values are rounded to this many decimals
LABEL_MAX = 40
LEVEL_EPSILON = 0.005    # a gap this small (after rounding) reads as "level"

_SCALE = 10 ** DIGITS


# -- numbers ----------------------------------------------------------------------------------
def _round(x):
    """Round half up to DIGITS decimals, the same way ghost.js does (floor(x * 100 + 0.5) / 100)."""
    return math.floor(x * _SCALE + 0.5) / _SCALE


def clean_number(value):
    """A usable float (clamped, rounded) or None for anything that is not a finite real number.
    Booleans are not numbers here."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        x = float(value)
    except (OverflowError, ValueError):
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    x = max(-MAX_ABS, min(MAX_ABS, x))
    x = _round(x)
    return 0.0 if x == 0 else x   # no negative zero


def _tidy(x):
    """A whole float becomes an int so the stored JSON stays short and identical in both languages."""
    return int(x) if x == int(x) else x


def _thin(values, limit):
    """Evenly thin a list to at most ``limit`` items, keeping the first and the last."""
    n = len(values)
    if n <= limit:
        return list(values)
    if limit == 1:
        return [values[-1]]
    return [values[math.floor(i * (n - 1) / (limit - 1) + 0.5)] for i in range(limit)]


def sanitise(raw, max_len=MAX_LEN):
    """Clean any value into a list of at most ``max_len`` numbers: non-numbers, NaN and infinity are
    dropped, the rest clamped and rounded, and an over-long list thinned evenly. Not a list/tuple, or
    longer than HARD_INPUT_LIMIT, gives []."""
    if not isinstance(raw, (list, tuple)) or len(raw) > HARD_INPUT_LIMIT:
        return []
    out = []
    for item in raw:
        x = clean_number(item)
        if x is not None:
            out.append(x)
    return [_tidy(x) for x in _thin(out, max(1, int(max_len)))]


_CONTROL = re.compile("[\u0000-\u001f\u007f-\u009f\u2028\u2029]")
_SPACE = re.compile("[ \t\r\n\f\v\u00a0\u2000-\u200b\u202f\u205f\u3000\ufeff]+")


def clean_label(label):
    """A short plain legend text: control characters and runs of spaces collapsed, at most LABEL_MAX characters."""
    if not isinstance(label, str):
        return ""
    text = _SPACE.sub(" ", _CONTROL.sub(" ", label)).strip(" ")
    return text[:LABEL_MAX].rstrip(" ")


# -- the trace --------------------------------------------------------------------------------
def make_trace(values, turns=None, label=""):
    """Build a trace from a finished run's per-turn numbers (``turns`` defaults to how many numbers
    survive cleaning). Returns None if fewer than MIN_POINTS numbers are usable."""
    if not isinstance(values, (list, tuple)) or len(values) > HARD_INPUT_LIMIT:
        return None
    if turns is None:
        turns = sum(1 for item in values if clean_number(item) is not None)
    return load({"v": TRACE_VERSION, "turns": turns, "values": list(values), "label": label})


def load(data):
    """Turn anything read from a save into a clean trace dict, or None. Never raises."""
    if not isinstance(data, dict):
        return None
    values = sanitise(data.get("values"))
    if len(values) < MIN_POINTS:
        return None
    turns = data.get("turns")
    if isinstance(turns, bool) or not isinstance(turns, (int, float)):
        turns = len(values)
    elif isinstance(turns, float) and (math.isnan(turns) or math.isinf(turns)):
        turns = len(values)
    else:
        turns = int(turns)
        if turns < 1:
            turns = len(values)
    turns = min(turns, MAX_TURNS)
    if turns < len(values):   # a trace cannot hold more points than turns; the shorter claim wins
        values = _thin(values, max(MIN_POINTS, turns))
        turns = max(turns, len(values))
    if turns < MIN_POINTS:
        return None
    return {"v": TRACE_VERSION, "turns": turns, "values": values, "label": clean_label(data.get("label"))}


def to_dict(trace):
    """The JSON-safe form of a trace for saving (a clean copy), or None."""
    return load(trace)


def value_at(trace, turn):
    """The ghost's number at a 1-based turn, or None when the turn is outside the run (or the trace is
    unusable). A run of at most MAX_LEN turns was stored point for point; a longer one was thinned
    evenly, so the read is spread over its length (floor(i + 0.5) rounding, same as ghost.js)."""
    t = load(trace)
    if t is None or isinstance(turn, bool) or not isinstance(turn, (int, float)):
        return None
    if isinstance(turn, float) and (math.isnan(turn) or math.isinf(turn)):
        return None
    turn = int(turn)
    n, total = len(t["values"]), t["turns"]
    if turn < 1 or turn > total:
        return None
    if total <= n:
        return t["values"][turn - 1]
    return t["values"][math.floor((turn - 1) * (n - 1) / (total - 1) + 0.5)]


# -- recording --------------------------------------------------------------------------------
class Recorder:
    """Records one number per turn without ever growing past MAX_LEN.

    ``record(value)`` once per turn. A value that is not a finite number repeats the previous turn's
    number (0 on the first turn), so turns stay aligned. When the list would pass its limit every
    second stored point is dropped and from then on only every second (then fourth, ...) turn is
    kept: a long run is thinned evenly, and the final turn is always added by ``trace()``.
    """

    def __init__(self, max_len=MAX_LEN):
        self.max_len = max(MIN_POINTS + 1, min(int(max_len), MAX_LEN))
        self.values = []
        self.turns = 0
        self.stride = 1
        self._last = 0.0

    def record(self, value):
        x = clean_number(value)
        if x is not None:
            self._last = x
        if self.turns >= MAX_TURNS:
            return
        if self.turns % self.stride == 0:
            self.values.append(self._last)
            if len(self.values) > self.max_len - 1:   # leave one slot for the final turn
                self.values = self.values[::2]
                self.stride *= 2
        self.turns += 1

    def trace(self, label=""):
        """The finished trace (always includes the last turn), or None while fewer than MIN_POINTS turns."""
        if self.turns < MIN_POINTS:
            return None
        values = list(self.values)
        if (self.turns - 1) % self.stride != 0:   # the last turn was skipped by thinning
            values.append(self._last)
        return load({"v": TRACE_VERSION, "turns": self.turns, "values": values, "label": label})

    def reset(self):
        self.__init__(self.max_len)


# -- comparing --------------------------------------------------------------------------------
def live_series(live):
    """The live run's per-turn numbers, cleaned but keeping every turn: an entry that is not a finite
    number repeats the previous turn's number (0 on the first turn). None if ``live`` is not a
    non-empty list, or longer than HARD_INPUT_LIMIT."""
    if not isinstance(live, (list, tuple)) or not live or len(live) > HARD_INPUT_LIMIT:
        return None
    out, last = [], 0.0
    for item in live:
        x = clean_number(item)
        if x is not None:
            last = x
        out.append(last)
    return out


def compare(live, trace, higher_is_better=True):
    """Compare the live run so far (a list of per-turn numbers) with a stored best trace.

    Returns None when either side is unusable, else a dict:
        turn        the live run's latest turn (1-based)
        live        its number
        ghost       the ghost's number at that turn, or None when the ghost's run had already ended
        gap         live - ghost (rounded), or None; positive = bigger than the ghost
        status      "ahead" | "behind" | "level" | "ended"  (ahead/behind follow ``higher_is_better``;
                    "ended" = the ghost's run was shorter than this turn)
        lead        the live run's lead over the ghost at the latest turn in the same direction as
                    ``status`` (never negative); 0 when level or ended
        best_turn / best_gap
                    the turn where the ghost was furthest AHEAD of the live run so far and by how
                    much (best_gap 0 and best_turn None when it was never ahead)
    """
    t = load(trace)
    if t is None:
        return None
    nums = live_series(live)
    if nums is None:
        return None
    sign = 1 if higher_is_better else -1
    best_turn, best_gap = None, 0.0
    for i, mine in enumerate(nums, start=1):
        g = value_at(t, i)
        if g is None:
            continue
        behind_by = sign * (g - mine)    # >0 means the ghost was ahead of the live run
        if behind_by > best_gap:
            best_turn, best_gap = i, _round(behind_by)
    turn = len(nums)
    mine = nums[-1]
    ghost = value_at(t, turn)
    if ghost is None:
        return {"turn": turn, "live": mine, "ghost": None, "gap": None, "status": "ended", "lead": 0,
                "best_turn": best_turn, "best_gap": best_gap}
    gap = _round(mine - ghost)
    lead = _round(sign * gap)
    if abs(lead) < LEVEL_EPSILON:
        status, lead = "level", 0
    elif lead > 0:
        status = "ahead"
    else:
        status, lead = "behind", _round(-lead)
    return {"turn": turn, "live": mine, "ghost": ghost, "gap": gap, "status": status, "lead": lead,
            "best_turn": best_turn, "best_gap": best_gap}


def format_number(x):
    """A short, language-independent reading of a number: whole numbers plain, otherwise up to 2 decimals."""
    x = _round(x)
    if x == int(x):
        return str(int(x))
    return ("%.2f" % x).rstrip("0").rstrip(".")


def summary(result, label="", unit=""):
    """The one-line accessible text for a ``compare`` result, from the ghost's point of view:

        ghost: your best run was 12 ahead at turn 7        (the live run is behind)
        ghost: you are 5 ahead of your best run at turn 7   (the live run is ahead)
        ghost: level with your best run at turn 7
        ghost: your best run ended before turn 21

    ``unit`` (for example "%" or " funds") is appended to numbers; ``label`` names the ghost instead of
    "your best run" (for example "your Run 3"). No result gives a plain "no ghost yet" line."""
    if not result:
        return "ghost: no earlier run to race yet"
    who = label.strip() if isinstance(label, str) and label.strip() else "your best run"
    turn = result["turn"]
    if result["status"] == "ended":
        return "ghost: %s ended before turn %d" % (who, turn)
    amount = format_number(result["lead"]) + (unit if isinstance(unit, str) else "")
    if result["status"] == "level":
        return "ghost: level with %s at turn %d" % (who, turn)
    if result["status"] == "ahead":
        return "ghost: you are %s ahead of %s at turn %d" % (amount, who, turn)
    return "ghost: %s was %s ahead at turn %d" % (who, amount, turn)
