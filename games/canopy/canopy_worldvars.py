"""Constants and in-place collections for the later features (regions, golden seedling, tend, weather, challenges, contracts, display options, rival logging), plus the variables those features keep. Rebound variables are in canopy_runstate."""

import canopy_runstate as runstate
from canopy_rules import BARE, DIFFICULTY_RIVAL, PRESERVED, RECOVERED, REPLANTING


# B17: plot index -> value gained this tick, for a floating "+X" pop on
# the next render_grid() call. Populated fresh in tick(), consumed (popped)
# by render_grid() so a pop only ever shows for the render right after the
# tick that earned it -- never persisted, never part of get_state().
_pending_value_pops = {}
VALUE_POP_MIN_DELTA = 0.05  # below this a pop would just be visual noise

_value_history = []
VALUE_HISTORY_MAX_POINTS = 120  # ~2 minutes at one point/tick, TICK_INTERVAL_MS==1000

# Z-3e: the live side of the ghost (shared/ghost.py): the standing value after every tick of this session, capped at
# GHOST_LIVE_CAP ticks. Ephemeral like the histories above (a loaded save starts a fresh one); the best earlier session
# is kept per device in its own localStorage key, see the "Z-3e" block further down.
GHOST_LIVE_CAP = 5000
_ghost_live = []
_ghost_state = {"peak": 0.0, "tainted": False}

# B13: three parallel per-tick series (biodiversity, standing value, community
# relations) for the report card's small trend graphs. Ephemeral for the same
# reason as _value_history above.
_report_history = []
# B4: plot indices that first hit "fully mature" this tick, consumed by the
# next render_grid() (same one-shot pattern as _pending_value_pops).
_pending_mature_bursts = set()

# B3/B23/B27: a bounded, persisted event log ("forest history"). Entries are
# {"tick", "kind", "plot", "text"} dicts; `plot` is the main-forest plot
# index the event concerns (or None), which is what B27's adopted-plot
# mini-history filters on. `forest_tick` is its own persisted counter
# rather than reusing `_session_ticks` (deliberately ephemeral, resets on
# load) so entry ticks stay monotonic across a save/load.
FOREST_LOG_MAX_ENTRIES = 200

# B-14 (2026-10-09): one record per answered community request, for the request-history table.
REQUEST_HISTORY_MAX = 60
request_history = []
# B-24 (2026-10-09): short personal labels on plots (right-click or long-press, or the note box below the plot
# readout), shown as a corner dot and in the tile's tooltip, saved with the session.
PLOT_NOTE_MAX = 20
plot_notes = {}

# B3 (planning/TODO.md "Per-game: Canopy"): a second, unlockable forest
# region. Deliberately a smaller, simpler, self-contained sibling grid --
# same Plot class and clear/replant/accrue mechanics as the main forest
# (no reason to invent a second economy), but no stakeholder tension and
# no biodiversity tracking of its own; it's a bonus area for a player
# who's already deep into a session, not a second full copy of every
# system. Fixed at HIGHLAND_ROWS x HIGHLAND_COLS regardless of the B13
# grid-size preset chosen for the main forest -- the two are independent
# axes (main-forest size vs. whether the bonus region exists at all).
HIGHLAND_ROWS = 3
HIGHLAND_COLS = 4
HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD = 2000.0

# V-CD-5 (planning/TODO.md section N, completion-audit fix): the original
# B3 idea specified Highland Grove should have genuinely different
# degradation/compounding rates than the main forest, not just a same-
# rules bonus copy. Highland Grove is framed (its lock banner/blurb, its
# mountain iconography, "a smaller, higher grove") as a high-altitude
# ecosystem, so the distinction is grounded in real alpine-ecology
# tradeoffs rather than an arbitrary number: thin alpine soil erodes
# faster once disturbed (soil degrades HIGHLAND_DEGRADE_MULTIPLIER times
# faster per clear than the main forest), while a harsher, shorter
# high-altitude growing season means standing value compounds
# HIGHLAND_GROWTH_MULTIPLIER times slower once a plot is intact. Both
# apply only inside Plot.productivity_multiplier()/accrue_tick() when
# self.region == "highland" -- main-forest plots (region == "main") are
# multiplied by an implicit 1.0 and are byte-for-byte unaffected.
HIGHLAND_DEGRADE_MULTIPLIER = 1.5
HIGHLAND_GROWTH_MULTIPLIER = 0.75

