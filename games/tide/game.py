"""Tide — Ocean Acidification & Sea-Level Rise Game.

Runs in-browser via Pyodide. Milestone 1: the core settlement loop —
seasonal rounds, funds, and three investment categories (output/
reduction/adaptation), mirroring Grid's build-capacity pattern. Acidity,
sea-level rise, and the tile-grid coastline land in later milestones.
"""

import copy
import html
import json
import math

import info_page
import js as _js
from js import document, setTimeout
from pyodide.ffi import create_proxy

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


def row_flood_threshold(row):
    elevation = COASTLINE_ROWS - row  # bottom row (index ROWS-1) = elevation 1
    return elevation * ROW_FLOOD_STEP


def tile_row_state(row, sea_level):
    return FLOODED if sea_level >= row_flood_threshold(row) else LAND


def coastline_grid(sea_level):
    """COASTLINE_ROWS x COASTLINE_COLS grid of "land"/"flooded" strings —
    pure state, no DOM — so the flood thresholds are testable without a
    browser."""
    return [
        [tile_row_state(row, sea_level) for _ in range(COASTLINE_COLS)]
        for row in range(COASTLINE_ROWS)
    ]


def flooded_row_count(sea_level):
    """How many of the COASTLINE_ROWS rows are flooded at a given sea
    level -- every row shares one state across all COASTLINE_COLS
    columns, so counting rows (not tiles) is the meaningful unit for
    "how much coastline is gone" (D4/D11/achievements all read this)."""
    return sum(1 for row in range(COASTLINE_ROWS) if tile_row_state(row, sea_level) == FLOODED)


