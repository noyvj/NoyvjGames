"""The module variables that get REPLACED while the game runs (tick counters, panel-open flags, lifetime stats, prestige, the Scarcity Run, ghost recordings).

Other modules read and write them as `runstate.x`, never as a copied name."""


research_progress = 0.0  # Iron invested in the current level's researched nodes (derived, see _recompute_research())
completed_tiers = 0      # derived from researched_nodes, kept as a variable for its many readers

unlocked_bodies = set()
current_planet = "Earth"
governor_priority = "balance"  # "growth" | "balance" | "ecology"
governor_budget_pct = 50.0
governor_tick_count = 0
# New tracked state (ACHIEVEMENTS-SYSTEM-DESIGN.md §4's "add new state only
# where genuinely necessary" case): governor_tick_count increments on every
# tick the moment ANY other planet exists to govern, which is true from the
# very first tick of a brand-new game -- it's a measure of time elapsed, not
# of the governor having actually done anything. governor_purchase_count
# only increments inside governor_step()'s own buy branches below, i.e. the
# governor genuinely spent resources managing a world while the player was
# elsewhere -- the real thing the "Governor Appointed" achievement means to
# reward.
governor_purchase_count = 0

# TODO.md's own note leaned toward starting simple -- a permanent flat
# bonus on restart -- over a full skill-tree prestige layer, since the
# latter is genuinely its own milestone-sized feature. Going with that: one
# integer that only ever goes up, and one flat production multiplier
# derived from it. prestige_level survives a prestige reset by design (see
# _prestige() below) -- it's the one piece of state a prestige is FOR
# keeping, everything else about the run is what gets cleared.
prestige_level = 0

# Each prestige earns 1 point (2 if the New Game+ Challenge below was active
# when you prestiged); points are spent on tree nodes that never reset.
# Tier 2 is a genuine second branch: gated on Prestige LEVEL (how many times
# you have prestiged), not just on points. The New Game+ Challenge (A3) is a
# node INSIDE this tree that unlocks a harder-replay toggle.
prestige_points_earned = 0
prestige_nodes = set()
ng_challenge_active = False
# A15: sandbox mode (only ever effective while every world is terraformed).
sandbox_mode = False

close_call_hit = False
back_from_brink_hit = False

# All of these only ever go up (or, for the *_hit booleans, flip False->True
# once and stay there) -- "lifetime" means lifetime, including across a
# prestige reset (see _prestige() below, which deliberately does NOT touch
# any of this block). total_ticks is an in-game clock (ticks * 100ms), not
# a wall-clock timestamp -- deterministic under test, immune to a
# backgrounded/throttled browser tab counting differently than active play,
# and exactly what the two speedrun achievements below mean to measure
# ("how much simulated play-time did this take", not "how much real time
# has passed since first opening the page").
total_ticks = 0
# A29: the total_ticks reading the first time every world was terraformed
# (None until then). Kept for life, like the other lifetime counters, so a
# later reset can't erase it. It is the score for the opt-in community
# "fastest full completion" leaderboard (shared/leaderboard.js).
full_system_completed_tick = None
_leaderboard_reported = False
# R-10: the fastest full playthrough, per RUN. `run_start_tick` is the
# total_ticks reading when this run began (0 at the start, reset by each
# prestige); `run_completed` marks that this run's completion has been
# recorded; `best_run_ticks` is the shortest completed run so far, kept for life.
run_start_tick = 0
run_completed = False
best_run_ticks = None
total_manual_clicks = 0
lifetime_resources_mined_by_click = 0.0
lifetime_resources_generated_by_automation = 0.0
lifetime_generators_built = 0
lifetime_recyclers_built = 0
lifetime_trade_routes_built = 0
lifetime_sky_cities_built = 0

