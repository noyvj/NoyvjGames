"""Void relic planner for prime parts (batch B #2).

This tracker's own builds (Zaw, Kitgun and Amp parts) are not relic drops, so
this is a manual planner: you add a prime part you want, the tool lists which
relics carry it, which of those are unvaulted, how many you own (typed), and
an opening/farming order.

DATA, read live from the Warframe Wiki on 2026-09-27 (nothing here is recalled):
  * the unvaulted relic list: https://wiki.warframe.com/w/Void_Relic
    ("Unvaulted/Available Relics" section: Lith 8, Meso 9, Neo 8, Axi 9 and one
    Requiem relic; 757 vaulted relics at the page's latest update, Hotfix 44.0.1,
    2026-09-24)
  * each relic's reward list and rarity, read from that relic's own page
    (https://wiki.warframe.com/w/<Relic_name>, e.g. .../w/Lith_A13), which also
    reported "AVAILABLE" (not vaulted) for every one of the 34 below
  * the refinement table (Void Relic page, "Refinement" and "Drop Chances")

NOT embedded, on purpose: the 757 vaulted relics (too many to embed and not
farmable anyway), the five Baro Ki'Teer exclusive relics (Neo O1, Axi A2, Axi A5,
Axi M5, Axi V8) and the Requiem relic "Requiem Eterna", which carries no prime
parts. Add any of them, or a relic that has since been unvaulted, with "add a
relic manually". The list can go stale the moment DE vaults or unvaults a relic:
check the Wiki page before spending Void Traces.
"""

import re

from wf_util import clean, dict_entries, find_ci, is_int, str_in

SOURCE_URL = "https://wiki.warframe.com/w/Void_Relic"
SOURCE_DATE = "2026-09-27"
SOURCE_NOTE = (
    "Unvaulted relics and their rewards read from the Warframe Wiki's Void Relic page and each relic's own page "
    f"({SOURCE_URL}) on {SOURCE_DATE}. Vaulted relics, Baro-exclusive relics and Requiem relics are not embedded: "
    "add them manually."
)

