"""Teach the Machine -- the hand-written side of the lessons (dev tool; the game never runs this).

Each spec says what a lesson is about, which features its cases have, the hidden rule that gives every case its bin, which features that
rule really needs, which switches the lesson starts with, and what kind of lesson it is (which proof the builder demands):

  basic     one feature decides. Proof: the needed feature alone reaches the target; unless `gentle`, the starting switches do NOT.
  two       two features decide together. Proof: the two reach the target; no single feature and no starting set does.
  distract  the needed features decide, the rest is noise that tempts the tree. Proof: the needed features reach the target;
            the lesson STARTS with every switch on and that set does NOT reach it, so choosing matters.

All data is invented. `rule` gets a dict {feature id: value} and returns the bin index. The builder (build_lessons.py) draws the cases
with a seeded generator and keeps the first seed whose tables pass the proof for the lesson's kind, so every table is fixed and reproducible.
"""


def yn(fid, label, about, p=50):
    return {"id": fid, "label": label, "kind": "yes_no", "about": about, "p": p}


def num(fid, label, lo, hi, about, unit=""):
    return {"id": fid, "label": label, "kind": "number", "lo": lo, "hi": hi, "unit": unit, "about": about}


def kind(fid, label, values, about):
    return {"id": fid, "label": label, "kind": "kind", "values": list(values), "about": about}


SPECS = []


def lesson(**kw):
    kw.setdefault("target", 90)
    kw.setdefault("n_train", 16)
    kw.setdefault("n_test", 20)
    kw.setdefault("gentle", False)
    kw.setdefault("start", None)
    SPECS.append(kw)


# ---- Shelf 1: Sorting Basics (one decisive feature) -------------------------------------------------------------------------------
lesson(id="ripe-crates", shelf=0, kind="basic", gentle=True, noun="Crate", bins=["Ripe", "Not yet"],
       title="Ripe Crates", task="Crates of fruit come off the line. Sort the ripe ones from the rest.",
       features=[num("glow", "Glow", 0, 9, "how brightly the crate glows, 0 to 9"), yn("stripes", "Stripes", "whether the crate is striped"),
                 num("weight", "Weight", 1, 20, "how heavy it is", "kg")],
       rule=lambda v: 0 if v["glow"] >= 6 else 1, needs=["glow"],
       learned="Ripe crates glow 6 or more. Stripes and weight told Pip nothing.")
lesson(id="safe-doors", shelf=0, kind="basic", gentle=True, noun="Door", bins=["Safe", "Too hot"],
       title="Safe Doors", task="Some doors on Deck 2 are hot to the touch. Tell Pip which are safe to open.",
       features=[num("heat", "Door heat", 15, 80, "how hot the door feels", "C"), kind("handle", "Handle", ["round", "bar", "flat"], "the shape of the handle"),
                 num("number", "Door number", 1, 99, "the number painted on the door")],
       rule=lambda v: 0 if v["heat"] < 45 else 1, needs=["heat"],
       learned="A door under 45 C is safe. The handle and the number on the door do not matter.")
lesson(id="friendly-signals", shelf=0, kind="basic", noun="Signal", bins=["Friendly", "Unknown"],
       title="Friendly Signals", task="The radio hears pulses from the dark. Pip should flag the friendly ones.",
       features=[num("pulses", "Pulses", 5, 60, "pulses per minute", "per min"), kind("tone", "Tone", ["high", "low", "hiss"], "the pitch of the signal"),
                 num("gap", "Gap", 1, 9, "silence between bursts, 1 to 9")],
       rule=lambda v: 0 if v["pulses"] < 30 else 1, needs=["pulses"], start=["gap"],
       learned="Friendly signals pulse slowly, under 30 a minute.")
lesson(id="seed-tray", shelf=0, kind="basic", noun="Seed", bins=["Will sprout", "Will not"],
       title="Seed Tray", task="The greenhouse has one tray of seeds. Which will sprout?",
       features=[yn("husk", "Soft husk", "whether the husk is soft"), num("size", "Size", 2, 9, "how wide the seed is", "mm"),
                 num("age", "Age", 1, 24, "months in storage", "mo")],
       rule=lambda v: 0 if v["husk"] else 1, needs=["husk"], start=["size", "age"],
       learned="Seeds with a soft husk sprout. Size and age did not decide it.")
lesson(id="parcel-belt", shelf=0, kind="basic", noun="Parcel", bins=["Cold store", "Shelf"],
       title="Parcel Belt", task="Parcels roll past on a belt. Some must go to the cold store.",
       features=[yn("tag", "Cold tag", "whether a cold tag is on it"), num("weight", "Weight", 1, 30, "how heavy it is", "kg"),
                 num("dents", "Dents", 0, 5, "dents in the box, 0 to 5")],
       rule=lambda v: 0 if v["tag"] else 1, needs=["tag"], start=["weight"],
       learned="A parcel with a cold tag goes to the cold store, whatever its weight or dents.")
