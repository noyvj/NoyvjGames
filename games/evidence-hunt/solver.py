"""Evidence Hunt -- the fairness checker and the careful plan behind the hints.

A case is FAIR when the investigator can always get a clean finish from the case file alone (the sheet, the client's account,
the rooms and their features): enter every room, look at the keepsake, pick a bag of at most `kit` pieces that tells every
remaining suspect apart in the restless room(s), take those readings and name the spirit. Nothing in that plan depends on
which suspect is the true one, so it works for every suspect and never needs a wrong guess or a second trip.

`analyse` finds every bag that works. `validate` lists everything wrong with an authored case. `next_action` is the careful
plan from any state (it is what the hint ladder shows), or None when a clean finish is gone and Restore is the way back."""

from itertools import combinations

import casework as cw
import lexicon as lx


def _static_slot(case, s):
    st = case.new_state()
    st = st[:cw.LOOKED] + (1,) + st[cw.LOOKED + 1:]
    st = st[:cw.ENTERED] + ((1 << len(case.rooms)) - 1,) + st[cw.ENTERED + 1:]
    return case.candidates(st, s)


def separates(case, kit, s, cands=None):
    """Does reading `kit` (a set of evidence indices) in the slot's restless rooms tell every pair of candidates apart?"""
    cands = _static_slot(case, s) if cands is None else cands
    usable = case.usable(s)
    for a, b in combinations(cands, 2):
        ea, eb = lx.KIND_EVIDENCE[a], lx.KIND_EVIDENCE[b]
        if not any(e in kit and e in usable and ((e in ea) != (e in eb)) for e in range(6)):
            return False
    return True


def all_kits(case, limit=None):
    """Every bag of at most `limit` (default the case's kit size) that separates all slots, smallest first."""
    limit = case.kit_size if limit is None else limit
    out = []
    for size in range(0, limit + 1):
        for kit in combinations(range(6), size):
            if all(separates(case, set(kit), s) for s in range(case.n)):
                out.append(kit)
    return out


def analyse(case):
    cands = [_static_slot(case, s) for s in range(case.n)]
    kits = all_kits(case)
    best = all_kits(case, 6)
    return {"cands": cands, "kits": kits, "min_kit": len(best[0]) if best else None, "unique": bool(best)}


def validate(data):
    """Everything wrong with an authored or generated case, as readable strings (empty when it is sound and fair)."""
    problems = []
    try:
        case = cw.Case(data)
    except (KeyError, ValueError, TypeError) as exc:
        return ["cannot compile: %r" % (exc,)]
    n = case.n
    if n not in (1, 2):
        problems.append("one or two presences only")
    if len(case.truth) != n:
        problems.append("truth must name one kind per presence")
    if any(k not in lx.KIND_INDEX for k in case.pool) or len(set(case.pool)) != len(case.pool):
        problems.append("pool must be distinct known kinds")
    if any(k not in case.pool for k in case.truth):
        problems.append("the truth must be on the sheet")
    if len(set(case.truth)) != len(case.truth):
        problems.append("two presences are two different kinds")
    rooms = [r for slot in case.slots for r in slot]
    if len(set(rooms)) != len(rooms) or not rooms:
        problems.append("restless rooms must be distinct and not empty")
    if n == 2 and any(len(slot) != 1 for slot in case.slots):
        problems.append("with two presences each is in exactly one room")
    for s, slot in enumerate(case.slots):
        if s >= len(case.truth):
            break
        bh = lx.KIND_BEHAVIOURS[case.truth[s]]
        if "fond" in bh and len(slot) != 1:
            problems.append("a fond spirit keeps to exactly one room")
        if "roamer" in bh and len(slot) < 2:
            problems.append("a roaming spirit is restless in two or more rooms")
    for b, r in case.accounts:
        if b not in lx.BH_IDS:
            problems.append("unknown behaviour %r" % (b,))
            continue
        if n == 2 and r is None:
            problems.append("with two presences every account names its room")
        owners = [s for s in range(n) if r is None or r in case.slots[s]]
        if r is not None and not owners:
            problems.append("an account names a room that is not restless")
        if not any(b in lx.KIND_BEHAVIOURS[case.truth[s]] for s in owners if s < len(case.truth)):
            problems.append("an account is not true of the spirit it describes (%s)" % b)
    if case.keep_room >= 0:
        if case.keep_room not in rooms:
            problems.append("the keepsake room must be restless")
        elif case.truth[case.room_slot[case.keep_room]:][:1] and case.keep_bh not in lx.KIND_BEHAVIOURS[case.truth[case.room_slot[case.keep_room]]]:
            problems.append("the keepsake's line must be true of its spirit")
        if case.keep_bh not in lx.BH_KEEPSAKE:
            problems.append("a keepsake can only show tidy, mover, shy or curious")
        if case.keep_id not in lx.KS_IDS:
            problems.append("unknown keepsake")
    if not 1 <= case.kit_size <= 6:
        problems.append("kit size 1 to 6")
    if problems:
        return problems
    info = analyse(case)
    for s, cands in enumerate(info["cands"]):
        if case.truth[s] not in cands:
            problems.append("the true kind is ruled out by the case's own file (%s)" % case.truth[s])
    if not info["unique"]:
        problems.append("no bag of any size tells the suspects apart: not deducible")
    elif info["min_kit"] > case.kit_size:
        problems.append("needs a bag of %d but the kit is %d" % (info["min_kit"], case.kit_size))
    return problems


