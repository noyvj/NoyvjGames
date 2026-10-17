"""Plot tile colours, tooltips, tile marks and the stats panel render (render_grid itself is in canopy_renderer)."""

from js import document

import canopy_runstate as runstate
from canopy_clearcut import soil_dip_text
from canopy_effects import clear_cut_dip_fraction, current_degrade_per_clear
from canopy_helpers import plot_coordinate_label
from canopy_rules import (
    BARE, MIN_PRODUCTIVITY_MULTIPLIER, REPLANTING, SPECIALIZATION_LABEL, STATE_LABEL, VALID_ACTIONS,
)


# REVIEW(reuse): byte-identical implementation in games/herd/game.py.
# Low urgency at only 2 occurrences, but worth a shared color-utility module
# if a third game ever needs a hex-color lerp.
def _lerp_color(start_hex, end_hex, t):
    """Linear-interpolates between two #rrggbb colors at t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(start_hex[1:3], 16), int(start_hex[3:5], 16), int(start_hex[5:7], 16)
    r2, g2, b2 = int(end_hex[1:3], 16), int(end_hex[3:5], 16), int(end_hex[5:7], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


# Gradient endpoints per state — bare stays flat (soil, not growth), the
# other two states gradient from a light/young color toward a deep,
# mature one as maturity_fraction() rises.
BARE_COLOR = "#6d4c31"
REPLANTING_START_COLOR = "#9c7a3c"
REPLANTING_END_COLOR = "#8bc34a"
GROWING_START_COLOR = "#8bc34a"
GROWING_END_COLOR = "#1b5e20"


def plot_display_color(plot):
    if plot.state == BARE:
        return BARE_COLOR
    if plot.state == REPLANTING:
        return _lerp_color(REPLANTING_START_COLOR, REPLANTING_END_COLOR, plot.maturity_fraction())
    return _lerp_color(GROWING_START_COLOR, GROWING_END_COLOR, plot.maturity_fraction())


def soil_hint_text(plot):
    """B12: plain-language explanation behind the soil-quality percentage.
    Soil quality is the plot's productivity multiplier: each clear cuts it
    permanently, and standing value grows in proportion to it."""
    pct = round(plot.productivity_multiplier() * 100)
    floor_pct = round(MIN_PRODUCTIVITY_MULTIPLIER * 100)
    step_pct = round(current_degrade_per_clear() * 100)
    return (
        f"Soil quality: this plot's future value grows at {pct}% of the rate of a never-cleared plot. "
        f"Every clear permanently costs {step_pct} points (never below {floor_pct}%), and replanting "
        "does not restore it."
        + (f" Right now it is also down {round(clear_cut_dip_fraction(plot) * 100)} points from a clear-cut, which heals by itself ({soil_dip_text(plot)})." if plot.soil_dip_ticks > 0 else "")
    )


def _plot_tooltip_text(plot):
    """B8: the exact numeric value + degradation level behind a plot tile,
    surfaced via a data attribute a small vanilla-JS listener in index.html
    reads on hover/tap (see that file -- positioning a tooltip near the
    cursor is plain DOM/event work with no game-state logic of its own, so
    it's a documented exception rather than round-tripping through
    Pyodide). Coordinate label first (B4) so the tooltip reads as "which
    plot, in what state, worth what" in one line."""
    soil_pct = round(plot.productivity_multiplier() * 100)
    label = f"{plot_coordinate_label(plot.index)} · {STATE_LABEL[plot.state]} · value {plot.value:.1f} · soil {soil_pct}%"
    if plot.state == REPLANTING:
        label += f" · recovering in {plot.replant_ticks_remaining} ticks"
    if plot.is_veteran():
        label += f" · veteran ({plot.requests_survived} requests survived)"
    if plot.specialization:
        label += f" · {SPECIALIZATION_LABEL[plot.specialization]} specialist"
    if plot.index == runstate.adopted_plot_index:
        label += " · adopted"
        if runstate.adopted_plot_nickname:
            label += f" as {runstate.adopted_plot_nickname}"
    return label


# B20: the floating "+X" pop varies by size only (font size + float
# distance in style.css), never by hue, so it adds no color-only meaning
# (consistent with the site's colorblind audit). Thresholds sit against a
# plot's real per-tick delta (~1.05 on a fresh plot, growing ~0.05/tick).
VALUE_POP_MEDIUM_DELTA = 2.0
VALUE_POP_LARGE_DELTA = 4.0


def _value_pop_size_class(delta):
    if delta >= VALUE_POP_LARGE_DELTA:
        return "value-pop--large"
    if delta >= VALUE_POP_MEDIUM_DELTA:
        return "value-pop--medium"
    return "value-pop--small"


LEAF_BURST_COUNT = 6


# B-17 (2026-10-09): visual refresh. Each tile gets a layered CSS sprite (canopy, trunk, ground shadow) that shows the
# plot's growth stage, tinted by the season, with a slow sway that stops for reduced motion and performance mode. The
# state icons, hatch patterns and letters stay, so nothing relies on the sprite or on colour.
UI_PREF_SPRITES_OFF = "canopy-sprites-off"


def sprite_kind(plot):
    """tree (standing), mature (fully grown), sapling (replanting) or stump (bare)."""
    if plot.state == BARE:
        return "stump"
    if plot.state == REPLANTING:
        return "sapling"
    return "mature" if plot.maturity_fraction() >= 1.0 else "tree"


def _make_tile_mark(class_name, text):
    mark = document.createElement("span")
    mark.className = class_name
    mark.innerText = text
    return mark


def render_panel():
    panel_state_el = document.getElementById("selected-plot-state")
    clear_button = document.getElementById("clear-button")
    replant_button = document.getElementById("replant-button")

    soil_el = document.getElementById("soil-hint")
    if runstate.selected_index is None:
        panel_state_el.innerText = "No plot selected"
        clear_button.disabled = True
        replant_button.disabled = True
        soil_el.hidden = True
        return

    plot = runstate.plots[runstate.selected_index]
    detail = f"value {plot.value:.1f}"
    if plot.state == REPLANTING:
        detail = f"recovering in {plot.replant_ticks_remaining} ticks"
    panel_state_el.innerText = (
        f"Plot {plot_coordinate_label(runstate.selected_index)}: {STATE_LABEL[plot.state]} ({detail})"
    )
    soil_el.hidden = False
    soil_el.innerText = f"Soil {round(plot.productivity_multiplier() * 100)}%" + (" (healing)" if plot.soil_dip_ticks > 0 else "") + " ?"
    soil_el.title = soil_hint_text(plot)
    clear_button.disabled = "clear" not in VALID_ACTIONS[plot.state] or plot.index == runstate.heart_tree_index
    replant_button.disabled = "replant" not in VALID_ACTIONS[plot.state]