class SettlementState:
    def __init__(self):
        self.season = 1
        self.funds = STARTING_FUNDS
        self.capacity = {c: 0 for c in CATEGORIES}
        self.acidity = 0.0
        self.acidity_history = []
        self.sea_level = 0.0
        self.cumulative_damage = 0.0
        self.undampened_damage_total = 0.0
        self.damage_log = []
        self.ticker_log = []
        # Iteration Pass 3 — fires once, the first season the damage curve
        # visibly flattens, so the ticker confirms recovery instead of
        # only the static damage-trend text passively updating.
        self.trend_flattening_announced = False

        # D5: the same ticker messages as ticker_log, but never truncated
        # below TICKER_FULL_HISTORY_LIMIT -- backs the expandable "full
        # history" panel, ticker_log stays the short live-glance version.
        self.ticker_full_history = []
        # D9: optional harder delayed-consequence lag (see
        # FISH_LAG_SEASONS_HARD/_effective_fish_lag()).
        self.hard_lag_mode = False
        # D3: the optional sister settlement (see SISTER_* above).
        self.sister_enabled = False
        self.sister_cumulative_damage = 0.0
        self.sister_net_funds = 0.0
        # D16: which income/acidity mix Output investment currently uses.
        # "fishing" reproduces the original single-formula behavior.
        self.output_mix = DEFAULT_OUTPUT_MIX
        # D15: fish_yield_multiplier() sampled once per season, parallel
        # to acidity_history, so a mini-graph can chart both together.
        self.fish_yield_history = []
        # D17: fires once, the very first time any coastline row floods.
        self.first_flood_announced = False
        # D18: a player-chosen checkpoint the "then vs. now" comparison
        # (render_coastline_comparison()/then_vs_now_text()) measures
        # against, instead of always the literal Season 1 start. Defaults
        # to the real start, so an untouched game behaves exactly as
        # before this feature existed.
        self.baseline_season = 1
        self.baseline_sea_level = 0.0
        self.baseline_damage = 0.0

        # Achievements' new tracked state (ACHIEVEMENTS-SYSTEM-DESIGN.md
        # §4): each of these answers "did this ever happen / how far did
        # this ever go", which the current-moment fields above can't
        # answer on their own once the number moves back the other way
        # (funds get spent, fish yield recovers, acidity falls).
        self.min_fish_yield_ever = 1.0
        self.max_acidity_ever = 0.0
        self.max_funds_ever = STARTING_FUNDS
        # Set once, inside invest()'s own tier-unlock branch, the instant
        # the top adaptation tier is reached while zero coastline rows are
        # flooded yet -- a genuine "before" fact that flooded_row_count()
        # alone can't recover later once the sea catches up.
        self.fortified_in_time_earned = False

        # D2: adaptation tier index active during each season, parallel
        # to damage_log, so the worst-season callout can name what was
        # (or wasn't) protecting the coast then.
        self.tier_log = []
        # D30: the one-time "takes effect next season" note for hard lag.
        self.hard_lag_note_seen = False
        # D23: a crash is "open" once yield dips to FISH_CRASH_LEVEL; the
        # recovery celebration fires once when it climbs back.
        self.fish_crash_open = False
        self.recovery_celebrated_season = 0
        # D19: sea-level-rise scenario (locked after the first season).
        self.sea_scenario = DEFAULT_SEA_SCENARIO
        # D29: a light diegetic layer -- an optional player-chosen name
        # plus a short chronicle of the settlement's notable moments.
        self.settlement_name = ""
        self.chronicle = []
        # D17: id -> HERITAGE_* status.
        self.heritage = {site["id"]: HERITAGE_UNPROTECTED for site in HERITAGE_SITES}
        # D21: how many facts revealed, and the season of the last report.
        self.monitoring_reports = 0
        self.monitoring_last_season = 0
        # D13: opt-in storm seasons.
        self.storm_mode = False
        self.storm_log = []
        # D1: rows given up on purpose (row indices, lowest first).
        self.retreat_rows = []
        # D5 / D15: population and displacement counters.
        self.population = POP_START
        self.peak_population = POP_START
        self.displaced_total = 0
        self.relocated_total = 0
        # D11: level of each diversified income source.
        self.diversification = {"tourism": 0, "aquaculture": 0}
        # D27: a saved snapshot of the run, and the "foresight" record of
        # what happened after it the last time the player replayed from it.
        self.checkpoint = None
        self.foresight = []
        self.replay_count = 0
        # D-1: one dict per resolved season (see _record_ledger_entry()).
        self.season_ledger = []
        # D-4: one compact snapshot per resolved season (see _record_snapshot()).
        self.season_snapshots = []

    # ---- D1 managed retreat ------------------------------------------
    def row_lost(self, row):
        """True for a flooded row and for one given up by managed retreat."""
        return row in self.retreat_rows or tile_row_state(row, self.sea_level) == FLOODED

    def next_retreat_row(self):
        for row in range(COASTLINE_ROWS - 1, -1, -1):
            if not self.row_lost(row):
                return row
        return None

    def can_retreat(self):
        return (
            len(self.retreat_rows) < RETREAT_MAX_STEPS
            and self.funds >= RETREAT_COST
            and self.next_retreat_row() is not None
        )

    def managed_retreat(self):
        if not self.can_retreat():
            return False
        row = self.next_retreat_row()
        self.funds -= RETREAT_COST
        self.retreat_rows.append(row)
        self._log_ticker(
            f"Managed retreat: row {row + 1} was cleared and its people rehoused inland — "
            f"sea-level damage is now permanently {RETREAT_DAMAGE_CUT * 100:.0f}% lower per step."
        )
        self._chronicle_event(f"The council chose an orderly retreat from row {row + 1}.")
        self._update_heritage()
        self._update_population(orderly=True)
        return True

    # ---- D5 / D15 population -----------------------------------------
    def housing_capacity(self):
        land_rows = sum(1 for row in range(COASTLINE_ROWS) if not self.row_lost(row))
        return land_rows * (POP_PER_ROW + POP_PER_ROW_PER_TIER * self.current_tier_index())

    def _update_population(self, orderly=False):
        """Displaces the excess when housing shrinks below the population,
        otherwise grows toward capacity while fish yield is healthy."""
        capacity = self.housing_capacity()
        if self.population > capacity:
            displaced = self.population - capacity
            self.population = capacity
            if orderly or self.retreat_rows:
                relocated = displaced // 2 if not orderly else displaced
                self.relocated_total += relocated
                self.displaced_total += displaced - relocated
            else:
                self.displaced_total += displaced
            self._log_ticker(
                f"{displaced} people had to leave the flooded coast"
                + (" (many rehoused in an orderly retreat)." if orderly or self.retreat_rows else " — refugees moving inland.")
            )
            self._chronicle_event(f"{displaced} residents relocated inland.")
        elif (
            self.population < capacity
            and self.fish_yield_multiplier() >= POP_GROWTH_MIN_FISH_YIELD
        ):
            growth = max(1, round(self.population * POP_GROWTH_RATE))
            self.population = min(capacity, self.population + growth)
        self.peak_population = max(self.peak_population, self.population)

    def population_text(self):
        text = f"Population {self.population} of {self.housing_capacity()} housing (peak {self.peak_population})."
        if self.displaced_total or self.relocated_total:
            text += f" Displaced so far: {self.displaced_total}; rehoused in orderly retreat: {self.relocated_total}."
        return text

    # ---- D11 diversification -----------------------------------------
    def diversify(self, kind):
        if kind not in DIVERSIFY_COST or self.diversification[kind] >= DIVERSIFY_MAX_LEVEL:
            return False
        if self.funds < DIVERSIFY_COST[kind]:
            return False
        self.funds -= DIVERSIFY_COST[kind]
        self.diversification[kind] += 1
        self._log_ticker(f"Economy diversified: {kind} is now level {self.diversification[kind]}.")
        return True

    def diversified_income(self):
        """(tourism, aquaculture) income per season at the current state."""
        land_rows = sum(1 for row in range(COASTLINE_ROWS) if not self.row_lost(row))
        tourism = self.diversification["tourism"] * (
            TOURISM_INCOME_PER_LEVEL * land_rows / COASTLINE_ROWS
            + TOURISM_HERITAGE_BONUS * self.protected_heritage_count()
        )
        multiplier = max(AQUACULTURE_MIN_MULTIPLIER, 1 - self.acidity / AQUACULTURE_ACIDITY_SCALE)
        aquaculture = self.diversification["aquaculture"] * AQUACULTURE_INCOME_PER_LEVEL * multiplier
        return tourism, aquaculture

    # ---- D27 checkpoint replay ---------------------------------------
    def set_checkpoint(self):
        snapshot = get_state()
        for key in CHECKPOINT_DROP_KEYS:
            snapshot.pop(key, None)
        snapshot.pop("checkpoint", None)
        snapshot.pop("foresight", None)
        self.checkpoint = snapshot
        self._log_ticker(f"Checkpoint saved at Season {self.season}.")

    def can_replay(self):
        return self.checkpoint is not None and self.season > self.checkpoint["season"]

    def foresight_text(self):
        """What the earlier run did in the seasons ahead, for the season the
        replay is currently in."""
        if not self.foresight:
            return ""
        upcoming = [e for e in self.foresight if e["season"] >= self.season][:3]
        if not upcoming:
            return "You have passed everything the earlier run showed you."
        parts = [
            f"Season {e['season']}: fish yield {e['fish_yield'] * 100:.0f}%, "
            f"{e['damage']:.0f} damage, {e['flooded']} row(s) flooded"
            for e in upcoming
        ]
        return "Foresight from your earlier run — " + " | ".join(parts)

    # ---- D17 heritage ------------------------------------------------
    def protect_heritage(self, site_id):
        site = next((x for x in HERITAGE_SITES if x["id"] == site_id), None)
        if site is None or self.heritage.get(site_id) != HERITAGE_UNPROTECTED:
            return False
        if self.funds < site["cost"] or self.row_lost(site["row"]):
            return False
        self.funds -= site["cost"]
        self.heritage[site_id] = HERITAGE_PROTECTED
        self._log_ticker(f"{site['name']} is now protected — it will outlast the flood, at a small upkeep each season.")
        self._chronicle_event(f"Townsfolk pooled funds to protect the {site['name'].lower()}.")
        return True

    def protected_heritage_count(self):
        return sum(1 for v in self.heritage.values() if v == HERITAGE_PROTECTED)

    def _update_heritage(self):
        """Unprotected sites whose row has flooded are lost; protected ones
        cost upkeep (never below zero funds)."""
        for site in HERITAGE_SITES:
            if (
                self.heritage.get(site["id"]) == HERITAGE_UNPROTECTED
                and self.row_lost(site["row"])
            ):
                self.heritage[site["id"]] = HERITAGE_LOST
                self._log_ticker(f"The {site['name'].lower()} has been lost to the sea.")
                self._chronicle_event(f"The {site['name'].lower()} was swallowed by the sea.")
        self.funds = max(0.0, self.funds - HERITAGE_UPKEEP * self.protected_heritage_count())

    # ---- D21 citizen science -----------------------------------------
    def can_monitor(self):
        if self.monitoring_reports >= len(CITIZEN_SCIENCE_FACTS) or self.funds < MONITOR_COST:
            return False
        return (
            self.monitoring_last_season == 0
            or self.season - self.monitoring_last_season >= MONITOR_COOLDOWN_SEASONS
        )

    def fund_monitoring(self):
        if not self.can_monitor():
            return False
        self.funds -= MONITOR_COST
        self.monitoring_reports += 1
        self.monitoring_last_season = self.season
        self._log_ticker("Monitoring report in: " + CITIZEN_SCIENCE_FACTS[self.monitoring_reports - 1])
        return True

    def revealed_facts(self):
        return CITIZEN_SCIENCE_FACTS[: self.monitoring_reports]

    # ---- D13 storms --------------------------------------------------
    def set_storm_mode(self, enabled):
        self.storm_mode = bool(enabled)

    def storm_this_season(self):
        return self.storm_mode and self.season % STORM_INTERVAL == 0

    def seasons_until_storm(self):
        """0 if the storm lands when this season resolves; None when off."""
        if not self.storm_mode:
            return None
        return (-self.season) % STORM_INTERVAL

    def storm_surge_strength(self):
        return STORM_BASE_SURGE + STORM_SURGE_GROWTH * len(self.storm_log)

    def _resolve_storm(self):
        """Called while advance_season() resolves a season. The surge is cut
        by the current dampening; what gets through costs funds."""
        surge = self.storm_surge_strength()
        taken = surge * (1 - self.dampening_fraction())
        funds_lost = min(self.funds, taken * STORM_FUNDS_PER_DAMAGE)
        self.funds -= funds_lost
        self.storm_log.append(
            {"season": self.season, "surge": surge, "taken": taken, "blocked": surge - taken}
        )
        self.storm_log = self.storm_log[-20:]
        self._log_ticker(
            f"⛈️ Storm surge in Season {self.season}: {surge - taken:.0f} of {surge:.0f} held back "
            f"by your defences; the rest cost {funds_lost:.0f} funds."
        )
        self._chronicle_event(f"A storm surge struck; defences held back {surge - taken:.0f} of {surge:.0f}.")

    def set_settlement_name(self, name):
        """D29: trims, collapses whitespace and caps the length; anything
        that isn't a string is ignored (no crash, no partial change)."""
        if not isinstance(name, str):
            return False
        cleaned = " ".join(name.split())[:SETTLEMENT_NAME_MAX]
        self.settlement_name = cleaned
        return True

    def display_name(self):
        return self.settlement_name or "Your settlement"

    def _chronicle_event(self, text):
        """D29: appends one dated line to the settlement's history."""
        self.chronicle.append({"season": self.season, "text": text})
        self.chronicle = self.chronicle[-CHRONICLE_LIMIT:]

    def chronicle_lines(self):
        return [f"Season {e['season']}: {e['text']}" for e in self.chronicle]

    def tide_offset(self):
        """D8: this season's tide height relative to mean sea level, a
        deterministic function of the season number (so it needs no saved
        state and a loaded save shows the same tide)."""
        return round(TIDE_AMPLITUDE * math.sin(self.season * TIDE_PERIOD_FACTOR), 1)

    def tide_label(self):
        offset = self.tide_offset()
        if offset >= TIDE_HIGH_CUTOFF:
            return "High"
        if offset <= -TIDE_HIGH_CUTOFF:
            return "Low"
        return "Mid"

    def tidal_rows(self):
        """D8: rows that are dry at mean sea level but that this season's
        tide would wash over."""
        effective = self.sea_level + self.tide_offset()
        return [
            row
            for row in range(COASTLINE_ROWS)
            if self.sea_level < row_flood_threshold(row) <= effective
        ]

    def tide_text(self):
        offset = self.tide_offset()
        rows = self.tidal_rows()
        wash = (
            f" — the tide is washing over {len(rows)} otherwise-dry row(s)."
            if rows
            else " — no dry rows are reached."
        )
        return f"Tide this season: {self.tide_label()} ({offset:+.1f} vs. mean sea level){wash}"

    def delayed_consequence_rows(self):
        """D7: for each banked season, the acidity fraction it recorded
        and the fish yield it will cause `lag` seasons later, as
        (season, acidity_fraction, arrival_season, projected_yield)."""
        lag = self._effective_fish_lag()
        rows = []
        for i, acidity in enumerate(self.acidity_history):
            projected = max(MIN_FISH_MULTIPLIER, 1 - acidity / FISH_DAMAGE_SCALE)
            rows.append((i + 1, min(1.0, acidity / FISH_DAMAGE_SCALE), i + 1 + lag, projected))
        return rows

    def delayed_consequence_text(self):
        rows = self.delayed_consequence_rows()
        if not rows:
            return "Advance a season to see today's acidity choices lined up against their later fish-yield impact."
        season, _fraction, arrival, projected = rows[-1]
        return (
            f"Acidity banked in Season {season} reaches fish stocks in Season {arrival}: "
            f"yield of about {projected * 100:.0f}% from that season's acidity alone."
        )

    def sea_rise_per_season(self):
        return SEA_SCENARIOS[self.sea_scenario]["rise"]

    def set_sea_scenario(self, scenario):
        """D19: only while nothing has been played yet -- changing the
        trajectory mid-run would silently rewrite history."""
        if scenario not in SEA_SCENARIOS or self.damage_log or self.season != 1:
            return False
        self.sea_scenario = scenario
        return True

    def invest(self, category):
        cost = INVEST_COST[category]
        if self.funds < cost:
            return False
        old_tier_index = self.current_tier_index() if category == "adaptation" else None
        self.funds -= cost
        self.capacity[category] += 1
        if category == "adaptation":
            new_tier_index = self.current_tier_index()
            if new_tier_index > old_tier_index:
                self._record_tier_unlock_message(new_tier_index)
                if (
                    new_tier_index == len(ADAPTATION_TIERS) - 1
                    and flooded_row_count(self.sea_level) == 0
                ):
                    self.fortified_in_time_earned = True
        return True

    def set_output_mix(self, mix):
        """D16: switches which income/acidity mix Output investment uses
        going forward. Invalid mix names are ignored (no crash, no
        partial state change) -- the same "degrade quietly" posture as
        set_hard_lag_mode()."""
        if mix in OUTPUT_MIX:
            self.output_mix = mix
            return True
        return False

    def set_hard_lag_mode(self, enabled):
        """D9: toggles the delayed-consequence lag length. Safe to flip
        mid-session -- it only changes which index _effective_fish_lag()
        reads out of acidity_history on the next call, nothing is
        recomputed retroactively."""
        enabled = bool(enabled)
        first_time = enabled != self.hard_lag_mode and not self.hard_lag_note_seen
        self.hard_lag_mode = enabled
        if first_time:
            # D30: one-time confirmation, via the same ticker the player
            # already reads.
            self.hard_lag_note_seen = True
            self._log_ticker(
                "Lag mode changed — the new lag takes effect from next season's fish yield."
            )

    def set_comparison_baseline(self):
        """D18: lets the player re-anchor the "then vs. now" comparison
        (both the coastline grids and then_vs_now_text()) to right now,
        instead of the literal Season 1 start -- useful for comparing
        "since I changed my strategy" rather than only "since the very
        beginning"."""
        self.baseline_season = self.season
        self.baseline_sea_level = self.sea_level
        self.baseline_damage = self.cumulative_damage

    def _effective_fish_lag(self):
        """D9: which lag length is currently live -- the hard-mode toggle
        only ever changes this lookup, never acidity_history itself."""
        return FISH_LAG_SEASONS_HARD if self.hard_lag_mode else FISH_LAG_SEASONS

    def fish_yield_multiplier(self):
        """1.0 (full yield) until enough seasons have passed for the lag
        to "arrive" — then reflects acidity from _effective_fish_lag()
        seasons ago."""
        lag = self._effective_fish_lag()
        if len(self.acidity_history) < lag:
            return 1.0
        lagged_acidity = self.acidity_history[-lag]
        return max(MIN_FISH_MULTIPLIER, 1 - lagged_acidity / FISH_DAMAGE_SCALE)

    def next_season_fish_yield_preview(self):
        """D14: what fish_yield_multiplier() will read out *next* season,
        computed from acidity already banked in acidity_history -- the
        lag means this is always knowable one season ahead of time.
        Returns None once there isn't yet enough history to preview (the
        same "hasn't arrived yet" case fish_yield_multiplier() itself
        handles by returning a flat 1.0)."""
        lag = self._effective_fish_lag()
        if lag <= 1:
            return None
        if len(self.acidity_history) < lag - 1:
            return None
        lagged_acidity = self.acidity_history[-(lag - 1)]
        return max(MIN_FISH_MULTIPLIER, 1 - lagged_acidity / FISH_DAMAGE_SCALE)

    def enable_sister(self):
        """D3: switches the sister settlement on (once; it cannot be turned off,
        since its history is part of the run)."""
        if self.sister_enabled:
            return False
        self.sister_enabled = True
        return True

    def sister_sea_level(self):
        return self.sea_level + SISTER_LEVEL_OFFSET

    def sister_rows_flooded(self):
        """How many of the sister's COASTLINE_ROWS rows the sea has reached."""
        return sum(1 for row in range(COASTLINE_ROWS) if self.sister_sea_level() >= row_flood_threshold(row))

    def _advance_sister(self, rise):
        """D3: this season's effect of the sister on the shared funds. Called
        right after the main coastline's own rise, with that same `rise`."""
        if not self.sister_enabled:
            return
        damage = rise * SISTER_EXPOSURE * (1 - self.dampening_fraction())
        self.sister_cumulative_damage += damage
        net = SISTER_INCOME - damage * SISTER_FUNDS_PER_DAMAGE
        self.sister_net_funds += net
        self.funds += net

    def sister_text(self):
        if not self.sister_enabled:
            return ""
        return (
            f"Sister settlement (low-lying, shares your funds and seawall tier): "
            f"{self.sister_rows_flooded()} of {COASTLINE_ROWS} rows flooded, "
            f"{self.sister_cumulative_damage:.0f} damage so far, "
            f"{self.sister_net_funds:+.0f} funds net for you."
        )

    def current_tier_index(self):
        """Index into ADAPTATION_TIERS of the highest tier this
        settlement's cumulative adaptation investment has reached."""
        index = 0
        for i, tier in enumerate(ADAPTATION_TIERS):
            if self.capacity["adaptation"] >= tier["threshold"]:
                index = i
        return index

    def current_tier(self):
        return ADAPTATION_TIERS[self.current_tier_index()]

    def dampening_fraction(self):
        """Tier dampening, plus D1's permanent per-step cut from managed
        retreat (compounded, so it can never reach 100%)."""
        tier = self.current_tier()["dampening"]
        if not self.retreat_rows:
            return tier
        return 1 - (1 - tier) * (1 - RETREAT_DAMAGE_CUT * len(self.retreat_rows))

    def next_tier_progress_text(self):
        tier_index = self.current_tier_index()
        if tier_index == len(ADAPTATION_TIERS) - 1:
            return f"{self.current_tier()['name']} — maximum adaptation tier reached."
        next_tier = ADAPTATION_TIERS[tier_index + 1]
        return (
            f"{self.capacity['adaptation']}/{next_tier['threshold']} invested toward "
            f"{next_tier['name']} (next tier)."
        )

    def sea_level_fraction(self):
        """0..1 — sea level relative to the point where even the highest
        coastline row would flood. Iteration-pass addition, giving the
        sea-level indicator its own meter distinct from acidity/fish."""
        return min(1.0, self.sea_level / SEA_LEVEL_METER_MAX)

    def next_flood_estimate(self):
        """D3: seasons remaining (rounded up) until the next currently-
        unflooded row crosses its threshold, reading rows bottom-up since
        that's the order they actually flood in. Returns 0 once every row
        is already flooded -- "estimate" bottoms out at "already
        happened" rather than returning a nonsensical negative or None."""
        for row in range(COASTLINE_ROWS - 1, -1, -1):
            threshold = row_flood_threshold(row)
            if self.sea_level < threshold:
                remaining = threshold - self.sea_level
                return math.ceil(remaining / self.sea_rise_per_season())
        return 0

    def worst_season(self):
        """D12: the single highest-damage season played so far, as
        (season_number, damage) -- damage_log[i] was recorded during the
        season the settlement was in *before* advance_season()'s own
        self.season += 1, i.e. season i+1. None before any season has
        been played."""
        if not self.damage_log:
            return None
        worst_index = max(range(len(self.damage_log)), key=lambda i: self.damage_log[i])
        return worst_index + 1, self.damage_log[worst_index]

    def seasons_until_flood(self, row):
        """D26: seasons left at the current pace before `row` floods (0
        once it already has)."""
        remaining = row_flood_threshold(row) - self.sea_level
        if remaining <= 0:
            return 0
        return math.ceil(remaining / self.sea_rise_per_season())

    def worst_season_cause(self):
        """D2: names what was (or wasn't) protecting the coast during the
        worst season. Returns None with no data; for a save that predates
        tier_log, falls back to no explanation."""
        worst = self.worst_season()
        if worst is None:
            return None
        index = worst[0] - 1
        if index >= len(self.tier_log):
            return None
        tier = ADAPTATION_TIERS[self.tier_log[index]]
        if self.tier_log[index] == 0:
            return "no adaptation investment had reached a tier yet"
        return f"only {tier['name']} ({tier['dampening'] * 100:.0f}% dampening) was in place"

    def then_vs_now_damage_series(self):
        """D14: per-season damage since the baseline, for a sparkline."""
        return list(self.damage_log[max(0, self.baseline_season - 1):])

    def output_mix_preview(self, mix):
        """D22: per-season (income, acidity change) at current capacity
        for a given mix, using the live fish-yield lag -- what the
        dropdown would do if chosen now."""
        cfg = OUTPUT_MIX[mix]
        share = cfg["fishing_share"]
        income = self.capacity["output"] * OUTPUT_INCOME_PER_UNIT * (
            share * self.fish_yield_multiplier() + (1 - share)
        )
        acidity = (
            self.capacity["output"] * ACIDITY_RISE_PER_OUTPUT * cfg["acidity_multiplier"]
            - self.capacity["reduction"] * ACIDITY_FALL_PER_REDUCTION
        )
        return income, acidity

    def then_vs_now_text(self):
        """D4: a numeric companion to the visual coastline-comparison
        grids -- rows flooded and damage taken, measured against whatever
        baseline_* currently points at (Season 1 by default, or a
        player-chosen checkpoint via set_comparison_baseline())."""
        then_flooded = flooded_row_count(self.baseline_sea_level)
        now_flooded = flooded_row_count(self.sea_level)
        damage_since_baseline = self.cumulative_damage - self.baseline_damage
        return (
            f"Then (Season {self.baseline_season}): {then_flooded}/{COASTLINE_ROWS} rows flooded. "
            f"Now (Season {self.season}): {now_flooded}/{COASTLINE_ROWS} rows flooded — "
            f"{damage_since_baseline:.0f} damage taken since then."
        )

    def counterfactual_message(self):
        """D6: "what if you'd invested earlier" -- holds the *current*
        adaptation tier's dampening fixed across every season already
        played (instead of the tier actually ramping up over time the
        way it really did) and compares the resulting hypothetical
        cumulative damage to what actually happened. A positive
        difference is the hope-angle payoff made concrete: investing
        early (so the strong tier is active from season 1) beats reaching
        the same tier late."""
        seasons_played = len(self.damage_log)
        if seasons_played == 0:
            return "Play a few seasons to see what earlier adaptation investment could have saved."
        hypothetical_damage = (
            self.sea_rise_per_season() * (1 - self.dampening_fraction()) * seasons_played
        )
        difference = self.cumulative_damage - hypothetical_damage
        if difference <= 0.5:
            return (
                "Your current adaptation tier has been in place essentially the whole "
                "time — there's little counterfactual gap left to close."
            )
        return (
            f"If you'd had your current tier ({self.current_tier()['name']}) since Season 1, "
            f"you'd have taken about {hypothetical_damage:.0f} cumulative damage instead of your "
            f"actual {self.cumulative_damage:.0f} — investing early would have saved roughly "
            f"{difference:.0f} more."
        )

    def session_summary_text(self):
        """D7: a player-triggered end-of-session recap, not an auto
        pop-up (same "never forced mid-session" posture as the info
        page/achievements panels)."""
        worst = self.worst_season()
        worst_text = (
            f"Worst season: Season {worst[0]} ({worst[1]:.0f} damage)."
            if worst
            else "No seasons played yet."
        )
        tier = self.current_tier()
        return (
            f"Seasons played: {max(0, self.season - 1)}. Final funds: {self.funds:.0f}. "
            f"Cumulative damage: {self.cumulative_damage:.0f} (saved {self.damage_saved():.0f} "
            f"via adaptation). Adaptation tier reached: {tier['name']}. {worst_text}"
        )

    # ---- D-1 Harbor Ledger -------------------------------------------
    def rows_dry_count(self):
        return sum(1 for row in range(COASTLINE_ROWS) if not self.row_lost(row))

    def _record_ledger_entry(self, resolved_season, damage, fish_yield):
        """Appends the just-resolved season to the ledger (rounded, so a
        saved ledger stays small)."""
        self.season_ledger.append(
            {
                "season": resolved_season,
                "funds": round(self.funds, 1),
                "acidity": round(self.acidity, 2),
                "fish_yield": round(fish_yield, 3),
                "damage": round(damage, 2),
                "rows_dry": self.rows_dry_count(),
                "population": int(self.population),
                "tier": self.current_tier_index(),
                "invested": int(sum(self.capacity.values())),
            }
        )
        self.season_ledger = self.season_ledger[-LEDGER_LIMIT:]

    def sorted_ledger(self, key="season", descending=False):
        """The ledger sorted by one column (stable, so ties keep season order)."""
        if key not in LEDGER_KEYS:
            key = "season"
        return sorted(self.season_ledger, key=lambda entry: entry[key], reverse=bool(descending))

    def ledger_series(self, key):
        """One column's values in season order, for its small chart."""
        return [entry[key] for entry in self.season_ledger if key in entry]

    def ledger_summary_text(self, key="season", descending=True):
        if not self.season_ledger:
            return "No seasons recorded yet. Advance a season and its row appears here."
        first, last = self.season_ledger[0]["season"], self.season_ledger[-1]["season"]
        label = dict(LEDGER_COLUMNS)[key if key in LEDGER_KEYS else "season"]
        peak = max(self.season_ledger, key=lambda e: e["funds"])
        low = min(self.season_ledger, key=lambda e: e["fish_yield"])
        text = (
            f"{len(self.season_ledger)} season(s) recorded (Season {first} to {last}), "
            f"sorted by {label.lower()}, {'highest first' if descending else 'lowest first'}. "
            f"Peak funds {peak['funds']:.0f} in Season {peak['season']}; "
            f"lowest fish yield {low['fish_yield'] * 100:.0f}% in Season {low['season']}."
        )
        if self.season - 1 > len(self.season_ledger) and len(self.season_ledger) < LEDGER_LIMIT:
            text += " Seasons played before the ledger existed (older saves) are not listed."
        return text

    # ---- D-4 season scrubber ------------------------------------------
    def _record_snapshot(self, resolved_season):
        """What the ledger cannot rebuild: the sea level, which heritage
        sites were safe, and which rows had been given up, as of the end of
        the season just resolved."""
        code = "".join(HERITAGE_CODES.get(self.heritage.get(site["id"]), "u") for site in HERITAGE_SITES)
        self.season_snapshots.append(
            [resolved_season, round(self.sea_level, 1), code, list(self.retreat_rows)]
        )
        self.season_snapshots = self.season_snapshots[-SNAPSHOT_LIMIT:]

    def scrub_snapshot(self, position):
        """A read-only picture of the start of season `position` (what the
        player saw before investing in it), or None for the live season, a
        future one or one this save has no record of. Position 1 is the
        fixed starting state."""
        if not isinstance(position, int) or position < 1 or position >= self.season:
            return None
        heritage = {site["id"]: HERITAGE_UNPROTECTED for site in HERITAGE_SITES}
        if position == 1:
            return {
                "season": 1, "funds": float(STARTING_FUNDS), "acidity": 0.0, "fish_yield": 1.0,
                "damage_total": 0.0, "sea_level": 0.0, "tier": 0, "rows_dry": COASTLINE_ROWS,
                "population": POP_START, "heritage": heritage, "retreat_rows": [],
            }
        resolved = position - 1
        entry = next((e for e in self.season_ledger if e["season"] == resolved), None)
        snap = next((x for x in self.season_snapshots if x[0] == resolved), None)
        if entry is None or snap is None or len(self.damage_log) < resolved:
            return None
        for site, letter in zip(HERITAGE_SITES, snap[2]):
            heritage[site["id"]] = next((k for k, v in HERITAGE_CODES.items() if v == letter), HERITAGE_UNPROTECTED)
        return {
            "season": position, "funds": entry["funds"], "acidity": entry["acidity"],
            "fish_yield": entry["fish_yield"], "damage_total": sum(self.damage_log[:resolved]),
            "sea_level": snap[1], "tier": entry["tier"], "rows_dry": entry["rows_dry"],
            "population": entry["population"], "heritage": heritage, "retreat_rows": list(snap[3]),
        }

    def scrub_positions(self):
        """Every season start the scrubber can show (ascending)."""
        return [n for n in range(1, self.season) if self.scrub_snapshot(n) is not None]

    def scrub_text(self, snap):
        tier = ADAPTATION_TIERS[snap["tier"]]
        sites = "; ".join(
            f"{site['name'].lower()} {snap['heritage'][site['id']]}" for site in HERITAGE_SITES
        )
        return (
            f"Start of Season {snap['season']} (read-only, your live run is untouched): "
            f"funds {snap['funds']:.0f}, acidity {snap['acidity']:.1f}, fishing yield "
            f"{snap['fish_yield'] * 100:.0f}%, damage so far {snap['damage_total']:.0f}, "
            f"{snap['rows_dry']} of {COASTLINE_ROWS} rows dry, population {snap['population']}, "
            f"tier {TIER_BADGES[snap['tier']]} {tier['name']}. Heritage: {sites}."
        )

    # ---- D-15 Advance x5 ---------------------------------------------
    def fish_warning_active(self):
        """True while the fish-yield early warning (D14) is showing."""
        preview = self.next_season_fish_yield_preview()
        current = self.fish_yield_multiplier()
        return (
            preview is not None
            and preview < current - 1e-6
            and preview <= FISH_YIELD_WARNING_THRESHOLD
        )

    def heritage_at_risk(self):
        """Unprotected, still-dry heritage sites close to flooding that the
        player can afford to protect right now."""
        return [
            site
            for site in HERITAGE_SITES
            if self.heritage.get(site["id"]) == HERITAGE_UNPROTECTED
            and not self.row_lost(site["row"])
            and self.funds >= site["cost"]
            and self.seasons_until_flood(site["row"]) <= HERITAGE_RISK_SEASONS
        ]

    def monitoring_ready_again(self):
        """True the first season a monitoring crew is available again, for a
        player who has used monitoring before (so it never nags anyone else)."""
        return (
            self.monitoring_reports > 0
            and self.monitoring_last_season > 0
            and self.can_monitor()
            and self.season - self.monitoring_last_season == MONITOR_COOLDOWN_SEASONS
        )

    def attention_reasons(self):
        """Things that deserve a decision before another season passes, as
        (kind, plain-language text). Advance x5 only runs while this is empty."""
        reasons = []
        wait = self.seasons_until_storm()
        if wait is not None and wait <= 1:
            when = "this season" if wait == 0 else "next season"
            reasons.append(("storm", f"a storm surge is forecast for {when}"))
        if self.fish_warning_active():
            reasons.append(("fish", "a fish-yield warning is showing"))
        for site in self.heritage_at_risk():
            reasons.append(("heritage", f"the {site['name'].lower()} is at risk and can be protected"))
        if self.monitoring_ready_again():
            reasons.append(("monitor", "a monitoring crew is available again"))
        return reasons

    def advance_quiet_seasons(self, count=ADVANCE_BATCH):
        """Runs up to `count` seasons, stopping BEFORE any season that has
        something needing attention. Returns (seasons_run, stop_text); stop_text
        is None when all `count` seasons ran quietly."""
        run = 0
        for _ in range(max(0, int(count))):
            reasons = self.attention_reasons()
            if reasons:
                return run, "; ".join(text for _kind, text in reasons)
            self.advance_season()
            run += 1
        return run, None

    # ---- D-7 screen-reader text --------------------------------------
    def coast_view(self):
        """The live coastline as a plain dict, the same shape scrub_snapshot()
        returns, so one renderer and one description can draw either."""
        return {
            "sea_level": self.sea_level, "tier": self.current_tier_index(),
            "heritage": self.heritage, "retreat_rows": self.retreat_rows,
            "tidal": self.tidal_rows(),
        }

    def coastline_row_description(self, row, view=None, col=None):
        """e.g. "Row 5: dry, seawall tier 2" -- the text twin of one grid row. With `col`
        it names one tile ("Row 5, column 3: dry, ..."); only the heritage column mentions
        the heritage site. `view` describes a scrubbed past season instead of the live one."""
        view = view or self.coast_view()
        if row in view["retreat_rows"]:
            status = "cleared by managed retreat"
        elif tile_row_state(row, view["sea_level"]) == FLOODED:
            status = "flooded"
        else:
            status = "dry"
        parts = [status]
        tier_index = view["tier"]
        if tier_index and _is_seawall_row(row, tier_index):
            parts.append(f"seawall tier {tier_index}")
        site = next((x for x in HERITAGE_SITES if x["row"] == row), None)
        if site is not None and (col is None or col == HERITAGE_COL):
            heritage = view["heritage"].get(site["id"])
            parts.append(f"{site['name'].lower()} {heritage}")
        if row in view.get("tidal", ()):
            parts.append("washed by this season's tide")
        where = f"Row {row + 1}" + (f", column {col + 1}" if col is not None else "")
        return f"{where}: " + ", ".join(parts)

    def coastline_description(self):
        lines = [self.coastline_row_description(r) for r in range(COASTLINE_ROWS)]
        return (
            f"Coastline, {COASTLINE_ROWS} rows from row 1 (highest ground) to row {COASTLINE_ROWS} "
            f"(at the shore). {self.rows_dry_count()} dry. " + ". ".join(lines) + "."
        )

    def season_result_text(self):
        """What a screen reader announces after a season resolves."""
        if not self.season_ledger:
            return f"Season {self.season}."
        last = self.season_ledger[-1]
        text = (
            f"Season {last['season']} resolved. Now Season {self.season}. "
            f"Funds {self.funds:.0f}. Ocean acidity {self.acidity:.1f}. "
            f"Fishing yield {self.fish_yield_multiplier() * 100:.0f} percent. "
            f"Damage this season {last['damage']:.0f}. "
            f"{self.rows_dry_count()} of {COASTLINE_ROWS} coastline rows dry."
        )
        if self.ticker_log:
            text += " Latest: " + self.ticker_log[-1]
        return text

    # ---- D-18 copy as text -------------------------------------------
    def share_text(self):
        lines = [
            f"{self.display_name()} — a Tide settlement",
            self.session_summary_text(),
            f"Population {self.population} (peak {self.peak_population}); "
            f"{self.rows_dry_count()} of {COASTLINE_ROWS} coastline rows dry; "
            f"sea scenario: {self.sea_scenario}.",
        ]
        chronicle = self.chronicle_lines()
        if chronicle:
            lines.append("")
            lines.append("Chronicle:")
            lines.extend(chronicle)
        return "\n".join(lines)

    def _log_ticker(self, message):
        """Every ticker-producing method routes through here so the short
        live ticker (ticker_log, capped at TICKER_LOG_LIMIT) and D5's
        long-form history (ticker_full_history, capped much higher) never
        drift out of sync with each other."""
        self.ticker_log.append(message)
        self.ticker_log = self.ticker_log[-TICKER_LOG_LIMIT:]
        self.ticker_full_history.append(message)
        self.ticker_full_history = self.ticker_full_history[-TICKER_FULL_HISTORY_LIMIT:]

    def _record_ticker_message(self, acidity_change, old_fish_yield, new_fish_yield):
        """Delayed-effect ticker: narrates the lag as it builds and
        lands, so cause stays traceable in hindsight without spelling
        out the mechanic outright. Iteration-pass addition."""
        lag = self._effective_fish_lag()
        message = None
        if new_fish_yield < old_fish_yield - 1e-6:
            message = (
                f"Fish stocks quietly declining — acidity from {lag} "
                f"seasons ago is catching up."
            )
        elif new_fish_yield > old_fish_yield + 1e-6:
            message = "Fish stocks recovering as past acidity spikes fade from the lag window."
        elif acidity_change > 0 and len(self.acidity_history) <= lag:
            message = "Acidity is rising — the effect on fish stocks won't show for a few more seasons."

        if message:
            self._log_ticker(message)

    def _record_tier_unlock_message(self, tier_index):
        """Iteration Pass 3 — immediate, visible payoff at the moment an
        adaptation tier unlocks, logged into the same ticker the player
        is already reading for decline/recovery. Without this, a tier
        upgrade was only a passive label change the player might not
        notice; this makes "you just made things better" as legible as
        the ticker already makes decline."""
        tier = ADAPTATION_TIERS[tier_index]
        message = (
            f"Adaptation upgraded to {tier['name']} — sea-level damage is now "
            f"dampened {tier['dampening'] * 100:.0f}%, effective immediately."
        )
        self._log_ticker(message)
        self._chronicle_event(f"{tier['name']} completed along the shore.")

    def _record_trend_message(self):
        """Iteration Pass 3 — recovery narration for the delayed damage
        trend: fires once, the first season the damage curve visibly
        flattens (mirrors the existing damage_trend() comparison used
        for the static display), so the player gets the same kind of
        clear, in-the-moment feedback for "adaptation is working" that
        the ticker already gives for fish-stock decline."""
        if self.trend_flattening_announced:
            return
        trend = self.damage_trend()
        if trend is None:
            return
        first_half_avg, second_half_avg = trend
        if second_half_avg < first_half_avg - 1e-6:
            self.trend_flattening_announced = True
            message = (
                f"Damage curve flattening ({first_half_avg:.1f}/season -> "
                f"{second_half_avg:.1f}/season) — your adaptation spending is visibly working."
            )
            self._log_ticker(message)

    def _record_first_flood_message(self):
        """D17: a one-time callout the first season any coastline row
        actually floods -- distinct from the ongoing decline/recovery/
        tier-unlock narration above, this one only ever fires once per
        settlement, ever."""
        if self.first_flood_announced:
            return
        if flooded_row_count(self.sea_level) >= 1:
            self.first_flood_announced = True
            self._log_ticker(
                "The first coastline tile has flooded — the sea has arrived."
            )
            self._chronicle_event("The first stretch of coast went under.")

    def advance_season(self):
        old_fish_yield = self.fish_yield_multiplier()
        mix = OUTPUT_MIX[self.output_mix]
        fishing_share = mix["fishing_share"]
        income = self.capacity["output"] * OUTPUT_INCOME_PER_UNIT * (
            fishing_share * old_fish_yield + (1 - fishing_share)
        )
        tourism_income, aquaculture_income = self.diversified_income()
        self.funds += income + tourism_income + aquaculture_income
        self.max_funds_ever = max(self.max_funds_ever, self.funds)

        acidity_change = (
            self.capacity["output"] * ACIDITY_RISE_PER_OUTPUT * mix["acidity_multiplier"]
            - self.capacity["reduction"] * ACIDITY_FALL_PER_REDUCTION
        )
        self.acidity = max(0.0, self.acidity + acidity_change)
        self.acidity_history.append(self.acidity)
        self.max_acidity_ever = max(self.max_acidity_ever, self.acidity)

        rise = self.sea_rise_per_season()
        self.sea_level += rise
        damage_this_season = rise * (1 - self.dampening_fraction())
        self.cumulative_damage += damage_this_season
        self.undampened_damage_total += rise
        self.damage_log.append(damage_this_season)
        self.tier_log.append(self.current_tier_index())
        self._advance_sister(rise)

        self._update_heritage()
        self._update_population()
        if self.storm_this_season():
            self._resolve_storm()

        self.season += 1

        new_fish_yield = self.fish_yield_multiplier()
        self.fish_yield_history.append(new_fish_yield)
        self.min_fish_yield_ever = min(self.min_fish_yield_ever, new_fish_yield)
        self._record_ledger_entry(self.season - 1, damage_this_season, new_fish_yield)
        self._record_snapshot(self.season - 1)

        self._record_ticker_message(acidity_change, old_fish_yield, new_fish_yield)
        self._record_trend_message()
        self._record_first_flood_message()
        self._record_recovery_message(new_fish_yield)

    def _record_recovery_message(self, fish_yield):
        """D23: a celebratory callout, equal in weight to the decline
        narration, once a crashed stock rebuilds."""
        if fish_yield <= FISH_CRASH_LEVEL:
            if not self.fish_crash_open:
                self._chronicle_event("The fish stocks crashed; boats came back near-empty.")
            self.fish_crash_open = True
        elif self.fish_crash_open and fish_yield >= FISH_RECOVERED_LEVEL:
            self.fish_crash_open = False
            self.recovery_celebrated_season = self.season
            self._chronicle_event("The fish stocks rebuilt after the lean years.")
            self._log_ticker(
                f"🎉 The fish stock has rebuilt to {fish_yield * 100:.0f}% — the "
                "consequence of past acidity has finally faded. Cleaner choices paid off."
            )

    def damage_saved(self):
        """The hope-angle payoff, as a direct number: how much less
        cumulative damage the settlement has taken than it would have
        with zero adaptation investment, ever."""
        return self.undampened_damage_total - self.cumulative_damage

    def damage_trend(self):
        """Compares the first half of seasons played to the second half —
        a visibly flattening damage curve is the direct, legible reward
        for early adaptation investment, not just a good final number."""
        n = len(self.damage_log)
        if n < 4:
            return None
        half = n // 2
        first_half_avg = sum(self.damage_log[:half]) / half
        second_half_avg = sum(self.damage_log[half:]) / (n - half)
        return first_half_avg, second_half_avg


