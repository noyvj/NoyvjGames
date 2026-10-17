"""Fixed numbers and content tables (costs, thresholds, tiers, coastlines, titles, storage keys): no browser calls, no state."""


STARTING_FUNDS = 300

CATEGORIES = ["output", "reduction", "adaptation"]

INVEST_COST = {
    "output": 20,
    "reduction": 25,
    "adaptation": 30,
}

OUTPUT_INCOME_PER_UNIT = 6

# Acidity: rises with industry output, falls (more slowly) with dedicated
# reduction spending. Never goes negative — there's no "banking" cleanup
# credit for later.
# D29 / D8: settlement-name cap, chronicle cap, and the tide model.
SETTLEMENT_NAME_MAX = 24
CHRONICLE_LIMIT = 40
TIDE_AMPLITUDE = 4.0
TIDE_PERIOD_FACTOR = 1.1
TIDE_HIGH_CUTOFF = 2.0

# D17: coastal heritage. Each site sits on one coastline row (column
# HERITAGE_COL); protecting it costs a one-off sum plus a small upkeep
# every season, and a protected site survives its row flooding.
HERITAGE_COL = 3
HERITAGE_UPKEEP = 6
HERITAGE_SITES = [
    {"id": "lighthouse", "name": "Old lighthouse", "emoji": "🗼", "row": 4, "cost": 120},
    {"id": "reef", "name": "Oyster-reef nursery", "emoji": "🦪", "row": 5, "cost": 180},
]
# GD-14 / GD-28 (2026-10-09): a balanced-seasons income streak and the comeback discount after a domino season.
BALANCE_MULTIPLIERS = (1.0, 1.1, 1.2, 1.3)  # by streak length, capped at the last
DOMINO_MIN_ROWS = 3
DOMINO_DISCOUNT = 0.25
DOMINO_DISCOUNT_SEASONS = 2
# GD-20 / GD-24 / GD-23 (2026-10-09): one Rewind per run, the hard-lag ironman badge and the speedrun trackers.
IRONMAN_SEASONS = 20
IDLE_CAP_SECONDS = 60  # a gap between clicks counts for at most this long, so walking away does not ruin a run
SPEEDRUN_KEY = "tide_speedrun_v1"
# GD-8 (2026-10-09): Trade Winds market events. Every MARKET_EVERY seasons a deal is offered (telegraphed the season before).
MARKET_EVERY = 4
MARKET_DIP_FACTOR = 0.9
MARKET_KINDS = ("export", "tourism", "insurance")
# GD-11 (2026-10-09): crew and specialists. Up to CREW_MAX can be hired at once; each has a one-off fee and a wage every season.
CREW = {
    "biologist": {"name": "Marine Biologist", "effect": "fish lag one season shorter"},
    "engineer": {"name": "Harbor Engineer", "effect": "adaptation costs 15% less"},
    "broker": {"name": "Broker", "effect": "Trade Winds deals pay 30% more and leave a lighter dip"},
}
CREW_MAX = 3
CREW_HIRE_COST = 60
CREW_WAGE = 5
ENGINEER_DISCOUNT = 0.15
BROKER_GAIN_BONUS = 0.30
# D-5 (2026-10-09): the Tide Workshop. Opt-in dials that change the rules of a NEW run; a run with any dial moved is
# labelled "custom rules" and stays out of the Almanac, the personal best and the session library.
WORKSHOP_DEFAULTS = {"funds": STARTING_FUNDS, "lag": 0, "rise": 1.0, "surge": 1.0, "fish": 1.0}  # lag 0 means the normal lag
WORKSHOP_RANGES = {"funds": (100, 600, 50), "lag": (0, 8, 1), "rise": (0.5, 2.0, 0.25), "surge": (0.5, 2.0, 0.25), "fish": (0.5, 2.0, 0.25)}
WORKSHOP_LABELS = {"funds": "Starting funds", "lag": "Fish lag (seasons, 0 = normal)", "rise": "Sea-level rise rate",
                   "surge": "Storm surge size", "fish": "Fish sensitivity to acidity"}
