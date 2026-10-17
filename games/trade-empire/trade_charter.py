"""The charter perk tree (O-1): perk and branch tables, the lifetime ledger, crest tiers, and the getters that turn a perk into a number (costs, decay, founding conditions)."""

import random

import trade_runstate as runstate
from trade_records import records
from trade_rules import (
    ALL_COLONIES, AUTOMATION_COST, COLONIES, COLONY_INVEST_COST, DEVELOPMENT_THRESHOLD,
    ENDGAME_BACKGROUND_REVENUE_PER_WORLD, ENDGAME_BACKGROUND_WORLDS_PER_TICK, ENDGAME_BACKGROUND_WORLD_CAP,
    GUILD_COOLDOWN_TICKS, GUILD_FIRST_OFFER_TICKS, GUILD_REWARD_MULTIPLIER, TRADE_POST_COST,
    TRADE_POST_INCOME_PER_TICK,
)


# ---------------------------------------------------------------------------
# O-1..O-4 -- "Renew the Charter". J21's legacy (above) stays exactly as it
# was shipped: it is the flat, capped baseline (starting credits + a small
# sale bonus, five levels). What O-1 adds on top is a small permanent
# skill tree of "charter perks" bought with CHARTER POINTS, which a
# renewal earns. The legacy level counts renewals up to its cap of 5; the
# renewal count itself (charters_completed) keeps going, so the tree and
# the ledger stay meaningful long after the flat legacy is maxed. A save
# from before this feature that already has legacy level N is migrated on
# load as N completed charters with N x CHARTER_POINTS_PER_RENEWAL points
# (see load_state()), so nobody who already renewed loses progress.
#
# Everything here is opt-in: a player who never renews has no charter
# state at all, no founding conditions, and unchanged balance.
# ---------------------------------------------------------------------------
CHARTER_POINTS_PER_RENEWAL = 2
HARD_CHARTER_BONUS_POINTS = 1  # extra point for finishing a harder charter
CHARTER_BRANCHES = {
    "routes": "Routes",
    "automation": "Automation",
    "colonies": "Colonies",
    "reputation": "Reputation",
}
# Each perk is small, bought once, and is either a flat convenience or a
# modest multiplier on something that already exists; nothing here is a
# raw sale-price bonus (that is what the legacy level is for), and costs
# scale by tier (1 / 2 / 3 points). "founding" perks also take effect the
# moment a renewal begins a new charter (and immediately when bought).
CHARTER_PERKS = {
    # Routes
    "surveyed_lanes": {
        "branch": "routes", "cost": 1, "label": "Surveyed Lanes", "requires": (),
        "description": "+1 unit of cargo on every load.",
    },
    "waystation_network": {
        "branch": "routes", "cost": 2, "label": "Waystation Network", "requires": ("surveyed_lanes",),
        "description": "Trade posts cost 25% less and pay +1 credit per tick.",
    },
    "standing_convoy": {
        "branch": "routes", "cost": 3, "label": "Standing Convoy", "founding": True,
        "requires": ("waystation_network", "standing_orders"),
        "description": "Ship 1 begins every charter already automated, free of charge.",
    },
    # Automation
    "standing_orders": {
        "branch": "automation", "cost": 1, "label": "Standing Orders", "requires": (),
        "description": "Automating a ship costs 20% less.",
    },
    "lab_automation": {
        "branch": "automation", "cost": 2, "label": "Lab Automation", "requires": ("standing_orders",),
        "description": "Research points accrue 20% faster.",
    },
    "auto_balancers": {
        "branch": "automation", "cost": 3, "label": "Auto-balancers", "requires": ("lab_automation",),
        "description": "Sold-down prices recover 20% faster.",
    },
    # Colonies
    "frontier_grants": {
        "branch": "colonies", "cost": 1, "label": "Frontier Grants", "requires": (),
        "description": "Investing in a colony costs 45 credits instead of 60.",
    },
    "settler_guilds": {
        "branch": "colonies", "cost": 2, "label": "Settler Guilds", "requires": ("frontier_grants",),
        "description": "Colony needs decay 10% slower.",
    },
    "charter_colonies": {
        "branch": "colonies", "cost": 3, "label": "Charter Colonies", "requires": ("settler_guilds",),
        "description": "Colonies reach Level 2 after 85 units delivered instead of 100.",
    },
    # Reputation
    "guild_standing": {
        "branch": "reputation", "cost": 1, "label": "Guild Standing", "requires": (),
        "description": "The Trade Guild's first offer comes after 15 ticks instead of 40, and it pauses 45 instead of 60 between contracts.",
    },
    "colonial_goodwill": {
        "branch": "reputation", "cost": 2, "label": "Colonial Goodwill", "founding": True,
        "requires": ("guild_standing",),
        "description": "Home colonies begin each charter with +10% need satisfaction.",
    },
    "trusted_name": {
        "branch": "reputation", "cost": 3, "label": "Trusted Name", "requires": ("colonial_goodwill",),
        "description": "Trade Guild contracts pay a 15% larger bonus.",
    },
}
CHARTER_CARGO_BONUS = 1
WAYSTATION_COST_MULTIPLIER = 0.75
WAYSTATION_INCOME_BONUS = 1
STANDING_ORDERS_COST_MULTIPLIER = 0.8
LAB_AUTOMATION_RESEARCH_MULTIPLIER = 1.2
AUTO_BALANCERS_RECOVERY_MULTIPLIER = 1.2
FRONTIER_GRANTS_INVEST_COST = 45
SETTLER_GUILDS_DECAY_MULTIPLIER = 0.9
CHARTER_COLONIES_DEVELOPMENT_THRESHOLD = 85.0
GUILD_STANDING_FIRST_OFFER_TICKS = 15
GUILD_STANDING_COOLDOWN_TICKS = 45
COLONIAL_GOODWILL_START_BONUS = 0.1
TRUSTED_NAME_REWARD_MULTIPLIER = 1.15