state = SettlementState()


def damage_saved_message(saved):
    if saved <= 0:
        return "No adaptation investment yet — every season of sea-level rise is hitting at full force."
    return (
        f"Adaptation has saved you {saved:.0f} in cumulative damage compared to "
        f"no investment at all — the sea kept rising, but you're weathering it better."
    )


def damage_trend_message(trend):
    if trend is None:
        return "Not enough seasons yet to show a trend."
    first_half_avg, second_half_avg = trend
    if second_half_avg < first_half_avg:
        return (
            f"Your damage curve is flattening ({first_half_avg:.1f}/season → "
            f"{second_half_avg:.1f}/season) — early adaptation is paying off."
        )
    if second_half_avg > first_half_avg:
        return (
            f"Your damage curve is steepening ({first_half_avg:.1f}/season → "
            f"{second_half_avg:.1f}/season)."
        )
    return f"Your damage rate has held steady at {second_half_avg:.1f}/season."


def _is_seawall_row(row_index, tier_index):
    """The bottom `tier_index` rows carry the seawall visual — thicker
    coverage as tiers unlock, since higher tiers mean more reinforced
    ground closest to the water."""
    return row_index >= COASTLINE_ROWS - tier_index


# D8: which rows were flooded as of the last render_coastline() call --
# purely a rendering concern (drives the one-shot flash below), never
# part of the save contract, so it's a plain module global rather than
# anything on SettlementState. Reset in setup() and load_state() so a
# fresh/loaded game doesn't spuriously flash every already-flooded row
# on its very first render.
_previous_flooded_rows = set()


def _resync_previous_flooded_rows():
    """Recomputes _previous_flooded_rows straight from live sea_level,
    so the next render_coastline() call doesn't mistake already-flooded
    rows (from a fresh load, or a fresh game) for newly-flooded ones."""
    global _previous_flooded_rows
    _previous_flooded_rows = {
        row for row in range(COASTLINE_ROWS) if tile_row_state(row, state.sea_level) == FLOODED
    }


def heritage_site_at(row, col):
    if col != HERITAGE_COL:
        return None
    for site in HERITAGE_SITES:
        if site["row"] == row:
            return site
    return None


def heritage_status_text(site):
    status = state.heritage.get(site["id"])
    if status == HERITAGE_PROTECTED:
        return f"{site['emoji']} {site['name']}: protected (upkeep {HERITAGE_UPKEEP}/season)."
    if status == HERITAGE_LOST:
        return f"✖ {site['name']}: lost to the sea."
    return f"{site['emoji']} {site['name']}: unprotected — floods with row {site['row'] + 1}. Protect for {site['cost']}."


def render_coastline():
    global _previous_flooded_rows
    grid_el = document.getElementById("coastline-grid")
    # D-4: while the season scrubber is on an earlier season, draw that season read-only
    # (no flash, no tide, no tooltip about "the current pace") and leave the flash tracker alone.
    scrubbed = scrub_view()
    live = scrubbed is None
    view = state.coast_view() if live else scrubbed
    # D-7: a re-render replaces every tile, so remember which one had keyboard
    # focus and give it back afterwards (otherwise Tab order restarts).
    focused = getattr(document, "activeElement", None)
    focused_id = getattr(focused, "id", "") if focused is not None else ""
    grid_el.innerHTML = ""
    grid_el.className = "coastline-grid" + ("" if live else " coastline-grid--scrubbed")
    tier_index = view["tier"]
    retreat_rows = view["retreat_rows"]
    current_flooded_rows = set()
    tidal_rows = view.get("tidal", [])
    for row_index, row in enumerate(coastline_grid(view["sea_level"])):
        tile_state = row[0]  # every column in a row shares the same state
        threshold = row_flood_threshold(row_index)
        # D1: a row given up by managed retreat is drawn flooded, with its
        # own class (diagonal hatch in CSS) so it reads as chosen.
        retreated = row_index in retreat_rows
        if retreated:
            tile_state = FLOODED
        if tile_state == FLOODED:
            current_flooded_rows.add(row_index)
        # D8: flash any row flooding for the first time this render --
        # compared against last render's snapshot, not against "flooded
        # right now", so the flash fires exactly once, at the moment of
        # crossing, not on every subsequent re-render while still flooded.
        just_flooded = live and tile_state == FLOODED and row_index not in _previous_flooded_rows
        for col_index in range(COASTLINE_COLS):
            tile = document.createElement("div")
            tile.id = f"coastline-tile-{row_index}-{col_index}"
            tile.className = f"coastline-tile coastline-{tile_state}"
            if _is_seawall_row(row_index, tier_index):
                # D28: per-tier class -> a distinct texture per tier, so
                # tiers are told apart without relying on colour.
                tile.className += f" coastline-seawall coastline-seawall--t{tier_index}"
            if retreated:
                tile.className += " coastline-retreated"
            if just_flooded:
                tile.className += " coastline-flash"
            site = heritage_site_at(row_index, col_index)
            if site is not None:
                status = view["heritage"].get(site["id"])
                tile.innerText = site["emoji"] if status != HERITAGE_LOST else "✖"
                tile.className += f" coastline-heritage coastline-heritage--{status}"
            # D8: dry rows the current tide reaches get a dashed edge
            # (a shape cue, not a hue one) and a title note.
            tidal = row_index in tidal_rows
            if tidal:
                tile.className += " coastline-tidal"
            # D19: a native hover/tap tooltip naming this row's flood
            # threshold -- zero extra markup, works identically for mouse
            # hover and (on most mobile browsers) a long-press/tap.
            if not live:
                base_title = (
                    "Cleared by managed retreat." if retreated
                    else "Flooded." if tile_state == FLOODED else "Dry."
                ) + f" Earlier view: Season {scrubbed['season']} (read-only)."
            else:
                base_title = (
                    "Managed retreat — this row was cleared on purpose and its people rehoused inland."
                    if retreated
                    else f"Flooded — this row floods once sea level reaches {threshold:.0f}."
                    if tile_state == FLOODED
                    else f"Floods once sea level reaches {threshold:.0f} "
                    f"(about {state.seasons_until_flood(row_index)} season(s) at the current pace)."
                    + (" This season's tide is washing over it." if tidal else "")
                )
            if site is not None:
                status = view["heritage"].get(site["id"])
                heritage_line = (
                    heritage_status_text(site) if live
                    else f"{site['emoji']} {site['name']}: {status}."
                )
                tile.title = heritage_line + " " + base_title
            else:
                tile.title = base_title
            # D-7: one Tab stop per row (column 0), but every tile is a labelled, focusable
            # target so Left/Right and Up/Down (ui.js) can walk the grid column by column.
            tile.tabIndex = 0 if col_index == 0 else -1
            tile.setAttribute("role", "img")
            tile.setAttribute(
                "aria-label",
                state.coastline_row_description(row_index, view)
                if col_index == 0
                else state.coastline_row_description(row_index, view, col_index),
            )
            grid_el.appendChild(tile)
    if live:
        _previous_flooded_rows = current_flooded_rows
    grid_el.setAttribute("role", "group")
    grid_el.setAttribute(
        "aria-label",
        "Coastline, one Tab stop per row. Use the arrow keys to move between rows and columns.",
    )
    description = document.getElementById("coastline-description")
    if description is not None:
        description.innerText = (
            state.coastline_description() if live
            else f"Season {scrubbed['season']} (earlier, read-only). " + state.scrub_text(scrubbed)
        )
    if focused_id.startswith("coastline-tile-"):
        refocus = document.getElementById(focused_id)
        if refocus is not None:
            refocus.focus()


def _render_mini_coastline(container_id, sea_level, tier_index=0):
    grid_el = document.getElementById(container_id)
    grid_el.innerHTML = ""
    for row_index, row in enumerate(coastline_grid(sea_level)):
        for tile_state in row:
            tile = document.createElement("div")
            tile.className = f"coastline-tile coastline-{tile_state}"
            if _is_seawall_row(row_index, tier_index):
                tile.className += " coastline-seawall"
            grid_el.appendChild(tile)


def render_coastline_comparison():
    """Iteration-pass addition: a small before/now side-by-side, so the
    hope-angle payoff (adaptation buys visibly less coastline loss) has
    a direct visual, not just the damage_saved() number.

    D18: "before" reads state.baseline_sea_level rather than a hardcoded
    0.0 -- defaults to the real Season 1 start, but set_comparison_
    baseline() can move it to any later checkpoint the player chooses.
    The before-grid's seawall overlay is always drawn at tier_index=0
    regardless of baseline, a deliberate simplification: Tide doesn't
    keep a season-by-season tier history to draw the *actual* tier that
    was active at an arbitrary past checkpoint, and the flood/land state
    itself (the part the comparison is really about) depends only on
    sea level, never on tier."""
    _render_mini_coastline("coastline-before-grid", state.baseline_sea_level, tier_index=0)
    _render_mini_coastline("coastline-now-grid", state.sea_level, tier_index=state.current_tier_index())
    before_label = document.getElementById("coastline-before-label")
    if before_label is not None:
        before_label.innerText = f"Season {state.baseline_season}"
    document.getElementById("coastline-now-label").innerText = f"Season {state.season}"


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Ocean acidification and sea-level rise are two separate "
        "consequences of the same underlying cause — the ocean absorbing "
        "extra CO2 and extra heat — and both show up on a delay: today's "
        "emissions determine damage that doesn't fully land for years. "
        "Tide's delayed-effect ticker and background sea-level timeline "
        "are built around that real lag."
    ),
    "mechanic_tie_in": (
        "The fish-stock crash mechanic mirrors the real acidification "
        "pathway — more absorbed CO2 makes water more acidic, which is "
        "measurably harmful to shellfish and reef-building organisms first."
    ),
    "sources": [
        {
            "label": "NOAA Fisheries — Understanding Ocean Acidification",
            "url": "https://www.fisheries.noaa.gov/insight/understanding-ocean-acidification",
            "note": "Explains the shellfish/reef impact mechanism directly — the real process behind Tide's fish-stock crash.",
        },
        {
            "label": "NASA Sea Level Change Portal — Global Mean Sea Level",
            "url": "https://sealevel.nasa.gov/understanding-sea-level/key-indicators/global-mean-sea-level/",
            "note": "Real satellite-measured sea-level data and rate-of-rise figures, informing the pacing of Tide's background timeline.",
        },
        {
            "label": "NOAA Climate.gov — Climate Change: Global Sea Level",
            "url": "https://www.climate.gov/news-features/understanding-climate/climate-change-global-sea-level",
            "note": "Explains both causes of sea-level rise (thermal expansion + ice melt) in plain language.",
        },
        {
            "label": "Smithsonian Ocean Portal — Ocean Acidification",
            "url": "https://ocean.si.edu/ocean-life/invertebrates/ocean-acidification",
            "note": "A clear, visual explanation of the acidification chemistry, most accessible of the four sources.",
        },
    ],
}
info_page_open = False


# Rendering/toggle logic lives in shared/info_page.py now (see that
# module's docstring) -- this used to be a ~25+4 line implementation
# byte-identical across all 8 climate games. info_page_open stays local
# here since it's part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, info_page_open)


def on_toggle_info_page(event=None):
    global info_page_open
    info_page_open = info_page.toggle(info_page_open)
    render_info_page()


# D15: a Grid-style historical mini-graph -- a small inline SVG built
# directly as a markup string (assigned via innerHTML), same technique
# Canopy's own session sparkline uses, charting acidity and fish yield
# together over the session so the delayed-consequence relationship
# between them is visible as a shape, not just two separate numbers.
SPARKLINE_WIDTH = 260
SPARKLINE_HEIGHT = 60
SPARKLINE_ACIDITY_COLOR = "#b06fd6"
SPARKLINE_FISH_COLOR = "#4c9c6e"


# D-22 / D-23: which stretch of the session the trend graphs show, and whether series get
# distinct dash styles and point shapes. Both are view options kept in this browser only.
graph_range = "all"
graph_markers = False

# Series styles used when markers are on: acidity is solid with circles, fish yield long-dashed
# with squares, damage dotted with triangles, so no series is told apart by colour alone.
SERIES_STYLES = {
    "acidity": {"color": SPARKLINE_ACIDITY_COLOR, "dash": None, "shape": "circle"},
    "fish": {"color": SPARKLINE_FISH_COLOR, "dash": "6 3", "shape": "square"},
    "damage": {"color": "#d8c088", "dash": "2 2", "shape": "triangle"},
    "risk": {"color": "#e8a03c", "dash": "2 2", "shape": "triangle"},
}


def graph_window_start(total):
    """First index of the seasons the graphs show for `total` recorded seasons."""
    if graph_range == "all":
        return 0
    return max(0, total - int(graph_range))


def _xy(values, step, max_value=1.0):
    denominator = max(max_value, 1e-9)
    return [
        (i * step, SPARKLINE_HEIGHT - min(1.0, max(0.0, v / denominator)) * SPARKLINE_HEIGHT)
        for i, v in enumerate(values)
    ]


def _poly_points(xy):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)


def _marker_svg(xy, shape, color):
    """D-23: a small shape at (up to GRAPH_MARKER_LIMIT of) the series' points."""
    if not graph_markers or not xy:
        return ""
    every = max(1, math.ceil(len(xy) / GRAPH_MARKER_LIMIT))
    out = []
    for i, (x, y) in enumerate(xy):
        if i % every and i != len(xy) - 1:
            continue
        if shape == "circle":
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.3" fill="{color}" stroke="#fff" stroke-width="0.4"/>')
        elif shape == "square":
            out.append(
                f'<rect x="{x - 2.1:.1f}" y="{y - 2.1:.1f}" width="4.2" height="4.2" fill="{color}" '
                f'stroke="#fff" stroke-width="0.4"/>'
            )
        else:
            out.append(
                f'<polygon points="{x:.1f},{y - 2.8:.1f} {x - 2.6:.1f},{y + 2.0:.1f} {x + 2.6:.1f},{y + 2.0:.1f}" '
                f'fill="{color}" stroke="#fff" stroke-width="0.4"/>'
            )
    return "".join(out)


def _series_svg(xy, style_key, dash=None, width=2, opacity=None, always_dash=False):
    """One polyline (plus markers when the toggle is on). The style's own dash is only used
    with markers on; `dash` forces a dash (a compared session) whatever the toggle says."""
    style = SERIES_STYLES[style_key]
    chosen = dash or (style["dash"] if graph_markers else None)
    attrs = f' stroke-dasharray="{chosen}"' if chosen else ""
    if opacity is not None:
        attrs += f' opacity="{opacity}"'
    line = (
        f'<polyline points="{_poly_points(xy)}" fill="none" stroke="{style["color"]}" '
        f'stroke-width="{width}"{attrs} />'
    )
    return line + _marker_svg(xy, style["shape"], style["color"])