# GD-12 (2026-10-09): the optional Acid Tide boss. When it is switched on, a mega acid surge arrives while Season
# ACID_BOSS_SEASON resolves unless the player braced for it (a big one-off sum of funds, with enough Reduction capacity).
ACID_BOSS_SEASON = 15
ACID_BOSS_SPIKE = 25.0
ACID_BRACE_COST = 150
ACID_BRACE_MIN_REDUCTION = 6
ACID_BOSS_WARN_SEASONS = 3
# GD-3 (2026-10-09): bracing for a storm. Within BRACE_WINDOW seasons of a forecast storm the player can commit funds to
# barriers (each BARRIER_FUNDS_PER_SURGE funds hold back one more point of surge), a stockpile (cash set aside that
# absorbs the storm's cost, the unused part coming back) and evacuating the unprotected heritage sites. The result is
# graded Shrugged Off, Battered or Breached; a breach loses any unprotected, non-evacuated site.
BRACE_WINDOW = 2
BRACE_STEP = 10
BARRIER_FUNDS_PER_SURGE = 5
EVACUATE_COST = 25
STORM_RESULT_TIERS = ((0.15, "Shrugged Off"), (0.5, "Battered"), (10**9, "Breached"))
# GD-4 (2026-10-09): Tidal Chess. A challenge mode: on top of the fish lag, industry runoff reaches the water RUNOFF_LAG
# seasons late (a second delay), the acidity readouts are hidden and only the fish warning stays visible. The score is how
# few seasons the fish yield dipped to the warning level. It can only be switched on before the first season.
CHESS_RUNOFF_LAG = 2
CHESS_RUNOFF_SHARE = 0.5  # share of each Output unit's normal acidity that arrives as late runoff instead of at once
# GD-27: a heritage site protected when its row would flood within this many seasons counts as a last-second rescue.
RESCUE_WITHIN_SEASONS = 1
HERITAGE_UNPROTECTED = "unprotected"
HERITAGE_PROTECTED = "protected"
HERITAGE_LOST = "lost"

# D21: citizen-science monitoring -- a paid, cooled-down action whose
# reward is the next fact in a list of real-world acidification/sea-level
# findings (paraphrased from NOAA/NASA public material, same sources as the
# info page).
MONITOR_COST = 50
MONITOR_COOLDOWN_SEASONS = 2
CITIZEN_SCIENCE_FACTS = [
    "Since the start of the industrial era, average surface-ocean pH has fallen from about 8.2 to about 8.1 — around 30% more acidic, because the pH scale is logarithmic.",
    "The ocean has taken up roughly a quarter of the carbon dioxide people have emitted — a service that slows warming but is exactly what acidifies the water.",
    "Global mean sea level has risen roughly 8–9 inches (21–24 cm) since 1880, and the yearly rate in recent decades is faster than the 20th-century average.",
    "Shell-building animals such as oysters and pteropods struggle in more acidic water: carbonate ions, the raw material for shells, become scarcer.",
    "US Pacific Northwest oyster hatcheries suffered major larval die-offs in the 2000s tied to corrosive seawater, and now monitor and buffer the water they draw in.",
    "The ocean has absorbed around 90% of the extra heat trapped by greenhouse gases; warm water expands, so thermal expansion is a major driver of sea-level rise alongside melting ice.",
    "Cold water dissolves more CO2, so polar seas are among the first places acidification becomes severe.",
    "Community and volunteer programmes help track coastal water chemistry and temperature, filling gaps between research ships and buoys.",
]

# D13: opt-in storm seasons -- an acute shock every STORM_INTERVAL seasons,
# forecast a season ahead, whose bite is cut by the current dampening.
STORM_INTERVAL = 5
STORM_BASE_SURGE = 18.0
STORM_SURGE_GROWTH = 3.0
STORM_FUNDS_PER_DAMAGE = 3.0