lesson(id="filter-check", shelf=0, kind="basic", noun="Filter", bins=["Clear", "Clogged"],
       title="Filter Check", task="Air filters hum along the corridor. Which are still clear?",
       features=[num("flow", "Flow", 10, 90, "air pushed through it", "l/min"), yn("hum", "Humming", "whether it hums"),
                 num("age", "Age", 1, 60, "days since it was fitted", "days")],
       rule=lambda v: 0 if v["flow"] >= 50 else 1, needs=["flow"], start=["hum", "age"],
       learned="A filter passing 50 litres a minute or more is clear. Humming and age were red herrings.")
lesson(id="battery-packs", shelf=0, kind="basic", noun="Pack", bins=["Charged", "Flat"],
       title="Battery Packs", task="A shelf of spare packs. Pip should find the charged ones.",
       features=[num("charge", "Charge", 0, 100, "how full it is", "%"), num("cycles", "Cycles", 1, 300, "times it has been recharged"),
                 yn("vent", "Vent open", "whether the vent flap is open")],
       rule=lambda v: 0 if v["charge"] >= 50 else 1, needs=["charge"], start=["vent"],
       learned="Packs at 50 percent or more are charged. Cycles and the vent flap do not say.")
lesson(id="pipe-taps", shelf=0, kind="basic", noun="Pipe", bins=["Sound", "Cracked"],
       title="Pipe Taps", task="Tap each pipe and listen. A cracked pipe rings differently.",
       features=[num("pitch", "Pitch", 100, 900, "the note when tapped", "Hz"), num("length", "Length", 1, 9, "how long the pipe is", "m"),
                 yn("scratches", "Scratches", "whether the outside is scratched")],
       rule=lambda v: 1 if v["pitch"] < 400 else 0, needs=["pitch"], start=["length"],
       learned="A pipe that rings below 400 Hz is cracked. Length and scratches say nothing about it.")

# ---- Shelf 2: Two Features (the answer needs two) ----------------------------------------------------------------------------------
lesson(id="night-crates", shelf=1, kind="two", noun="Crate", bins=["Ripe", "Not yet"], n_train=24,
       title="Night Crates", task="The night crates are trickier. A glow is not the whole story now.",
       features=[num("glow", "Glow", 0, 9, "how brightly the crate glows, 0 to 9"), yn("stripes", "Stripes", "whether the crate is striped"),
                 num("weight", "Weight", 1, 20, "how heavy it is", "kg"), num("age", "Age", 1, 12, "days since picking", "days")],
       rule=lambda v: 0 if v["glow"] >= 5 and not v["stripes"] else 1, needs=["glow", "stripes"], start=["glow"],
       learned="A crate is ripe when it glows 5 or more and has no stripes.")
lesson(id="hot-and-heavy", shelf=1, kind="two", noun="Door", bins=["Safe", "Keep shut"], n_train=24,
       title="Hot and Heavy", task="Doors on the pressure deck can be hot, or have air pushing on them, or both.",
       features=[num("heat", "Door heat", 15, 80, "how hot the door feels", "C"), num("pressure", "Pressure", 1, 9, "air pressing on it, 1 to 9"),
                 kind("handle", "Handle", ["round", "bar", "flat"], "the shape of the handle")],
       rule=lambda v: 0 if v["heat"] < 45 and v["pressure"] < 5 else 1, needs=["heat", "pressure"], start=["handle"],
       learned="A door is safe only if it is under 45 C and the pressure is under 5.")
lesson(id="signal-pairs", shelf=1, kind="two", noun="Signal", bins=["Friendly", "Unknown"], n_train=24,
       title="Signal Pairs", task="Two things can make a signal friendly. Pip needs to know about both.",
       features=[num("pulses", "Pulses", 5, 60, "pulses per minute", "per min"), kind("tone", "Tone", ["high", "low", "hiss"], "the pitch of the signal"),
                 num("gap", "Gap", 1, 9, "silence between bursts, 1 to 9")],
       rule=lambda v: 0 if v["pulses"] < 25 or v["tone"] == "low" else 1, needs=["pulses", "tone"], start=["pulses", "gap"],
       learned="A signal is friendly if it pulses under 25 a minute or has a low tone.")