# O-4 -- the opt-in harder charter (SOL's New Game+ Challenge shape: a
# tougher run, not a bonus-boosted easier one). Faster market saturation
# and quicker-fading colony needs; the reward is one extra charter point.
HARD_CHARTER_SATURATION_MULTIPLIER = 1.5
HARD_CHARTER_DECAY_MULTIPLIER = 1.35

# O-2 -- founding conditions: from the second charter on, a saved seed picks
# which two home colonies start thriving and connected (ships 1 and 2 begin
# docked at them) and what each specialises in; every other home colony
# begins stretched, so the first logistics bottleneck moves around.
FOUNDING_THRIVING_NEED = 0.8
FOUNDING_STRETCHED_NEED = 0.35
FOUNDING_FOCI = {
    "bulk": {"label": "Bulk exporter", "output": 1.15, "decay": 1.0},
    "steady": {"label": "Steady settlement", "output": 1.0, "decay": 0.7},
}
FOUNDING_SEED_MAX = 2**31 - 1

charter_rng = None  # None = the run seed's "charter" stream; a test may set a random.Random

LEDGER_MAX = 10_000_000_000
CHARTER_COUNT_MAX = 100_000
CHARTER_VETERAN_COUNT = 3  # renewals for the Charter Veteran achievement

CAREER_MAX_ENTRIES = 40
# J-14 -- the crest shown beside the title: a shape plus a text label (never
# colour only), chosen by how many charters have been completed.
CREST_TIERS = (
    (10, "Sovereign", "\u2605"),
    (5, "Master", "\u25c6"),
    (3, "Veteran", "\u25a0"),
    (1, "Renewed", "\u25b2"),
    (0, "Founder", "\u25cf"),
)


def crest_for(completed):
    """(label, glyph) of the crest earned by `completed` finished charters."""
    for minimum, label, glyph in CREST_TIERS:
        if completed >= minimum:
            return label, glyph
    return CREST_TIERS[-1][1], CREST_TIERS[-1][2]


def charter_crest():
    """(label, glyph) of the active charter's crest."""
    return crest_for(runstate.charters_completed)


def charter_crest_text():
    label, glyph = charter_crest()
    return (
        f"{glyph} {label}" + (" (harder)" if runstate.hard_charter_active else "")
        + (" \u25d0 Dark run" if records["dark_runs"] else "")  # J-30: the badge by the title
    )


def charter_perk(perk_id):
    return perk_id in runstate.charter_perks


def charter_points_spent():
    return sum(CHARTER_PERKS[perk_id]["cost"] for perk_id in runstate.charter_perks)


def charter_points_available():
    return runstate.charter_points_earned - charter_points_spent()


def charter_perk_missing_requirements(perk_id):
    return [r for r in CHARTER_PERKS[perk_id]["requires"] if r not in runstate.charter_perks]


def can_buy_charter_perk(perk_id):
    if not isinstance(perk_id, str) or perk_id not in CHARTER_PERKS or perk_id in runstate.charter_perks:
        return False
    if charter_perk_missing_requirements(perk_id):
        return False
    return charter_points_available() >= CHARTER_PERKS[perk_id]["cost"]


# --- perk-aware values (each equals its plain constant when no perk applies) ---
def automation_cost():
    if charter_perk("standing_orders"):
        return int(round(AUTOMATION_COST * STANDING_ORDERS_COST_MULTIPLIER))
    return AUTOMATION_COST


def colony_invest_cost():
    return FRONTIER_GRANTS_INVEST_COST if charter_perk("frontier_grants") else COLONY_INVEST_COST


def trade_post_cost():
    if charter_perk("waystation_network"):
        return int(round(TRADE_POST_COST * WAYSTATION_COST_MULTIPLIER))
    return TRADE_POST_COST