# D1: managed retreat -- a strategy branch alongside the four adaptation
# tiers. Each step gives up the lowest still-dry row on purpose (it shows as
# flooded) in exchange for a permanent extra cut to sea-level damage.
RETREAT_COST = 100
RETREAT_MAX_STEPS = 2
RETREAT_EARLY_MAX_FLOODED = 1  # D-10: a retreat counts as "ahead of the sea" while at most this many rows have flooded
RETREAT_DAMAGE_CUT = 0.2

# D5 / D15: population. It grows toward the housing the dry rows can hold
# (denser building behind higher adaptation tiers); rows lost push the
# excess out as displaced people.
POP_START = 100
POP_PER_ROW = 22
POP_PER_ROW_PER_TIER = 4
POP_GROWTH_RATE = 0.06
POP_GROWTH_MIN_FISH_YIELD = 0.5

# D11: economy diversification -- a third income source, hedging the fish
# crash. Tourism fades as coastline is lost (and gets a boost from protected
# heritage); aquaculture pays on a shorter, milder acidity penalty.
DIVERSIFY_COST = {"tourism": 140, "aquaculture": 160}
DIVERSIFY_MAX_LEVEL = 3
TOURISM_INCOME_PER_LEVEL = 5.0
TOURISM_HERITAGE_BONUS = 2.0
AQUACULTURE_INCOME_PER_LEVEL = 5.0
AQUACULTURE_ACIDITY_SCALE = 75.0  # 1.5x FISH_DAMAGE_SCALE: a milder, unlagged penalty
AQUACULTURE_MIN_MULTIPLIER = 0.4

# D27: how much of the run's state a checkpoint keeps.
CHECKPOINT_FORESIGHT_LIMIT = 200
CHECKPOINT_DROP_KEYS = (
    "ticker_full_history", "achievements_earned", "season_ledger", "season_snapshots",
)

# D-1: the Harbor Ledger -- one compact row per resolved season. (key, header label).
LEDGER_LIMIT = 120
LEDGER_COLUMNS = [
    ("season", "Season"),
    ("funds", "Funds"),
    ("acidity", "Acidity"),
    ("fish_yield", "Fish yield"),
    ("damage", "Damage"),
    ("rows_dry", "Rows dry"),
    ("population", "Population"),
    ("tier", "Tier"),
    ("invested", "Invested"),
]
LEDGER_KEYS = [key for key, _label in LEDGER_COLUMNS]

# D-4: the season scrubber. One compact snapshot per resolved season
# ([season, sea_level, heritage code, retreat rows]); everything else the
# scrubbed view shows (funds, acidity, yield, tier, rows dry, population) is
# already in the ledger, so a snapshot stays about 30 bytes in a save.
SNAPSHOT_LIMIT = LEDGER_LIMIT
HERITAGE_CODES = {HERITAGE_UNPROTECTED: "u", HERITAGE_PROTECTED: "p", HERITAGE_LOST: "l"}

# D-22 / D-23: graph view options (this browser only, never in a save).
GRAPH_RANGES = [("10", "Last 10"), ("20", "Last 20"), ("all", "All")]
GRAPH_PREFS_KEY = "tide_graph_prefs_v1"
GRAPH_MARKER_LIMIT = 40

# D-2: the session library (this browser only).
LIBRARY_KEY = "tide_session_library_v1"
LIBRARY_LIMIT = 12
LIBRARY_MIN_SEASONS = 3
LIBRARY_CURRENT = "current"

# D-6: the season planner looks at most this many seasons ahead.
PLANNER_MAX_SEASONS = 5
PLANNER_MIN_SEASONS = 3
PLANNER_MAX_PER_CATEGORY = 9
PLANNER_RISK_SEASONS = 2

# D-9: the Harbor Almanac (this browser only, lifetime across sessions).
ALMANAC_KEY = "tide_almanac_v1"

# D-15: Advance x5 runs up to this many quiet seasons in a row.
ADVANCE_BATCH = 5
# D-15: an unprotected heritage site this close to flooding (and affordable
# to protect) is a reason for Advance x5 to stop and let the player act.
HERITAGE_RISK_SEASONS = 1

