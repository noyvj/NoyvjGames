"""Station Medic -- the lexicon: every sign, scan, supply, treatment and condition in the game.

All of it is invented for the station. Nothing here is a real condition, drug or treatment, and none of it is medical
advice (a test scans every player-facing string for real medical words). A condition is defined by what a patient shows
(its signs), which scans read positive for it (its findings) and what settles it (cures cure it, an ease only settles it
with a cost). The rules that use these tables live in shift.py.
"""

# ---- signs: what a patient shows -------------------------------------------------------------------------------------
SIGNS = (
    ("flushed", "Flushed"), ("pale", "Pale"), ("chills", "Chills"), ("sweating", "Sweating"),
    ("cough", "Cough"), ("aching", "Aching"), ("rash", "Rash"), ("dizzy", "Dizzy"),
    ("drowsy", "Drowsy"), ("thirst", "Thirst"), ("blurred", "Blurred sight"), ("numb", "Numb fingers"),
    ("cramps", "Cramps"), ("shaking", "Shaking"), ("flecks", "Spore flecks"), ("ringing", "Ringing ears"),
)
SIGN_NAME = dict(SIGNS)
SIGN_IDS = tuple(s for s, _n in SIGNS)
SHAKING = "shaking"      # a shaking patient must be steadied before a scan or a treatment
FLECKS = "flecks"        # the sign of the contagious conditions

# ---- supplies (the cabinet's shelves) ------------------------------------------------------------------------------------
# id, name, glyph (a letter so a shelf is never told apart by colour alone)
ITEMS = (
    ("roll", "Paper roll", "R"), ("vials", "Glass vials", "V"), ("cells", "Lamp cells", "C"), ("liners", "Cuff liners", "L"),
    ("tonic", "Slate tonic", "T"), ("gel", "Pearl gel", "G"), ("drip", "Brine drip", "D"), ("wrap", "Kelp wraps", "K"),
    ("loz", "Wick lozenges", "W"), ("salve", "Tin salve", "S"), ("band", "Steadying bands", "B"),
)
ITEM_IDS = tuple(i[0] for i in ITEMS)
ITEM_NAME = {i[0]: i[1] for i in ITEMS}
ITEM_GLYPH = {i[0]: i[2] for i in ITEMS}

# ---- scans: a yes or no reading each ---------------------------------------------------------------------------------
# id, name, supply used, what a positive reading looks like, codex line
TESTS = (
    ("dye", "Dye strip", "roll", "turns blue", "A strip cut from the paper roll. It turns blue on contact with some conditions and stays pale on others."),
    ("lamp", "Lamp scan", "cells", "glows amber", "A hand lamp that burns through one cell per reading. Some conditions make the skin glow amber under it."),
    ("pulse", "Pulse cuff", "liners", "drums fast", "A cuff with a disposable liner. It reads a fast drumming pulse for some conditions and a steady one for others."),
    ("breath", "Breath vial", "vials", "clouds", "A glass vial the patient breathes into. It clouds for some conditions and stays clear for others."),
)
TEST_IDS = tuple(t[0] for t in TESTS)
TEST_BY_ID = {t[0]: {"id": t[0], "name": t[1], "item": t[2], "positive": t[3], "blurb": t[4]} for t in TESTS}

