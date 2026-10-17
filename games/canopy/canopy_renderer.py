"""render() and the functions that call each other with it (reset_session, render_grid, the region, level, vault and expedition renders and their button handlers). They form one cycle, so they live together."""

import copy

import skill_tree
from js import document
from pyodide.ffi import create_proxy

import canopy_runstate as runstate
from canopy_achievements import _sync_earned_and_toast, update_achievements_display
from canopy_almanac import _ghost_stag_plot_index, render_almanac, render_forest_title
from canopy_challenge import (
    SCENARIO_SPECS, _apply_challenge_start, _apply_scenario_start, render_challenge_status,
)
from canopy_clearcut import render_clear_cut_panel, soil_dip_text
from canopy_comfort import _coach_dismissed
from canopy_contracts import render_contracts
from canopy_effects import (
    EXPEDITION_RICH_GROWTH, EXPEDITION_THIN_GROWTH, EXPEDITION_TREE, VAULT_TREE, _expedition_effect_cache,
    expedition_terrain, vault_owned, vault_perks_active,
)
from canopy_expedition import (
    EXPEDITION_SEASONS, EXPEDITION_TERRAIN_MARK, _apply_expedition_start, _expedition_proxies,
    _new_expedition_run, expedition_bests_text, expedition_finished, expedition_map_text,
    expedition_points_earned, expedition_result_text, expedition_season, expedition_status_text,
    expedition_summary_text,
)
from canopy_forecast import (
    render_announcer, render_season_forecast, render_season_indicator, selection_announcement,
)
from canopy_forestlog import render_adopt_panel, render_specialist_panel
from canopy_gbstate import _reset_gb_state
from canopy_ghost import _bank_ghost, _reset_ghost_session
from canopy_gridview import (
    LEAF_BURST_COUNT, UI_PREF_SPRITES_OFF, _make_tile_mark, _plot_tooltip_text, _value_pop_size_class,
    plot_display_color, render_panel, sprite_kind,
)
from canopy_hazards import (
    FIRE_BURN_TICKS, _reset_fire, _reset_rival, blight_pressure, blight_status_for, easement_cost,
    fire_damp, fires, render_fire, render_rival,
)
from canopy_helpers import _announce, _el, _log_event, _plot_tile_id, _plot_tooltip_detail, soil_band, ui_pref
from canopy_infopanels import render_info_page, update_changelog_display
from canopy_labui import render_lab_banner, set_lab_values
from canopy_layout import _update_layout_best, apply_layout_to_plots, render_layout_badge
from canopy_levels import (
    LEVEL_SPECS, _active_poacher_plot, _burn_level_start, _js_window, _level_mode, _level_proxies,
    _save_meta, _set_class, _storm_exposed, _storm_warning_rows, _to_js, _vault_proxies, drive_off_poacher,
    level_lock_reason, level_number, level_status_text, next_level_id, poacher_run, spirit_line_text,
    vault_points_earned, vault_points_free,
)
from canopy_lifetime import _bank_lifetime
from canopy_plot import Plot
from canopy_plotsheet import render_plot_note_input, render_plot_sheet
from canopy_realworld import render_grid_size_select, render_real_world
from canopy_records import _bank_legacy_value, _personal_best_flashed, load_legacy_bonus
from canopy_regions import (
    _highland_tooltip_text, _wetland_tooltip_text, render_highland_panel, render_highland_stats,
    render_wetland_panel, render_wetland_stats, wetland_flood_loss_fraction, wetland_flood_warning_active,
    wetland_plot_flooded, wetland_wildlife_found,
)
from canopy_rules import (
    ACCRUING_STATES, BARE, DEGRADE_PER_CLEAR_BY_DIFFICULTY, DIFFICULTY_NORMAL, GRID_SIZE_PRESETS, RECOVERED,
    SCENARIO_NONE, SPECIES, SPECIES_MANGROVE, STARTING_COMMUNITY_RELATIONS, STATE_ICON, STATE_LABEL,
    SYNERGY_PER_NEIGHBOUR, SYNERGY_REPLANT_FACTOR, UI_PREF_SYNERGY_MARKS_OFF, _is_mature_standing, carbon,
    expedition_meta, mature_neighbour_count, species_planted,
)
from canopy_session import _KEEP_EXPEDITION, _KEEP_LAYOUT, _KEEP_LEVEL, render_reset_button
from canopy_sessionview import render_session_summary, render_stats
from canopy_stakeholders import render_stakeholder_panel, stakeholder_faces
from canopy_summary import REPLAY_START_EVERY, _replay_frames, _replay_state
from canopy_survey import render_survey
from canopy_tend import _heart_tree_aura, collect_golden_seedling, render_tend_panel, render_undo_chip
from canopy_valuation import standing_forest_value
from canopy_vault import vault_crews_text, vault_summary_text
from canopy_worldvars import (
    CHALLENGE_NONE, CHALLENGE_NO_HIGHLAND, CHALLENGE_SPECS, HIGHLAND_COLS, HIGHLAND_ROWS,
    HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD, MATURE_LETTER, PACE_NORMAL, REQUEST_PACE_FACTOR,
    RIVAL_BUYOUT_COST, STATE_LETTER, UI_PREF_PLOT_CONTRAST, UI_PREF_SOIL_OVERLAY, WETLAND_COLS,
    WETLAND_FLOOD_INTERVAL_TICKS, WETLAND_FLOOD_LOSS_YOUNG, WETLAND_ROWS,
    WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD, _pending_bloom, _pending_golden_bursts, _pending_mature_bursts,
    _pending_value_pops, _report_history, _value_history, plot_notes, request_history, rival_claims,
    rival_locked,
)


