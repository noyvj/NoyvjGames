"""The live state of the running game: the module variables that get REPLACED (rebound) while it runs.

THE RULE: a variable that some function reassigns (`total_income += ...`, `selected_index = 3`) lives only here, and every
other module reads and writes it as `runstate.<name>` (each module starts with `import canopy_runstate as runstate`). Never
`from canopy_runstate import total_income`: that copies the value once and goes stale at the next change. Lists, dicts and sets
that are only changed in place can stay in the module that owns them.

A few variables start from a constant or a function defined in a feature module (the plots, the starting difficulty ...);
they have a plain default here and the module that owns the initial value sets it when it is imported.

LIVE_NAMES at the bottom lists every such variable. game.py forwards `game.<name>` reads and writes to this module for exactly
those names (tests use game.total_income, game.selected_index and so on). Add a new rebound variable here AND to LIVE_NAMES."""


current_grid_size = "normal"

_mixed_bonus = 1.0

# B1/B6 (planning/TODO.md "Per-game: Canopy"): session-summary support --
# a running tick count (for B20's counterfactual math) and a bounded
# history of (income, standing_value) samples (for B6's sparkline).
# Deliberately ephemeral: never part of get_state()/load_state(), same
# reasoning as `_pending_value_pops` above -- a loaded save's history
# would be a different, disjoint session's shape, not a continuation of
# this one, so starting fresh on load is more honest than splicing two
# unrelated histories together.
_session_ticks = 0

selected_index = None
total_income = 0.0

pending_stakeholder_request = None  # {"plot_index": int, "reason": str} or None
_ticks_since_last_request = 0
_stakeholder_request_count = 0

# New tracked state for achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md §4):
# most of Canopy's catalog is a pure function of state that already exists
# (plots, total_income, community_relations, ...), but a handful of
# achievements are genuinely about something *having happened*, which
# monotonic-but-resettable fields like `plot.clear_count` (never decreases,
# so it already covers "ever cleared") don't all cover on their own. Each
# of these follows the same five-step defensive pattern as SOL's
# `visited_bodies`: a safe default here, mutated only at the real event
# below, added to get_state(), and given a `.get(key, <current>)` fallback
# in load_state() so an older save missing the field just keeps its
# fresh-module default instead of crashing the next render.
total_replants = 0  # incremented in on_replant() on a real replant() call
total_recoveries = 0  # incremented in tick() when advance_recovery() finishes one
plots_with_wildlife_ever = set()  # plot indices that have ever crossed the wildlife threshold
stakeholder_grants_count = 0  # incremented in grant_stakeholder_request()'s real-grant path
stakeholder_declines_count = 0  # incremented in decline_stakeholder_request()'s real-decline path

forest_log = []

_note_input_for = None
forest_tick = 0
adopted_plot_index = None  # B27

highland_unlocked = False

highland_selected_index = None
highland_income = 0.0
# Same leak-prevention pattern as the main grid's `_plot_click_proxies`
# (see render_grid()'s own comment) -- a second, independent dict since
# these track a disjoint set of DOM elements.
_highland_plot_click_proxies = {}

wetland_unlocked = False

wetland_selected_index = None
wetland_income = 0.0

wetland_floods_survived = 0
wetland_flood_value_lost = 0.0
_wetland_plot_click_proxies = {}

# Saved state (each written only when non-default).
forest_name = ""
adopted_plot_nickname = ""
heart_tree_index = None
rare_wildlife_found = []
peak_standing_value = 0.0
milestone_tier = 0
tend_cooldown_ticks = 0
perfect_streak = 0
season_cleared = False  # a main-forest Clear happened this season
season_min_relations = None  # lowest community relations seen this season

challenge_complete_tick = None  # forest_tick the active challenge was finished on, or None

contracts_completed = 0
contract_refill_ticks = 0
contract_last_clear_tick = 0  # forest_tick of the last main-forest clear (for the "calm" contract)
contract_clear_count_seen = 0
tends_done = 0
seedlings_caught = 0

# Ephemeral state (never saved): timers and one-shot render hints.
golden_seedling = None  # {"plot": index, "ticks_left": n} or None

_tend_message = ""
_undo_snapshot = None
clear_cuts_total = 0  # GB-21: clear-cuts made in this forest (saved only when above 0)
_recent_matures = []  # (forest_tick, plot index) for chain bloom

_forest_pulse_gen = 0
almanac_open = False

contracts_open = False
_challenge_record_cache = None  # GB-17: per-browser fastest-completion record, read lazily

plot_sheet_open = False

_community_ticks = 0

current_layout = None  # {"name": str, "cells": "1101..."} or None for the ordinary full grid


# The editor stages a cells string; Apply starts the forest, Save keeps it with a name.
layout_draft = None


# Per-plot click-handler proxies from the most recent render_grid() call.
# render_grid() rebuilds every tile element from scratch on every render
# (at minimum once per tick, i.e. once a second for the life of a
# session), and each create_proxy() call allocates a persistent
# Python<->JS bridge object that Pyodide never garbage-collects on its
# own. Without tracking and `.destroy()`ing the previous render's proxies,
# the old ones leak indefinitely even though the DOM nodes they were
# attached to are long gone — a slow memory leak over a long play
# session. Keyed by plot index so at most one live proxy per plot exists
# at any time.
_plot_click_proxies = {}


session_summary_open = False


achievements_open = False

# Tracks the earned-id set as of the last time it was checked, so a fresh
# unlock (one that wasn't in this set last time) can trigger a toast
# without re-toasting every already-earned achievement on every render.
# Reset (without toasting) right after setup()'s initial render and right
# after load_state() applies a save, so neither a fresh game nor a loaded
# one spams toasts for achievements that were already satisfied before
# this render cycle started.
_previously_earned_ids = set()