# D-17: ticker history filter chips (key, label). "other" messages only show under All.
TICKER_FILTERS = [
    ("all", "All"),
    ("fish", "Fish"),
    ("sea", "Sea"),
    ("economy", "Economy"),
    ("storm", "Storm"),
    ("chronicle", "Chronicle"),
]

ACIDITY_RISE_PER_OUTPUT = 2.0
ACIDITY_FALL_PER_REDUCTION = 1.5

# Delayed consequence: this season's fishing yield depends on acidity
# from FISH_LAG_SEASONS ago, not today's number — the whole point being
# that damage from today's choices doesn't show up right away.
FISH_LAG_SEASONS = 3
# D9 (planning/TODO.md's per-game Tide section): an optional "harder lag"
# difficulty mode -- a longer, more punishing gap between cause and
# effect for players who want the delayed-consequence lesson turned up.
# Toggled any time via SettlementState.set_hard_lag_mode(); only changes
# which lag length future fish_yield_multiplier()/next_season_fish_yield_
# preview() calls read, so flipping it mid-session never crashes -- it
# just re-aims the same lookback at a different point in acidity_history.
FISH_LAG_SEASONS_HARD = 6
FISH_DAMAGE_SCALE = 50.0
MIN_FISH_MULTIPLIER = 0.2
# D14: below this fraction, an upcoming fish-yield drop is worth a
# heads-up banner rather than just quietly landing in the ticker log.
FISH_YIELD_WARNING_THRESHOLD = 0.7

# Sea level rises every season no matter what the player does — adaptation
# infrastructure never stops or slows the rise itself, only how much
# economic damage that rise translates into. Capped so it can never fully
# neutralize the threat outright.
SEA_LEVEL_RISE_PER_SEASON = 5.0
MAX_DAMPENING = 0.9

# D19: real-world-grounded sea-level-rise trajectories, chosen at game
# start (locked once the first season is played). "moderate" is the
# original SEA_LEVEL_RISE_PER_SEASON, so an untouched game is unchanged.
SEA_SCENARIOS = {
    "conservative": {"label": "Conservative (low-emissions pathway)", "rise": 4.0},
    "moderate": {"label": "Moderate (intermediate pathway)", "rise": SEA_LEVEL_RISE_PER_SEASON},
    "severe": {"label": "Severe (high-emissions pathway)", "rise": 6.5},
}
DEFAULT_SEA_SCENARIO = "moderate"

# D20/D28: one glyph per adaptation tier, shared by the investments
# panel badge (a non-colour cue, like the seawall texture per tier).
TIER_BADGES = ["⚪", "🧱", "🏗️", "🛡️", "🌊"]

# D23: yield must have dipped to/below this before a rebuild counts as a
# "recovery", and must climb back to/above RECOVERED to celebrate it.
FISH_CRASH_LEVEL = 0.7
FISH_RECOVERED_LEVEL = 0.9

# Iteration Pass 2 — adaptation tech tree: dampening no longer scales
# continuously with adaptation capacity. Instead, sustained investment
# (cumulative capacity — it never decays, so "sustained" just means
# "keep investing") crosses thresholds that unlock discrete, stronger
# tiers, each with its own visible coastline signature. Ordered
# ascending by threshold; the top tier's dampening matches the old
# MAX_DAMPENING cap so the ceiling behavior is unchanged.
# D2 (planning/TODO.md's per-game Tide section): a fourth, tougher tier
# above the old ceiling. MAX_DAMPENING now describes the third tier
# (Reinforced seawalls) rather than the top of the whole list -- the new
# top tier's own dampening is its own literal, same as every other tier.
ADAPTATION_TIERS = [
    {"threshold": 0, "name": "No adaptation", "dampening": 0.0},
    {"threshold": 3, "name": "Sandbag berms", "dampening": 0.3},
    {"threshold": 6, "name": "Seawalls", "dampening": 0.6},
    {"threshold": 10, "name": "Reinforced seawalls", "dampening": MAX_DAMPENING},
    {"threshold": 15, "name": "Storm-surge barriers", "dampening": 0.95},
]

