"""Dev aid: python3 tools/check.py [shift id ...] -- for each authored shift print whether it is fair (a no-cost plan exists
whatever the scans say), how long the search took and which shelves are tight (taking one unit away breaks it)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cases  # noqa: E402
from shift import Case  # noqa: E402
from solver import Solver  # noqa: E402


def main(ids):
    for d in cases.ALL:
        if ids and d["id"] not in ids:
            continue
        c = Case(d)
        t0 = time.time()
        s = Solver(c)
        ok = s.solvable()
        tight = []
        total = sum(d["stock"].values())
        for item, n in d["stock"].items():
            if n:
                d2 = dict(d)
                d2["stock"] = dict(d["stock"])
                d2["stock"][item] = n - 1
                if not Solver(Case(d2)).solvable():
                    tight.append(item)
        print("%-5s %-22s errors=%s fair=%s %.2fs units=%d tight=%s" % (d["id"], d["title"][:22], c.errors, ok, time.time() - t0, total, ",".join(tight)))


main(sys.argv[1:])
