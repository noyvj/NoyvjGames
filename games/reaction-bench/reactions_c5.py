"""Chapter 5, Works: industrial routes in two steps. Each route is two orders; what the first one makes is carried into the second.

A step-two order opens only when its step-one order is on the shelf (data: `route`, `step`, and `carries` on step one, which must be a
product of step one and a reactant of step two). Products are chosen from four lists, and the dials work as before.
"""

CHAPTER = {
    "id": "works", "name": "Works",
    "blurb": "Real plants make things in two steps. Each route here has two orders: what the first makes is carried into the second, which opens once the first is on the shelf.",
}

ROUTES = {
    "sulfuric": "Sulfuric acid works",
    "fertiliser": "Fertiliser works",
    "iron": "Iron works",
    "sugar": "Sugar works",
}

REACTIONS = (
    dict(id="sulfur-trioxide", route="sulfuric", step=1, carries="SO3", title="Sulfur trioxide", reactants=["SO2", "O2"], products=["SO3"], answer=[2, 1, 2],
         choices=[["SO3", "CO2"], ["SO3"], ["SO2"], ["H2SO4"]], right=1,
         blurb="In a sulfuric acid works, sulfur dioxide takes up more oxygen and becomes sulfur trioxide. A catalyst speeds it along.",
         fennel="Two in, one oxygen, two out. The first half of something bigger."),
    dict(id="sulfuric-acid", route="sulfuric", step=2, title="Sulfuric acid", reactants=["SO3", "H2O"], products=["H2SO4"], answer=[1, 1, 1],
         choices=[["SO2"], ["H2SO4", "O2"], ["H2SO4"], ["H2SO4", "CO2"]], right=2,
         blurb="Sulfuric acid is one of the most widely made chemicals, and most of it goes into fertiliser.",
         fennel="All ones. After the last order I think I have earned them."),
    dict(id="haber", route="fertiliser", step=1, carries="NH3", title="Ammonia, the Haber step", reactants=["N2", "H2"], products=["NH3"], answer=[1, 3, 2],
         choices=[["N2"], ["NH3", "H2O"], ["H2"], ["NH3"]], right=3,
         blurb="The Haber process makes ammonia from nitrogen in the air and hydrogen. It feeds the fertiliser industry and changed farming.",
         fennel="Three hydrogens for every nitrogen. Every farmer owes this ratio."),
    dict(id="ammonium-phosphate", route="fertiliser", step=2, title="Ammonium phosphate", reactants=["NH3", "H3PO4"], products=["(NH4)3PO4"], answer=[3, 1, 1],
         choices=[["(NH4)3PO4"], ["NH4Cl"], ["(NH4)3PO4", "H2"], ["NH3"]], right=0,
         blurb="Ammonium phosphate is a fertiliser that gives crops both nitrogen and phosphorus.",
         fennel="Take the ammonia you carried over. I kept it warm."),
    dict(id="iron-from-ore", route="iron", step=1, carries="Fe", title="Iron from its ore", reactants=["Fe2O3", "C"], products=["Fe", "CO2"], answer=[2, 3, 4, 3],
         choices=[["Fe"], ["Fe", "CO2"], ["Fe", "H2O"], ["Fe3O4", "C"]], right=1,
         blurb="Most iron is made from its oxide ore with carbon in a furnace, which takes the oxygen away as carbon dioxide. The iron then goes on to be made into steel.",
         fennel="Rust, run backwards. I like to think of it as an apology."),
    dict(id="iron-chloride", route="iron", step=2, title="Iron(III) chloride", reactants=["Fe", "Cl2"], products=["FeCl3"], answer=[2, 3, 2],
         choices=[["Fe2O3"], ["FeCl3", "H2"], ["FeCl3"], ["NaCl"]], right=2,
         blurb="Iron(III) chloride is used to clean up water and to etch circuit boards.",
         fennel="You carried iron out of a furnace for this. I am moved."),
    dict(id="photosynthesis", route="sugar", step=1, carries="C6H12O6", title="Photosynthesis", reactants=["CO2", "H2O"], products=["C6H12O6", "O2"], answer=[6, 6, 1, 6],
         choices=[["C6H12O6"], ["C6H12O6", "O2", "N2"], ["C6H12O6", "O2"], ["CO2", "H2"]], right=2,
         blurb="Plants build sugar from carbon dioxide and water using sunlight, and they give off oxygen. Nearly all the food on Earth traces back to this.",
         fennel="Six, six, one, six. A leaf does it without a ledger."),
    dict(id="sugar-to-fuel", route="sugar", step=2, title="Sugar to fuel", reactants=["C6H12O6"], products=["C2H5OH", "CO2"], answer=[1, 2, 2],
         choices=[["C2H5OH", "CO2", "N2"], ["C2H5OH"], ["CO2", "H2O"], ["C2H5OH", "CO2"]], right=3,
         blurb="Yeast turns sugar into ethanol and carbon dioxide. The ethanol can be used as a fuel, and many countries blend it into petrol.",
         fennel="One sugar, four things out. The yeast does the heavy lifting."),
)
