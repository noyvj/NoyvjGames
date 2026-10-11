"""Rule Finder -- the rule language: items, clauses, rules, and the one judge of whether two rules agree.

Everything here is pure and deterministic (no clock, no random source). A DOMAIN is a fixed, ordered list of items:

  num    the integers 0 to 99                                (item key "42")
  shape  strings of 3 to 6 tiles from four shapes c s t d     (item key "cstd": circle, square, triangle, diamond)
  grid   3 by 3 patterns of filled and empty squares          (item key "#.#.#.#.#": nine marks, row by row)

A CLAUSE is one named property of an item ("is even", "starts with a circle"). A RULE is one to three clauses, each one
optionally negated (NOT), joined by AND / OR and read left to right: ((a OP b) OP c). Negating a single clause is enough
for every use of NOT (not (a and b) is the same as (not a) or (not b)), so the language needs nothing more.

A rule is judged by its TABLE: a Python int with bit i set when item i of the domain is let through. Two rules agree
when their tables are equal, which is exactly "agree on every item in the domain" (extensional equality, by exhaustive
evaluation). The Sorter's answer to a test is one bit of the hidden rule's table.
"""

from collections import namedtuple
from itertools import product

NUM, SHAPE, GRID = "num", "shape", "grid"
KINDS = (NUM, SHAPE, GRID)
SUBJECT = {NUM: "number", SHAPE: "string", GRID: "pattern"}
MAX_CLAUSES = 3

SHAPE_LETTERS = "cstd"
SHAPE_NAMES = {"c": "circle", "s": "square", "t": "triangle", "d": "diamond"}
SHAPE_RANK = {"c": 0, "s": 1, "t": 2, "d": 3}      # smallest to largest
SHAPE_LENS = (3, 4, 5, 6)
GRID_CELLS = 9

Clause = namedtuple("Clause", "id family yes no fn")
Rule = namedtuple("Rule", "lits ops")                 # lits: ((clause id, negated 0/1), ...), ops: ("and" | "or", ...)

PRIMES = frozenset(n for n in range(2, 100) if all(n % d for d in range(2, 10) if d < n))
SQUARES = frozenset(i * i for i in range(10))

# family id -> (label, nudge phrase). The nudge never says which clause or how many are joined by what.
FAMILIES = {
    "parity": ("Odd and even", "whether the numbers are odd or even"),
    "size": ("How big", "how big the number is"),
    "multiples": ("Multiples", "whether the number divides evenly by something"),
    "digit sums": ("Digit sums", "what the digits add up to"),
    "digits": ("Digits", "which digits appear in the number"),
    "special": ("Special numbers", "whether the number is one of the famous kinds"),
    "digit order": ("Digit order", "how the two digits compare with each other"),
    "length": ("Length", "how many tiles there are"),
    "which shapes": ("Which shapes", "which shapes are in the string"),
    "counts": ("Counts", "how many of one shape there are"),
    "ends": ("Ends", "what the first and last tiles are"),
    "repeats": ("Repeats", "whether a shape repeats right next to itself"),
    "mirror": ("Mirror", "how the string reads backwards"),
    "order": ("Order", "whether the tiles grow or shrink along the string"),
    "variety": ("Variety", "how many different shapes are used"),
    "neighbours": ("Neighbours", "which shapes sit next to each other"),
    "how many": ("How many", "how many squares are filled"),
    "corners": ("Corners and centre", "the corners and the middle square"),
    "lines": ("Lines", "whether a whole row, column or diagonal is filled"),
    "symmetry": ("Symmetry", "whether the pattern is the same when flipped or turned"),
    "edges": ("Edges", "which edges of the pattern are empty"),
    "touching": ("Touching", "whether filled squares touch each other"),
    "balance": ("Balance", "which side of the pattern is fuller"),
}


# ---- clause libraries ---------------------------------------------------------------------------------------------
def _add(out, cid, family, yes, no, fn):
    out.append(Clause(cid, family, yes, no, fn))


def _digits(n):
    return n // 10, n % 10


