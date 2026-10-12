"""Reaction Bench -- the periodic table: all 118 names and places, and the bench elements' snapshot facts and one-line uses.

`LAYOUT` puts every element in the usual 18-column picture (the lanthanides and actinides in two rows beneath it, and a marker
cell in the body where each row belongs). Only elements that an order on the bench actually uses carry a `BENCH` entry
(atomic mass and kind of element copied from the PubChem Periodic Table service on 2026-10-12, the one-line use written for
this game); the other cells are drawn faint and labelled "not on this bench". Nothing here reads a clock.
"""

SNAPSHOT_DATE = "2026-10-12"
SNAPSHOT_SOURCE = "PubChem Periodic Table (pubchem.ncbi.nlm.nih.gov)"

_NAMES = (
    "H Hydrogen,He Helium,Li Lithium,Be Beryllium,B Boron,C Carbon,N Nitrogen,O Oxygen,F Fluorine,Ne Neon,"
    "Na Sodium,Mg Magnesium,Al Aluminium,Si Silicon,P Phosphorus,S Sulfur,Cl Chlorine,Ar Argon,K Potassium,Ca Calcium,"
    "Sc Scandium,Ti Titanium,V Vanadium,Cr Chromium,Mn Manganese,Fe Iron,Co Cobalt,Ni Nickel,Cu Copper,Zn Zinc,"
    "Ga Gallium,Ge Germanium,As Arsenic,Se Selenium,Br Bromine,Kr Krypton,Rb Rubidium,Sr Strontium,Y Yttrium,Zr Zirconium,"
    "Nb Niobium,Mo Molybdenum,Tc Technetium,Ru Ruthenium,Rh Rhodium,Pd Palladium,Ag Silver,Cd Cadmium,In Indium,Sn Tin,"
    "Sb Antimony,Te Tellurium,I Iodine,Xe Xenon,Cs Caesium,Ba Barium,La Lanthanum,Ce Cerium,Pr Praseodymium,Nd Neodymium,"
    "Pm Promethium,Sm Samarium,Eu Europium,Gd Gadolinium,Tb Terbium,Dy Dysprosium,Ho Holmium,Er Erbium,Tm Thulium,Yb Ytterbium,"
    "Lu Lutetium,Hf Hafnium,Ta Tantalum,W Tungsten,Re Rhenium,Os Osmium,Ir Iridium,Pt Platinum,Au Gold,Hg Mercury,"
    "Tl Thallium,Pb Lead,Bi Bismuth,Po Polonium,At Astatine,Rn Radon,Fr Francium,Ra Radium,Ac Actinium,Th Thorium,"
    "Pa Protactinium,U Uranium,Np Neptunium,Pu Plutonium,Am Americium,Cm Curium,Bk Berkelium,Cf Californium,Es Einsteinium,Fm Fermium,"
    "Md Mendelevium,No Nobelium,Lr Lawrencium,Rf Rutherfordium,Db Dubnium,Sg Seaborgium,Bh Bohrium,Hs Hassium,Mt Meitnerium,Ds Darmstadtium,"
    "Rg Roentgenium,Cn Copernicium,Nh Nihonium,Fl Flerovium,Mc Moscovium,Lv Livermorium,Ts Tennessine,Og Oganesson"
)
ELEMENTS = []                                     # [(atomic number, symbol, name)]
for _i, _pair in enumerate(_NAMES.split(",")):
    _sym, _name = _pair.split(" ", 1)
    ELEMENTS.append((_i + 1, _sym, _name))
BY_SYMBOL = {sym: (z, sym, name) for z, sym, name in ELEMENTS}
BY_NUMBER = {z: (z, sym, name) for z, sym, name in ELEMENTS}


def name_of(symbol):
    return BY_SYMBOL[symbol][2].lower()


def number_of(symbol):
    return BY_SYMBOL[symbol][0]