def reset_session(grid_size=None, _render_after=True, difficulty=None, challenge=None, pace=None, level=_KEEP_LEVEL, scenario=None, lab_values=None, layout=_KEEP_LAYOUT, expedition=_KEEP_EXPEDITION):
    """Rebuilds every module-level mutable global back to its fresh-start
    default, optionally at a different GRID_SIZE_PRESETS key. Always
    rebuilds `plots` from scratch (even on a same-size reset) rather than
    resetting each existing Plot in place -- simpler than maintaining two
    code paths, and correctness-equivalent since Plot.__init__ already is
    the fresh-plot state. `personal_best` (B14) is deliberately NOT reset
    here -- it's a per-browser best across every session on this device,
    not this session's own state."""

    # B15: bank this (about-to-end) session's standing value for the next
    # session's legacy bonus, then reload the multiplier so the session
    # that's about to start immediately reflects it -- not just a future
    # page load. Skipped on the very first call (plots is still empty
    # before the module has ever had a session), so there's nothing to
    # bank yet.
    if runstate.plots:
        _bank_ghost()  # Z-3e: before the session's numbers are cleared below
        _bank_lifetime()  # B-9
        _bank_legacy_value()
        runstate.legacy_multiplier = load_legacy_bonus()
    if lab_values is not None:  # B-5: switched only after the ending session was banked under its own settings
        set_lab_values(lab_values)

    _personal_best_flashed["standing_value"] = False
    _personal_best_flashed["income"] = False
    if difficulty is not None:
        if difficulty not in DEGRADE_PER_CLEAR_BY_DIFFICULTY:
            return False
        runstate.current_difficulty = difficulty
    if challenge is not None:  # GB-17
        if challenge != CHALLENGE_NONE and challenge not in CHALLENGE_SPECS:
            return False
        runstate.current_challenge = challenge
        if challenge != CHALLENGE_NONE and scenario is None:
            runstate.current_scenario = SCENARIO_NONE  # a challenge brings its own starting forest
    if scenario is not None:  # B-11
        if scenario != SCENARIO_NONE and scenario not in SCENARIO_SPECS:
            return False
        runstate.current_scenario = scenario
    if pace is not None:  # B-6
        if pace not in REQUEST_PACE_FACTOR:
            return False
        runstate.current_pace = pace
    if grid_size is not None:
        if grid_size not in GRID_SIZE_PRESETS:
            return False
        runstate.current_grid_size = grid_size
    # W-1: Reset Session keeps the running level (so it retries it); changing a setting by hand leaves the level.
    if level is not _KEEP_LEVEL:
        runstate.current_level = level
    elif grid_size is not None or difficulty is not None or challenge is not None or pace is not None or scenario is not None:
        runstate.current_level = None
    # GB-3: Reset Session retries the running Expedition on the same seed (upgrades back to none); changing a setting by
    # hand, starting a level or applying a layout leaves it; an explicit seed (start_expedition) starts a new one.
    if expedition is not _KEEP_EXPEDITION:
        runstate.current_expedition = None if expedition is None else _new_expedition_run(expedition)
    elif runstate.current_expedition is not None:
        settings_changed = (
            grid_size is not None or difficulty is not None or challenge is not None or pace is not None
            or scenario is not None or (level is not _KEEP_LEVEL and level is not None)
            or (layout is not _KEEP_LAYOUT and layout is not None)
        )
        runstate.current_expedition = None if settings_changed else _new_expedition_run(runstate.current_expedition["seed"])
    runstate.GRID_ROWS, runstate.GRID_COLS = GRID_SIZE_PRESETS[runstate.current_grid_size]
    # B-29: a layout is for one grid size and one plain game mode. Choosing one clears any scenario, challenge or level;
    # choosing one of those, or another grid size, drops it. Everything else (difficulty, pace, Reset) keeps it.
    if layout is not _KEEP_LAYOUT:
        runstate.current_layout = None if layout is None else {"name": str(layout[0])[:20], "cells": layout[1]}
        if runstate.current_layout is not None:
            runstate.current_scenario, runstate.current_challenge, runstate.current_level = SCENARIO_NONE, CHALLENGE_NONE, None
    elif runstate.current_layout is not None and (
        grid_size is not None
        or (scenario is not None and scenario != SCENARIO_NONE)
        or (challenge is not None and challenge != CHALLENGE_NONE)
        or (level is not _KEEP_LEVEL and level is not None)
    ):
        runstate.current_layout = None
    if runstate.current_layout is not None and len(runstate.current_layout["cells"]) != runstate.GRID_ROWS * runstate.GRID_COLS:
        runstate.current_layout = None

    # Same leak-prevention discipline as render_grid()'s per-render proxy
    # cleanup -- these proxies' plots are about to be dropped entirely.
    for proxy in runstate._plot_click_proxies.values():
        proxy.destroy()
    runstate._plot_click_proxies = {}

    runstate.plots = [Plot(i) for i in range(runstate.GRID_ROWS * runstate.GRID_COLS)]
    if runstate.current_layout is not None:  # B-29
        apply_layout_to_plots(runstate.current_layout["cells"])
    runstate.selected_index = None
    runstate.total_income = 0.0
    runstate.community_relations = STARTING_COMMUNITY_RELATIONS
    runstate.pending_stakeholder_request = None
    runstate._ticks_since_last_request = 0
    runstate._stakeholder_request_count = 0
    runstate.total_replants = 0
    runstate.total_recoveries = 0
    runstate.plots_with_wildlife_ever = set()
    runstate.stakeholder_grants_count = 0
    runstate.stakeholder_declines_count = 0
    runstate.community_relations_min_ever = STARTING_COMMUNITY_RELATIONS
    runstate._previously_earned_ids = set()
    runstate._session_ticks = 0
    _value_history.clear()
    _report_history.clear()
    _reset_ghost_session()  # Z-3e
    _replay_frames.clear()  # B-3
    blight_pressure.clear()  # GB-7
    _reset_fire()  # GB-1
    _reset_rival()  # GB-12
    species_planted.clear()  # GB-6
    _replay_state["every"] = REPLAY_START_EVERY
    _pending_mature_bursts.clear()
    runstate.forest_log = []
    request_history.clear()
    stakeholder_faces.clear()  # GB-25
    carbon.update({"credits": 0.0, "slump": 0, "sold": 0.0, "earned_from_sales": 0.0})  # GB-29
    plot_notes.clear()
    _coach_dismissed.clear()
    _coach_dismissed.clear()
    runstate.forest_tick = 0
    runstate.adopted_plot_index = None
    _reset_gb_state()
    _apply_challenge_start()  # GB-17: Scorched Start burns the plots just built
    _apply_scenario_start()  # B-11
    _burn_level_start()  # W-1: some levels begin with part of the forest bare
    _apply_expedition_start()  # GB-3: the seed's map (rich and thin soil, a few bare plots)

    for proxy in runstate._highland_plot_click_proxies.values():
        proxy.destroy()
    runstate._highland_plot_click_proxies = {}
    runstate.highland_unlocked = False
    runstate.highland_plots = [Plot(i, region="highland") for i in range(HIGHLAND_ROWS * HIGHLAND_COLS)]
    runstate.highland_selected_index = None
    runstate.highland_income = 0.0

    for proxy in runstate._wetland_plot_click_proxies.values():
        proxy.destroy()
    runstate._wetland_plot_click_proxies = {}
    runstate.wetland_unlocked = False
    runstate.wetland_plots = [Plot(i, region="wetland") for i in range(WETLAND_ROWS * WETLAND_COLS)]
    runstate.wetland_selected_index = None
    runstate.wetland_income = 0.0
    runstate.wetland_flood_countdown = WETLAND_FLOOD_INTERVAL_TICKS
    runstate.wetland_floods_survived = 0
    runstate.wetland_flood_value_lost = 0.0
    wetland_wildlife_found.clear()  # GB-24

    if _render_after:
        render()
    return True