def _crosshair_attr(lines):
    """D-21: the per-position readout strings ui.js shows at the crosshair."""
    return f' data-crosshair="{html.escape(json.dumps(lines, separators=(",", ":")), quote=True)}"'


def graph_range_text():
    return "all seasons" if graph_range == "all" else f"the last {graph_range} seasons"


def then_vs_now_sparkline_svg():
    """D14: tiny per-season damage sparkline since the baseline; "" until
    there are two points to draw a line between."""
    series = state.then_vs_now_damage_series()
    if len(series) < 2:
        return ""
    top = max(max(series), 1e-9)
    step = SPARKLINE_WIDTH / max(1, len(series) - 1)
    xy = _xy(series, step, top)
    first = state.baseline_season
    lines = [f"Season {first + i}: damage {value:.0f}" for i, value in enumerate(series)]
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" '
        f'class="acidity-fish-sparkline" role="img" tabindex="0"{_crosshair_attr(lines)} '
        f'aria-label="Damage per season since the baseline">'
        f"{_series_svg(xy, 'damage', width=2)}"
        f"</svg>"
    )


def _sparkline_points(series, max_value):
    """Maps a list of values onto SVG viewport coordinates -- x spread
    evenly left-to-right, y scaled so 0 sits on the baseline and
    `max_value` sits at the top. An empty series returns "" rather than
    dividing by zero."""
    if not series:
        return ""
    step = SPARKLINE_WIDTH / max(1, len(series) - 1)
    return _poly_points(_xy(series, step, max_value))


def _funds_by_season():
    return {e["season"]: e["funds"] for e in state.season_ledger}


def acidity_fish_history_svg():
    """Returns "" once there's no history yet -- render() shows a plain
    "not enough data" message instead in that case. Acidity is charted as
    a fraction of FISH_DAMAGE_SCALE (its own natural ceiling) and fish
    yield as a fraction of 1.0 (already 0..1), so both lines share one
    0..1 vertical scale despite being different units.

    D-22 draws only the chosen range, D-23 optionally adds dash styles and point
    shapes, D-21 attaches a readout per season for the crosshair, and D-2 can draw a
    saved session from the library as dashed lines behind the live ones."""
    if not state.acidity_history:
        return ""
    overlay = library_overlay_record()
    live_acid = [min(1.0, a / FISH_DAMAGE_SCALE) for a in state.acidity_history]
    live_fish = list(state.fish_yield_history)
    over_acid = overlay["acidity"] if overlay else []
    over_fish = overlay["fish"] if overlay else []
    full = max(len(live_acid), len(over_acid))
    start = graph_window_start(full)
    count = full - start
    step = SPARKLINE_WIDTH / max(1, count - 1)
    acid_view, fish_view = live_acid[start:], live_fish[start:]
    # D10: dashed reference line at the average acidity of the seasons in view, like
    # Thaw's melt-threshold gridline.
    average = sum(acid_view) / len(acid_view) if acid_view else 0.0
    average_y = SPARKLINE_HEIGHT - average * SPARKLINE_HEIGHT
    reference = (
        f'<line x1="0" y1="{average_y:.1f}" x2="{SPARKLINE_WIDTH}" y2="{average_y:.1f}" '
        f'stroke="{SPARKLINE_ACIDITY_COLOR}" stroke-width="1" stroke-dasharray="4 3" '
        f'opacity="0.6"><title>Average acidity, {graph_range_text()}</title></line>'
    )
    # D18: a marker at the season the comparison baseline was set (when it is in view).
    marker = ""
    baseline_index = state.baseline_season - 1 - start
    if state.baseline_season > 1 and count > 1 and baseline_index >= 0:
        marker_x = min(SPARKLINE_WIDTH, baseline_index * step)
        marker = (
            f'<line x1="{marker_x:.1f}" y1="0" x2="{marker_x:.1f}" y2="{SPARKLINE_HEIGHT}" '
            f'stroke="#d8c088" stroke-width="1" stroke-dasharray="2 2">'
            f'<title>Baseline set here (Season {state.baseline_season})</title></line>'
        )
    funds = _funds_by_season()
    lines = []
    for j in range(count):
        season = start + j + 1
        index = start + j
        parts = []
        if index < len(live_acid):
            parts.append(f"acidity {state.acidity_history[index]:.1f}")
            if index < len(live_fish):
                parts.append(f"fishing yield {live_fish[index] * 100:.0f}%")
            if index < len(state.damage_log):
                parts.append(f"damage {state.damage_log[index]:.0f}")
            if season in funds:
                parts.append(f"funds {funds[season]:.0f}")
        text = f"Season {season}: " + (", ".join(parts) if parts else "no data")
        if overlay and index < len(over_acid):
            extra = f"acidity {over_acid[index] * FISH_DAMAGE_SCALE:.1f}"
            if index < len(over_fish):
                extra += f", fishing yield {over_fish[index] * 100:.0f}%"
            text += f" | {overlay['name']}: {extra}"
        lines.append(text)
    drawn = ""
    if overlay:
        drawn += _series_svg(_xy(over_acid[start:], step), "acidity", dash="3 3", width=1.4, opacity=0.75)
        drawn += _series_svg(_xy(over_fish[start:], step), "fish", dash="3 3", width=1.4, opacity=0.75)
    drawn += _series_svg(_xy(acid_view, step), "acidity")
    drawn += _series_svg(_xy(fish_view, step), "fish")
    compare_note = f" Dashed lines: the saved session {overlay['name']}." if overlay else ""
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" '
        f'class="acidity-fish-sparkline" role="img" tabindex="0"{_crosshair_attr(lines)} '
        f'aria-label="Ocean acidity and fishing yield over {graph_range_text()}. Latest: acidity '
        f'{state.acidity:.1f}, fishing yield {state.fish_yield_multiplier() * 100:.0f} percent.'
        f'{html.escape(compare_note, quote=True)} Left and right arrow keys read each season.">'
        f"{reference}{marker}{drawn}"
        f"</svg>"
    )


def delayed_consequence_svg():
    """D7: acidity (purple) plotted at the season it was banked, against
    the fish yield it will cause (green, dashed) plotted `lag` seasons
    later -- the horizontal gap between the two lines is the lag. "" with
    no history yet. D-22 limits it to the chosen range; D-21 and D-23 as above."""
    rows_all = state.delayed_consequence_rows()
    if not rows_all:
        return ""
    lag = state._effective_fish_lag()
    start = graph_window_start(len(rows_all))
    rows = rows_all[start:]
    first = rows[0][0]
    total_seasons = len(rows) + lag
    step = SPARKLINE_WIDTH / max(1, total_seasons - 1)
    acidity_xy = [
        ((season - first) * step, SPARKLINE_HEIGHT - fraction * SPARKLINE_HEIGHT)
        for season, fraction, _arrival, _yield in rows
    ]
    fish_xy = [
        ((arrival - first) * step, SPARKLINE_HEIGHT - projected * SPARKLINE_HEIGHT)
        for _season, _fraction, arrival, projected in rows
    ]
    now_x = (state.season - first) * step
    now_line = (
        f'<line x1="{now_x:.1f}" y1="0" x2="{now_x:.1f}" y2="{SPARKLINE_HEIGHT}" '
        f'stroke="#d8c088" stroke-width="1" stroke-dasharray="2 2">'
        f"<title>Now (Season {state.season}): everything right of here has not happened yet</title></line>"
    )
    lines = []
    arrivals = {arrival: projected for _s, _f, arrival, projected in rows}
    for j in range(total_seasons):
        season = first + j
        parts = []
        if j < len(rows):
            parts.append(f"acidity banked {state.acidity_history[season - 1]:.1f}")
        if season in arrivals:
            parts.append(f"fish yield from earlier acidity about {arrivals[season] * 100:.0f}%")
        if season >= state.season:
            parts.append("not yet played")
        lines.append(f"Season {season}: " + (", ".join(parts) if parts else "nothing recorded"))
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" '
        f'class="acidity-fish-sparkline" role="img" tabindex="0"{_crosshair_attr(lines)} '
        f'aria-label="Acidity banked each season and the fish yield it causes {lag} seasons later, '
        f'over {graph_range_text()}">'
        f"{now_line}"
        f'{_series_svg(acidity_xy, "acidity")}'
        f'{_series_svg(fish_xy, "fish", dash="5 3")}'
        f"</svg>"
    )


# D13: a per-browser "best coastline saved" personal best -- the highest
# damage_saved() this browser has ever seen, across every session/save on
# this device. Deliberately NOT part of get_state()/the save-code system
# (same distinction Canopy's B14/Thaw's G19 draw): this is a cross-session
# device record, not one save's snapshot.
BEST_COASTLINE_STORAGE_KEY = "tide_best_coastline_saved_v1"

# Z6 (planning/TODO.md "Z. Games"): duration of the shared
# .personal-best-display.just-improved pulse (shared/personal-best.css) --
# matches the CSS animation's own length, same value Canopy/Thaw use.
PERSONAL_BEST_BADGE_MS = 1800


def _read_local_storage_item(key):
    """Lazy `import js` (same convention as _read_achievements_json())
    so this file stays importable outside a real browser. Broad except on
    the actual read below is deliberate: a real browser can refuse
    localStorage access entirely (private-browsing mode in some
    browsers), surfaced as a JS exception with no stable Python type to
    catch narrowly -- this feature is a nice-to-have, so it degrades to
    "no personal best recorded" rather than crashing the module import."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        return None
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return None
    try:
        return storage.getItem(key)
    except Exception:  # noqa: BLE001 — see docstring above
        return None


def _write_local_storage_item(key, value):
    try:
        import js  # noqa: PLC0415
    except ImportError:
        return
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return
    try:
        storage.setItem(key, value)
    except Exception:  # noqa: BLE001 — see _read_local_storage_item's docstring
        pass


def load_best_coastline_saved():
    raw = _read_local_storage_item(BEST_COASTLINE_STORAGE_KEY)
    if not raw:
        return 0.0
    try:
        return float(json.loads(raw))
    except (ValueError, TypeError):
        return 0.0


best_coastline_saved = load_best_coastline_saved()


def _maybe_update_best_coastline_saved():
    """Called every render(); bumps + persists the record whenever the
    live session's damage_saved() exceeds it."""
    global best_coastline_saved
    saved = state.damage_saved()
    if saved > best_coastline_saved:
        best_coastline_saved = saved
        _write_local_storage_item(BEST_COASTLINE_STORAGE_KEY, json.dumps(best_coastline_saved))
        _flash_personal_best_badge()


def _flash_personal_best_badge():
    """Z6: briefly adds the shared .just-improved class (see
    shared/personal-best.css) right when a session beats its stored best.
    Same setTimeout+create_proxy shape as Canopy/Thaw's equivalent."""
    element = document.getElementById("best-coastline-display")
    if element is None:
        return
    element.classList.add("just-improved")

    def _unflash():
        el = document.getElementById("best-coastline-display")
        if el is not None:
            el.classList.remove("just-improved")

    setTimeout(create_proxy(_unflash), PERSONAL_BEST_BADGE_MS)


def render_best_coastline_saved():
    element = document.getElementById("best-coastline-display")
    if element is None:
        return
    element.innerText = f"Best coastline saved (this browser): {best_coastline_saved:.0f} damage avoided"


# ===========================================================================
# Achievements (planning/ACHIEVEMENTS-SYSTEM-DESIGN.md) — SOL is the
# reference integration for the hub-wide achievements framework; this is
# Tide's own catalog, grounded in its actual mechanics (the three
# investment categories, the adaptation tech tree, the delayed fish-stock
# crash, and the coastline's own flood progression) rather than generic
# filler.
# ===========================================================================
#
# Every achievement's earned status is a pure function of state that
# already exists elsewhere on `state`, recomputed fresh on every call —
# never a separately hand-maintained "earned" flag ("derive, don't
# track"). Four checks genuinely needed new tracked state (min_fish_yield_
# ever, max_acidity_ever, max_funds_ever, fortified_in_time_earned — see
# SettlementState.__init__) because the thing they measure ("how far did
# this ever go", "did this happen before that") isn't recoverable from a
# field that only reflects the current moment. Every other check below
# reads state.capacity/state.season/coastline math directly.
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract SOL's game.py established: the page's boot
    script fetches achievements.json and hands it to Python as a window
    global before this file runs; the pytest harness's fake `js` module
    simply has no such attribute, so this falls through to reading the
    file straight off disk, which keeps the module importable outside a
    real browser."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "ACHIEVEMENTS_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 — only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Defensive per SOL's own note on this pattern: the real Pyodide runtime
# executes this file's fetched text via `pyodide.runPythonAsync(code)`,
# which never defines `__file__` -- if the window-global read ever comes
# back empty, the filesystem fallback would crash with a bare NameError
# that takes down this entire module import. Achievements are additive,
# not core to Tide's own gameplay, so this degrades to "no achievements
# catalog" instead.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

LOSING_GROUND_ROW_FRACTION = 0.5
TURNING_THE_TIDE_DROP = 20.0
FLUSH_COFFERS_THRESHOLD = 1000.0
TIME_BOUGHT_THRESHOLD = 100.0
THE_LONG_HAUL_SEASON = 20
WELL_ROUNDED_CAPACITY = 5
STOCKS_REBOUND_CRASH_THRESHOLD = 0.7
STOCKS_REBOUND_RECOVERY_THRESHOLD = 0.9


def _max_tier_index():
    return len(ADAPTATION_TIERS) - 1


ACHIEVEMENT_CHECKS = {
    "underway": lambda: state.season >= 2,
    "first_output": lambda: state.capacity["output"] >= 1,
    "first_reduction": lambda: state.capacity["reduction"] >= 1,
    "first_adaptation": lambda: state.capacity["adaptation"] >= 1,
    "tier_sandbags": lambda: state.current_tier_index() >= 1,
    "tier_seawalls": lambda: state.current_tier_index() >= 2,
    "tier_reinforced": lambda: state.current_tier_index() >= 3,
    "tier_storm_surge": lambda: state.current_tier_index() >= _max_tier_index(),
    "first_flood": lambda: flooded_row_count(state.sea_level) >= 1,
    "losing_ground": lambda: (
        flooded_row_count(state.sea_level) >= math.ceil(COASTLINE_ROWS * LOSING_GROUND_ROW_FRACTION)
    ),
    "fully_submerged": lambda: flooded_row_count(state.sea_level) >= COASTLINE_ROWS,
    "the_lag_arrives": lambda: state.min_fish_yield_ever <= 0.5,
    "stocks_rebound": lambda: (
        state.min_fish_yield_ever < STOCKS_REBOUND_CRASH_THRESHOLD
        and state.fish_yield_multiplier() >= STOCKS_REBOUND_RECOVERY_THRESHOLD
    ),
    "turning_the_tide": lambda: (state.max_acidity_ever - state.acidity) >= TURNING_THE_TIDE_DROP,
    "flush_coffers": lambda: state.max_funds_ever >= FLUSH_COFFERS_THRESHOLD,
    "time_bought": lambda: state.damage_saved() >= TIME_BOUGHT_THRESHOLD,
    "the_long_haul": lambda: state.season >= THE_LONG_HAUL_SEASON,
    "bending_the_curve": lambda: state.trend_flattening_announced,
    "well_rounded": lambda: all(
        state.capacity[category] >= WELL_ROUNDED_CAPACITY for category in CATEGORIES
    ),
    "fortified_in_time": lambda: state.fortified_in_time_earned,
}

# Progress readouts, only for achievements with a natural numeric
# scale-up — a plain earned/not-yet is the honest shape for the rest
# (one-shot milestones like "invest in Output for the first time" don't
# get a fake "0 of 1").
ACHIEVEMENT_PROGRESS = {
    "losing_ground": lambda: (
        flooded_row_count(state.sea_level),
        math.ceil(COASTLINE_ROWS * LOSING_GROUND_ROW_FRACTION),
    ),
    "fully_submerged": lambda: (flooded_row_count(state.sea_level), COASTLINE_ROWS),
    "flush_coffers": lambda: (int(state.max_funds_ever), int(FLUSH_COFFERS_THRESHOLD)),
    "time_bought": lambda: (int(state.damage_saved()), int(TIME_BOUGHT_THRESHOLD)),
    "the_long_haul": lambda: (state.season, THE_LONG_HAUL_SEASON),
    "well_rounded": lambda: (
        min(state.capacity[category] for category in CATEGORIES),
        WELL_ROUNDED_CAPACITY,
    ),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field. Always recomputed, never itself a save
    input."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


def achievements_summary():
    """The full catalog, in order, each entry annotated with whether it's
    currently earned and (where one exists) a live progress readout."""
    earned_ids = set(achievement_ids_earned())
    summary = []
    for entry in ACHIEVEMENTS:
        progress_fn = ACHIEVEMENT_PROGRESS.get(entry["id"])
        summary.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "description": entry["description"],
                "earned": entry["id"] in earned_ids,
                "progress": progress_fn() if progress_fn else None,
            }
        )
    return summary


achievements_open = False

# Tracks the earned-id set as of the last time it was checked, so a fresh
# unlock (one that wasn't in this set last time) can trigger a toast
# without re-toasting every already-earned achievement on every render.
# Reset (without toasting) right after setup()'s initial render and right
# after load_state() applies a save, so neither a fresh game nor a loaded
# one spams toasts for achievements that were already satisfied before
# this render cycle started.
_previously_earned_ids = set()
_toast_hide_proxy = None
_toast_hide_proxy_gen = 0

ACHIEVEMENT_TOAST_DURATION_MS = 4000


def _earned_snapshot():
    return set(achievement_ids_earned())


def show_achievement_toast(message):
    toast = document.getElementById("achievement-toast")
    if toast is None:
        return
    toast.innerText = message
    toast.hidden = False
    toast.classList.add("achievement-toast--visible")

    # Never destroy a still-pending timer's proxy: the browser would later
    # call it and Pyodide throws "Object has already been destroyed". Each
    # timer owns its own proxy and destroys it after firing; a newer toast
    # just bumps the generation so stale timers become no-ops.
    global _toast_hide_proxy_gen
    _toast_hide_proxy_gen += 1
    my_gen = _toast_hide_proxy_gen
    holder = []

    def _hide():
        if my_gen == _toast_hide_proxy_gen:
            toast.classList.remove("achievement-toast--visible")
            toast.hidden = True
        holder[0].destroy()

    holder.append(create_proxy(_hide))
    setTimeout(holder[0], ACHIEVEMENT_TOAST_DURATION_MS)


def _sync_earned_and_toast():
    """Diffs the live earned set against the last-seen snapshot; anything
    newly present gets a toast (batched into one message if several land
    in the same render pass, e.g. an Advance Season click that both
    unlocks a tier and crashes fish yield)."""
    global _previously_earned_ids
    current = _earned_snapshot()
    newly_earned_ids = current - _previously_earned_ids
    _previously_earned_ids = current
    if not newly_earned_ids:
        return
    newly_earned = [entry for entry in ACHIEVEMENTS if entry["id"] in newly_earned_ids]
    if not newly_earned:
        return
    if len(newly_earned) == 1:
        message = f"\U0001F3C6 Achievement unlocked: {newly_earned[0]['label']}"
    else:
        labels = ", ".join(entry["label"] for entry in newly_earned)
        message = f"\U0001F3C6 {len(newly_earned)} achievements unlocked: {labels}"
    show_achievement_toast(message)