_toast_hide_proxy_gen = 0

changelog_open = False


example_open = False

info_page_open = False


_harvester_badge_announced = False


_announce_flip = False

# Saved / per-browser meta-progress (survives Reset Session).
levels_state = {"done": [], "best": {}}

# Session state of the running level (saved as "level_run" while a level is on).
current_level = None
level_ticks = 0
level_done_tick = None

# Ephemeral.
vault_open = False
_crew_tend_wait = 0
_crew_replant_clock = 0
_last_vault_points = 0

_vault_view = None

_levels_bridge_ready = False

# The running Expedition: None, or {"seed", "owned": [node ids], "done_tick": int | None, "score": int | None}.
current_expedition = None

expedition_open = False
_expedition_view = None

_expedition_message = ""
_expedition_shown_seed = None


# B-13 (2026-10-09): Survey mode. The tick is frozen; Clear, Replant and a queued decline of the pending clear request
# are written into a plan instead of happening. The panel shows what the plan would do (income gained, standing value
# given up, the gap to the "left standing" forest from the Session Summary, soil quality) and Commit runs it in order.
survey_mode = False

fire_warning = None  # {"plot": int, "ticks_left": int}
dampen_cooldown = 0
fire_value_lost = 0.0

rival_notice = None  # {"plot": int, "ticks_left": int}

perf_mode = False
_perf_strikes = 0
_perf_steady = 0
_last_tick_clock = None

_away_snapshot = None
_away_started_at = None

GRID_ROWS = 0  # canopy_rules sets it from the grid size when it is imported

GRID_COLS = 0  # canopy_rules sets it from the grid size when it is imported

current_difficulty = None  # canopy_rules sets it (normal) when it is imported

community_relations = 0  # canopy_rules sets it when it is imported

community_relations_min_ever = 0  # canopy_rules sets it when it is imported

plots = []  # canopy_plot fills it when it is imported

highland_plots = []  # canopy_plot fills it when it is imported

wetland_plots = []  # canopy_plot fills it when it is imported

wetland_flood_countdown = 0  # canopy_worldvars sets it when it is imported

current_challenge = None  # canopy_worldvars sets it when it is imported

current_pace = None  # canopy_worldvars sets it when it is imported

_golden_next_tick = 0  # canopy_worldvars sets it when it is imported

legacy_multiplier = 1.0  # canopy_records sets it when it is imported

playstyle_runs = []  # canopy_playstyle fills it when it is imported

current_scenario = None  # canopy_challenge sets it when it is imported

species_choice = None  # canopy_species sets it when it is imported


# Names that other modules must reach as runstate.<name> (game.py forwards reads and writes to them).
LIVE_NAMES = (
    "current_grid_size",
    "GRID_COLS",
    "GRID_ROWS",
    "current_difficulty",
    "_mixed_bonus",
    "_session_ticks",
    "plots",
    "selected_index",
    "total_income",
    "community_relations",
    "pending_stakeholder_request",
    "_ticks_since_last_request",
    "_stakeholder_request_count",
    "total_replants",
    "total_recoveries",
    "plots_with_wildlife_ever",
    "stakeholder_grants_count",
    "stakeholder_declines_count",
    "community_relations_min_ever",
    "forest_log",
    "_note_input_for",
    "forest_tick",
    "adopted_plot_index",
    "highland_unlocked",
    "highland_plots",
    "highland_selected_index",
    "highland_income",
    "_highland_plot_click_proxies",
    "wetland_unlocked",
    "wetland_plots",
    "wetland_selected_index",
    "wetland_income",
    "wetland_flood_countdown",
    "wetland_floods_survived",
    "wetland_flood_value_lost",
    "_wetland_plot_click_proxies",
    "forest_name",
    "adopted_plot_nickname",
    "heart_tree_index",
    "rare_wildlife_found",
    "peak_standing_value",
    "milestone_tier",
    "tend_cooldown_ticks",
    "perfect_streak",
    "season_cleared",
    "season_min_relations",
    "current_challenge",
    "challenge_complete_tick",
    "current_pace",
    "contracts_completed",
    "contract_refill_ticks",
    "contract_last_clear_tick",
    "contract_clear_count_seen",
    "tends_done",
    "seedlings_caught",
    "golden_seedling",
    "_golden_next_tick",
    "_tend_message",
    "_undo_snapshot",
    "clear_cuts_total",
    "_recent_matures",
    "_forest_pulse_gen",
    "almanac_open",
    "contracts_open",
    "_challenge_record_cache",
    "plot_sheet_open",
    "_community_ticks",
    "current_layout",
    "layout_draft",
    "_plot_click_proxies",
    "legacy_multiplier",
    "playstyle_runs",
    "session_summary_open",
    "achievements_open",
    "_previously_earned_ids",
    "_toast_hide_proxy_gen",
    "changelog_open",
    "example_open",
    "info_page_open",
    "_harvester_badge_announced",
    "_announce_flip",
    "current_scenario",
    "levels_state",
    "current_level",
    "level_ticks",
    "level_done_tick",
    "vault_open",
    "_crew_tend_wait",
    "_crew_replant_clock",
    "_last_vault_points",
    "_vault_view",
    "_levels_bridge_ready",
    "current_expedition",
    "expedition_open",
    "_expedition_view",
    "_expedition_message",
    "_expedition_shown_seed",
    "species_choice",
    "survey_mode",
    "fire_warning",
    "dampen_cooldown",
    "fire_value_lost",
    "rival_notice",
    "perf_mode",
    "_perf_strikes",
    "_perf_steady",
    "_last_tick_clock",
    "_away_snapshot",
    "_away_started_at",
)