def next_action(case, st):
    """The careful next step from any state, or None when no clean finish is left (the answer is then to Restore)."""
    if st[cw.SOLVED]:
        return None
    for r in range(len(case.rooms)):
        if not st[cw.ENTERED] >> r & 1:
            return ("go", r)
    if case.keep_room >= 0 and not st[cw.LOOKED]:
        return ("look",) if st[cw.ROOM] == case.keep_room else ("go", case.keep_room)
    cands = [case.candidates(st, s) for s in range(case.n)]
    if all(len(c) == 1 for c in cands):
        return ("accuse",) + tuple(lx.KIND_INDEX[c[0]] for c in cands)
    if any(not c for c in cands):
        return None
    usable = [case.usable(s) for s in range(case.n)]

    def works(kit):
        return all(separates(case, kit, s, cands[s]) for s in range(case.n) if len(cands[s]) > 1)

    have = {e for e in range(6) if st[cw.KIT] >> e & 1}
    if st[cw.READ]:
        if not works(have):
            return None
        want = have
    else:
        want = None
        if works(have):
            want = have
        else:
            for size in range(len(have), case.kit_size + 1):
                for kit in combinations(range(6), size):
                    if have <= set(kit) and works(set(kit)):
                        want = set(kit)
                        break
                if want:
                    break
            if want is None:
                for size in range(0, case.kit_size + 1):
                    for kit in combinations(range(6), size):
                        if works(set(kit)):
                            want = set(kit)
                            break
                    if want is not None:
                        break
            if want is None:
                return None
            for e in sorted(have - want) if not have <= want else []:
                return ("pack", e)
            for e in sorted(want - have):
                return ("pack", e)
    pending = []
    for s in range(case.n):
        if len(cands[s]) < 2:
            continue
        for e in sorted(want & usable[s]):
            clean_rooms = [r for r in case.slots[s] if case.reading(r, e) != cw.DOUBTFUL]
            if any(st[cw.NOTES][r * 6 + e] in (cw.CLEAR, cw.POSITIVE) for r in clean_rooms):
                continue
            here = [r for r in clean_rooms if r == st[cw.ROOM]]
            pending.append((here[0] if here else clean_rooms[0], e))
    if not pending:
        return None
    pending.sort(key=lambda p: (p[0] != st[cw.ROOM], p))
    r, e = pending[0]
    return ("use", e) if st[cw.ROOM] == r else ("go", r)
