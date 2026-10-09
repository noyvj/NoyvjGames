"""Station Medic -- the crew of Lowlight Station. Names and roles live here; each crew member's short story (their beats)
is added in the crew-files milestone. Everyone is flawed and gentle; nobody dies; the medic is not a hero either."""

# id, name, role
CREW = (
    ("maren", "Maren Oyelaran", "hydroponics tech"),
    ("dov", "Dov Kestrel", "chief engineer"),
    ("imre", "Imre Solace", "cadet"),
    ("nell", "Nell Archer", "quartermaster"),
    ("teo", "Teo Banik", "night cook"),
    ("halloran", "Halloran Pike", "pilot"),
    ("yusra", "Yusra Delacroix", "comms officer"),
    ("kit", "Kit Marlowe", "drone wrangler"),
    ("orla", "Orla Venn", "station commander"),
    ("pell", "Pell Ansgar", "retired surveyor"),
)
CREW_IDS = tuple(c[0] for c in CREW)
CREW_BY_ID = {c[0]: {"id": c[0], "name": c[1], "role": c[2]} for c in CREW}
