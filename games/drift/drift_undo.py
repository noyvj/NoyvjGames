"""Reset this round, the Rewind Token, and Play 5 rounds (snapshots, automatic rounds)."""

import copy

from js import document

import drift_runstate as runstate
from drift_collection import _collect_after_round
from drift_ledger import latest_recap
from drift_model_region import RegionState, region
from drift_regional import _sync_spillover, neighbor_spillover
from drift_rules import CALENDAR_KINDS, STRAIN_LEVEL_THRESHOLDS


# ---- I-15 / GI-18: undo family ---------------------------------------------


def _clone_region(saved_dict):
    other = RegionState()
    other.__dict__.clear()
    other.__dict__.update(copy.deepcopy(saved_dict))
    return other


def _take_round_start_snapshot():
    return {
        "funds": region.funds,
        "capacity": dict(region.capacity),
        "policy_level": dict(region.policy_level),
        "cumulative_services_investment": region.cumulative_services_investment,
        "spend_by_type": dict(region.spend_by_type),
        "round_spend": dict(region.round_spend),
        "braced_rounds": list(region.braced_rounds),
        "neighbor": copy.deepcopy(runstate.neighbor.__dict__) if runstate.neighbor is not None else None,
        "support_sent": runstate.neighbor_support_sent,
    }


def _take_full_snapshot():
    return {
        "region": copy.deepcopy(region.__dict__),
        "neighbor": copy.deepcopy(runstate.neighbor.__dict__) if runstate.neighbor is not None else None,
        "support_sent": runstate.neighbor_support_sent,
        "round_start": copy.deepcopy(runstate.round_start_snapshot),
    }


def reset_round():
    """I-15: refund everything decided since the round began (capacity, policies,
    reallocations and neighbour moves). Returns False if there is nothing to undo."""
    snap = runstate.round_start_snapshot
    if snap is None or region.round_buys <= 0:
        return False
    region.funds = snap["funds"]
    region.capacity = dict(snap["capacity"])
    region.policy_level = dict(snap["policy_level"])
    region.cumulative_services_investment = snap["cumulative_services_investment"]
    region.spend_by_type = dict(snap["spend_by_type"])
    region.round_spend = dict(snap["round_spend"])
    region.braced_rounds = list(snap.get("braced_rounds", region.braced_rounds))
    region.round_buys = 0
    runstate.neighbor = _clone_region(snap["neighbor"]) if snap["neighbor"] is not None else None
    runstate.neighbor_support_sent = snap["support_sent"]
    return True


def rewind_available():
    return region.rewind_used_round is None and runstate.rewind_snapshot is not None


def use_rewind_token():
    """GI-18: one take-back per region. Restores the whole state to just before the
    last Advance Round (anything decided since is refunded with it)."""
    if not rewind_available():
        return False
    snap = runstate.rewind_snapshot
    region.__dict__.clear()
    region.__dict__.update(copy.deepcopy(snap["region"]))
    region.rewind_used_round = region.round_number
    runstate.neighbor = _clone_region(snap["neighbor"]) if snap["neighbor"] is not None else None
    runstate.neighbor_support_sent = snap["support_sent"]
    runstate.round_start_snapshot = copy.deepcopy(snap["round_start"]) if snap["round_start"] is not None else _take_round_start_snapshot()
    runstate.rewind_snapshot = None
    return True


def _reset_undo_state():
    """After a load or a fresh start: nothing earlier than now can be undone."""
    region.round_buys = 0
    runstate.round_start_snapshot = _take_round_start_snapshot()
    runstate.rewind_snapshot = None
    runstate.rewind_armed = False


# ---- GI-30: Play 5 rounds ----------------------------------------------------
PLAY_ROUNDS_COUNT = 5


def _strain_rank(fraction):
    rank = 0
    for index, (threshold, _label) in enumerate(STRAIN_LEVEL_THRESHOLDS):
        if fraction >= threshold:
            rank = index
    return rank