# ---- treatments ------------------------------------------------------------------------------------------------------------
# id, name, supply used, tags (a chart note can forbid a tag; two heavy treatments on one patient clash), codex line
TREATMENTS = (
    ("tonic", "Slate tonic", "tonic", ("heavy",), "A grey tonic from the lower stores. It works well and sits heavy: two heavy treatments never go together."),
    ("gel", "Pearl gel", "gel", (), "The gentlest thing in the cabinet. It cures a lot of ordinary conditions and clashes with nothing."),
    ("patch", "Moth patch", "roll", (), "A patch cut from the same roll as the dye strips, so every patch is a strip not made."),
    ("drip", "Brine drip", "drip", ("brine",), "A slow drip of salt water and something bitter. Charts that say to avoid brine mean this."),
    ("wrap", "Kelp wrap", "wrap", ("cold",), "A cool wrap grown in the hydroponics bay. Charts that note cold sensitivity rule it out."),
    ("loz", "Wick lozenge", "loz", ("wick",), "A lozenge scented with burnt wick. Some charts carry a wick reaction and must avoid it."),
    ("draught", "Hush draught", "vials", ("heavy",), "A quiet draught decanted into the same glass vials the breath scan needs. Heavy, like the tonic."),
    ("salve", "Tin salve", "salve", ("cold",), "A cold, metallic salve. It works fast and the cold-sensitive cannot take it."),
)
TX_IDS = tuple(t[0] for t in TREATMENTS)
TX_BY_ID = {t[0]: {"id": t[0], "name": t[1], "item": t[2], "tags": frozenset(t[3]), "blurb": t[4]} for t in TREATMENTS}
BAND = {"name": "Steadying band", "item": "band"}
BAND_ITEM = "band"

# A chart note forbids a treatment tag. id -> (tag it forbids, the note on the chart)
TRAITS = {
    "brine": ("brine", "Chart note: avoid brine treatments."),
    "wick": ("wick", "Chart note: a wick reaction is on file."),
    "heavy": ("heavy", "Chart note: no heavy treatments."),
    "cold": ("cold", "Chart note: sensitive to cold treatments."),
}
CLASH_TAG = "heavy"

