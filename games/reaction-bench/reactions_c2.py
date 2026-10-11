"""Chapter 2, Burning: a fuel and oxygen go in; you choose what comes out from four lists, and only one list can be balanced.

`choices` are the candidate product lists in a fixed order (no shuffling); `right` is the index of the one that balances.
Every wrong list either holds an element that is not on the left, leaves an element out, or (a few) has every element but no
whole-number settings that come out equal. The tests prove exactly one of the four can be balanced.
"""

CHAPTER = {
    "id": "burning", "name": "Burning",
    "blurb": "A fuel meets oxygen. First choose what comes out, then balance it.",
}

REACTIONS = (
    dict(id="methane", title="Methane flame", reactants=["CH4", "O2"], products=["CO2", "H2O"], answer=[1, 2, 1, 2],
         choices=[["CO2"], ["H2O"], ["CO2", "H2O"], ["CO2", "H2O", "N2"]], right=2,
         blurb="Methane is the main part of natural gas. Burnt completely it makes carbon dioxide and water.",
         fennel="A tidy flame. I would call it polite, if flames could be."),
    dict(id="propane", title="Propane stove", reactants=["C3H8", "O2"], products=["CO2", "H2O"], answer=[1, 5, 3, 4],
         choices=[["CO2", "H2O", "N2"], ["CO2", "H2O"], ["H2O"], ["CO2"]], right=1,
         blurb="Propane is the fuel in many camping stoves and gas barbecues. It is sold as a liquid under pressure in a cylinder.",
         fennel="Five oxygens for one propane. It is a hungry molecule."),
    dict(id="ethanol", title="Ethanol fuel", reactants=["C2H5OH", "O2"], products=["CO2", "H2O"], answer=[1, 3, 2, 3],
         choices=[["H2O", "N2"], ["CO2"], ["CO2", "H2O"], ["CO2", "NaCl"]], right=2,
         blurb="Ethanol is the alcohol that is blended into petrol in many countries. Burnt completely it makes only carbon dioxide and water.",
         fennel="The OH hides inside the formula. Count it anyway."),
    dict(id="pentane", title="Pentane", reactants=["C5H12", "O2"], products=["CO2", "H2O"], answer=[1, 8, 5, 6],
         choices=[["H2O"], ["CO2", "H2O", "N2"], ["CO2"], ["CO2", "H2O"]], right=3,
         blurb="Pentane is one of the light liquids found in petrol.",
         fennel="Five carbons, twelve hydrogens. The dial only goes to twelve. It was close."),
    dict(id="ethyne", title="Welding flame", reactants=["C2H2", "O2"], products=["CO2", "H2O"], answer=[2, 5, 4, 2],
         choices=[["CO2", "H2O"], ["CO2", "NaCl"], ["H2O"], ["CO2"]], right=0,
         blurb="Ethyne, also called acetylene, burns very hot with oxygen, which is why it is used in welding torches.",
         fennel="Two, five, four, two. I would put it on a poster."),
    dict(id="sulfur", title="Sulfur burning", reactants=["S", "O2"], products=["SO2"], answer=[1, 1, 1],
         choices=[["CO2"], ["SO2", "CO2"], ["H2O"], ["SO2"]], right=3,
         blurb="Burning sulfur makes sulfur dioxide, a sharp-smelling gas and one of the causes of acid rain.",
         fennel="Everyone has a one-to-one-to-one. This is mine."),
    dict(id="glucose", title="Sugar, burnt and breathed", reactants=["C6H12O6", "O2"], products=["CO2", "H2O"], answer=[1, 6, 6, 6],
         choices=[["H2O", "N2"], ["CO2", "H2O"], ["CO2"], ["CO2", "H2O", "N2"]], right=1,
         blurb="Your cells use oxygen to break glucose down into carbon dioxide and water and release energy. It is the same overall equation as burning it.",
         fennel="Thirty-odd atoms in one sugar, and every one has to be accounted for. Nobody asked me if I minded."),
    dict(id="ammonia-burning", title="Ammonia in oxygen", reactants=["NH3", "O2"], products=["N2", "H2O"], answer=[4, 3, 2, 6],
         choices=[["N2"], ["H2O"], ["CO2", "H2O"], ["N2", "H2O"]], right=3,
         blurb="Ammonia does not burn easily in air, but in pure oxygen it burns to nitrogen and water.",
         fennel="Four ammonias, three oxygens. The ledger is tickled."),
)