# D16: splits what used to be a single, purely fishing-flavored Output
# investment into a player-chosen mix between fishing-tied income (rises
# and falls with fish_yield_multiplier(), same as the original formula)
# and flat industrial income (unaffected by the fish-stock crash, but
# dirtier). "fishing" is the default and reproduces the exact original
# formula byte-for-byte (fishing_share=1.0, acidity_multiplier=1.0), so
# every save/behavior that predates this feature keeps working unchanged
# unless the player actively picks a different mix.
OUTPUT_MIX = {
    "fishing": {"fishing_share": 1.0, "acidity_multiplier": 1.0},
    "mixed": {"fishing_share": 0.5, "acidity_multiplier": 1.15},
    "industry": {"fishing_share": 0.0, "acidity_multiplier": 1.4},
}
DEFAULT_OUTPUT_MIX = "fishing"

# Coastline tile grid: row 0 is the top of the grid (highest ground, high
# threshold, floods last); the bottom row is the lowest ground and floods
# first — water rises visually from the bottom, matching a real coastline.
COASTLINE_ROWS = 6
COASTLINE_COLS = 8
ROW_FLOOD_STEP = 15.0

# D3: the sister settlement (the lighter version of a multi-settlement mode).
# An optional second coastal settlement that SHARES your funds and your
# adaptation tier (so one investment protects both) but has its own, lower-lying
# coastline: the same sea rise reaches it SISTER_EXPOSURE times harder, and its
# rows flood SISTER_LEVEL_OFFSET earlier. Each season it pays SISTER_FUNDS_PER_DAMAGE
# funds for every point of damage it takes (after the shared dampening) and
# earns SISTER_INCOME from its own fishing and trade. It is not a second game to
# manage: it only adds a second, differently exposed thing that your one set of
# decisions has to protect. Off by default and turned on once, by choice.
SISTER_EXPOSURE = 1.3
SISTER_LEVEL_OFFSET = 20.0
SISTER_FUNDS_PER_DAMAGE = 2.0
SISTER_INCOME = 10.0

LAND = "land"
FLOODED = "flooded"

# Iteration-pass addition: a normalization ceiling for the sea-level
# meter — the level at which the entire coastline grid (even the
# highest row) would be flooded.
SEA_LEVEL_METER_MAX = ROW_FLOOD_STEP * COASTLINE_ROWS

# Iteration-pass addition: how many recent delayed-effect messages the
# ticker keeps visible at once.
TICKER_LOG_LIMIT = 5

# D5: a much longer, persisted history behind an expandable panel,
# alongside (not instead of) the short live ticker above -- capped, not
# unbounded, so a very long session's save payload doesn't grow forever.
TICKER_FULL_HISTORY_LIMIT = 200

# D4: purely decorative wave-cue speed range, in seconds per animation
# cycle -- calmest (slowest) at an empty meter, fastest at a full one.
# Python computes the duration from sea_level_fraction() and sets it as
# an inline style; the CSS @keyframes itself (`sea-level-wave-cue-drift`
# in style.css) never changes, same "Python computes, CSS keyframe just
# plays it" pattern as this hub's other percentage-driven visuals.
SEA_LEVEL_WAVE_CUE_MAX_DURATION = 6.0
SEA_LEVEL_WAVE_CUE_MIN_DURATION = 1.5


def sea_level_wave_cue_duration(fraction):
    """Maps a 0..1 sea-level fraction to an animation-duration in seconds,
    linearly interpolating from the slow/calm end down to the fast end as
    the fraction climbs. Purely cosmetic -- never read back, never affects
    game state."""
    fraction = max(0.0, min(1.0, fraction))
    span = SEA_LEVEL_WAVE_CUE_MAX_DURATION - SEA_LEVEL_WAVE_CUE_MIN_DURATION
    return SEA_LEVEL_WAVE_CUE_MAX_DURATION - span * fraction