def _num_clauses():
    out = []
    _add(out, "even", "parity", "is even", "is odd", lambda n: n % 2 == 0)
    for k in (10, 20, 30, 40, 50, 60, 70, 80, 90):
        _add(out, "ge:%d" % k, "size", "is %d or more" % k, "is less than %d" % k, lambda n, k=k: n >= k)
    for k in (3, 4, 5, 6, 7, 8, 9, 10):
        _add(out, "mult:%d" % k, "multiples", "is a multiple of %d" % k, "is not a multiple of %d" % k, lambda n, k=k: n % k == 0)
    _add(out, "dsum_even", "digit sums", "has digits that add up to an even number", "has digits that add up to an odd number",
         lambda n: sum(_digits(n)) % 2 == 0)
    _add(out, "dsum_ge:10", "digit sums", "has digits that add up to 10 or more", "has digits that add up to less than 10",
         lambda n: sum(_digits(n)) >= 10)
    for d in range(1, 10):
        _add(out, "has:%d" % d, "digits", "has a %d in it" % d, "has no %d in it" % d, lambda n, d=d: str(d) in str(n))
    _add(out, "square", "special", "is a square number", "is not a square number", lambda n: n in SQUARES)
    _add(out, "prime", "special", "is a prime number", "is not a prime number", lambda n: n in PRIMES)
    _add(out, "tens_gt", "digit order", "has a tens digit larger than its ones digit",
         "does not have a tens digit larger than its ones digit", lambda n: n // 10 > n % 10)
    _add(out, "ones_gt", "digit order", "has a ones digit larger than its tens digit",
         "does not have a ones digit larger than its tens digit", lambda n: n % 10 > n // 10)
    return out


def _runs(s):
    return any(a == b for a, b in zip(s, s[1:]))


def _rank(s):
    return [SHAPE_RANK[c] for c in s]


def _shape_clauses():
    out = []
    for k in (4, 5, 6):
        _add(out, "len_ge:%d" % k, "length", "has %d or more tiles" % k, "has fewer than %d tiles" % k, lambda s, k=k: len(s) >= k)
    _add(out, "len_even", "length", "has an even number of tiles", "has an odd number of tiles", lambda s: len(s) % 2 == 0)
    for c in SHAPE_LETTERS:
        n = SHAPE_NAMES[c]
        _add(out, "has:" + c, "which shapes", "has a %s in it" % n, "has no %s in it" % n, lambda s, c=c: c in s)
    for c in SHAPE_LETTERS:
        n = SHAPE_NAMES[c]
        _add(out, "twice:" + c, "counts", "has at least two %ss" % n, "has fewer than two %ss" % n, lambda s, c=c: s.count(c) >= 2)
    for c in SHAPE_LETTERS:
        n = SHAPE_NAMES[c]
        _add(out, "first:" + c, "ends", "starts with a %s" % n, "does not start with a %s" % n, lambda s, c=c: s[0] == c)
    for c in SHAPE_LETTERS:
        n = SHAPE_NAMES[c]
        _add(out, "last:" + c, "ends", "ends with a %s" % n, "does not end with a %s" % n, lambda s, c=c: s[-1] == c)
    _add(out, "ends_same", "ends", "starts and ends with the same shape", "starts and ends with different shapes", lambda s: s[0] == s[-1])
    _add(out, "pair", "repeats", "has the same shape twice in a row", "never has the same shape twice in a row", _runs)
    _add(out, "mirror", "mirror", "reads the same backwards", "reads differently backwards", lambda s: s == s[::-1])
    _add(out, "up", "order", "gets larger with every tile", "does not get larger with every tile",
         lambda s: all(b > a for a, b in zip(_rank(s), _rank(s)[1:])))
    _add(out, "down", "order", "gets smaller with every tile", "does not get smaller with every tile",
         lambda s: all(b < a for a, b in zip(_rank(s), _rank(s)[1:])))
    _add(out, "nodown", "order", "never gets smaller from one tile to the next", "gets smaller somewhere along the string",
         lambda s: all(b >= a for a, b in zip(_rank(s), _rank(s)[1:])))
    _add(out, "noup", "order", "never gets larger from one tile to the next", "gets larger somewhere along the string",
         lambda s: all(b <= a for a, b in zip(_rank(s), _rank(s)[1:])))
    for k in (2, 3, 4):
        _add(out, "kinds_ge:%d" % k, "variety", "uses at least %d different shapes" % k, "uses fewer than %d different shapes" % k,
             lambda s, k=k: len(set(s)) >= k)
    letters = SHAPE_LETTERS
    for i in range(4):
        for j in range(i + 1, 4):
            a, b = letters[i], letters[j]
            na, nb = SHAPE_NAMES[a], SHAPE_NAMES[b]
            _add(out, "next:" + a + b, "neighbours", "has a %s right next to a %s" % (na, nb),
                 "never has a %s right next to a %s" % (na, nb),
                 lambda s, a=a, b=b: (a + b) in s or (b + a) in s)
    return out


ROWS = ((0, 1, 2), (3, 4, 5), (6, 7, 8))
COLS = ((0, 3, 6), (1, 4, 7), (2, 5, 8))
DIAGS = ((0, 4, 8), (2, 4, 6))
CORNERS = (0, 2, 6, 8)
FLIP_LR = (2, 1, 0, 5, 4, 3, 8, 7, 6)
FLIP_TB = (6, 7, 8, 3, 4, 5, 0, 1, 2)
TURN = (8, 7, 6, 5, 4, 3, 2, 1, 0)
SIDE_BY_SIDE = tuple((r * 3 + c, r * 3 + c + 1) for r in range(3) for c in range(2)) + tuple((r * 3 + c, r * 3 + c + 3) for r in range(2) for c in range(3))


def _count(p):
    return sum(p)


def _same(p, order):
    return all(p[i] == p[j] for i, j in enumerate(order))


def _grid_clauses():
    out = []
    for k in range(2, 8):
        _add(out, "count_ge:%d" % k, "how many", "has %d or more filled squares" % k, "has fewer than %d filled squares" % k,
             lambda p, k=k: _count(p) >= k)
    _add(out, "count_even", "how many", "has an even number of filled squares", "has an odd number of filled squares", lambda p: _count(p) % 2 == 0)
    for k in (1, 2, 3):
        _add(out, "corners_ge:%d" % k, "corners", "fills at least %d of the four corners" % k, "fills fewer than %d of the four corners" % k,
             lambda p, k=k: sum(p[i] for i in CORNERS) >= k)
    _add(out, "centre", "corners", "has the middle square filled", "has the middle square empty", lambda p: bool(p[4]))
    _add(out, "row", "lines", "has a whole row filled", "has no whole row filled", lambda p: any(all(p[i] for i in r) for r in ROWS))
    _add(out, "col", "lines", "has a whole column filled", "has no whole column filled", lambda p: any(all(p[i] for i in c) for c in COLS))
    _add(out, "diag", "lines", "has a whole diagonal filled", "has no whole diagonal filled", lambda p: any(all(p[i] for i in d) for d in DIAGS))
    _add(out, "sym_lr", "symmetry", "is the same flipped left to right", "changes when flipped left to right", lambda p: _same(p, FLIP_LR))
    _add(out, "sym_tb", "symmetry", "is the same flipped top to bottom", "changes when flipped top to bottom", lambda p: _same(p, FLIP_TB))
    _add(out, "sym_turn", "symmetry", "is the same turned upside down", "changes when turned upside down", lambda p: _same(p, TURN))
    for name, cells in (("top", ROWS[0]), ("bottom", ROWS[2]), ("left", COLS[0]), ("right", COLS[2])):
        _add(out, "empty:" + name, "edges", "has an empty %s %s" % (name, "row" if name in ("top", "bottom") else "column"),
             "has something filled in its %s %s" % (name, "row" if name in ("top", "bottom") else "column"),
             lambda p, cells=cells: not any(p[i] for i in cells))
    _add(out, "touch", "touching", "has two filled squares touching side by side", "has no two filled squares touching side by side",
         lambda p: any(p[i] and p[j] for i, j in SIDE_BY_SIDE))
    _add(out, "top_more", "balance", "has more filled squares in its top row than in its bottom row",
         "does not have more filled squares in its top row than in its bottom row", lambda p: sum(p[i] for i in ROWS[0]) > sum(p[i] for i in ROWS[2]))
    _add(out, "left_more", "balance", "has more filled squares in its left column than in its right column",
         "does not have more filled squares in its left column than in its right column",
         lambda p: sum(p[i] for i in COLS[0]) > sum(p[i] for i in COLS[2]))
    return out


# ---- domains ------------------------------------------------------------------------------------------------------
class Domain:
    """An ordered list of items with a parsed value for each, and a cached table per clause."""

    def __init__(self, kind):
        self.kind = kind
        if kind == NUM:
            self.items = [str(n) for n in range(100)]
            self.vals = list(range(100))
            self.clauses = _num_clauses()
        elif kind == SHAPE:
            self.items = ["".join(t) for n in SHAPE_LENS for t in product(SHAPE_LETTERS, repeat=n)]
            self.vals = list(self.items)
            self.clauses = _shape_clauses()
        else:
            self.items = ["".join("#" if (bits >> (8 - i)) & 1 else "." for i in range(9)) for bits in range(512)]
            self.vals = [tuple(1 if ch == "#" else 0 for ch in key) for key in self.items]
            self.clauses = _grid_clauses()
        self.index = {key: i for i, key in enumerate(self.items)}
        self.size = len(self.items)
        self.full = (1 << self.size) - 1
        self.clause_by_id = {c.id: c for c in self.clauses}
        self.clause_ids = [c.id for c in self.clauses]
        self._tables = {}

    def normalize(self, raw):
        """The canonical key of a raw item (a string or, for numbers, an int), or None when it is not in the domain."""
        if self.kind == NUM:
            if isinstance(raw, bool):
                return None
            if isinstance(raw, int):
                key = str(raw)
            elif isinstance(raw, str) and raw.isdigit() and raw.isascii() and len(raw) <= 3:
                key = str(int(raw))
            else:
                return None
        else:
            key = raw
        return key if isinstance(key, str) and key in self.index else None

    def table(self, cid):
        """Bit i is set when item i satisfies clause `cid`."""
        found = self._tables.get(cid)
        if found is None:
            fn = self.clause_by_id[cid].fn
            found = 0
            for i, v in enumerate(self.vals):
                if fn(v):
                    found |= 1 << i
            self._tables[cid] = found
        return found

    def holds(self, cid, key):
        return bool(self.clause_by_id[cid].fn(self.vals[self.index[key]]))


_DOMAINS = {}


def domain(kind):
    if kind not in _DOMAINS:
        _DOMAINS[kind] = Domain(kind)
    return _DOMAINS[kind]


# ---- rules --------------------------------------------------------------------------------------------------------
def make_rule(lits, ops=()):
    return Rule(tuple((c, 1 if n else 0) for c, n in lits), tuple(ops))


def parse_rule(kind, raw):
    """A Rule from a request or a save, or None. Accepts the encoded string ("even&~ge:50|has:7") or
    {"lits": [[clause id, negated], ...], "ops": ["and", ...]}. Every clause must exist for this kind."""
    dom = domain(kind)
    if isinstance(raw, str):
        lits, ops, token, neg = [], [], "", 0
        pieces = []
        for ch in raw:
            if ch in "&|":
                pieces.append(token)
                pieces.append(ch)
                token = ""
            else:
                token += ch
        pieces.append(token)
        for n, piece in enumerate(pieces):
            if n % 2:
                ops.append("and" if piece == "&" else "or")
            else:
                neg = 1 if piece.startswith("~") else 0
                lits.append((piece[neg:], neg))
    elif isinstance(raw, dict):
        raw_lits, raw_ops = raw.get("lits"), raw.get("ops", [])
        if not isinstance(raw_lits, list) or not isinstance(raw_ops, list):
            return None
        lits, ops = [], []
        for entry in raw_lits:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2 or not isinstance(entry[0], str) or isinstance(entry[1], str):
                return None
            lits.append((entry[0], 1 if entry[1] else 0))
        for op in raw_ops:
            if op not in ("and", "or"):
                return None
            ops.append(op)
    else:
        return None
    if not 1 <= len(lits) <= MAX_CLAUSES or len(ops) != len(lits) - 1:
        return None
    if any(cid not in dom.clause_by_id for cid, _n in lits):
        return None
    return Rule(tuple(lits), tuple(ops))


def encode_rule(rule):
    out = ""
    for n, (cid, neg) in enumerate(rule.lits):
        if n:
            out += "&" if rule.ops[n - 1] == "and" else "|"
        out += ("~" if neg else "") + cid
    return out


def rule_json(rule):
    return {"lits": [[c, n] for c, n in rule.lits], "ops": list(rule.ops)}


def rule_table(kind, rule):
    dom = domain(kind)
    value = None
    for n, (cid, neg) in enumerate(rule.lits):
        t = dom.table(cid)
        if neg:
            t = dom.full ^ t
        if value is None:
            value = t
        elif rule.ops[n - 1] == "and":
            value &= t
        else:
            value |= t
    return value


def rule_accepts(kind, rule, key):
    """Does the rule let this one item through? (Pure evaluation of the clauses; no table needed.)"""
    dom = domain(kind)
    v = dom.vals[dom.index[key]]
    value = None
    for n, (cid, neg) in enumerate(rule.lits):
        t = bool(dom.clause_by_id[cid].fn(v)) != bool(neg)
        if value is None:
            value = t
        elif rule.ops[n - 1] == "and":
            value = value and t
        else:
            value = value or t
    return value


def agree(kind, a, b):
    return rule_table(kind, a) == rule_table(kind, b)


def first_difference(kind, a, b, skip=()):
    """The first item (in domain order) on which two rules disagree, or None. Items in `skip` are passed over."""
    dom = domain(kind)
    diff = rule_table(kind, a) ^ rule_table(kind, b)
    for key in skip:
        diff &= ~(1 << dom.index[key])
    if not diff:
        return None
    return dom.items[(diff & -diff).bit_length() - 1]


def uses_not(rule):
    return any(neg for _c, neg in rule.lits)


def families(kind, rule):
    dom = domain(kind)
    out = []
    for cid, _n in rule.lits:
        fam = dom.clause_by_id[cid].family
        if fam not in out:
            out.append(fam)
    return out


# ---- words --------------------------------------------------------------------------------------------------------
def clause_words(kind, cid, neg=0):
    c = domain(kind).clause_by_id[cid]
    return c.no if neg else c.yes


def rule_words(kind, rule):
    """The rule as one plain sentence. Three clauses are grouped as (first two) then the third, the way they are read."""
    subject = SUBJECT[kind]
    parts = ["it " + clause_words(kind, c, n) for c, n in rule.lits]
    text = parts[0]
    for n in range(1, len(parts)):
        if n == 2 and rule.ops[0] != rule.ops[1]:
            text = "(" + text + ")"
        text = "%s %s %s" % (text, rule.ops[n - 1], parts[n])
    return "A %s goes Through if %s." % (subject, text)


def menu(kind):
    """The clause menu for the Rule Builder, grouped by family in library order."""
    dom = domain(kind)
    groups = []
    for c in dom.clauses:
        if not groups or groups[-1]["family"] != c.family:
            groups.append({"family": c.family, "label": FAMILIES[c.family][0], "clauses": []})
        groups[-1]["clauses"].append({"id": c.id, "yes": c.yes, "no": c.no})
    return groups


def item_words(kind, key):
    """A short spoken form of an item, for screen readers and the log."""
    if kind == NUM:
        return key
    if kind == SHAPE:
        return " ".join(SHAPE_NAMES[c] for c in key)
    filled = key.count("#")
    rows = ", ".join("row %d %s" % (n + 1, " ".join("filled" if key[n * 3 + c] == "#" else "empty" for c in range(3))) for n in range(3))
    return "%d filled: %s" % (filled, rows)
