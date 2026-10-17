"""Ranger contracts: board, progress, rewards and the panel, plus their save fields."""

from js import document

import canopy_runstate as runstate
from canopy_achievements import _mature_plot_count, _wildlife_active_count
from canopy_helpers import _el, _gb_hash, _gb_toast, _log_event, _number_or
from canopy_valuation import _total_clear_count, active_plot_count, standing_forest_value
from canopy_worldvars import (
    CHALLENGE_NONE, CHALLENGE_SPECS, CONTRACT_CALM_TICKS, CONTRACT_RANKS, CONTRACT_REFILL_TICKS,
    CONTRACT_REWARD_PER_PLOT, CONTRACT_SLOTS, CONTRACT_TYPES, PACE_NORMAL, REQUEST_PACE_FACTOR,
    _announce_queue, contract_board, contract_stamps,
)


# --- GB-9: Ranger contracts board ------------------------------------------------------------------------------

def _contract_target_and_base(type_id):
    n = len(runstate.plots)
    if type_id == "replant":
        return 3, runstate.total_replants
    if type_id == "mature":
        return max(2, n // 6, _mature_plot_count() + 2), 0
    if type_id == "wildlife":
        return max(3, n // 5, _wildlife_active_count() + 2), 0
    if type_id == "decline":
        return 2, runstate.stakeholder_declines_count
    if type_id == "accept":
        return 1, runstate.stakeholder_grants_count
    if type_id == "tend":
        return 2, runstate.tends_done
    if type_id == "seedling":
        return 1, runstate.seedlings_caught
    if type_id == "standing":
        return max(10, int(round((standing_forest_value() * 1.25 + 60 * n) / 10.0)) * 10), 0
    if type_id == "calm":
        return CONTRACT_CALM_TICKS, 0
    return min(100, max(60, runstate.community_relations + 15)), 0  # trust


def _contract_progress(contract):
    type_id = contract["type"]
    base = contract.get("base", 0)
    if type_id == "replant":
        return runstate.total_replants - base
    if type_id == "mature":
        return _mature_plot_count()
    if type_id == "wildlife":
        return _wildlife_active_count()
    if type_id == "decline":
        return runstate.stakeholder_declines_count - base
    if type_id == "accept":
        return runstate.stakeholder_grants_count - base
    if type_id == "tend":
        return runstate.tends_done - base
    if type_id == "seedling":
        return runstate.seedlings_caught - base
    if type_id == "standing":
        return int(standing_forest_value())
    if type_id == "calm":
        return max(0, runstate.forest_tick - runstate.contract_last_clear_tick)
    return runstate.community_relations


def contract_text(contract):
    target = contract["target"]
    return {
        "replant": f"Replant {target} plots",
        "mature": f"Have {target} fully mature plots at once",
        "wildlife": f"Have wildlife on {target} plots at once",
        "decline": f"Decline {target} community requests",
        "accept": f"Say yes to {target} community request or offer",
        "tend": f"Tend {target} plots (T)",
        "seedling": "Catch a golden seedling (G)",
        "standing": f"Grow your standing value to {target}",
        "calm": f"Go {target} ticks without clearing a plot",
        "trust": f"Raise community relations to {target}",
    }[contract["type"]]


def contract_reward():
    return CONTRACT_REWARD_PER_PLOT * active_plot_count()


def contract_rank():
    title = CONTRACT_RANKS[0][1]
    for needed, name in CONTRACT_RANKS:
        if runstate.contracts_completed >= needed:
            title = name
    return title


def _pick_contract_type():
    """Deterministic pick (hash of the tick and the count so far). Contracts whose stamp you have not
    collected come first, so a patient player sees all ten."""
    on_board = {c["type"] for c in contract_board}
    start = _gb_hash(runstate.forest_tick, runstate.contracts_completed, len(contract_board), 91) % len(CONTRACT_TYPES)
    ordered = [CONTRACT_TYPES[(start + k) % len(CONTRACT_TYPES)][0] for k in range(len(CONTRACT_TYPES))]
    candidates = [t for t in ordered if t not in on_board and not (t == "trust" and runstate.community_relations >= 90)]
    fresh = [t for t in candidates if t not in contract_stamps]
    pool = fresh or candidates
    return pool[0] if pool else None


def _add_contract():
    type_id = _pick_contract_type()
    if type_id is None:
        return False
    target, base = _contract_target_and_base(type_id)
    contract_board.append({"type": type_id, "target": target, "base": base})
    return True


def _fill_contract_board():
    del contract_board[:]
    if runstate.current_challenge != CHALLENGE_NONE:
        return
    while len(contract_board) < CONTRACT_SLOTS and _add_contract():
        pass


def _stamp_name(type_id):
    for tid, _icon, name in CONTRACT_TYPES:
        if tid == type_id:
            return name
    return type_id


def _complete_contract(contract):
    contract_board.remove(contract)
    reward = contract_reward()
    runstate.total_income += reward
    runstate.contracts_completed += 1
    new_stamp = contract["type"] not in contract_stamps
    if new_stamp:
        contract_stamps.append(contract["type"])
    if len(contract_board) < CONTRACT_SLOTS and runstate.contract_refill_ticks <= 0:
        runstate.contract_refill_ticks = CONTRACT_REFILL_TICKS
    _log_event("contract", f"Contract done: {contract_text(contract)} (+{reward} income)", None)
    stamp_part = f", new stamp: {_stamp_name(contract['type'])}" if new_stamp else ""
    _gb_toast(f"\U0001F4DC Contract done: +{reward} income{stamp_part}")


def _advance_contracts():
    clears = _total_clear_count()
    if clears > runstate.contract_clear_count_seen:
        runstate.contract_last_clear_tick = runstate.forest_tick
    runstate.contract_clear_count_seen = clears
    if runstate.current_challenge != CHALLENGE_NONE:
        return
    for contract in list(contract_board):
        if _contract_progress(contract) >= contract["target"]:
            _complete_contract(contract)
    if len(contract_board) < CONTRACT_SLOTS:
        if runstate.contract_refill_ticks > 0:
            runstate.contract_refill_ticks -= 1
        elif _add_contract() and len(contract_board) < CONTRACT_SLOTS:
            runstate.contract_refill_ticks = CONTRACT_REFILL_TICKS


def on_toggle_contracts(event=None):
    runstate.contracts_open = not runstate.contracts_open
    render_contracts()


def render_contracts():
    toggle = _el("contracts-toggle-button")
    panel = _el("contracts-panel")
    if toggle is None or panel is None:
        return
    if runstate.current_challenge != CHALLENGE_NONE:
        label_count = "closed"
    else:
        label_count = f"{len(contract_board)} open"
    toggle.innerText = (
        f"Hide Contracts ({label_count})" if runstate.contracts_open else f"\U0001F4DC Contracts ({label_count})"
    )
    panel.hidden = not runstate.contracts_open
    if not runstate.contracts_open:
        return
    panel.innerHTML = ""
    title = document.createElement("h2")
    title.className = "contracts-title"
    title.innerText = "Ranger contracts"
    panel.appendChild(title)
    rank = document.createElement("p")
    rank.className = "contracts-rank"
    rank.innerText = (
        f"Rank: {contract_rank()} · {runstate.contracts_completed} contract{'s' if runstate.contracts_completed != 1 else ''} done "
        f"· each pays {contract_reward()} income"
    )
    panel.appendChild(rank)
    if runstate.current_challenge != CHALLENGE_NONE:
        closed = document.createElement("p")
        closed.className = "contracts-note"
        closed.innerText = "The ranger service is closed during a challenge run. Choose No challenge to reopen the board."
        panel.appendChild(closed)
    else:
        board = document.createElement("ul")
        board.className = "contracts-list"
        for contract in contract_board:
            progress = max(0, min(contract["target"], _contract_progress(contract)))
            item = document.createElement("li")
            item.className = "contract-card"
            label = document.createElement("p")
            label.className = "contract-card-label"
            icon = next((c[1] for c in CONTRACT_TYPES if c[0] == contract["type"]), "")
            label.innerText = f"{icon} {contract_text(contract)}"
            item.appendChild(label)
            count = document.createElement("p")
            count.className = "contract-card-progress"
            count.innerText = f"{progress} of {contract['target']}"
            item.appendChild(count)
            bar = document.createElement("progress")
            bar.className = "contract-card-bar"
            bar.max = contract["target"]
            bar.value = progress
            bar.setAttribute("aria-label", f"{contract_text(contract)}: {progress} of {contract['target']}")
            item.appendChild(bar)
            board.appendChild(item)
        if not contract_board:
            waiting = document.createElement("li")
            waiting.className = "contract-card contract-card--waiting"
            waiting.innerText = f"Next contract in {max(1, runstate.contract_refill_ticks)} ticks"
            board.appendChild(waiting)
        panel.appendChild(board)
    stamps_heading = document.createElement("h3")
    stamps_heading.className = "almanac-heading"
    stamps_heading.innerText = f"Stamps ({len(contract_stamps)}/{len(CONTRACT_TYPES)})"
    panel.appendChild(stamps_heading)
    stamp_row = document.createElement("ul")
    stamp_row.className = "almanac-list"
    for type_id, icon, name in CONTRACT_TYPES:
        got = type_id in contract_stamps
        item = document.createElement("li")
        item.className = "almanac-item almanac-item--found" if got else "almanac-item almanac-item--unfound"
        item.setAttribute("aria-label", f"{name}: {'stamped' if got else 'not yet stamped'}")
        glyph = document.createElement("span")
        glyph.className = "almanac-icon" if got else "almanac-icon almanac-silhouette"
        glyph.setAttribute("aria-hidden", "true")
        glyph.innerText = icon
        item.appendChild(glyph)
        text = document.createElement("span")
        text.className = "almanac-name"
        text.innerText = name if got else "???"
        item.appendChild(text)
        stamp_row.appendChild(item)
    panel.appendChild(stamp_row)


def _load_contracts(data):
    """Applies the validated ranger_contracts blob (a save without one keeps the fresh board)."""
    runstate.contract_clear_count_seen = _total_clear_count()
    raw = data.get("ranger_contracts")
    if not isinstance(raw, dict) or runstate.current_challenge != CHALLENGE_NONE:
        return
    valid = {t[0] for t in CONTRACT_TYPES}
    board = []
    seen = set()
    saved_board = raw.get("board")
    for entry in saved_board if isinstance(saved_board, list) else []:
        if not isinstance(entry, dict) or len(board) >= CONTRACT_SLOTS:
            continue
        type_id = entry.get("type")
        if not isinstance(type_id, str) or type_id not in valid or type_id in seen:
            continue
        target = _number_or(entry.get("target"), None, 1, 100000)
        if target is None:
            continue
        seen.add(type_id)
        board.append({"type": type_id, "target": int(target), "base": int(_number_or(entry.get("base"), 0, 0, 10 ** 9))})
    contract_board[:] = board
    del contract_stamps[:]
    saved_stamps = raw.get("stamps")
    for type_id in saved_stamps if isinstance(saved_stamps, list) else []:
        if isinstance(type_id, str) and type_id in valid and type_id not in contract_stamps:
            contract_stamps.append(type_id)
    runstate.contracts_completed = int(_number_or(raw.get("completed"), 0, 0, 10 ** 6))
    runstate.contract_refill_ticks = int(_number_or(raw.get("refill"), 0, 0, CONTRACT_REFILL_TICKS))
    runstate.contract_last_clear_tick = int(_number_or(raw.get("last_clear_tick"), 0, 0, 10 ** 9))
    runstate.tends_done = int(_number_or(raw.get("tends"), 0, 0, 10 ** 9))
    runstate.seedlings_caught = int(_number_or(raw.get("seedlings"), 0, 0, 10 ** 9))


def _reset_gb2_state():
    runstate.challenge_complete_tick = None
    runstate.contracts_completed = 0
    runstate.contract_refill_ticks = 0
    runstate.contract_last_clear_tick = 0
    runstate.contract_clear_count_seen = 0
    runstate.tends_done = 0
    runstate.seedlings_caught = 0
    del contract_stamps[:]
    del _announce_queue[:]
    _fill_contract_board()


def _load_gb2_state(data):
    if runstate.current_challenge != CHALLENGE_NONE:
        saved = data.get("challenge")
        done = saved.get("done_tick") if isinstance(saved, dict) else None
        if isinstance(done, int) and not isinstance(done, bool) and done >= 0:
            runstate.challenge_complete_tick = done
    _load_contracts(data)


def _saved_challenge_id(data):
    saved = data.get("challenge")
    cid = saved.get("id") if isinstance(saved, dict) else None
    return cid if isinstance(cid, str) and cid in CHALLENGE_SPECS else CHALLENGE_NONE


def _saved_pace(data):
    pace = data.get("request_pace")
    return pace if isinstance(pace, str) and pace in REQUEST_PACE_FACTOR else PACE_NORMAL
