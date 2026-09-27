"""Crafting tracker (batch B #3) and pet breeding/imprint log (batch B #6).

CRAFTING TRACKER: a manual list of foundry items (weapons, warframes, companions)
and their component needs. A need whose name matches one of the tracker's 65
resources takes its "have" from the live resource inventory (built + raw);
any other component keeps a count you type.

IMPORTED OWNERSHIP: the lastData.dat / inventory.json import can mark an item as
already owned. The inventory response's owned-equipment arrays are named in the
open-source SpaceNinjaServer type definitions
(https://github.com/SpaceNinjaServer/SpaceNinjaServer, src/types/inventoryTypes/
inventoryTypes.ts, read 2026-09-27): Suits, LongGuns, Pistols, Melee, Sentinels,
SentinelWeapons, KubrowPets, MoaPets and OperatorAmps, each element carrying an
"ItemType" path. That is a community server that mirrors the real response's shape,
not Digital Extremes' own documentation, and this project still has no real export
to test against. So the match is best-effort: the last part of each ItemType path,
lower-cased with punctuation removed, is compared with the craft's name the same
way ("Excalibur Prime" against ".../ExcaliburPrime"). Weapon paths often do not end
in the wiki name, so those simply stay unmatched and you tick them by hand. The
import result says how many items it saw and which crafts it marked.

PET LOG: fully manual. Nothing in the tracker assumes the import exposes pet or
mod data (KubrowPets is named in the type definitions above, but this project has no
real file to prove what is inside it). Facts shown beside the log were read from the
Warframe Wiki's Kubrow and Kavat pages on 2026-09-27.
"""

from wf_util import clean, dict_entries, find_ci, is_int, norm, pooled, str_in

CRAFT_KINDS = ("weapon", "warframe", "companion")
CRAFT_KIND_LABELS = {"weapon": "Weapon", "warframe": "Warframe", "companion": "Companion"}
CRAFT_MAX = 40
NEED_MAX = 20
CRAFT_NAME_MAX = 40
NEED_NAME_MAX = 40
QTY_MAX = 99999

OWNED_ARRAYS = ("Suits", "LongGuns", "Pistols", "Melee", "Sentinels", "SentinelWeapons",
                "KubrowPets", "MoaPets", "OperatorAmps")
IMPORT_SOURCE = "https://github.com/SpaceNinjaServer/SpaceNinjaServer (src/types/inventoryTypes/inventoryTypes.ts)"


def find_craft(crafts, name):
    for craft in crafts:
        if craft["n"].lower() == str(name or "").strip().lower():
            return craft
    return None


def add_craft(crafts, name, kind):
    name = clean(name, CRAFT_NAME_MAX)
    if not name:
        return False, "Give the item a name."
    if kind not in CRAFT_KINDS:
        return False, "Pick weapon, warframe or companion."
    if find_craft(crafts, name):
        return False, "That item is already in the list."
    if len(crafts) >= CRAFT_MAX:
        return False, f"You can track up to {CRAFT_MAX} items."
    crafts.append({"n": name, "k": kind, "needs": [], "own": False, "imp": False})
    return True, f"Added {name}."


def remove_craft(crafts, name):
    craft = find_craft(crafts, name)
    if craft is None:
        return False
    crafts.remove(craft)
    return True


def resource_index(resource_names):
    """normalised name -> the tracker's own resource name."""
    return {norm(n): n for n in resource_names}


def add_need(crafts, item, component, qty, resource_names=()):
    craft = find_craft(crafts, item)
    if craft is None:
        return False, "Add the item first."
    component = clean(component, NEED_NAME_MAX)
    if not component:
        return False, "Give the component a name."
    if not is_int(qty) or not 1 <= qty <= QTY_MAX:
        return False, f"Quantity must be a whole number from 1 to {QTY_MAX}."
    linked = resource_index(resource_names).get(norm(component))
    if linked:
        component = linked
    if any(n["n"].lower() == component.lower() for n in craft["needs"]):
        return False, "That component is already listed for this item."
    if len(craft["needs"]) >= NEED_MAX:
        return False, f"An item can list up to {NEED_MAX} components."
    craft["needs"].append({"n": component, "q": qty, "h": 0})
    return True, f"Added {component} x{qty} to {craft['n']}."


