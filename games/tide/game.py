"""Tide — Ocean Acidification & Sea-Level Rise Game.

Runs in-browser via Pyodide. Milestone 1: the core settlement loop —
seasonal rounds, funds, and three investment categories (output/
reduction/adaptation), mirroring Grid's build-capacity pattern. Acidity,
sea-level rise, and the tile-grid coastline land in later milestones.
"""

import copy

from js import document
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
ACIDITY_RISE_PER_OUTPUT = 2.0
ACIDITY_FALL_PER_REDUCTION = 1.5

# Delayed consequence: this season's fishing yield depends on acidity
# from FISH_LAG_SEASONS ago, not today's number — the whole point being
# that damage from today's choices doesn't show up right away.
FISH_LAG_SEASONS = 3
FISH_DAMAGE_SCALE = 50.0
MIN_FISH_MULTIPLIER = 0.2

# Sea level rises every season no matter what the player does — adaptation
# infrastructure never stops or slows the rise itself, only how much
# economic damage that rise translates into. Capped so it can never fully
# neutralize the threat outright.
SEA_LEVEL_RISE_PER_SEASON = 5.0
MAX_DAMPENING = 0.9

# Iteration Pass 2 — adaptation tech tree: dampening no longer scales
# continuously with adaptation capacity. Instead, sustained investment
# (cumulative capacity — it never decays, so "sustained" just means
# "keep investing") crosses thresholds that unlock discrete, stronger
# tiers, each with its own visible coastline signature. Ordered
# ascending by threshold; the top tier's dampening matches the old
# MAX_DAMPENING cap so the ceiling behavior is unchanged.
ADAPTATION_TIERS = [
    {"threshold": 0, "name": "No adaptation", "dampening": 0.0},
    {"threshold": 3, "name": "Sandbag berms", "dampening": 0.3},
    {"threshold": 6, "name": "Seawalls", "dampening": 0.6},
    {"threshold": 10, "name": "Reinforced seawalls", "dampening": MAX_DAMPENING},
]

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
        return True

    def fish_yield_multiplier(self):
        """1.0 (full yield) until enough seasons have passed for the lag
        to "arrive" — then reflects acidity from FISH_LAG_SEASONS ago."""
        if len(self.acidity_history) < FISH_LAG_SEASONS:
            return 1.0
        lagged_acidity = self.acidity_history[-FISH_LAG_SEASONS]
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
        return self.current_tier()["dampening"]

    def next_tier_progress_text(self):
        tier_index = self.current_tier_index()
        if tier_index == len(ADAPTATION_TIERS) - 1:
            return "Reinforced seawalls — maximum adaptation tier reached."
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

    def _record_ticker_message(self, acidity_change, old_fish_yield, new_fish_yield):
        """Delayed-effect ticker: narrates the lag as it builds and
        lands, so cause stays traceable in hindsight without spelling
        out the mechanic outright. Iteration-pass addition."""
        message = None
        if new_fish_yield < old_fish_yield - 1e-6:
            message = (
                f"Fish stocks quietly declining — acidity from {FISH_LAG_SEASONS} "
                f"seasons ago is catching up."
            )
        elif new_fish_yield > old_fish_yield + 1e-6:
            message = "Fish stocks recovering as past acidity spikes fade from the lag window."
        elif acidity_change > 0 and len(self.acidity_history) <= FISH_LAG_SEASONS:
            message = "Acidity is rising — the effect on fish stocks won't show for a few more seasons."

        if message:
            self.ticker_log.append(message)
            self.ticker_log = self.ticker_log[-TICKER_LOG_LIMIT:]

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
        self.ticker_log.append(message)
        self.ticker_log = self.ticker_log[-TICKER_LOG_LIMIT:]

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
            self.ticker_log.append(message)
            self.ticker_log = self.ticker_log[-TICKER_LOG_LIMIT:]

    def advance_season(self):
        old_fish_yield = self.fish_yield_multiplier()
        income = self.capacity["output"] * OUTPUT_INCOME_PER_UNIT * old_fish_yield
        self.funds += income

        acidity_change = (
            self.capacity["output"] * ACIDITY_RISE_PER_OUTPUT
            - self.capacity["reduction"] * ACIDITY_FALL_PER_REDUCTION
        )
        self.acidity = max(0.0, self.acidity + acidity_change)
        self.acidity_history.append(self.acidity)

        self.sea_level += SEA_LEVEL_RISE_PER_SEASON
        damage_this_season = SEA_LEVEL_RISE_PER_SEASON * (1 - self.dampening_fraction())
        self.cumulative_damage += damage_this_season
        self.undampened_damage_total += SEA_LEVEL_RISE_PER_SEASON
        self.damage_log.append(damage_this_season)

        self.season += 1

        new_fish_yield = self.fish_yield_multiplier()
        self._record_ticker_message(acidity_change, old_fish_yield, new_fish_yield)
        self._record_trend_message()

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


