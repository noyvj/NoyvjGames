"""Reaction Bench -- the chapters and their reactions, the compound names, and the gating rule.

Chapter 0 is open from the start; chapter n+1 opens when OPEN_AT (5) orders of chapter n are on the shelf (any five). Inside a
chapter every order is open in any order. Everything here is frozen data and pure functions of the shelf, so the gate only goes up.
Adding a chapter: write reactions_cN.py with CHAPTER and REACTIONS, add it to _MODULES here and to ENGINE_MODULES in app.js (a
test checks the list), run `python3 tools/balance.py`, then the tests.
"""

import chem
import elements
import reactions_c1
import reactions_c2
import reactions_c3
import reactions_c4
import reactions_c5

OPEN_AT = 5

# What every formula on the bench is called. (Wrong-product lists use these too.)
NAMES = {
    "C": "carbon", "O2": "oxygen", "CO2": "carbon dioxide", "Na": "sodium", "Cl2": "chlorine", "NaCl": "sodium chloride (table salt)",
    "H2": "hydrogen", "H2O": "water", "Mg": "magnesium", "MgO": "magnesium oxide", "Fe": "iron", "Fe2O3": "iron(III) oxide",
    "Al": "aluminium", "Al2O3": "aluminium oxide", "N2": "nitrogen", "Mg3N2": "magnesium nitride", "AlCl3": "aluminium chloride",
    "CH4": "methane", "C3H8": "propane", "C2H5OH": "ethanol", "C5H12": "pentane", "C2H2": "ethyne (acetylene)", "S": "sulfur",
    "SO2": "sulfur dioxide", "C6H12O6": "glucose", "NH3": "ammonia", "CaCO3": "calcium carbonate (limestone)",
    "CaO": "calcium oxide (quicklime)", "Ca(OH)2": "calcium hydroxide (slaked lime)", "NaHCO3": "sodium hydrogencarbonate (baking soda)",
    "Na2CO3": "sodium carbonate", "H2O2": "hydrogen peroxide", "Al(OH)3": "aluminium hydroxide", "Fe(OH)2": "iron(II) hydroxide",
    "Fe(OH)3": "iron(III) hydroxide", "H2SO4": "sulfuric acid", "(NH4)2SO4": "ammonium sulfate (fertiliser)", "NH4Cl": "ammonium chloride",
    "FeCl3": "iron(III) chloride", "Ca": "calcium", "Na2O": "sodium oxide",
    "HCl": "hydrochloric acid", "NaOH": "sodium hydroxide (caustic soda)", "Mg(OH)2": "magnesium hydroxide (milk of magnesia)",
    "MgCl2": "magnesium chloride", "KOH": "potassium hydroxide", "K2SO4": "potassium sulfate", "KCl": "potassium chloride",
    "CaCl2": "calcium chloride", "Cu": "copper", "AgNO3": "silver nitrate", "Cu(NO3)2": "copper(II) nitrate", "Ag": "silver",
    "CuO": "copper(II) oxide", "H3PO4": "phosphoric acid", "Ca3(PO4)2": "calcium phosphate", "SO3": "sulfur trioxide",
    "(NH4)3PO4": "ammonium phosphate (fertiliser)", "Fe3O4": "iron(II,III) oxide (magnetite)",
}

_MODULES = (reactions_c1, reactions_c2, reactions_c3, reactions_c4, reactions_c5)


class Reaction:
    def __init__(self, number, chapter, data):
        self.number = number                         # 1-based over the whole bench
        self.chapter = chapter                       # index of its chapter
        self.id = data["id"]
        self.title = data["title"]
        self.reactants = list(data["reactants"])
        self.products = list(data["products"])
        self.answer = list(data["answer"])
        self.choices = [list(c) for c in data["choices"]] if data.get("choices") else None
        self.right = data.get("right")
        self.blurb = data["blurb"]
        self.fennel = data["fennel"]
        self.route = data.get("route")                # a two-step route: its id, which step (1 or 2) and, on step 1, what it carries on
        self.step = data.get("step", 0)
        self.carries = data.get("carries")
        self.after = None                             # on step 2: the id of the step-1 order that must be on the shelf first
        self.size = len(self.reactants) + len(self.products)
        self.elements = chem.elements_of(self.reactants + self.products)
        self.has_group = any(chem.has_group(f) for f in self.reactants + self.products)

    @property
    def is_round(self):
        """A product-choice round: the player picks what comes out before the dials open."""
        return self.choices is not None

    def formulas(self):
        return self.reactants + self.products


CHAPTERS = []
ALL = []
for _ci, _mod in enumerate(_MODULES):
    _items = []
    for _data in _mod.REACTIONS:
        _r = Reaction(len(ALL) + 1, _ci, _data)
        _items.append(_r)
        ALL.append(_r)
    CHAPTERS.append({"id": _mod.CHAPTER["id"], "name": _mod.CHAPTER["name"], "blurb": _mod.CHAPTER["blurb"], "reactions": _items})
BY_ID = {r.id: r for r in ALL}
ROUTES = {}                                           # route id -> {"name", "first", "second"} (the two orders)
for _mod in _MODULES:
    ROUTES.update({rid: {"name": name} for rid, name in getattr(_mod, "ROUTES", {}).items()})
for _r in ALL:
    if _r.route:
        ROUTES[_r.route]["first" if _r.step == 1 else "second"] = _r
        if _r.step == 2:
            _r.after = ROUTES[_r.route]["first"].id
ORDER = [r.id for r in ALL]

BENCH_ELEMENTS = []                                  # the elements some order uses, in atomic-number order
for _sym in sorted({s for r in ALL for s in r.elements}, key=elements.number_of):
    BENCH_ELEMENTS.append(_sym)


def name_of(formula):
    return NAMES[formula]


def chapter_shelved(shelf, ci):
    return sum(1 for r in CHAPTERS[ci]["reactions"] if r.id in shelf)


def chapter_need(ci):
    """How many shelved orders in chapter ci open the next chapter."""
    return min(OPEN_AT, len(CHAPTERS[ci]["reactions"]))


def chapter_open(shelf, ci):
    return ci == 0 or chapter_shelved(shelf, ci - 1) >= chapter_need(ci - 1)


def reaction_open(shelf, rid):
    """Its chapter is open and, for step two of a route, step one is on the shelf."""
    r = BY_ID[rid]
    return chapter_open(shelf, r.chapter) and (r.after is None or r.after in shelf)


def route_locked(shelf, rid):
    """True for a step-two order in an open chapter whose step-one order is not on the shelf yet."""
    r = BY_ID[rid]
    return chapter_open(shelf, r.chapter) and r.after is not None and r.after not in shelf


def chapters_done(shelf):
    return sum(1 for ci in range(len(CHAPTERS)) if chapter_shelved(shelf, ci) == len(CHAPTERS[ci]["reactions"]))