# Whether a generator has EVER existed anywhere -- from a manual buy or a
# governor purchase, either counts, and it never resets. This is what makes
# "never automated" checkable at all: generator_count alone only tells you
# the CURRENT count, which a live check can't use to mean "was ever built"
# once one is later scrapped-and-rebuilt-free by a world reset (A18).
any_generator_ever_built = False

quick_start_hit = False
swift_expansion_hit = False
manual_labor_hit = False
off_the_grid_hit = False


_research_effect_cache = None  # only ever a dict inside a headless run, where research cannot change

# New tracked state (see the module docstring above): every body the player
# has ever actually traveled to, Earth included from the start since that's
# where every game begins. Mutated in place (never reassigned) from each
# on_travel_* handler below via `_mark_visited()`, so no `global` declaration
# is needed at those call sites — only deserialize_state() below, which does
# reassign it wholesale from a loaded save, needs one.
visited_bodies = {"Earth"}


achievements_open = False

# Achievements retrofit (TODO.md "roll achievements out everywhere" — SOL's
# own toast/hub-link retrofit, built after the base 18-achievement rollout
# shipped): a snapshot of which achievement ids were already earned as of
# the last full render, so tick()'s live check can tell "newly earned this
# tick" apart from "already earned before this page load/save load" and
# only toast for the former. Seeded (never diffed-against-empty) inside
# _full_render() -- both the fresh-game path (setup()) and the loaded-save
# path (load_state()/load_save_state_json()) call _full_render(), so a save
# that already has 12 achievements earned never floods the player with 12
# toasts the instant it loads.
_achievements_seen_ids = set()

click_streak = 0
best_click_streak = 0
_streak_last_tick = None

splits_open = False

_trophy_fresh_id = None  # the badge to flourish, only for an unlock this session

chains_open = False

changelog_open = False

# Efficiency here means the same production_multiplier() every planet's own
# automation already runs on every tick (100% at healthy ecology, 75% under
# the 25%-output penalty, 0% during a full collapse) -- surfaced explicitly
# per governed world rather than left implicit in how fast its resource
# count climbs. "Generated while governed" is governed_resource_generated
# (see planet_state's own comment above and _simulate_planet), a lifetime
# total that only counts production that happened while that world was NOT
# current_planet, i.e. genuinely produced by the governor while the player
# was elsewhere.
governor_report_open = False

stats_open = False

_departure_snapshots = {}  # planet -> what its state looked like when the player left it

_active_floaters = 0

overview_open = False
_overview_signature = None

build_plan_open = False

prestige_tree_open = False

epilogue_open = False

mutators_run = []  # the rules the run in progress is being played under

_active_anomaly = None  # id of the anomaly in effect this tick, or None

charter_open = False
_charter_signature = None

megaprojects_all_ever = False  # lifetime: all four built in one run once

doctrine_open = False

_doctrine_fired_counts = {}  # rule index -> times fired (per session; reset when the list changes)
_doctrine_last_fired = {}  # planet -> (rule text, game tick)
_doctrine_relief_ready = {}  # planet -> tick when relief may fire again
_doctrine_dry_text = ""
_doctrine_signature = None

_dry_run = False

stress_best_margin = None  # lifetime best margin, saved when set
_stress_last = None
_stress_run_id = 0

_terraform_done_seen = set()  # worlds already at 100% as of the last tick (transient)

survey_data = 0  # lifetime currency, saved when above 0
chart_revealed = 0  # how many chart regions are uncovered (the order is fixed), saved when above 0

comets_caught_total = 0  # lifetime catches, saved when above 0
_comet_since = None  # transient: tick the current comet appeared (restarts bright after a reload)
observatory_open = False
_observatory_signature = None

capsules_open = False
_capsules_signature = None


_capsule_next_id = 1

_scarcity = None  # the active run: {"spec", "stash", "trophies", "samples", "done", "ghost", "ghost_label"}
_scarcity_keep_days = False

scarcity_open = False
_scarcity_selected = None
_scarcity_month = None
_scarcity_signature = None

