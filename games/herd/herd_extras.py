"""Extra panels: vignettes, season, welfare, genetics and biogas lines, the policy cards, the satellite farm and the tagline.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from js import document

import herd_runstate as runstate
from herd_rules import (
    BASE_COUPLING_RATIO, CAPTURE_SELF_USE_UNITS, GENETICS_COST, GENETICS_MATURE_ROUNDS,
    HALF_DECOUPLED_CALLOUT_THRESHOLD, POLICY_EVENT_INTERVAL, POLICY_OPTIONS, POULTRY_MEASURES,
    POULTRY_UPKEEP_PER_UNIT, PRESSURE_CALLOUT_THRESHOLD, REGIONAL_CAP, SATELLITE_BASE_RATIO,
    SATELLITE_MAX_RETROFITS, SATELLITE_MAX_SIZE, SATELLITE_OFFSET_FLOOR, SATELLITE_OPEN_COST,
    SATELLITE_RETROFIT_COST, SUPPLY_CHAIN_COST, SUPPLY_CHAIN_MAX_UNITS, WELFARE_MAX,
)
from herd_model import demand_surge_active, season_for_round
from herd_succession import render_succession


# F17 -- farm tour: short flavor vignettes reacting to the coupling ratio.
VIGNETTES = {
    "coupled": [
        "A neighbour's kid asks why the sky over the ridge looks hazy this morning.",
        "The co-op newsletter mentions methane again. You fold it into the pile of letters.",
        "Every feed truck that pulls in seems to leave a little more haze behind.",
    ],
    "improving": [
        "The vet notes the herd's digestion is calmer since the feed change.",
        "A sensor on the barn roof reads lower than last month. You tap it twice to be sure.",
        "At the market stall someone asks how you cut the smell. You show them the numbers.",
    ],
    "clean": [
        "Evening light, quiet pasture: the wisps over the cows have almost gone.",
        "A regional inspector visits, nods, and asks if she can bring a school group next spring.",
        "You catch yourself explaining decoupling to a stranger at the gate, and enjoying it.",
    ],
}


def farm_vignette():
    """Pure function of ratio + round: same farm, same story."""
    ratio = runstate.farm.coupling_ratio()
    band = "coupled" if ratio > 0.8 else ("improving" if ratio > 0.4 else "clean")
    options = VIGNETTES[band]
    return "\U0001F69C " + options[runstate.farm.round_number % len(options)]


def season_message():
    if not runstate.farm.variation_enabled:
        return "Market & weather variation is off (turn it on under Scenario options)."
    name, _raw = season_for_round(runstate.farm.round_number)
    mod = runstate.farm.season_modifier()
    text = f"This round: {name}, income {mod * 100:+.0f}%."
    if demand_surge_active(runstate.farm.round_number):
        text += " Plant-based demand surge: plant-based output earns more this round."
    return text


def welfare_message():
    bonus = (runstate.farm.welfare_multiplier() - 1) * 100
    return f"Herd welfare: {runstate.farm.welfare():.0f}/100 (income {bonus:+.1f}% from welfare)"


def genetics_message():
    return (
        f"Breeding: {runstate.farm.genetics_active} lines active, {len(runstate.farm.genetics_pending)} maturing "
        f"({GENETICS_MATURE_ROUNDS} rounds each; a ring below counts each one down)"
    )


def biogas_message():
    surplus = max(0, runstate.farm.decoupling_investment["capture"] - CAPTURE_SELF_USE_UNITS)
    if surplus == 0:
        return (
            f"Biogas sales: the first {CAPTURE_SELF_USE_UNITS} Capture Systems cover on-farm energy; "
            "extra capacity is sold as biogas."
        )
    return f"Biogas sales: {surplus} surplus capture unit(s) earn {runstate.farm.biogas_sales():.1f} funds per round."


def policy_option_blurb(option_id):
    """What the option would do right now, with today's numbers."""
    spec = POLICY_OPTIONS[option_id]
    if option_id == "carbon_credit":
        return f"{runstate.farm.carbon_credit_value()} funds now ({spec['blurb']})"
    if option_id == "welfare_grant":
        return f"{runstate.farm.welfare_grant_value()} funds now ({spec['blurb']})"
    return spec["blurb"]


def policy_active_message():
    parts = []
    if runstate.farm.subsidy_rounds_left > 0:
        parts.append(f"decoupling subsidy, {runstate.farm.subsidy_rounds_left} rounds left")
    if runstate.farm.hedge_rounds_left > 0:
        parts.append(f"feed-price hedge, {runstate.farm.hedge_rounds_left} rounds left")
    if runstate.farm.label_rounds_left > 0:
        parts.append(f"organic label trial, {runstate.farm.label_rounds_left} rounds left")
    return ("Active: " + "; ".join(parts) + ".") if parts else ""


