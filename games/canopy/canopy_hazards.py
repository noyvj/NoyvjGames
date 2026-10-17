"""Blight, wildfire and the rival logging company: state, per-tick rules and renders."""

import canopy_runstate as runstate
from canopy_helpers import _el, _gb_hash, _log_event, _plot_ref, plot_coordinate_label, ui_pref
from canopy_rules import (
    ACCRUING_STATES, DIFFICULTY_WILDFIRE, SEASON_LABEL, SPECIES, _edge_neighbours, current_season,
)
from canopy_weather import _season_at
from canopy_worldvars import (
    RIVAL_BUYOUT_COST, RIVAL_CLAIM_TICKS, RIVAL_EASEMENT_MIN, RIVAL_EASEMENT_SHARE, RIVAL_FIRST_BID_TICKS,
    RIVAL_INTERVAL_FLOOR, RIVAL_INTERVAL_STEP, RIVAL_INTERVAL_TICKS, RIVAL_NOTICE_TICKS, rival_claims,
    rival_enabled, rival_locked, rival_state,
)


# GB-7 (2026-10-09): blight in monocultures. A connected patch of BLIGHT_MIN_PATCH or more plots of one chosen species
# builds up blight pressure each tick. At BLIGHT_WARN_TICKS a warning appears (the patch is marked and announced); from
# BLIGHT_HIT_TICKS the blight kills one plot back to bare every BLIGHT_SPREAD_TICKS, always the least valuable one in
# the patch, until it is broken up or only one plot is left. Tending any plot in the patch resets it, and a patch that includes
# a different species or a standard seedling is smaller and so resists. Deterministic (no dice), recoverable (a blighted plot is just bare:
# no soil damage, no clear counted) and switchable off in Settings. Standard seedlings never count.
BLIGHT_MIN_PATCH = 5
BLIGHT_WARN_TICKS = 40
BLIGHT_HIT_TICKS = 60
BLIGHT_SPREAD_TICKS = 10
UI_PREF_BLIGHT_OFF = "canopy-blight-off"
blight_pressure = {}  # plot index -> ticks of pressure (ephemeral: a reload gives the forest a fresh start)


def blight_enabled():
    return ui_pref(UI_PREF_BLIGHT_OFF) != "true"


def species_patches(plot_list=None, cols=None):
    """Connected (up, down, left, right) groups of standing plots sharing one chosen species, as lists of indexes."""
    plot_list = runstate.plots if plot_list is None else plot_list
    cols = runstate.GRID_COLS if cols is None else cols
    by_index = {p.index: p for p in plot_list if p.state in ACCRUING_STATES and p.species}
    seen, patches = set(), []
    for start in sorted(by_index):
        if start in seen:
            continue
        species, stack, group = by_index[start].species, [start], []
        seen.add(start)
        while stack:
            current = stack.pop()
            group.append(current)
            row, col = divmod(current, cols)
            for nr, nc in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                if nr < 0 or nc < 0 or nc >= cols:
                    continue
                neighbour = nr * cols + nc
                if neighbour in by_index and neighbour not in seen and by_index[neighbour].species == species:
                    seen.add(neighbour)
                    stack.append(neighbour)
        patches.append(sorted(group))
    return patches


def blight_patch_for(index):
    for patch in species_patches():
        if index in patch:
            return patch
    return []


def relieve_blight(index):
    """Tending a plot calms the whole patch it belongs to."""
    for member in blight_patch_for(index):
        blight_pressure.pop(member, None)


def _blight_tick():
    """Advances every big single-species patch by one tick of pressure and applies the blight when due."""
    if not blight_enabled():
        blight_pressure.clear()
        return
    # A patch qualifies when it is big enough, or when the blight already took hold in it and two or more plots remain.
    large = [patch for patch in species_patches()
             if len(patch) >= BLIGHT_MIN_PATCH
             or (len(patch) >= 2 and max(blight_pressure.get(i, 0) for i in patch) >= BLIGHT_HIT_TICKS)]
    in_patch = {i for patch in large for i in patch}
    for index in list(blight_pressure):
        if index not in in_patch:
            del blight_pressure[index]
    for patch in large:
        pressure = max(blight_pressure.get(i, 0) for i in patch) + 1
        for member in patch:
            blight_pressure[member] = pressure
        name = SPECIES[runstate.plots[patch[0]].species]["label"].lower()
        if pressure == BLIGHT_WARN_TICKS:
            _log_event("blight", f"Blight warning: the {name} patch ({len(patch)} plots) is struggling. Tend a plot in it, or break it up with another species")
        if pressure >= BLIGHT_HIT_TICKS and (pressure - BLIGHT_HIT_TICKS) % BLIGHT_SPREAD_TICKS == 0:
            victim = min(patch, key=lambda i: (runstate.plots[i].value, i))
            runstate.plots[victim].blight()
            blight_pressure.pop(victim, None)
            _log_event("blight", f"Blight killed {_plot_ref(victim)} in the {name} patch. Replant it, ideally with a different species", victim)


