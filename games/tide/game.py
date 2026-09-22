"""Tide — Ocean Acidification & Sea-Level Rise Game.

Runs in-browser via Pyodide. Milestone 1: the core settlement loop —
seasonal rounds, funds, and three investment categories (output/
reduction/adaptation), mirroring Grid's build-capacity pattern. Acidity,
sea-level rise, and the tile-grid coastline land in later milestones.
"""

import copy
import json
import math

import info_page
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
CHECKPOINT_DROP_KEYS = ("ticker_full_history", "achievements_earned")

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

        self._update_heritage()
        self._update_population()
        if self.storm_this_season():
            self._resolve_storm()

        self.season += 1

        new_fish_yield = self.fish_yield_multiplier()
        self.fish_yield_history.append(new_fish_yield)
        self.min_fish_yield_ever = min(self.min_fish_yield_ever, new_fish_yield)

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
    grid_el.innerHTML = ""
    tier_index = state.current_tier_index()
    current_flooded_rows = set()
    tidal_rows = state.tidal_rows()
    for row_index, row in enumerate(coastline_grid(state.sea_level)):
        tile_state = row[0]  # every column in a row shares the same state
        threshold = row_flood_threshold(row_index)
        # D1: a row given up by managed retreat is drawn flooded, with its
        # own class (diagonal hatch in CSS) so it reads as chosen.
        retreated = row_index in state.retreat_rows
        if retreated:
            tile_state = FLOODED
        if tile_state == FLOODED:
            current_flooded_rows.add(row_index)
        # D8: flash any row flooding for the first time this render --
        # compared against last render's snapshot, not against "flooded
        # right now", so the flash fires exactly once, at the moment of
        # crossing, not on every subsequent re-render while still flooded.
        just_flooded = tile_state == FLOODED and row_index not in _previous_flooded_rows
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
                status = state.heritage.get(site["id"])
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
            base_title = (
                "Managed retreat — this row was cleared on purpose and its people rehoused inland."
                if retreated
                else f"Flooded — this row floods once sea level reaches {threshold:.0f}."
                if tile_state == FLOODED
                else f"Floods once sea level reaches {threshold:.0f} "
                f"(about {state.seasons_until_flood(row_index)} season(s) at the current pace)."
                + (" This season's tide is washing over it." if tidal else "")
            )
            tile.title = (heritage_status_text(site) + " " if site is not None else "") + base_title
            grid_el.appendChild(tile)
    _previous_flooded_rows = current_flooded_rows


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


def then_vs_now_sparkline_svg():
    """D14: tiny per-season damage sparkline since the baseline; "" until
    there are two points to draw a line between."""
    series = state.then_vs_now_damage_series()
    if len(series) < 2:
        return ""
    top = max(max(series), 1e-9)
    points = _sparkline_points(series, top)
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" '
        f'class="acidity-fish-sparkline" role="img" '
        f'aria-label="Damage per season since the baseline">'
        f'<polyline points="{points}" fill="none" stroke="#d8c088" stroke-width="2" />'
        f"</svg>"
    )


