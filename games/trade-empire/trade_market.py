"""Prices and demand: market multipliers, trends, seasons, diplomacy, route hazards and insurance, the run seed and its random streams, selling, the stockpile, price recovery."""

import seed as seed_lib

import trade_runstate as runstate
from trade_charter import AUTO_BALANCERS_RECOVERY_MULTIPLIER, HARD_CHARTER_SATURATION_MULTIPLIER, charter_perk
from trade_colony import active_colony_ids, colony_producing
from trade_effects import cartel_multiplier, meridian_multiplier, weather_multiplier
from trade_research import MARKET_INSIGHT_2_DECAY_MULTIPLIER, MARKET_INSIGHT_RECOVERY_MULTIPLIER
from trade_rules import (
    AEROGEL, ALL_COLONIES, ANTIMATTER, BIOMASS, CRYSTAL, ENERGY, GRAIN, ISOTOPES, MACHINERY, NEUTRONIUM,
    ORE, POLYMER, RARE_METALS, SELL_PRICE, SUPERFLUID, WATER,
)


# Milestone 4 — market economics: each good has a price multiplier that
# drops when it's sold and recovers gradually over time. Overproducing
# a single good (running the same route on repeat) craters its price;
# diversifying across the triangle keeps prices near baseline. Floored
# so a good never becomes worthless, and capped at baseline — no
# scarcity premium in v1.
MARKET_PRICE_DECAY_PER_UNIT_SOLD = 0.01
MARKET_PRICE_RECOVERY_PER_TICK = 0.01
MIN_PRICE_MULTIPLIER = 0.3
MAX_PRICE_MULTIPLIER = 1.0

market_multiplier = {
    ORE: 1.0, GRAIN: 1.0, MACHINERY: 1.0, WATER: 1.0, ENERGY: 1.0,
    RARE_METALS: 1.0, BIOMASS: 1.0, ISOTOPES: 1.0,
    CRYSTAL: 1.0, POLYMER: 1.0, ANTIMATTER: 1.0,
    NEUTRONIUM: 1.0, SUPERFLUID: 1.0, AEROGEL: 1.0,
}

# J11 — per-route profitability. Every good in the galaxy is produced by
# exactly one colony and needed by exactly one other (colony_producing()/
# colony_needing() are both single-valued), so a good's cumulative sale
# profit *is* that route's cumulative profit -- no separate route-keyed
# structure needed on top of the good-keyed one.
good_profit_recent = {}  # J2 — good -> last few sale profits, for the trend arrow
good_profit_total = {good: 0 for good in market_multiplier}
# V-E-8 (J11): completed sales per good, so each route line can show average profit per trip
good_trip_count = {good: 0 for good in market_multiplier}

# J12/J14 — a short rolling trend history (market price per good, need
# satisfaction per colony), just long enough for a small inline
# sparkline to read as a real shape. Same "unlabeled inline-SVG
# polyline" technique Herd's own trend graph uses.
TREND_HISTORY_MAX_POINTS = 30
price_history = {good: [] for good in market_multiplier}
need_history = {}


# J29 -- opt-in seasonal demand. Every SEASON_LENGTH_TICKS the "in demand"
# pair of goods rotates through the goods the player can reach; a good in
# demand sells for SEASONAL_DEMAND_BONUS more. Purely a bonus (nothing is
# ever marked down), fully predictable (the status line always names the
# current and next pair), and off by default so the base economy is
# unchanged. season_ticks only advances while the mode is on.
SEASON_LENGTH_TICKS = 30
SEASONAL_DEMAND_BONUS = 0.25
SEASONAL_HOT_GOOD_COUNT = 2


# J23 -- diplomatic relations between star systems. Every unit delivered on
# a trip that crosses systems (home / Kepler / Rift / Umbral Deep) counts toward a
# relations level; each level is a small permanent bonus on the proceeds of
# every sale. Purely a bonus, and it can only matter once the player has
# reached a second system, so the base game is untouched.
DIPLOMACY_THRESHOLDS = (25, 75, 150)
DIPLOMACY_BONUS_PER_LEVEL = 0.05


def diplomacy_level():
    return sum(1 for threshold in DIPLOMACY_THRESHOLDS if runstate.cross_system_units >= threshold)


def diplomacy_multiplier():
    return 1.0 + diplomacy_level() * DIPLOMACY_BONUS_PER_LEVEL