def blight_status_for(index):
    """'' when the plot is safe, else a short phrase for its tooltip."""
    pressure = blight_pressure.get(index, 0)
    if pressure >= BLIGHT_HIT_TICKS:
        return f"blight is spreading here (the patch loses a plot every {BLIGHT_SPREAD_TICKS} ticks): tend a plot in it or plant another species"
    if pressure >= BLIGHT_WARN_TICKS:
        return f"blight warning: {BLIGHT_HIT_TICKS - pressure} ticks until it spreads (tend a plot in the patch or plant another species)"
    return ""


# GB-1 (2026-10-09): wildfire season, only on the "Wildfire season" difficulty. In summer (every 30-tick block) and about
# half the autumn blocks a spark is due on a standing plot. Three ticks before, smoke marks the plot and the log warns.
# A burning plot sets its standing neighbours alight from its second tick, and burns out (back to bare, value lost, no soil
# damage) on its fourth. Bare and replanting plots are firebreaks, so clearing a plot on purpose (and taking the soil hit)
# can save a mature cluster; Dampen puts a burning or smoking plot out and shields it for a while. The Heart Tree never burns.
# Deterministic (the same hash as the weather, no dice) and not saved: a reload starts calm.
FIRE_BLOCK_TICKS = 30
FIRE_WARNING_TICKS = 3
FIRE_SPREAD_AGE = 2
FIRE_BURN_TICKS = 4
FIRE_DAMP_TICKS = 12
FIRE_DAMPEN_COOLDOWN = 6
FIRE_SEASON_PERCENT = {"summer": 100, "autumn": 50}
fires = {}  # plot index -> ticks burning
fire_damp = {}  # plot index -> ticks of protection left


def _reset_fire():
    fires.clear()
    fire_damp.clear()
    runstate.fire_warning = None
    runstate.dampen_cooldown = 0
    runstate.fire_value_lost = 0.0


def wildfire_enabled():
    return runstate.current_difficulty == DIFFICULTY_WILDFIRE