# One line per relic: three commons / two uncommons / one rare, exactly as the relic's
# Wiki page lists them ("2 X Forma Blueprint" is kept as the page writes it).
_RELIC_TEXT = """
Lith A13: Fang Prime Blade|Steflos Prime Receiver|Paris Prime Lower Limb / Dual Zoren Prime Blueprint|Gyre Prime Chassis Blueprint / Alternox Prime Blueprint
Lith C15: Daikyu Prime String|Corufell Prime Stock|Burston Prime Receiver / 2 X Forma Blueprint|Yareli Prime Blueprint / Cedo Prime Blueprint
Lith C7: Forma Blueprint|Hikou Prime Pouch|Valkyr Prime Blueprint / Nyx Prime Systems Blueprint|Scindo Prime Blueprint / Cernos Prime Lower Limb
Lith G14: Forma Blueprint|Lavos Prime Chassis Blueprint|Paris Prime Lower Limb / Fang Prime Handle|Vadarya Prime Receiver / Gyre Prime Neuroptics Blueprint
Lith L8: Orthos Prime Handle|Kestrel Prime Blade|Perigale Prime Blueprint / Alternox Prime Barrel|Akbolto Prime Link / Lavos Prime Systems Blueprint
Lith S18: Kestrel Prime Blade|Burston Prime Stock|Daikyu Prime String / Vadarya Prime Barrel|2 X Forma Blueprint / Styanax Prime Neuroptics Blueprint
Lith S19: Bronco Prime Receiver|Forma Blueprint|Braton Prime Barrel / Citrine Prime Systems Blueprint|Orthos Prime Blueprint / Sarofang Prime Blade
Lith V11: Kompressa Prime Blueprint|Braton Prime Stock|Orthos Prime Handle / Caliban Prime Blueprint|Dual Zoren Prime Blueprint / Voruna Prime Systems Blueprint
Meso A12: Perigale Prime Blueprint|Sarofang Prime Handle|Forma Blueprint / Voruna Prime Neuroptics Blueprint|Bronco Prime Barrel / Afentis Prime Blade
Meso C11: Kompressa Prime Blueprint|Lavos Prime Chassis Blueprint|Paris Prime Blueprint / 2 X Forma Blueprint|Daikyu Prime Upper Limb / Citrine Prime Blueprint
Meso D8: Braton Prime Blueprint|Bronco Prime Barrel|Dual Zoren Prime Handle / Voruna Prime Neuroptics Blueprint|Yareli Prime Blueprint / Daikyu Prime Grip
Meso D9: Paris Prime Upper Limb|Afentis Prime Handle|Burston Prime Blueprint / Cedo Prime Receiver|Steflos Prime Stock / Dual Zoren Prime Blade
Meso K9: Yareli Prime Chassis Blueprint|Athodai Prime Blueprint|Fang Prime Blueprint / Perigale Prime Receiver|Caliban Prime Blueprint / Kestrel Prime Grip
Meso N11: Cernos Prime Upper Limb|Scindo Prime Handle|Lex Prime Barrel / 2 X Forma Blueprint|Valkyr Prime Neuroptics Blueprint / Nyx Prime Neuroptics Blueprint
Meso V13: Braton Prime Blueprint|Bronco Prime Receiver|Forma Blueprint / Burston Prime Barrel|Caliban Prime Blueprint / Venato Prime Blade
Meso V17: Forma Blueprint|Corufell Prime Blueprint|Akbronco Prime Blueprint / Lavos Prime Blueprint|Paris Prime Grip / Voruna Prime Systems Blueprint
Meso Y2: Gyre Prime Systems Blueprint|Lex Prime Blueprint|Bronco Prime Receiver / Daikyu Prime Upper Limb|Styanax Prime Chassis Blueprint / Yareli Prime Neuroptics Blueprint
Neo A16: Dual Zoren Prime Handle|Perigale Prime Stock|Yareli Prime Chassis Blueprint / Lavos Prime Blueprint|Sarofang Prime Blueprint / Athodai Prime Barrel
Neo C10: Braton Prime Stock|Forma Blueprint|Caliban Prime Chassis Blueprint / Afentis Prime Barrel|Styanax Prime Systems Blueprint / Corufell Prime Receiver
Neo C11: Daikyu Prime Blueprint|Citrine Prime Chassis Blueprint|Lex Prime Receiver / Vadarya Prime Receiver|Cedo Prime Barrel / Caliban Prime Systems Blueprint
Neo C7: Braton Prime Barrel|Forma Blueprint|Kompressa Prime Blueprint / Vadarya Prime Receiver|Daikyu Prime Upper Limb / Caliban Prime Neuroptics Blueprint
Neo K10: Gyre Prime Systems Blueprint|Bronco Prime Blueprint|Forma Blueprint / Daikyu Prime Lower Limb|Venato Prime Blueprint / Kompressa Prime Barrel
Neo V13: Styanax Prime Blueprint|Paris Prime String|Sarofang Prime Handle / 2 X Forma Blueprint|Lavos Prime Neuroptics Blueprint / Vadarya Prime Blueprint
Neo V9: Forma Blueprint|Nyx Prime Blueprint|Venka Prime Blades / Cernos Prime Blueprint|Lex Prime Blueprint / Valkyr Prime Chassis Blueprint
Neo Y2: Lex Prime Blueprint|Burston Prime Stock|Venato Prime Handle / 2 X Forma Blueprint|Steflos Prime Blueprint / Yareli Prime Systems Blueprint
Axi A21: Vadarya Prime Stock|Styanax Prime Blueprint|Forma Blueprint / Cedo Prime Barrel|Voruna Prime Chassis Blueprint / Alternox Prime Stock
Axi A22: Venato Prime Handle|Dual Zoren Prime Handle|Burston Prime Blueprint / Kompressa Prime Receiver|Forma Blueprint / Afentis Prime Blueprint
Axi C12: Alternox Prime Receiver|Vadarya Prime Stock|Daikyu Prime Blueprint / Corufell Prime Handle|Kestrel Prime Blueprint / Citrine Prime Neuroptics Blueprint
Axi D6: Lavos Prime Chassis Blueprint|Lex Prime Receiver|Paris Prime Lower Limb / Cedo Prime Barrel|Orthos Prime Blade / Dual Zoren Prime Blade
Axi P10: Caliban Prime Chassis Blueprint|Fang Prime Blade|Forma Blueprint / Lavos Prime Neuroptics Blueprint|Athodai Prime Receiver / Perigale Prime Barrel
Axi S21: Cedo Prime Stock|Caliban Prime Chassis Blueprint|Dual Zoren Prime Handle / Gyre Prime Blueprint|2 X Forma Blueprint / Steflos Prime Barrel
Axi S8: Cernos Prime Grip|Forma Blueprint|Hikou Prime Blueprint / Nyx Prime Chassis Blueprint|Venka Prime Blueprint / Scindo Prime Blade
Axi V10: Cernos Prime String|Hikou Prime Stars|Lex Prime Receiver / 2 X Forma Blueprint|Valkyr Prime Systems Blueprint / Venka Prime Gauntlet
Axi V14: Alternox Prime Receiver|Fang Prime Blueprint|Lex Prime Barrel / 2 X Forma Blueprint|Kompressa Prime Receiver / Voruna Prime Blueprint
"""

