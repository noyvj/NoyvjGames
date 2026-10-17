"""The Highland Grove and the Wetland Forest: unlocking, tides and floods, tooltips, stats and panels."""

from js import document

import canopy_runstate as runstate
from canopy_helpers import _log_event, fmt_num
from canopy_rules import (
    ACCRUING_STATES, MATURITY_TICKS, RECOVERY_TICKS, REPLANTING, SPECIES_MANGROVE, STATE_LABEL,
    VALID_ACTIONS,
)
from canopy_valuation import standing_forest_value
from canopy_worldvars import (
    CHALLENGE_NO_HIGHLAND, HIGHLAND_COLS, HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD, WETLAND_COLS,
    WETLAND_FLOOD_INTERVAL_TICKS, WETLAND_FLOOD_LOSS_MATURE, WETLAND_FLOOD_LOSS_YOUNG,
    WETLAND_FLOOD_SILT_TICKS, WETLAND_FLOOD_WARNING_TICKS, WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD,
)


# ===========================================================================
# Highland Grove -- B3's second, unlockable forest region (planning/
# TODO.md "Per-game: Canopy"). Reuses the Plot class and its clear/
# replant/accrue_tick() mechanics directly (same rules, same math); this
# section is the region-specific plumbing (its own grid, selection,
# income, and rendering) layered on top.
# ===========================================================================


def _maybe_unlock_highland():
    """Checked once per tick(). A sticky, one-way unlock -- once the main
    forest's standing value has ever crossed the threshold, Highland Grove
    stays unlocked even if that value later drops (e.g. the player clears
    plots afterward), matching this game's no-dead-end-states philosophy:
    unlocking a region is a permanent milestone, not a live gate that
    could lock back up mid-session."""
    if runstate.current_challenge == CHALLENGE_NO_HIGHLAND:
        return  # GB-17: the regions stay sealed
    if not runstate.highland_unlocked and standing_forest_value() >= HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD:
        runstate.highland_unlocked = True
        _log_event("unlock", "Highland Grove unlocked", None)


def highland_plot_coordinate_label(index):
    """B4's coordinate-label convention, applied to Highland Grove's own
    (smaller) grid -- uses HIGHLAND_COLS, not GRID_COLS, so a Highland
    tile's letter wraps at the right width for its own 4-wide grid rather
    than the main forest's."""
    row, col = divmod(index, HIGHLAND_COLS)
    return f"{chr(ord('A') + col)}{row + 1}"


def highland_standing_value():
    return sum(plot.value for plot in runstate.highland_plots)


def _highland_tooltip_text(plot):
    """Highland Grove's own version of _plot_tooltip_text() -- same shape,
    but using highland_plot_coordinate_label() so the label matches this
    grid's own width."""
    soil_pct = round(plot.productivity_multiplier() * 100)
    label = f"{highland_plot_coordinate_label(plot.index)} · {STATE_LABEL[plot.state]} · value {plot.value:.1f} · soil {soil_pct}%"
    if plot.state == REPLANTING:
        label += f" · recovering in {plot.replant_ticks_remaining} ticks"
    return label


def render_highland_panel():
    state_el = document.getElementById("highland-selected-plot-state")
    clear_button = document.getElementById("highland-clear-button")
    replant_button = document.getElementById("highland-replant-button")

    if runstate.highland_selected_index is None:
        state_el.innerText = "No plot selected"
        clear_button.disabled = True
        replant_button.disabled = True
        return

    plot = runstate.highland_plots[runstate.highland_selected_index]
    detail = f"value {plot.value:.1f}"
    if plot.state == REPLANTING:
        detail = f"recovering in {plot.replant_ticks_remaining} ticks"
    state_el.innerText = (
        f"Plot {highland_plot_coordinate_label(runstate.highland_selected_index)}: {STATE_LABEL[plot.state]} ({detail})"
    )
    clear_button.disabled = "clear" not in VALID_ACTIONS[plot.state]
    replant_button.disabled = "replant" not in VALID_ACTIONS[plot.state]


def render_highland_stats():
    document.getElementById("highland-income-display").innerText = f"Harvested income: {fmt_num(runstate.highland_income)}"
    document.getElementById("highland-standing-value-display").innerText = (
        f"Standing grove value: {fmt_num(highland_standing_value())}"
    )