def render_grid():
    grid_el = document.getElementById("plot-grid")
    grid_el.innerHTML = ""
    # B16: lets the plain-JS arrow-key handler in index.html know the grid
    # width without hardcoding it a second time in JS.
    grid_el.setAttribute("data-cols", str(runstate.GRID_COLS))
    # B13: style.css's `.plot-grid` rule hardcodes `repeat(6, 1fr)` for the
    # "normal" grid shape; an inline style here overrides it (inline style
    # always wins over any class rule, no cascade tricks needed) so the
    # "large" (9x8) preset actually lays out 8 columns instead of silently
    # wrapping at 6. Found live in a real browser -- the fake-DOM pytest
    # suite has no CSS engine to catch a purely visual layout bug like
    # this one.
    grid_el.style.gridTemplateColumns = f"repeat({runstate.GRID_COLS}, 1fr)"
    heart_aura = _heart_tree_aura()
    stag_plot = _ghost_stag_plot_index() if "ghost_stag" in runstate.rare_wildlife_found else None
    poacher_plot = _active_poacher_plot()
    storm_rows = _storm_warning_rows()
    contrast_on = ui_pref(UI_PREF_PLOT_CONTRAST) == "true"  # B-8
    soil_on = ui_pref(UI_PREF_SOIL_OVERLAY) == "true"  # B-10
    for plot in runstate.plots:
        tile = document.createElement("button")
        tile.id = _plot_tile_id(plot.index)
        if plot.blocked:  # B-29: open ground in a custom layout; nothing to select, grow or count
            tile.className = "plot-tile plot-blocked"
            tile.disabled = True
            tile.title = "Open ground: not part of this layout"
            tile.setAttribute("aria-label", "Open ground, not part of this layout")
            grid_el.appendChild(tile)
            continue
        tile.className = f"plot-tile plot-{plot.state}"
        if plot.index == runstate.selected_index:
            tile.className += " plot-selected"
        if plot.just_recovered:
            tile.className += " plot-just-recovered"
            plot.just_recovered = False
        # B19: a distinct "fully mature" cap-off visual once a Recovered
        # plot's maturity_fraction() caps out -- the hope-angle payoff that
        # recovery doesn't just reach parity, it visibly finishes.
        if plot.state == RECOVERED and plot.maturity_fraction() >= 1.0:
            tile.className += " plot-fully-mature"
        tile.title = STATE_LABEL[plot.state]
        tile.innerText = STATE_ICON[plot.state]
        note = plot_notes.get(plot.index)
        if note:  # B-24
            tile.className += " plot-has-note"
            tile.title += f" \u2014 note: {note}"
            tile.appendChild(_make_tile_mark("note-mark", "\u2022"))
        if plot.has_wildlife():
            tile.className += " plot-has-wildlife"
        mature_standing = plot.state in ACCRUING_STATES and plot.maturity_fraction() >= 1.0
        if mature_standing:
            tile.className += " plot-mature"
        if plot.is_veteran():
            tile.className += " plot-veteran"
            tile.appendChild(_make_tile_mark("veteran-mark", "\U0001F396\ufe0f"))
        if plot.index == runstate.adopted_plot_index:
            tile.className += " plot-adopted"
            tile.appendChild(_make_tile_mark("adopted-mark", "\u2B50"))
        bloom_rank = _pending_bloom.pop(plot.index, None)  # GB-27: one-shot, ripples in rank order
        golden_burst = plot.index in _pending_golden_bursts  # GB-2: reuses the B4 burst
        _pending_golden_bursts.discard(plot.index)
        if plot.index in _pending_mature_bursts or bloom_rank is not None or golden_burst:
            tile.className += " plot-mature-burst"
            if bloom_rank is not None:
                tile.className += f" plot-chain-bloom plot-chain-bloom-{bloom_rank}"
            for n in range(LEAF_BURST_COUNT):
                leaf = _make_tile_mark("leaf-burst", "\U0001F343")
                leaf.className = f"leaf-burst leaf-burst--{n}"
                tile.appendChild(leaf)
        if plot.soil_dip_ticks > 0:  # GB-21: a down-arrow mark and a dashed edge, so the dip never relies on colour
            tile.className += " plot-soil-dip"
            dip_mark = _make_tile_mark("soil-dip-mark", "\u2193")
            dip_mark.setAttribute("aria-hidden", "true")
            tile.appendChild(dip_mark)
        if plot.tend_ticks_left > 0:  # GB-4
            tile.className += " plot-tended"
            tile.appendChild(_make_tile_mark("tend-mark", "\U0001F33F"))
        if plot.index == runstate.heart_tree_index:  # GB-8: no legend entry, no hint
            tile.className += " plot-heart-tree"
            tile.appendChild(_make_tile_mark("heart-tree-aura", ""))
            tile.appendChild(_make_tile_mark("heart-tree-mark", "\U0001F49A"))
        elif plot.index in heart_aura:
            tile.className += " plot-heart-aura"
        if runstate.golden_seedling is not None and runstate.golden_seedling["plot"] == plot.index:  # GB-2
            tile.className += " plot-golden-seedling"
            tile.appendChild(_make_tile_mark("golden-seedling-mark", "\u2728\U0001F331"))
        if plot.index == poacher_plot:  # GB-13: a poacher is working on this plot
            tile.className += " plot-poacher"
            tile.appendChild(_make_tile_mark("poacher-mark", "\U0001FA93"))
        if plot.index // runstate.GRID_COLS in storm_rows:  # GB-15: the storm front's band, shown before it arrives
            tile.className += " plot-storm-warning"
            tile.appendChild(_make_tile_mark("storm-mark", "⛈️"))
        if plot.index == stag_plot:  # GB-20
            tile.className += " plot-ghost-stag"
            tile.appendChild(_make_tile_mark("ghost-stag-mark", "\U0001F98C"))
        tile.style.backgroundColor = plot_display_color(plot)
        if ui_pref(UI_PREF_SPRITES_OFF) != "true":  # B-17: a small tree drawn in CSS behind the icon
            tile.appendChild(_make_tile_mark(f"tile-sprite tile-sprite--{sprite_kind(plot)}", ""))
        if contrast_on:  # B-8: a letter on every tile so state reads without the green gradient
            tile.className += " plot-contrast"
            letter = MATURE_LETTER if mature_standing else STATE_LETTER[plot.state]
            letter_mark = _make_tile_mark("state-letter", letter)
            letter_mark.setAttribute("aria-hidden", "true")
            tile.appendChild(letter_mark)
        if soil_on:  # B-10: soil quality as a coloured border band and a number
            soil_pct, band = soil_band(plot)
            tile.className += f" plot-soil plot-soil--{band}"
            soil_mark = _make_tile_mark("soil-badge", str(soil_pct))
            soil_mark.setAttribute("aria-hidden", "true")
            tile.appendChild(soil_mark)
        tooltip = _plot_tooltip_text(plot)
        terrain = expedition_terrain.get(plot.index) if runstate.current_expedition is not None else None
        if terrain:  # GB-3: the map's soil, as a triangle mark and words (never colour alone)
            tile.className += f" plot-terrain plot-terrain--{terrain}"
            terrain_mark = _make_tile_mark("terrain-mark", EXPEDITION_TERRAIN_MARK[terrain])
            terrain_mark.setAttribute("aria-hidden", "true")
            tile.appendChild(terrain_mark)
            tooltip += (
                f" \u00b7 rich soil (Expedition map): grows {round((EXPEDITION_RICH_GROWTH - 1) * 100)}% faster" if terrain == "rich"
                else f" \u00b7 thin soil (Expedition map): grows {round((1 - EXPEDITION_THIN_GROWTH) * 100)}% slower"
            )
        if plot.index in fires:  # GB-1: a flame glyph and a solid outline, so fire never relies on colour
            tile.className += " plot-burning"
            fire_mark = _make_tile_mark("fire-mark", "\U0001F525")
            fire_mark.setAttribute("aria-hidden", "true")
            tile.appendChild(fire_mark)
            tooltip += f" \u00b7 BURNING ({FIRE_BURN_TICKS - fires[plot.index]} ticks left): select it and press Dampen"
        elif runstate.fire_warning is not None and runstate.fire_warning["plot"] == plot.index:
            tile.className += " plot-smoke"
            smoke_mark = _make_tile_mark("fire-mark", "\U0001F4A8")
            smoke_mark.setAttribute("aria-hidden", "true")
            tile.appendChild(smoke_mark)
            tooltip += f" \u00b7 smoke: a spark in {runstate.fire_warning['ticks_left']} ticks"
        elif fire_damp.get(plot.index, 0) > 0:
            tooltip += f" \u00b7 damp: safe from fire for {fire_damp[plot.index]} ticks"
        if runstate.rival_notice is not None and runstate.rival_notice["plot"] == plot.index:  # GB-12: a flag glyph and a dotted outline
            tile.className += " plot-bid"
            tile.appendChild(_make_tile_mark("rival-mark", "\U0001F6A9"))
            tooltip += f" \u00b7 Halloran Timber Co. takes this in {runstate.rival_notice['ticks_left']} ticks: lock it with an easement ({easement_cost(plot.index):.1f})"
        elif plot.index in rival_claims:
            tile.className += " plot-claimed"
            tile.appendChild(_make_tile_mark("rival-mark", "\u26CF\ufe0f"))
            tooltip += f" \u00b7 mining claim ({rival_claims[plot.index]} ticks left): buy it out ({RIVAL_BUYOUT_COST:.0f}) or wait"
        elif plot.index in rival_locked:
            tile.className += " plot-easement"
            tile.appendChild(_make_tile_mark("rival-mark", "\U0001F512"))
            tooltip += " \u00b7 under a conservation easement"
        links = mature_neighbour_count(plot) if _is_mature_standing(plot) else 0  # GB-5
        if links:
            bonus_pct = round(SYNERGY_PER_NEIGHBOUR * links * 100)
            tooltip += f" \u00b7 canopy link: +{bonus_pct}% growth from {links} mature neighbour{'s' if links != 1 else ''}"
            if ui_pref(UI_PREF_SYNERGY_MARKS_OFF) != "true":
                tile.className += " plot-linked"
                link_mark = _make_tile_mark("link-mark", "+link")
                link_mark.setAttribute("aria-hidden", "true")
                tile.appendChild(link_mark)
        elif plot.state == BARE and mature_neighbour_count(plot):
            tooltip += f" \u00b7 a mature neighbour: replants {round((1 - SYNERGY_REPLANT_FACTOR) * 100)}% faster"
        if plot.species and plot.state != BARE:  # GB-6: a shape mark and a name, so species never rely on colour
            tile.className += f" plot-species plot-species--{plot.species}"
            species_mark = _make_tile_mark("species-mark", SPECIES[plot.species]["mark"])
            species_mark.setAttribute("aria-hidden", "true")
            tile.appendChild(species_mark)
            tooltip += f" \u00b7 {SPECIES[plot.species]['label']}"
            blight_note = blight_status_for(plot.index)  # GB-7
            if blight_note:
                tile.className += " plot-blight"
                tooltip += f" \u00b7 {blight_note}"
        if runstate.golden_seedling is not None and runstate.golden_seedling["plot"] == plot.index:
            tooltip += " \u00b7 golden seedling: click it now for a burst of recovery"
        if plot.tend_ticks_left > 0:
            tooltip += f" \u00b7 tended ({plot.tend_ticks_left} ticks left)"
        if plot.soil_dip_ticks > 0:  # GB-21
            tooltip += f" \u00b7 {soil_dip_text(plot)}"
        if plot.index == poacher_plot:
            tooltip += f" \u00b7 POACHER: click this plot or press P within {poacher_run['ticks_left']} ticks"
        if plot.index // runstate.GRID_COLS in storm_rows:
            tooltip += " \u00b7 a storm front is about to cross this row" + (" (a bare neighbour leaves it exposed)" if _storm_exposed(plot.index) else "")
        detail = _plot_tooltip_detail(plot)  # B-16: second line of the plot card
        tile.setAttribute("data-tooltip", tooltip + "\n" + detail)
        tile.setAttribute("aria-label", tooltip + "\n" + detail)
        # B17: a brief floating "+X" pop the tick this plot's standing
        # value actually rose, computed by tick() and consumed here once.
        pop_delta = _pending_value_pops.pop(plot.index, None)
        if pop_delta is not None:
            pop = document.createElement("span")
            pop.className = f"value-pop {_value_pop_size_class(pop_delta)}"
            pop.innerText = f"+{pop_delta:.2f}"
            tile.appendChild(pop)
        old_proxy = runstate._plot_click_proxies.pop(plot.index, None)
        if old_proxy is not None:
            old_proxy.destroy()
        proxy = create_proxy(_make_select_handler(plot.index))
        runstate._plot_click_proxies[plot.index] = proxy
        tile.addEventListener("click", proxy)
        grid_el.appendChild(tile)


