"""Thaw — Permafrost Feedback Loop Game.

Runs in-browser via Pyodide. Milestone 1: the background trajectory and
core loop — global temperature rises on a fixed schedule each round,
independent of the player, while the player allocates regional resources
across output/preserve/monitor. The permafrost melt + methane feedback
loop (the entire point of this game) lands in Milestone 2.
"""

from js import document
from pyodide.ffi import create_proxy

STARTING_FUNDS = 300.0

CATEGORIES = ["output", "preserve", "monitor"]

CATEGORY_LABEL = {
    "output": "Output",
    "preserve": "Permafrost Preservation",
    "monitor": "Monitoring & Response",
}

INVEST_COST = {
    "output": 20,
    "preserve": 25,
    "monitor": 20,
}

OUTPUT_INCOME_PER_UNIT = 6

# Global temperature rises this much every round, no matter what the
# player does — it's a background trajectory, not something the player
# directly drives. This is the thing that makes Thaw different from
# Herd/Grid: the player isn't the primary cause of the central meter.
BASE_TEMP_RISE_PER_ROUND = 1.0

# Permafrost melt + methane feedback: once temperature crosses this
# threshold, melt releases methane that ADDS to next round's rise —
# warming causes melt causes more warming. This is the entire lesson of
# the game: a slow, linear problem tipping into a runaway one.
MELT_THRESHOLD = 10.0
FEEDBACK_RATE_PER_DEGREE_OVER = 0.15

# Intervention: preserve/monitor investment dampens the FEEDBACK
# contribution only — never the background BASE_TEMP_RISE_PER_ROUND,
# which stays outside player control by design. "A real lever that
# measurably slows the loop, even if it can't fully stop the background
# trajectory" — the plan's hope-angle requirement, made literal.
DAMPENING_PER_PRESERVE_UNIT = 0.08
DAMPENING_PER_MONITOR_UNIT = 0.04
MAX_FEEDBACK_DAMPENING = 0.85


class RegionState:
    def __init__(self):
        self.round_number = 1
        self.funds = STARTING_FUNDS
        self.capacity = {c: 0 for c in CATEGORIES}
        self.temperature = 0.0
        self.melt_started_round = None
        # A parallel, fully undampened trajectory — same background rise,
        # same feedback mechanics, but zero intervention ever. The gap
        # between this and the real temperature is the hope-angle payoff.
        self.counterfactual_temperature = 0.0

    def invest(self, category):
        cost = INVEST_COST[category]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.capacity[category] += 1
        return True

    def is_melting(self):
        return self.temperature >= MELT_THRESHOLD

    def feedback_dampening_fraction(self):
        total = (
            self.capacity["preserve"] * DAMPENING_PER_PRESERVE_UNIT
            + self.capacity["monitor"] * DAMPENING_PER_MONITOR_UNIT
        )
        return min(MAX_FEEDBACK_DAMPENING, total)

    def feedback_bonus(self):
        """Extra warming this round from methane released by permafrost
        melt — zero until the melt threshold is crossed, then grows with
        how far past it the temperature has climbed. Intervention
        investment dampens this, never the background rise itself."""
        excess = max(0.0, self.temperature - MELT_THRESHOLD)
        raw_bonus = excess * FEEDBACK_RATE_PER_DEGREE_OVER
        return raw_bonus * (1 - self.feedback_dampening_fraction())

    def current_rise_rate(self):
        return BASE_TEMP_RISE_PER_ROUND + self.feedback_bonus()

    def advance_round(self):
        self.funds += self.capacity["output"] * OUTPUT_INCOME_PER_UNIT
        current_round = self.round_number
        self.temperature += self.current_rise_rate()
        if self.melt_started_round is None and self.is_melting():
            self.melt_started_round = current_round

        counterfactual_excess = max(0.0, self.counterfactual_temperature - MELT_THRESHOLD)
        counterfactual_rate = BASE_TEMP_RISE_PER_ROUND + (
            counterfactual_excess * FEEDBACK_RATE_PER_DEGREE_OVER
        )
        self.counterfactual_temperature += counterfactual_rate

        self.round_number += 1

    def temperature_saved(self):
        """The hope-angle payoff, as a direct number: how much lower
        temperature is right now than the fully-undampened counterfactual
        trajectory would have reached by this round."""
        return self.counterfactual_temperature - self.temperature

    def trajectory_message(self):
        saved = self.temperature_saved()
        if saved <= 0.01:
            return "No meaningful difference from intervention yet."
        return (
            f"Early intervention has kept warming {saved:.1f}° lower than an "
            f"unmitigated trajectory would have reached by now."
        )

    def acceleration_factor(self):
        """How many times faster than the background baseline warming is
        rising right now — 1.0x when stable, growing once melt kicks in."""
        return self.current_rise_rate() / BASE_TEMP_RISE_PER_ROUND

    def acceleration_message(self):
        if not self.is_melting():
            return "Warming is rising at a steady, linear rate."
        return (
            f"Warming has accelerated to {self.acceleration_factor():.1f}x the background "
            f"rate since permafrost began melting in round {self.melt_started_round}."
        )


region = RegionState()


def render():
    document.getElementById("round-display").innerText = f"Round {region.round_number}"
    document.getElementById("funds-display").innerText = f"Funds: {region.funds:.0f}"
    document.getElementById("temperature-display").innerText = (
        f"Global temperature: +{region.temperature:.1f}°"
    )
    document.getElementById("rise-rate-display").innerText = (
        f"Current warming rate: {region.current_rise_rate():.2f}°/round"
    )
    document.getElementById("melt-status-display").innerText = (
        "Permafrost is actively melting — methane feedback is accelerating warming."
        if region.is_melting()
        else "Permafrost stable — no feedback yet."
    )
    document.getElementById("dampening-display").innerText = (
        f"Feedback dampening: {region.feedback_dampening_fraction() * 100:.0f}%"
    )
    document.getElementById("acceleration-display").innerText = region.acceleration_message()
    document.getElementById("acceleration-bar").style.width = (
        f"{min(1.0, (region.acceleration_factor() - 1) / 2) * 100:.0f}%"
    )
    document.getElementById("trajectory-display").innerText = region.trajectory_message()

    for category in CATEGORIES:
        document.getElementById(f"{category}-count").innerText = str(region.capacity[category])
        invest_button = document.getElementById(f"{category}-invest-button")
        invest_button.innerText = f"Invest ({INVEST_COST[category]})"
        invest_button.disabled = region.funds < INVEST_COST[category]


def _make_invest_handler(category):
    def handler(event=None):
        region.invest(category)
        render()
    return handler


def on_advance_round(event=None):
    region.advance_round()
    render()


def setup():
    for category in CATEGORIES:
        document.getElementById(f"{category}-invest-button").addEventListener(
            "click", create_proxy(_make_invest_handler(category))
        )
    document.getElementById("advance-round-button").addEventListener(
        "click", create_proxy(on_advance_round)
    )
    render()


setup()