def _auto_block_reason():
    """Why an automatic run must not start the current round, or None. A braceable
    calendar event due this round has to be braced by hand, or advanced by hand."""
    event = region.calendar_event()
    if (
        event is not None
        and CALENDAR_KINDS[event["kind"]]["braceable"]
        and region.round_number not in region.braced_rounds
    ):
        return f"{event['name']} is due this round: brace for it, or press Advance Round yourself"
    return None


def _run_auto_rounds(count, before_round=None):
    """Advance up to `count` rounds as automatic rounds. `before_round` (optional) makes
    purchases first (the Budget Autopilot). Stops early, after the round that caused it, if
    strain moves up a level, a second-wave event arrives, the neighbouring district starts
    sending people, or the Crisis Calendar shows a braceable event for next round; and
    refuses to start a round whose braceable event is unbraced. Returns (advanced, reason)."""
    advanced = 0
    reason = None
    for _ in range(count):
        blocked = _auto_block_reason()
        if blocked:
            reason = blocked
            break
        level_before = _strain_rank(region.strain_fraction())
        wave_before = region.second_wave_status
        spill_before = neighbor_spillover()
        _sync_spillover()
        if before_round is not None:
            before_round()
        runstate.rewind_snapshot = _take_full_snapshot()
        completed = region.round_number
        region.advance_round(auto=True)
        if runstate.neighbor is not None:
            runstate.neighbor.advance_round()
        _sync_spillover()
        _collect_after_round(completed)
        advanced += 1
        upcoming = region.calendar_event(region.round_number + 1)
        if _strain_rank(region.strain_fraction()) > level_before:
            reason = f"strain rose to {region.strain_level()}"
        elif region.second_wave_status != wave_before:
            reason = {
                "warned": "a second wave was announced",
                "active": "the second wave arrived",
                "done": "the second wave ended",
            }.get(region.second_wave_status, "a forecast event arrived")
        elif spill_before == 0.0 and neighbor_spillover() > 0.0:
            reason = "the neighbouring district went critical and is sending people your way"
        elif (
            upcoming is not None
            and CALENDAR_KINDS[upcoming["kind"]]["braceable"]
            and upcoming["round"] not in region.braced_rounds
        ):
            reason = f"the Crisis Calendar shows {upcoming['name']} next round"
        if reason:
            break
    runstate.round_start_snapshot = _take_round_start_snapshot()
    return advanced, reason


def play_rounds(count=PLAY_ROUNDS_COUNT):
    """Advance up to `count` rounds with the current allocation (no purchases).
    Returns (rounds advanced, reason or None)."""
    return _run_auto_rounds(count)


def render_round_tools():
    buys = region.round_buys
    reset_button = document.getElementById("reset-round-button")
    reset_button.disabled = not (buys > 0 and runstate.round_start_snapshot is not None)
    reset_button.innerText = (
        f"↩️ Reset this round ({buys} decision{'s' if buys != 1 else ''})" if buys > 0 else "↩️ Reset this round"
    )
    rewind_button = document.getElementById("rewind-button")
    if region.rewind_used_round is not None:
        rewind_button.innerText = f"⏪ Rewind Token used in round {region.rewind_used_round}"
        rewind_button.disabled = True
    elif runstate.rewind_snapshot is None:
        rewind_button.innerText = "⏪ Rewind Token (1 left)"
        rewind_button.disabled = True
    elif runstate.rewind_armed:
        rewind_button.innerText = "Confirm: undo the last Advance Round"
        rewind_button.disabled = False
    else:
        rewind_button.innerText = "⏪ Rewind Token (1 left)"
        rewind_button.disabled = False
    document.getElementById("play-rounds-button").innerText = f"⏩ Play {PLAY_ROUNDS_COUNT} rounds"
    note = document.getElementById("round-tools-note")
    note.innerText = runstate.round_tools_message
    note.hidden = runstate.round_tools_message == ""
    recap = latest_recap()
    details = document.getElementById("round-recap-details")
    details.hidden = recap is None
    document.getElementById("round-recap-display").innerText = recap or ""