def on_toggle_achievements(event=None):
    global achievements_open
    achievements_open = not achievements_open
    update_achievements_display()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    if toggle is None or panel is None:
        return
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if achievements_open
        else f"\U0001F3C6 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not achievements_open
    if not achievements_open:
        return

    panel.innerHTML = ""
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = (
            "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        )
        card.dataset.achievementId = entry["id"]

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"\U0001F3C6 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    hub_link = document.createElement("a")
    hub_link.className = "achievements-hub-link"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.innerText = "View achievements across every game →"
    panel.appendChild(hub_link)

    _request_achievement_stats()


def _request_achievement_stats():
    """Z27b: asks the page's optional JS hook (window.applyAchievementStats,
    shared/achievement-stats.js) to fill in each achievement card's own
    "Earned by N% of players" line from the cross-player stats endpoint
    (planning/TODO.md Z1). Absent hook (pytest, or a page without the
    shared script) leaves the cards exactly as rendered above -- same
    fails-soft shape as Grid's C15 window.gridCompare."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "applyAchievementStats", None)
    if hook is not None:
        hook()


# ===========================================================================
# "What's New" changelog panel (site-wide goal, planning/TODO.md, origin K16)
# ===========================================================================
# Same static-JSON-asset loading contract as ACHIEVEMENTS above: the boot
# script fetches changelog.json and hands it to Python as a window global
# before this module runs; the pytest harness's fake `js` has no such
# attribute, so this falls through to reading the file straight off disk.
# A flat, hand-written list of highlights pulled from this game's own
# CLAUDE.md milestone table and iteration-pass notes -- not a full
# duplicate of the dev logs, just a quick "what's new" view.
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    try:
        import js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "CHANGELOG_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Same defensive posture as ACHIEVEMENTS above: the changelog is additive,
# not core to gameplay, so any loading failure degrades to "no changelog"
# instead of crashing the whole module import. changelog.json is authored
# newest-first already, but sorted defensively here in case a future entry
# is appended out of order.
try:
    CHANGELOG = sorted(
        json.loads(_read_changelog_json())["changelog"],
        key=lambda entry: entry["date"],
        reverse=True,
    )
except (ValueError, OSError, NameError, KeyError):
    CHANGELOG = []

changelog_open = False


def on_toggle_changelog(event=None):
    global changelog_open
    changelog_open = not changelog_open
    update_changelog_display()


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide What's New" if changelog_open else "📋 What's New"
    panel.hidden = not changelog_open
    if not changelog_open:
        return

    panel.innerHTML = ""
    for entry in CHANGELOG:
        row = document.createElement("div")
        row.className = "changelog-entry"

        date = document.createElement("p")
        date.className = "changelog-entry-date"
        date.innerText = entry["date"]
        row.appendChild(date)

        text = document.createElement("p")
        text.className = "changelog-entry-text"
        text.innerText = entry["entry"]
        row.appendChild(text)

        panel.appendChild(row)


# D7: an end-of-session summary screen -- player-triggered, same
# optional/never-forced pattern as the achievements/info-page panels.
session_summary_open = False


def on_toggle_session_summary(event=None):
    global session_summary_open
    session_summary_open = not session_summary_open
    update_session_summary_display()


def update_session_summary_display():
    toggle = document.getElementById("session-summary-toggle-button")
    panel = document.getElementById("session-summary-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Session Summary" if session_summary_open else "📋 Session Summary"
    panel.hidden = not session_summary_open
    if not session_summary_open:
        return
    text_el = document.getElementById("session-summary-text")
    if text_el is not None:
        best_line = almanac_best_line()
        text_el.innerText = state.session_summary_text() + (" " + best_line if best_line else "")


def copy_result_fields():
    """Z-20: the fields shared/copy-result.js turns into one pasteable line
    ("Tide, 12 seasons, 340 damage taken, ..."). Read by the page's own
    inline script through pyodide.globals when the Copy result button is
    pressed, so it always describes the run as it stands right now."""
    seasons = max(0, state.season - 1)
    stats = [
        {"n": round(state.cumulative_damage), "one": "damage taken", "many": "damage taken"},
        {"n": round(state.damage_saved()), "one": "damage saved by adaptation", "many": "damage saved by adaptation"},
        "tier: " + state.current_tier()["name"],
    ]
    storms = len(state.storm_log)
    if storms:
        stats.append({"n": storms, "one": "storm survived", "many": "storms survived"})
    return {
        "game": "Tide",
        "score": seasons,
        "unit": "season" if seasons == 1 else "seasons",
        "stats": stats,
    }


def render_fish_warning_banner():
    """D14: an early-warning banner for a fish-yield crash already locked
    in by acidity that's already in the pipeline -- distinct from the
    ticker's after-the-fact narration, this fires *before* the drop
    lands, using next_season_fish_yield_preview()."""
    banner = document.getElementById("fish-warning-banner")
    if banner is None:
        return
    if state.fish_warning_active():
        preview = state.next_season_fish_yield_preview()
        banner.hidden = False
        banner.innerText = (
            f"⚠️ Heads up: fishing yield is on track to fall to about {preview * 100:.0f}% "
            f"next season — acidity already recorded is catching up. "
            "Suggested action: invest in Acidity Reduction now, and expect the dip to last a few seasons."
        )
    else:
        banner.hidden = True


# D-17: which filter chip and search text the full history is showing. A
# view preference only: never saved, resets on reload.
ticker_filter = "all"
ticker_search = ""


def ticker_category(message):
    """D-17: classifies a ticker message from its wording, so older saves
    (which stored plain strings) filter exactly like new ones."""
    text = message.lower()
    if "⛈" in message or "storm surge in season" in text:
        return "storm"
    if (
        text.startswith(("monitoring report", "checkpoint", "replaying", "managed retreat"))
        or "people had to leave" in text
        or "founded" in text
        or any(site["name"].lower() in text for site in HERITAGE_SITES)
    ):
        return "chronicle"
    if any(word in text for word in ("fish", "acidity", "stock", "yield")):
        return "fish"
    if any(word in text for word in ("diversif", "economy", "income", "funds", "tourism", "aquaculture")):
        return "economy"
    if any(word in text for word in ("sea", "flood", "tile", "coast", "tier", "adaptation", "damage", "seawall", "tide")):
        return "sea"
    return "other"


def filtered_ticker_history(category=None, search=None):
    """D-17: the full history, narrowed by chip and by a case-insensitive
    text search. Returns a new list; the stored history is never changed."""
    category = ticker_filter if category is None else category
    search = ticker_search if search is None else search
    needle = (search or "").strip().lower()
    messages = []
    for message in state.ticker_full_history:
        if category != "all" and ticker_category(message) != category:
            continue
        if needle and needle not in message.lower():
            continue
        messages.append(message)
    return messages


def render_ticker_history():
    """D5: the full, uncapped-within-TICKER_FULL_HISTORY_LIMIT ticker log
    behind an expandable panel, alongside (not instead of) the short live
    ticker rendered separately above. D-17: chips and a search box narrow
    this history (the short live ticker is deliberately never filtered)."""
    history_el = document.getElementById("ticker-history-list")
    if history_el is None:
        return
    for key, _label in TICKER_FILTERS:
        chip = document.getElementById(f"ticker-filter-{key}")
        if chip is not None:
            chip.setAttribute("aria-pressed", "true" if key == ticker_filter else "false")
            if key == ticker_filter:
                chip.classList.add("selected")
            else:
                chip.classList.remove("selected")
    messages = filtered_ticker_history()
    status_el = document.getElementById("ticker-filter-status")
    if status_el is not None:
        filtering = ticker_filter != "all" or ticker_search.strip()
        status_el.innerText = (
            f"Showing {len(messages)} of {len(state.ticker_full_history)} message(s)."
            if filtering and state.ticker_full_history
            else ""
        )
    if not state.ticker_full_history:
        history_el.innerHTML = "No notable changes yet."
    elif not messages:
        history_el.innerHTML = "No messages match this filter."
    else:
        history_el.innerHTML = "<br>".join(messages)


def _make_ticker_filter_handler(key):
    def handler(event=None):
        global ticker_filter
        ticker_filter = key
        render_ticker_history()
    return handler


def on_ticker_search(event):
    global ticker_search
    ticker_search = str(event.target.value or "")
    render_ticker_history()


# ---- D-1 Harbor Ledger ----------------------------------------------
ledger_open = False
ledger_sort_key = "season"
ledger_sort_descending = True
LEDGER_CHART_WIDTH = 80
LEDGER_CHART_HEIGHT = 22


def _ledger_chart_svg(key):
    series = state.ledger_series(key)
    if len(series) < 2:
        return ""
    low, high = min(series), max(series)
    span = high - low
    step = LEDGER_CHART_WIDTH / (len(series) - 1)
    points = []
    for i, value in enumerate(series):
        y = LEDGER_CHART_HEIGHT / 2 if span <= 1e-9 else (
            LEDGER_CHART_HEIGHT - 2 - (value - low) / span * (LEDGER_CHART_HEIGHT - 4)
        )
        points.append(f"{i * step:.1f},{y:.1f}")
    label = dict(LEDGER_COLUMNS)[key]
    return (
        f'<svg viewBox="0 0 {LEDGER_CHART_WIDTH} {LEDGER_CHART_HEIGHT}" class="ledger-chart" '
        f'role="img" aria-label="{label} by season, from {series[0]:.4g} to {series[-1]:.4g}">'
        f'<polyline points="{" ".join(points)}" fill="none" stroke="currentColor" stroke-width="1.6" />'
        f"</svg>"
    )


def _ledger_cell(key, entry):
    value = entry[key]
    if key == "funds" or key == "damage":
        return f"{value:.0f}"
    if key == "acidity":
        return f"{value:.1f}"
    if key == "fish_yield":
        return f"{value * 100:.0f}%"
    if key == "tier":
        index = max(0, min(int(value), len(ADAPTATION_TIERS) - 1))
        return f"{TIER_BADGES[index]} {index}"
    return str(value)


def ledger_rows_html():
    rows = []
    for entry in state.sorted_ledger(ledger_sort_key, ledger_sort_descending):
        cells = "".join(f"<td>{_ledger_cell(key, entry)}</td>" for key in LEDGER_KEYS)
        rows.append(f"<tr>{cells}</tr>")
    return "".join(rows)


def render_ledger():
    toggle = document.getElementById("ledger-toggle-button")
    panel = document.getElementById("ledger-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Harbor Ledger" if ledger_open else "📒 Harbor Ledger"
    panel.hidden = not ledger_open
    if not ledger_open:
        return
    for key, label in LEDGER_COLUMNS:
        button = document.getElementById(f"ledger-sort-{key}")
        header = document.getElementById(f"ledger-th-{key}")
        active = key == ledger_sort_key
        if button is not None:
            button.innerText = label + (" ▼" if active and ledger_sort_descending else " ▲" if active else "")
        if header is not None:
            header.setAttribute(
                "aria-sort",
                ("descending" if ledger_sort_descending else "ascending") if active else "none",
            )
        chart = document.getElementById(f"ledger-chart-{key}")
        if chart is not None:
            chart.innerHTML = "" if key == "season" else _ledger_chart_svg(key)
    body = document.getElementById("ledger-body")
    if body is not None:
        body.innerHTML = ledger_rows_html()
    summary = document.getElementById("ledger-summary")
    if summary is not None:
        summary.innerText = state.ledger_summary_text(ledger_sort_key, ledger_sort_descending)


def on_toggle_ledger(event=None):
    global ledger_open
    ledger_open = not ledger_open
    render_ledger()


def _make_ledger_sort_handler(key):
    def handler(event=None):
        global ledger_sort_key, ledger_sort_descending
        if key == ledger_sort_key:
            ledger_sort_descending = not ledger_sort_descending
        else:
            ledger_sort_key = key
            ledger_sort_descending = True
        render_ledger()
    return handler


# ---- D-22 / D-23 graph controls ----------------------------------------
def _load_graph_prefs():
    global graph_range, graph_markers
    raw = _read_local_storage_item(GRAPH_PREFS_KEY)
    if not raw:
        return
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return
    if isinstance(data, dict):
        if data.get("range") in dict(GRAPH_RANGES):
            graph_range = data["range"]
        if isinstance(data.get("markers"), bool):
            graph_markers = data["markers"]


def _save_graph_prefs():
    _write_local_storage_item(
        GRAPH_PREFS_KEY, json.dumps({"range": graph_range, "markers": graph_markers})
    )


def render_graphs():
    """Redraws the trend graphs (they follow the range and marker options)."""
    graph_container = document.getElementById("acidity-fish-graph")
    if graph_container is not None:
        svg = acidity_fish_history_svg()
        if svg:
            graph_container.innerHTML = svg
        else:
            graph_container.innerHTML = ""
            graph_container.innerText = "Not enough seasons yet to chart a trend."
    consequence_graph = document.getElementById("delayed-consequence-graph")
    if consequence_graph is not None:
        consequence_graph.innerHTML = delayed_consequence_svg()
    then_vs_now_graph = document.getElementById("then-vs-now-graph")
    if then_vs_now_graph is not None:
        then_vs_now_graph.innerHTML = then_vs_now_sparkline_svg()


def render_graph_controls():
    for key, label in GRAPH_RANGES:
        button = document.getElementById(f"graph-range-{key}")
        if button is not None:
            button.innerText = label
            button.setAttribute("aria-pressed", "true" if key == graph_range else "false")
    markers = document.getElementById("graph-markers-toggle")
    if markers is not None:
        markers.innerText = "Series markers: On" if graph_markers else "Series markers: Off"
        markers.setAttribute("aria-pressed", "true" if graph_markers else "false")


def _make_graph_range_handler(key):
    def handler(event=None):
        global graph_range
        graph_range = key
        _save_graph_prefs()
        render_graph_controls()
        render_graphs()
        render_library()
        render_planner()
    return handler


def on_toggle_graph_markers(event=None):
    global graph_markers
    graph_markers = not graph_markers
    _save_graph_prefs()
    render_graph_controls()
    render_graphs()
    render_library()
    render_planner()


# ---- D-4 season scrubber -----------------------------------------------
scrub_season = None
_scrub_stamp = None


def _state_stamp():
    """Anything the player can change that should end a read-only look back."""
    return (
        state.season, round(state.funds, 1), sum(state.capacity.values()),
        len(state.ticker_full_history), len(state.chronicle), state.output_mix,
        state.hard_lag_mode, state.sea_scenario,
    )


def scrub_view():
    """The scrubbed season as a coastline view dict, or None while viewing the live run.
    Any change to the live run (invest, advance, load, ...) quietly ends the look back."""
    global scrub_season
    if scrub_season is None:
        return None
    snap = state.scrub_snapshot(scrub_season) if _scrub_stamp == _state_stamp() else None
    if snap is None:
        scrub_season = None
        return None
    snap = dict(snap)
    snap["tidal"] = []
    return snap


def scrub_to(position):
    global scrub_season, _scrub_stamp
    if state.scrub_snapshot(position) is None:
        scrub_season = None
    else:
        scrub_season = position
        _scrub_stamp = _state_stamp()
    render_coastline()
    render_scrubber()


def on_scrub_input(event=None):
    target = getattr(event, "target", None)
    try:
        position = int(float(getattr(target, "value", "")))
    except (TypeError, ValueError):
        return
    scrub_to(position)


def on_scrub_live(event=None):
    scrub_to(state.season)


def render_scrubber():
    section = document.getElementById("scrub-section")
    if section is None:
        return
    positions = state.scrub_positions()
    section.hidden = not positions
    if not positions:
        return
    view = scrub_view()
    slider = document.getElementById("scrub-slider")
    if slider is not None:
        slider.setAttribute("min", str(positions[0]))
        slider.setAttribute("max", str(state.season))
        slider.value = str(view["season"] if view else state.season)
        slider.setAttribute(
            "aria-valuetext",
            f"Season {view['season']}, earlier and read-only" if view else f"Season {state.season}, the live run",
        )
    readout = document.getElementById("scrub-readout")
    if readout is not None:
        readout.innerText = (
            state.scrub_text(view) if view
            else f"Season {state.season} (live). Drag the slider back to look at an earlier season; nothing you do there changes your run."
        )
    live_button = document.getElementById("scrub-live-button")
    if live_button is not None:
        live_button.hidden = view is None


# ---- D-2 session library -------------------------------------------------
library_open = False
library_a = LIBRARY_CURRENT
library_b = ""
library_overlay_id = ""
_library_status = ""
_library_proxies = []


def _clean_series(values):
    if not isinstance(values, list) or not values:
        return None
    out = []
    for v in values[-LEDGER_LIMIT:]:
        if not _finite_number(v, 0, 1):
            return None
        out.append(round(float(v), 3))
    return out


def _validate_session_record(item):
    if not isinstance(item, dict):
        return None
    rid, name = item.get("id"), item.get("name")
    seasons, rows_dry, tier = item.get("seasons"), item.get("rows_dry"), item.get("tier")
    acidity, fish = _clean_series(item.get("acidity")), _clean_series(item.get("fish"))
    if (
        not isinstance(rid, int) or isinstance(rid, bool) or rid < 1
        or not isinstance(name, str)
        or not isinstance(seasons, int) or isinstance(seasons, bool) or not 0 <= seasons <= 10**6
        or not isinstance(rows_dry, int) or isinstance(rows_dry, bool) or not 0 <= rows_dry <= COASTLINE_ROWS
        or not isinstance(tier, int) or isinstance(tier, bool) or not 0 <= tier < len(ADAPTATION_TIERS)
        or item.get("scenario") not in SEA_SCENARIOS
        or item.get("lag") not in ("standard", "hard")
        or not isinstance(item.get("storms"), bool)
        or not _finite_number(item.get("score"), -1e9, 1e9)
        or acidity is None or fish is None
    ):
        return None
    return {
        "id": rid, "name": " ".join(name.split())[:SETTLEMENT_NAME_MAX] or f"Session {rid}",
        "seasons": seasons, "scenario": item["scenario"], "lag": item["lag"],
        "storms": item["storms"], "score": round(float(item["score"]), 1),
        "rows_dry": rows_dry, "tier": tier, "acidity": acidity, "fish": fish,
    }


def library_records():
    """Saved sessions of this browser, oldest first; damaged entries are skipped."""
    raw = _read_local_storage_item(LIBRARY_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    records = [r for r in (_validate_session_record(item) for item in data) if r is not None]
    return records[-LIBRARY_LIMIT:]


def _write_library(records):
    _write_local_storage_item(LIBRARY_KEY, json.dumps(records, separators=(",", ":")))


def live_session_record():
    """The running session in the same shape as a saved one."""
    return {
        "id": LIBRARY_CURRENT, "name": state.display_name(), "seasons": max(0, state.season - 1),
        "scenario": state.sea_scenario, "lag": "hard" if state.hard_lag_mode else "standard",
        "storms": bool(state.storm_mode), "score": round(state.damage_saved(), 1),
        "rows_dry": state.rows_dry_count(), "tier": state.current_tier_index(),
        "acidity": [round(min(1.0, a / FISH_DAMAGE_SCALE), 3) for a in state.acidity_history][-LEDGER_LIMIT:],
        "fish": [round(v, 3) for v in state.fish_yield_history][-LEDGER_LIMIT:],
    }


def library_get(session_id):
    if session_id == LIBRARY_CURRENT:
        return live_session_record()
    for record in library_records():
        if str(record["id"]) == str(session_id):
            return record
    return None


def library_overlay_record():
    if not library_overlay_id:
        return None
    record = library_get(library_overlay_id)
    if record is None or record["id"] == LIBRARY_CURRENT or not record["acidity"]:
        return None
    return record


def library_summary_text(record):
    lag = "harder lag" if record["lag"] == "hard" else "standard lag"
    storms = ", storm seasons on" if record["storms"] else ""
    return (
        f"{record['name']}: {record['seasons']} seasons, {record['scenario']} sea, {lag}{storms}. "
        f"Damage avoided {record['score']:.0f}, {record['rows_dry']} of {COASTLINE_ROWS} rows dry, "
        f"tier {TIER_BADGES[record['tier']]} {ADAPTATION_TIERS[record['tier']]['name']}."
    )


def library_save_current():
    """D-2: stores the running session (its settings, outcome and the acidity and fish-yield
    series) in this browser. Needs a few seasons so a saved session is worth comparing."""
    global _library_status, library_b
    if state.season - 1 < LIBRARY_MIN_SEASONS:
        _library_status = f"Play at least {LIBRARY_MIN_SEASONS} seasons before saving a session to the library."
        return False
    records = library_records()
    record_id = max([r["id"] for r in records], default=0) + 1
    record = live_session_record()
    record["id"] = record_id
    record["name"] = state.settlement_name or f"Session {record_id}"
    records.append(record)
    dropped = max(0, len(records) - LIBRARY_LIMIT)
    records = records[-LIBRARY_LIMIT:]
    _write_library(records)
    if not library_b:
        library_b = str(record_id)
    _library_status = (
        f"Saved {record['name']} to the library ({len(records)} of {LIBRARY_LIMIT})."
        + (f" The oldest {dropped} saved session(s) were dropped to stay within the limit." if dropped else "")
    )
    return True


def library_delete(record_id):
    global _library_status
    records = library_records()
    kept = [r for r in records if r["id"] != record_id]
    if len(kept) == len(records):
        return False
    _write_library(kept)
    for name in ("library_a", "library_b", "library_overlay_id"):
        if globals()[name] == str(record_id):
            globals()[name] = LIBRARY_CURRENT if name == "library_a" else ""
    _library_status = "Removed the saved session."
    return True


def library_compare_svg(rec_a, rec_b):
    """A solid, B dashed; acidity purple, fish yield green. "" if either is missing."""
    if rec_a is None or rec_b is None or not rec_a["acidity"] or not rec_b["acidity"]:
        return ""
    full = max(len(rec_a["acidity"]), len(rec_b["acidity"]))
    start = graph_window_start(full)
    count = full - start
    step = SPARKLINE_WIDTH / max(1, count - 1)
    lines = []
    for j in range(count):
        index = start + j
        parts = []
        for label, record in (("A", rec_a), ("B", rec_b)):
            if index < len(record["acidity"]):
                piece = f"{label} {record['name']}: acidity {record['acidity'][index] * FISH_DAMAGE_SCALE:.1f}"
                if index < len(record["fish"]):
                    piece += f", fishing yield {record['fish'][index] * 100:.0f}%"
                parts.append(piece)
        lines.append(f"Season {index + 1}: " + (" | ".join(parts) if parts else "no data"))
    drawn = ""
    for record, dash in ((rec_a, None), (rec_b, "4 3")):
        drawn += _series_svg(_xy(record["acidity"][start:], step), "acidity", dash=dash)
        drawn += _series_svg(_xy(record["fish"][start:], step), "fish", dash=dash)
    label = html.escape(f"Session A {rec_a['name']} (solid) against session B {rec_b['name']} (dashed)", quote=True)
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" class="acidity-fish-sparkline" '
        f'role="img" tabindex="0"{_crosshair_attr(lines)} '
        f'aria-label="Acidity and fishing yield over {graph_range_text()}: {label}. '
        f'Left and right arrow keys read each season.">{drawn}</svg>'
    )


def _session_options(records, blank=None, include_current=True):
    options = []
    if blank is not None:
        options.append(f'<option value="">{html.escape(blank)}</option>')
    if include_current:
        options.append(f'<option value="{LIBRARY_CURRENT}">Current session (Season {state.season})</option>')
    for record in records:
        options.append(
            f'<option value="{record["id"]}">{html.escape(record["name"])} '
            f"({record['seasons']} seasons)</option>"
        )
    return "".join(options)


def render_library():
    global library_a, library_b, library_overlay_id, _library_proxies
    toggle = document.getElementById("library-toggle-button")
    panel = document.getElementById("library-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Session Library" if library_open else "📚 Session Library"
    panel.hidden = not library_open
    if not library_open:
        return
    records = library_records()
    valid = {str(r["id"]) for r in records}
    if library_a != LIBRARY_CURRENT and library_a not in valid:
        library_a = LIBRARY_CURRENT
    if library_b not in valid:
        library_b = next((str(r["id"]) for r in reversed(records)), "")
    if library_overlay_id and library_overlay_id not in valid:
        library_overlay_id = ""
    for select_id, options, value in (
        ("library-select-a", _session_options(records), library_a),
        ("library-select-b", _session_options(records, blank="(choose a session)"), library_b),
        ("library-overlay-select", _session_options(records, blank="(none)", include_current=False), library_overlay_id),
    ):
        select = document.getElementById(select_id)
        if select is not None:
            select.innerHTML = options
            select.value = value
    status = document.getElementById("library-status")
    if status is not None:
        status.innerText = _library_status or (
            f"{len(records)} saved session(s). Sessions are kept in this browser only."
        )
    listing = document.getElementById("library-list")
    if listing is not None:
        for proxy in _library_proxies:
            proxy.destroy()
        _library_proxies = []
        listing.innerHTML = ""
        if not records:
            listing.innerText = "Nothing saved yet. Play a few seasons, then save the session here."
        for record in records:
            item = document.createElement("li")
            item.className = "library-item"
            text = document.createElement("span")
            text.innerText = library_summary_text(record)
            remove = document.createElement("button")
            remove.className = "secondary library-delete"
            remove.type = "button"
            remove.innerText = "Delete"
            remove.setAttribute("aria-label", f"Delete saved session {record['name']}")
            proxy = create_proxy(_make_library_delete_handler(record["id"]))
            _library_proxies.append(proxy)
            remove.addEventListener("click", proxy)
            item.appendChild(text)
            item.appendChild(remove)
            listing.appendChild(item)
    compare = document.getElementById("library-compare-graph")
    if compare is not None:
        svg = library_compare_svg(library_get(library_a), library_get(library_b) if library_b else None)
        compare.innerHTML = svg
        if not svg:
            compare.innerText = "Choose two sessions to overlay them: A is drawn solid, B dashed."
    caption = document.getElementById("library-compare-caption")
    if caption is not None:
        a, b = library_get(library_a), library_get(library_b) if library_b else None
        caption.innerText = (
            f"A (solid): {library_summary_text(a)} B (dashed): {library_summary_text(b)}" if a and b else ""
        )


def _make_library_delete_handler(record_id):
    def handler(event=None):
        library_delete(record_id)
        render()
    return handler


def on_toggle_library(event=None):
    global library_open
    library_open = not library_open
    render_library()


def on_library_save(event=None):
    library_save_current()
    render_library()


def _make_library_select_handler(name):
    def handler(event=None):
        value = str(getattr(getattr(event, "target", None), "value", ""))
        globals()[name] = value
        if name == "library_overlay_id":
            render_graphs()
        render_library()
    return handler


# ---- D-9 Harbor Almanac ----------------------------------------------------
ALMANAC_LIFETIME = [
    ("seasons", "Seasons played"),
    ("rows_kept", "Rows kept dry (counted each season)"),
    ("heritage", "Heritage sites protected"),
    ("storms", "Storms weathered"),
]


def _empty_almanac():
    return {key: 0 for key, _label in ALMANAC_LIFETIME} | {"best": {}}


def _load_almanac():
    data = _empty_almanac()
    raw = _read_local_storage_item(ALMANAC_KEY)
    if not raw:
        return data
    try:
        saved = json.loads(raw)
    except (ValueError, TypeError):
        return data
    if not isinstance(saved, dict):
        return data
    for key, _label in ALMANAC_LIFETIME:
        value = saved.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 10**9:
            data[key] = value
    best = saved.get("best")
    if isinstance(best, dict):
        for combo, entry in best.items():
            scenario, _sep, lag = str(combo).partition("|")
            if (
                scenario in SEA_SCENARIOS and lag in ("standard", "hard") and isinstance(entry, dict)
                and _finite_number(entry.get("score"), -1e9, 1e9)
                and isinstance(entry.get("seasons"), int) and 0 <= entry["seasons"] <= 10**6
                and isinstance(entry.get("tier"), int) and 0 <= entry["tier"] < len(ADAPTATION_TIERS)
                and isinstance(entry.get("rows_dry"), int) and 0 <= entry["rows_dry"] <= COASTLINE_ROWS
            ):
                data["best"][combo] = {
                    "score": round(float(entry["score"]), 1), "seasons": entry["seasons"],
                    "tier": entry["tier"], "rows_dry": entry["rows_dry"],
                    "retreat": _clamped_int(entry.get("retreat"), 0, RETREAT_MAX_STEPS),
                    "tourism": _clamped_int(entry.get("tourism"), 0, DIVERSIFY_MAX_LEVEL),
                    "aquaculture": _clamped_int(entry.get("aquaculture"), 0, DIVERSIFY_MAX_LEVEL),
                    "heritage": _clamped_int(entry.get("heritage"), 0, len(HERITAGE_SITES)),
                }
    return data


almanac = _empty_almanac()  # filled from localStorage just before setup(), once every helper exists
# Where the almanac has counted up to in THIS run (so loading a save or rewinding to a
# checkpoint never counts the same season twice).
_almanac_cursor = {"season": 1, "protected": 0}
almanac_open = False


def almanac_combo_key():
    return f"{state.sea_scenario}|{'hard' if state.hard_lag_mode else 'standard'}"


def almanac_resync():
    _almanac_cursor["season"] = state.season
    _almanac_cursor["protected"] = state.protected_heritage_count()


def almanac_sync():
    """Adds whatever happened since the last call to the lifetime totals and updates the
    personal best for this scenario and lag mode. Called from render(), so it is idempotent."""
    cursor = _almanac_cursor
    if state.season < cursor["season"]:
        cursor["season"] = state.season
    new_seasons = state.season - cursor["season"]
    changed = False
    if new_seasons > 0:
        almanac["seasons"] += new_seasons
        for entry in state.season_ledger:
            if cursor["season"] <= entry["season"] < state.season:
                almanac["rows_kept"] += entry["rows_dry"]
        for storm in state.storm_log:
            if cursor["season"] <= storm["season"] < state.season:
                almanac["storms"] += 1
        cursor["season"] = state.season
        changed = True
    protected = state.protected_heritage_count()
    if protected > cursor["protected"]:
        almanac["heritage"] += protected - cursor["protected"]
        changed = True
    cursor["protected"] = protected
    if new_seasons > 0:
        score = round(state.damage_saved(), 1)
        key = almanac_combo_key()
        best = almanac["best"].get(key)
        if best is None or score > best["score"]:
            almanac["best"][key] = {
                "score": score, "seasons": state.season - 1, "tier": state.current_tier_index(),
                "rows_dry": state.rows_dry_count(), "retreat": len(state.retreat_rows),
                "tourism": state.diversification["tourism"],
                "aquaculture": state.diversification["aquaculture"], "heritage": protected,
            }
    if changed:
        _write_local_storage_item(ALMANAC_KEY, json.dumps(almanac, separators=(",", ":")))


def almanac_best_text(entry):
    parts = [f"tier {TIER_BADGES[entry['tier']]} {ADAPTATION_TIERS[entry['tier']]['name']}"]
    if entry["retreat"]:
        parts.append(f"retreat x{entry['retreat']}")
    if entry["tourism"] or entry["aquaculture"]:
        parts.append(f"tourism {entry['tourism']}, aquaculture {entry['aquaculture']}")
    if entry["heritage"]:
        parts.append(f"{entry['heritage']} heritage site(s)")
    return (
        f"{entry['score']:.0f} damage avoided over {entry['seasons']} seasons, "
        f"{entry['rows_dry']} of {COASTLINE_ROWS} rows dry; " + ", ".join(parts)
    )


def almanac_best_line():
    """D-25: one line for the session summary, from the almanac."""
    entry = almanac["best"].get(almanac_combo_key())
    lag = "harder lag" if state.hard_lag_mode else "standard lag"
    if entry is None:
        return ""
    return (
        f"Best for the {state.sea_scenario} sea with {lag}: {entry['score']:.0f} damage avoided over "
        f"{entry['seasons']} seasons. This session: {state.damage_saved():.0f} over {max(0, state.season - 1)}."
    )


def almanac_rows_html():
    rows = []
    for scenario, config in SEA_SCENARIOS.items():
        for lag, lag_label in (("standard", "Standard lag"), ("hard", "Harder lag")):
            key = f"{scenario}|{lag}"
            entry = almanac["best"].get(key)
            current = " (this session)" if key == almanac_combo_key() else ""
            label = f"{scenario.capitalize()} sea, {lag_label}{current}"
            rows.append(
                f"<tr><th scope=\"row\">{html.escape(label)}</th>"
                f"<td>{html.escape(almanac_best_text(entry)) if entry else 'No run yet'}</td></tr>"
            )
    return "".join(rows)


def render_almanac():
    toggle = document.getElementById("almanac-toggle-button")
    panel = document.getElementById("almanac-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Harbor Almanac" if almanac_open else "📖 Harbor Almanac"
    panel.hidden = not almanac_open
    if not almanac_open:
        return
    lifetime = document.getElementById("almanac-lifetime")
    if lifetime is not None:
        lifetime.innerHTML = "".join(
            f"<li><strong>{almanac[key]}</strong> {html.escape(label.lower())}</li>"
            for key, label in ALMANAC_LIFETIME
        )
    best = document.getElementById("almanac-best-body")
    if best is not None:
        best.innerHTML = almanac_rows_html()


def on_toggle_almanac(event=None):
    global almanac_open
    almanac_open = not almanac_open
    render_almanac()


# ---- D-6 season planner -----------------------------------------------------
planner_open = False
planner_length = PLANNER_MIN_SEASONS
planner_plan = [{category: 0 for category in CATEGORIES} for _ in range(PLANNER_MAX_SEASONS)]


def project_plan(plan, length):
    """Runs the staged investments through a COPY of the settlement and returns one dict
    per planned season (plus the starting point first). The real state is never touched."""
    global state
    real = state
    simulated = copy.deepcopy(real)
    state = simulated
    points = [_planner_point(simulated, 0, 0)]
    try:
        for index in range(max(0, min(int(length), PLANNER_MAX_SEASONS))):
            skipped = 0
            for category in CATEGORIES:
                for _ in range(plan[index].get(category, 0)):
                    if not simulated.invest(category):
                        skipped += 1
            simulated.advance_season()
            points.append(_planner_point(simulated, index + 1, skipped))
    finally:
        state = real
    return points


def _planner_point(sim, step, skipped):
    at_risk = sum(
        1 for row in range(COASTLINE_ROWS)
        if not sim.row_lost(row) and sim.seasons_until_flood(row) <= PLANNER_RISK_SEASONS
    )
    return {
        "step": step, "season": sim.season, "funds": sim.funds, "acidity": sim.acidity,
        "fish_yield": sim.fish_yield_multiplier(), "rows_dry": sim.rows_dry_count(),
        "rows_at_risk": at_risk, "tier": sim.current_tier_index(), "skipped": skipped,
        "damage": sim.damage_log[-1] if step else 0.0,
    }


def planner_chart_svg(points):
    if len(points) < 2:
        return ""
    step = SPARKLINE_WIDTH / (len(points) - 1)
    acid = _xy([min(1.0, p["acidity"] / FISH_DAMAGE_SCALE) for p in points], step)
    fish = _xy([p["fish_yield"] for p in points], step)
    risk = _xy([p["rows_at_risk"] / COASTLINE_ROWS for p in points], step)
    lines = [
        ("Now" if p["step"] == 0 else f"Planned season {p['step']}")
        + f": acidity {p['acidity']:.1f}, fishing yield {p['fish_yield'] * 100:.0f}%, "
        f"{p['rows_at_risk']} dry row(s) at risk, funds {p['funds']:.0f}"
        for p in points
    ]
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" class="acidity-fish-sparkline" '
        f'role="img" tabindex="0"{_crosshair_attr(lines)} '
        f'aria-label="Projected acidity (purple), fishing yield (green) and dry rows at risk (amber) '
        f'over the planned seasons. Left and right arrow keys read each season.">'
        f'{_series_svg(acid, "acidity")}{_series_svg(fish, "fish", dash="5 3")}'
        f'{_series_svg(risk, "risk", dash="2 2")}</svg>'
    )


def planner_summary_text(points):
    if len(points) < 2:
        return "Stage some investments to see where they lead."
    last = points[-1]
    skipped = sum(p["skipped"] for p in points)
    text = (
        f"After {len(points) - 1} planned season(s) you would be at Season {last['season']} with "
        f"{last['funds']:.0f} funds, acidity {last['acidity']:.1f}, fishing yield "
        f"{last['fish_yield'] * 100:.0f}%, {last['rows_dry']} of {COASTLINE_ROWS} rows dry and "
        f"{last['rows_at_risk']} of those at risk (flooding within {PLANNER_RISK_SEASONS} seasons)."
    )
    if skipped:
        text += f" {skipped} staged investment(s) were not affordable and were skipped."
    return text + " This is a projection only; nothing has been spent."


def planner_rows_html(points):
    rows = []
    for p in points[1:]:
        flag = f" ({p['skipped']} not affordable)" if p["skipped"] else ""
        rows.append(
            f"<tr><td>{p['season'] - 1}</td><td>{p['funds']:.0f}{flag}</td><td>{p['acidity']:.1f}</td>"
            f"<td>{p['fish_yield'] * 100:.0f}%</td><td>{p['damage']:.0f}</td>"
            f"<td>{p['rows_dry']}</td><td>{p['rows_at_risk']}</td>"
            f"<td>{TIER_BADGES[p['tier']]} {p['tier']}</td></tr>"
        )
    return "".join(rows)


def render_planner():
    toggle = document.getElementById("planner-toggle-button")
    panel = document.getElementById("planner-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Season Planner" if planner_open else "🧭 Season Planner"
    panel.hidden = not planner_open
    if not planner_open:
        return
    length_select = document.getElementById("planner-length")
    if length_select is not None and str(length_select.value) != str(planner_length):
        length_select.value = str(planner_length)
    for number in range(1, PLANNER_MAX_SEASONS + 1):
        row = document.getElementById(f"planner-row-{number}")
        if row is not None:
            row.hidden = number > planner_length
        for category in CATEGORIES:
            field = document.getElementById(f"planner-s{number}-{category}")
            if field is not None and str(field.value) != str(planner_plan[number - 1][category]):
                field.value = str(planner_plan[number - 1][category])
    points = project_plan(planner_plan, planner_length)
    body = document.getElementById("planner-body")
    if body is not None:
        body.innerHTML = planner_rows_html(points)
    chart = document.getElementById("planner-chart")
    if chart is not None:
        chart.innerHTML = planner_chart_svg(points)
    summary = document.getElementById("planner-summary")
    if summary is not None:
        summary.innerText = planner_summary_text(points)
    commit = document.getElementById("planner-commit-button")
    if commit is not None:
        commit.innerText = f"Commit season {state.season} (spend and advance)"


def on_toggle_planner(event=None):
    global planner_open
    planner_open = not planner_open
    render_planner()


def on_planner_length(event=None):
    global planner_length
    try:
        value = int(float(getattr(getattr(event, "target", None), "value", "")))
    except (TypeError, ValueError):
        return
    planner_length = max(PLANNER_MIN_SEASONS, min(PLANNER_MAX_SEASONS, value))
    render_planner()


def _make_planner_input_handler(number, category):
    def handler(event=None):
        try:
            value = int(float(getattr(getattr(event, "target", None), "value", "")))
        except (TypeError, ValueError):
            value = 0
        planner_plan[number - 1][category] = max(0, min(PLANNER_MAX_PER_CATEGORY, value))
        render_planner()
    return handler


def on_planner_clear(event=None):
    for entry in planner_plan:
        for category in CATEGORIES:
            entry[category] = 0
    render_planner()


def on_planner_commit(event=None):
    """Applies the FIRST planned season for real (invest, then advance) and slides the
    rest of the plan up one place."""
    plan = planner_plan[0]
    bought = 0
    for category in CATEGORIES:
        for _ in range(plan[category]):
            if state.invest(category):
                bought += 1
    state.advance_season()
    del planner_plan[0]
    planner_plan.append({category: 0 for category in CATEGORIES})
    render()
    announce(f"Committed the first planned season: {bought} investment(s). " + state.season_result_text())
    _set_advance_note("")


# ---- D-7 announcements -------------------------------------------------
def announce(text):
    """Writes into the polite live region screen readers watch."""
    region = document.getElementById("season-announcer")
    if region is not None:
        region.innerText = text


# ---- D-24 tab title and favicon ----------------------------------------
_FAVICON_ORIGINAL = None


def _favicon_data_uri(kind):
    """A small wave badge; a warning adds an amber circle, a storm a red
    square (a different shape, so the two are not told apart by hue alone)."""
    marker = ""
    if kind == "warning":
        marker = '<circle cx="23" cy="9" r="7" fill="#f5a623" stroke="#fff" stroke-width="1.5"/>'
    elif kind == "storm":
        marker = '<rect x="16" y="2" width="14" height="14" fill="#e03e3e" stroke="#fff" stroke-width="1.5"/>'
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="7" fill="#0e5a8a"/>'
        '<path d="M3 20 Q8 14 13 20 T23 20 T31 20 V30 H3Z" fill="#7fd4ee"/>'
        f"{marker}</svg>"
    )
    return "data:image/svg+xml," + svg.replace("<", "%3C").replace(">", "%3E").replace("#", "%23").replace('"', "'")


def tab_status():
    """(title, favicon kind) for the current state."""
    title = f"Tide S{state.season}"
    reasons = state.attention_reasons()
    kinds = [kind for kind, _text in reasons]
    if "storm" in kinds:
        return title + " - storm forecast", "storm"
    if "fish" in kinds:
        return title + " - fish warning", "warning"
    if "heritage" in kinds:
        return title + " - heritage at risk", "warning"
    return title, "normal"


def update_tab_status():
    global _FAVICON_ORIGINAL
    title, kind = tab_status()
    try:
        document.title = title
    except Exception:
        pass
    query = getattr(document, "querySelector", None)
    if query is None:
        return
    link = query('link[rel="icon"]')
    if link is None:
        return
    if _FAVICON_ORIGINAL is None:
        _FAVICON_ORIGINAL = link.href
    link.href = _FAVICON_ORIGINAL if kind == "normal" else _favicon_data_uri(kind)


# ---- D-18 copy as text -------------------------------------------------
_copy_proxies = {}


def _copy_to_clipboard(text, on_done=None, on_fail=None):
    """True when a clipboard write was started. The browser promise's own
    outcome is reported through on_done/on_fail when they are given."""
    navigator = getattr(_js, "navigator", None)
    clipboard = getattr(navigator, "clipboard", None) if navigator is not None else None
    if clipboard is None:
        return False
    try:
        promise = clipboard.writeText(text)
        if on_done is not None and on_fail is not None and hasattr(promise, "then"):
            for name, handler in (("done", on_done), ("fail", on_fail)):
                _copy_proxies[name] = create_proxy(handler)
            promise.then(_copy_proxies["done"], _copy_proxies["fail"])
        return True
    except Exception:
        return False


def _show_copy_fallback(text):
    status = document.getElementById("copy-text-status")
    area = document.getElementById("copy-text-area")
    if area is not None:
        area.hidden = False
        area.value = text
    if status is not None:
        status.innerText = "Could not copy automatically. Select the text below and copy it yourself."


def on_copy_text(event=None):
    text = state.share_text()
    status = document.getElementById("copy-text-status")
    area = document.getElementById("copy-text-area")
    if area is not None:
        area.hidden = True

    def done(_result=None):
        if status is not None:
            status.innerText = "Copied your settlement summary to the clipboard."

    def failed(_error=None):
        _show_copy_fallback(text)

    if _copy_to_clipboard(text, done, failed):
        if status is not None:
            status.innerText = "Copying..."
    else:
        _show_copy_fallback(text)


def render_output_mix_controls():
    """D16: keeps the output-mix <select> showing whatever mix is
    actually live -- needed because load_state() can change output_mix
    from a code path other than the dropdown itself."""
    select = document.getElementById("output-mix-select")
    if select is not None:
        select.value = state.output_mix
    # D22: live preview of every mix's per-season trade-off at current
    # capacity, so the choice is informed before it's made.
    preview_el = document.getElementById("output-mix-preview")
    if preview_el is not None:
        parts = []
        for mix in OUTPUT_MIX:
            income, acidity = state.output_mix_preview(mix)
            parts.append(f"{mix.capitalize()}: {income:+.0f} funds, {acidity:+.1f} acidity")
        preview_el.innerText = "Per season at current capacity — " + " | ".join(parts)


def render_fish_recovery_banner():
    """D23: shown for the season a crashed fish stock finishes rebuilding."""
    banner = document.getElementById("fish-recovery-banner")
    if banner is None:
        return
    if state.recovery_celebrated_season and state.recovery_celebrated_season == state.season:
        banner.hidden = False
        banner.innerText = (
            "🎉 Recovery! The fish stock has rebuilt — the lag that delayed the "
            "damage also delayed the healing, and your cleaner choices got you here."
        )
    else:
        banner.hidden = True


def render_sea_scenario_controls():
    """D19: syncs the scenario <select>, locking it once play has begun."""
    select = document.getElementById("sea-scenario-select")
    if select is not None:
        select.value = state.sea_scenario
        select.disabled = bool(state.damage_log) or state.season != 1


def render_settlement_history():
    """D29: the settlement's name field and chronicle."""
    heading = document.getElementById("settlement-heading")
    if heading is not None:
        heading.innerText = f"{state.display_name()} — chronicle"
    name_input = document.getElementById("settlement-name-input")
    if name_input is not None and name_input.value != state.settlement_name:
        name_input.value = state.settlement_name
    log_el = document.getElementById("settlement-chronicle")
    if log_el is not None:
        lines = state.chronicle_lines()
        log_el.innerHTML = (
            "<br>".join(lines) if lines else "Nothing to record yet — history starts as you play."
        )


def render_programmes():
    """D17 / D21 / D13 (and later additions): the collapsed "Coastal
    programmes" section's readouts and button states."""
    for i, site in enumerate(HERITAGE_SITES):
        status_el = document.getElementById(f"heritage-status-{i}")
        if status_el is not None:
            status_el.innerText = heritage_status_text(site)
        button = document.getElementById(f"heritage-protect-{i}")
        if button is not None:
            button.innerText = f"Protect ({site['cost']})"
            button.disabled = not (
                state.heritage.get(site["id"]) == HERITAGE_UNPROTECTED
                and state.funds >= site["cost"]
                and not state.row_lost(site["row"])
            )
    monitor_button = document.getElementById("monitor-button")
    if monitor_button is not None:
        if state.monitoring_reports >= len(CITIZEN_SCIENCE_FACTS):
            monitor_button.innerText = "All monitoring reports collected"
        elif (
            state.monitoring_last_season
            and state.season - state.monitoring_last_season < MONITOR_COOLDOWN_SEASONS
        ):
            monitor_button.innerText = "Monitoring crews are out — report next season"
        else:
            monitor_button.innerText = f"Fund monitoring ({MONITOR_COST})"
        monitor_button.disabled = not state.can_monitor()
    monitor_log = document.getElementById("monitor-log")
    if monitor_log is not None:
        facts = state.revealed_facts()
        monitor_log.innerHTML = (
            "<br>".join(f"{i + 1}. {fact}" for i, fact in enumerate(facts))
            if facts
            else "No reports yet — each funded report reveals a real-world finding."
        )
    # D1 managed retreat.
    retreat_button = document.getElementById("retreat-button")
    if retreat_button is not None:
        retreat_button.innerText = (
            f"Managed retreat ({RETREAT_COST})"
            if len(state.retreat_rows) < RETREAT_MAX_STEPS
            else "Managed retreat complete"
        )
        retreat_button.disabled = not state.can_retreat()
    retreat_el = document.getElementById("retreat-status")
    if retreat_el is not None:
        steps = len(state.retreat_rows)
        retreat_el.innerText = (
            f"Retreat steps taken: {steps}/{RETREAT_MAX_STEPS} — sea-level damage cut a further "
            f"{steps * RETREAT_DAMAGE_CUT * 100:.0f}% (compounding with your tier), at the price of "
            f"{steps} row(s) of coast."
        )
    # D5 / D15 population, always visible in the status block.
    population_el = document.getElementById("population-display")
    if population_el is not None:
        population_el.innerText = state.population_text()
    # D11 diversification.
    for kind, cost in DIVERSIFY_COST.items():
        button = document.getElementById(f"diversify-{kind}-button")
        if button is not None:
            level = state.diversification[kind]
            button.innerText = (
                f"{kind.capitalize()} level {level}/{DIVERSIFY_MAX_LEVEL} — max"
                if level >= DIVERSIFY_MAX_LEVEL
                else f"{kind.capitalize()} level {level}/{DIVERSIFY_MAX_LEVEL} — upgrade ({cost})"
            )
            button.disabled = level >= DIVERSIFY_MAX_LEVEL or state.funds < cost
    diversify_el = document.getElementById("diversify-status")
    if diversify_el is not None:
        tourism, aquaculture = state.diversified_income()
        diversify_el.innerText = (
            f"Extra income per season: tourism {tourism:.1f}, aquaculture {aquaculture:.1f}. "
            "Neither depends on the lagged fish-yield crash; tourism fades as coast is lost."
        )
    # D27 checkpoint replay.
    checkpoint_el = document.getElementById("checkpoint-status")
    if checkpoint_el is not None:
        checkpoint_el.innerText = (
            f"Checkpoint set at Season {state.checkpoint['season']}."
            if state.checkpoint
            else "No checkpoint set."
        ) + (f" Replays so far: {state.replay_count}." if state.replay_count else "")
    replay_button = document.getElementById("replay-button")
    if replay_button is not None:
        replay_button.disabled = not state.can_replay()
    foresight_el = document.getElementById("foresight-display")
    if foresight_el is not None:
        foresight_el.innerText = state.foresight_text()
    storm_button = document.getElementById("storm-toggle-button")
    if storm_button is not None:
        storm_button.innerText = "Storm seasons: On (turn off)" if state.storm_mode else "Storm seasons: Off (turn on)"
    storm_el = document.getElementById("storm-forecast")
    if storm_el is not None:
        storm_el.innerText = storm_forecast_text()


def storm_forecast_text():
    wait = state.seasons_until_storm()
    if wait is None:
        return "Storm seasons are off. Turn them on for a surge every 5 seasons that tests your adaptation tier."
    surge = state.storm_surge_strength()
    held = surge * state.dampening_fraction()
    when = "this season's end" if wait == 0 else f"{wait} season(s) from now"
    return (
        f"Forecast: a surge of about {surge:.0f} arrives at {when}; your current tier would hold back "
        f"about {held:.0f} of it."
    )


def render_hard_lag_toggle():
    """D9: keeps the toggle button's label in sync with the live mode."""
    button = document.getElementById("hard-lag-toggle-button")
    if button is not None:
        button.innerText = (
            "Harder Lag: On (turn off)" if state.hard_lag_mode else "Harder Lag: Off (turn on)"
        )


# FY-2 (Tide D10): the acidity from three seasons ago, shown beside the
# current one so the delay between cause and effect is visible as numbers.
ACIDITY_PAST_SEASONS = 3


def acidity_past_text():
    """'Three seasons ago: acidity 2.3 (now 3.1, up 0.8)' once three seasons are banked."""
    history = state.acidity_history
    if len(history) < ACIDITY_PAST_SEASONS:
        return f"Three seasons ago: not yet played ({len(history)} of {ACIDITY_PAST_SEASONS} seasons banked)"
    past = history[-ACIDITY_PAST_SEASONS]
    change = state.acidity - past
    if abs(change) < 0.05:
        word = "unchanged"
    elif change > 0:
        word = f"up {change:.1f}"
    else:
        word = f"down {-change:.1f}"
    return f"Three seasons ago: acidity {past:.1f} (now {state.acidity:.1f}, {word})"


def render():
    render_info_page()
    render_sister()
    document.getElementById("season-display").innerText = f"Season {state.season}"
    document.getElementById("funds-display").innerText = f"Funds: {state.funds:.0f}"
    document.getElementById("acidity-display").innerText = f"Ocean acidity: {state.acidity:.1f}"
    document.getElementById("acidity-past-display").innerText = acidity_past_text()
    acidity_fraction = min(1.0, state.acidity / FISH_DAMAGE_SCALE)
    document.getElementById("acidity-bar").style.width = f"{acidity_fraction * 100:.0f}%"

    fish_yield = state.fish_yield_multiplier()
    document.getElementById("fish-yield-display").innerText = f"Fishing yield: {fish_yield * 100:.0f}%"
    document.getElementById("fish-yield-bar").style.width = f"{fish_yield * 100:.0f}%"
    render_fish_warning_banner()
    render_fish_recovery_banner()
    survived_el = document.getElementById("seasons-survived-display")
    if survived_el is not None:
        survived_el.innerText = f"Seasons survived: {max(0, state.season - 1)}"
    document.getElementById("sea-level-display").innerText = f"Sea level: {state.sea_level:.0f}"
    document.getElementById("damage-display").innerText = (
        f"Cumulative damage: {state.cumulative_damage:.0f}"
    )
    document.getElementById("damage-saved-display").innerText = damage_saved_message(state.damage_saved())
    document.getElementById("damage-trend-display").innerText = damage_trend_message(state.damage_trend())
    tier = state.current_tier()
    document.getElementById("adaptation-tier-display").innerText = (
        f"Adaptation tier: {tier['name']} ({tier['dampening'] * 100:.0f}% damage dampening)"
    )
    document.getElementById("adaptation-tier-progress").innerText = state.next_tier_progress_text()

    # D3: seasons until the next currently-unflooded row goes under.
    next_flood_el = document.getElementById("next-flood-display")
    if next_flood_el is not None:
        remaining = state.next_flood_estimate()
        next_flood_el.innerText = (
            "Every coastline row is already flooded."
            if remaining <= 0
            else f"Next row floods in an estimated {remaining} season(s)."
        )

    # D12: the single worst season played so far.
    worst_el = document.getElementById("worst-season-display")
    if worst_el is not None:
        worst = state.worst_season()
        cause = state.worst_season_cause()
        worst_el.innerText = (
            f"Worst season: Season {worst[0]} ({worst[1]:.0f} damage)"
            + (f" — {cause}." if cause else ".")
            if worst
            else "Worst season: none yet."
        )

    render_coastline()
    render_coastline_comparison()

    # D4: a numeric then-vs-now companion to the visual comparison grids.
    then_vs_now_el = document.getElementById("then-vs-now-display")
    if then_vs_now_el is not None:
        then_vs_now_el.innerText = state.then_vs_now_text()

    # D6: "what if you'd invested earlier" counterfactual replay.
    counterfactual_el = document.getElementById("counterfactual-display")
    if counterfactual_el is not None:
        counterfactual_el.innerText = state.counterfactual_message()

    # D13: cross-session personal-best coastline-damage-saved record.
    _maybe_update_best_coastline_saved()
    render_best_coastline_saved()

    # D15 / D7: the trend graphs (range, markers, crosshair data, compared session).
    render_graph_controls()
    render_graphs()
    consequence_text = document.getElementById("delayed-consequence-text")
    if consequence_text is not None:
        consequence_text.innerText = state.delayed_consequence_text()
    # D8: this season's tide.
    tide_el = document.getElementById("tide-indicator")
    if tide_el is not None:
        tide_el.innerText = state.tide_text()
    render_settlement_history()

    sea_level_bar = document.getElementById("sea-level-bar")
    sea_level_bar.style.width = f"{state.sea_level_fraction() * 100:.0f}%"

    # D4: decorative wave/tide cue next to the meter -- speed only, never
    # touches the meter's own width/text above.
    wave_cue = document.getElementById("sea-level-wave-cue")
    if wave_cue is not None:
        duration = sea_level_wave_cue_duration(state.sea_level_fraction())
        wave_cue.style.animationDuration = f"{duration:.2f}s"

    ticker_el = document.getElementById("ticker-log")
    if state.ticker_log:
        ticker_el.innerHTML = "<br>".join(state.ticker_log)
    else:
        ticker_el.innerHTML = "No notable changes yet."
    render_ticker_history()

    for category in CATEGORIES:
        document.getElementById(f"{category}-count").innerText = str(state.capacity[category])
        invest_button = document.getElementById(f"{category}-invest-button")
        invest_button.innerText = f"Invest ({INVEST_COST[category]})"
        invest_button.disabled = state.funds < INVEST_COST[category]
        # D-7: three buttons all reading "Invest (30)" are ambiguous to a screen reader.
        invest_button.setAttribute(
            "aria-label", f"Invest {INVEST_COST[category]} funds in {INVEST_LABELS[category]}"
        )

    render_output_mix_controls()
    render_sea_scenario_controls()
    badge = document.getElementById("adaptation-tier-badge")
    if badge is not None:
        badge.innerText = TIER_BADGES[state.current_tier_index()]
        badge.title = f"Current tier: {state.current_tier()['name']}"
    render_hard_lag_toggle()
    render_programmes()
    update_achievements_display()
    update_changelog_display()
    update_session_summary_display()
    render_ledger()
    render_scrubber()
    render_library()
    render_planner()
    almanac_sync()
    render_almanac()
    update_tab_status()
    _sync_earned_and_toast()


INVEST_LABELS = {"output": "Output", "reduction": "Acidity Reduction", "adaptation": "Adaptation"}


def _make_invest_handler(category):
    def handler(event=None):
        funds_before = state.funds
        done = state.invest(category)
        render()
        if done:
            announce(f"Invested in {INVEST_LABELS[category]}. Funds now {state.funds:.0f}.")
        elif funds_before < INVEST_COST[category]:
            announce(f"Not enough funds to invest in {INVEST_LABELS[category]}.")
    return handler


def on_advance_season(event=None):
    state.advance_season()
    render()
    announce(state.season_result_text())
    _set_advance_note("")


def _set_advance_note(text):
    note = document.getElementById("advance-x5-note")
    if note is not None:
        note.innerText = text


def on_advance_x5(event=None):
    """D-15: up to five quiet seasons in one click; stops before any season
    that needs a decision and says why."""
    ran, stop_text = state.advance_quiet_seasons(ADVANCE_BATCH)
    render()
    if ran == 0:
        note = f"Not started: {stop_text}. Use Advance Season to go one at a time."
    elif stop_text:
        note = f"Ran {ran} season(s), then stopped: {stop_text}."
    else:
        note = f"Ran {ADVANCE_BATCH} quiet seasons."
    _set_advance_note(note)
    announce((state.season_result_text() + " " if ran else "") + note)


def on_output_mix_change(event):
    """D16: reads the <select>'s chosen value the same way Canopy's own
    on_grid_size_change() reads event.target.value from a real DOM change
    event; an unrecognized value is a silent no-op via set_output_mix()."""
    state.set_output_mix(event.target.value)
    render()


def on_sea_scenario_change(event):
    state.set_sea_scenario(event.target.value)
    render()


def on_enable_sister(event=None):
    if state.enable_sister():
        render()


def render_sister():
    button = document.getElementById("sister-enable-button")
    text = document.getElementById("sister-display")
    button.hidden = state.sister_enabled
    text.hidden = not state.sister_enabled
    text.innerText = state.sister_text()


def on_toggle_hard_lag(event=None):
    state.set_hard_lag_mode(not state.hard_lag_mode)
    render()


def _make_heritage_handler(site_id):
    def handler(event=None):
        state.protect_heritage(site_id)
        render()
    return handler


def on_retreat(event=None):
    state.managed_retreat()
    render()


def _make_diversify_handler(kind):
    def handler(event=None):
        state.diversify(kind)
        render()
    return handler


def on_set_checkpoint(event=None):
    state.set_checkpoint()
    render()


def replay_from_checkpoint():
    """D27: rewinds to the checkpoint, keeping a record of what happened
    afterwards in the abandoned run as "foresight" -- unlike D6's
    counterfactual (a what-if computed on the same history), the player
    actually plays the stretch again knowing what is coming."""
    if not state.can_replay():
        return False
    snapshot = copy.deepcopy(state.checkpoint)
    start = snapshot["season"]
    rise = state.sea_rise_per_season()
    foresight = []
    for season in range(start, state.season):
        index = season - 1
        if index >= len(state.damage_log) or index >= len(state.fish_yield_history):
            continue
        foresight.append(
            {
                "season": season,
                "fish_yield": state.fish_yield_history[index],
                "damage": state.damage_log[index],
                "flooded": flooded_row_count(rise * season),
            }
        )
    replays = state.replay_count + 1
    kept_ledger = [e for e in state.season_ledger if e["season"] < start]
    kept_snapshots = [x for x in state.season_snapshots if x[0] < start]
    load_state(snapshot)
    state.season_ledger = kept_ledger
    state.season_snapshots = kept_snapshots
    state.checkpoint = copy.deepcopy(snapshot)
    state.foresight = foresight
    state.replay_count = replays
    state._log_ticker(
        f"Replaying from Season {start} — you now know what the earlier run brought."
    )
    render()
    return True


def on_replay(event=None):
    replay_from_checkpoint()


def on_monitor(event=None):
    state.fund_monitoring()
    render()


def on_toggle_storms(event=None):
    state.set_storm_mode(not state.storm_mode)
    render()


def on_settlement_name_change(event):
    """D29: reads the text input's value on change."""
    if state.set_settlement_name(event.target.value) and state.settlement_name:
        if not any("Founded" in e["text"] for e in state.chronicle):
            state.chronicle.insert(0, {"season": state.season, "text": f"Founded as {state.settlement_name}."})
    render()


def on_set_baseline(event=None):
    state.set_comparison_baseline()
    render()


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state() packages every module-level mutable global — here, all of
# it lives on the single `state` object — into a plain JSON-safe dict
# (numbers/strings/lists/dicts/bools only, no SettlementState instance
# itself crossing the boundary). The three log lists and the capacity
# dict are deep-copied so a live reference into `state` is never leaked
# into the saved snapshot; a shallow reference would let continued play
# after "saving" silently mutate what was supposed to be a frozen copy
# (same reasoning as SOL's serialize_state() docstring). Tide tracks no
# non-JSON-native types (no sets, unlike SOL's unlocked_bodies), so no
# extra conversion is needed. load_state() is the exact inverse, then
# calls render() (Tide's full-render function) so the UI reflects the
# loaded state immediately.
def _tier_first_season_field():
    """D9: the season each adaptation tier was first active, for the tiers this
    settlement has reached (t1 = sandbag berms, ...). A write-only number
    group for the community seawall comparison; never read back."""
    first = {}
    for tier_index in range(1, len(ADAPTATION_TIERS)):
        for i, tier in enumerate(state.tier_log):
            if tier >= tier_index:
                first[f"t{tier_index}"] = i + 1
                break
    return {"tier_first_season": first} if first else {}


def get_state():
    return {
        "season": state.season,
        "funds": state.funds,
        "capacity": copy.deepcopy(state.capacity),
        "acidity": state.acidity,
        "acidity_history": copy.deepcopy(state.acidity_history),
        "sea_level": state.sea_level,
        "cumulative_damage": state.cumulative_damage,
        "undampened_damage_total": state.undampened_damage_total,
        "damage_log": copy.deepcopy(state.damage_log),
        "ticker_log": copy.deepcopy(state.ticker_log),
        "trend_flattening_announced": state.trend_flattening_announced,
        "ticker_full_history": copy.deepcopy(state.ticker_full_history),
        "hard_lag_mode": state.hard_lag_mode,
        **(
            {"sister": {
                "damage": state.sister_cumulative_damage, "net_funds": state.sister_net_funds,
            }}
            if state.sister_enabled else {}
        ),
        "output_mix": state.output_mix,
        "fish_yield_history": copy.deepcopy(state.fish_yield_history),
        "first_flood_announced": state.first_flood_announced,
        "baseline_season": state.baseline_season,
        "baseline_sea_level": state.baseline_sea_level,
        "baseline_damage": state.baseline_damage,
        "min_fish_yield_ever": state.min_fish_yield_ever,
        "max_acidity_ever": state.max_acidity_ever,
        "max_funds_ever": state.max_funds_ever,
        "fortified_in_time_earned": state.fortified_in_time_earned,
        "tier_log": copy.deepcopy(state.tier_log),
        **_tier_first_season_field(),
        "hard_lag_note_seen": state.hard_lag_note_seen,
        "fish_crash_open": state.fish_crash_open,
        "recovery_celebrated_season": state.recovery_celebrated_season,
        "sea_scenario": state.sea_scenario,
        "settlement_name": state.settlement_name,
        "chronicle": copy.deepcopy(state.chronicle),
        "heritage": copy.deepcopy(state.heritage),
        "monitoring_reports": state.monitoring_reports,
        "monitoring_last_season": state.monitoring_last_season,
        "storm_mode": state.storm_mode,
        "storm_log": copy.deepcopy(state.storm_log),
        "retreat_rows": list(state.retreat_rows),
        "population": state.population,
        "peak_population": state.peak_population,
        "displaced_total": state.displaced_total,
        "relocated_total": state.relocated_total,
        "diversification": dict(state.diversification),
        "checkpoint": copy.deepcopy(state.checkpoint),
        "foresight": copy.deepcopy(state.foresight),
        "replay_count": state.replay_count,
        "season_ledger": copy.deepcopy(state.season_ledger),
        "season_snapshots": copy.deepcopy(state.season_snapshots),
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) —
        # always freshly recomputed, never read back in load_state().
        "achievements_earned": achievement_ids_earned(),
    }


