"""Heist Committee -- edits to a plan (place, clear, move a lane). Pure functions on plain dicts, so the
engine view and the tests share one definition of 'a cell was placed'."""

import copy

import engine
from engine import LANES, parse_cell


def span_of(content, cell):
    action_id, _ = parse_cell(cell)
    action = content.actions.get(action_id)
    if not action or action["kind"] not in ("task", "support"):
        return 1
    return int(action.get("duration", 1))


def _drop_overlapping(content, plan, n, lane, lo, hi):
    slots_by_lane, _ = engine.build_slots(content, plan, n)
    for slot in slots_by_lane[lane]:
        if slot["start"] <= hi and slot["end"] >= lo:
            for b in range(slot["start"], slot["end"] + 1):
                plan["lanes"][lane][b] = None


def place(content, plan, n, lane, beat, cell, default_kind=None):
    """Put `cell` at (lane, beat). Returns (new_plan, error_text_or_None). Anything it overlaps is removed."""
    new = engine.clean_plan(content, copy.deepcopy(plan), n)
    if not (0 <= lane < LANES and 0 <= beat < n):
        return new, "That cell is not on the timeline."
    action_id, arg = parse_cell(cell)
    action = content.actions.get(action_id)
    if not action:
        return new, "Unknown action."
    if action["kind"] == "wait":
        return clear(content, new, n, lane, beat), None
    if action["kind"] == "standby":
        kind = arg if arg in content.kinds else default_kind
        if kind not in content.kinds:
            return new, "Pick what to stand by for."
        cell = "standby:" + kind
    else:
        cell = action_id
    dur = span_of(content, cell)
    if beat + dur > n:
        return new, "%s needs %d beats, and only %d are left." % (action["name"], dur, n - beat)
    _drop_overlapping(content, new, n, lane, beat, beat + dur - 1)
    new["lanes"][lane][beat] = cell
    return new, None


def clear(content, plan, n, lane, beat):
    new = engine.clean_plan(content, copy.deepcopy(plan), n)
    if 0 <= lane < LANES and 0 <= beat < n:
        _drop_overlapping(content, new, n, lane, beat, beat)
    return new


def move_lane(plan, lane, direction):
    """Swap a lane with its neighbour. Returns (plan, new_lane_index or None)."""
    other = lane + direction
    if not (0 <= lane < LANES and 0 <= other < LANES):
        return plan, None
    new = copy.deepcopy(plan)
    new["lanes"][lane], new["lanes"][other] = new["lanes"][other], new["lanes"][lane]
    return new, other


def move_cell(content, plan, n, lane, beat, to_lane, to_beat, default_kind=None):
    """Move the action that covers (lane, beat) to (to_lane, to_beat). Returns (plan, error)."""
    base = engine.clean_plan(content, copy.deepcopy(plan), n)
    slots_by_lane, occ = engine.build_slots(content, base, n)
    if not (0 <= lane < LANES and 0 <= beat < n):
        return base, "That cell is not on the timeline."
    slot = occ[lane][beat]
    if not slot:
        return base, "Nothing to move."
    cell = slot["action"]["id"] + (":" + slot["arg"] if slot["arg"] else "")
    cleared = clear(content, base, n, lane, beat)
    new, err = place(content, cleared, n, to_lane, to_beat, cell, default_kind)
    if err:
        return base, err
    return new, None
