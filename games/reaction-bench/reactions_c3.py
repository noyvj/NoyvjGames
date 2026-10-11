"""Chapter 3, Oxides and Salts: bracket groups. A group in brackets, like (OH) in Ca(OH)2, is a unit whose atoms are all multiplied
by the number after the bracket, and the page draws the bracket so you can see the unit. Products are chosen from four lists again.
"""

CHAPTER = {
    "id": "oxides-salts", "name": "Oxides and Salts",
    "blurb": "Some formulas hide a group in brackets. The number after the bracket multiplies every atom inside it.",
}

REACTIONS = (
    dict(id="limestone", title="Limestone to lime", reactants=["CaCO3"], products=["CaO", "CO2"], answer=[1, 1, 1],
         choices=[["CaO"], ["CaO", "CO2"], ["CO2"], ["CaO", "N2"]], right=1,
         blurb="Heating limestone drives off carbon dioxide and leaves quicklime. People have made lime this way for mortar for thousands of years.",
         fennel="One goes in, two come out. It is the closest thing to a bargain in here."),
    dict(id="slaked-lime", title="Slaked lime", reactants=["CaO", "H2O"], products=["Ca(OH)2"], answer=[1, 1, 1],
         choices=[["CaCO3"], ["H2O2"], ["Ca(OH)2"], ["Ca", "O2"]], right=2,
         blurb="Quicklime reacts with water to make slaked lime, and it gives off a lot of heat as it does.",
         fennel="Bracket, two. Take the O and the H and double them. Both of them."),
    dict(id="limewater", title="Limewater test", reactants=["Ca(OH)2", "CO2"], products=["CaCO3", "H2O"], answer=[1, 1, 1, 1],
         choices=[["CaO", "H2O"], ["CaCO3"], ["CaCO3", "H2O", "NaCl"], ["CaCO3", "H2O"]], right=3,
         blurb="Limewater, a solution of calcium hydroxide, turns cloudy when carbon dioxide is bubbled through it, because tiny crystals of calcium carbonate form.",
         fennel="Four ones in a row. Please enjoy it while it lasts."),
    dict(id="baking-soda", title="Baking soda", reactants=["NaHCO3"], products=["Na2CO3", "H2O", "CO2"], answer=[2, 1, 1, 1],
         choices=[["Na2CO3", "H2O"], ["NaCl", "H2O", "CO2"], ["Na2CO3", "H2O", "CO2"], ["Na2O", "CO2"]], right=2,
         blurb="Baking soda gives off carbon dioxide when it is heated, and that gas is what makes a cake rise.",
         fennel="Two go in, three things come out. The sums are irritatingly fair."),
    dict(id="peroxide", title="Peroxide", reactants=["H2O2"], products=["H2O", "O2"], answer=[2, 2, 1],
         choices=[["H2O"], ["H2", "N2"], ["H2O", "O2"], ["H2O", "N2"]], right=2,
         blurb="Hydrogen peroxide slowly breaks down into water and oxygen, which is why it is sold in dark bottles.",
         fennel="It falls apart on its own. Relatable."),
    dict(id="aluminium-hydroxide", title="Aluminium hydroxide", reactants=["Al(OH)3"], products=["Al2O3", "H2O"], answer=[2, 1, 3],
         choices=[["Al", "H2O"], ["AlCl3", "H2O"], ["Al2O3"], ["Al2O3", "H2O"]], right=3,
         blurb="Aluminium hydroxide is used in some indigestion medicines and as a fire retardant. Heated, it loses water and leaves aluminium oxide.",
         fennel="Three OH groups, three brackets' worth of patience."),
    dict(id="rust-wet-step", title="Rust, the wet step", reactants=["Fe(OH)2", "O2", "H2O"], products=["Fe(OH)3"], answer=[4, 1, 2, 4],
         choices=[["Fe2O3"], ["FeCl3"], ["Fe(OH)3"], ["Fe(OH)3", "CO2"]], right=2,
         blurb="Iron(II) hydroxide turns into iron(III) hydroxide when oxygen reaches it in water, one of the steps in how rust forms.",
         fennel="Three things in, one thing out. Bring a pencil."),
    dict(id="fertiliser", title="Fertiliser", reactants=["NH3", "H2SO4"], products=["(NH4)2SO4"], answer=[2, 1, 1],
         choices=[["NH4Cl"], ["(NH4)2SO4", "H2O"], ["N2", "SO2"], ["(NH4)2SO4"]], right=3,
         blurb="Ammonium sulfate is a widely used fertiliser. It feeds crops nitrogen and some sulfur.",
         fennel="Two ammonias walk into a sulfuric acid. Nothing else happens, which is the good outcome."),
)
