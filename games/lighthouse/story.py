"""Lighthouse -- the story layer's engine: who is met, which letter arrives, what a gift does.

Everything here is optional. A Quiet run (`keep.quiet`) skips all of it, and nothing in the sim reads it except two
small, story-only extras (a gift's food, and the lens cloth's one step of reach). Letters arrive in the morning, at
most one a night, after the sailor's boat has got safely by often enough and the keeper's name is known enough.
"""

import lore
import mysteries
import unease
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


def eerie(keep):
    """The per-device 'Eerie details' choice, handed in by game.py on each request; true when unset."""
    return getattr(keep, "_eerie", True)


def beat_nights(keep):
    return {b[0]: b[1] for b in keep.story["beats"]}


def _gate_ok(keep, letter):
    gate = letter["gate"]
    if gate.get("beat") and not (gate["beat"] in beat_nights(keep) and beat_nights(keep)[gate["beat"]] < keep.night):
        return False
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
    out = {"letters": [], "met": [], "beats": [], "unrecorded": []}
    if not on(keep):
        return out
    resolved = emit_morning(keep, out)
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
    seen = beat_nights(keep)
    out["unrecorded"] = [b["board"] for _m, b in unease.beats_on(keep.seed, keep.night) if b.get("board") and seen.get(b["id"]) == keep.night]
    stats = keep.night_stats
    keep.story["unease"] = unease.meter_after_night(keep.story["unease"], stats["worst_cond"], stats["fog_ticks"], bool(out["letters"]), resolved)
    keep.story["tonight"] = ""
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
        "notebook": notebook(keep), "odd": odd_visuals(keep), "eerie": eerie(keep), "room_odd": room_odd(keep),
    }


# ---- the odd and the kind: mystery beats and small oddities ----------------------------------------------------
def _fmt(keep, text):
    stats = keep.night_stats
    names = [sh["name"] for sh in __import__("sim").tonight_ships(keep) if sh["kind"] != "mail"][:3]
    board = " and ".join(names) if names else "no one"
    try:
        return text.format(passed=stats["passed"], hours=round(stats["lamp_ticks"] / 6.0, 1), board=board)
    except (KeyError, IndexError, ValueError):
        return text


def _record(keep, mid, beat):
    keep.story["beats"].append([beat["id"], keep.night])
    if mid not in keep.meta["story"]["mysteries"]:
        keep.meta["story"]["mysteries"].append(mid)


def _fire(keep, mid, beat, out=None):
    """Show one mystery beat. Odd and moment beats are skipped, silently, when Eerie details is off. Returns True when
    the beat was a resolve."""
    if beat["id"] in beat_nights(keep):
        return False
    odd = beat["kind"] in unease.ODD_KINDS
    if odd and not eerie(keep):
        return False
    text = _fmt(keep, beat["text"])
    _record(keep, mid, beat)
    log_kind = "hand" if beat.get("font") else "odd" if odd else "story"
    keep.add_log(log_kind, text)
    if out is not None:
        out["beats"].append({"kind": beat["kind"], "text": text})
    if beat.get("gift") and beat["gift"] not in keep.story["gifts"]:
        take_gift(keep, beat["gift"])
    if beat["kind"] == "resolve":
        keep.story["unease"] = max(0, keep.story["unease"] - 40)
        who = mysteries.MYSTERIES[mid].get("who")
        if who:
            meet(keep, who)
        return True
    return False


def begin_night(keep):
    """Decide tonight's small oddity (if any) once, so a pause or a save cannot change the answer."""
    keep.story["tonight"] = ""
    if not on(keep) or not eerie(keep):
        return
    odd, kind = unease.odd_nights(keep.seed)
    odd = set(odd) | set(keep.story["trifles"].values())
    pick = unease.trifle_tonight(keep.seed, keep.night, keep.story["unease"], keep.story["trifles"], odd, kind)
    if pick:
        keep.story["tonight"] = pick


