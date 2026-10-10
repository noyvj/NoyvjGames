"""Signal -- a daily deduction puzzle with a retro radio-room feel.

Hidden transmitters broadcast on a small grid. A "ping" on a tile returns ONE
number: the sum of every transmitter's signal at that tile, where a single
transmitter's signal is max(0, radius - manhattan_distance). You have a small
ping budget, then you must mark the exact tiles of every transmitter and
commit.

This file is the ENGINE and holds every game rule: the seeded generator, the
constraint solver that proves each puzzle is solvable, scoring, streaks,
achievements, the share text, and the save/load contract. It never touches
the DOM. index.html's small glue script (app.js) draws whatever the engine
returns and forwards taps to it, so the engine runs the same under plain
CPython/pytest (the tests) and under Pyodide (the browser).

Public surface (what app.js and the shared save widget call):
    handle(request)  -- one JSON request in, one JSON response out
    get_state()      -- plain JSON-safe dict (shared/save-widget.js contract)
    load_state(data) -- merges a saved dict in (the inverse of get_state)

The rest of this docstring is the data model, because the save format is the
part that must never drift:

    {
      "schema": 1,
      "days":  {"YYYY-MM-DD:mode": {"mode", "kind": "daily"|"archive",
                                     "pings": [[r, c, reading], ...],
                                     "marks": [[r, c], ...], "guess": [[r, c], ...],
                                     "result": "inprogress"|"won"|"lost",
                                     "pings_used": n, "par": n|null}},
      "practice": null | {"code", "mode", "kind": "practice", ...same fields...},
      "practice_stats": {"easy": {"played", "won", "pings_hist"}, ...},
      "settings": {"mode", "assist_shading", "ascii_share", "show_streaks", "last_preset"},
      "earned": {"achievement_id": "YYYY-MM-DD"},
      "flags": {"shared": bool},
      "onboarding_seen": bool,
      "session": {"type", "date", "mode", "marks"},
      "achievements_earned": [ids]   # derived projection, never read back
      "stats": {...}                 # derived projection, never read back
    }
"""

import datetime
import json
import random
import re

GAME_ID = "signal"
SCHEMA = 1
SEED_VERSION = "v1"

# Puzzle #1 is the UTC day the game first shipped, fixed in the release
# commit and never changed afterwards (planning/signal-plan.md, decision 5).
# app.js mirrors this constant for the engine-less archive calendar, and a
# test asserts the two agree.
EPOCH = "2026-09-27"

# Presets. "top" is only a display ceiling (readings above it draw as the
# tallest bar), tuned so typical readings use the whole glyph range.
PRESETS = {
    "easy": {
        "label": "Easy", "letter": "E", "size": 9, "k": 2, "radius": 4, "spacing": 3,
        "budget": 8, "top": 5, "assist": True, "daily": True,
    },
    "hard": {
        "label": "Hard", "letter": "H", "size": 9, "k": 4, "radius": 4, "spacing": 2,
        "budget": 9, "top": 8, "assist": False, "daily": True,
    },
    "wide": {
        "label": "Wide", "letter": "W", "size": 13, "k": 4, "radius": 5, "spacing": 3,
        "budget": 12, "top": 10, "assist": False, "daily": False, "sample": 100,
    },
    "bigsky": {
        "label": "Big Sky", "letter": "B", "size": 15, "k": 5, "radius": 6, "spacing": 3,
        "budget": 14, "top": 12, "assist": False, "daily": False, "sample": 100,
    },
}
PRESET_ORDER = ("easy", "hard", "wide", "bigsky")
DAILY_MODES = tuple(k for k in PRESET_ORDER if PRESETS[k]["daily"])
LETTER_TO_PRESET = {p["letter"]: key for key, p in PRESETS.items()}

# A puzzle is accepted only if a greedy solver identifies it in at most
# budget - PAR_MARGIN pings, so a sensible player always has slack.
PAR_MARGIN = 2
MAX_ATTEMPTS = 80
SOLUTION_SAMPLE = 200
MAX_DAYS = 800

GLYPHS = "▁▂▃▄▅▆▇█"  # low bar .. full block
ASCII_GLYPHS = ".:+#"
COLUMN_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LENGTH = 5

# --------------------------------------------------------------------------
# Static assets (achievements.json / changelog.json). The boot script fetches
# them and sets window globals; the filesystem fallback keeps the module
# importable and testable outside a browser with no test-only special-casing
# (ACHIEVEMENTS-SYSTEM-DESIGN.md section 2).


def _read_json_asset(name, global_name):
    raw = None
    try:
        import js  # noqa: WPS433 (only exists inside Pyodide)
        raw = getattr(js, global_name, None)
        if raw is not None:
            raw = str(raw)
    except ImportError:
        raw = None
    if raw is None:
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, name), encoding="utf-8") as handle_:
            raw = handle_.read()
    return json.loads(raw)


def _load_catalogs():
    ach = _read_json_asset("achievements.json", "ACHIEVEMENTS_JSON")["achievements"]
    log = _read_json_asset("changelog.json", "CHANGELOG_JSON")
    if isinstance(log, dict):
        log = log["changelog"]
    log = sorted(log, key=lambda entry: entry["date"], reverse=True)
    return ach, log


ACHIEVEMENTS, CHANGELOG = _load_catalogs()
ACHIEVEMENT_IDS = [a["id"] for a in ACHIEVEMENTS]


# --------------------------------------------------------------------------
# Pure helpers: dates, RNG, coordinates


_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def parse_date(text):
    """A datetime.date for a strict YYYY-MM-DD string, else None."""
    if not isinstance(text, str) or not _DATE_RE.match(text):
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def puzzle_number(date_text):
    """Days since EPOCH + 1 (the launch day is puzzle #1)."""
    return (parse_date(date_text) - parse_date(EPOCH)).days + 1


def _real_clock():
    return datetime.datetime.now(datetime.timezone.utc).date()


_clock = _real_clock


def set_clock(func):
    """Tests inject a fixed UTC date; None restores the real clock."""
    global _clock
    _clock = func or _real_clock


def utc_today():
    return _clock().isoformat()


def fnv1a32(text):
    """32-bit FNV-1a of the UTF-8 bytes (integer-only, so identical everywhere)."""
    h = 0x811C9DC5
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


class Rng:
    """mulberry32. Integer-only so every Python (and any port) agrees."""

    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFF

    def random(self):
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.state
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    def below(self, n):
        return int(self.random() * n)


def cell_label(r, c):
    """Spreadsheet-style label: column letter then 1-based row, e.g. D4."""
    return "%s%d" % (COLUMN_LETTERS[c], r + 1)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


# --------------------------------------------------------------------------
# Board geometry and the constraint solver