# ---- conditions ----------------------------------------------------------------------------------------------------------------
# id, name, signs, findings (scans that read positive), cures, ease, contagious, codex line
_C = (
    ("coil", "Coil Fever", ("flushed", "sweating"), ("pulse",), ("gel", "wrap"), "loz", False, "A heat that settles in the chest like warm wire. Common on the engine decks."),
    ("ember", "Ember Fever", ("flushed", "sweating"), ("lamp",), ("tonic", "salve"), "gel", False, "A fever that glows. It looks the same as Coil Fever until a lamp is held to the skin."),
    ("brass", "Brass Fever", ("flushed", "sweating"), ("pulse", "lamp"), ("drip", "gel"), "wrap", False, "The two fevers at once, in one body. It rings on both scans."),
    ("vent", "Vent Cough", ("cough", "aching"), ("breath",), ("loz", "gel"), "patch", False, "A dry cough that comes up the air shafts, worse near the old vents."),
    ("dust", "Dust Cough", ("cough", "aching"), ("dye",), ("tonic", "drip"), "loz", False, "Grey dust from the filter stores. It stains a dye strip blue."),
    ("rasp", "Hull Rasp", ("cough", "aching"), (), ("patch", "wrap"), "tonic", False, "A rasp with nothing to find. It reads clear on every scan and still wants treating."),
    ("drift", "Drift Sick", ("dizzy", "drowsy"), ("dye",), ("draught", "patch"), "gel", False, "The floor seems to tilt. Common after a long spell in the outer corridors."),
    ("hum", "Low Hum", ("dizzy", "drowsy"), ("lamp",), ("gel", "tonic"), "loz", False, "A low hum behind the eyes that makes the day slow down."),
    ("tide", "Slow Tide", ("dizzy", "drowsy"), ("breath",), ("loz", "drip"), "wrap", False, "A heavy, slow feeling, like wading. It clouds the breath vial."),
    ("emberrash", "Ember Rash", ("rash", "flushed"), ("dye",), ("patch", "salve"), "gel", False, "Red patches near the galley. It turns a dye strip blue."),
    ("mothrash", "Moth Rash", ("rash", "flushed"), (), ("wrap", "gel"), "patch", False, "Pale, papery patches. No scan finds it; the signs are all there is."),
    ("coldh", "Cold Hands", ("chills", "numb"), ("lamp",), ("loz", "tonic"), "gel", False, "Fingers that will not warm. Lamp scans glow amber on the knuckles."),
    ("frost", "Frost Lock", ("chills", "numb"), (), ("drip", "patch"), "salve", False, "Cold that goes inward. It hides from every scan."),
    ("lampeye", "Lamp Eye", ("blurred", "aching"), ("pulse",), ("gel", "patch"), "wrap", False, "Sight that smears around lights. The pulse drums fast."),
    ("static", "Static Eye", ("blurred", "aching"), ("breath",), ("wrap", "draught"), "gel", False, "Sight that fizzes like a dead screen. The breath vial clouds."),
    ("brine", "Brine Cramp", ("thirst", "cramps"), ("dye",), ("tonic", "salve"), "drip", False, "Cramps from too little water and too much salt. Stains the dye strip."),
    ("seam", "Dry Seam", ("thirst", "cramps"), ("pulse",), ("drip", "patch"), "loz", False, "A tight, dry ache along the sides. The pulse drums."),
    ("saltt", "Salt Tremor", ("shaking", "thirst"), ("lamp",), ("tonic", "gel"), "loz", False, "Hands that will not hold still, and a thirst that does not end. Glows amber under the lamp."),
    ("loose", "Loose Shake", ("shaking", "thirst"), ("dye",), ("draught", "patch"), "wrap", False, "A shake that comes in waves. It is Salt Tremor's twin and stains the dye strip."),
    ("shiver", "Shiver Shake", ("shaking", "chills"), (), ("loz", "wrap"), "gel", False, "A shake with a chill under it. Nothing reads on a scan."),
    ("rattle", "Rattle Drift", ("shaking", "dizzy"), ("breath",), ("gel", "draught"), "tonic", False, "A rattle in the bones and a tilting floor. The breath vial clouds."),
    ("spore", "Spore Cough", ("cough", "flecks"), ("breath",), ("loz", "gel"), "patch", True, "A cough with flecks of spore on the cloth. It spreads in a shared ward. Treat it in the cold room."),
    ("soot", "Soot Cough", ("cough", "flecks"), ("dye",), ("tonic", "patch"), "loz", False, "Soot from the galley vents looks just like spore. It does not spread."),
    ("fleckrash", "Fleck Rash", ("rash", "flecks"), ("dye",), ("patch", "wrap"), "gel", True, "A rash dotted with spore flecks. It spreads by touch."),
    ("moss", "Moss Fever", ("flushed", "flecks"), ("pulse",), ("gel", "tonic"), "salve", True, "A fever with a green dusting on the skin. It spreads in a shared ward."),
    ("grit", "Grit Flush", ("flushed", "flecks"), ("lamp",), ("wrap", "gel"), "loz", False, "Metal grit under the skin looks like moss. It is harmless to the others."),
    ("palemoss", "Pale Moss", ("pale", "flecks"), ("lamp",), ("drip", "salve"), "gel", True, "A pallor with a fine green dusting. It spreads, slowly, and glows under the lamp."),
    ("ring", "Ring Dizzy", ("ringing", "dizzy"), ("pulse",), ("gel", "draught"), "loz", False, "A thin ringing in the ears and a floor that will not stay put."),
    ("palew", "Pale Drift", ("pale", "drowsy"), ("dye",), ("tonic", "loz"), "gel", False, "A washed-out, sleepy pallor. Stains the dye strip."),
    ("hollow", "Hollow Ache", ("pale", "aching"), ("breath",), ("wrap", "patch"), "tonic", False, "An ache that sits in the middle of the chest like an empty room."),
)
COND_IDS = tuple(c[0] for c in _C)
COND = {}
for _id, _name, _signs, _finds, _cures, _ease, _spreads, _blurb in _C:
    COND[_id] = {"id": _id, "name": _name, "signs": frozenset(_signs), "findings": frozenset(_finds), "cures": tuple(_cures),
                 "ease": _ease, "spreads": _spreads, "blurb": _blurb}


def name_of(kind, ident):
    table = {"sign": SIGN_NAME, "item": ITEM_NAME}
    if kind in table:
        return table[kind].get(ident, ident)
    if kind == "test":
        return TEST_BY_ID[ident]["name"]
    if kind == "tx":
        return TX_BY_ID[ident]["name"]
    if kind == "cond":
        return COND[ident]["name"]
    return ident
