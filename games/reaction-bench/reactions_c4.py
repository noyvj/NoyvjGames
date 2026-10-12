"""Chapter 4, Acids, Bases and Swaps: acids meet bases, metals meet acids, and two salts swap partners. Products are chosen from four
lists again (only one can be balanced), and the formulas get longer: three bracket groups and a five-species order.

Every order is a textbook reaction, equations only. tools/balance.py and tests/test_reactions.py prove the answers.
"""

CHAPTER = {
    "id": "acids-bases", "name": "Acids, Bases and Swaps",
    "blurb": "Acids and bases cancel out, metals push each other aside, and two salts can swap partners. Choose what comes out, then balance it.",
}

REACTIONS = (
    dict(id="neutralisation", title="Neutralisation", reactants=["HCl", "NaOH"], products=["NaCl", "H2O"], answer=[1, 1, 1, 1],
         choices=[["NaCl"], ["NaCl", "H2O2"], ["NaCl", "H2O"], ["NaCl", "CO2"]], right=2,
         blurb="An acid and a base cancel each other out and leave a salt and water. Here hydrochloric acid and sodium hydroxide make table salt.",
         fennel="Acid meets base and they both calm down. I aspire to this."),
    dict(id="milk-of-magnesia", title="Milk of magnesia", reactants=["Mg(OH)2", "HCl"], products=["MgCl2", "H2O"], answer=[1, 2, 1, 2],
         choices=[["MgCl2", "H2O"], ["MgCl2", "H2"], ["MgCl2", "H2O", "NaCl"], ["MgCl2", "H2O2"]], right=0,
         blurb="Magnesium hydroxide is the white liquid sold as milk of magnesia. It is a mild base, so it cancels extra stomach acid, which is hydrochloric acid.",
         fennel="A bracket, a two, and an acid. You have met all three."),
    dict(id="potassium-sulfate", title="Potassium sulfate", reactants=["KOH", "H2SO4"], products=["K2SO4", "H2O"], answer=[2, 1, 1, 2],
         choices=[["K2SO4", "H2"], ["KCl", "H2O"], ["K2SO4"], ["K2SO4", "H2O"]], right=3,
         blurb="Potassium sulfate is a fertiliser that gives plants potassium without any chloride. A potassium base and sulfuric acid make it.",
         fennel="Two potassiums for one sulfate. It is that sort of afternoon."),
    dict(id="fizz", title="Fizz", reactants=["Na2CO3", "HCl"], products=["NaCl", "H2O", "CO2"], answer=[1, 2, 2, 1, 1],
         choices=[["NaCl", "H2O"], ["NaCl", "H2O", "CO2"], ["NaCl", "H2", "CO2"], ["NaCl", "H2O", "N2"]], right=1,
         blurb="A carbonate and an acid give off carbon dioxide gas, and that gas is the fizz. Chalk and limestone do the same thing.",
         fennel="Five formulas, and one of them leaves as a gas. It is allowed to."),
    dict(id="metal-in-acid", title="A metal in acid", reactants=["Al", "HCl"], products=["AlCl3", "H2"], answer=[2, 6, 2, 3],
         choices=[["AlCl3"], ["Al2O3", "H2"], ["AlCl3", "H2"], ["H2", "Cl2"]], right=2,
         blurb="Many metals dissolve in acid and release hydrogen gas. Aluminium in hydrochloric acid makes aluminium chloride and hydrogen.",
         fennel="Two, six, two, three. It is not a pattern. It is just true."),
    dict(id="chalk-from-salts", title="Chalk from two salts", reactants=["CaCl2", "Na2CO3"], products=["CaCO3", "NaCl"], answer=[1, 1, 1, 2],
         choices=[["CaCO3", "NaCl", "CO2"], ["CaCO3", "NaCl"], ["CaCO3"], ["CaCO3", "NaCl", "H2O"]], right=1,
         blurb="Two dissolved salts can swap partners. Calcium chloride and sodium carbonate swap to make solid calcium carbonate, which is chalk, and table salt.",
         fennel="They swap partners and neither one complains. Typical."),
    dict(id="copper-beats-silver", title="Copper beats silver", reactants=["Cu", "AgNO3"], products=["Cu(NO3)2", "Ag"], answer=[1, 2, 1, 2],
         choices=[["CuO", "AgNO3"], ["Cu(NO3)2"], ["Cu(NO3)2", "Ag", "H2O"], ["Cu(NO3)2", "Ag"]], right=3,
         blurb="Copper is more reactive than silver, so copper pushes silver out of a silver nitrate solution and silver crystals form. This is called displacement.",
         fennel="The more reactive metal wins. It is not even close."),
    dict(id="calcium-phosphate", title="Calcium phosphate", reactants=["Ca(OH)2", "H3PO4"], products=["Ca3(PO4)2", "H2O"], answer=[3, 2, 1, 6],
         choices=[["Ca3(PO4)2", "H2O"], ["Ca3(PO4)2", "H2"], ["CaCO3", "H2O"], ["Ca3(PO4)2"]], right=0,
         blurb="Calcium phosphate is the main mineral of bones and teeth, in a slightly different form. Slaked lime and phosphoric acid can make the plain salt.",
         fennel="Three, two, one, six. The hardest sum in the chapter, and my favourite."),
)