def _make_highland_select_handler(index):
    def handler(event):
        highland_select_plot(index)
    return handler


def highland_select_plot(index):
    runstate.highland_selected_index = index
    render()


def render_highland_grid():
    grid_el = document.getElementById("highland-plot-grid")
    grid_el.innerHTML = ""
    grid_el.setAttribute("data-cols", str(HIGHLAND_COLS))
    # See render_grid()'s identical line for why this inline override is
    # needed on top of style.css's shared `.plot-grid` rule (B13's real-
    # browser-only bug, fixed for the main grid and applied here from the
    # start rather than repeating the same discovery).
    grid_el.style.gridTemplateColumns = f"repeat({HIGHLAND_COLS}, 1fr)"
    for plot in runstate.highland_plots:
        tile = document.createElement("button")
        tile.id = f"highland-plot-{plot.index}"
        tile.className = f"plot-tile plot-{plot.state}"
        if plot.index == runstate.highland_selected_index:
            tile.className += " plot-selected"
        if plot.just_recovered:
            tile.className += " plot-just-recovered"
            plot.just_recovered = False
        if plot.state == RECOVERED and plot.maturity_fraction() >= 1.0:
            tile.className += " plot-fully-mature"
        tile.title = STATE_LABEL[plot.state]
        tile.innerText = STATE_ICON[plot.state]
        tile.style.backgroundColor = plot_display_color(plot)
        tile.setAttribute("data-tooltip", _highland_tooltip_text(plot))
        tile.setAttribute("aria-label", _highland_tooltip_text(plot))
        old_proxy = runstate._highland_plot_click_proxies.pop(plot.index, None)
        if old_proxy is not None:
            old_proxy.destroy()
        proxy = create_proxy(_make_highland_select_handler(plot.index))
        runstate._highland_plot_click_proxies[plot.index] = proxy
        tile.addEventListener("click", proxy)
        grid_el.appendChild(tile)