RARITIES = ("Common", "Uncommon", "Rare")

# Void Relic page, "Drop Chances": the chance of each single reward (the page's
# parenthesised figure) at each refinement level, and the Void Traces to refine.
REFINEMENT = (
    {"name": "Intact", "traces": 0, "chance": {"Common": 25.33, "Uncommon": 11.0, "Rare": 2.0}},
    {"name": "Exceptional", "traces": 25, "chance": {"Common": 23.33, "Uncommon": 13.0, "Rare": 4.0}},
    {"name": "Flawless", "traces": 50, "chance": {"Common": 20.0, "Uncommon": 17.0, "Rare": 6.0}},
    {"name": "Radiant", "traces": 100, "chance": {"Common": 16.67, "Uncommon": 20.0, "Rare": 10.0}},
)

WANT_MAX = 30
CUSTOM_MAX = 40
CUSTOM_PARTS_MAX = 8
PART_NAME_MAX = 40
RELIC_NAME_MAX = 20
OWNED_MAX = 9999
_QTY_PREFIX = re.compile(r"^\d+\s*x\s+", re.IGNORECASE)


def part_key(item):
    """The part a reward row names, without a leading "2 X " quantity."""
    return _QTY_PREFIX.sub("", str(item).strip())


def _parse(text):
    relics = {}
    for line in text.strip().splitlines():
        name, _, body = line.partition(":")
        rows = []
        for rarity, group in zip(RARITIES, body.split(" / ")):
            for item in group.split("|"):
                item = item.strip()
                rows.append({"item": item, "part": part_key(item), "rarity": rarity})
        relics[name.strip()] = rows
    return relics


RELICS = _parse(_RELIC_TEXT)
FORMA_PART = "Forma Blueprint"


def default_relics():
    return {"wants": [], "owned": {}, "custom": []}


def is_default(rel):
    return not rel["wants"] and not rel["owned"] and not rel["custom"]


def relic_names(rel):
    return list(RELICS) + [c["n"] for c in rel["custom"]]


def resolve_relic(rel, text):
    return find_ci(relic_names(rel), text)


def known_parts(rel):
    """Every part named by an embedded or a custom relic, sorted."""
    parts = {row["part"] for rows in RELICS.values() for row in rows}
    for custom in rel["custom"]:
        parts.update(custom["p"])
    return sorted(parts)


def resolve_part(rel, text):
    """The canonical part name for typed text (case-insensitive), else the text itself."""
    text = clean(text, PART_NAME_MAX)
    return find_ci(known_parts(rel), text) or text


