"""Clear-cut soil dips (GB-21): healing, preview, the harvester badge and the panel."""

import canopy_runstate as runstate
from canopy_effects import clear_cut_dip_fraction, expedition_extra_heal
from canopy_helpers import _announce, _el, _gb_toast, _log_event, _plot_ref
from canopy_rules import CLEAR_CUT_DIP, CLEAR_CUT_HEAL_TICKS, SEASON_CYCLE_TICKS, VALID_ACTIONS
from canopy_valuation import BADGE_HARVESTER, BADGE_ICON, playstyle_badge


# --- GB-21: clear-cut for a quick payout ------------------------------------------------------------
# A second way to clear a standing plot, with no dice: CLEAR_CUT_BONUS more income now, in exchange for a visible,
# recoverable soil dip (CLEAR_CUT_DIP of the plot's growth) that heals in a straight line over CLEAR_CUT_HEAL_TICKS (three
# seasons), whether the plot is bare, replanting or growing again. It counts as an ordinary clear in every other way
# (the permanent soil cost per clear, the playstyle badge, contracts, Pacifist), so it is purely an extra choice. Main
# forest only; Undo works; never offered in Survey mode (a plan is Clear or Replant).
CLEAR_CUT_BONUS = 0.20


def _soil_heal_rate():
    """Ticks of dip healed per tick (the Expedition's Soil Salve doubles it)."""
    return 1 + expedition_extra_heal()


def soil_dip_text(plot):
    """'' when the plot has no dip, else a plain sentence for the tooltip and the soil hint."""
    ticks = getattr(plot, "soil_dip_ticks", 0)
    if ticks <= 0:
        return ""
    points = round(clear_cut_dip_fraction(plot) * 100)
    rate = _soil_heal_rate()
    left = -(-ticks // rate)  # ceiling: ticks until fully healed at the current rate
    seasons = left / SEASON_CYCLE_TICKS
    return f"clear-cut soil dip: down {points} points, healed in {left} ticks (about {seasons:.1f} seasons)"


def _advance_soil_dips():
    """One tick of healing on every main-forest plot; logs the moment a plot's soil is whole again."""
    rate = _soil_heal_rate()
    for plot in runstate.plots:
        if plot.soil_dip_ticks <= 0:
            continue
        plot.soil_dip_ticks = max(0, plot.soil_dip_ticks - rate)
        if plot.soil_dip_ticks == 0:
            _log_event("heal", f"The soil at {_plot_ref(plot.index)} has healed from the clear-cut", plot.index)


def clear_cut_preview(plot):
    """(payout, bonus) the clear-cut of this plot would give right now."""
    bonus = plot.value * CLEAR_CUT_BONUS
    return plot.value + bonus, bonus


def _note_harvester_badge():
    """Says so once when clear-cutting tips the forest into the Harvester playstyle badge."""
    if playstyle_badge() == BADGE_HARVESTER and not runstate._harvester_badge_announced:
        runstate._harvester_badge_announced = True
        _gb_toast(f"{BADGE_ICON[BADGE_HARVESTER]} Playstyle badge: Harvester. Quick payouts, and the soil will heal")
        _announce("Playstyle badge: Harvester")


def render_clear_cut_panel():
    button = _el("clear-cut-button")
    if button is None:
        return
    status = _el("clear-cut-status")
    plot = runstate.plots[runstate.selected_index] if runstate.selected_index is not None else None
    allowed = (
        plot is not None and not runstate.survey_mode and not plot.blocked and "clear" in VALID_ACTIONS[plot.state]
        and plot.index != runstate.heart_tree_index
    )
    button.disabled = not allowed
    if allowed:
        payout, bonus = clear_cut_preview(plot)
        button.title = (
            f"Clear-cut (K): bank {payout:.1f} income now ({bonus:.1f} more than Clear). The soil then dips "
            f"{round(CLEAR_CUT_DIP * 100)} points and heals over about {CLEAR_CUT_HEAL_TICKS // SEASON_CYCLE_TICKS} seasons. Undo works."
        )
    else:
        button.title = (
            f"Clear-cut (K): a bonus of {round(CLEAR_CUT_BONUS * 100)}% now for a soil dip that heals over about "
            f"{CLEAR_CUT_HEAL_TICKS // SEASON_CYCLE_TICKS} seasons. Select a standing plot first."
        )
    if status is not None:
        dipped = [p for p in runstate.plots if p.soil_dip_ticks > 0 and not p.blocked]
        parts = []
        if dipped:
            worst = max(p.soil_dip_ticks for p in dipped)
            parts.append(f"{len(dipped)} plot{'s' if len(dipped) != 1 else ''} healing from a clear-cut (the last in about {worst} ticks)")
        if runstate.clear_cuts_total:
            parts.append(f"{runstate.clear_cuts_total} clear-cut{'s' if runstate.clear_cuts_total != 1 else ''} so far")
        status.innerText = ". ".join(parts)