def diplomacy_units_to_next_level():
    for threshold in DIPLOMACY_THRESHOLDS:
        if runstate.cross_system_units < threshold:
            return threshold - runstate.cross_system_units
    return 0


# J11 -- opt-in route hazards and insurance. With hazards on, each loaded
# arrival has a ROUTE_HAZARD_CHANCE of being disrupted (cargo lost, nothing
# sold or delivered). Insurance costs INSURANCE_PREMIUM_PER_TICK for every
# ship in transit and refunds INSURANCE_COVERAGE of the lost trip's
# proceeds, so it is a variance-versus-cost decision, roughly break-even.
# Both are off by default: the base economy carries no hazard.
ROUTE_HAZARD_CHANCE = 0.08
INSURANCE_COVERAGE = 0.75
INSURANCE_PREMIUM_PER_TICK = 1

hazard_rng = None  # None = the run seed's "hazard" stream; a test may set any object with .random()

# Seeded runs (Z-1b, the shared shared/seed.py reused read-only). One short run seed such as
# TRADEEMPIRE-K7F2Q drives the three random systems: route hazards, Trade Guild offers and the
# founding conditions of a renewed charter. Every draw comes from a STATELESS stream named by
# (seed, purpose, counter), so the same seed and the same choices give the same hazards, contracts
# and founding conditions, and a saved game resumes exactly where it was. The seed is a run-level
# key, written to a save only once it has been used or typed (a brand-new save is unchanged), and a
# charter renewal keeps it. Old saves without one simply get a fresh seed when they load.
SEED_GAME = "trade-empire"


def new_run_seed():
    return seed_lib.new_seed(SEED_GAME)


def current_run_seed():
    if not runstate.run_seed:
        runstate.run_seed = new_run_seed()
    return runstate.run_seed


def run_stream(label, n):
    """The deterministic generator for one purpose and one position in the run."""
    return seed_lib.Rng(f"{current_run_seed()}#{label}#{n}")


def run_seed_draws():
    """How many seeded draws this run has already made."""
    return runstate.hazard_rolls + runstate.guild_offers + runstate.charters_completed + (1 if runstate.founding_seed else 0)


def run_seed_changeable():
    """A typed seed is accepted only before the run has used its seed (and not in the practice sandbox)."""
    return not runstate.sandbox_active and run_seed_draws() == 0


def set_run_seed(text):
    """Start from a typed seed. Returns (ok, message)."""
    result = seed_lib.validate(text, SEED_GAME)
    if not result["ok"]:
        return False, result["message"]
    if not run_seed_changeable():
        return False, "The seed can only be changed before a hazard, a guild offer or a new charter has used it."
    runstate.run_seed = result["seed"]
    runstate.run_seed_pinned = True
    return True, f"Seed {runstate.run_seed} set."


def hazard_roll():
    """One route-hazard roll in [0, 1): the override when a test set one, else the run's hazard stream."""
    n = runstate.hazard_rolls
    runstate.hazard_rolls += 1
    if hazard_rng is not None:
        return hazard_rng.random()
    return run_stream("hazard", n).random()


def seasonal_reachable_goods():
    reachable = set(active_colony_ids())
    return [g for g in SELL_PRICE if colony_producing(g) in reachable]


def seasonal_hot_goods(season_index):
    goods = seasonal_reachable_goods()
    if not goods:
        return []
    count = min(SEASONAL_HOT_GOOD_COUNT, len(goods))
    start = (season_index * SEASONAL_HOT_GOOD_COUNT) % len(goods)
    return [goods[(start + offset) % len(goods)] for offset in range(count)]


def seasonal_status():
    """(season number, ticks left, hot goods now, hot goods next season)."""
    index = runstate.season_ticks // SEASON_LENGTH_TICKS
    left = SEASON_LENGTH_TICKS - (runstate.season_ticks % SEASON_LENGTH_TICKS)
    return index + 1, left, seasonal_hot_goods(index), seasonal_hot_goods(index + 1)