def chance(rarity, level="Intact"):
    for row in REFINEMENT:
        if row["name"] == level:
            return row["chance"].get(rarity)
    return None


def carriers(rel, part):
    """Every relic (embedded or your own) carrying `part`, with its rarity there and
    whether it is currently unvaulted."""
    found = []
    for name, rows in RELICS.items():
        for row in rows:
            if row["part"] == part:
                found.append({"relic": name, "rarity": row["rarity"], "unvaulted": True, "yours": False})
    for custom in rel["custom"]:
        if part in custom["p"]:
            found.append({"relic": custom["n"], "rarity": None, "unvaulted": custom["v"], "yours": True})
    return found


# --- edits ---------------------------------------------------------------

def add_want(rel, text):
    part = resolve_part(rel, text)
    if not part:
        return False, "Type the prime part you want, for example Braton Prime Barrel."
    if find_ci(rel["wants"], part):
        return False, "That part is already on your list."
    if len(rel["wants"]) >= WANT_MAX:
        return False, f"You can list up to {WANT_MAX} parts."
    rel["wants"].append(part)
    return True, f"Added {part}."


def remove_want(rel, text):
    part = find_ci(rel["wants"], text)
    if part is None:
        return False, "That part is not on your list."
    rel["wants"].remove(part)
    return True, f"Removed {part}."


def add_custom(rel, name, parts_text, unvaulted=True):
    """Adds a relic of your own (a Baro relic, a newly unvaulted one) with the parts it carries."""
    name = clean(name, RELIC_NAME_MAX)
    parts = []
    for piece in str(parts_text or "").split(","):
        piece = part_key(clean(piece, PART_NAME_MAX))
        if piece and not find_ci(parts, piece):
            parts.append(find_ci(known_parts(rel), piece) or piece)
    if not name:
        return False, "Give the relic a name, for example Neo O1."
    if not parts or len(parts) > CUSTOM_PARTS_MAX:
        return False, f"List 1 to {CUSTOM_PARTS_MAX} parts separated by commas."
    if resolve_relic(rel, name):
        return False, "A relic with that name already exists."
    if len(rel["custom"]) >= CUSTOM_MAX:
        return False, f"You can add up to {CUSTOM_MAX} relics of your own."
    rel["custom"].append({"n": name, "v": bool(unvaulted), "p": parts})
    return True, f"Added relic {name}."


def remove_custom(rel, name):
    entry = find_ci([c["n"] for c in rel["custom"]], name)
    if entry is None:
        return False, "No relic of your own with that name."
    rel["custom"] = [c for c in rel["custom"] if c["n"] != entry]
    rel["owned"].pop(entry, None)
    return True, f"Removed relic {entry}."


def set_owned(rel, name, count):
    relic = resolve_relic(rel, name)
    if relic is None:
        return False, "Unknown relic. Pick one from the list, or add it manually first."
    if not is_int(count) or not 0 <= count <= OWNED_MAX:
        return False, f"Type a number from 0 to {OWNED_MAX}."
    if count:
        rel["owned"][relic] = count
    else:
        rel["owned"].pop(relic, None)
    return True, f"You own {count} x {relic}."


# --- the plan ------------------------------------------------------------

def best_level(carried):
    """The refinement level that maximises the summed chance of the wanted parts a
    relic carries (cheapest level on a tie). Pure arithmetic on the Wiki's table."""
    best = None
    for level in REFINEMENT:
        total = sum(level["chance"].get(c["rarity"], 0) for c in carried if c["rarity"])
        if best is None or total > best[1] + 1e-9:
            best = (level, total)
    return best