def set_have(craft, index, have):
    if not 0 <= index < len(craft["needs"]) or not is_int(have) or not 0 <= have <= QTY_MAX:
        return False
    craft["needs"][index]["h"] = have
    return True


def set_owned(craft, flag):
    """Your own tick. Unticking also clears an import mark: your tick wins."""
    craft["own"] = bool(flag)
    if not flag:
        craft["imp"] = False


def craft_progress(craft, inventory, resource_names):
    """One item's status: each need with its have/short (linked resources read the live
    inventory), whether it is owned (ticked or found by an import), whether every
    component is on hand, and a completion percentage."""
    index = resource_index(resource_names)
    needs = []
    for need in craft["needs"]:
        linked = index.get(norm(need["n"]))
        have = pooled(inventory.get(linked)) if linked else need["h"]
        needs.append({"n": need["n"], "q": need["q"], "have": have, "short": max(0, need["q"] - have),
                      "linked": bool(linked)})
    owned = craft["own"] or craft["imp"]
    total = sum(n["q"] for n in needs)
    covered = sum(min(n["have"], n["q"]) for n in needs)
    ready = bool(needs) and all(n["short"] == 0 for n in needs)
    if owned:
        pct = 100
    else:
        pct = round(covered / total * 100) if total else 0
    return {"craft": craft, "needs": needs, "owned": owned, "ready": ready and not owned, "pct": pct,
            "source": "import" if craft["imp"] and not craft["own"] else ("ticked" if craft["own"] else "")}


def owned_tails(data):
    """Normalised last path segments of every ItemType in the owned-equipment arrays of an
    inventory response, plus how many entries were seen. Tolerates missing/odd data."""
    tails = set()
    seen = 0
    if not isinstance(data, dict):
        return tails, seen
    for array in OWNED_ARRAYS:
        items = data.get(array)
        for entry in items if isinstance(items, list) else []:
            if not isinstance(entry, dict):
                continue
            item_type = entry.get("ItemType") or entry.get("itemType") or ""
            if not isinstance(item_type, str) or not item_type:
                continue
            seen += 1
            tails.add(norm(item_type.rstrip("/").rsplit("/", 1)[-1]))
    return tails, seen


def mark_imported(crafts, tails):
    """Sets each craft's import mark from the tails; returns the names that just became owned."""
    newly = []
    for craft in crafts:
        was = craft["imp"]
        craft["imp"] = norm(craft["n"]) in tails
        if craft["imp"] and not was and not craft["own"]:
            newly.append(craft["n"])
    return newly


# --- pets ----------------------------------------------------------------

PET_KINDS = ("kubrow", "kavat")
PET_MAX = 30
PET_NAME_MAX = 30
PET_TEXT_MAX = 200
IMPRINT_MAX = 9
KUBROW_IMPRINT_LIMIT = 2
IMPRINT_HOURS = 1.5

PET_FACTS = (
    ("Incubation takes 48 hours, or 24 hours with an Incubator Upgrade Segment, and can be rushed for 15 Platinum.",
     "https://wiki.warframe.com/w/Kubrow"),
    ("Only 2 imprints can be made per Kubrow; an imprint takes 1.5 hours and cannot be cancelled once started.",
     "https://wiki.warframe.com/w/Kubrow"),
    ("A Genetic Code Template makes the imprinted traits much more likely in the result, but not guaranteed.",
     "https://wiki.warframe.com/w/Kubrow"),
    ("Each Kavat breeding attempt needs 10 Kavat Genetic Codes and an Incubator Power Core; the Wiki names no imprint limit for Kavats.",
     "https://wiki.warframe.com/w/Kavat"),
)
PET_FACTS_DATE = "2026-09-27"


def find_pet(pets, name):
    for pet in pets:
        if pet["n"].lower() == str(name or "").strip().lower():
            return pet
    return None