def render_coastline():
    grid_el = document.getElementById("coastline-grid")
    grid_el.innerHTML = ""
    tier_index = state.current_tier_index()
    for row_index, row in enumerate(coastline_grid(state.sea_level)):
        for col_index, tile_state in enumerate(row):
            tile = document.createElement("div")
            tile.id = f"coastline-tile-{row_index}-{col_index}"
            tile.className = f"coastline-tile coastline-{tile_state}"
            if _is_seawall_row(row_index, tier_index):
                tile.className += " coastline-seawall"
            grid_el.appendChild(tile)


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
    a direct visual, not just the damage_saved() number."""
    _render_mini_coastline("coastline-before-grid", 0.0, tier_index=0)
    _render_mini_coastline("coastline-now-grid", state.sea_level, tier_index=state.current_tier_index())
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


# REVIEW(reuse): render_info_page()/on_toggle_info_page() (~25+4 lines) are\n# logically identical across all 8 climate games (canopy, grid, tide,\n# aftermath, herd, thaw, loop, drift) -- only the per-game INFO_PAGE data\n# dict differs. Matching HTML/CSS (.info-page-* rules, #info-page-panel\n# markup) is duplicated the same way. A shared JS-driven widget or small\n# shared Python helper, driven by each game's own INFO_PAGE dict -- the same\n# pattern already used for shared/save-widget.js -- would remove ~250 lines\n# of duplication.
def render_info_page():
    panel = document.getElementById("info-page-panel")
    panel.hidden = not info_page_open
    toggle_button = document.getElementById("info-page-toggle-button")
    toggle_button.innerText = "Hide The Real Story" if info_page_open else "The Real Story"
    if not info_page_open:
        return
    document.getElementById("info-page-framing").innerText = INFO_PAGE["framing"]
    document.getElementById("info-page-tie-in").innerText = INFO_PAGE["mechanic_tie_in"]
    list_el = document.getElementById("info-page-sources")
    list_el.innerHTML = ""
    for source in INFO_PAGE["sources"]:
        item = document.createElement("li")
        item.className = "info-page-source"
        link = document.createElement("a")
        link.href = source["url"]
        link.target = "_blank"
        link.rel = "noopener noreferrer"
        link.innerText = source["label"]
        item.appendChild(link)
        note = document.createElement("p")
        note.className = "info-page-source-note"
        note.innerText = source["note"]
        item.appendChild(note)
        list_el.appendChild(item)


def on_toggle_info_page(event=None):
    global info_page_open
    info_page_open = not info_page_open
    render()


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
    render_coastline()
    render_coastline_comparison()

    sea_level_bar = document.getElementById("sea-level-bar")
    sea_level_bar.style.width = f"{state.sea_level_fraction() * 100:.0f}%"

    ticker_el = document.getElementById("ticker-log")
    if state.ticker_log:
        ticker_el.innerHTML = "<br>".join(state.ticker_log)
    else:
        ticker_el.innerHTML = "No notable changes yet."

    for category in CATEGORIES:
        document.getElementById(f"{category}-count").innerText = str(state.capacity[category])
        invest_button = document.getElementById(f"{category}-invest-button")
        invest_button.innerText = f"Invest ({INVEST_COST[category]})"
        invest_button.disabled = state.funds < INVEST_COST[category]


def _make_invest_handler(category):
    def handler(event=None):
        state.invest(category)
        render()
    return handler


def on_advance_season(event=None):
    state.advance_season()
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
    render()


setup()
