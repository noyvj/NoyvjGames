"""Tide — Ocean Acidification & Sea-Level Rise Game.

Runs in-browser via Pyodide. Milestone 1: the core settlement loop —
seasonal rounds, funds, and three investment categories (output/
reduction/adaptation), mirroring Grid's build-capacity pattern. Acidity,
sea-level rise, and the tile-grid coastline land in later milestones.
"""

from js import document
from pyodide.ffi import create_proxy

STARTING_FUNDS = 300

CATEGORIES = ["output", "reduction", "adaptation"]

CATEGORY_LABEL = {
    "output": "Output",
    "reduction": "Acidity Reduction",
    "adaptation": "Adaptation",
}

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
DAMPENING_PER_ADAPTATION_UNIT = 0.08
MAX_DAMPENING = 0.9

# Coastline tile grid: row 0 is the top of the grid (highest ground, high
# threshold, floods last); the bottom row is the lowest ground and floods
# first — water rises visually from the bottom, matching a real coastline.
COASTLINE_ROWS = 6
COASTLINE_COLS = 8
ROW_FLOOD_STEP = 15.0

LAND = "land"
FLOODED = "flooded"


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

    def invest(self, category):
        cost = INVEST_COST[category]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.capacity[category] += 1
        return True

    def fish_yield_multiplier(self):
        """1.0 (full yield) until enough seasons have passed for the lag
        to "arrive" — then reflects acidity from FISH_LAG_SEASONS ago."""
        if len(self.acidity_history) < FISH_LAG_SEASONS:
            return 1.0
        lagged_acidity = self.acidity_history[-FISH_LAG_SEASONS]
        return max(MIN_FISH_MULTIPLIER, 1 - lagged_acidity / FISH_DAMAGE_SCALE)

    def dampening_fraction(self):
        return min(MAX_DAMPENING, self.capacity["adaptation"] * DAMPENING_PER_ADAPTATION_UNIT)

    def advance_season(self):
        income = self.capacity["output"] * OUTPUT_INCOME_PER_UNIT * self.fish_yield_multiplier()
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


def render_coastline():
    grid_el = document.getElementById("coastline-grid")
    grid_el.innerHTML = ""
    for row_index, row in enumerate(coastline_grid(state.sea_level)):
        for col_index, tile_state in enumerate(row):
            tile = document.createElement("div")
            tile.id = f"coastline-tile-{row_index}-{col_index}"
            tile.className = f"coastline-tile coastline-{tile_state}"
            grid_el.appendChild(tile)


def render():
    document.getElementById("season-display").innerText = f"Season {state.season}"
    document.getElementById("funds-display").innerText = f"Funds: {state.funds:.0f}"
    document.getElementById("acidity-display").innerText = f"Ocean acidity: {state.acidity:.1f}"
    document.getElementById("fish-yield-display").innerText = (
        f"Fishing yield: {state.fish_yield_multiplier() * 100:.0f}%"
    )
    document.getElementById("sea-level-display").innerText = f"Sea level: {state.sea_level:.0f}"
    document.getElementById("damage-display").innerText = (
        f"Cumulative damage: {state.cumulative_damage:.0f}"
    )
    document.getElementById("damage-saved-display").innerText = damage_saved_message(state.damage_saved())
    document.getElementById("damage-trend-display").innerText = damage_trend_message(state.damage_trend())
    render_coastline()

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


def setup():
    for category in CATEGORIES:
        document.getElementById(f"{category}-invest-button").addEventListener(
            "click", create_proxy(_make_invest_handler(category))
        )
    document.getElementById("advance-season-button").addEventListener(
        "click", create_proxy(on_advance_season)
    )
    render()


setup()
