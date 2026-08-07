"""Drift — Climate Migration & Displacement Game.

Runs in-browser via Pyodide. Milestone 1: the core allocation loop — a
receiving region invests its budget across housing, integration
services, and infrastructure capacity, round by round. Displacement
pressure, strain, integration payoff, and composite scoring land in
later milestones; this milestone is just "can the region build
capacity at all."
"""

from js import document
from pyodide.ffi import create_proxy

STARTING_FUNDS = 300.0

# A receiving region has some baseline economic activity of its own,
# independent of any arrivals — this is what lets a region build capacity
# ahead of pressure, not just react to it once people are already arriving.
BASE_REGIONAL_INCOME_PER_ROUND = 50.0

CAPACITY_TYPES = ["housing", "services", "infrastructure"]

CAPACITY_LABEL = {
    "housing": "Housing",
    "services": "Integration Services",
    "infrastructure": "Infrastructure",
}

CAPACITY_ICON = {
    "housing": "\U0001F3E0",
    "services": "\U0001F4DA",
    "infrastructure": "\U0001F6E0️",
}

INVEST_COST = {
    "housing": 20.0,
    "services": 20.0,
    "infrastructure": 25.0,
}

# Capacity units gained per investment — infrastructure is the most
# expensive but also the most durable/broadly useful, which M3's strain
# system will lean on.
CAPACITY_PER_INVESTMENT = {
    "housing": 10.0,
    "services": 8.0,
    "infrastructure": 6.0,
}

# Displacement pressure: background climate severity rises steadily and
# largely outside the player's control (mirrors Thaw's background
# trajectory), and arrivals each round scale with it. This is the
# pressure the region's capacity gets measured against starting in
# Milestone 3 — not something the player causes or can dial down, only
# something they can prepare for.
BACKGROUND_SEVERITY_RISE_PER_ROUND = 0.5
BASE_ARRIVALS_PER_ROUND = 5.0
ARRIVALS_PER_SEVERITY_POINT = 3.0

# Strain: how much cumulative arrivals outrun cumulative capacity. Soft
# consequence only — strain eats into the region's own income (service
# shortfalls and friction cost money) but never blocks play or zeroes
# funds outright, since strain_fraction is naturally capped at 1.0.
STRAIN_LEVEL_THRESHOLDS = [
    (0.0, "stable"),
    (0.25, "strained"),
    (0.6, "critical"),
]

# Integration payoff: services capacity is the region's throughput for
# moving arrived people from "pending" to "integrated" — language,
# employment, education access. Integrated people contribute back to
# the regional economy every round after that, which is what makes
# integration net-positive rather than a permanent drain: a services
# investment (cost 20, +8 capacity) pays for itself in about 6 rounds
# once integration ramps up (8 * 0.3 = 2.4 people/round * 1.5/person =
# 3.6 funds/round), and keeps paying indefinitely after that.
INTEGRATION_RATE_PER_SERVICES_UNIT = 0.3
INTEGRATION_CONTRIBUTION_PER_PERSON = 1.5

# Composite wellbeing: three separately-tracked sub-scores (0-100 each)
# rather than one blended number, per the plan's explicit instruction —
# keeps the end-state legible ("service quality is fine but cohesion is
# lagging" reads very differently from one number). Wellbeing score is
# their simple average.
WELLBEING_FUNDS_SCALE = 1000.0


