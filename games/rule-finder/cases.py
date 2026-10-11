"""Rule Finder -- the cases, assembled from the frozen drawer files (cases_*.py, written by tools/build_cases.py).

A case is a hidden rule over one domain, a few starting examples and a PAR TEST SET: a smallest list of items whose answers, with
the examples, tell the hidden rule from every other rule of its size or shorter (proved by tools/finder.py and re-checked in the
tests). The medal target ("par") is that shortest path plus PAR_ALLOWANCE, because a person is not an oracle.
"""

import cases_not
import cases_numbers
import cases_shapes
import cases_two
import lang

PAR_ALLOWANCE = 2
SILVER_ALLOWANCE = 4          # silver: within this many tests of par
MODULES = (cases_numbers, cases_shapes, cases_two, cases_not)


class Case:
    def __init__(self, raw, drawer, number):
        self.id = raw["id"]
        self.name = raw["name"]
        self.drawer = drawer
        self.number = number
        self.kind = raw["domain"]
        self.rule_text = raw["rule"]
        self.rule = lang.parse_rule(self.kind, raw["rule"])
        self.size = raw["size"]
        self.yes = tuple(raw["yes"])
        self.no = tuple(raw["no"])
        self.examples = self.yes + self.no
        self.shortest = tuple(raw["par"])
        self.par = len(self.shortest) + PAR_ALLOWANCE
        self.line = raw["line"]
        self._table = None

    @property
    def table(self):
        if self._table is None:
            self._table = lang.rule_table(self.kind, self.rule)
        return self._table

    @property
    def domain(self):
        return lang.domain(self.kind)

    def accepts(self, key):
        """The Sorter's answer for one item: True is Through, False is Stopped."""
        return lang.rule_accepts(self.kind, self.rule, key)

    @property
    def words(self):
        return lang.rule_words(self.kind, self.rule)

    @property
    def families(self):
        return lang.families(self.kind, self.rule)


def medal_for(case, tests):
    """'gold' within par, 'silver' within SILVER_ALLOWANCE more, else 'bronze'; named at all is at least bronze."""
    if tests <= case.par:
        return "gold"
    if tests <= case.par + SILVER_ALLOWANCE:
        return "silver"
    return "bronze"


DRAWER_LIST = []
ALL_CASES = []
for _index, _mod in enumerate(MODULES):
    _cases = [Case(raw, _index, n + 1) for n, raw in enumerate(_mod.CASES)]
    DRAWER_LIST.append({"id": _mod.KEY, "name": _mod.NAME, "blurb": _mod.BLURB, "max_clauses": _mod.MAX_CLAUSES, "cases": _cases})
    ALL_CASES.extend(_cases)

ORDER = [c.id for c in ALL_CASES]
BY_ID = {c.id: c for c in ALL_CASES}