# D-8 (2026-10-11): named coastlines. Each has its own elevation profile (the sea level at which each row floods, row 0
# at the top), heritage sites, economy weights (multipliers on Output, tourism and aquaculture income), storm interval
# and surge size. "open" is the standard game and reproduces every number the game used before coastlines existed.
DEFAULT_COASTLINE = "open"
_OPEN_THRESHOLDS = tuple((COASTLINE_ROWS - row) * ROW_FLOOD_STEP for row in range(COASTLINE_ROWS))
COASTLINES = {
    "open": {
        "label": "Open coast (the standard game)",
        "blurb": "A gently sloping shore: one row floods about every three seasons.",
        "thresholds": _OPEN_THRESHOLDS,
        "heritage": HERITAGE_SITES,
        "output": 1.0, "tourism": 1.0, "aquaculture": 1.0,
        "storm_interval": STORM_INTERVAL, "surge": 1.0,
    },
    "delta": {
        "label": "Low delta town",
        "blurb": "Flat, fertile and close to the water: rows go under early, but the fishing is rich.",
        "thresholds": (72.0, 60.0, 48.0, 35.0, 23.0, 10.0),
        "heritage": [
            {"id": "grain-hall", "name": "Old grain hall", "emoji": "\U0001F3DB\ufe0f", "row": 3, "cost": 110},
            {"id": "ferry", "name": "Ferry landing", "emoji": "\u26F4\ufe0f", "row": 5, "cost": 150},
        ],
        "output": 1.2, "tourism": 0.9, "aquaculture": 1.1,
        "storm_interval": 4, "surge": 1.0,
    },
    "headland": {
        "label": "Rocky headland",
        "blurb": "Steep ground that floods late, a thin fishery and a scenic harbour: strong tourism, and storms from the open sea.",
        "thresholds": (120.0, 100.0, 80.0, 60.0, 45.0, 30.0),
        "heritage": [
            {"id": "watchtower", "name": "Cliff watchtower", "emoji": "\U0001F3F0", "row": 3, "cost": 130},
            {"id": "chapel", "name": "Harbour chapel", "emoji": "\u26EA", "row": 4, "cost": 100},
        ],
        "output": 0.8, "tourism": 1.5, "aquaculture": 0.8,
        "storm_interval": 4, "surge": 1.15,
    },
    "atoll": {
        "label": "Atoll",
        "blurb": "A narrow ring of land that stays dry for a long while, then goes almost all at once. A sheltered lagoon suits aquaculture and visitors, and storms are rarer.",
        "thresholds": (80.0, 73.0, 66.0, 59.0, 52.0, 45.0),
        "heritage": [
            {"id": "coral-shrine", "name": "Coral shrine", "emoji": "\U0001F41A", "row": 3, "cost": 100},
            {"id": "lagoon-school", "name": "Lagoon school", "emoji": "\U0001F3EB", "row": 4, "cost": 140},
        ],
        "output": 0.85, "tourism": 1.2, "aquaculture": 1.5,
        "storm_interval": 6, "surge": 1.0,
    },
    "port": {
        "label": "Dredged port",
        "blurb": "Reclaimed land behind a working quay: the best Output income, little tourism and a cheap, exposed first row.",
        "thresholds": (85.0, 70.0, 55.0, 40.0, 30.0, 20.0),
        "heritage": [
            {"id": "customs-house", "name": "Old customs house", "emoji": "\U0001F3E2", "row": 3, "cost": 120},
            {"id": "crane", "name": "Steam crane", "emoji": "\U0001F3D7\ufe0f", "row": 5, "cost": 160},
        ],
        "output": 1.3, "tourism": 0.6, "aquaculture": 0.7,
        "storm_interval": 5, "surge": 1.0,
    },
}
COASTLINE_IDS = tuple(COASTLINES)


INVEST_LABELS = {"output": "Output", "reduction": "Acidity Reduction", "adaptation": "Adaptation"}
