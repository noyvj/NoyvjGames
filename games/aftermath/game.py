"""Aftermath — Climate Adaptation & Resilience Game.

Runs in-browser via Pyodide. Milestone 1: the single-run core loop — a
fixed schedule of extreme weather events, resource allocation between
events (resilience vs. growth investment), and damage resolution.
Run scoring, the persistent skill tree, and cross-run comparisons land
in later milestones.
"""

from js import document
from pyodide.ffi import create_proxy

STARTING_RESOURCES = 200.0

RESILIENCE_COST = 25
GROWTH_COST = 20
GROWTH_INCOME_PER_UNIT = 8

RESILIENCE_MITIGATION_PER_UNIT = 0.05
MAX_MITIGATION = 0.85

# Fixed schedule — every run faces the same sequence of event types, so
# runs are comparable to each other (needed for Milestone 5's "how far
# you've come" comparison).
EVENT_SCHEDULE = ["flood", "heatwave", "storm", "flood", "storm"]

EVENT_LABEL = {
    "flood": "Flood",
    "heatwave": "Heatwave",
    "storm": "Storm",
}

EVENT_BASE_DAMAGE = {
    "flood": 40.0,
    "heatwave": 35.0,
    "storm": 50.0,
}


class RunState:
    def __init__(self):
        self.event_index = 0
        self.resources = STARTING_RESOURCES
        self.resilience_capacity = 0
        self.growth_capacity = 0
        self.damage_taken = 0.0
        self.event_log = []

    def is_complete(self):
        return self.event_index >= len(EVENT_SCHEDULE)

    def next_event_type(self):
        if self.is_complete():
            return None
        return EVENT_SCHEDULE[self.event_index]

    def invest_resilience(self):
        if self.resources < RESILIENCE_COST:
            return False
        self.resources -= RESILIENCE_COST
        self.resilience_capacity += 1
        return True

    def invest_growth(self):
        if self.resources < GROWTH_COST:
            return False
        self.resources -= GROWTH_COST
        self.growth_capacity += 1
        return True

    def mitigation_fraction(self):
        return min(MAX_MITIGATION, self.resilience_capacity * RESILIENCE_MITIGATION_PER_UNIT)

    def resolve_next_event(self):
        """Applies growth income, then resolves the next scheduled event's
        damage (reduced by resilience mitigation). No-op once the run is
        complete."""
        if self.is_complete():
            return False

        self.resources += self.growth_capacity * GROWTH_INCOME_PER_UNIT

        event_type = EVENT_SCHEDULE[self.event_index]
        damage = EVENT_BASE_DAMAGE[event_type] * (1 - self.mitigation_fraction())
        self.resources = max(0.0, self.resources - damage)
        self.damage_taken += damage
        self.event_log.append({"type": event_type, "damage": damage})
        self.event_index += 1
        return True


run = RunState()


def render():
    document.getElementById("resources-display").innerText = f"Resources: {run.resources:.0f}"
    document.getElementById("resilience-display").innerText = f"Resilience: {run.resilience_capacity}"
    document.getElementById("growth-display").innerText = f"Growth: {run.growth_capacity}"

    if run.is_complete():
        document.getElementById("progress-display").innerText = "Run complete"
        document.getElementById("next-event-display").innerText = "No more events this run."
    else:
        document.getElementById("progress-display").innerText = (
            f"Event {run.event_index + 1} of {len(EVENT_SCHEDULE)}"
        )
        document.getElementById("next-event-display").innerText = (
            f"Next: {EVENT_LABEL[run.next_event_type()]}"
        )

    resilience_button = document.getElementById("resilience-invest-button")
    resilience_button.innerText = f"Invest in Resilience ({RESILIENCE_COST})"
    resilience_button.disabled = run.resources < RESILIENCE_COST or run.is_complete()

    growth_button = document.getElementById("growth-invest-button")
    growth_button.innerText = f"Invest in Growth ({GROWTH_COST})"
    growth_button.disabled = run.resources < GROWTH_COST or run.is_complete()

    resolve_button = document.getElementById("resolve-event-button")
    resolve_button.disabled = run.is_complete()


def on_invest_resilience(event=None):
    run.invest_resilience()
    render()


def on_invest_growth(event=None):
    run.invest_growth()
    render()


def on_resolve_event(event=None):
    run.resolve_next_event()
    render()


def setup():
    document.getElementById("resilience-invest-button").addEventListener(
        "click", create_proxy(on_invest_resilience)
    )
    document.getElementById("growth-invest-button").addEventListener(
        "click", create_proxy(on_invest_growth)
    )
    document.getElementById("resolve-event-button").addEventListener(
        "click", create_proxy(on_resolve_event)
    )
    render()


setup()