def policy_message():
    if runstate.farm.policy_offer_pending:
        first, second = runstate.farm.current_policy_offer()
        return (
            f"Policy advisor: pick one. {POLICY_OPTIONS[first]['label']}: {policy_option_blurb(first)}. "
            f"Or {POLICY_OPTIONS[second]['label']}: {policy_option_blurb(second)}."
        )
    return policy_active_message()


def policy_real_message():
    if not runstate.farm.policy_offer_pending:
        return ""
    return " ".join(POLICY_OPTIONS[o]["real"] for o in runstate.farm.current_policy_offer())


def policy_history_html():
    if not runstate.farm.policy_history:
        return (
            f"<li>No advisor offers taken yet. An advisor visits every {POLICY_EVENT_INTERVAL} rounds "
            "with two options from a pool of six.</li>"
        )
    rows = []
    for rnd, taken, other in reversed(runstate.farm.policy_history):
        t, o = POLICY_OPTIONS[taken], POLICY_OPTIONS[other]
        rows.append(
            f"<li>Round {rnd}: took {t['label']} ({t['tag']}), passed on {o['label']} ({o['tag']}).</li>"
        )
    return "".join(rows)


def policy_report_line():
    if not runstate.farm.policy_history:
        return "Advisor choices: none yet."
    names = ", ".join(POLICY_OPTIONS[t]["label"] for _r, t, _o in runstate.farm.policy_history[-4:])
    return f"Advisor choices ({len(runstate.farm.policy_history)} so far, latest last): {names}."


def render_extras():
    document.getElementById("vignette-display").innerText = farm_vignette()
    document.getElementById("season-display").innerText = season_message()
    document.getElementById("welfare-display").innerText = welfare_message()
    document.getElementById("genetics-display").innerText = genetics_message()
    genetics_button = document.getElementById("genetics-invest-button")
    genetics_button.innerText = f"Breeding Program ({GENETICS_COST})"
    genetics_button.disabled = runstate.farm.funds < GENETICS_COST
    document.getElementById("supply-chain-display").innerText = (
        f"Supply chain: {runstate.farm.supply_chain_investment}/{SUPPLY_CHAIN_MAX_UNITS} "
        f"(+{(runstate.farm.supply_chain_multiplier() - 1) * 100:.0f}% income)"
    )
    supply_button = document.getElementById("supply-chain-invest-button")
    supply_button.innerText = f"Processing & Distribution ({SUPPLY_CHAIN_COST})"
    supply_button.disabled = runstate.farm.funds < SUPPLY_CHAIN_COST or runstate.farm.supply_chain_investment >= SUPPLY_CHAIN_MAX_UNITS
    document.getElementById("biogas-display").innerText = biogas_message()
    # F-14: the two small bars (welfare out of 100, supply chain out of its maximum).
    document.getElementById("welfare-bar").style.width = f"{runstate.farm.welfare() / WELFARE_MAX * 100:.0f}%"
    document.getElementById("supply-chain-bar").style.width = (
        f"{runstate.farm.supply_chain_investment / SUPPLY_CHAIN_MAX_UNITS * 100:.0f}%"
    )
    document.getElementById("variation-checkbox").checked = runstate.farm.variation_enabled
    document.getElementById("cap-checkbox").checked = runstate.farm.regional_cap_enabled
    document.getElementById("cap-display").innerText = (
        f"Regional cap: {runstate.farm.methane_this_round():.1f} of {REGIONAL_CAP:.0f} methane/round. Growth is blocked past the cap."
        if runstate.farm.regional_cap_enabled else "Regional methane cap is off."
    )
    # F27 policy advisor
    document.getElementById("policy-panel").hidden = not runstate.farm.policy_offer_pending
    document.getElementById("policy-display").innerText = policy_message()
    document.getElementById("policy-real-display").innerText = policy_real_message()
    for slot, button_id in enumerate(("policy-subsidy-button", "policy-cash-button")):
        option = POLICY_OPTIONS[runstate.farm.current_policy_offer()[slot]]
        button = document.getElementById(button_id)
        button.innerText = f"Take: {option['label']} ({option['tag']})"
        button.title = option["real"]
    document.getElementById("policy-history-list").innerHTML = policy_history_html()
    render_succession()
    render_satellite()
    document.getElementById("tagline-display").innerText = tagline_message()

    # F23 poultry
    unlocked = runstate.farm.poultry_unlocked()
    document.getElementById("poultry-panel").hidden = not unlocked
    if unlocked:
        document.getElementById("poultry-display").innerText = (
            f"Flock: {runstate.farm.poultry_size} bird(s). Emissions {runstate.farm.poultry_coupling_ratio():.2f} methane-equivalent "
            f"per bird per round (cattle start at {BASE_COUPLING_RATIO:.2f}). Upkeep {POULTRY_UPKEEP_PER_UNIT} per bird."
        )
        grow_cost = runstate.farm.poultry_grow_cost()
        button = document.getElementById("poultry-grow-button")
        button.innerText = f"Grow Flock ({grow_cost:.0f})"
        button.disabled = runstate.farm.funds < grow_cost or runstate.farm.cap_blocks_growth(poultry=1)
        for measure, spec in POULTRY_MEASURES.items():
            document.getElementById(f"{measure}-count").innerText = str(runstate.farm.poultry_investment[measure])
            b = document.getElementById(f"{measure}-invest-button")
            b.innerText = f"{spec['label']} ({spec['cost']})"
            b.disabled = runstate.farm.funds < spec["cost"]


