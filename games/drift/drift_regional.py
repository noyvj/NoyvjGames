"""The optional neighbouring region (open, invest, support, spillover) and the second-wave, policies and neighbour panels."""

from js import document

import drift_runstate as runstate
from drift_model_region import RegionState, region
from drift_rules import (
    CAPACITY_LABEL, CAPACITY_TYPES, INVEST_COST, NEIGHBOR_MIN_ROUND, NEIGHBOR_SPILLOVER_ARRIVALS,
    NEIGHBOR_START_ARRIVALS, NEIGHBOR_START_FUNDS, NEIGHBOR_START_HOUSING, NEIGHBOR_START_SEVERITY,
    NEIGHBOR_SUPPORT_AMOUNT, NEIGHBOR_SUPPORT_RESERVE, POLICIES, POLICY_MAX_LEVEL, STRAIN_LEVEL_THRESHOLDS,
)


def neighbor_available():
    return runstate.neighbor is not None or region.round_number >= NEIGHBOR_MIN_ROUND


def _new_neighbor_region():
    """A fresh neighbouring region: housing-rich but with no integration
    services, little money and a higher background pressure. Its own second
    wave and cross-region learning are switched off so it stays a simple
    second dial, not a second copy of every system."""
    other = RegionState()
    other.funds = NEIGHBOR_START_FUNDS
    other.capacity["housing"] = NEIGHBOR_START_HOUSING
    other.total_arrivals = NEIGHBOR_START_ARRIVALS
    other.background_severity = NEIGHBOR_START_SEVERITY
    other.learning_active = False
    other.second_wave_status = "done"
    other.second_wave_result = "held"
    return other


def open_neighbor():
    if runstate.neighbor is not None or region.round_number < NEIGHBOR_MIN_ROUND:
        return False
    runstate.neighbor = _new_neighbor_region()
    _sync_spillover()
    return True


def invest_neighbor(capacity_type):
    if runstate.neighbor is None or capacity_type not in CAPACITY_TYPES:
        return False
    bought = runstate.neighbor.invest(capacity_type)
    if bought:
        region.round_buys += 1  # I-15: counts as a decision this round
    return bought


def main_region_well_prepared():
    """I7: the main region can spare help only while it is not strained and
    would still hold a reserve after sending it."""
    return (
        region.strain_fraction() < STRAIN_LEVEL_THRESHOLDS[1][0]
        and region.funds >= NEIGHBOR_SUPPORT_AMOUNT + NEIGHBOR_SUPPORT_RESERVE
    )


def support_neighbor():
    if runstate.neighbor is None or not main_region_well_prepared():
        return False
    region.funds -= NEIGHBOR_SUPPORT_AMOUNT
    runstate.neighbor.funds += NEIGHBOR_SUPPORT_AMOUNT
    runstate.neighbor_support_sent += NEIGHBOR_SUPPORT_AMOUNT
    region.round_buys += 1  # I-15
    return True


def neighbor_spillover():
    if runstate.neighbor is not None and runstate.neighbor.strain_fraction() >= STRAIN_LEVEL_THRESHOLDS[2][0]:
        return NEIGHBOR_SPILLOVER_ARRIVALS
    return 0.0


def _sync_spillover():
    region.spillover_arrivals = neighbor_spillover()


def render_second_wave():
    element = document.getElementById("second-wave-display")
    if element is None:
        return
    text = region.second_wave_message()
    element.innerText = text
    element.hidden = text == ""


def render_policies():
    for policy, spec in POLICIES.items():
        level = region.policy_level[policy]
        document.getElementById(f"policy-{policy.replace('_', '-')}-name").innerText = (
            f"{spec['icon']} {spec['label']} ({level}/{POLICY_MAX_LEVEL})"
        )
        button = document.getElementById(f"policy-{policy.replace('_', '-')}-button")
        if level >= POLICY_MAX_LEVEL:
            button.innerText = "Maxed"
            button.disabled = True
        else:
            button.innerText = f"Fund ({region.policy_cost(policy):.0f})"
            button.disabled = region.funds < region.policy_cost(policy)


def neighbor_message():
    if runstate.neighbor is None:
        return (
            "A neighbouring district has plenty of housing but no integration services, little money and a "
            "higher background pressure. Open it to run both regions side by side."
        )
    text = (
        f"Neighbouring district, round {runstate.neighbor.round_number}: funds {runstate.neighbor.funds:.0f}, "
        f"capacity {runstate.neighbor.total_capacity():.0f}, strain {runstate.neighbor.strain_fraction() * 100:.0f}% "
        f"({runstate.neighbor.strain_level()}), integrated {runstate.neighbor.integrated_population:.0f} of "
        f"{runstate.neighbor.total_arrivals:.0f} arrivals, wellbeing {runstate.neighbor.wellbeing_score():.0f}."
    )
    if neighbor_spillover():
        text += (
            f" Its strain is critical, so {NEIGHBOR_SPILLOVER_ARRIVALS:.0f} extra people a round are "
            "reaching your region."
        )
    if runstate.neighbor_support_sent:
        text += f" You have sent it {runstate.neighbor_support_sent:.0f} funds so far."
    return text


def render_neighbor():
    panel = document.getElementById("neighbor-panel")
    available = neighbor_available()
    panel.hidden = not available
    if not available:
        return
    document.getElementById("neighbor-display").innerText = neighbor_message()
    open_button = document.getElementById("neighbor-open-button")
    open_button.hidden = runstate.neighbor is not None
    for capacity_type in CAPACITY_TYPES:
        button = document.getElementById(f"neighbor-{capacity_type}-button")
        button.hidden = runstate.neighbor is None
        button.innerText = f"{CAPACITY_LABEL[capacity_type]} ({INVEST_COST[capacity_type]:.0f})"
        button.disabled = runstate.neighbor is None or runstate.neighbor.funds < INVEST_COST[capacity_type]
    support_button = document.getElementById("neighbor-support-button")
    support_button.hidden = runstate.neighbor is None
    support_button.innerText = f"Send support ({NEIGHBOR_SUPPORT_AMOUNT:.0f})"
    support_button.disabled = not main_region_well_prepared()
