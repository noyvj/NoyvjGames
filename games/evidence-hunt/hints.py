"""Evidence Hunt -- the hint ladder: nudge, hint, answer. All three come from the careful plan's next step for the state on screen,
so they are always right for what has already been done. Hints are free, asked for by the player, and never touch a seal."""

import casework as cw
import lexicon as lx
import solver as sv


def next_action(case, st):
    return sv.next_action(case, st)


def describe(case, st, act):
    """{kind, nudge, hint, answer, label} for an action (or the restore advice when no clean finish is left)."""
    if act is None:
        return {"kind": "restore", "label": "Restore the case",
                "nudge": "A clean finish is no longer possible from here: something was spent that the rest of the case needed.",
                "hint": "You can finish with a cost, or restore the case to its start and try a different plan.",
                "answer": "Restore the case and start again. The house, the sheet and the readings are the same every time."}
    kind = act[0]
    if kind == "go":
        room = case.rooms[act[1]]["name"]
        unentered = [r for r in range(len(case.rooms)) if not st[cw.ENTERED] >> r & 1]
        if unentered:
            return {"kind": kind, "label": "Walk into the %s" % room,
                    "nudge": "Not every room has been walked yet. Walking is free, and a restless room shows itself the moment you step in.",
                    "hint": "Step into the %s next." % room, "answer": "Walk into the %s." % room}
        if case.keep_room >= 0 and not st[cw.LOOKED] and act[1] == case.keep_room:
            return {"kind": kind, "label": "Walk into the %s" % room,
                    "nudge": "A keepsake in this house will tell you a little more if you look at it.",
                    "hint": "The keepsake is in the %s." % room, "answer": "Walk into the %s to look at the keepsake." % room}
        return {"kind": kind, "label": "Walk into the %s" % room,
                "nudge": "Readings are taken in a restless room that the house does not fool.",
                "hint": "The %s is restless, and nothing in it spoils the reading you need." % room,
                "answer": "Walk into the %s." % room}
    if kind == "look":
        return {"kind": kind, "label": "Look at the keepsake",
                "nudge": "The keepsake in this room carries one more line of testimony.",
                "hint": "Look at %s." % lx.KS_WHAT[case.keep_id], "answer": "Look at %s." % lx.KS_WHAT[case.keep_id]}
    if kind == "pack":
        e = act[1]
        removing = bool(st[cw.KIT] >> e & 1)
        gear = lx.GEAR_NAME[e]
        if removing:
            return {"kind": kind, "label": "Take the %s out of the bag" % gear,
                    "nudge": "The bag has a piece that will not help tell the suspects apart.",
                    "hint": "Take the %s out to make room for one that will." % gear, "answer": "Take the %s out of the bag." % gear}
        return {"kind": kind, "label": "Pack the %s" % gear,
                "nudge": "More than one suspect still fits. The right bag can tell them apart.",
                "hint": "The %s reads %s, which is not the same for the suspects that are left." % (gear, lx.EV_NAME[e].lower()),
                "answer": "Pack the %s." % gear}
    if kind == "use":
        e = act[1]
        return {"kind": kind, "label": "Use the %s here" % lx.GEAR_NAME[e],
                "nudge": "You are in the right room with the right bag. A reading will cut the list down.",
                "hint": "Read %s in this room: %s" % (lx.EV_NAME[e].lower(), lx.GEAR_HOW[e].lower()),
                "answer": "Use the %s." % lx.GEAR_NAME[e]}
    if kind == "accuse":
        names = " and ".join(lx.KIND_NAME[lx.KIND_IDS[k]] for k in act[1:])
        return {"kind": kind, "label": "Name %s" % names,
                "nudge": "Only one kind on the sheet fits everything in your notebook.",
                "hint": "Look at the 'Could be' list: it has one name for each presence.",
                "answer": "Name %s." % names}
    return {"kind": "restore", "label": "Restore the case", "nudge": "", "hint": "", "answer": "Restore the case."}