# Read with .get(), and merge `capacity` key-by-key into the live dict
# rather than replacing it wholesale: `data` may be a hand-edited/
# truncated save code, or simply a payload from a different build of this
# game with a different field set (a save made before some future field
# existed, or capacity category added/removed). Every field used to be
# read with a bare data["..."], so a single missing key raised partway
# through the assignments — leaving some fields already overwritten with
# the save's values and others still at whatever they were before the
# call, a worse outcome than either a clean load or a clean failure. The
# capacity dict specifically wants a key-by-key merge (not just a
# missing-field default) because render() and every invest-cost lookup
# index state.capacity[category] unconditionally for every category in
# CATEGORIES — a wholesale-replaced dict missing a category would crash
# the very next render, not just look wrong (same reasoning as
# Continuum's CITY_KEYED_DICTS).
# REVIEW(patterns): uses defensive data.get(key, default)/isinstance checks
# throughout, returning False on malformed input — diverges from the direct
# data["key"] indexing convention every other game's load_state uses
# (aftermath, canopy, drift, grid, herd, loop, thaw all raise KeyError on a
# malformed/missing field instead). Not documented as an intentional
# deviation in this file's CLAUDE.md.
def _clamped_int(value, low, high):
    """Save-field validator: a real int (not bool) clamped to [low, high],
    else `low`."""
    if isinstance(value, bool) or not isinstance(value, int):
        return low
    return max(low, min(high, value))