def _sparkline_points(series, max_value):
    """Maps a list of values onto SVG viewport coordinates -- x spread
    evenly left-to-right, y scaled so 0 sits on the baseline and
    `max_value` sits at the top. An empty series returns "" rather than
    dividing by zero."""
    if not series:
        return ""
    denominator = max(max_value, 1e-9)
    step = SPARKLINE_WIDTH / max(1, len(series) - 1)
    points = []
    for i, value in enumerate(series):
        x = i * step
        y = SPARKLINE_HEIGHT - (value / denominator) * SPARKLINE_HEIGHT
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def acidity_fish_history_svg():
    """Returns "" once there's no history yet -- render() shows a plain
    "not enough data" message instead in that case. Acidity is charted as
    a fraction of FISH_DAMAGE_SCALE (its own natural ceiling) and fish
    yield as a fraction of 1.0 (already 0..1), so both lines share one
    0..1 vertical scale despite being different units."""
    if not state.acidity_history:
        return ""
    acidity_fractions = [min(1.0, a / FISH_DAMAGE_SCALE) for a in state.acidity_history]
    fish_points = _sparkline_points(state.fish_yield_history, 1.0)
    acidity_points = _sparkline_points(acidity_fractions, 1.0)
    # D10: dashed reference line at the session-average acidity, like
    # Thaw's melt-threshold gridline.
    average = sum(acidity_fractions) / len(acidity_fractions)
    average_y = SPARKLINE_HEIGHT - average * SPARKLINE_HEIGHT
    reference = (
        f'<line x1="0" y1="{average_y:.1f}" x2="{SPARKLINE_WIDTH}" y2="{average_y:.1f}" '
        f'stroke="{SPARKLINE_ACIDITY_COLOR}" stroke-width="1" stroke-dasharray="4 3" '
        f'opacity="0.6"><title>Average acidity this session</title></line>'
    )
    # D18: a marker at the season the comparison baseline was set.
    marker = ""
    if state.baseline_season > 1 and len(state.acidity_history) > 1:
        step = SPARKLINE_WIDTH / max(1, len(state.acidity_history) - 1)
        marker_x = min(SPARKLINE_WIDTH, (state.baseline_season - 1) * step)
        marker = (
            f'<line x1="{marker_x:.1f}" y1="0" x2="{marker_x:.1f}" y2="{SPARKLINE_HEIGHT}" '
            f'stroke="#d8c088" stroke-width="1" stroke-dasharray="2 2">'
            f'<title>Baseline set here (Season {state.baseline_season})</title></line>'
        )
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" '
        f'class="acidity-fish-sparkline" role="img" '
        f'aria-label="Ocean acidity and fishing yield over the session">'
        f"{reference}{marker}"
        f'<polyline points="{acidity_points}" fill="none" '
        f'stroke="{SPARKLINE_ACIDITY_COLOR}" stroke-width="2" />'
        f'<polyline points="{fish_points}" fill="none" '
        f'stroke="{SPARKLINE_FISH_COLOR}" stroke-width="2" />'
        f"</svg>"
    )


def delayed_consequence_svg():
    """D7: acidity (purple) plotted at the season it was banked, against
    the fish yield it will cause (green, dashed) plotted `lag` seasons
    later -- the horizontal gap between the two lines is the lag. "" with
    no history yet."""
    rows = state.delayed_consequence_rows()
    if not rows:
        return ""
    lag = state._effective_fish_lag()
    total_seasons = len(rows) + lag
    step = SPARKLINE_WIDTH / max(1, total_seasons - 1)
    acidity_pts = " ".join(
        f"{(season - 1) * step:.1f},{SPARKLINE_HEIGHT - fraction * SPARKLINE_HEIGHT:.1f}"
        for season, fraction, _arrival, _yield in rows
    )
    fish_pts = " ".join(
        f"{(arrival - 1) * step:.1f},{SPARKLINE_HEIGHT - projected * SPARKLINE_HEIGHT:.1f}"
        for _season, _fraction, arrival, projected in rows
    )
    now_x = (state.season - 1) * step
    now_line = (
        f'<line x1="{now_x:.1f}" y1="0" x2="{now_x:.1f}" y2="{SPARKLINE_HEIGHT}" '
        f'stroke="#d8c088" stroke-width="1" stroke-dasharray="2 2">'
        f"<title>Now (Season {state.season}): everything right of here has not happened yet</title></line>"
    )
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" '
        f'class="acidity-fish-sparkline" role="img" '
        f'aria-label="Acidity banked each season and the fish yield it causes {lag} seasons later">'
        f"{now_line}"
        f'<polyline points="{acidity_pts}" fill="none" '
        f'stroke="{SPARKLINE_ACIDITY_COLOR}" stroke-width="2" />'
        f'<polyline points="{fish_pts}" fill="none" stroke="{SPARKLINE_FISH_COLOR}" '
        f'stroke-width="2" stroke-dasharray="5 3" />'
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
        text_el.innerText = state.session_summary_text()


