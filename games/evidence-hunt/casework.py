"""Evidence Hunt -- the rules of one case. A `Case` is compiled from an authored dict (casekit.py) and is a pure function: the
same case and the same list of actions always give the same state. There is no clock and no random source here.

State is a tuple: (kit, room, read, trips, wrong, solved, covered, looked, returned, entered, notes)
  kit      bitmask of the equipment in the bag (bit e = evidence e)
  room     the room the investigator stands in, or -1 at the van
  read     1 once a reading has been taken on this trip (the bag is then locked until the van)
  trips    1 or more
  wrong    wrong accusations so far
  solved   1 once the spirit is named
  covered  1 if the sheet is covered ("from memory")
  looked   1 once the keepsake has been looked at
  returned 1 once the keepsake is returned after the case is solved
  entered  bitmask of rooms entered
  notes    tuple, six cells per room (0 unknown, 1 clear, 2 positive, 3 doubtful)

Actions (tuples, or colon-joined tokens in a save): ("pack", e), ("van",), ("go", r), ("use", e), ("look",), ("accuse", k, k2),
("cover",), ("return",)."""

import houses
import lexicon as lx

KIT, ROOM, READ, TRIPS, WRONG, SOLVED, COVERED, LOOKED, RETURNED, ENTERED, NOTES = range(11)
UNKNOWN, CLEAR, POSITIVE, DOUBTFUL = 0, 1, 2, 3
NOTE_WORD = {UNKNOWN: "not read", CLEAR: "clear", POSITIVE: "positive", DOUBTFUL: "doubtful"}
MAX_ROOMS = 16


def popcount(x):
    return bin(x).count("1")


def grade_of(cost):
    return 3 if cost == 0 else (2 if cost <= 2 else 1)