# ===========================================================================
# Wetland Forest -- B1's third region. Same shape as Highland Grove above
# (own grid, selection, income), plus the flood timer described at
# WETLAND_ROWS.
# ===========================================================================


def _maybe_unlock_wetland():
    if runstate.current_challenge == CHALLENGE_NO_HIGHLAND:
        return  # GB-17: the regions stay sealed
    if not runstate.wetland_unlocked and standing_forest_value() >= WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD:
        runstate.wetland_unlocked = True
        runstate.wetland_flood_countdown = WETLAND_FLOOD_INTERVAL_TICKS
        _log_event("unlock", "Wetland Forest unlocked", None)


def wetland_plot_coordinate_label(index):
    row, col = divmod(index, WETLAND_COLS)
    return f"{chr(ord('A') + col)}{row + 1}"


def wetland_standing_value():
    return sum(plot.value for plot in runstate.wetland_plots)


# GB-24 (2026-10-09): tides. Every WETLAND_TIDE_HALF_TICKS the tide turns and the two halves of the wetland (a chessboard
# split) swap between under water and dry, so exactly half the plots are flooded at any moment. A bare dry plot takes a
# normal seedling, a bare flooded plot can only take a mangrove, which recovers fast and is immune to the big flood.
# Standing mangroves bring wetland wildlife into the Almanac. Pure function of the tick, so nothing is saved.
WETLAND_TIDE_HALF_TICKS = 6
MANGROVES_FOR_HERON = 3