def render_fish_warning_banner():
    """D14: an early-warning banner for a fish-yield crash already locked
    in by acidity that's already in the pipeline -- distinct from the
    ticker's after-the-fact narration, this fires *before* the drop
    lands, using next_season_fish_yield_preview()."""
    banner = document.getElementById("fish-warning-banner")
    if banner is None:
        return
    preview = state.next_season_fish_yield_preview()
    current = state.fish_yield_multiplier()
    if preview is not None and preview < current - 1e-6 and preview <= FISH_YIELD_WARNING_THRESHOLD:
        banner.hidden = False
        banner.innerText = (
            f"⚠️ Heads up: fishing yield is on track to fall to about {preview * 100:.0f}% "
            f"next season — acidity already recorded is catching up. "
            "Suggested action: invest in Acidity Reduction now, and expect the dip to last a few seasons."
        )
    else:
        banner.hidden = True


def render_ticker_history():
    """D5: the full, uncapped-within-TICKER_FULL_HISTORY_LIMIT ticker log
    behind an expandable panel, alongside (not instead of) the short live
    ticker rendered separately above."""
    history_el = document.getElementById("ticker-history-list")
    if history_el is None:
        return
    if state.ticker_full_history:
        history_el.innerHTML = "<br>".join(state.ticker_full_history)
    else:
        history_el.innerHTML = "No notable changes yet."


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


def render():
    render_info_page()
    document.getElementById("season-display").innerText = f"Season {state.season}"
    document.getElementById("funds-display").innerText = f"Funds: {state.funds:.0f}"
    document.getElementById("acidity-display").innerText = f"Ocean acidity: {state.acidity:.1f}"
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

    then_vs_now_graph = document.getElementById("then-vs-now-graph")
    if then_vs_now_graph is not None:
        then_vs_now_graph.innerHTML = then_vs_now_sparkline_svg()

    # D6: "what if you'd invested earlier" counterfactual replay.
    counterfactual_el = document.getElementById("counterfactual-display")
    if counterfactual_el is not None:
        counterfactual_el.innerText = state.counterfactual_message()

    # D13: cross-session personal-best coastline-damage-saved record.
    _maybe_update_best_coastline_saved()
    render_best_coastline_saved()

    # D15: acidity-vs-fish-yield mini-graph.
    graph_container = document.getElementById("acidity-fish-graph")
    if graph_container is not None:
        svg = acidity_fish_history_svg()
        if svg:
            graph_container.innerHTML = svg
        else:
            graph_container.innerHTML = ""
            graph_container.innerText = "Not enough seasons yet to chart a trend."

    # D7: today's acidity choices vs. the fish yield they cause later.
    consequence_graph = document.getElementById("delayed-consequence-graph")
    if consequence_graph is not None:
        consequence_graph.innerHTML = delayed_consequence_svg()
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
    _sync_earned_and_toast()


def _make_invest_handler(category):
    def handler(event=None):
        state.invest(category)
        render()
    return handler


def on_advance_season(event=None):
    state.advance_season()
    render()


def on_output_mix_change(event):
    """D16: reads the <select>'s chosen value the same way Canopy's own
    on_grid_size_change() reads event.target.value from a real DOM change
    event; an unrecognized value is a silent no-op via set_output_mix()."""
    state.set_output_mix(event.target.value)
    render()


def on_sea_scenario_change(event):
    state.set_sea_scenario(event.target.value)
    render()


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
    load_state(snapshot)
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

    # D8's flash-tracking global and the achievements toast-diffing
    # baseline both need to resync to the just-loaded state before
    # render() below draws anything or checks for newly-earned
    # achievements -- otherwise a loaded save could flash every already-
    # flooded row, or toast every already-earned achievement, as if they
    # had all just happened this instant.
    _resync_previous_flooded_rows()
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
    render()


setup()