def add_pet(pets, name, kind, imprints, mods, note):
    name = clean(name, PET_NAME_MAX)
    if not name:
        return False, "Give the pet a name."
    if kind not in PET_KINDS:
        return False, "Pick kubrow or kavat."
    if not is_int(imprints) or not 0 <= imprints <= IMPRINT_MAX:
        return False, f"Imprints made must be 0 to {IMPRINT_MAX}."
    if kind == "kubrow" and imprints > KUBROW_IMPRINT_LIMIT:
        return False, f"The Wiki says only {KUBROW_IMPRINT_LIMIT} imprints can be made per Kubrow."
    if find_pet(pets, name):
        return False, "You already have a pet with that name."
    if len(pets) >= PET_MAX:
        return False, f"You can log up to {PET_MAX} pets."
    pets.append({"n": name, "k": kind, "i": imprints, "m": clean(mods, PET_TEXT_MAX), "t": clean(note, PET_TEXT_MAX)})
    return True, f"Logged {name}."


def remove_pet(pets, name):
    pet = find_pet(pets, name)
    if pet is None:
        return False
    pets.remove(pet)
    return True


def bump_imprint(pets, name):
    """Records one more imprint made on this pet, within the stated Kubrow limit."""
    pet = find_pet(pets, name)
    if pet is None:
        return False, "Unknown pet."
    if pet["k"] == "kubrow" and pet["i"] >= KUBROW_IMPRINT_LIMIT:
        return False, f"{pet['n']} already has the {KUBROW_IMPRINT_LIMIT} imprints the Wiki allows."
    if pet["i"] >= IMPRINT_MAX:
        return False, f"That is the maximum count the log keeps ({IMPRINT_MAX})."
    pet["i"] += 1
    return True, f"{pet['n']} now has {pet['i']} imprint(s) logged."


def pet_line(pet):
    text = f"{pet['n']} ({pet['k']}): {pet['i']} imprint(s) logged"
    if pet["k"] == "kubrow":
        text += f", {max(0, KUBROW_IMPRINT_LIMIT - pet['i'])} left"
    if pet["m"]:
        text += f". Mods: {pet['m']}"
    if pet["t"]:
        text += f". Note: {pet['t']}"
    return text


# --- save/load -----------------------------------------------------------

def export_crafts(crafts):
    return [{"n": c["n"], "k": c["k"], "own": c["own"], "imp": c["imp"],
             "needs": [dict(n) for n in c["needs"]]} for c in crafts]


def load_crafts(value):
    crafts = []
    for entry in dict_entries(value)[:CRAFT_MAX]:
        name, kind = entry.get("n"), entry.get("k")
        if not (isinstance(name, str) and name.strip() and str_in(kind, CRAFT_KINDS)
                and isinstance(entry.get("own"), bool) and isinstance(entry.get("imp"), bool)):
            continue
        name = name.strip()[:CRAFT_NAME_MAX]
        if find_craft(crafts, name):
            continue
        needs = []
        for need in dict_entries(entry.get("needs"))[:NEED_MAX]:
            comp, qty, have = need.get("n"), need.get("q"), need.get("h")
            if (isinstance(comp, str) and comp.strip() and is_int(qty) and 1 <= qty <= QTY_MAX
                    and is_int(have) and 0 <= have <= QTY_MAX
                    and not find_ci([n["n"] for n in needs], comp)):
                needs.append({"n": comp.strip()[:NEED_NAME_MAX], "q": qty, "h": have})
        crafts.append({"n": name, "k": kind, "needs": needs, "own": entry["own"], "imp": entry["imp"]})
    return crafts


def export_pets(pets):
    return [dict(p) for p in pets]


def load_pets(value):
    pets = []
    for entry in dict_entries(value)[:PET_MAX]:
        name, kind, imprints = entry.get("n"), entry.get("k"), entry.get("i")
        mods, note = entry.get("m"), entry.get("t")
        if not (isinstance(name, str) and name.strip() and str_in(kind, PET_KINDS) and is_int(imprints)
                and 0 <= imprints <= IMPRINT_MAX and isinstance(mods, str) and isinstance(note, str)):
            continue
        if kind == "kubrow" and imprints > KUBROW_IMPRINT_LIMIT:
            continue
        name = name.strip()[:PET_NAME_MAX]
        if not find_pet(pets, name):
            pets.append({"n": name, "k": kind, "i": imprints, "m": mods.strip()[:PET_TEXT_MAX],
                         "t": note.strip()[:PET_TEXT_MAX]})
    return pets
