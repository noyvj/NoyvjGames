"""Chapter 1, Bench Basics: two things go in, one comes out. The whole equation is shown; only the dials are yours.

Each reaction is frozen data: id, title, reactants, products, answer (the lowest whole-number settings), a plain fact (shown once
the order is shelved) and one dry line from Fennel. tools/balance.py and tests/test_reactions.py prove the answers.
"""

CHAPTER = {
    "id": "basics", "name": "Bench Basics",
    "blurb": "Two things go in, one comes out. Turn the dials until the ledger reads equal on both sides.",
}

REACTIONS = (
    dict(id="carbon-dioxide", title="Carbon dioxide", reactants=["C", "O2"], products=["CO2"], answer=[1, 1, 1],
         blurb="Carbon dioxide is the gas you breathe out and the gas plants take in. Burning carbon makes it.",
         fennel="One of each. I checked twice, and then I checked the checking."),
    dict(id="table-salt", title="Table salt", reactants=["Na", "Cl2"], products=["NaCl"], answer=[2, 1, 2],
         blurb="Sodium and chlorine are both hard to handle on their own. Joined as sodium chloride they are the salt on the table.",
         fennel="Chlorine comes in pairs. It is that kind of element."),
    dict(id="water", title="Water", reactants=["H2", "O2"], products=["H2O"], answer=[2, 1, 2],
         blurb="A water molecule is two hydrogen atoms and one oxygen atom. Hydrogen burning in air makes nothing but water.",
         fennel="Oxygen arrives in twos and leaves in ones. Do not ask me where the other half goes."),
    dict(id="magnesium-oxide", title="Magnesium oxide", reactants=["Mg", "O2"], products=["MgO"], answer=[2, 1, 2],
         blurb="Magnesium burns in air with a brilliant white light and leaves a white powder, magnesium oxide.",
         fennel="Bright, quick and tidy. Everything I want in a colleague."),
    dict(id="rust", title="Rust", reactants=["Fe", "O2"], products=["Fe2O3"], answer=[4, 3, 2],
         blurb="Rust is mostly iron(III) oxide with some water bound into it. This order makes the plain oxide.",
         fennel="Rust never sleeps. It does not even lie down."),
    dict(id="aluminium-oxide", title="Aluminium oxide", reactants=["Al", "O2"], products=["Al2O3"], answer=[4, 3, 2],
         blurb="Aluminium grows a thin skin of aluminium oxide the moment it meets air, and the skin protects the metal beneath.",
         fennel="A skin that heals itself. I am a little envious."),
    dict(id="magnesium-nitride", title="Magnesium nitride", reactants=["Mg", "N2"], products=["Mg3N2"], answer=[3, 1, 1],
         blurb="Magnesium burning in air makes mostly magnesium oxide, but a little magnesium nitride forms too, because air is mostly nitrogen.",
         fennel="Three to one. The numbers are asymmetric. I respect that."),
    dict(id="aluminium-chloride", title="Aluminium chloride", reactants=["Al", "Cl2"], products=["AlCl3"], answer=[2, 3, 2],
         blurb="Aluminium chloride is a white solid that the chemical industry uses to speed other reactions along.",
         fennel="Chapter one, last order. Try to look surprised."),
)
