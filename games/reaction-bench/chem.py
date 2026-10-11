"""Reaction Bench -- the chemistry kernel: formula parser, atom ledger, exact nullspace balancer, banned-list lint.

Pure functions of formulas and whole-number coefficients: no clock, no randomness, no DOM. Python 3.9 compatible.

A formula is plain ASCII: element symbols with optional counts and round brackets, "Ca(OH)2", "(NH4)2SO4", "C2H5OH".
`parse_tree` gives the structure the page draws (elements and bracketed groups); `count_atoms` the totals per element.

Balancing is proved, not guessed: `nullspace` is exact Gaussian elimination over fractions, `solutions` lists every
positive whole-number setting inside the dial range, and `smallest` is the one in lowest terms. tools/balance.py prints
the proof table; tests/test_chem.py and tests/test_reactions.py hold the assertions.
"""

import re
from fractions import Fraction
from math import gcd

import elements

MIN_COEF = 1
MAX_COEF = 12                              # the dials turn from 1 to 12

_TOKEN = re.compile(r"[A-Z][a-z]?|\(|\)|\d+")


class FormulaError(ValueError):
    pass


def _tokens(formula):
    if not isinstance(formula, str) or not formula:
        raise FormulaError("empty formula")
    out, pos = [], 0
    while pos < len(formula):
        m = _TOKEN.match(formula, pos)
        if not m:
            raise FormulaError("cannot read %r at %d" % (formula, pos))
        out.append(m.group(0))
        pos = m.end()
    return out


def parse_tree(formula):
    """[{"t": "el", "sym": "Ca", "n": 1}, {"t": "group", "parts": [...], "n": 2}, ...]  (n is the subscript, 1 when none)."""
    tokens = _tokens(formula)
    pos = [0]

    def number():
        if pos[0] < len(tokens) and tokens[pos[0]].isdigit():
            n = int(tokens[pos[0]])
            pos[0] += 1
            if n < 1:
                raise FormulaError("a count of zero in %r" % formula)
            return n
        return 1

    def sequence(closing):
        parts = []
        while pos[0] < len(tokens):
            tok = tokens[pos[0]]
            if tok == ")":
                if not closing:
                    raise FormulaError("unmatched ) in %r" % formula)
                return parts
            pos[0] += 1
            if tok == "(":
                inner = sequence(True)
                if pos[0] >= len(tokens) or tokens[pos[0]] != ")":
                    raise FormulaError("unmatched ( in %r" % formula)
                pos[0] += 1
                if not inner:
                    raise FormulaError("empty brackets in %r" % formula)
                parts.append({"t": "group", "parts": inner, "n": number()})
            elif tok.isdigit():
                raise FormulaError("a number with nothing before it in %r" % formula)
            else:
                if tok not in elements.BY_SYMBOL:
                    raise FormulaError("%s is not an element symbol (in %r)" % (tok, formula))
                parts.append({"t": "el", "sym": tok, "n": number()})
        if closing:
            raise FormulaError("unmatched ( in %r" % formula)
        return parts

    tree = sequence(False)
    if not tree:
        raise FormulaError("empty formula")
    return tree


def _add(tree, factor, into):
    for part in tree:
        if part["t"] == "el":
            into[part["sym"]] = into.get(part["sym"], 0) + part["n"] * factor
        else:
            _add(part["parts"], factor * part["n"], into)


def count_atoms(formula):
    """{symbol: atoms in one unit of the formula}"""
    out = {}
    _add(parse_tree(formula), 1, out)
    return out


def has_group(formula):
    return any(part["t"] == "group" for part in parse_tree(formula))


def elements_of(formulas):
    """Symbols in order of first appearance across the formulas."""
    seen = []
    for f in formulas:
        for sym in count_atoms(f):
            if sym not in seen:
                seen.append(sym)
    return seen


# ---- the ledger (what the player sees) -------------------------------------------------------------------------------
def ledger(reactants, products, coefs):
    """One row per element: atoms on the left, atoms on the right and the difference (right minus left).
    `coefs` lists the reactants' coefficients first, then the products'."""
    n = len(reactants)
    rows = []
    for sym in elements_of(list(reactants) + list(products)):
        left = sum(coefs[i] * count_atoms(f).get(sym, 0) for i, f in enumerate(reactants))
        right = sum(coefs[n + i] * count_atoms(f).get(sym, 0) for i, f in enumerate(products))
        rows.append({"symbol": sym, "left": left, "right": right, "diff": right - left})
    return rows


def is_balanced(rows):
    return bool(rows) and all(r["diff"] == 0 for r in rows)


def lowest_terms(coefs):
    g = 0
    for c in coefs:
        g = gcd(g, c)
    return g == 1


# ---- exact balancing ------------------------------------------------------------------------------------------------
def _matrix(reactants, products):
    syms = elements_of(list(reactants) + list(products))
    cols = [count_atoms(f) for f in reactants] + [count_atoms(f) for f in products]
    sign = [1] * len(reactants) + [-1] * len(products)
    return syms, [[Fraction(sign[j] * cols[j].get(s, 0)) for j in range(len(cols))] for s in syms]