def _finite_number(value, low, high):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value == value
        and low <= value <= high
    )


def _load_ledger(saved):
    """D-1: keeps only entries that carry every column as a sane number; a
    save without a ledger (or with a damaged one) loads an empty ledger."""
    if not isinstance(saved, list):
        return []
    ranges = {
        "season": (1, 10**6), "funds": (0, 1e9), "acidity": (0, 1e6), "fish_yield": (0, 1),
        "damage": (0, 1e9), "rows_dry": (0, COASTLINE_ROWS), "population": (0, 10**6),
        "tier": (0, len(ADAPTATION_TIERS) - 1), "invested": (0, 10**6),
    }
    entries = []
    for item in saved:
        if not isinstance(item, dict) or not all(_finite_number(item.get(k), *ranges[k]) for k in LEDGER_KEYS):
            continue
        entries.append(
            {
                "season": int(item["season"]), "funds": float(item["funds"]),
                "acidity": float(item["acidity"]), "fish_yield": float(item["fish_yield"]),
                "damage": float(item["damage"]), "rows_dry": int(item["rows_dry"]),
                "population": int(item["population"]), "tier": int(item["tier"]),
                "invested": int(item["invested"]),
            }
        )
    return entries[-LEDGER_LIMIT:]


def _load_snapshots(saved):
    """D-4: keeps only well-formed [season, sea_level, heritage code, retreat rows]
    entries; a save without them (or with damaged ones) simply has nothing to scrub
    back to for those seasons."""
    if not isinstance(saved, list):
        return []
    entries = []
    allowed = set("upl")
    for item in saved:
        if not (isinstance(item, list) and len(item) == 4):
            continue
        season, sea, code, retreat = item
        if (
            isinstance(season, int) and not isinstance(season, bool) and 1 <= season <= 10**6
            and _finite_number(sea, 0, 1e6)
            and isinstance(code, str) and len(code) == len(HERITAGE_SITES) and set(code) <= allowed
            and isinstance(retreat, list) and len(retreat) <= RETREAT_MAX_STEPS
            and all(isinstance(r, int) and not isinstance(r, bool) and 0 <= r < COASTLINE_ROWS for r in retreat)
        ):
            entries.append([season, float(sea), code, list(retreat)])
    return entries[-SNAPSHOT_LIMIT:]