# B1 (planning/TODO.md "Per-game: Canopy"): a third biome, Wetland Forest.
# Same Plot class and clear/replant loop again, but its own tension: it
# grows faster than the main forest (WETLAND_GROWTH_MULTIPLIER) and a flood
# sweeps it on a fixed timer. A flood strips a fraction of every standing
# plot's value -- much less from a plot that has stood a full MATURITY_TICKS
# (deep roots hold the water back) than from a young one -- and silts up
# any plot still replanting, pushing its recovery back. There is a warning
# window before each flood, so the choice is real: harvest a young plot
# now and bank its value, or gamble that it holds. Unlocks (sticky, one-way)
# at a higher standing-value threshold than Highland Grove.
WETLAND_ROWS = 3
WETLAND_COLS = 4
WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD = 5000.0
WETLAND_GROWTH_MULTIPLIER = 1.25
WETLAND_FLOOD_INTERVAL_TICKS = 50
WETLAND_FLOOD_WARNING_TICKS = 10
WETLAND_FLOOD_LOSS_YOUNG = 0.30
WETLAND_FLOOD_LOSS_MATURE = 0.10
WETLAND_FLOOD_SILT_TICKS = 8

runstate.wetland_flood_countdown = WETLAND_FLOOD_INTERVAL_TICKS


# ===========================================================================
# GB batch 1 (planning/IMPROVEMENT-IDEAS-ROUND-3.md section GB): golden
# seedling (GB-2), Tend (GB-4), Heart Tree (GB-8), names (GB-14), undo
# (GB-18), rare wildlife (GB-20), standing-value tiers (GB-22), weather
# (GB-23), chain bloom (GB-27), Forest Almanac (GB-28), Perfect Season
# (GB-30). Constants and state live here; the behaviour is in the "GB batch 1"
# section just above render().
#
# Rules kept from the rest of the game: no RNG (a small hash of forest_tick
# stands in wherever a "random" pick is wanted, so runs and tests stay
# deterministic); anything timed rides the 1-second tick (the golden seedling, Tend and the undo
# chip); the only setTimeouts are the brief pulse/flash clean-ups; new
# save keys are written only when non-default and validated on load.
# ===========================================================================
GOLDEN_SEEDLING_TICKS = 4  # GB-2: it stays for about 4 seconds (one tick = 1 s)
GOLDEN_SEEDLING_RECOVERY_TICKS = 4  # recovery progress banked on a click
GOLDEN_SEEDLING_MIN_GAP = 20  # ticks between one seedling and the next...
GOLDEN_SEEDLING_GAP_SPREAD = 25  # ...plus up to this many more (hash-picked)

TEND_DURATION_TICKS = 5  # GB-4
TEND_COOLDOWN_TICKS = 20
TEND_GROWTH_MULTIPLIER = 1.5  # economic accrual on the tended plot; replanting plots recover an extra tick per tick

HEART_TREE_MIN_MATURE_NEIGHBOURS = 7  # GB-8: of the 8 plots around a centre plot
HEART_TREE_AURA_BONUS = 0.10  # extra standing-value growth on the 8 plots around the Heart Tree

FOREST_NAME_MAX = 24  # GB-14
NICKNAME_MAX = 20

UNDO_WINDOW_TICKS = 3  # GB-18: the chip survives 3 full ticks (3 to 4 seconds at 1 tick/s)

BIODIVERSITY_FULL_SCORE = 2.0  # GB-20: "100% biodiversity" for one plot (100 ticks of base accrual)
RARE_STAG_MIN_FRACTION = 0.9
DUSK_TICKS_IN_AUTUMN = 10  # the last 10 ticks of autumn are the night-tinted ones
RARE_FOX_DECLINED_REQUESTS = 3
RARE_WILDLIFE = [
    ("ghost_stag", "\U0001F98C", "ghost stag", "Only at night-tinted late-autumn ticks, on a plot at 90%+ biodiversity."),
    ("wary_fox", "\U0001F98A", "wary fox", "Comes out once you have declined three requests to clear."),
]

STANDING_TIERS = [(1000.0, "Seedling"), (2500.0, "Grove"), (5000.0, "Woodland"), (10000.0, "Old-Growth")]  # GB-22
TIER_ACHIEVEMENT_THRESHOLDS = {"tier_grove": 2500.0, "tier_woodland": 5000.0, "tier_old_growth_steward": 10000.0}
FOREST_PULSE_MS = 1800