def _rref(m):
    m = [row[:] for row in m]
    pivots, r = [], 0
    width = len(m[0]) if m else 0
    for c in range(width):
        p = next((i for i in range(r, len(m)) if m[i][c] != 0), None)
        if p is None:
            continue
        m[r], m[p] = m[p], m[r]
        lead = m[r][c]
        m[r] = [x / lead for x in m[r]]
        for i in range(len(m)):
            if i != r and m[i][c] != 0:
                f = m[i][c]
                m[i] = [a - f * b for a, b in zip(m[i], m[r])]
        pivots.append(c)
        r += 1
        if r == len(m):
            break
    return m, pivots


def nullspace(reactants, products):
    """A basis (list of Fraction vectors) of the settings that make every element equal."""
    _syms, m = _matrix(reactants, products)
    width = len(reactants) + len(products)
    rref, pivots = _rref(m)
    free = [c for c in range(width) if c not in pivots]
    basis = []
    for f in free:
        v = [Fraction(0)] * width
        v[f] = Fraction(1)
        for row, p in enumerate(pivots):
            v[p] = -rref[row][f]
        basis.append(v)
    return basis


def solutions(reactants, products, limit=MAX_COEF):
    """Every setting with each coefficient a whole number from 1 to `limit` that balances (found from the nullspace)."""
    _syms, m = _matrix(reactants, products)
    width = len(reactants) + len(products)
    rref, pivots = _rref(m)
    free = [c for c in range(width) if c not in pivots]
    out = []

    def walk(i, assigned):
        if i == len(free):
            vec = [None] * width
            for f, val in zip(free, assigned):
                vec[f] = Fraction(val)
            for row, p in enumerate(pivots):
                vec[p] = -sum(rref[row][f] * vec[f] for f in free)
            if all(v.denominator == 1 and 1 <= v <= limit for v in vec):
                out.append([int(v) for v in vec])
            return
        for val in range(1, limit + 1):
            walk(i + 1, assigned + [val])

    walk(0, [])
    return out


def smallest(reactants, products, limit=MAX_COEF):
    """The one balancing setting in lowest terms, or None when there is none (or, wrongly, more than one)."""
    found = [s for s in solutions(reactants, products, limit) if lowest_terms(s)]
    return found[0] if len(found) == 1 else None


def can_balance(reactants, products, limit=MAX_COEF):
    return bool(solutions(reactants, products, limit))


def why_not(reactants, products):
    """Words for a set of products that cannot be balanced against these reactants, from the formulas alone."""
    left = elements_of(reactants)
    right = elements_of(products)
    extra = [s for s in right if s not in left]
    missing = [s for s in left if s not in right]
    if extra:
        return "%s would have to appear from nowhere: there is none on the left." % _join([elements.name_of(s) for s in extra]).capitalize()
    if missing:
        return "%s goes in on the left but has nowhere to go on the right." % _join([elements.name_of(s) for s in missing]).capitalize()
    return "Every element is on both sides, but no whole-number settings make them all come out equal."


def _join(items):
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


# ---- mass (the second, independent check) ----------------------------------------------------------------------------
def formula_mass(formula, masses):
    """Exact mass of one unit of the formula; `masses` maps symbol -> decimal string."""
    return sum(Fraction(masses[s]) * n for s, n in count_atoms(formula).items())


def side_mass(formulas, coefs, masses):
    return sum(c * formula_mass(f, masses) for f, c in zip(formulas, coefs))


# ---- the banned-list lint ------------------------------------------------------------------------------------------
BANNED_WORDS = re.compile(
    r"\b(explosive|explode|detonat\w*|dynamite|gunpowder|tnt|nitroglycerin\w*|bomb\w*|fireworks?|thermite|napalm|"
    r"poison\w*|toxic|nerve agent|sarin|mustard gas|phosgene|cyanide|ricin|chemical weapon\w*|"
    r"drug\w*|meth\w*amphetamine|cocaine|heroin|fentanyl|opiate\w*|narcotic\w*|lsd|mdma|"
    r"how to make|recipe for|at home)\b", re.IGNORECASE)
# formulas that are never on the bench (checked on the parsed atom counts, so spacing and ordering cannot hide them)
_BANNED_FORMULAS = ("KClO3", "NH4NO3", "HCN", "KCN", "NaCN", "COCl2", "C3H5N3O9", "C7H5N3O6", "NaN3", "Pb(N3)2", "H2S", "CO", "NO2",
                    "Cl2O", "KClO4", "NaClO3", "C7H5N3O6", "HgC2N2O2", "AsH3", "PH3", "HF", "SF6")


def _key(formula):
    return tuple(sorted(count_atoms(formula).items()))


BANNED_KEYS = frozenset(_key(f) for f in _BANNED_FORMULAS)


def lint(texts, formulas):
    """Problems found in the words and formulas of one reaction: banned words, banned formulas, unreadable formulas."""
    problems = []
    for text in texts:
        hit = BANNED_WORDS.search(text or "")
        if hit:
            problems.append("banned word %r in %r" % (hit.group(0), (text or "")[:50]))
    for f in formulas:
        try:
            if _key(f) in BANNED_KEYS:
                problems.append("banned formula %s" % f)
        except FormulaError as err:
            problems.append(str(err))
    return problems