lesson(id="cargo-docks", shelf=1, kind="two", noun="Case", bins=["Dock A", "Dock B", "Hold"], n_train=28,
       title="Cargo Docks", task="Cases go to one of two docks, or wait in the hold if they are delicate.",
       features=[yn("fragile", "Fragile", "whether it says fragile on the lid", 35), num("weight", "Weight", 1, 25, "how heavy it is", "kg"),
                 kind("wrap", "Wrapping", ["paper", "foil", "plain"], "what it is wrapped in")],
       rule=lambda v: 2 if v["fragile"] else (0 if v["weight"] >= 12 else 1), needs=["fragile", "weight"], start=["weight"],
       learned="Fragile cases wait in the hold. The rest go to Dock A if they weigh 12 kg or more, and Dock B if lighter.")
lesson(id="greenhouse-pots", shelf=1, kind="two", noun="Pot", bins=["Water now", "Leave"], n_train=24,
       title="Greenhouse Pots", task="Which pots need watering? Rain on the roof matters too.",
       features=[num("moisture", "Soil moisture", 0, 100, "how damp the soil is", "%"), yn("rained", "Rained on", "whether it was under the leaking roof"),
                 num("leaves", "Leaves", 2, 20, "leaves on the plant")],
       rule=lambda v: 0 if v["moisture"] < 35 and not v["rained"] else 1, needs=["moisture", "rained"], start=["leaves"],
       learned="A pot needs water if the soil is under 35 percent damp and it was not rained on.")
lesson(id="lift-loads", shelf=1, kind="two", noun="Load", bins=["Lift", "Wait"], n_train=24,
       title="Lift Loads", task="The crane can lift a load, or wait for better conditions.",
       features=[num("wind", "Wind", 0, 10, "wind on the pad, 0 to 10"), num("stack", "Stack height", 1, 12, "crates in the stack"),
                 num("crew", "Crew", 1, 9, "people on the pad")],
       rule=lambda v: 1 if v["wind"] >= 6 or v["stack"] >= 8 else 0, needs=["wind", "stack"], start=["stack"],
       learned="Wait if the wind is 6 or more, or the stack is 8 or taller. Otherwise lift.")
lesson(id="comms-priority", shelf=1, kind="two", noun="Message", bins=["Urgent", "Normal", "Later"], n_train=28,
       title="Comms Priority", task="Messages pile up. Crew first, then short ones, then the long ones.",
       features=[kind("sender", "Sender", ["crew", "depot", "vendor"], "who sent it"), num("words", "Words", 5, 120, "how long it is"),
                 num("hour", "Hour", 0, 23, "hour it arrived")],
       rule=lambda v: 0 if v["sender"] == "crew" else (1 if v["words"] < 50 else 2), needs=["sender", "words"], start=["sender", "hour"],
       learned="Messages from the crew are urgent. Others are normal if short (under 50 words) and later if long.")
lesson(id="tool-rack", shelf=1, kind="two", noun="Tool", bins=["Keep", "Recycle"], n_train=24,
       title="Tool Rack", task="Sort the old tools. Some are worth keeping, some are scrap.",
       features=[num("rust", "Rust", 0, 9, "rust on the tool, 0 to 9"), num("grip", "Grip", 0, 9, "how good the grip is, 0 to 9"),
                 num("length", "Length", 5, 60, "how long it is", "cm")],
       rule=lambda v: 0 if v["rust"] < 4 and v["grip"] >= 5 else 1, needs=["rust", "grip"], start=["length", "rust"],
       learned="Keep a tool with rust under 4 and a grip of 5 or more.")

# ---- Shelf 3: Distractions (more to look at is not better) -------------------------------------------------------------------------
lesson(id="noisy-crates", shelf=2, kind="distract", noun="Crate", bins=["Ripe", "Not yet"], n_train=14,
       title="Noisy Crates", task="Ripe crates again, but a crate can also be overripe. The crates carry stamps and codes too.",
       features=[num("glow", "Glow", 0, 9, "how brightly the crate glows, 0 to 9"), num("serial", "Serial", 1, 99, "the number stamped on the side"),
                 kind("dock", "Dock", ["north", "south", "east", "west"], "the dock it came from"), num("day", "Day packed", 1, 31, "day of the month it was packed")],
       rule=lambda v: 0 if 4 <= v["glow"] <= 7 else 1, needs=["glow"],
       learned="A crate is ripe when it glows 4 to 7: dimmer is green, brighter is overripe. The serial, the dock and the day were noise.")
lesson(id="crowded-doors", shelf=2, kind="distract", noun="Door", bins=["Safe", "Not safe"], n_train=14,
       title="Crowded Doors", task="Doors can be too hot or so cold they ice up. Every door has a lot of facts attached.",
       features=[num("heat", "Door heat", 15, 80, "how hot the door feels", "C"), num("number", "Door number", 1, 99, "the number painted on it"),
                 num("hinges", "Hinges", 2, 9, "hinges on the door"), yn("painted", "Painted", "whether it has been repainted")],
       rule=lambda v: 0 if 25 <= v["heat"] < 60 else 1, needs=["heat"],
       learned="A door from 25 C up to 59 C is safe: colder ices up, hotter burns. Number, hinges and paint were noise.")
