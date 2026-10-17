"""The forest log and wildlife log lines, and the specialist and adopt panels."""

from js import document

import canopy_runstate as runstate
from canopy_helpers import plot_coordinate_label
from canopy_rules import STATE_LABEL
from canopy_worldvars import RARE_WILDLIFE


# ===========================================================================
# Forest log (B3 history timeline, B23 wildlife log, B27 adopted plot),
# playstyle badge (B9/B18) and end-of-session report card (B13). All of it
# lives inside the already-opt-in Session Summary panel (collapsible
# <details> sections) so the main screen gains no new always-visible block.
# ===========================================================================

WILDLIFE_SPECIES = [
    ("\U0001F989", "owl"),
    ("\U0001F98A", "fox"),
    ("\U0001F98C", "deer"),
    ("\U0001F438", "frog"),
    ("\U0001F98B", "butterfly"),
    ("\U0001F426", "woodpecker"),
]
FOREST_LOG_DISPLAY_LIMIT = 60


def wildlife_species_for_plot(index):
    """B23: each plot's wildlife is a fixed species (deterministic by plot
    index, no RNG anywhere in this game) so the log can name what arrived."""
    return WILDLIFE_SPECIES[index % len(WILDLIFE_SPECIES)]


def species_seen():
    """B23: the distinct species whose icons have ever appeared, in catalog
    order. Derived from plots_with_wildlife_ever, so it needs no state of its
    own."""
    seen_names = {wildlife_species_for_plot(i)[1] for i in runstate.plots_with_wildlife_ever}
    return [sp for sp in WILDLIFE_SPECIES if sp[1] in seen_names]


def forest_log_lines(limit=FOREST_LOG_DISPLAY_LIMIT, kinds=None, plot_index=None):
    """Newest-first display strings, optionally filtered by event kind(s) or
    plot."""
    entries = [
        e for e in runstate.forest_log
        if (kinds is None or e["kind"] in kinds) and (plot_index is None or e["plot"] == plot_index)
    ]
    return [f"t{e['tick']}: {e['text']}" for e in reversed(entries)][:limit]


def render_specialist_panel():
    row = document.getElementById("specialist-row")
    if row is None:
        return
    plot = runstate.plots[runstate.selected_index] if runstate.selected_index is not None else None
    row.hidden = plot is None or not plot.can_specialize()


def render_adopt_panel():
    button = document.getElementById("adopt-plot-button")
    panel = document.getElementById("adopted-plot-panel")
    if button is None or panel is None:
        return
    button.disabled = runstate.selected_index is None
    button.innerText = (
        "\u2B50 Release adopted plot" if runstate.selected_index is not None and runstate.selected_index == runstate.adopted_plot_index
        else "\u2B50 Adopt plot"
    )
    if runstate.adopted_plot_index is None:
        panel.hidden = True
        return
    panel.hidden = False
    plot = runstate.plots[runstate.adopted_plot_index]
    history = forest_log_lines(limit=8, plot_index=runstate.adopted_plot_index)
    nickname_part = f' "{runstate.adopted_plot_nickname}"' if runstate.adopted_plot_nickname else ""
    panel.innerText = (
        f"Adopted plot {plot_coordinate_label(runstate.adopted_plot_index)}{nickname_part}: {STATE_LABEL[plot.state]}, "
        f"value {plot.value:.1f}, cleared {plot.clear_count}x, soil {round(plot.productivity_multiplier() * 100)}%."
        + (" History: " + " | ".join(history) if history else "")
    )


def _rare_entry(rare_id):
    for entry in RARE_WILDLIFE:
        if entry[0] == rare_id:
            return entry
    return None
