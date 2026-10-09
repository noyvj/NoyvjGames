"""Dev aid: python3 tools/shrink.py <shift id> [item ...] -- starting from a generous shelf (every item the shift lists, plus any
extra named, three of each), remove units in several orders and print the minimal fair stocks found."""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cases  # noqa: E402
from shift import Case  # noqa: E402
from solver import Solver  # noqa: E402


def fair(d, stock):
    d2 = dict(d)
    d2["stock"] = stock
    return Solver(Case(d2)).solvable()


def main():
    d = next(x for x in cases.ALL if x["id"] == sys.argv[1])
    items = list(dict.fromkeys(list(d["stock"]) + sys.argv[2:]))
    found = set()
    for order in itertools.islice(itertools.permutations(items), 0, 200):
        stock = {i: 3 for i in items}
        if not fair(d, stock):
            print("not fair even with 3 of everything")
            return
        for item in order:
            while stock[item] and fair(d, dict(stock, **{item: stock[item] - 1})):
                stock[item] -= 1
        found.add(tuple(sorted((k, v) for k, v in stock.items() if v)))
    for f in sorted(found, key=lambda f: sum(v for _k, v in f)):
        print(sum(v for _k, v in f), dict(f))


main()