def trade_post_income_each():
    return TRADE_POST_INCOME_PER_TICK + (WAYSTATION_INCOME_BONUS if charter_perk("waystation_network") else 0)


def development_threshold():
    return CHARTER_COLONIES_DEVELOPMENT_THRESHOLD if charter_perk("charter_colonies") else DEVELOPMENT_THRESHOLD


def guild_first_offer_ticks():
    return GUILD_STANDING_FIRST_OFFER_TICKS if charter_perk("guild_standing") else GUILD_FIRST_OFFER_TICKS


def guild_cooldown_ticks():
    return GUILD_STANDING_COOLDOWN_TICKS if charter_perk("guild_standing") else GUILD_COOLDOWN_TICKS


def guild_reward_multiplier():
    return GUILD_REWARD_MULTIPLIER * (TRUSTED_NAME_REWARD_MULTIPLIER if charter_perk("trusted_name") else 1.0)


def founding_from_seed(seed):
    """Deterministic founding conditions for a saved seed: the two home
    colonies that start thriving and connected, and each one's focus."""
    rng = random.Random(seed)
    order = list(COLONIES)
    pair = sorted(rng.sample(order, 2), key=order.index)
    foci = {colony_id: rng.choice(list(FOUNDING_FOCI)) for colony_id in pair}
    return {"pair": pair, "foci": foci}


def founding_focus(colony_id):
    """The founding focus key for a colony in the current charter, or None."""
    if not runstate.founding_seed:
        return None
    return founding_from_seed(runstate.founding_seed)["foci"].get(colony_id)


def founding_output_multiplier(colony_id):
    focus = founding_focus(colony_id)
    return FOUNDING_FOCI[focus]["output"] if focus else 1.0


def charter_decay_multiplier(colony_id):
    """Everything that scales how fast a colony's need fades, in one place."""
    multiplier = 1.0
    if runstate.hard_charter_active:
        multiplier *= HARD_CHARTER_DECAY_MULTIPLIER
    if charter_perk("settler_guilds"):
        multiplier *= SETTLER_GUILDS_DECAY_MULTIPLIER
    focus = founding_focus(colony_id)
    if focus:
        multiplier *= FOUNDING_FOCI[focus]["decay"]
    return multiplier


def founding_summary_text():
    if not runstate.founding_seed:
        return "Founding conditions: the standard opening. From your second charter on, each one starts differently."
    info = founding_from_seed(runstate.founding_seed)
    a, b = info["pair"]
    parts = ", ".join(
        f"{ALL_COLONIES[cid]['name']} is a {FOUNDING_FOCI[info['foci'][cid]]['label'].lower()}" for cid in info["pair"]
    )
    return (
        f"Founding conditions: {ALL_COLONIES[a]['name']} and {ALL_COLONIES[b]['name']} start thriving and connected "
        f"(Ships 1 and 2 begin docked there); {parts}. The other home colonies start stretched."
    )


def hard_charter_unlocked():
    """Available from the first endgame onward, never before it."""
    return runstate.endgame_reached or runstate.charters_completed > 0


def set_hard_charter_next(enabled):
    if not hard_charter_unlocked():
        return False
    runstate.hard_charter_next = bool(enabled)
    return True


def charter_points_for_next_renewal():
    return CHARTER_POINTS_PER_RENEWAL + (HARD_CHARTER_BONUS_POINTS if runstate.hard_charter_active else 0)


def ledger_record_sale(qty, route_key):
    """O-3: called for every completed, undisrupted delivery."""
    runstate.ledger_units_moved = min(LEDGER_MAX, runstate.ledger_units_moved + max(0, int(qty)))
    runstate.ledger_charter_units = min(LEDGER_MAX, runstate.ledger_charter_units + max(0, int(qty)))
    if route_key and route_key not in runstate.ledger_routes_seen:
        runstate.ledger_routes_seen.add(route_key)
        runstate.ledger_routes_established = min(LEDGER_MAX, runstate.ledger_routes_established + 1)


def charter_summary_text():
    if not runstate.charters_completed and not runstate.charter_perks:
        return "Charter: not yet renewed."
    hard = " (harder charter)" if runstate.hard_charter_active else ""
    return (
        f"Charter: {runstate.charters_completed} renewed, {charter_points_available()} charter points to spend, "
        f"{len(runstate.charter_perks)}/{len(CHARTER_PERKS)} perks{hard}."
    )


def background_world_count():
    return min(ENDGAME_BACKGROUND_WORLD_CAP, ENDGAME_BACKGROUND_WORLDS_PER_TICK * runstate.ticks_since_endgame)


def background_revenue_this_tick():
    return round(background_world_count() * ENDGAME_BACKGROUND_REVENUE_PER_WORLD)