def seasonal_multiplier(good):
    if not runstate.seasonal_demand_enabled:
        return 1.0
    hot = seasonal_hot_goods(runstate.season_ticks // SEASON_LENGTH_TICKS)
    return 1.0 + SEASONAL_DEMAND_BONUS if good in hot else 1.0


def current_sell_price(good):
    return max(1, round(SELL_PRICE[good] * market_multiplier[good] * seasonal_multiplier(good) * weather_multiplier(good)
               * meridian_multiplier(good) * cartel_multiplier(good)))


def apply_market_sale(good, qty):
    decay = MARKET_PRICE_DECAY_PER_UNIT_SOLD * (
        MARKET_INSIGHT_2_DECAY_MULTIPLIER if "market_insight_2" in runstate.unlocked_research else 1.0
    ) * (HARD_CHARTER_SATURATION_MULTIPLIER if runstate.hard_charter_active else 1.0)
    market_multiplier[good] = max(MIN_PRICE_MULTIPLIER, market_multiplier[good] - qty * decay)
    if market_multiplier[good] < MARKET_CRASH_THRESHOLD:
        market_crash_ever[good] = True


# J9 -- market speculation: a small warehouse per good. Buy a lot while a
# price is crashed, hold it, and sell once the price has recovered. Buying
# pushes the price up and selling pushes it down (the same per-unit impact
# a ship's sale has), capacity is small, and selling pays a fee, so it is a
# timing decision with real risk, not a money loop. Stockpile sales are not
# counted as trade sales (no achievements or route stats).
STOCKPILE_CAPACITY = 15
STOCKPILE_LOT = 5
STOCKPILE_SELL_FEE = 0.10
stockpile = {good: 0 for good in SELL_PRICE}
# J-4 -- the "price memory" ghost line: where each good's price multiplier was
# just before the player's last stockpile buy or sell, drawn dashed (and named
# in text) on its sparkline. Only the player's own market moves set it.
price_memory = {}


def can_stockpile_buy(good):
    if good not in stockpile or colony_producing(good) not in active_colony_ids():
        return False
    if stockpile[good] >= stockpile_capacity(good):
        return False
    qty = min(STOCKPILE_LOT, stockpile_capacity(good) - stockpile[good])
    return runstate.total_profit >= qty * current_sell_price(good)


def buy_stockpile(good):
    if not can_stockpile_buy(good):
        return False
    qty = min(STOCKPILE_LOT, stockpile_capacity(good) - stockpile[good])
    price_memory[good] = market_multiplier[good]
    runstate.total_profit -= qty * current_sell_price(good)
    stockpile[good] += qty
    market_multiplier[good] = min(
        MAX_PRICE_MULTIPLIER, market_multiplier[good] + qty * MARKET_PRICE_DECAY_PER_UNIT_SOLD
    )
    return True


def stockpile_sale_value(good):
    return int(round(stockpile.get(good, 0) * current_sell_price(good) * (1 - STOCKPILE_SELL_FEE)))


def sell_stockpile(good):
    if stockpile.get(good, 0) <= 0 or colony_producing(good) not in active_colony_ids():
        return False
    qty = stockpile[good]
    price_memory[good] = market_multiplier[good]
    runstate.total_profit += stockpile_sale_value(good)
    stockpile[good] = 0
    apply_market_sale(good, qty)
    return True


def recover_market():
    for good in market_multiplier:
        recovery = MARKET_PRICE_RECOVERY_PER_TICK * (
            MARKET_INSIGHT_RECOVERY_MULTIPLIER if "market_insight" in runstate.unlocked_research else 1.0
        ) * (AUTO_BALANCERS_RECOVERY_MULTIPLIER if charter_perk("auto_balancers") else 1.0)
        market_multiplier[good] = min(MAX_PRICE_MULTIPLIER, market_multiplier[good] + recovery)


# Per-good watermark: True once that good's price has crashed below
# MARKET_CRASH_THRESHOLD at least once this session -- market_recovery
# checks for a good that's both crashed at some point and currently back
# above MARKET_RECOVERY_THRESHOLD.
market_crash_ever = {good: False for good in market_multiplier}
MARKET_CRASH_THRESHOLD = 0.4

HUB_STOCKPILE_CAP = 8


def stockpile_capacity(good):
    """15 units, or HUB_STOCKPILE_CAP for the good made at the Distribution Hub."""
    if runstate.hub_colony is not None and ALL_COLONIES[runstate.hub_colony]["produces"] == good:
        return HUB_STOCKPILE_CAP
    return STOCKPILE_CAPACITY
