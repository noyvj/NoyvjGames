"""Dev tool: prove every authored reaction. Run by hand after adding or changing one:

    python3 tools/balance.py            # every reaction
    python3 tools/balance.py burning    # one chapter (by id)

For each reaction it prints the nullspace dimension (must be 1), the lowest whole-number setting the exact balancer finds
(must equal the stored answer), a brute-force count of balancing settings (an independent check), the exact mass on each side
(must match), and for a product-choice round how many of its candidate lists can be balanced (must be exactly 1).
"""

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chem  # noqa: E402
import elements  # noqa: E402
import reactions  # noqa: E402


def brute_force(reactants, products, limit=chem.MAX_COEF):
    """Every setting from 1..limit that balances, by trying them all (independent of the nullspace code)."""
    cols = [chem.count_atoms(f) for f in reactants + products]
    syms = chem.elements_of(reactants + products)
    sign = [1] * len(reactants) + [-1] * len(products)
    found = []
    for combo in itertools.product(range(1, limit + 1), repeat=len(cols)):
        if all(sum(sign[j] * combo[j] * cols[j].get(s, 0) for j in range(len(cols))) == 0 for s in syms):
            found.append(list(combo))
    return found


def check(r):
    basis = chem.nullspace(r.reactants, r.products)
    small = chem.smallest(r.reactants, r.products)
    brute = [s for s in brute_force(r.reactants, r.products) if chem.lowest_terms(s)] if r.size <= 5 else None
    left = chem.side_mass(r.reactants, r.answer[:len(r.reactants)], elements.MASSES)
    right = chem.side_mass(r.products, r.answer[len(r.reactants):], elements.MASSES)
    ok_choices = None
    if r.is_round:
        ok_choices = [i for i, c in enumerate(r.choices) if chem.can_balance(r.reactants, c)]
    good = (len(basis) == 1 and small == r.answer and (brute is None or brute == [r.answer]) and left == right
            and (ok_choices is None or ok_choices == [r.right]))
    return good, basis, small, brute, left, right, ok_choices


def main(argv):
    wanted = [a for a in argv if not a.startswith("--")]
    bad = 0
    for chapter in reactions.CHAPTERS:
        if wanted and chapter["id"] not in wanted:
            continue
        print("== %s ==" % chapter["name"])
        for r in chapter["reactions"]:
            good, basis, small, brute, left, right, ok_choices = check(r)
            bad += 0 if good else 1
            print("%-22s dim %d  smallest %-14s brute %-16s mass %s = %s  %s%s" % (
                r.id, len(basis), small, "skipped" if brute is None else brute, float(left), float(right),
                "choices ok %s" % ok_choices if ok_choices is not None else "", "  OK" if good else "  FAIL"))
    print("%d problem(s)" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