WEATHER_BLOCK_TICKS = 32  # GB-23: at most one episode starts per block
WEATHER_DURATION_TICKS = 8
WEATHER_FIRST_TICK = 24  # a fresh forest gets a calm opening
WEATHER_EPISODE_PERCENT = 55  # chance a given block has an episode
WEATHER_RAIN_MULTIPLIER = 1.15
WEATHER_DROUGHT_MULTIPLIER = 0.85
WEATHER_SEASON_KIND = {"spring": "rain", "summer": "drought", "autumn": "rain", "winter": None}
WEATHER_LABEL = {"rain": "Rain", "drought": "Drought"}
WEATHER_ICON = {"rain": "\u2614", "drought": "\U0001F3DC\ufe0f"}

CHAIN_BLOOM_WINDOW_TICKS = 3  # GB-27
CHAIN_BLOOM_MIN_PLOTS = 3
CHAIN_BLOOM_MAX_RANK = 7

PERFECT_SEASON_MIN_RELATIONS = 30  # GB-30
PERFECT_STREAK_BONUS_PER_SEASON = 0.02
PERFECT_STREAK_MAX_BONUS_SEASONS = 5

# ===========================================================================
# GB batch 2 (2026-10-07): challenge runs (GB-17), the Ranger contracts board
# (GB-9), the season forecast (B-12), the request-pace selector (B-6), the
# screen-reader announcer and C/R hotkeys (B-7), the plot tooltip card (B-16),
# and three display options read from localStorage: high-contrast plots
# (B-8), the soil overlay (B-10) and number formats (B-26). Same rules as
# batch 1: no RNG, everything timed rides the 1 s tick, new save keys written
# only when non-default and validated on load.
# ===========================================================================

# --- GB-17: challenge runs ---------------------------------------------------
CHALLENGE_NONE = "none"
CHALLENGE_PACIFIST = "pacifist"
CHALLENGE_SCORCHED = "scorched"
CHALLENGE_SPRINT = "sprint"
CHALLENGE_NO_HIGHLAND = "no_highland"
CHALLENGE_SPECS = {
    CHALLENGE_PACIFIST: {
        "label": "Pacifist",
        "icon": "\U0001F54A️",
        "achievement": "challenge_pacifist",
    },
    CHALLENGE_SCORCHED: {
        "label": "Scorched Start",
        "icon": "\U0001F525",
        "achievement": "challenge_scorched",
    },
    CHALLENGE_SPRINT: {
        "label": "Sprint",
        "icon": "⏱️",
        "achievement": "challenge_sprint",
    },
    CHALLENGE_NO_HIGHLAND: {
        "label": "No-Highland",
        "icon": "\U0001F3D4️",
        "achievement": "challenge_no_highland",
    },
}
CHALLENGE_PACIFIST_STANDING_PER_PLOT = 40  # goals scale with the grid so Small and Large stay fair
CHALLENGE_SCORCHED_STANDING_PER_PLOT = 50
CHALLENGE_NO_HIGHLAND_STANDING_PER_PLOT = 100
CHALLENGE_SPRINT_INCOME_PER_PLOT = 28
CHALLENGE_SPRINT_STANDING_PER_PLOT = 70
CHALLENGE_SPRINT_TICK_LIMIT = 60
CHALLENGE_SCORCHED_BARE_FRACTION = 2 / 3  # two thirds of the plots start bare (soil untouched, so nothing counts as a clear)
CHALLENGE_RECORDS_STORAGE_KEY = "canopy_challenge_records_v1"  # per browser: id -> fastest completion tick
CHALLENGE_ACTIVE = "active"
CHALLENGE_COMPLETE = "complete"
CHALLENGE_FAILED = "failed"

# --- GB-9: Ranger contracts board ---------------------------------------------
CONTRACT_SLOTS = 3
CONTRACT_REFILL_TICKS = 6  # a finished slot stays empty this long before the next contract appears
CONTRACT_REWARD_PER_PLOT = 5  # banked as income, so a 36-plot forest earns 180 a contract
CONTRACT_CALM_TICKS = 30
CONTRACT_TYPES = [
    # (id, icon, short stamp name)
    ("replant", "\U0001F331", "Replanter"),
    ("mature", "\U0001F333", "Elder grove"),
    ("wildlife", "\U0001F98B", "Wildlife warden"),
    ("decline", "✋", "Firm refusal"),
    ("accept", "\U0001F91D", "Good neighbour"),
    ("tend", "\U0001F33F", "Gardener"),
    ("seedling", "✨", "Seedling catcher"),
    ("standing", "\U0001F4C8", "Value grower"),
    ("calm", "\U0001F54A️", "Long peace"),
    ("trust", "\U0001F3D8️", "Village trust"),
]
CONTRACT_RANKS = [(0, "Trainee"), (3, "Ranger"), (8, "Senior ranger"), (15, "Warden"), (25, "Chief warden")]