def render_highland_section():
    """Shows a locked-progress banner until HIGHLAND_UNLOCK_STANDING_VALUE_
    THRESHOLD is crossed, then swaps to the actual playable section --
    same optional-reveal spirit as every other panel in this game, except
    this one *starts* inaccessible rather than merely collapsed."""
    banner = document.getElementById("highland-lock-banner")
    section = document.getElementById("highland-section")
    bar = document.getElementById("highland-unlock-progress")
    if banner is None or section is None:
        return
    if not runstate.highland_unlocked and runstate.current_challenge == CHALLENGE_NO_HIGHLAND:
        section.hidden = True
        banner.hidden = False
        bar.hidden = True
        banner.innerText = "\u26F0\ufe0f Highland Grove and Wetland Forest are sealed during the No-Highland challenge."
        return
    if not runstate.highland_unlocked:
        section.hidden = True
        banner.hidden = False
        progress = min(standing_forest_value(), HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD)
        # B6: the unlock is a visible progress bar toward the threshold,
        # not just a fraction in text.
        bar.hidden = False
        bar.max = HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD
        bar.value = progress
        banner.innerText = (
            "⛰️ Highland Grove is locked — reach "
            f"{HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD:.0f} standing forest value in your "
            f"main forest to unlock a second region ({progress:.0f}/"
            f"{HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD:.0f})."
        )
        return
    banner.hidden = True
    bar.hidden = True
    section.hidden = False
    render_highland_grid()
    render_highland_panel()
    render_highland_stats()