def _load_sister(data):
    """D3: a save without a valid 'sister' block loads with the sister off."""
    state.sister_enabled = False
    state.sister_cumulative_damage = 0.0
    state.sister_net_funds = 0.0
    saved = data.get("sister")
    if not isinstance(saved, dict):
        return
    state.sister_enabled = True
    damage = saved.get("damage")
    net = saved.get("net_funds")
    if isinstance(damage, (int, float)) and not isinstance(damage, bool) and damage == damage and 0 <= damage < 1e9:
        state.sister_cumulative_damage = float(damage)
    if isinstance(net, (int, float)) and not isinstance(net, bool) and net == net and abs(net) < 1e9:
        state.sister_net_funds = float(net)


def load_state(data):
    if not isinstance(data, dict):
        return False
    state.season = data.get("season", state.season)
    state.funds = data.get("funds", state.funds)
    saved_capacity = data.get("capacity")
    if isinstance(saved_capacity, dict):
        for category in CATEGORIES:
            if category in saved_capacity:
                state.capacity[category] = saved_capacity[category]
    state.acidity = data.get("acidity", state.acidity)
    saved_acidity_history = data.get("acidity_history")
    if isinstance(saved_acidity_history, list):
        state.acidity_history = copy.deepcopy(saved_acidity_history)
    state.sea_level = data.get("sea_level", state.sea_level)
    state.cumulative_damage = data.get("cumulative_damage", state.cumulative_damage)
    state.undampened_damage_total = data.get(
        "undampened_damage_total", state.undampened_damage_total
    )
    saved_damage_log = data.get("damage_log")
    if isinstance(saved_damage_log, list):
        state.damage_log = copy.deepcopy(saved_damage_log)
    saved_ticker_log = data.get("ticker_log")
    if isinstance(saved_ticker_log, list):
        state.ticker_log = copy.deepcopy(saved_ticker_log)
    state.trend_flattening_announced = data.get(
        "trend_flattening_announced", state.trend_flattening_announced
    )

    # Every field below predates a feature added after this game's initial
    # save-system integration -- a save from before any of them simply
    # lacks the key, so each falls back to whatever's already live (the
    # fresh-module default) rather than crashing on a missing key, same
    # discipline as every field above.
    saved_ticker_full_history = data.get("ticker_full_history")
    if isinstance(saved_ticker_full_history, list):
        state.ticker_full_history = copy.deepcopy(saved_ticker_full_history)
    state.hard_lag_mode = bool(data.get("hard_lag_mode", state.hard_lag_mode))
    _load_sister(data)
    saved_output_mix = data.get("output_mix")
    if saved_output_mix in OUTPUT_MIX:
        state.output_mix = saved_output_mix
    saved_fish_yield_history = data.get("fish_yield_history")
    if isinstance(saved_fish_yield_history, list):
        state.fish_yield_history = copy.deepcopy(saved_fish_yield_history)
    state.first_flood_announced = bool(
        data.get("first_flood_announced", state.first_flood_announced)
    )
    state.baseline_season = data.get("baseline_season", state.baseline_season)
    state.baseline_sea_level = data.get("baseline_sea_level", state.baseline_sea_level)
    state.baseline_damage = data.get("baseline_damage", state.baseline_damage)

    # Achievements' new tracked state -- belt-and-suspenders backfill
    # (same idea as SOL's visited_bodies) for a save predating these
    # fields: the restored acidity/funds/fish-yield values are themselves
    # valid lower/upper bounds on what the "ever" extremes must have been.
    state.min_fish_yield_ever = min(
        data.get("min_fish_yield_ever", state.min_fish_yield_ever),
        state.fish_yield_multiplier(),
    )
    state.max_acidity_ever = max(
        data.get("max_acidity_ever", state.max_acidity_ever), state.acidity
    )
    state.max_funds_ever = max(
        data.get("max_funds_ever", state.max_funds_ever), state.funds
    )
    state.fortified_in_time_earned = bool(
        data.get("fortified_in_time_earned", state.fortified_in_time_earned)
    )

    saved_tier_log = data.get("tier_log")
    if isinstance(saved_tier_log, list):
        state.tier_log = [
            t for t in saved_tier_log if isinstance(t, int) and 0 <= t < len(ADAPTATION_TIERS)
        ]
    state.hard_lag_note_seen = bool(data.get("hard_lag_note_seen", state.hard_lag_note_seen))
    state.fish_crash_open = bool(data.get("fish_crash_open", state.fish_crash_open))
    saved_recovery = data.get("recovery_celebrated_season", state.recovery_celebrated_season)
    state.recovery_celebrated_season = saved_recovery if isinstance(saved_recovery, int) else 0
    saved_scenario = data.get("sea_scenario")
    if saved_scenario in SEA_SCENARIOS:
        state.sea_scenario = saved_scenario

    saved_name = data.get("settlement_name")
    state.settlement_name = (
        " ".join(saved_name.split())[:SETTLEMENT_NAME_MAX] if isinstance(saved_name, str) else ""
    )
    saved_chronicle = data.get("chronicle")
    if isinstance(saved_chronicle, list):
        state.chronicle = [
            {"season": e["season"], "text": e["text"][:200]}
            for e in saved_chronicle
            if isinstance(e, dict)
            and isinstance(e.get("season"), int)
            and isinstance(e.get("text"), str)
        ][-CHRONICLE_LIMIT:]
    else:
        state.chronicle = []

    saved_heritage = data.get("heritage")
    state.heritage = {site["id"]: HERITAGE_UNPROTECTED for site in HERITAGE_SITES}
    if isinstance(saved_heritage, dict):
        for site in HERITAGE_SITES:
            if saved_heritage.get(site["id"]) in (HERITAGE_UNPROTECTED, HERITAGE_PROTECTED, HERITAGE_LOST):
                state.heritage[site["id"]] = saved_heritage[site["id"]]
    state.monitoring_reports = _clamped_int(
        data.get("monitoring_reports"), 0, len(CITIZEN_SCIENCE_FACTS)
    )
    state.monitoring_last_season = _clamped_int(data.get("monitoring_last_season"), 0, 10**6)
    state.storm_mode = bool(data.get("storm_mode", False))
    saved_storm_log = data.get("storm_log")
    state.storm_log = (
        [
            {k: float(e[k]) if k != "season" else int(e[k]) for k in ("season", "surge", "taken", "blocked")}
            for e in saved_storm_log
            if isinstance(e, dict)
            and all(isinstance(e.get(k), (int, float)) and not isinstance(e.get(k), bool) for k in ("season", "surge", "taken", "blocked"))
        ][-20:]
        if isinstance(saved_storm_log, list)
        else []
    )

    saved_retreat = data.get("retreat_rows")
    retreat_rows = []
    if isinstance(saved_retreat, list):
        for row in saved_retreat:
            if (
                isinstance(row, int)
                and not isinstance(row, bool)
                and 0 <= row < COASTLINE_ROWS
                and row not in retreat_rows
                and len(retreat_rows) < RETREAT_MAX_STEPS
            ):
                retreat_rows.append(row)
    state.retreat_rows = retreat_rows
    state.population = _clamped_int(data.get("population"), 0, 10**5) or POP_START
    state.peak_population = max(state.population, _clamped_int(data.get("peak_population"), 0, 10**5))
    state.displaced_total = _clamped_int(data.get("displaced_total"), 0, 10**7)
    state.relocated_total = _clamped_int(data.get("relocated_total"), 0, 10**7)
    saved_diversification = data.get("diversification")
    state.diversification = {
        kind: _clamped_int(
            saved_diversification.get(kind) if isinstance(saved_diversification, dict) else 0,
            0,
            DIVERSIFY_MAX_LEVEL,
        )
        for kind in DIVERSIFY_COST
    }
    saved_checkpoint = data.get("checkpoint")
    state.checkpoint = (
        copy.deepcopy(saved_checkpoint)
        if isinstance(saved_checkpoint, dict)
        and isinstance(saved_checkpoint.get("season"), int)
        and not isinstance(saved_checkpoint.get("season"), bool)
        and saved_checkpoint["season"] >= 1
        else None
    )
    saved_foresight = data.get("foresight")
    state.foresight = (
        [
            {
                "season": e["season"],
                "fish_yield": float(e["fish_yield"]),
                "damage": float(e["damage"]),
                "flooded": e["flooded"],
            }
            for e in saved_foresight
            if isinstance(e, dict)
            and isinstance(e.get("season"), int)
            and isinstance(e.get("flooded"), int)
            and all(isinstance(e.get(k), (int, float)) for k in ("fish_yield", "damage"))
        ][:CHECKPOINT_FORESIGHT_LIMIT]
        if isinstance(saved_foresight, list)
        else []
    )
    state.replay_count = _clamped_int(data.get("replay_count"), 0, 10**4)
    state.season_ledger = _load_ledger(data.get("season_ledger"))
    state.season_snapshots = _load_snapshots(data.get("season_snapshots"))

    # D8's flash-tracking global and the achievements toast-diffing
    # baseline both need to resync to the just-loaded state before
    # render() below draws anything or checks for newly-earned
    # achievements -- otherwise a loaded save could flash every already-
    # flooded row, or toast every already-earned achievement, as if they
    # had all just happened this instant.
    _resync_previous_flooded_rows()
    almanac_resync()
    global _previously_earned_ids
    _previously_earned_ids = _earned_snapshot()

    render()
    return True


def setup():
    for category in CATEGORIES:
        document.getElementById(f"{category}-invest-button").addEventListener(
            "click", create_proxy(_make_invest_handler(category))
        )
    document.getElementById("advance-season-button").addEventListener(
        "click", create_proxy(on_advance_season)
    )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    # D-15 / D-1 / D-18 / D-17: later additions, each tolerant of a missing node.
    for element_id, handler in (
        ("advance-x5-button", on_advance_x5),
        ("ledger-toggle-button", on_toggle_ledger),
        ("copy-text-button", on_copy_text),
    ):
        el = document.getElementById(element_id)
        if el is not None:
            el.addEventListener("click", create_proxy(handler))
    # 2026-10-08 pass: graph range/markers, scrubber, library, almanac, planner.
    for element_id, handler in (
        ("graph-markers-toggle", on_toggle_graph_markers),
        ("scrub-live-button", on_scrub_live),
        ("library-toggle-button", on_toggle_library),
        ("library-save-button", on_library_save),
        ("almanac-toggle-button", on_toggle_almanac),
        ("planner-toggle-button", on_toggle_planner),
        ("planner-clear-button", on_planner_clear),
        ("planner-commit-button", on_planner_commit),
    ):
        el = document.getElementById(element_id)
        if el is not None:
            el.addEventListener("click", create_proxy(handler))
    for key, _label in GRAPH_RANGES:
        el = document.getElementById(f"graph-range-{key}")
        if el is not None:
            el.addEventListener("click", create_proxy(_make_graph_range_handler(key)))
    for element_id, event_name, handler in (
        ("scrub-slider", "input", on_scrub_input),
        ("library-select-a", "change", _make_library_select_handler("library_a")),
        ("library-select-b", "change", _make_library_select_handler("library_b")),
        ("library-overlay-select", "change", _make_library_select_handler("library_overlay_id")),
        ("planner-length", "change", on_planner_length),
    ):
        el = document.getElementById(element_id)
        if el is not None:
            el.addEventListener(event_name, create_proxy(handler))
    for number in range(1, PLANNER_MAX_SEASONS + 1):
        for category in CATEGORIES:
            el = document.getElementById(f"planner-s{number}-{category}")
            if el is not None:
                el.addEventListener("input", create_proxy(_make_planner_input_handler(number, category)))
    for key in LEDGER_KEYS:
        el = document.getElementById(f"ledger-sort-{key}")
        if el is not None:
            el.addEventListener("click", create_proxy(_make_ledger_sort_handler(key)))
    for key, _label in TICKER_FILTERS:
        el = document.getElementById(f"ticker-filter-{key}")
        if el is not None:
            el.addEventListener("click", create_proxy(_make_ticker_filter_handler(key)))
    search_el = document.getElementById("ticker-search-input")
    if search_el is not None:
        search_el.addEventListener("input", create_proxy(on_ticker_search))
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("session-summary-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_session_summary)
    )
    output_mix_select = document.getElementById("output-mix-select")
    if output_mix_select is not None:
        output_mix_select.addEventListener("change", create_proxy(on_output_mix_change))
    scenario_select = document.getElementById("sea-scenario-select")
    if scenario_select is not None:
        scenario_select.addEventListener("change", create_proxy(on_sea_scenario_change))
    document.getElementById("sister-enable-button").addEventListener("click", create_proxy(on_enable_sister))
    document.getElementById("hard-lag-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_hard_lag)
    )
    for i, site in enumerate(HERITAGE_SITES):
        protect_button = document.getElementById(f"heritage-protect-{i}")
        if protect_button is not None:
            protect_button.addEventListener("click", create_proxy(_make_heritage_handler(site["id"])))
    for kind in DIVERSIFY_COST:
        el = document.getElementById(f"diversify-{kind}-button")
        if el is not None:
            el.addEventListener("click", create_proxy(_make_diversify_handler(kind)))
    for element_id, handler in (
        ("monitor-button", on_monitor),
        ("storm-toggle-button", on_toggle_storms),
        ("retreat-button", on_retreat),
        ("checkpoint-button", on_set_checkpoint),
        ("replay-button", on_replay),
    ):
        el = document.getElementById(element_id)
        if el is not None:
            el.addEventListener("click", create_proxy(handler))
    name_input = document.getElementById("settlement-name-input")
    if name_input is not None:
        name_input.addEventListener("change", create_proxy(on_settlement_name_change))
    document.getElementById("set-baseline-button").addEventListener(
        "click", create_proxy(on_set_baseline)
    )
    # Explicit, not just relying on index.html's `hidden` attribute -- the
    # toast/banner elements are only otherwise touched by their own show/
    # hide logic (unlike every *panel*, which gets its `hidden` state
    # re-set on every render()), so they need their own starting state
    # set here rather than trusting markup alone.
    toast = document.getElementById("achievement-toast")
    if toast is not None:
        toast.hidden = True
    _resync_previous_flooded_rows()
    almanac_resync()
    render()


_load_graph_prefs()
almanac = _load_almanac()
setup()
