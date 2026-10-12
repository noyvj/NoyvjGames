"""Reaction Bench -- the hint ladder, built on each order's stored (proved) answer. Three rungs per order, all free, none touching the
shelf or any record; each opens only when the player asks ("Would you like a suggestion?").

While the products are still to be chosen (a product round):
  1 Nudge   what comes out is made only from what goes in; the elements that go in are named
  2 Hint    one list that cannot be the one, with its reason in words (the first wrong list not already tried)
  3 Answer  the one list that can be balanced (the page asks first, except on Easy), chosen for you

Once the dials are open:
  1 Nudge   the element that is easiest to fix first (the one in the fewest formulas among the rows that read unequal) and how it reads
  2 Hint    the one dial to turn, and what it should read (the first dial that differs from the answer, preferring that element's)
  3 Answer  every dial set to the answer (the page asks first, except on Easy)

Difficulty: Normal is the ladder above. Easy opens the nudge and the hint together on the first press and the answer needs no question
first. Hard has no third rung. Everything is a pure function of the order, the dials and the lists already tried, so the same state
always gives the same words, and following the hints one dial at a time always finishes the order.
"""

import chem
import elements
import reactions

STAGE_CHOOSE, STAGE_DIALS = "choose", "dials"


def stage(known):
    return STAGE_DIALS if known else STAGE_CHOOSE


def _list_words(r, option):
    return " + ".join(r.choices[option])


def easiest_row(r, coefs):
    """The unequal ledger row whose element is in the fewest formulas of the order (ties: the first in the ledger's order)."""
    rows = [row for row in chem.ledger(r.reactants, r.products, coefs) if row["diff"] != 0]
    if not rows:
        return None
    formulas = r.reactants + r.products

    def key(item):
        i, row = item
        return (sum(1 for f in formulas if row["symbol"] in chem.count_atoms(f)), i)
    return min(enumerate(rows), key=key)[1]


def target_dial(r, coefs, symbol):
    """The dial to turn: the first that differs from the answer among the formulas holding `symbol`, else the first that differs at all."""
    formulas = r.reactants + r.products
    holding = [i for i, f in enumerate(formulas) if symbol in chem.count_atoms(f)]
    for i in holding + list(range(len(formulas))):
        if coefs[i] != r.answer[i]:
            return i
    return None


def _row_words(row):
    name = elements.name_of(row["symbol"]).capitalize()
    return "%s reads %d too %s on the right" % (name, abs(row["diff"]), "many" if row["diff"] > 0 else "few")


def choose_texts(r, tried):
    """(nudge, hint, answer, eliminated option or None) for a product round."""
    names = [elements.name_of(s) for s in chem.elements_of(r.reactants)]
    nudge = ("What comes out is made only from what goes in, and every element that goes in has to come out somewhere. "
             "Going in: %s." % chem._join(names))
    wrong = [i for i in range(len(r.choices)) if i != r.right and i not in tried]
    if wrong:
        i = wrong[0]
        hint = "List %d cannot be the one. %s" % (i + 1, chem.why_not(r.reactants, r.choices[i]))
    else:
        i = None
        hint = "Every other list has been tried, so list %d is the one that is left." % (r.right + 1)
    answer = "List %d is the one: %s. It has no element from nowhere, and nothing is left behind." % (r.right + 1, _list_words(r, r.right))
    return nudge, hint, answer, i


def dial_texts(r, coefs):
    """(nudge, hint, answer, dial index) for an order whose dials are open and whose ledger is not equal yet, or None when it is equal."""
    row = easiest_row(r, coefs)
    if row is None:
        return None
    formulas = r.reactants + r.products
    count = sum(1 for f in formulas if row["symbol"] in chem.count_atoms(f))
    nudge = "Start with %s. It is in only %d of the formulas, so it is the easiest to fix. %s." % (
        elements.name_of(row["symbol"]), count, _row_words(row))
    index = target_dial(r, coefs, row["symbol"])
    f = formulas[index]
    hint = "Turn the dial for %s (%s) to %d. It reads %d now." % (f, reactions.name_of(f), r.answer[index], coefs[index])
    n = len(r.reactants)
    words = " + ".join("%d %s" % (r.answer[i], g) for i, g in enumerate(r.reactants)) + " gives " + \
        " + ".join("%d %s" % (r.answer[n + i], g) for i, g in enumerate(r.products))
    answer = "Every dial is set: %s." % words
    return nudge, hint, answer, index


# ---- the rungs on offer -----------------------------------------------------------------------------------------------
def rung_cap(difficulty):
    return 2 if difficulty == "hard" else 3


def first_rung(difficulty):
    return 2 if difficulty == "easy" else 1


def button_label(rung_now, stage_name):
    """The words on the suggestion button for the press that opens the next rung."""
    if rung_now == 0:
        return "Would you like a suggestion?"
    if rung_now == 1:
        return "Another hint"
    return "Another hint: choose it for me" if stage_name == STAGE_CHOOSE else "Another hint: set the dials for me"