lesson(id="busy-signals", shelf=2, kind="distract", noun="Signal", bins=["Friendly", "Unknown"], n_train=14,
       title="Busy Signals", task="The radio logs a lot about each signal. Most of it is not useful.",
       features=[num("pulses", "Pulses", 5, 60, "pulses per minute", "per min"), num("minute", "Minute heard", 0, 59, "minute of the hour it arrived"),
                 num("callsign", "Call sign", 100, 999, "the number it announces"), kind("antenna", "Antenna", ["north", "south", "dish"], "which antenna caught it")],
       rule=lambda v: 0 if 20 <= v["pulses"] <= 40 else 1, needs=["pulses"],
       learned="Friendly signals pulse between 20 and 40 a minute. The minute, the call sign and the antenna were noise.")
lesson(id="lab-samples", shelf=2, kind="distract", noun="Sample", bins=["Keep cold", "Room"], n_train=16,
       title="Lab Samples", task="Some samples fizz and need the cold shelf. The labels have lots of extras.",
       features=[yn("fizz", "Fizzing", "whether the sample fizzes", 45), num("temp", "Warmth", 5, 35, "how warm the room is where it sits", "C"), num("tray", "Tray", 1, 60, "the tray number"),
                 num("label", "Label length", 3, 14, "letters on the label"), kind("shift", "Shift", ["early", "late", "night"], "who logged it")],
       rule=lambda v: 0 if v["fizz"] and v["temp"] >= 20 else 1, needs=["fizz", "temp"],
       learned="A sample needs the cold shelf if it fizzes and sits in a room at 20 C or warmer. The tray, the label and the shift were noise.")
lesson(id="grain-sacks", shelf=2, kind="distract", noun="Sack", bins=["Dry first", "Store"], n_train=18,
       title="Grain Sacks", task="Damp grain spoils. Mould is a bad sign too. Everything else is paperwork.",
       features=[num("moisture", "Moisture", 2, 30, "how damp the grain is", "%"), yn("mould", "Mould smell", "whether it smells of mould", 30),
                 num("stitches", "Stitches", 10, 99, "stitches in the seam"), num("lot", "Lot", 100, 999, "the lot number")],
       rule=lambda v: 0 if v["moisture"] >= 14 or v["mould"] else 1, needs=["moisture", "mould"],
       learned="Dry the sack first if the grain is 14 percent damp or more, or smells of mould.")
lesson(id="workshop-bolts", shelf=2, kind="distract", noun="Bolt", bins=["Short", "Medium", "Long"], n_train=12,
       title="Workshop Bolts", task="Sort the bolts into three boxes by how long the threaded part is.",
       features=[num("thread", "Thread", 1, 60, "length of the thread", "mm"), num("stamp", "Stamp", 1, 99, "the maker's number"),
                 kind("box", "Old box", ["tin", "card", "bag"], "what it was found in"), num("row", "Shelf row", 1, 12, "the row it was on")],
       rule=lambda v: 0 if v["thread"] < 20 else (1 if v["thread"] < 40 else 2), needs=["thread"],
       learned="Thread under 20 mm is short, 20 to 39 medium, 40 and over long.")
lesson(id="water-taps", shelf=2, kind="distract", noun="Tap", bins=["Check", "Fine"], n_train=14,
       title="Water Taps", task="Taps that run too slowly or too fast need checking. Pip has several things to look at, and only one matters.",
       features=[num("flow", "Flow", 1, 12, "water per second, 1 to 12"), num("drips", "Drips", 0, 9, "drips after closing"),
                 num("tapno", "Tap number", 1, 99, "the number on the tap"), kind("room", "Room", ["galley", "lab", "bay", "bunk"], "where the tap is")],
       rule=lambda v: 0 if v["flow"] < 4 or v["flow"] > 9 else 1, needs=["flow"],
       learned="A tap needs checking if it runs under 4 (blocked) or over 9 (a loose washer). Drips, number and room were noise.")
lesson(id="drone-pings", shelf=2, kind="distract", noun="Ping", bins=["Real", "Echo"], n_train=18,
       title="Drone Pings", task="Drones send pings. Strong, fresh ones are real; the others are echoes.",
       features=[num("power", "Power", 0, 9, "how strong the ping is, 0 to 9"), yn("fresh", "Fresh", "whether it is a first ping", 70),
                 num("pingid", "Ping ID", 100, 999, "its id number"), kind("region", "Region", ["north", "south", "east", "west"], "where it came from")],
       rule=lambda v: 0 if v["power"] >= 5 and v["fresh"] else 1, needs=["power", "fresh"],
       learned="A ping is real when its power is 5 or more and it is fresh.")