def position(z):
    """(row, column, kind) of element z. Rows 1-7 are the body; rows 9 and 10 hold the lanthanides and actinides."""
    if z == 1:
        return 1, 1, "body"
    if z == 2:
        return 1, 18, "body"
    if z <= 4:
        return 2, z - 2, "body"
    if z <= 10:
        return 2, z + 8, "body"
    if z <= 12:
        return 3, z - 10, "body"
    if z <= 18:
        return 3, z, "body"
    if z <= 36:
        return 4, z - 18, "body"
    if z <= 54:
        return 5, z - 36, "body"
    if z <= 56:
        return 6, z - 54, "body"
    if z <= 71:
        return 9, z - 54, "f"                     # La (57) .. Lu (71) in columns 3-17
    if z <= 86:
        return 6, z - 68, "body"                  # Hf (72) in column 4
    if z <= 88:
        return 7, z - 86, "body"
    if z <= 103:
        return 10, z - 86, "f"                    # Ac (89) .. Lr (103) in columns 3-17
    return 7, z - 100, "body"                     # Rf (104) in column 4


MARKERS = (                                       # the body cells that say where each row of the f-block belongs
    {"row": 6, "col": 3, "text": "57-71", "label": "Lanthanides, shown in the row beneath"},
    {"row": 7, "col": 3, "text": "89-103", "label": "Actinides, shown in the row beneath"},
)


def period_of(z):
    row, _col, kind = position(z)
    if kind == "f":
        return 6 if row == 9 else 7
    return row


def group_of(z):
    """The group number 1-18 for a body element, or 0 for the lanthanides and actinides."""
    row, col, kind = position(z)
    return 0 if kind == "f" else col


# Snapshot facts for the elements the shipped orders use. mass: decimal string as PubChem gives it. kind: its "GroupBlock".
# state: the usual state at room temperature. use: one line written for this game (an everyday or industrial use, kept plain).
BENCH = {
    "H": {"mass": "1.0080", "kind": "Nonmetal", "state": "gas",
          "use": "The lightest element. It burns with oxygen to make water, and it is used to make ammonia."},
    "C": {"mass": "12.011", "kind": "Nonmetal", "state": "solid",
          "use": "The backbone of fuels, sugars and charcoal. Burning carbon makes carbon dioxide."},
    "N": {"mass": "14.007", "kind": "Nonmetal", "state": "gas",
          "use": "About four-fifths of the air is nitrogen. Plants need it, so it goes into fertiliser."},
    "O": {"mass": "15.999", "kind": "Nonmetal", "state": "gas",
          "use": "About a fifth of the air. Fire, rust and breathing all use it up."},
    "Na": {"mass": "22.9897693", "kind": "Alkali metal", "state": "solid",
           "use": "A soft metal that joins chlorine to make the salt on the table."},
    "Mg": {"mass": "24.305", "kind": "Alkaline earth metal", "state": "solid",
           "use": "A light metal used in alloys. It burns with a brilliant white light."},
    "Al": {"mass": "26.981538", "kind": "Post-transition metal", "state": "solid",
           "use": "A light metal for cans, foil and aircraft. A thin oxide skin forms on it at once and protects it."},
    "S": {"mass": "32.07", "kind": "Nonmetal", "state": "solid",
          "use": "A yellow solid. Most of it ends up as sulfuric acid."},
    "Cl": {"mass": "35.45", "kind": "Halogen", "state": "gas",
           "use": "A green-yellow gas on its own. Its compounds include table salt, and it is used to treat drinking water."},
    "Ca": {"mass": "40.08", "kind": "Alkaline earth metal", "state": "solid",
           "use": "Found in limestone, chalk, shells and bones. Heated limestone gives quicklime."},
    "Fe": {"mass": "55.84", "kind": "Transition metal", "state": "solid",
           "use": "The main metal of steel. It rusts where wet air reaches it."},
    "P": {"mass": "30.97376200", "kind": "Nonmetal", "state": "solid",
          "use": "Found in bones, teeth and every living cell. Phosphates are a main fertiliser ingredient."},
    "K": {"mass": "39.0983", "kind": "Alkali metal", "state": "solid",
          "use": "A soft, silvery metal. Plants need potassium, so its salts go into fertiliser."},
    "Cu": {"mass": "63.55", "kind": "Transition metal", "state": "solid",
           "use": "A reddish metal used in wiring and pipes. Outdoors it slowly gets a green coating."},
    "Ag": {"mass": "107.868", "kind": "Transition metal", "state": "solid",
           "use": "A bright metal that carries electricity very well. It is used in jewellery, coins and electronics."},
}

MASSES = {sym: info["mass"] for sym, info in BENCH.items()}
