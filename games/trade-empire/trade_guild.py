"""The Trade Guild contract (offer, accept, delivery, deadline) and its panel, plus the endgame background-galaxy numbers."""

from js import document

import trade_runstate as runstate
from trade_charter import guild_cooldown_ticks, guild_reward_multiplier
from trade_colony import active_colony_ids
from trade_effects import guild_contract
from trade_market import current_sell_price, run_stream
from trade_rules import ALL_COLONIES, GUILD_FIRST_OFFER_TICKS
from trade_uikit import show_notice_toast


# J3 -- the Trade Guild: an NPC faction that occasionally offers a bulk
# contract (deliver N units of a good to a colony that needs it, before a
# deadline) for a bonus on top of the ordinary sale. Deliveries still sell
# normally, so a contract is purely an extra reward. Accepting is optional;
# failing or ignoring one costs nothing.
GUILD_MIN_SALES = 3  # nothing is offered until the player has made a few sales

GUILD_OFFER_LAPSE_TICKS = 90  # how long an unanswered offer stays on the table
GUILD_DEADLINE_TICKS = 150
GUILD_UNITS_MIN, GUILD_UNITS_MAX = 10, 30

GUILD_STATES = ("none", "offered", "active")
guild_rng = None  # None = the run seed's "guild" stream; a test may set a random.Random

runstate.guild_cooldown = GUILD_FIRST_OFFER_TICKS


def _guild_clear(cooldown=None):
    if cooldown is None:
        cooldown = guild_cooldown_ticks()
    runstate.guild_state = "none"
    runstate.guild_cooldown = cooldown
    guild_contract.update({"good": None, "destination": None, "units": 0, "delivered": 0, "ticks_left": 0, "reward": 0})


def guild_candidates():
    """(destination, good) pairs the guild could ask for: a reachable colony
    and the good it naturally needs."""
    return [(cid, ALL_COLONIES[cid]["needs"]) for cid in active_colony_ids()]


def guild_make_offer():
    options = guild_candidates()
    if not options or runstate.guild_state != "none":
        return False
    rng = guild_rng if guild_rng is not None else run_stream("guild", runstate.guild_offers)
    runstate.guild_offers += 1
    destination, good = rng.choice(options)
    units = rng.randint(GUILD_UNITS_MIN, GUILD_UNITS_MAX)
    guild_contract.update({
        "good": good,
        "destination": destination,
        "units": units,
        "delivered": 0,
        "ticks_left": GUILD_OFFER_LAPSE_TICKS,
        "reward": int(round(units * current_sell_price(good) * guild_reward_multiplier())),
    })
    runstate.guild_state = "offered"
    return True


def guild_accept():
    if runstate.guild_state != "offered":
        return False
    runstate.guild_state = "active"
    guild_contract["ticks_left"] = GUILD_DEADLINE_TICKS
    return True


def guild_decline():
    if runstate.guild_state != "offered":
        return False
    _guild_clear()
    return True


def guild_record_delivery(good, destination, qty):
    """Called for every completed, undisrupted sale."""
    if runstate.guild_state != "active" or good != guild_contract["good"] or destination != guild_contract["destination"]:
        return
    guild_contract["delivered"] = min(guild_contract["units"], guild_contract["delivered"] + max(0, int(qty)))
    if guild_contract["delivered"] >= guild_contract["units"]:
        reward = guild_contract["reward"]
        runstate.total_profit += reward
        runstate.max_profit_ever = max(runstate.max_profit_ever, runstate.total_profit)
        runstate.guild_completed += 1
        _guild_clear()
        show_notice_toast(f"\U0001F91D Trade Guild contract complete: +{reward:,} credits.")


def guild_tick():
    if runstate.guild_state == "none":
        runstate.guild_cooldown -= 1
        if runstate.guild_cooldown <= 0 and runstate.total_sales_count >= GUILD_MIN_SALES:
            guild_make_offer()
    elif runstate.guild_state == "offered":
        guild_contract["ticks_left"] -= 1
        if guild_contract["ticks_left"] <= 0:
            _guild_clear()  # lapsed unanswered: no penalty
    elif runstate.guild_state == "active":
        guild_contract["ticks_left"] -= 1
        if guild_contract["ticks_left"] <= 0:
            runstate.guild_failed += 1
            _guild_clear()  # missed the deadline: no penalty, just no bonus


def guild_status_text():
    c = guild_contract
    if runstate.guild_state == "offered":
        return (
            f"The Trade Guild offers a contract: deliver {c['units']} {c['good'].replace('_', ' ')} to "
            f"{ALL_COLONIES[c['destination']]['name']} within {GUILD_DEADLINE_TICKS} ticks of accepting "
            f"for a {c['reward']:,}-credit bonus on top of the normal sale."
        )
    if runstate.guild_state == "active":
        return (
            f"Contract accepted: {c['delivered']}/{c['units']} {c['good'].replace('_', ' ')} delivered to "
            f"{ALL_COLONIES[c['destination']]['name']}, {c['ticks_left']} ticks left "
            f"for a {c['reward']:,}-credit bonus."
        )
    record = f" Contracts completed: {runstate.guild_completed}." if runstate.guild_completed else ""
    return "The Trade Guild is watching your fleet. A contract will be offered when it has one for you." + record


def render_guild():
    document.getElementById("guild-status-display").innerText = guild_status_text()
    document.getElementById("guild-accept-button").hidden = runstate.guild_state != "offered"
    document.getElementById("guild-decline-button").hidden = runstate.guild_state != "offered"