def fire_ignition_tick(block):
    """The tick inside `block` at which a spark is due, or None when that block has no fire."""
    start = block * FIRE_BLOCK_TICKS
    season = _season_at(start + FIRE_BLOCK_TICKS // 2)
    if _gb_hash(block, 41) % 100 >= FIRE_SEASON_PERCENT.get(season, 0):
        return None
    return start + FIRE_WARNING_TICKS + _gb_hash(block, 43) % (FIRE_BLOCK_TICKS - FIRE_WARNING_TICKS - 1)


def _fire_candidates():
    return [p.index for p in runstate.plots if p.state in ACCRUING_STATES and p.index not in fires
            and fire_damp.get(p.index, 0) <= 0 and p.index != runstate.heart_tree_index and p.value > 0]


def _ignite(index, message=None):
    fires[index] = 0
    _log_event("fire", message or f"Fire spread to {_plot_ref(index)}", index)


def _burn_out(index):
    fires.pop(index, None)
    plot = runstate.plots[index]
    runstate.fire_value_lost += plot.value
    lost = plot.value
    plot.blight()  # back to bare: nothing harvested, soil untouched
    _log_event("fire", f"Fire burned out {_plot_ref(index)} and took {lost:.1f} of value. Replant it when it is safe", index)


def _fire_tick():
    """Advances warnings, fires and protection by one tick (a no-op unless the difficulty is Wildfire season)."""
    if not wildfire_enabled():
        if fires or runstate.fire_warning or fire_damp:
            fires.clear()
            fire_damp.clear()
            runstate.fire_warning = None
        return
    runstate.dampen_cooldown = max(0, runstate.dampen_cooldown - 1)
    for index in list(fire_damp):
        fire_damp[index] -= 1
        if fire_damp[index] <= 0:
            del fire_damp[index]
    for index in list(fires):  # snapshot: plots set alight this tick start their own clock next tick
        if index not in fires:
            continue
        fires[index] += 1
        if fires[index] >= FIRE_SPREAD_AGE:
            for neighbour in _edge_neighbours(index):
                if (neighbour < len(runstate.plots) and neighbour not in fires and runstate.plots[neighbour].state in ACCRUING_STATES
                        and runstate.plots[neighbour].region == "main" and fire_damp.get(neighbour, 0) <= 0
                        and neighbour != runstate.heart_tree_index):
                    _ignite(neighbour)
        if fires[index] >= FIRE_BURN_TICKS:
            _burn_out(index)
    for index in list(fires):  # a plot that stopped standing some other way (cleared) is out
        if runstate.plots[index].state not in ACCRUING_STATES:
            del fires[index]
    ignition_block = runstate.forest_tick // FIRE_BLOCK_TICKS
    due = fire_ignition_tick(ignition_block)
    if runstate.fire_warning is not None:
        runstate.fire_warning["ticks_left"] -= 1
        if runstate.fire_warning["ticks_left"] <= 0:
            target = runstate.fire_warning["plot"]
            runstate.fire_warning = None
            if runstate.plots[target].state in ACCRUING_STATES and fire_damp.get(target, 0) <= 0 and target not in fires:
                _ignite(target, f"A spark caught on {_plot_ref(target)}. Dampen it, or clear a plot to make a firebreak")
    elif due is not None and runstate.forest_tick == due - FIRE_WARNING_TICKS:
        candidates = _fire_candidates()
        if candidates:
            target = candidates[_gb_hash(ignition_block, 47) % len(candidates)]
            runstate.fire_warning = {"plot": target, "ticks_left": FIRE_WARNING_TICKS}
            _log_event("fire", f"Smoke over {_plot_ref(target)}: a spark is due in {FIRE_WARNING_TICKS} ticks. Select it and press Dampen", target)


def can_dampen(index):
    if not wildfire_enabled() or index is None or runstate.dampen_cooldown > 0:
        return False
    return index in fires or (runstate.fire_warning is not None and runstate.fire_warning["plot"] == index)


def fire_status_text():
    if not wildfire_enabled():
        return ""
    if fires:
        labels = ", ".join(plot_coordinate_label(i) for i in sorted(fires))
        soonest = FIRE_BURN_TICKS - max(fires.values())
        return f"Fire on {labels}: the oldest burns out in {soonest} tick{'s' if soonest != 1 else ''}. Dampen it or clear a plot to stop it spreading."
    if runstate.fire_warning is not None:
        return f"Smoke over {plot_coordinate_label(runstate.fire_warning['plot'])}: a spark in {runstate.fire_warning['ticks_left']} tick{'s' if runstate.fire_warning['ticks_left'] != 1 else ''}."
    return f"Fire season: calm for now ({SEASON_LABEL[current_season()].lower()}). Lost to fire so far: {runstate.fire_value_lost:.1f}."


def render_fire():
    status = _el("fire-status")
    if status is not None:
        text = fire_status_text()
        status.hidden = not text
        status.innerText = text
    button = _el("dampen-button")
    if button is not None:
        button.hidden = not wildfire_enabled()
        button.disabled = not can_dampen(runstate.selected_index)
        button.title = ("Put out the burning or smoking plot you selected and shield it for a while"
                        + (f" (ready in {runstate.dampen_cooldown} ticks)" if runstate.dampen_cooldown else ""))


def _reset_rival():
    rival_claims.clear()
    rival_locked.clear()
    runstate.rival_notice = None
    rival_state.update({"next_bid": RIVAL_FIRST_BID_TICKS, "bids": 0})


def _is_edge(index):
    row, col = divmod(index, runstate.GRID_COLS)
    return row in (0, runstate.GRID_ROWS - 1) or col in (0, runstate.GRID_COLS - 1)


def rival_bid_interval():
    return max(RIVAL_INTERVAL_FLOOR, RIVAL_INTERVAL_TICKS - RIVAL_INTERVAL_STEP * rival_state["bids"])


def _rival_candidates():
    return [p.index for p in runstate.plots if p.state in ACCRUING_STATES and not p.blocked and _is_edge(p.index)
            and p.index not in rival_locked and p.index != runstate.heart_tree_index]


def easement_cost(index):
    return round(max(RIVAL_EASEMENT_MIN, RIVAL_EASEMENT_SHARE * runstate.plots[index].value), 1)


def can_lock(index):
    return (rival_enabled() and index is not None and 0 <= index < len(runstate.plots) and runstate.plots[index].state in ACCRUING_STATES
            and not runstate.plots[index].blocked and index not in rival_locked and runstate.total_income >= easement_cost(index))


def can_buy_out(index):
    return rival_enabled() and index in rival_claims and runstate.total_income >= RIVAL_BUYOUT_COST


def _rival_tick():
    if not rival_enabled():
        if rival_claims or runstate.rival_notice or rival_locked:
            _reset_rival()
        return
    for index in list(rival_claims):
        rival_claims[index] -= 1
        if rival_claims[index] <= 0:
            del rival_claims[index]
            _log_event("rival", f"Halloran Timber Co. has left {_plot_ref(index)}. It is bare and free to replant", index)
    if runstate.rival_notice is not None:
        runstate.rival_notice["ticks_left"] -= 1
        if runstate.rival_notice["ticks_left"] <= 0:
            target = runstate.rival_notice["plot"]
            runstate.rival_notice = None
            if runstate.plots[target].state in ACCRUING_STATES and target not in rival_locked:
                lost = runstate.plots[target].value
                runstate.plots[target].blight()  # bare with no soil damage, like a fire: nothing was harvested
                rival_claims[target] = RIVAL_CLAIM_TICKS
                _log_event("rival", f"Halloran Timber Co. took {_plot_ref(target)} ({lost:.1f} of value). Buy the claim out, or wait {RIVAL_CLAIM_TICKS} ticks", target)
    elif runstate.forest_tick >= rival_state["next_bid"]:
        candidates = _rival_candidates()
        rival_state["next_bid"] = runstate.forest_tick + rival_bid_interval()
        if candidates:
            target = candidates[_gb_hash(rival_state["bids"], runstate.forest_tick // 7, 53) % len(candidates)]
            rival_state["bids"] += 1
            runstate.rival_notice = {"plot": target, "ticks_left": RIVAL_NOTICE_TICKS}
            _log_event("rival", f"Halloran Timber Co. is bidding on {_plot_ref(target)}: they take it in {RIVAL_NOTICE_TICKS} ticks. "
                                f"Lock it with an easement ({easement_cost(target):.1f}) to keep it", target)


def rival_status_text():
    if not rival_enabled():
        return ""
    if runstate.rival_notice is not None:
        t = runstate.rival_notice["plot"]
        return (f"Halloran Timber Co. is bidding on {plot_coordinate_label(t)}: claim in {runstate.rival_notice['ticks_left']} ticks. "
                f"An easement costs {easement_cost(t):.1f}.")
    parts = [f"Halloran Timber Co.: next bid in about {max(0, rival_state['next_bid'] - runstate.forest_tick)} ticks."]
    if rival_claims:
        parts.append("Mining claims: " + ", ".join(f"{plot_coordinate_label(i)} ({n} ticks left)" for i, n in sorted(rival_claims.items())) + ".")
    if rival_locked:
        parts.append(f"{len(rival_locked)} plot{'s' if len(rival_locked) != 1 else ''} under easement.")
    return " ".join(parts)


def render_rival():
    status = _el("rival-status")
    text = rival_status_text()
    if status is not None:
        status.hidden = not text
        status.innerText = text
    lock_button, buyout_button = _el("rival-lock-button"), _el("rival-buyout-button")
    target = runstate.rival_notice["plot"] if runstate.rival_notice is not None else runstate.selected_index
    if lock_button is not None:
        lock_button.hidden = not rival_enabled()
        lock_button.disabled = not can_lock(target)
        lock_button.innerText = f"\U0001F512 Lock plot ({easement_cost(target):.1f})" if target is not None and 0 <= target < len(runstate.plots) else "\U0001F512 Lock plot"
    if buyout_button is not None:
        buyout_button.hidden = not rival_enabled()
        buyout_button.disabled = not can_buy_out(runstate.selected_index)
        buyout_button.innerText = f"Buy out claim ({RIVAL_BUYOUT_COST:.0f})"


def _note_recovery(plot):
    runstate.total_recoveries += 1
    _log_event("recovered", f"{_plot_ref(plot.index)} finished recovering", plot.index)
