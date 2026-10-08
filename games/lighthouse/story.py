"""Lighthouse -- the story layer's engine: who is met, which letter arrives, what a gift does.

Everything here is optional. A Quiet run (`keep.quiet`) skips all of it, and nothing in the sim reads it except two
small, story-only extras (a gift's food, and the lens cloth's one step of reach). Letters arrive in the morning, at
most one a night, after the sailor's boat has got safely by often enough and the keeper's name is known enough.
"""

import lore
from data import SUPPLY_CAP


def on(keep):
    return not keep.quiet


def sailor_name(sid):
    return lore.SAILORS[sid]["name"]


def label_ship(keep, ship, text):
    """The log's name for a ship: with the sailor's name when the story is on and someone known is aboard."""
    who = ship.get("who")
    if on(keep) and who in lore.SAILORS:
        return "%s (%s)" % (text, sailor_name(who))
    return text


def delivered_ids(keep):
    return [i["id"] for i in keep.story["inbox"]]


def lens_cloth_bonus(keep):
    return 1 if on(keep) and keep.story["buffs"].get("lens_cloth", 0) > 0 else 0


def _gate_ok(keep, letter):
    gate = letter["gate"]
    sid = letter["from"]
    if gate.get("passes") is not None and keep.story["met"].get(sid, 0) < gate["passes"]:
        return False
    if keep.reputation < gate.get("rep", 0):
        return False
    if keep.night < gate.get("night", 0):
        return False
    if gate.get("after") and gate["after"] not in delivered_ids(keep):
        return False
    return True


def meet(keep, sid):
    st = keep.story
    st["met"].setdefault(sid, 0)
    if sid not in keep.meta["story"]["met"]:
        keep.meta["story"]["met"].append(sid)


def after_night(keep, ships):
    """Called once at dawn, after the ships are settled. Returns what the morning report should mention."""
    out = {"letters": [], "met": []}
    if not on(keep):
        return out
    st = keep.story
    for ship in ships:
        who = ship.get("who")
        rec = keep.progress.get(ship["id"], {})
        if who and rec.get("state") == "passed":
            if who not in st["met"]:
                out["met"].append(who)
            meet(keep, who)
            st["met"][who] += 1
    if st["buffs"].get("lens_cloth", 0) > 0:
        st["buffs"]["lens_cloth"] -= 1
    have = set(delivered_ids(keep))
    for lid in lore.LETTER_ORDER:
        letter = lore.LETTERS[lid]
        if lid in have or not _gate_ok(keep, letter):
            continue
        if lore.SAILORS[letter["from"]]["kind"] == "" and letter["from"] not in st["met"]:
            out["met"].append(letter["from"])
        meet(keep, letter["from"])
        st["inbox"].append({"id": lid, "night": keep.night})
        out["letters"].append(lid)
        break
    return out


def read_letter(keep, lid):
    """Read a letter that has come. Takes any gift that was in it. Returns (ok, message)."""
    st = keep.story
    if not on(keep):
        return False, "There is no post tonight."
    if lid not in delivered_ids(keep):
        return False, "There is no such letter."
    letter = lore.LETTERS[lid]
    if lid in st["read"]:
        return False, "You have read that one."
    st["read"].append(lid)
    if lid not in keep.meta["story"]["letters"]:
        keep.meta["story"]["letters"].append(lid)
    message = "You read the letter from %s." % sailor_name(letter["from"])
    gift = letter.get("gift")
    if gift and gift not in st["gifts"]:
        message += " " + take_gift(keep, gift)
    return True, message


def take_gift(keep, gid):
    g = lore.GIFTS[gid]
    st = keep.story
    st["gifts"].append(gid)
    if gid not in keep.meta["story"]["gifts"]:
        keep.meta["story"]["gifts"].append(gid)
    text = "%s is added to the room." % g["name"]
    effect = g.get("effect", {})
    if "food" in effect:
        keep.supplies["food"] = min(SUPPLY_CAP, keep.supplies["food"] + effect["food"])
        text += " (+%d food)" % effect["food"]
    if "lens_cloth" in effect:
        st["buffs"]["lens_cloth"] = effect["lens_cloth"]
        text += " The beam will reach one step further for %d nights." % effect["lens_cloth"]
    return text


def reply(keep, lid, rid):
    st = keep.story
    if not on(keep) or lid not in st["read"]:
        return False, "Read the letter first."
    letter = lore.LETTERS[lid]
    options = {r[0]: r for r in letter.get("replies", ())}
    if rid not in options:
        return False, "That is not one of the replies."
    if lid in st["choices"]:
        return False, "You have already answered that one."
    st["choices"][lid] = [rid, keep.night]
    return True, "Your reply goes out with the next boat."


def view(keep):
    st = keep.story
    shown = []
    for item in reversed(st["inbox"]):
        letter = lore.LETTERS[item["id"]]
        entry = {
            "id": item["id"], "from": letter["from"], "from_name": sailor_name(letter["from"]), "subject": letter["subject"],
            "night": item["night"], "read": item["id"] in st["read"], "text": letter["text"] if item["id"] in st["read"] else "",
            "replies": [{"id": r[0], "label": r[1]} for r in letter.get("replies", ())] if item["id"] in st["read"] else [],
            "gift": None, "reply": None, "answer": None,
        }
        if letter.get("gift") and entry["read"]:
            g = lore.GIFTS[letter["gift"]]
            entry["gift"] = {"id": letter["gift"], "name": g["name"]}
        choice = st["choices"].get(item["id"])
        if choice:
            opt = next(r for r in letter["replies"] if r[0] == choice[0])
            entry["reply"] = opt[1]
            entry["answer"] = opt[2] if keep.night > choice[1] else None
        shown.append(entry)
    sailors = []
    for sid in lore.SAILOR_ORDER:
        s = lore.SAILORS[sid]
        met = sid in st["met"] or sid in keep.meta["story"]["met"]
        letters = [lid for lid, l in lore.LETTERS.items() if l["from"] == sid]
        got = [lid for lid in letters if lid in delivered_ids(keep)]
        sailors.append({"id": sid, "met": met, "name": s["name"] if met else "Someone you have not met", "role": s["role"] if met else "",
                        "blurb": s["blurb"] if met else "", "passes": st["met"].get(sid, 0), "letters": len(letters),
                        "letters_got": len(got) if met else 0, "ashore": s["kind"] == ""})
    gifts = [{"id": gid, "have": gid in st["gifts"], "ever": gid in keep.meta["story"]["gifts"],
              "name": lore.GIFTS[gid]["name"] if gid in keep.meta["story"]["gifts"] or gid in st["gifts"] else "A gift you have not found",
              "text": lore.GIFTS[gid]["text"] if gid in st["gifts"] else "", "slot": lore.GIFTS[gid]["slot"]} for gid in lore.GIFT_ORDER]
    return {
        "on": on(keep), "inbox": shown, "unread": sum(1 for i in st["inbox"] if i["id"] not in st["read"]),
        "sailors": sailors, "gifts": gifts, "room": [g for g in st["gifts"]],
        "counts": {"met": len(keep.meta["story"]["met"]), "sailors": len(lore.SAILORS), "letters": len(keep.meta["story"]["letters"]),
                   "letters_total": len(lore.LETTERS), "gifts": len(keep.meta["story"]["gifts"]), "gifts_total": len(lore.GIFTS)},
        "buffs": dict(st["buffs"]), "note": lore.CONTENT_NOTE,
    }