class Case:
    def __init__(self, data):
        self.data = data
        self.id = data["id"]
        self.title = data["title"]
        self.intro = data.get("intro", "")
        self.client = data.get("client", "")
        self.ending = data.get("ending", "")
        self.layout = data["layout"]
        self.rooms = houses.rooms_of(self.layout)
        for rid, name in (data.get("names") or {}).items():
            self.rooms[self.index(rid)]["name"] = name
        self.kit_size = data["kit"]
        self.pool = tuple(sorted(data["pool"], key=lx.KIND_INDEX.get))
        self.truth = tuple(data["truth"])
        self.slots = tuple(tuple(self.index(r) for r in slot) for slot in data["restless"])
        self.n = len(self.slots)
        self.room_slot = {r: s for s, slot in enumerate(self.slots) for r in slot}
        self.feature = {self.index(r): lx.FT_INDEX[f] for r, f in (data.get("features") or {}).items()}
        ks = data.get("keepsake")
        self.keep_room, self.keep_id, self.keep_bh = (self.index(ks[0]), ks[1], ks[2]) if ks else (-1, "", "")
        self.accounts = tuple((b, self.index(r) if r else None) for b, r in data.get("accounts", ()))
        self.chapter = data.get("chapter", -1)
        self.practice = bool(data.get("practice"))
        self.code = data.get("code", "")

    # ---- the house ---------------------------------------------------------------------------------------------------
    def index(self, rid):
        for i, r in enumerate(self.rooms):
            if r["id"] == rid:
                return i
        raise KeyError(rid)

    def reading(self, room, e):
        """What the equipment shows in a room: CLEAR, POSITIVE or DOUBTFUL. Pure, from the case alone."""
        if room == self.keep_room:
            return DOUBTFUL
        f = self.feature.get(room)
        if f is not None and lx.FT_FOOLS[lx.FT_IDS[f]] == e:
            return DOUBTFUL
        slot = self.room_slot.get(room)
        if slot is None:
            return CLEAR
        return POSITIVE if e in lx.KIND_EVIDENCE[self.truth[slot]] else CLEAR

    def _why(self, room):
        """Why a reading in this room cannot be trusted, as a clause."""
        if room == self.keep_room:
            return "the %s in this room swamps every reading here" % lx.KS_NAME[self.keep_id].lower()
        text = lx.FEATURES[self.feature[room]][3].rstrip(".")
        return text[0].lower() + text[1:]

    def room_text(self, room):
        r = self.rooms[room]
        bits = [r["text"], "The air here is restless." if room in self.room_slot else "This room is still."]
        f = self.feature.get(room)
        if f is not None:
            bits.append(lx.FEATURES[f][3])
        if room == self.keep_room:
            bits.append("%s sits here. Look at it." % lx.KS_WHAT[self.keep_id].capitalize())
        return " ".join(bits)

    # ---- state -------------------------------------------------------------------------------------------------------
    def new_state(self):
        return (0, -1, 0, 1, 0, 0, 0, 0, 0, 0, (UNKNOWN,) * (6 * len(self.rooms)))

    def done(self, st):
        return bool(st[SOLVED])

    def total_cost(self, st):
        return st[WRONG] + st[TRIPS] - 1

    def all_entered(self, st):
        return st[ENTERED] == (1 << len(self.rooms)) - 1

    def kit_list(self, st):
        return [e for e in range(6) if st[KIT] >> e & 1]

    def _replace(self, st, **kw):
        names = ("kit", "room", "read", "trips", "wrong", "solved", "covered", "looked", "returned", "entered", "notes")
        vals = list(st)
        for k, v in kw.items():
            vals[names.index(k)] = v
        return tuple(vals)

    def apply(self, st, act):
        """(new state, info) or (None, info) when the action is refused. info = {"msg", "kind"}."""
        kind = act[0]
        if st[SOLVED] and kind not in ("return", "cover"):
            return None, {"msg": "This case is solved. Restore it to play it again, or go on to the next.", "kind": "refused"}
        if kind == "pack":
            e = act[1]
            if not 0 <= e < 6:
                return None, {"msg": "That is not equipment you own.", "kind": "refused"}
            if st[READ]:
                return None, {"msg": "The bag is locked once a reading is taken. Go back to the van for a different bag (a second trip costs 1).", "kind": "refused"}
            if st[KIT] >> e & 1:
                return self._replace(st, kit=st[KIT] & ~(1 << e)), {"msg": "You take the %s out of the bag." % lx.GEAR_NAME[e], "kind": "pack"}
            if popcount(st[KIT]) >= self.kit_size:
                return None, {"msg": "The bag holds %d pieces. Take one out first." % self.kit_size, "kind": "refused"}
            return self._replace(st, kit=st[KIT] | (1 << e)), {"msg": "You pack the %s." % lx.GEAR_NAME[e], "kind": "pack"}
        if kind == "van":
            if st[READ]:
                return self._replace(st, kit=0, room=-1, read=0, trips=st[TRIPS] + 1), \
                    {"msg": "Back to the van for a different bag. That is trip %d (cost 1). Your notebook keeps every reading." % (st[TRIPS] + 1), "kind": "van"}
            return self._replace(st, kit=0, room=-1), {"msg": "You are at the van with an empty bag. Nothing has been read yet, so this costs nothing.", "kind": "van"}
        if kind == "go":
            r = act[1]
            if not 0 <= r < len(self.rooms):
                return None, {"msg": "There is no such room.", "kind": "refused"}
            first = not st[ENTERED] >> r & 1
            msg = "%s. %s" % (self.rooms[r]["name"], self.room_text(r))
            return self._replace(st, room=r, entered=st[ENTERED] | (1 << r)), {"msg": msg, "kind": "enter", "first": first, "room": r}
        if kind == "use":
            e = act[1]
            if not 0 <= e < 6:
                return None, {"msg": "That is not equipment you own.", "kind": "refused"}
            if st[ROOM] < 0:
                return None, {"msg": "Walk into a room first. Readings are taken in a room.", "kind": "refused"}
            if not st[KIT] >> e & 1:
                return None, {"msg": "The %s is not in the bag." % lx.GEAR_NAME[e], "kind": "refused"}
            cell = st[ROOM] * 6 + e
            if st[NOTES][cell] != UNKNOWN:
                return None, {"msg": "The %s is already noted for this room." % lx.GEAR_NAME[e], "kind": "refused"}
            res = self.reading(st[ROOM], e)
            notes = st[NOTES][:cell] + (res,) + st[NOTES][cell + 1:]
            room = st[ROOM]
            if res == DOUBTFUL:
                msg = "%s: %s But %s, so this reading is doubtful and tells you nothing about the spirit." % (lx.GEAR_NAME[e], lx.POSITIVE[e], self._why(room))
            elif res == POSITIVE:
                msg = "%s: %s" % (lx.GEAR_NAME[e], lx.POSITIVE[e])
            else:
                msg = "%s: %s" % (lx.GEAR_NAME[e], lx.CLEAR[e])
                if room not in self.room_slot:
                    msg += " (This room is still, so a clear reading here tells you nothing.)"
            return self._replace(st, read=1, notes=notes), {"msg": msg, "kind": "read", "result": res, "e": e, "room": room}
        if kind == "look":
            if st[ROOM] != self.keep_room or self.keep_room < 0:
                return None, {"msg": "There is nothing here to look at closely.", "kind": "refused"}
            if st[LOOKED]:
                return None, {"msg": "You have looked at it already. Your notebook has the line.", "kind": "refused"}
            msg = "You look at %s. %s" % (lx.KS_WHAT[self.keep_id], lx.BH_KEEPSAKE[self.keep_bh])
            return self._replace(st, looked=1), {"msg": msg, "kind": "look"}
        if kind == "cover":
            now = "The sheet is uncovered." if st[COVERED] else "The sheet is covered: kinds your guide already holds are hidden."
            return self._replace(st, covered=1 - st[COVERED]), {"msg": now, "kind": "cover"}
        if kind == "return":
            if not st[SOLVED] or self.keep_room < 0:
                return None, {"msg": "There is nothing to return.", "kind": "refused"}
            if st[RETURNED]:
                return None, {"msg": "It is already home.", "kind": "refused"}
            return self._replace(st, returned=1), {"msg": lx.KS_RETURN[self.keep_id], "kind": "return"}
        if kind == "accuse":
            names = []
            for k in act[1:]:
                if not 0 <= k < len(lx.KIND_IDS) or lx.KIND_IDS[k] not in self.pool:
                    return None, {"msg": "That kind is not on the sheet for this house.", "kind": "refused"}
                names.append(lx.KIND_IDS[k])
            if len(names) != self.n or len(set(names)) != self.n:
                return None, {"msg": "Name %s." % ("one spirit" if self.n == 1 else "two different spirits"), "kind": "refused"}
            if sorted(names) == sorted(self.truth):
                return self._replace(st, solved=1), {"msg": "Yes. " + self.ending, "kind": "right"}
            if self.n == 2 and set(names) & set(self.truth):
                return self._replace(st, wrong=st[WRONG] + 1), {"msg": "Half of that is right, and half is not. Cost 1. Look again, or try another pair.", "kind": "wrong"}
            return self._replace(st, wrong=st[WRONG] + 1), {"msg": "Not quite. The house stays quiet and nothing is harmed. Cost 1. Your notebook is as you left it: look again, or try another name.", "kind": "wrong"}
        return None, {"msg": "That is not something the investigator does.", "kind": "refused"}

    # ---- what the notebook lets you say ------------------------------------------------------------------------------
    def testimony(self, st, slot):
        """The behaviours known for a slot: the client's account, and the keepsake's line once looked at."""
        out = []
        rooms = self.slots[slot]
        for b, r in self.accounts:
            if r is None or r in rooms:
                out.append(b)
        if st[LOOKED] and self.keep_room in rooms:
            out.append(self.keep_bh)
        return out

    def candidates(self, st, slot):
        """The kinds on the sheet that still fit this slot, from what the player holds: the testimony so far, how many restless
        rooms have turned up, and every clean reading in the notebook."""
        rooms = self.slots[slot]
        found = [r for r in rooms if st[ENTERED] >> r & 1]
        all_in = self.all_entered(st)
        said = self.testimony(st, slot)
        out = []
        for k in self.pool:
            bh = lx.KIND_BEHAVIOURS[k]
            if any(b not in bh for b in said):
                continue
            if "fond" in bh and len(found) >= 2:
                continue
            if "roamer" in bh and (self.n == 2 or (all_in and len(found) == 1)):
                continue
            ev = lx.KIND_EVIDENCE[k]
            ok = True
            for r in found:
                for e in range(6):
                    v = st[NOTES][r * 6 + e]
                    if (v == POSITIVE and e not in ev) or (v == CLEAR and e in ev):
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                out.append(k)
        return out

    def usable(self, slot):
        """Evidence that some restless room of the slot can read cleanly."""
        return {e for e in range(6) for r in self.slots[slot] if self.reading(r, e) != DOUBTFUL}


def to_token(act):
    return ":".join(str(x) for x in act)


def from_token(token):
    """Parse a token back into an action tuple, or None if it is not one."""
    if not isinstance(token, str):
        return None
    parts = token.split(":")
    sizes = {"pack": 2, "van": 1, "go": 2, "use": 2, "look": 1, "cover": 1, "return": 1}
    name = parts[0]
    if name == "accuse":
        ok = len(parts) in (2, 3)
    else:
        ok = name in sizes and len(parts) == sizes[name]
    if not ok:
        return None
    try:
        nums = [int(x) for x in parts[1:]]
    except ValueError:
        return None
    if any(n < 0 or n > 99 for n in nums):
        return None
    return (name,) + tuple(nums)


def replay(case, tokens):
    """Run a list of tokens from a fresh state. Returns (state, infos), or (None, None) if any action is refused."""
    st = case.new_state()
    infos = []
    for token in tokens:
        act = from_token(token)
        if act is None:
            return None, None
        st2, info = case.apply(st, act)
        if st2 is None:
            return None, None
        st = st2
        infos.append(info)
    return st, infos