def _make_wetland_select_handler(index):
    def handler(event):
        wetland_select_plot(index)
    return handler


def wetland_select_plot(index):
    runstate.wetland_selected_index = index
    render()


def render_wetland_grid():
    grid_el = document.getElementById("wetland-plot-grid")
    grid_el.innerHTML = ""
    grid_el.setAttribute("data-cols", str(WETLAND_COLS))
    grid_el.style.gridTemplateColumns = f"repeat({WETLAND_COLS}, 1fr)"
    warning = wetland_flood_warning_active()
    for plot in runstate.wetland_plots:
        tile = document.createElement("button")
        tile.id = f"wetland-plot-{plot.index}"
        tile.className = f"plot-tile plot-{plot.state}"
        if plot.index == runstate.wetland_selected_index:
            tile.className += " plot-selected"
        if plot.just_recovered:
            tile.className += " plot-just-recovered"
            plot.just_recovered = False
        if plot.state == RECOVERED and plot.maturity_fraction() >= 1.0:
            tile.className += " plot-fully-mature"
        if warning and wetland_flood_loss_fraction(plot) >= WETLAND_FLOOD_LOSS_YOUNG:
            tile.className += " plot-flood-risk"
        tile.title = STATE_LABEL[plot.state]
        tile.innerText = STATE_ICON[plot.state]
        tile.style.backgroundColor = plot_display_color(plot)
        if wetland_plot_flooded(plot.index):  # GB-24: a wave glyph and a dashed lower edge, so tide never relies on colour
            tile.className += " plot-tidal"
            tile.appendChild(_make_tile_mark("tide-mark", "\u2248"))
        if plot.species == SPECIES_MANGROVE and plot.state != BARE:
            tile.className += " plot-species plot-species--mangrove"
            tile.appendChild(_make_tile_mark("species-mark", SPECIES[SPECIES_MANGROVE]["mark"]))
        tile.setAttribute("data-tooltip", _wetland_tooltip_text(plot))
        tile.setAttribute("aria-label", _wetland_tooltip_text(plot))
        old_proxy = runstate._wetland_plot_click_proxies.pop(plot.index, None)
        if old_proxy is not None:
            old_proxy.destroy()
        proxy = create_proxy(_make_wetland_select_handler(plot.index))
        runstate._wetland_plot_click_proxies[plot.index] = proxy
        tile.addEventListener("click", proxy)
        grid_el.appendChild(tile)


def render_wetland_section():
    banner = document.getElementById("wetland-lock-banner")
    section = document.getElementById("wetland-section")
    bar = document.getElementById("wetland-unlock-progress")
    if banner is None or section is None:
        return
    if not runstate.wetland_unlocked:
        section.hidden = True
        # Only tease this third region once the second one is open, so the
        # early game doesn't stack two locked banners.
        banner.hidden = not runstate.highland_unlocked
        bar.hidden = not runstate.highland_unlocked
        progress = min(standing_forest_value(), WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD)
        bar.max = WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD
        bar.value = progress
        banner.innerText = (
            "🌊 Wetland Forest is locked — reach "
            f"{WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD:.0f} standing forest value in your "
            f"main forest to open a lush but flood-prone third region ({progress:.0f}/"
            f"{WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD:.0f})."
        )
        return
    banner.hidden = True
    bar.hidden = True
    section.hidden = False
    render_wetland_grid()
    render_wetland_panel()
    render_wetland_stats()