class Board:
    """Distance/weight tables for one preset (built once, cached)."""

    def __init__(self, key):
        p = PRESETS[key]
        self.key = key
        self.n = p["size"]
        self.k = p["k"]
        self.radius = p["radius"]
        self.spacing = p["spacing"]
        n = self.n
        total = n * n
        self.dist = [[abs(a // n - b // n) + abs(a % n - b % n) for b in range(total)] for a in range(total)]
        self.weight = [[max(0, self.radius - d) for d in row] for row in self.dist]
        # Transmitters never sit on the outer ring (it keeps readings informative).
        self.cells = [r * n + c for r in range(1, n - 1) for c in range(1, n - 1)]
        self.interior = set(self.cells)


_BOARDS = {}


def board_for(key):
    if key not in _BOARDS:
        _BOARDS[key] = Board(key)
    return _BOARDS[key]


def reading_at(board, transmitters, cell):
    weights = board.weight[cell]
    return sum(weights[t] for t in transmitters)


def solve(board, pings, limit=2, forced=None, node_cap=None):
    """Every transmitter set consistent with `pings`, up to `limit` of them.

    pings: list of (cell, reading). forced: a cell that must be a transmitter.
    Returns (solutions, complete): solutions is a list of sorted tuples of
    cells; complete is False only if node_cap stopped the search early.

    A constraint search, not a brute-force scan: any tile a reading rules out
    is dropped up front (a zero reading clears its whole neighbourhood), then
    it repeatedly branches on the most constrained ping still owed signal.
    Branching is "include cell i, exclude cells 1..i-1" over the cells that
    could supply that ping, which partitions the solutions so each set is
    found exactly once.
    """
    n_pings = len(pings)
    dist = board.dist
    spacing = board.spacing
    tables = [board.weight[cell] for cell, _ in pings]
    start_res = [reading for _, reading in pings]
    out = []
    nodes = [0]

    class _Stop(Exception):
        pass

    def fits(cell, res):
        for i in range(n_pings):
            if tables[i][cell] > res[i]:
                return False
        return True

    def free_fill(cands, m, chosen):
        def go(begin, left, current):
            if len(out) >= limit:
                return
            if left == 0:
                out.append(tuple(sorted(chosen + current)))
                return
            for j in range(begin, len(cands)):
                cell = cands[j]
                ok = True
                for other in current:
                    if dist[cell][other] < spacing:
                        ok = False
                        break
                if ok:
                    go(j + 1, left - 1, current + [cell])
        go(0, m, [])

    def rec(cands, res, m, chosen):
        nodes[0] += 1
        if node_cap is not None and nodes[0] > node_cap:
            raise _Stop()
        if len(out) >= limit:
            return
        if m == 0:
            if not any(res):
                out.append(tuple(sorted(chosen)))
            return
        if len(cands) < m:
            return
        best_i, best_cover = -1, None
        for i in range(n_pings):
            if res[i] > 0:
                table = tables[i]
                cover = [c for c in cands if table[c] > 0]
                if not cover:
                    return
                top = sorted((table[c] for c in cover), reverse=True)[:m]
                if sum(top) < res[i]:
                    return
                if best_cover is None or len(cover) < len(best_cover):
                    best_i, best_cover = i, cover
        if best_i < 0:
            free_fill(cands, m, chosen)
            return
        excluded = set()
        for cell in best_cover:
            if len(out) >= limit:
                return
            new_res = [res[i] - tables[i][cell] for i in range(n_pings)]
            row = dist[cell]
            new_cands = [
                x for x in cands
                if x != cell and x not in excluded and row[x] >= spacing and fits(x, new_res)
            ]
            rec(new_cands, new_res, m - 1, chosen + [cell])
            excluded.add(cell)

    cands0 = [c for c in board.cells if fits(c, start_res)]
    try:
        if forced is not None:
            if forced not in cands0:
                return [], True
            new_res = [start_res[i] - tables[i][forced] for i in range(n_pings)]
            row = dist[forced]
            new_cands = [
                x for x in cands0
                if x != forced and row[x] >= spacing and fits(x, new_res)
            ]
            rec(new_cands, new_res, board.k - 1, [forced])
        else:
            rec(cands0, list(start_res), board.k, [])
    except _Stop:
        return out, False
    return out, True


def possible_cells(board, pings, node_cap=3000):
    """Tiles that could still hold a transmitter given the readings so far.

    A tile survives if some consistent set contains it. If the per-tile search
    runs out of budget the tile is kept (an over-approximation, never a false
    'ruled out')."""
    n_pings = len(pings)
    tables = [board.weight[cell] for cell, _ in pings]
    result = []
    for cell in board.cells:
        if any(tables[i][cell] > pings[i][1] for i in range(n_pings)):
            continue
        sols, complete = solve(board, pings, limit=1, forced=cell, node_cap=node_cap)
        if sols or not complete:
            result.append(cell)
    return result


# --------------------------------------------------------------------------
# Puzzle generation


class Puzzle:
    __slots__ = ("mode", "seed", "transmitters", "par", "reference", "attempts")

    def __init__(self, mode, seed, transmitters, par, reference, attempts):
        self.mode = mode
        self.seed = seed
        self.transmitters = transmitters
        self.par = par
        self.reference = reference
        self.attempts = attempts


def _place(board, rng):
    """Random spaced transmitters on the interior, by rejection sampling."""
    while True:
        chosen = []
        tries = 0
        while len(chosen) < board.k and tries < 400:
            tries += 1
            cell = board.cells[rng.below(len(board.cells))]
            if all(board.dist[cell][other] >= board.spacing for other in chosen):
                chosen.append(cell)
        if len(chosen) == board.k:
            return tuple(sorted(chosen))


def adaptive_par(board, transmitters, max_pings, sample=SOLUTION_SAMPLE):
    """(par, reference_pings) for a placement, or (None, pings) past max_pings.

    par = how many pings a deterministic greedy solver needs before exactly
    one transmitter set is left. Its opening ping is the centre; each later
    ping is the untried tile that best splits a sample of the sets still
    consistent (lowest sum of squared class sizes, ties to the lowest tile).
    It is an upper bound on the true optimum, which is what "par" means."""
    total = board.n * board.n
    weight = board.weight
    pings = []
    reference = []
    used = set()
    for _ in range(max_pings):
        if pings:
            sols, _complete = solve(board, pings, limit=sample)
            if len(sols) == 1:
                return len(pings), reference
            best = None
            for cell in range(total):
                if cell in used:
                    continue
                row = weight[cell]
                counts = {}
                for sol in sols:
                    value = sum(row[t] for t in sol)
                    counts[value] = counts.get(value, 0) + 1
                score = sum(v * v for v in counts.values())
                if best is None or score < best[0]:
                    best = (score, cell)
            cell = best[1]
        else:
            cell = (board.n // 2) * board.n + board.n // 2
        used.add(cell)
        reference.append(cell)
        pings.append((cell, reading_at(board, transmitters, cell)))
    sols, _complete = solve(board, pings, limit=2)
    if len(sols) == 1:
        return len(pings), reference
    return None, reference


def generate(mode, seed_text):
    """The puzzle for a seed: a pure function of (mode, seed_text)."""
    preset = PRESETS[mode]
    board = board_for(mode)
    rng = Rng(fnv1a32(seed_text))
    limit = preset["budget"] - PAR_MARGIN
    for attempt in range(1, MAX_ATTEMPTS + 1):
        transmitters = _place(board, rng)
        par, reference = adaptive_par(board, transmitters, limit, preset.get("sample", SOLUTION_SAMPLE))
        if par is not None:
            return Puzzle(mode, seed_text, transmitters, par, tuple(reference), attempt)
    raise RuntimeError("no solvable puzzle for seed %r" % seed_text)


def daily_seed(date_text, mode):
    return "signal:%s:%s:%s" % (SEED_VERSION, date_text, mode)


def practice_seed(mode, code):
    return "signal:%s:practice:%s:%s" % (SEED_VERSION, mode, code)


_PUZZLE_CACHE = {}


def puzzle_for_seed(mode, seed_text):
    key = (mode, seed_text)
    if key not in _PUZZLE_CACHE:
        if len(_PUZZLE_CACHE) >= 48:
            _PUZZLE_CACHE.pop(next(iter(_PUZZLE_CACHE)))
        _PUZZLE_CACHE[key] = generate(mode, seed_text)
    return _PUZZLE_CACHE[key]


def daily_puzzle(date_text, mode):
    return puzzle_for_seed(mode, daily_seed(date_text, mode))


# Practice codes: "P-" + preset letter + 5 Crockford base32 characters. The
# code carries the preset so a shared code is enough to reproduce a puzzle.

_rand = random.Random()


def set_random_source(source):
    """Tests inject a seeded random.Random; None restores an OS-seeded one."""
    global _rand
    _rand = source or random.Random()


def new_practice_code(mode):
    body = "".join(CODE_ALPHABET[_rand.randrange(len(CODE_ALPHABET))] for _ in range(CODE_LENGTH))
    return "P-%s%s" % (PRESETS[mode]["letter"], body)


def parse_practice_code(text):
    """(mode, canonical_code) for a practice code, else None. Forgiving about
    case, spaces, a missing 'P-', and Crockford's O/I/L look-alikes."""
    if not isinstance(text, str):
        return None
    cleaned = re.sub(r"[\s\-]", "", text.upper())
    if cleaned.startswith("P"):
        cleaned = cleaned[1:]
    if len(cleaned) != 1 + CODE_LENGTH:
        return None
    letter, body = cleaned[0], cleaned[1:]
    mode = LETTER_TO_PRESET.get(letter)
    if mode is None:
        return None
    body = body.replace("O", "0").replace("I", "1").replace("L", "1")
    if any(ch not in CODE_ALPHABET for ch in body):
        return None
    return mode, "P-%s%s" % (letter, body)


# --------------------------------------------------------------------------
# Glyphs, flavour text, share text


def reading_level(reading, top):
    """0-7 bar height for a reading (0 stays 0; anything above top is 7)."""
    if reading <= 0:
        return 0
    return min(7, max(1, -(-reading * 7 // top)))


def reading_fill(reading, top):
    return round(min(1.0, max(0.0, reading / float(top))), 2)


def glyph_for(level, ascii_mode=False):
    if ascii_mode:
        return ASCII_GLYPHS[level // 2]
    return GLYPHS[level]


def result_label(rec):
    return rec["result"]


def build_share_text(rec, mode, number, ascii_mode=False):
    """No positions, no per-tile numbers: just the rhythm of your readings."""
    preset = PRESETS[mode]
    won = rec["result"] == "won"
    used = "%d/%d" % (rec["pings_used"], preset["budget"]) if won else "X/%d" % preset["budget"]
    kind = rec.get("kind")
    if kind == "practice":
        head = "Signal practice %s %s %s" % (rec.get("code", ""), preset["label"].lower(), used)
    elif kind == "archive":
        head = "Signal #%d %s (archive) %s" % (number, preset["label"].lower(), used)
    else:
        head = "Signal #%d %s %s" % (number, preset["label"].lower(), used)
    if not ascii_mode:
        head += " ⚡"
    strip = "".join(
        glyph_for(reading_level(ping[2], preset["top"]), ascii_mode) for ping in rec["pings"]
    )
    if not strip:
        strip = "-"
    if ascii_mode:
        tail = "OK" if won else "X"
    else:
        tail = "✔" if won else "✖"
    return "%s\n%s %s" % (head, strip, tail)


_LINES = {
    "zero": [
        "Static. Nothing on this tile.",
        "Dead air. Good to know.",
        "Silence. That is data too.",
        "Nothing here but the hiss.",
        "The needle does not move.",
    ],
    "low": [
        "A faint carrier, somewhere close by.",
        "Barely a whisper on the dial.",
        "Something is out there. Not near.",
        "Weak, but it is real.",
    ],
    "mid": [
        "A clear signal. Someone is broadcasting.",
        "The needle lifts. Interesting.",
        "Good strength. Not the whole story yet.",
        "That is a busy stretch of sky.",
    ],
    "stacked": [
        "Two fields stacking. That is no single transmitter.",
        "Overlap. The dial climbs higher than one source can push it.",
        "Stronger than any one tower. They are close together.",
        "Fields overlapping. Now we are getting somewhere.",
        "The needle pins. More than one voice here.",
    ],
    "win": [
        "Locked on. Every transmitter found.",
        "Clean copy. The room goes quiet.",
        "All stations accounted for.",
        "Signal confirmed. Nicely done.",
    ],
    "win_par": [
        "At par or better. The operator is showing off.",
        "Textbook. The solver could not do it faster.",
        "Tuned in on the fewest pings. Very tidy.",
        "Right on the money, and quickly.",
    ],
    "win_last": [
        "On the very last ping. Do not tell anyone how close that was.",
        "Final ping, right answer. The tape was running out.",
        "Out of budget and into the win.",
    ],
    "lose": [
        "Lost the signal. Everyone loses one.",
        "Wrong stations. The static wins this round.",
        "Not this time. The board is revealed below.",
        "Dead air on the wrong tiles. Reveal follows.",
        "The transmitters were elsewhere. Study the reveal.",
    ],
    "near": [
        "So close. Part of it was right.",
        "Some of those were right. Not all.",
        "Half a chord. Not the whole one.",
    ],
    "gave_up": [
        "Off the air. The board is revealed.",
        "Signing off early. Here is where they were.",
    ],
    "start": [
        "Receiver on. Ping a tile to listen.",
        "Headphones on. Where would you listen first?",
        "The band is open. Pick a tile.",
        "Someone is out there. Find them.",
    ],
}


def _pick(kind, salt):
    options = _LINES[kind]
    return options[salt % len(options)]


def flavour_for_reading(reading, radius, salt):
    if reading <= 0:
        return _pick("zero", salt)
    if reading > radius:
        return _pick("stacked", salt)
    if reading <= max(1, radius // 2):
        return _pick("low", salt)
    return _pick("mid", salt)


# --------------------------------------------------------------------------
# Engine state

_DEFAULT_SETTINGS = {"mode": "easy", "assist_shading": True, "ascii_share": False, "show_streaks": False, "last_preset": "easy"}


def _fresh_state():
    return {
        "days": {},
        "practice": None,
        "practice_stats": {key: {"played": 0, "won": 0, "pings_hist": [0] * PRESETS[key]["budget"]} for key in PRESET_ORDER},
        "settings": dict(_DEFAULT_SETTINGS),
        "earned": {},
        "flags": {"shared": False},
        "onboarding_seen": False,
        "session": {"type": "daily", "date": None, "mode": "easy", "marks": []},
    }


S = _fresh_state()
_cur = None  # runtime: {"type", "date", "mode", "puzzle"}
_last_today = None


def reset_engine():
    """Back to a brand-new player (also used by the in-game reset)."""
    global S, _cur, _last_today
    S = _fresh_state()
    _cur = None
    _last_today = None


def _day_key(date_text, mode):
    return "%s:%s" % (date_text, mode)


def _parse_day_key(key):
    if not isinstance(key, str):
        return None
    parts = key.split(":")
    if len(parts) != 2 or parse_date(parts[0]) is None:
        return None
    if parts[1] not in PRESETS or not PRESETS[parts[1]]["daily"]:
        return None
    return parts[0], parts[1]


def _new_record(kind, mode, code=None):
    rec = {
        "mode": mode, "kind": kind, "pings": [], "marks": [], "guess": [],
        "result": "inprogress", "pings_used": 0, "par": None,
    }
    if code is not None:
        rec["code"] = code
    return rec


# ---- record validation (used on load and when re-opening a puzzle) --------


def _clean_cell_list(value, board, max_len, interior_only):
    if not isinstance(value, list) or len(value) > max_len:
        return None
    out = []
    seen = set()
    for item in value:
        if not isinstance(item, list) or len(item) != 2:
            return None
        r, c = item
        if not (_is_int(r) and _is_int(c)) or not (0 <= r < board.n and 0 <= c < board.n):
            return None
        cell = r * board.n + c
        if cell in seen or (interior_only and cell not in board.interior):
            return None
        seen.add(cell)
        out.append([r, c])
    return out


def _clean_record(raw, expected_kinds, expected_mode=None):
    """A validated deep copy of a record, or None if it is unusable."""
    if not isinstance(raw, dict):
        return None
    mode = raw.get("mode")
    if not isinstance(mode, str) or mode not in PRESETS:
        return None
    if expected_mode is not None and mode != expected_mode:
        return None
    kind = raw.get("kind")
    if not isinstance(kind, str) or kind not in expected_kinds:
        return None
    preset = PRESETS[mode]
    board = board_for(mode)
    pings = raw.get("pings")
    if not isinstance(pings, list) or len(pings) > preset["budget"]:
        return None
    clean_pings = []
    seen = set()
    max_reading = preset["k"] * preset["radius"]
    for item in pings:
        if not isinstance(item, list) or len(item) != 3:
            return None
        r, c, v = item
        if not (_is_int(r) and _is_int(c) and _is_int(v)):
            return None
        if not (0 <= r < board.n and 0 <= c < board.n and 0 <= v <= max_reading):
            return None
        if (r, c) in seen:
            return None
        seen.add((r, c))
        clean_pings.append([r, c, v])
    marks = _clean_cell_list(raw.get("marks", []), board, preset["k"], True)
    guess = _clean_cell_list(raw.get("guess", []), board, preset["k"], True)
    if marks is None or guess is None:
        return None
    result = raw.get("result")
    if not isinstance(result, str) or result not in ("inprogress", "won", "lost"):
        return None
    if result == "inprogress":
        guess = []
    par = raw.get("par")
    if par is not None and not (_is_int(par) and 1 <= par <= preset["budget"]):
        return None
    if result == "won" and len(guess) != preset["k"]:
        return None
    rec = {
        "mode": mode, "kind": kind, "pings": clean_pings, "marks": marks, "guess": guess,
        "result": result, "pings_used": len(clean_pings), "par": par,
    }
    if kind == "practice":
        parsed = parse_practice_code(raw.get("code"))
        if parsed is None or parsed[0] != mode:
            return None
        rec["code"] = parsed[1]
    return rec


def _verify_against_puzzle(rec, puzzle):
    """Lazy repair when a stored record is opened and its puzzle regenerated:
    stored readings are recomputed from the true transmitters, and a 'won'
    that does not match the truth is downgraded to 'lost'. (A hand-edited
    save cannot improve a result this way; it stays a local toy either way.)"""
    board = board_for(rec["mode"])
    n = board.n
    for ping in rec["pings"]:
        ping[2] = reading_at(board, puzzle.transmitters, ping[0] * n + ping[1])
    truth = sorted(puzzle.transmitters)
    if rec["result"] == "won":
        guess = sorted(r * n + c for r, c in rec["guess"])
        if guess != truth:
            rec["result"] = "lost"
    if rec["result"] != "inprogress":
        rec["par"] = puzzle.par


# ---- stats (derived, never trusted from a save) ---------------------------


def _finished(rec):
    return rec["result"] in ("won", "lost")


def _mode_records(mode, kind):
    for key, rec in S["days"].items():
        if rec["mode"] == mode and rec["kind"] == kind and _parse_day_key(key):
            yield key, rec


def _streaks(win_dates, today, lost_today):
    """(current, best) run lengths over a set of date ordinals."""
    if not win_dates:
        return 0, 0
    ordered = sorted(win_dates)
    best = run = 1
    for prev, cur in zip(ordered, ordered[1:]):
        run = run + 1 if cur == prev + 1 else 1
        best = max(best, run)
    if lost_today:
        return 0, best
    today_ord = today.toordinal()
    anchor = today_ord if today_ord in win_dates else (today_ord - 1 if today_ord - 1 in win_dates else None)
    if anchor is None:
        return 0, best
    length = 0
    while anchor - length in win_dates:
        length += 1
    return length, best


def compute_stats(mode, kind, today_text):
    """Stats for one mode and one kind ("daily" or "archive"), from `days`."""
    budget = PRESETS[mode]["budget"]
    today = parse_date(today_text)
    hist = [0] * budget
    played = won = 0
    win_dates = set()
    last_played = None
    lost_today = False
    for key, rec in _mode_records(mode, kind):
        if not _finished(rec):
            continue
        date_text = key.split(":")[0]
        played += 1
        if last_played is None or date_text > last_played:
            last_played = date_text
        if rec["result"] == "won":
            won += 1
            hist[max(rec["pings_used"], 1) - 1] += 1
            win_dates.add(parse_date(date_text).toordinal())
        elif date_text == today_text and kind == "daily":
            lost_today = True
    streak, best = _streaks(win_dates, today, lost_today) if kind == "daily" else (0, 0)
    return {
        "played": played, "won": won, "streak": streak, "best_streak": best,
        "last_played_utc": last_played, "pings_hist": hist,
    }


def _practice_stats(mode):
    stats = S["practice_stats"][mode]
    return {"played": stats["played"], "won": stats["won"], "pings_hist": list(stats["pings_hist"])}


# ---- achievements ---------------------------------------------------------


def _earn(achievement_id, newly):
    if achievement_id in ACHIEVEMENT_IDS and achievement_id not in S["earned"]:
        S["earned"][achievement_id] = _last_today or utc_today()
        newly.append(achievement_id)


def _rec_meta(rec):
    preset = PRESETS[rec["mode"]]
    return preset["budget"], preset["radius"]


def evaluate_achievements():
    """Recompute what is earned from all recorded play; returns the ids that
    are newly earned. Earned status is permanent once granted (a save that
    later prunes old days never loses one)."""
    newly = []
    today = _last_today or utc_today()
    records = [rec for _key, rec in S["days"].items()]
    if S["practice"] is not None:
        records.append(S["practice"])

    for rec in records:
        budget, radius = _rec_meta(rec)
        zeros = sum(1 for p in rec["pings"] if p[2] == 0)
        if zeros >= 3:
            _earn("silent_night", newly)
        if any(p[2] > radius for p in rec["pings"]):
            _earn("overlap", newly)
        if not _finished(rec):
            continue
        _earn("first_contact", newly)
        if rec["result"] == "lost":
            _earn("static", newly)
            continue
        used = rec["pings_used"]
        par = rec.get("par")
        if par is not None and used <= par:
            _earn("clean_signal", newly)
        if par is not None and used < par:
            _earn("under_par", newly)
        if budget - used >= 4:
            _earn("lucky_guess", newly)
        if used == budget:
            _earn("last_gasp", newly)
        if rec["mode"] == "hard":
            _earn("hard_copy", newly)
        if rec["mode"] in ("wide", "bigsky"):
            _earn("wide_open", newly)

    total_practice = sum(S["practice_stats"][m]["played"] for m in PRESET_ORDER)
    if total_practice >= 1:
        _earn("first_contact", newly)
    if total_practice >= 5:
        _earn("dial_practice", newly)
    for m in PRESET_ORDER:
        stats = S["practice_stats"][m]
        if stats["won"] >= 1:
            if m == "hard":
                _earn("hard_copy", newly)
            if m in ("wide", "bigsky"):
                _earn("wide_open", newly)
    if any(S["practice_stats"][m]["played"] - S["practice_stats"][m]["won"] > 0 for m in PRESET_ORDER):
        _earn("static", newly)

    archive_finished = sum(1 for _k, rec in S["days"].items() if rec["kind"] == "archive" and _finished(rec))
    if archive_finished >= 10:
        _earn("archivist", newly)

    # AN-11: no streak by default. The three streak badges are earned only while "Show my daily streak" is on
    # (they are recomputed from the played days, so switching it on later awards what the history already earned).
    if S["settings"].get("show_streaks"):
        best = 0
        for m in DAILY_MODES:
            best = max(best, compute_stats(m, "daily", today)["best_streak"])
        if best >= 3:
            _earn("three_in_a_row", newly)
        if best >= 7:
            _earn("week_on_air", newly)
        if best >= 30:
            _earn("month_on_air", newly)

    won_by_date = {}
    for key, rec in S["days"].items():
        parsed = _parse_day_key(key)
        if parsed and rec["kind"] == "daily" and rec["result"] == "won":
            won_by_date.setdefault(parsed[0], set()).add(rec["mode"])
        if parsed and rec["kind"] == "daily" and _finished(rec) and puzzle_number(parsed[0]) >= 100:
            _earn("puzzle_100", newly)
    if any({"easy", "hard"} <= modes for modes in won_by_date.values()):
        _earn("both_bands", newly)
    if S["flags"].get("shared"):
        _earn("show_off", newly)
    return newly


def achievement_ids_earned():
    return [a for a in ACHIEVEMENT_IDS if a in S["earned"]]


def achievements_summary():
    return [
        {
            "id": a["id"], "label": a["label"], "description": a["description"],
            "earned": a["id"] in S["earned"], "date": S["earned"].get(a["id"]),
        }
        for a in ACHIEVEMENTS
    ]


# ---- the leaderboard number ----------------------------------------------


def overall_best_streak(today_text):
    return max(compute_stats(m, "daily", today_text)["best_streak"] for m in DAILY_MODES)


# --------------------------------------------------------------------------
# Session / record plumbing


def _today():
    """Today's UTC date, clamped to launch day (before EPOCH the game behaves
    as if it were launch day, so a pre-launch dev build still works)."""
    global _last_today
    _last_today = max(utc_today(), EPOCH)
    return _last_today


def _current_record():
    """The stored record for the open puzzle, or None if nothing is stored yet."""
    if _cur is None:
        return None
    if _cur["type"] == "practice":
        rec = S["practice"]
        return rec if rec is not None and rec.get("code") == _cur["code"] else None
    return S["days"].get(_day_key(_cur["date"], _cur["mode"]))


def _pending_marks():
    return S["session"]["marks"]


def _marks():
    rec = _current_record()
    return rec["marks"] if rec is not None else _pending_marks()


def _ensure_record(today_text):
    """Create the stored record on the first ping/commit/give-up, deciding
    daily-vs-archive right then: a puzzle is a daily only if its first ping
    happens on its own UTC date."""
    rec = _current_record()
    if rec is not None:
        return rec
    if _cur["type"] == "practice":
        raise RuntimeError("practice record missing")
    kind = "daily" if _cur["date"] == today_text else "archive"
    rec = _new_record(kind, _cur["mode"])
    rec["marks"] = [list(m) for m in _pending_marks()]
    S["days"][_day_key(_cur["date"], _cur["mode"])] = rec
    S["session"]["marks"] = []
    _prune_days()
    return rec


def _prune_days():
    if len(S["days"]) <= MAX_DAYS:
        return
    keep_open = _day_key(_cur["date"], _cur["mode"]) if _cur and _cur["type"] != "practice" else None
    ordered = sorted(S["days"], key=lambda k: (k.split(":")[0], k))
    excess = len(S["days"]) - MAX_DAYS
    for key in ordered:
        if excess <= 0:
            break
        if key == keep_open:
            continue
        del S["days"][key]
        excess -= 1


def _open_daily(date_text, mode, today_text):
    global _cur
    if not isinstance(mode, str) or mode not in DAILY_MODES:
        return "That mode has no daily puzzle."
    date = parse_date(date_text)
    if date is None:
        return "That is not a valid date."
    if date_text < EPOCH:
        return "There is no puzzle before %s." % EPOCH
    if date_text > today_text:
        return "That puzzle has not been broadcast yet."
    puzzle = daily_puzzle(date_text, mode)
    _cur = {"type": "daily" if date_text == today_text else "archive", "date": date_text, "mode": mode, "puzzle": puzzle}
    rec = S["days"].get(_day_key(date_text, mode))
    if rec is not None:
        _verify_against_puzzle(rec, puzzle)
    S["session"] = {"type": _cur["type"], "date": date_text, "mode": mode, "marks": []}
    S["settings"]["mode"] = mode
    return None


def _open_practice(mode, code, today_text):
    global _cur
    if code is None:
        if not isinstance(mode, str) or mode not in PRESETS:
            return "Unknown preset."
        code = new_practice_code(mode)
    else:
        parsed = parse_practice_code(code)
        if parsed is None:
            return "That practice code is not valid."
        mode, code = parsed
    puzzle = puzzle_for_seed(mode, practice_seed(mode, code))
    _cur = {"type": "practice", "date": None, "mode": mode, "puzzle": puzzle, "code": code}
    rec = S["practice"]
    if rec is None or rec.get("code") != code:
        S["practice"] = _new_record("practice", mode, code)
    else:
        _verify_against_puzzle(rec, puzzle)
    S["session"] = {"type": "practice", "date": None, "mode": mode, "marks": []}
    S["settings"]["last_preset"] = mode
    return None


def _label_for_cur():
    p = PRESETS[_cur["mode"]]
    if _cur["type"] == "practice":
        return "Practice %s · %s" % (_cur["code"], p["label"])
    kind = "Daily" if _cur["type"] == "daily" else "Archive"
    return "Signal #%d · %s · %s" % (puzzle_number(_cur["date"]), p["label"], kind)


def _boot(today_text):
    """Resume the saved session; a stale daily becomes today's daily."""
    session = S["session"]
    mode = session["mode"] if session["mode"] in PRESETS else "easy"
    err = None
    if session["type"] == "practice" and S["practice"] is not None:
        err = _open_practice(S["practice"]["mode"], S["practice"]["code"], today_text)
    elif session["type"] == "archive" and session["date"] and EPOCH <= session["date"] < today_text and mode in DAILY_MODES:
        err = _open_daily(session["date"], mode, today_text)
    else:
        daily_mode = S["settings"]["mode"] if S["settings"]["mode"] in DAILY_MODES else "easy"
        err = _open_daily(today_text, daily_mode, today_text)
    return err


# --------------------------------------------------------------------------
# View (what the UI draws)


def _view():
    today = _last_today or utc_today()
    mode = _cur["mode"]
    preset = PRESETS[mode]
    board = board_for(mode)
    puzzle = _cur["puzzle"]
    rec = _current_record()
    pings = rec["pings"] if rec is not None else []
    marks = _marks()
    result = rec["result"] if rec is not None else "inprogress"
    finished = result in ("won", "lost")
    ascii_mode = S["settings"]["ascii_share"]
    ping_views = []
    for r, c, v in pings:
        level = reading_level(v, preset["top"])
        ping_views.append({
            "r": r, "c": c, "v": v, "level": level, "fill": reading_fill(v, preset["top"]),
            "glyph": glyph_for(level), "label": cell_label(r, c),
        })
    assist_on = (
        preset["assist"] and S["settings"]["assist_shading"] and not finished and bool(pings)
    )
    possible = None
    if assist_on:
        n = board.n
        cells = possible_cells(board, [(r * n + c, v) for r, c, v in pings])
        possible = [[cell // n, cell % n] for cell in cells]
    result_view = None
    truth = None
    if finished:
        n = board.n
        truth = [[t // n, t % n] for t in puzzle.transmitters]
        used = rec["pings_used"]
        won = result == "won"
        result_view = {
            "won": won, "pings_used": used, "budget": preset["budget"], "par": puzzle.par,
            "under_par": won and used < puzzle.par, "at_par": won and used <= puzzle.par,
            "share_ready": True,
        }
    stats = None
    if _cur["type"] != "practice":
        stats = compute_stats(mode, "daily", today)
    number = puzzle_number(_cur["date"]) if _cur["date"] else None
    tomorrow = (parse_date(today) + datetime.timedelta(days=1)).isoformat()
    return {
        "session": {
            "type": _cur["type"], "date": _cur["date"], "mode": mode, "label": _label_for_cur(),
            "number": number, "code": _cur.get("code"),
        },
        "board": {
            "n": board.n, "k": board.k, "radius": board.radius, "budget": preset["budget"],
            "par": puzzle.par, "top": preset["top"], "assist": preset["assist"],
            "spacing": board.spacing, "mode_label": preset["label"],
        },
        "pings": ping_views,
        "marks": [list(m) for m in marks],
        "status": result,
        "pings_left": preset["budget"] - len(pings),
        "can_commit": (not finished) and len(marks) == board.k,
        "possible": possible,
        "truth": truth,
        "guess": [list(g) for g in rec["guess"]] if (rec is not None and finished) else None,
        "result": result_view,
        "stats": stats,
        "ach": {"earned": len(S["earned"]), "total": len(ACHIEVEMENTS)},
        "presets": [
            {"key": k, "label": PRESETS[k]["label"], "size": PRESETS[k]["size"], "k": PRESETS[k]["k"],
             "budget": PRESETS[k]["budget"], "daily": PRESETS[k]["daily"]}
            for k in PRESET_ORDER
        ],
        "settings": dict(S["settings"]),
        "today": today,
        "epoch": EPOCH,
        "next_utc": tomorrow,
        "first_run": not S["onboarding_seen"] and not pings,
        "ascii": ascii_mode,
    }


def _response(ok=True, error=None, message=None, newly=None, events=None, dirty=False, extra=None):
    payload = {
        "ok": ok, "error": error, "message": message,
        "view": _view() if _cur is not None else None,
        "new": [
            {"id": a["id"], "label": a["label"], "description": a["description"]}
            for a in ACHIEVEMENTS if a["id"] in (newly or [])
        ],
        "events": events or [],
        "dirty": dirty,
    }
    if extra:
        payload.update(extra)
    return payload


# --------------------------------------------------------------------------
# Actions


def _cell_from(req, board):
    r, c = req.get("r"), req.get("c")
    if not (_is_int(r) and _is_int(c)) or not (0 <= r < board.n and 0 <= c < board.n):
        return None
    return r, c


def _action_ping(req, today_text):
    board = board_for(_cur["mode"])
    preset = PRESETS[_cur["mode"]]
    cell_rc = _cell_from(req, board)
    if cell_rc is None:
        return _response(False, "That tile is not on the board.")
    rec = _current_record()
    if rec is not None and _finished(rec):
        return _response(False, "This puzzle is finished.")
    if rec is not None and len(rec["pings"]) >= preset["budget"]:
        return _response(False, "Out of pings. Mark your answer and commit.")
    r, c = cell_rc
    if rec is not None and any(p[0] == r and p[1] == c for p in rec["pings"]):
        return _response(False, "You already pinged %s." % cell_label(r, c))
    rec = _ensure_record(today_text)
    reading = reading_at(board, _cur["puzzle"].transmitters, r * board.n + c)
    rec["pings"].append([r, c, reading])
    rec["pings_used"] = len(rec["pings"])
    salt = fnv1a32("%s:%d:%d" % (_cur["puzzle"].seed, r, c))
    message = "%s reads %d. %s" % (cell_label(r, c), reading, flavour_for_reading(reading, board.radius, salt))
    S["onboarding_seen"] = True
    newly = evaluate_achievements()
    return _response(message=message, newly=newly, dirty=True)


def _action_mark(req):
    board = board_for(_cur["mode"])
    cell_rc = _cell_from(req, board)
    if cell_rc is None:
        return _response(False, "That tile is not on the board.")
    rec = _current_record()
    if rec is not None and _finished(rec):
        return _response(False, "This puzzle is finished.")
    r, c = cell_rc
    if (r * board.n + c) not in board.interior:
        return _response(False, "Nothing broadcasts from the outer ring.")
    marks = _marks()
    existing = [i for i, m in enumerate(marks) if m[0] == r and m[1] == c]
    if existing:
        del marks[existing[0]]
        return _response(message="Cleared the marker on %s." % cell_label(r, c), dirty=True)
    if len(marks) >= board.k:
        return _response(False, "All %d markers are placed. Clear one first." % board.k)
    marks.append([r, c])
    return _response(message="Marked %s." % cell_label(r, c), dirty=True)


def _action_clear_marks():
    rec = _current_record()
    if rec is not None and _finished(rec):
        return _response(False, "This puzzle is finished.")
    del _marks()[:]
    return _response(message="Markers cleared.", dirty=True)


def _finish(rec, won, today_text, gave_up=False):
    puzzle = _cur["puzzle"]
    rec["result"] = "won" if won else "lost"
    rec["guess"] = [list(m) for m in rec["marks"]]
    rec["pings_used"] = len(rec["pings"])
    rec["par"] = puzzle.par
    events = []
    if rec["kind"] == "practice":
        stats = S["practice_stats"][rec["mode"]]
        stats["played"] += 1
        if won:
            stats["won"] += 1
            stats["pings_hist"][max(rec["pings_used"], 1) - 1] += 1
    board = board_for(rec["mode"])
    preset = PRESETS[rec["mode"]]
    n = board.n
    truth = set(puzzle.transmitters)
    right = len([1 for r, c in rec["guess"] if r * n + c in truth])
    salt = fnv1a32(puzzle.seed)
    if won:
        if rec["pings_used"] == preset["budget"]:
            line = _pick("win_last", salt)
        elif rec["pings_used"] <= puzzle.par:
            line = _pick("win_par", salt)
        else:
            line = _pick("win", salt)
    elif gave_up:
        line = _pick("gave_up", salt)
    elif right > 0:
        line = "%s %d of %d were right." % (_pick("near", salt), right, board.k)
    else:
        line = _pick("lose", salt)
    newly = evaluate_achievements()
    if rec["kind"] == "daily" and won and S["settings"].get("show_streaks"):
        best = overall_best_streak(today_text)
        if best >= 1:
            events.append({
                "type": "leaderboard", "game": GAME_ID, "board": "best_streak",
                "score": best, "detail": "%s streak" % rec["mode"],
            })
    return line, newly, events


def _action_commit(today_text):
    board = board_for(_cur["mode"])
    rec = _current_record()
    if rec is not None and _finished(rec):
        return _response(False, "This puzzle is finished.")
    marks = _marks()
    if len(marks) != board.k:
        return _response(False, "Mark exactly %d tiles before committing." % board.k)
    rec = _ensure_record(today_text)
    n = board.n
    won = sorted(r * n + c for r, c in rec["marks"]) == sorted(_cur["puzzle"].transmitters)
    line, newly, events = _finish(rec, won, today_text)
    S["onboarding_seen"] = True
    return _response(message=line, newly=newly, events=events, dirty=True)


def _action_give_up(today_text):
    rec = _current_record()
    if rec is not None and _finished(rec):
        return _response(False, "This puzzle is finished.")
    rec = _ensure_record(today_text)
    line, newly, events = _finish(rec, False, today_text, gave_up=True)
    return _response(message=line, newly=newly, events=events, dirty=True)


def _action_share(req):
    rec = _current_record()
    if rec is None or not _finished(rec):
        return _response(False, "Finish the puzzle before sharing.")
    if "ascii" in req and isinstance(req["ascii"], bool):
        S["settings"]["ascii_share"] = req["ascii"]
    number = puzzle_number(_cur["date"]) if _cur["date"] else 0
    text = build_share_text(rec, _cur["mode"], number, S["settings"]["ascii_share"])
    S["flags"]["shared"] = True
    newly = evaluate_achievements()
    return _response(message="Result copied.", newly=newly, dirty=True, extra={"text": text})


_SETTING_TYPES = {"assist_shading": bool, "ascii_share": bool, "show_streaks": bool}


def _action_settings(req, today_text=None):
    changed = False
    before_streaks = S["settings"].get("show_streaks")
    for key, kind in _SETTING_TYPES.items():
        if key in req:
            if not isinstance(req[key], kind):
                return _response(False, "Bad value for %s." % key)
            S["settings"][key] = req[key]
            changed = True
    if "last_preset" in req:
        value = req["last_preset"]
        if not isinstance(value, str) or value not in PRESETS:
            return _response(False, "Unknown preset.")
        S["settings"]["last_preset"] = value
        changed = True
    newly = None
    if today_text is not None and S["settings"].get("show_streaks") and not before_streaks:
        newly = evaluate_achievements()      # AN-11: switching streaks on awards what the history already earned
    return _response(newly=newly, dirty=changed)


def _action_stats(today_text):
    modes = {}
    for m in PRESET_ORDER:
        entry = {"label": PRESETS[m]["label"], "daily_mode": PRESETS[m]["daily"], "practice": _practice_stats(m)}
        if PRESETS[m]["daily"]:
            entry["daily"] = compute_stats(m, "daily", today_text)
            entry["archive"] = compute_stats(m, "archive", today_text)
        modes[m] = entry
    return _response(extra={"stats": modes, "best_streak": overall_best_streak(today_text) if S["settings"].get("show_streaks") else None})


def handle_dict(req):
    """Dispatch one request dict; returns the response dict."""
    if not isinstance(req, dict) or not isinstance(req.get("action"), str):
        return _response(False, "Bad request.")
    action = req["action"]
    today_text = _today()
    if action == "reset":
        reset_engine()
        err = _boot(_today())
        return _response(err is None, err, dirty=True)
    if action == "boot":
        err = _boot(today_text)
        newly = evaluate_achievements()
        return _response(err is None, err, newly=newly, dirty=bool(newly), extra={"changelog": CHANGELOG})
    if _cur is None:
        return _response(False, "Engine not started: send boot first.")
    if action == "view":
        return _response()
    if action == "open":
        err = _open_daily(req.get("date"), req.get("mode"), today_text)
        return _response(err is None, err, dirty=err is None)
    if action == "practice":
        err = _open_practice(req.get("mode"), req.get("code"), today_text)
        return _response(err is None, err, dirty=err is None)
    if action == "ping":
        return _action_ping(req, today_text)
    if action == "mark":
        return _action_mark(req)
    if action == "clear_marks":
        return _action_clear_marks()
    if action == "commit":
        return _action_commit(today_text)
    if action == "give_up":
        return _action_give_up(today_text)
    if action == "share":
        return _action_share(req)
    if action == "settings":
        return _action_settings(req, today_text)
    if action == "stats":
        return _action_stats(today_text)
    if action == "achievements":
        return _response(extra={"achievements": achievements_summary()})
    if action == "ack_onboarding":
        S["onboarding_seen"] = True
        return _response(dirty=True)
    return _response(False, "Unknown action.")


def handle(request):
    """The one entry point app.js calls: JSON text in, JSON text out."""
    try:
        req = json.loads(request) if isinstance(request, str) else request
        return json.dumps(handle_dict(req))
    except Exception as exc:  # noqa: BLE001 -- the UI must never see a raw traceback
        return json.dumps({"ok": False, "error": "Engine error: %s" % exc, "view": None, "new": [], "events": [], "dirty": False})


# --------------------------------------------------------------------------
# Save / load (shared/save-widget.js contract)


def _json_copy(value):
    return json.loads(json.dumps(value))


def get_state():
    today = _last_today or _today()
    derived = {}
    for m in DAILY_MODES:
        st = compute_stats(m, "daily", today)
        derived[m] = st
    return {
        "schema": SCHEMA,
        "stats": derived,
        "days": _json_copy(S["days"]),
        "practice": _json_copy(S["practice"]),
        "practice_stats": _json_copy(S["practice_stats"]),
        "settings": dict(S["settings"]),
        "earned": dict(S["earned"]),
        "flags": dict(S["flags"]),
        "onboarding_seen": S["onboarding_seen"],
        "session": _json_copy(S["session"]),
        "achievements_earned": achievement_ids_earned(),
    }


def _rank(rec):
    """Ordering key for merging two records of the same puzzle: finished
    beats in-progress, a daily beats an archive replay (so replaying a
    finished daily elsewhere cannot rewrite the streak), a win beats a loss,
    fewer pings beats more. Ties fall back to the canonical JSON so the merge
    is commutative."""
    finished = _finished(rec)
    return (
        1 if finished else 0,
        1 if rec["kind"] == "daily" else 0,
        1 if rec["result"] == "won" else 0,
        -rec["pings_used"] if finished else rec["pings_used"],
        json.dumps(rec, sort_keys=True),
    )


def _merge_days(local, incoming):
    merged = dict(local)
    for key, rec in incoming.items():
        if key not in merged or _rank(rec) > _rank(merged[key]):
            merged[key] = rec
    return merged


def _clean_settings(raw):
    out = dict(_DEFAULT_SETTINGS)
    if not isinstance(raw, dict):
        return out
    mode = raw.get("mode")
    if isinstance(mode, str) and mode in DAILY_MODES:
        out["mode"] = mode
    for key in ("assist_shading", "ascii_share", "show_streaks"):
        if isinstance(raw.get(key), bool):
            out[key] = raw[key]
    last = raw.get("last_preset")
    if isinstance(last, str) and last in PRESETS:
        out["last_preset"] = last
    return out


def _clean_practice_stats(raw):
    out = {}
    for key in PRESET_ORDER:
        budget = PRESETS[key]["budget"]
        entry = raw.get(key) if isinstance(raw, dict) else None
        played = won = 0
        hist = [0] * budget
        if isinstance(entry, dict):
            if _is_int(entry.get("played")) and entry["played"] >= 0:
                played = entry["played"]
            if _is_int(entry.get("won")) and 0 <= entry["won"] <= played:
                won = entry["won"]
            h = entry.get("pings_hist")
            if isinstance(h, list) and len(h) == budget and all(_is_int(x) and x >= 0 for x in h):
                hist = list(h)
        out[key] = {"played": played, "won": won, "pings_hist": hist}
    return out


def _clean_earned(raw):
    out = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(key, str) and key in ACHIEVEMENT_IDS and isinstance(value, str) and parse_date(value):
                out[key] = value
    return out


def _clean_days(raw):
    out = {}
    if not isinstance(raw, dict):
        return out
    for key, rec in raw.items():
        parsed = _parse_day_key(key)
        if parsed is None:
            continue
        clean = _clean_record(rec, ("daily", "archive"), expected_mode=parsed[1])
        if clean is not None:
            out[key] = clean
    return out


def _notify_ui():
    """Tell app.js the state changed under it (a save was just loaded)."""
    try:
        import js  # noqa: WPS433
        callback = getattr(js.window, "signalOnStateLoaded", None)
        if callback:
            callback()
    except Exception:  # noqa: BLE001 -- no browser, or the UI is not up yet
        pass


def load_state(data):
    """Merge a saved state in (inverse of get_state). Returns True if the
    data was usable. Junk never raises: bad fields are dropped one by one.
    Days are unioned (never lost), earned achievements are unioned, practice
    counters take the larger value, settings come from the save. Streaks and
    stats are recomputed from `days`, never trusted from the blob."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            return False
    if not isinstance(data, dict):
        return False
    schema = data.get("schema", SCHEMA)
    if not _is_int(schema) or schema < 1 or schema > SCHEMA:
        return False
    S["days"] = _merge_days(S["days"], _clean_days(data.get("days")))
    incoming_stats = _clean_practice_stats(data.get("practice_stats"))
    for key in PRESET_ORDER:
        mine, theirs = S["practice_stats"][key], incoming_stats[key]
        mine["played"] = max(mine["played"], theirs["played"])
        mine["won"] = min(max(mine["won"], theirs["won"]), mine["played"])
        mine["pings_hist"] = [max(a, b) for a, b in zip(mine["pings_hist"], theirs["pings_hist"])]
    if S["practice"] is None:
        S["practice"] = _clean_record(data.get("practice"), ("practice",))
    for key, value in _clean_earned(data.get("earned")).items():
        if key not in S["earned"] or value < S["earned"][key]:
            S["earned"][key] = value
    if isinstance(data.get("settings"), dict):
        S["settings"] = _clean_settings(data["settings"])
    flags = data.get("flags")
    if isinstance(flags, dict) and flags.get("shared") is True:
        S["flags"]["shared"] = True
    if data.get("onboarding_seen") is True:
        S["onboarding_seen"] = True
    _prune_days()
    evaluate_achievements()
    _notify_ui()
    return True
