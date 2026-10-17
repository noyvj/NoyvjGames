"""Rare wildlife, milestone tiers and forest titles, chain bloom, and the Forest Almanac."""

from js import document

import canopy_runstate as runstate
from canopy_challenge import render_challenge_badges
from canopy_forestlog import WILDLIFE_SPECIES, _rare_entry, species_seen
from canopy_helpers import _el, _flash_forest_pulse, _forest_display_name, _gb_toast, _log_event, _plot_ref
from canopy_regions import wetland_wildlife_entries
from canopy_rules import ACCRUING_STATES, SEASONS, SEASON_ICON, SEASON_LABEL, species_planted
from canopy_valuation import _peak_now, seasons_survived
from canopy_weather import is_dusk_window
from canopy_worldvars import (
    BIODIVERSITY_FULL_SCORE, CHAIN_BLOOM_MAX_RANK, CHAIN_BLOOM_MIN_PLOTS, CHAIN_BLOOM_WINDOW_TICKS,
    RARE_FOX_DECLINED_REQUESTS, RARE_STAG_MIN_FRACTION, RARE_WILDLIFE, STANDING_TIERS, _pending_bloom,
)


# --- GB-20: rare wildlife ------------------------------------------------------------------------


def biodiversity_fraction(plot):
    return min(1.0, plot.biodiversity / BIODIVERSITY_FULL_SCORE)


def _ghost_stag_plot_index():
    """The plot the ghost stag would be standing on right now, or None."""
    if not is_dusk_window():
        return None
    for plot in runstate.plots:
        if plot.state in ACCRUING_STATES and biodiversity_fraction(plot) >= RARE_STAG_MIN_FRACTION:
            return plot.index
    return None


def declined_clear_requests_total():
    """Every declined clear request across the forest (each bumps its plot's
    requests_survived, which never resets)."""
    return sum(plot.requests_survived for plot in runstate.plots)


def _found_rare(rare_id, plot_index=None):
    icon, name = _rare_entry(rare_id)[1:3]
    runstate.rare_wildlife_found.append(rare_id)
    if rare_id == "ghost_stag":
        text = f"{icon} A ghost stag stepped out of the dusk at {_plot_ref(plot_index)} and was gone by morning"
    else:
        text = f"{icon} A wary fox watched from the treeline, drawn by a forest that keeps its ground"
    _log_event("rare", text, plot_index)
    _gb_toast(f"{icon} Rare sighting: {name}. It has been added to your wildlife log.")


def _check_rare_wildlife():
    if "ghost_stag" not in runstate.rare_wildlife_found:
        stag_plot = _ghost_stag_plot_index()
        if stag_plot is not None:
            _found_rare("ghost_stag", stag_plot)
    if "wary_fox" not in runstate.rare_wildlife_found and declined_clear_requests_total() >= RARE_FOX_DECLINED_REQUESTS:
        _found_rare("wary_fox")


# --- GB-22: standing value tiers --------------------------------------------------------------------

def forest_title():
    return STANDING_TIERS[runstate.milestone_tier - 1][1] if runstate.milestone_tier > 0 else ""


def _tiers_reached_for(peak):
    return sum(1 for threshold, _title in STANDING_TIERS if peak >= threshold)


def _check_milestones(celebrate=True):
    """Tracks the best standing value this session and celebrates each tier
    (1k Seedling, 2.5k Grove, 5k Woodland, 10k Old-Growth) once."""
    runstate.peak_standing_value = _peak_now()
    reached = _tiers_reached_for(runstate.peak_standing_value)
    if reached <= runstate.milestone_tier:
        return
    old = runstate.milestone_tier
    runstate.milestone_tier = reached
    for i in range(old, reached):
        threshold, title = STANDING_TIERS[i]
        _log_event("milestone", f"{_forest_display_name()} grew into a {title} forest ({threshold:,.0f} standing value)")
    if celebrate:
        threshold, title = STANDING_TIERS[reached - 1]
        _gb_toast(f"\U0001F332 {_forest_display_name()} is now a {title} forest ({threshold:,.0f} standing value)")
        _flash_forest_pulse()


def render_forest_title():
    element = _el("forest-title-display")
    if element is None:
        return
    title = forest_title()
    element.hidden = not (title or runstate.forest_name)
    label = f"{runstate.forest_name}, " if runstate.forest_name else ""
    element.innerText = f"Forest: {label}{title} tier" if title else f"Forest: {runstate.forest_name}"


# --- GB-27: chain bloom -------------------------------------------------------------------------------------

def _register_chain_bloom(new_indices):
    """Plots reaching full maturity within CHAIN_BLOOM_WINDOW_TICKS of each
    other ripple their leaf bursts across the grid in order, each one bigger
    and later than the last (juice only: it changes no number)."""
    runstate._recent_matures = [(t, i) for t, i in runstate._recent_matures if runstate.forest_tick - t < CHAIN_BLOOM_WINDOW_TICKS]
    runstate._recent_matures.extend((runstate.forest_tick, i) for i in sorted(new_indices))
    if len(runstate._recent_matures) < CHAIN_BLOOM_MIN_PLOTS:
        return
    for position, (_tick, index) in enumerate(runstate._recent_matures):
        _pending_bloom[index] = min(position, CHAIN_BLOOM_MAX_RANK)


# --- GB-28: Forest Almanac ------------------------------------------------------------------------------------