def satellite_message():
    if not runstate.farm.satellite_open:
        return (
            f"Open a smaller satellite farm for {SATELLITE_OPEN_COST} funds. It starts dirtier than your main farm "
            f"({SATELLITE_BASE_RATIO:.2f} methane per animal), but decoupling your main farm past "
            f"{round(SATELLITE_OFFSET_FLOOR * 100)}% starts cutting its emissions too."
        )
    offset = round(runstate.farm.satellite_offset_fraction() * 100)
    return (
        f"Satellite herd: {runstate.farm.satellite_size} of {SATELLITE_MAX_SIZE} animals. Emissions "
        f"{runstate.farm.satellite_coupling_ratio():.2f} methane per animal per round "
        f"(its own retrofits give {runstate.farm.satellite_own_ratio():.2f}; main-farm surplus offsets {offset}%). "
        f"Retrofits {runstate.farm.satellite_retrofits}/{SATELLITE_MAX_RETROFITS}."
    )


def render_satellite():
    panel = document.getElementById("satellite-panel")
    available = runstate.farm.satellite_available()
    panel.hidden = not available
    if not available:
        return
    document.getElementById("satellite-display").innerText = satellite_message()
    open_button = document.getElementById("satellite-open-button")
    grow_button = document.getElementById("satellite-grow-button")
    retrofit_button = document.getElementById("satellite-retrofit-button")
    open_button.hidden = runstate.farm.satellite_open
    grow_button.hidden = not runstate.farm.satellite_open
    retrofit_button.hidden = not runstate.farm.satellite_open
    open_button.innerText = f"Open Satellite Farm ({SATELLITE_OPEN_COST})"
    open_button.disabled = runstate.farm.funds < SATELLITE_OPEN_COST
    grow_cost = runstate.farm.satellite_grow_cost()
    grow_button.innerText = f"Grow Satellite Herd ({grow_cost:.1f})"
    grow_button.disabled = (
        runstate.farm.funds < grow_cost or runstate.farm.satellite_size >= SATELLITE_MAX_SIZE or runstate.farm.cap_blocks_growth(satellite=1)
    )
    retrofit_button.innerText = f"Retrofit Barns ({SATELLITE_RETROFIT_COST})"
    retrofit_button.disabled = (
        runstate.farm.funds < SATELLITE_RETROFIT_COST or runstate.farm.satellite_retrofits >= SATELLITE_MAX_RETROFITS
    )


SATELLITE_LEVER_KEYS = {
    "open_satellite": "satellite_open",
    "grow_satellite": "satellite_grow",
    "retrofit_satellite": "satellite_retrofit",
}


def _satellite_action_cost(action):
    return {
        "open_satellite": SATELLITE_OPEN_COST,
        "grow_satellite": runstate.farm.satellite_grow_cost(),
        "retrofit_satellite": SATELLITE_RETROFIT_COST,
    }[action]


# R-23: the sentence under the title reacts to how the session is going.
TAGLINE_DEFAULT = "Grow a farm. Herd size and methane emissions are coupled by default — decoupling them takes deliberate investment."
TAGLINE_PRESSURE = "Methane is building, and the market is starting to push back. Growth is beginning to cost more than it earns."
TAGLINE_HALF = "Half the coupling is gone: the same herd now emits far less. Keep going, or start to diversify."
TAGLINE_CERTIFIED = "A certified farm. Growing the herd and cutting methane are no longer pulling against each other."


def tagline_message():
    """One sentence for the current state, in priority order: certified,
    then decoupled by half or more, then methane pressure past the callout
    level, else the opening line."""
    if runstate.farm.certified:
        return TAGLINE_CERTIFIED
    if runstate.farm.decoupled_fraction() >= HALF_DECOUPLED_CALLOUT_THRESHOLD:
        return TAGLINE_HALF
    if runstate.farm.pressure_fraction() >= PRESSURE_CALLOUT_THRESHOLD:
        return TAGLINE_PRESSURE
    return TAGLINE_DEFAULT