class RegionState:
    def __init__(self):
        self.round_number = 1
        self.funds = STARTING_FUNDS
        self.capacity = {t: 0.0 for t in CAPACITY_TYPES}
        self.background_severity = 0.0
        self.total_arrivals = 0.0
        self.arrivals_log = []
        self.strain_log = []
        self.integrated_population = 0.0

    def total_capacity(self):
        return sum(self.capacity[t] for t in CAPACITY_TYPES)

    def invest(self, capacity_type):
        cost = INVEST_COST[capacity_type]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.capacity[capacity_type] += CAPACITY_PER_INVESTMENT[capacity_type]
        return True

    def arrivals_this_round(self):
        """People arriving this round, rising with background severity —
        loosely tied to it, not a hard function the player can reverse-
        engineer to zero, but predictable enough to plan capacity around."""
        return BASE_ARRIVALS_PER_ROUND + self.background_severity * ARRIVALS_PER_SEVERITY_POINT

    def strain_fraction(self):
        """0..1 — the share of the region's arrived population that
        current capacity fails to cover. Zero while capacity keeps pace
        with arrivals; rises toward (but never reaches) 1 as arrivals
        outrun capacity."""
        if self.total_arrivals <= 0:
            return 0.0
        shortfall = max(0.0, self.total_arrivals - self.total_capacity())
        return min(1.0, shortfall / self.total_arrivals)

    def strain_level(self):
        level = STRAIN_LEVEL_THRESHOLDS[0][1]
        for threshold, label in STRAIN_LEVEL_THRESHOLDS:
            if self.strain_fraction() >= threshold:
                level = label
        return level

    def pending_population(self):
        """Arrived people not yet integrated — still waiting on services
        throughput to reach them."""
        return max(0.0, self.total_arrivals - self.integrated_population)

    def integration_this_round(self):
        """People who move from pending to integrated this round, capped
        by services throughput and by how many people are actually
        waiting — this cap is the lag: a region can only integrate as
        fast as its services capacity allows, regardless of funds."""
        throughput = self.capacity["services"] * INTEGRATION_RATE_PER_SERVICES_UNIT
        return min(self.pending_population(), throughput)

    def integration_contribution(self):
        """Funds integrated people contribute back each round — the
        net-positive core of the hope angle: integration isn't a
        permanent drain, it eventually pays for the services investment
        that enabled it and keeps paying after that."""
        return self.integrated_population * INTEGRATION_CONTRIBUTION_PER_PERSON

    def average_strain(self):
        """Sustained strain across the whole run so far, not just the
        current snapshot — a late recovery can't fully erase an early
        crisis, mirroring Grid's average_clean_fraction."""
        if not self.strain_log:
            return 0.0
        return sum(self.strain_log) / len(self.strain_log)

    def integration_fraction(self):
        if self.total_arrivals <= 0:
            return 0.0
        return self.integrated_population / self.total_arrivals

    def service_quality(self):
        """0-100 — how well services have kept pace with arrivals over
        the whole run, not just right now."""
        return (1 - self.average_strain()) * 100

    def economic_health(self):
        """0-100 — regional funds relative to a reference scale, capped
        both ends so a very poor or very rich region reads as a clean
        floor/ceiling rather than an unbounded number."""
        return min(100.0, max(0.0, self.funds / WELLBEING_FUNDS_SCALE * 100))

    def social_cohesion(self):
        """0-100 — the share of everyone who's arrived that's actually
        been integrated so far."""
        return self.integration_fraction() * 100

    def wellbeing_score(self):
        return (self.service_quality() + self.economic_health() + self.social_cohesion()) / 3

    def advance_round(self):
        strain = self.strain_fraction()
        self.strain_log.append(strain)
        income = BASE_REGIONAL_INCOME_PER_ROUND * (1 - strain)
        income += self.integration_contribution()

        self.integrated_population += self.integration_this_round()

        arrivals = self.arrivals_this_round()
        self.total_arrivals += arrivals
        self.arrivals_log.append(arrivals)
        self.background_severity += BACKGROUND_SEVERITY_RISE_PER_ROUND
        self.funds += income
        self.round_number += 1


region = RegionState()


def wellbeing_message(score):
    if score >= 70:
        return "This region is turning displacement into a manageable — even thriving — transition."
    if score >= 40:
        return "This region is managing, but strain and slow integration are holding it back."
    return "This region is struggling: capacity hasn't kept pace with arrivals."


def render():
    document.getElementById("round-display").innerText = f"Round {region.round_number}"
    document.getElementById("funds-display").innerText = f"Funds: {region.funds:.0f}"
    document.getElementById("total-capacity-display").innerText = (
        f"Total capacity: {region.total_capacity():.0f}"
    )
    document.getElementById("arrivals-display").innerText = (
        f"Arrivals this round: {region.arrivals_this_round():.0f} people "
        f"(background severity: {region.background_severity:.1f})"
    )
    document.getElementById("total-arrivals-display").innerText = (
        f"Total arrivals (lifetime): {region.total_arrivals:.0f} people"
    )
    document.getElementById("strain-display").innerText = (
        f"Strain: {region.strain_fraction() * 100:.0f}% ({region.strain_level()})"
    )
    document.getElementById("strain-bar").style.width = f"{region.strain_fraction() * 100:.0f}%"

    document.getElementById("integrated-display").innerText = (
        f"Integrated: {region.integrated_population:.0f} people "
        f"(contributing {region.integration_contribution():.0f} funds/round)"
    )
    document.getElementById("pending-display").innerText = (
        f"Pending integration: {region.pending_population():.0f} people"
    )

    document.getElementById("service-quality-display").innerText = (
        f"Service quality: {region.service_quality():.0f}"
    )
    document.getElementById("economic-health-display").innerText = (
        f"Economic health: {region.economic_health():.0f}"
    )
    document.getElementById("social-cohesion-display").innerText = (
        f"Social cohesion: {region.social_cohesion():.0f}"
    )
    document.getElementById("wellbeing-display").innerText = (
        f"Wellbeing score: {region.wellbeing_score():.0f}"
    )
    document.getElementById("wellbeing-message-display").innerText = wellbeing_message(
        region.wellbeing_score()
    )

    for capacity_type in CAPACITY_TYPES:
        document.getElementById(f"{capacity_type}-name").innerText = (
            f"{CAPACITY_ICON[capacity_type]} {CAPACITY_LABEL[capacity_type]}"
        )
        document.getElementById(f"{capacity_type}-count").innerText = (
            f"{region.capacity[capacity_type]:.0f}"
        )
        button = document.getElementById(f"{capacity_type}-invest-button")
        button.innerText = f"{CAPACITY_LABEL[capacity_type]} ({INVEST_COST[capacity_type]:.0f})"
        button.disabled = region.funds < INVEST_COST[capacity_type]


def on_advance_round(event=None):
    region.advance_round()
    render()


def _make_invest_handler(capacity_type):
    def handler(event=None):
        region.invest(capacity_type)
        render()
    return handler


def setup():
    document.getElementById("advance-round-button").addEventListener(
        "click", create_proxy(on_advance_round)
    )
    for capacity_type in CAPACITY_TYPES:
        document.getElementById(f"{capacity_type}-invest-button").addEventListener(
            "click", create_proxy(_make_invest_handler(capacity_type))
        )
    render()


setup()