def wetland_tide_high(tick=None):
    tick = runstate.forest_tick if tick is None else tick
    return (tick // WETLAND_TIDE_HALF_TICKS) % 2 == 1


def wetland_plot_flooded(index, tick=None):
    row, col = divmod(index, WETLAND_COLS)
    return (row + col) % 2 == (1 if wetland_tide_high(tick) else 0)


def wetland_ticks_to_tide_turn(tick=None):
    tick = runstate.forest_tick if tick is None else tick
    return WETLAND_TIDE_HALF_TICKS - (tick % WETLAND_TIDE_HALF_TICKS)


def wetland_tide_text():
    flooded = ", ".join(wetland_plot_label_safe(i) for i in range(len(runstate.wetland_plots)) if wetland_plot_flooded(i))
    turn = wetland_ticks_to_tide_turn()
    return (f"Tide: {'high' if wetland_tide_high() else 'low'}, turning in {turn} tick{'s' if turn != 1 else ''}. "
            f"Under water now: {flooded or 'none'}. Plant mangroves on flooded plots and seedlings on dry ones.")


def wetland_plot_label_safe(index):
    return wetland_plot_coordinate_label(index)


def standing_mangroves():
    return [p for p in runstate.wetland_plots if p.state in ACCRUING_STATES and p.species == SPECIES_MANGROVE]


def wetland_wildlife_entries():
    """Almanac entries for the tidal wildlife a mangrove stand attracts: (icon, name, found, hint)."""
    found_heron = "heron" in wetland_wildlife_found or len(standing_mangroves()) >= MANGROVES_FOR_HERON
    found_crab = "crab" in wetland_wildlife_found or any(p.ticks_intact >= MATURITY_TICKS for p in standing_mangroves())
    return [("\U0001F9A9", "Tidal heron", found_heron, ""), ("\U0001F980", "Mangrove crab", found_crab, "")]


def note_wetland_wildlife():
    """Remembers wildlife once found (a later flood or clear does not take it back out of the Almanac)."""
    for _icon, name, found, _hint in wetland_wildlife_entries():
        if found:
            wetland_wildlife_found.add("heron" if "heron" in name else "crab")


wetland_wildlife_found = set()


def wetland_flood_loss_fraction(plot):
    """Share of a standing plot's value the next flood would strip: mature
    plots (a full MATURITY_TICKS intact) hold the water back far better
    than young ones. 0.0 for a plot holding no standing value."""
    if plot.state not in ACCRUING_STATES or plot.species == SPECIES_MANGROVE:  # GB-24: mangroves hold the water back
        return 0.0
    return WETLAND_FLOOD_LOSS_MATURE if plot.ticks_intact >= MATURITY_TICKS else WETLAND_FLOOD_LOSS_YOUNG


def wetland_flood_warning_active():
    return runstate.wetland_unlocked and runstate.wetland_flood_countdown <= WETLAND_FLOOD_WARNING_TICKS


def apply_wetland_flood():
    """Sweeps every wetland plot once. Returns the total value stripped."""
    lost = 0.0
    for plot in runstate.wetland_plots:
        if plot.state in ACCRUING_STATES:
            loss = plot.value * wetland_flood_loss_fraction(plot)
            plot.value -= loss
            lost += loss
        elif plot.state == REPLANTING:
            plot.replant_ticks_remaining = min(
                RECOVERY_TICKS, plot.replant_ticks_remaining + WETLAND_FLOOD_SILT_TICKS
            )
    runstate.wetland_floods_survived += 1
    runstate.wetland_flood_value_lost += lost
    _log_event("flood", f"Wetland flood: {lost:.1f} standing value swept away", None)
    return lost


def _advance_wetland_tick():
    """One tick of the wetland: grow/recover every plot, then run the flood
    timer. Only called once the region is unlocked."""
    for plot in runstate.wetland_plots:
        plot.accrue_tick()
        plot.advance_recovery()
    runstate.wetland_flood_countdown -= 1
    if runstate.wetland_flood_countdown <= 0:
        apply_wetland_flood()
        runstate.wetland_flood_countdown = WETLAND_FLOOD_INTERVAL_TICKS


def _wetland_tooltip_text(plot):
    soil_pct = round(plot.productivity_multiplier() * 100)
    label = f"{wetland_plot_coordinate_label(plot.index)} · {STATE_LABEL[plot.state]} · value {plot.value:.1f} · soil {soil_pct}%"
    if plot.state == REPLANTING:
        label += f" · recovering in {plot.replant_ticks_remaining} ticks"
    loss = wetland_flood_loss_fraction(plot)
    if loss:
        label += f" · flood would cost {round(loss * 100)}%"
    if plot.species == SPECIES_MANGROVE:
        label += " · mangrove (flood-proof)"
    label += " · under water now" if wetland_plot_flooded(plot.index) else " · dry now"
    return label


def render_wetland_panel():
    state_el = document.getElementById("wetland-selected-plot-state")
    clear_button = document.getElementById("wetland-clear-button")
    replant_button = document.getElementById("wetland-replant-button")

    mangrove_button = document.getElementById("wetland-mangrove-button")  # GB-24
    if runstate.wetland_selected_index is None:
        state_el.innerText = "No plot selected"
        clear_button.disabled = True
        replant_button.disabled = True
        if mangrove_button is not None:
            mangrove_button.disabled = True
        return

    plot = runstate.wetland_plots[runstate.wetland_selected_index]
    detail = f"value {plot.value:.1f}"
    if plot.state == REPLANTING:
        detail = f"recovering in {plot.replant_ticks_remaining} ticks"
    state_el.innerText = (
        f"Plot {wetland_plot_coordinate_label(runstate.wetland_selected_index)}: {STATE_LABEL[plot.state]} ({detail})"
    )
    clear_button.disabled = "clear" not in VALID_ACTIONS[plot.state]
    flooded = wetland_plot_flooded(runstate.wetland_selected_index)
    replant_button.disabled = "replant" not in VALID_ACTIONS[plot.state] or flooded
    replant_button.title = "Under water: only a mangrove can be planted now" if flooded else "Replant with a normal seedling (dry plots only)"
    if mangrove_button is not None:
        mangrove_button.disabled = "replant" not in VALID_ACTIONS[plot.state] or not flooded
        mangrove_button.title = "Plant a mangrove (flooded plots only)" if flooded else "Dry now: wait for the tide to turn to plant a mangrove here"


def wetland_flood_status_text():
    if wetland_flood_warning_active():
        return f"🌊 Flood warning — water arrives in {runstate.wetland_flood_countdown} ticks. Young plots (highlighted) would lose {round(WETLAND_FLOOD_LOSS_YOUNG * 100)}%."
    return f"Next flood in {runstate.wetland_flood_countdown} ticks · floods survived: {runstate.wetland_floods_survived}"


def render_wetland_stats():
    document.getElementById("wetland-income-display").innerText = f"Harvested income: {fmt_num(runstate.wetland_income)}"
    document.getElementById("wetland-standing-value-display").innerText = (
        f"Standing wetland value: {fmt_num(wetland_standing_value())}"
    )
    document.getElementById("wetland-flood-status").innerText = wetland_flood_status_text() + " " + wetland_tide_text()