_scarcity_notice = ""
_scarcity_ghost_choice = "none"  # "none", "best", "par" or "friend" for the next run
_scarcity_friend_code = ""
_scarcity_friend = None  # {"date", "rec", "label"}: a friend's blueprint played by the Governor on one date
_PRISTINE_JSON = ""  # the fresh-game state, taken just before setup()

# A recording is the average terraform percent (tenths of a point) sampled every GHOST_STEP (25)
# ticks. Recordings stay in this browser's localStorage, never in the save code, and are validated
# on read (challenges.clean_recording). Normal play records your run automatically; it is kept only
# when it is a new personal best (the fastest full playthrough). A Scarcity Run keeps your best
# recording for each date, and can also race the Governor alone or a friend's blueprint played by
# the Governor on that day.
_pb_ghost = None  # the personal-best recording, or None
_live_ghost = []  # this run's samples so far
_live_ghost_partial = False  # started mid-run (older save or a gap): can never become the best
_live_ghost_run = 0  # run_start_tick the live samples belong to

_splits_signature = None


# Names that other modules must reach as runstate.<name> (game.py forwards reads and writes to them).
LIVE_NAMES = (
    "research_progress",
    "completed_tiers",
    "unlocked_bodies",
    "current_planet",
    "governor_priority",
    "governor_budget_pct",
    "governor_tick_count",
    "governor_purchase_count",
    "prestige_level",
    "prestige_points_earned",
    "prestige_nodes",
    "ng_challenge_active",
    "sandbox_mode",
    "close_call_hit",
    "back_from_brink_hit",
    "total_ticks",
    "full_system_completed_tick",
    "_leaderboard_reported",
    "run_start_tick",
    "run_completed",
    "best_run_ticks",
    "total_manual_clicks",
    "lifetime_resources_mined_by_click",
    "lifetime_resources_generated_by_automation",
    "lifetime_generators_built",
    "lifetime_recyclers_built",
    "lifetime_trade_routes_built",
    "lifetime_sky_cities_built",
    "any_generator_ever_built",
    "quick_start_hit",
    "swift_expansion_hit",
    "manual_labor_hit",
    "off_the_grid_hit",
    "_research_effect_cache",
    "visited_bodies",
    "achievements_open",
    "_achievements_seen_ids",
    "click_streak",
    "best_click_streak",
    "_streak_last_tick",
    "splits_open",
    "_trophy_fresh_id",
    "chains_open",
    "changelog_open",
    "governor_report_open",
    "stats_open",
    "_departure_snapshots",
    "_active_floaters",
    "overview_open",
    "_overview_signature",
    "build_plan_open",
    "prestige_tree_open",
    "epilogue_open",
    "mutators_run",
    "_active_anomaly",
    "charter_open",
    "_charter_signature",
    "megaprojects_all_ever",
    "doctrine_open",
    "_doctrine_fired_counts",
    "_doctrine_last_fired",
    "_doctrine_relief_ready",
    "_doctrine_dry_text",
    "_doctrine_signature",
    "_dry_run",
    "stress_best_margin",
    "_stress_last",
    "_stress_run_id",
    "_terraform_done_seen",
    "survey_data",
    "chart_revealed",
    "comets_caught_total",
    "_comet_since",
    "observatory_open",
    "_observatory_signature",
    "capsules_open",
    "_capsules_signature",
    "_capsule_next_id",
    "_scarcity",
    "_scarcity_keep_days",
    "scarcity_open",
    "_scarcity_selected",
    "_scarcity_month",
    "_scarcity_signature",
    "_scarcity_notice",
    "_scarcity_ghost_choice",
    "_scarcity_friend_code",
    "_scarcity_friend",
    "_PRISTINE_JSON",
    "_pb_ghost",
    "_live_ghost",
    "_live_ghost_partial",
    "_live_ghost_run",
    "_splits_signature",
)