def _setup_levels_bridge():
    """Hands the level screen its start callback once (configure() queues until levels.json has loaded)."""
    if runstate._levels_bridge_ready:
        return True
    window = _js_window()
    levels = getattr(window, "NoyvjLevels", None) if window is not None else None
    if levels is None:
        return False
    proxy = create_proxy(lambda level_id, level=None: start_level(str(level_id)))
    _level_proxies.append(proxy)
    payload = _to_js({"state": copy.deepcopy(runstate.levels_state), "onStart": proxy})
    if payload is None:
        proxy.destroy()
        del _level_proxies[:]
        return False
    try:
        levels.configure(payload)
    except Exception:  # noqa: BLE001
        return False
    runstate._levels_bridge_ready = True
    return True


def start_level(level_id, force=False):
    """Starts a level: a fresh session with the level's presets, then the level's goal rides the tick.
    Returns False for an unknown or still-locked level (the level screen already says why)."""
    spec = LEVEL_SPECS.get(level_id)
    if spec is None:
        return False
    if not force and level_lock_reason(level_id):
        return False
    started = reset_session(
        grid_size=spec.get("grid", "normal"),
        difficulty=spec.get("difficulty", DIFFICULTY_NORMAL),
        challenge=spec.get("challenge", CHALLENGE_NONE),
        pace=spec.get("pace", PACE_NORMAL),
        level=level_id,
        _render_after=False,
    )
    if not started:
        return False
    _log_event("level", f"Level {level_number(level_id)} started: {spec['title']}", None)
    render()
    return True


def render_level_status():
    if not runstate._levels_bridge_ready:
        _setup_levels_bridge()
    box = _el("level-box")
    status = _el("level-status")
    if box is None or status is None:
        return
    box.hidden = runstate.current_level is None
    status.innerText = level_status_text()
    spirit = _el("spirit-line")
    if spirit is not None:
        line = spirit_line_text()
        spirit.hidden = not line
        spirit.innerText = f"✨ {line}" if line else ""
    mode = _level_mode() if runstate.current_level is not None else None
    for name in ("poacher", "storm", "spirit"):
        _set_class(box, f"level-box--{name}", mode == name)
    _set_class(box, "level-box--done", runstate.level_done_tick is not None)
    next_button = _el("level-next-button")  # GN-3
    if next_button is not None:
        next_id = next_level_id()
        next_button.hidden = not (runstate.current_level is not None and runstate.level_done_tick is not None and next_id is not None)
        if not next_button.hidden:
            reason = level_lock_reason(next_id)
            next_button.disabled = bool(reason)
            title = LEVEL_SPECS[next_id]["title"]
            next_button.innerText = f"Next level: {title}"
            next_button.title = reason or f"Start level {level_number(next_id)}: {title}"


def buy_vault_node(node_id):
    """Buys a Seed Vault node with free seed points. Returns the shared tree's result dict."""
    result = skill_tree.buy(VAULT_TREE, vault_owned, node_id, vault_points_earned())
    if result["ok"]:
        vault_owned[:] = result["owned"]
        _save_meta()
        label = next(n["label"] for n in VAULT_TREE["nodes"] if n["id"] == node_id)
        _log_event("vault", f"Seed Vault: bought {label}", None)
        render()
    return result


def refund_vault_node(node_id):
    result = skill_tree.refund(VAULT_TREE, vault_owned, node_id)
    if result["ok"]:
        vault_owned[:] = result["owned"]
        _save_meta()
        render()
    return result


def refund_all_vault():
    result = skill_tree.refund_all(VAULT_TREE, vault_owned)
    vault_owned[:] = result["owned"]
    _save_meta()
    render()
    return result


def _vault_callbacks():
    if _vault_proxies:
        return _vault_proxies
    _vault_proxies.extend([
        create_proxy(lambda node_id, node=None: buy_vault_node(str(node_id))),
        create_proxy(lambda node_id, node=None: refund_vault_node(str(node_id))),
        create_proxy(lambda: refund_all_vault()),
    ])
    return _vault_proxies


def _render_vault_tree():
    window = _js_window()
    skill_view = getattr(window, "NoyvjSkillTree", None) if window is not None else None
    container = _el("vault-tree")
    if skill_view is None or container is None:
        return
    earned = vault_points_earned()
    if runstate._vault_view is None:
        buy, refund, refund_all = _vault_callbacks()
        options = _to_js({
            "tree": VAULT_TREE, "owned": list(vault_owned), "earned": earned, "refundNodes": True,
            "onBuy": buy, "onRefund": refund, "onRefundAll": refund_all,
        })
        if options is not None:
            runstate._vault_view = skill_view.render(container, options)
        return
    update = _to_js({"owned": list(vault_owned), "earned": earned})
    if update is not None:
        runstate._vault_view.update(update)