# --- B-6: how often the village asks ---------------------------------------------
PACE_RELAXED = "relaxed"
PACE_NORMAL = "normal"
PACE_FREQUENT = "frequent"
REQUEST_PACE_FACTOR = {PACE_RELAXED: 1.5, PACE_NORMAL: 1.0, PACE_FREQUENT: 2 / 3}
REQUEST_PACE_LABEL = {PACE_RELAXED: "Relaxed requests", PACE_NORMAL: "Normal requests", PACE_FREQUENT: "Frequent requests"}

# --- B-8 / B-10 / B-26: display options stored per browser (settings.js writes them) ---
UI_PREF_PLOT_CONTRAST = "canopy-plot-contrast"
UI_PREF_SOIL_OVERLAY = "canopy-soil-overlay"
UI_PREF_COACH = "canopy-coach-hints"  # B-27, opt-in
UI_PREF_NUMBER_FORMAT = "canopy-number-format"
NUMBER_FORMAT_STANDARD = "standard"  # one decimal, as the game always showed numbers
NUMBER_FORMAT_GROUPED = "grouped"  # 12,345.6
NUMBER_FORMAT_COMPACT = "compact"  # 12.3k
NUMBER_FORMAT_PRECISE = "precise"  # two decimals
NUMBER_FORMATS = (NUMBER_FORMAT_STANDARD, NUMBER_FORMAT_GROUPED, NUMBER_FORMAT_COMPACT, NUMBER_FORMAT_PRECISE)
STATE_LETTER = {BARE: "B", REPLANTING: "R", PRESERVED: "G", RECOVERED: "G"}  # G = growing; M = mature (below)
MATURE_LETTER = "M"
SOIL_BANDS = [(90, "good"), (70, "fair"), (50, "poor"), (0, "depleted")]

# GB batch 2 (session settings are chosen with the selects and reset the session, like difficulty):
runstate.current_challenge = CHALLENGE_NONE  # GB-17

runstate.current_pace = PACE_NORMAL  # B-6
contract_board = []  # GB-9: [{"type", "target", "base"}] for the open contracts
contract_stamps = []  # contract type ids completed at least once this session

runstate._golden_next_tick = GOLDEN_SEEDLING_MIN_GAP

_pending_bloom = {}  # plot index -> ripple rank, consumed by the next render_grid()
_pending_golden_bursts = set()  # plot indices, consumed by the next render_grid()

_gb_toast_queue = []  # GB toasts waiting for the next render
_announce_queue = []  # B-7: messages for the screen-reader live region, flushed once per render


# GB-12 (2026-10-09): the rival logging company, only on the "Rival logging company" difficulty. Halloran Timber Co. bids on
# a standing plot on the edge of the grid: the plot is flagged RIVAL_NOTICE_TICKS ticks ahead, then becomes a mining claim
# (bare, cannot be replanted) that Halloran works for RIVAL_CLAIM_TICKS ticks before leaving it bare and free. You can lock
# a plot with a conservation easement (it costs a share of that plot's value from your income) so it can never be claimed,
# or pay a buy-out to end a claim early. Bids come faster as the session goes on (down to a floor). Deterministic, fully
# telegraphed and recoverable: a claimed plot comes back. This is a one-player mode; the idea of a second human
# player in Halloran's place is parked with the multiplayer scoping.
RIVAL_FIRST_BID_TICKS = 40
RIVAL_INTERVAL_TICKS = 45
RIVAL_INTERVAL_STEP = 4
RIVAL_INTERVAL_FLOOR = 24
RIVAL_NOTICE_TICKS = 10
RIVAL_CLAIM_TICKS = 40
RIVAL_EASEMENT_SHARE = 0.15
RIVAL_EASEMENT_MIN = 10.0
RIVAL_BUYOUT_COST = 30.0
rival_claims = {}  # plot index -> ticks left on the mining claim

rival_locked = set()  # plots under a conservation easement
rival_state = {"next_bid": RIVAL_FIRST_BID_TICKS, "bids": 0}


def rival_enabled():
    return runstate.current_difficulty == DIFFICULTY_RIVAL


SEASON_FRAMES_MAX = 20
SEASON_FRAME_LETTER = {PRESERVED: "P", BARE: "B", REPLANTING: "R", RECOVERED: "C"}
season_frames = []