ALMANAC_TREES = [
    ("evergreen", "\U0001F332", "Evergreen stand", lambda: True),
    ("seedling", "\U0001F331", "Replanted seedling", lambda: runstate.total_replants >= 1),
    ("deciduous", "\U0001F333", "Recovered woodland", lambda: runstate.total_recoveries >= 1),
    ("crown", "\U0001F451", "Old-growth crown", lambda: any(p.mature_celebrated for p in runstate.plots)),
    ("pine", "\u25b2", "Pioneer pine", lambda: "pine" in species_planted),  # GB-6
    ("oak", "\u25cf", "Hardwood oak", lambda: "oak" in species_planted),
    ("orchard", "\u25c6", "Orchard", lambda: "orchard" in species_planted),
]


def almanac_sections():
    """The Almanac as data: [(title, [(icon, name, found, hint), ...])]. Trees
    and wildlife show a silhouette until found; rare wildlife and hidden
    structures show '???' as their name."""
    seen_names = {name for _icon, name in species_seen()}
    trees = [(icon, name, bool(cond()), "") for _id, icon, name, cond in ALMANAC_TREES]
    wildlife = [(icon, name, name in seen_names, "") for icon, name in WILDLIFE_SPECIES]
    rare = [(icon, name, rid in runstate.rare_wildlife_found, hint) for rid, icon, name, hint in RARE_WILDLIFE]
    structures = [("\U0001F333", "Heart Tree", runstate.heart_tree_index is not None, "")]
    sections = [
        ("Trees planted", trees),
        ("Wildlife seen", wildlife),
        ("Rare wildlife", rare),
        ("Hidden structures", structures),
    ]
    if runstate.wetland_unlocked:  # GB-24: the tidal wildlife only appears once the wetland is open
        sections.append(("Tidal wildlife", wetland_wildlife_entries()))
    return sections


def almanac_found_total():
    found = total = 0
    for _title, entries in almanac_sections():
        total += len(entries)
        found += sum(1 for entry in entries if entry[2])
    return found, total


def on_toggle_almanac(event=None):
    runstate.almanac_open = not runstate.almanac_open
    render_almanac()


def render_almanac():
    toggle = _el("almanac-toggle-button")
    panel = _el("almanac-panel")
    if toggle is None or panel is None:
        return
    found, total = almanac_found_total()
    toggle.innerText = f"Hide Almanac ({found}/{total})" if runstate.almanac_open else f"\U0001F4DA Almanac ({found}/{total})"
    panel.hidden = not runstate.almanac_open
    if not runstate.almanac_open:
        return
    panel.innerHTML = ""
    title = document.createElement("h2")
    title.className = "almanac-title"
    title.innerText = f"Forest Almanac: {runstate.forest_name}" if runstate.forest_name else "Forest Almanac"
    panel.appendChild(title)

    for section_title, entries in almanac_sections():
        heading = document.createElement("h3")
        heading.className = "almanac-heading"
        heading.innerText = f"{section_title} ({sum(1 for e in entries if e[2])}/{len(entries)})"
        panel.appendChild(heading)
        row = document.createElement("ul")
        row.className = "almanac-list"
        for icon, name, is_found, _hint in entries:
            item = document.createElement("li")
            item.className = "almanac-item almanac-item--found" if is_found else "almanac-item almanac-item--unfound"
            shown = name if is_found else "???"
            item.setAttribute("aria-label", f"{name}: found" if is_found else f"{section_title}: not yet found")
            glyph = document.createElement("span")
            glyph.className = "almanac-icon" if is_found else "almanac-icon almanac-silhouette"
            glyph.setAttribute("aria-hidden", "true")
            # Hidden structures give away nothing before they are found: no silhouette either.
            glyph.innerText = "" if (section_title == "Hidden structures" and not is_found) else icon
            item.appendChild(glyph)
            text = document.createElement("span")
            text.className = "almanac-name"
            text.innerText = shown
            item.appendChild(text)
            row.appendChild(item)
        panel.appendChild(row)

    seasons_heading = document.createElement("h3")
    seasons_heading.className = "almanac-heading"
    seasons_heading.innerText = f"Seasons survived: {seasons_survived()}"
    panel.appendChild(seasons_heading)
    seasons_row = document.createElement("ul")
    seasons_row.className = "almanac-list"
    for k, season in enumerate(SEASONS):
        done = seasons_survived() > k
        item = document.createElement("li")
        item.className = "almanac-item almanac-item--found" if done else "almanac-item almanac-item--unfound"
        item.setAttribute("aria-label", f"{SEASON_LABEL[season]}: {'lived through' if done else 'not yet lived through'}")
        glyph = document.createElement("span")
        glyph.className = "almanac-icon" if done else "almanac-icon almanac-silhouette"
        glyph.setAttribute("aria-hidden", "true")
        glyph.innerText = SEASON_ICON[season]
        item.appendChild(glyph)
        text = document.createElement("span")
        text.className = "almanac-name"
        text.innerText = SEASON_LABEL[season] if done else "???"
        item.appendChild(text)
        seasons_row.appendChild(item)
    panel.appendChild(seasons_row)
    streak_line = document.createElement("p")
    streak_line.className = "almanac-note"
    streak_line.innerText = f"Perfect Season streak: {runstate.perfect_streak}"
    panel.appendChild(streak_line)
    render_challenge_badges(panel)  # GB-17