def render_vault():
    toggle = _el("vault-toggle-button")
    panel = _el("vault-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Seed Vault" if runstate.vault_open else f"\U0001F330 Seed Vault ({vault_points_free()} pts)"
    panel.hidden = not runstate.vault_open
    if not runstate.vault_open:
        return
    for element_id, text in (
        ("vault-summary", vault_summary_text()),
        ("vault-crews", vault_crews_text()),
        ("vault-note", "" if vault_perks_active() else "Perks and crews rest during a challenge run or an Expedition, so those stay comparable."),
    ):
        element = _el(element_id)
        if element is not None:
            element.innerText = text
    _render_vault_tree()


def buy_expedition_node(node_id):
    if runstate.current_expedition is None:
        return {"ok": False, "reason": "none"}
    result = skill_tree.buy(EXPEDITION_TREE, runstate.current_expedition["owned"], node_id, expedition_points_earned())
    if result["ok"]:
        runstate.current_expedition["owned"] = list(result["owned"])
        _expedition_effect_cache.clear()
        label = next(n["label"] for n in EXPEDITION_TREE["nodes"] if n["id"] == node_id)
        _log_event("expedition", f"Expedition upgrade: {label}", None)
        render()
    return result


def refund_expedition_node(node_id):
    if runstate.current_expedition is None:
        return {"ok": False, "reason": "none"}
    result = skill_tree.refund(EXPEDITION_TREE, runstate.current_expedition["owned"], node_id)
    if result["ok"]:
        runstate.current_expedition["owned"] = list(result["owned"])
        _expedition_effect_cache.clear()
        render()
    return result


def refund_all_expedition():
    if runstate.current_expedition is None:
        return {"ok": False, "reason": "none"}
    result = skill_tree.refund_all(EXPEDITION_TREE, runstate.current_expedition["owned"])
    runstate.current_expedition["owned"] = list(result["owned"])
    _expedition_effect_cache.clear()
    render()
    return result


def _expedition_callbacks():
    if _expedition_proxies:
        return _expedition_proxies
    _expedition_proxies.extend([
        create_proxy(lambda node_id, node=None: buy_expedition_node(str(node_id))),
        create_proxy(lambda node_id, node=None: refund_expedition_node(str(node_id))),
        create_proxy(lambda: refund_all_expedition()),
    ])
    return _expedition_proxies


def _render_expedition_tree():
    container = _el("expedition-tree")
    if container is None:
        return
    container.hidden = runstate.current_expedition is None
    if runstate.current_expedition is None:
        return
    window = _js_window()
    skill_view = getattr(window, "NoyvjSkillTree", None) if window is not None else None
    if skill_view is None:
        return
    earned = expedition_points_earned()
    if runstate._expedition_view is None:
        buy, refund, refund_all = _expedition_callbacks()
        options = _to_js({
            "tree": EXPEDITION_TREE, "owned": list(runstate.current_expedition["owned"]), "earned": earned, "refundNodes": True,
            "onBuy": buy, "onRefund": refund, "onRefundAll": refund_all,
        })
        if options is not None:
            runstate._expedition_view = skill_view.render(container, options)
        return
    update = _to_js({"owned": list(runstate.current_expedition["owned"]), "earned": earned})
    if update is not None:
        runstate._expedition_view.update(update)


def render_expedition():
    toggle = _el("expedition-toggle-button")
    panel = _el("expedition-panel")
    status = _el("expedition-status")
    if status is not None:
        text = expedition_status_text()
        status.innerText = text
        status.hidden = not text
    if toggle is not None:
        if runstate.expedition_open:
            toggle.innerText = "Hide Expedition"
        elif runstate.current_expedition is not None and not expedition_finished():
            toggle.innerText = f"\U0001F9ED Expedition ({expedition_season()}/{EXPEDITION_SEASONS})"
        else:
            toggle.innerText = "\U0001F9ED Expedition"
    if panel is None:
        return
    panel.hidden = not runstate.expedition_open
    if not runstate.expedition_open:
        return
    field = _el("expedition-seed-input")
    if field is not None:
        shown = runstate.current_expedition["seed"] if runstate.current_expedition is not None else expedition_meta["last_seed"]
        if shown != runstate._expedition_shown_seed:  # a seed the player is typing is never overwritten by a re-render
            runstate._expedition_shown_seed = shown
            if shown:
                field.value = shown
    leave = _el("expedition-leave-button")
    if leave is not None:
        leave.disabled = runstate.current_expedition is None
    start = _el("expedition-start-button")
    if start is not None:
        start.innerText = "Retry this seed" if runstate.current_expedition is not None and (field is None or getattr(field, "value", "") in ("", runstate.current_expedition["seed"])) else "Start Expedition"
    for element_id, text in (
        ("expedition-seed-message", runstate._expedition_message),
        ("expedition-summary", expedition_summary_text()),
        ("expedition-map-note", expedition_map_text()),
        ("expedition-result", expedition_result_text()),
        ("expedition-bests", expedition_bests_text()),
    ):
        element = _el(element_id)
        if element is not None:
            element.innerText = text
    _render_expedition_tree()


def render():
    render_info_page()
    render_grid()
    render_panel()
    render_plot_note_input()  # B-24
    render_plot_sheet()  # B-28
    render_survey()  # B-13
    render_lab_banner()  # B-5
    render_fire()  # GB-1
    render_rival()  # GB-12
    render_layout_badge()  # B-29
    _update_layout_best()
    render_stats()
    render_stakeholder_panel()
    render_real_world()
    render_grid_size_select()
    render_reset_button()
    render_adopt_panel()
    render_specialist_panel()
    render_season_indicator()
    render_season_forecast()
    render_challenge_status()
    render_forest_title()
    render_tend_panel()
    render_clear_cut_panel()  # GB-21
    render_undo_chip()
    render_almanac()
    render_contracts()
    render_level_status()
    render_vault()
    render_expedition()  # GB-3
    render_session_summary()
    render_highland_section()
    render_wetland_section()
    update_achievements_display()
    update_changelog_display()
    _sync_earned_and_toast()
    render_announcer()  # B-7: last, so everything this render queued is spoken once


def _make_select_handler(index):
    def handler(event):
        select_plot(index)
    return handler


def select_plot(index):
    if 0 <= index < len(runstate.plots) and runstate.plots[index].blocked:  # B-29
        return
    if runstate.golden_seedling is not None and runstate.golden_seedling["plot"] == index:
        collect_golden_seedling(index)  # GB-2: clicking the plot the seedling sits on catches it
    drive_off_poacher(index)  # GB-13: clicking the plot a poacher is working on drives it off
    runstate.selected_index = index
    _announce(selection_announcement(index))  # B-7: say which plot is now selected and what keys act on it
    render()