def build_plan(rel):
    """Per wanted part: who carries it. Plus one ordered list of relics worth opening."""
    wants = []
    by_relic = {}
    for part in rel["wants"]:
        found = carriers(rel, part)
        wants.append({"part": part, "carriers": found,
                      "unvaulted": [c for c in found if c["unvaulted"]],
                      "known": bool(found)})
        for c in found:
            if c["unvaulted"]:
                by_relic.setdefault(c["relic"], []).append({"part": part, "rarity": c["rarity"]})
    steps = []
    for name, carried in by_relic.items():
        owned = rel["owned"].get(name, 0)
        level, total = best_level(carried)
        steps.append({"relic": name, "carries": carried, "owned": owned, "level": level["name"],
                      "traces": level["traces"], "chance_sum": round(total, 2),
                      "yours": name not in RELICS})
    steps.sort(key=lambda s: (-len(s["carries"]), 0 if s["owned"] else 1, -s["chance_sum"], s["relic"]))
    owned_total = sum(s["owned"] for s in steps)
    return {"wants": wants, "steps": steps, "owned_total": owned_total}


def step_text(step, number):
    parts = ", ".join(
        c["part"] + (f" ({c['rarity']})" if c["rarity"] else "") for c in step["carries"]
    )
    head = f"{number}. {step['relic']}: carries {parts}."
    if step["owned"]:
        action = f" You own {step['owned']}: open these first"
    else:
        action = " You own none: farm it"
    if step["chance_sum"]:
        if step["traces"]:
            action += f", refine to {step['level']} ({step['traces']} Void Traces)"
        else:
            action += ", keep it Intact (no Void Traces)"
        action += f", about {step['chance_sum']:g}% chance of a wanted part per relic opened"
    return head + action + "."


def plan_lines(plan):
    lines = []
    for want in plan["wants"]:
        if not want["known"]:
            lines.append(f"{want['part']}: not in the embedded relic data. Look it up on the Wiki and add its relic manually.")
        elif not want["unvaulted"]:
            lines.append(f"{want['part']}: every relic that carries it is vaulted, so it cannot be farmed from relics right now.")
        else:
            names = ", ".join(c["relic"] + (f" ({c['rarity']})" if c["rarity"] else "") for c in want["unvaulted"])
            lines.append(f"{want['part']}: {names}.")
    return lines


def forma_relics(rel=None):
    """Embedded relics that carry a Forma Blueprint (a way to farm Forma), for the forma planner."""
    return [name for name, rows in RELICS.items() if any(r["part"] == FORMA_PART for r in rows)]


# --- save/load -----------------------------------------------------------

def export(rel):
    out = {}
    if rel["wants"]:
        out["wants"] = list(rel["wants"])
    if rel["owned"]:
        out["owned"] = dict(rel["owned"])
    if rel["custom"]:
        out["custom"] = [{"n": c["n"], "v": c["v"], "p": list(c["p"])} for c in rel["custom"]]
    return out


def load(data):
    """Validates a saved "relics" value: wrong types, bad bounds and unknown relics are dropped."""
    rel = default_relics()
    if not isinstance(data, dict):
        return rel
    for entry in dict_entries(data.get("custom"))[:CUSTOM_MAX]:
        name, parts, vault = entry.get("n"), entry.get("p"), entry.get("v")
        if not (isinstance(name, str) and name.strip() and isinstance(parts, list) and isinstance(vault, bool)):
            continue
        name = name.strip()[:RELIC_NAME_MAX]
        clean_parts = []
        for piece in parts[:CUSTOM_PARTS_MAX]:
            if isinstance(piece, str) and piece.strip() and not find_ci(clean_parts, piece):
                clean_parts.append(piece.strip()[:PART_NAME_MAX])
        if clean_parts and not resolve_relic(rel, name):
            rel["custom"].append({"n": name, "v": vault, "p": clean_parts})
    wants = data.get("wants")
    for text in wants[:WANT_MAX] if isinstance(wants, list) else []:
        if isinstance(text, str) and text.strip() and not find_ci(rel["wants"], text):
            rel["wants"].append(text.strip()[:PART_NAME_MAX])
    owned = data.get("owned")
    if isinstance(owned, dict):
        for name, count in owned.items():
            if str_in(name, relic_names(rel)) and is_int(count) and 1 <= count <= OWNED_MAX:
                rel["owned"][name] = count
    return rel