def emit_tick(keep, tick):
    """Called by the sim at the end of each tick: the beats and the oddity that show at exactly this tick."""
    if not on(keep):
        return
    for mid, beat in unease.beats_on(keep.seed, keep.night):
        if beat["at"] != "morning" and unease.beat_tick(keep.night, beat["at"]) == tick:
            _fire(keep, mid, beat)
    tid = keep.story.get("tonight")
    if tid and tid not in keep.story["trifles"]:
        spec = mysteries.TRIFLES[tid]
        if spec["at"] != "morning" and unease.beat_tick(keep.night, spec["at"]) == tick:
            _show_trifle(keep, tid, None)


def _show_trifle(keep, tid, out):
    keep.story["trifles"][tid] = keep.night
    text = mysteries.TRIFLES[tid]["odd"]
    keep.add_log("odd", text)
    if out is not None:
        out["beats"].append({"kind": "trifle", "text": text})


def emit_morning(keep, out):
    """The beats and oddities that belong to the morning, and the explanations that are due. Returns whether a
    mystery was solved."""
    resolved = False
    for mid, beat in unease.beats_on(keep.seed, keep.night):
        if beat["at"] == "morning":
            resolved = _fire(keep, mid, beat, out) or resolved
    tid = keep.story.get("tonight")
    if tid and tid not in keep.story["trifles"] and mysteries.TRIFLES[tid]["at"] == "morning":
        _show_trifle(keep, tid, out)
    for tid, night in list(keep.story["trifles"].items()):
        if tid in keep.story["explained"]:
            continue
        if keep.night >= night + mysteries.TRIFLES[tid]["delay"]:
            keep.story["explained"].append(tid)
            text = mysteries.TRIFLES[tid]["resolve"]
            out["beats"].append({"kind": "explain", "text": text})
            keep.add_log("story", text)
            keep.story["unease"] = max(0, keep.story["unease"] - 15)
            if tid not in keep.meta["story"]["oddities"]:
                keep.meta["story"]["oddities"].append(tid)
    return resolved


def odd_visuals(keep):
    """What the scene should draw tonight for the odd beats already shown: the latest light of each mystery."""
    if not on(keep) or keep.phase != "night":
        return []
    seen = beat_nights(keep)
    out = []
    for mid, beat in unease.beats_on(keep.seed, keep.night):
        if beat["id"] in seen and beat.get("visual"):
            out.append(dict(beat["visual"], mystery=mid, id=beat["id"]))
    return out


def notebook(keep):
    seen = beat_nights(keep)
    rows = []
    for mid in unease.mystery_order():
        m = mysteries.MYSTERIES[mid]
        shown = [b for b in m["beats"] if b["id"] in seen]
        solved = any(b["kind"] == "resolve" for b in shown)
        rows.append({
            "id": mid, "begun": bool(shown), "solved": solved,
            "title": m["title"] if shown else "A mystery you have not begun",
            "summary": m["summary"] if solved else "",
            "entries": [{"kind": b["kind"], "night": seen[b["id"]], "text": _plain(b["text"]), "technique": b["technique"]} for b in shown],
        })
    trifles = []
    for tid in mysteries.TRIFLE_ORDER:
        if tid in keep.story["trifles"]:
            t = mysteries.TRIFLES[tid]
            done = tid in keep.story["explained"]
            trifles.append({"id": tid, "night": keep.story["trifles"][tid], "odd": t["odd"], "explained": done, "resolve": t["resolve"] if done else ""})
    return {"mysteries": rows, "trifles": trifles, "mysteries_total": len(mysteries.MYSTERIES), "trifles_total": len(mysteries.TRIFLES)}


def _plain(text):
    return text.replace("{passed}", "some").replace("{hours}", "some").replace("{level}", "the")


def board_extras(keep, night):
    """Ships the harbour board lists that never come (the 'ghost entries'): only with the story and Eerie details on."""
    if not on(keep) or not eerie(keep):
        return []
    return [b["board"] for _m, b in unease.beats_on(keep.seed, night) if b.get("board")]


def room_odd(keep):
    seen = beat_nights(keep)
    chair = 0
    cup = False
    for m in mysteries.MYSTERIES.values():
        for b in m["beats"]:
            if b["id"] in seen and b.get("room"):
                chair = max(chair, b["room"].get("chair", 0))
                cup = cup or bool(b["room"].get("cup"))
    return {"chair": chair, "cup": cup and "second_cup" not in keep.story["gifts"]}
