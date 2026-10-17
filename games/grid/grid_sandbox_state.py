"""The practice sandbox's grid (SandboxGridState) and its balance sliders (Z-18, C-27). Entering and leaving the sandbox
needs render() and get_state(), so those functions live in grid_handlers_play.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import skill_tree

from grid_rules import (
    CAREER_TREE, CAREER_UNLOCK_ORDER, DEMAND_GROWTH_PER_ROUND, EMERGENCY_HOLD_ROUNDS,
    MAX_AGE_BREAKDOWN_PROBABILITY, RD_GRANT_DECAY, REVENUE_PER_UNIT_MET, SCENARIOS,
)
from grid_state import GridState


# --- Z-18: the practice sandbox -------------------------------------------------------------------
# An opt-in mode with no fail states, every tool open and the real game and its achievements left
# alone. The rules, in one place:
#   - unlimited funds (the balance never drops below SANDBOX_FUNDS, so every build, maintenance pass and
#     demand-response purchase is free);
#   - no disruptions, no aging breakdowns, no surprise grants or fines and an emergency that cannot be
#     missed: nothing the player does can break the grid;
#   - every upgrade-tree node is switched on (loadouts, peek forecast, cheaper builds and upkeep), and the
#     starting scenario can be changed at any time (which starts the sandbox grid over);
#   - the real game is set aside whole (see sandbox_enter) and put back unchanged on leaving.
# The sandbox grid is a separate SandboxGridState object, so nothing it does can touch the real one.
SANDBOX_FUNDS = 1_000_000
# C-27: the balance sliders. Each moves one number of the sandbox grid (never a real run): how fast renewables get
# cheaper per unit built, how likely an aging breakdown is (as a percentage of the real game's chance; 0 is the sandbox's
# usual "nothing breaks"), how far demand grows each round and what a unit of demand met earns.
SANDBOX_BALANCE = {
    "cost_decay": {"label": "Renewable cost multiplier per unit built", "min": 0.85, "max": 1.0, "step": 0.01, "format": "{:.2f}"},
    "breakdown": {"label": "Breakdown chance, % of the real game's", "min": 0.0, "max": 300.0, "step": 10.0, "format": "{:.0f}%"},
    "growth": {"label": "Demand growth per round", "min": 0.0, "max": 30.0, "step": 1.0, "format": "{:.0f}"},
    "revenue": {"label": "Revenue per unit of demand met", "min": 0.0, "max": 6.0, "step": 0.5, "format": "{:.1f}"},
}
SANDBOX_BALANCE_DEFAULTS = {
    "cost_decay": RD_GRANT_DECAY, "breakdown": 0.0, "growth": float(DEMAND_GROWTH_PER_ROUND),
    "revenue": float(REVENUE_PER_UNIT_MET),
}
SANDBOX_ALL_PERKS = frozenset(skill_tree.effects(CAREER_TREE, CAREER_UNLOCK_ORDER))


class SandboxGridState(GridState):
    """A grid that cannot fail: see the Z-18 note above."""

    sandbox = True

    def __init__(self):
        super().__init__()
        self.balance = dict(SANDBOX_BALANCE_DEFAULTS)
        self.breakdown_scale = 0.0

    def set_balance(self, key, value):
        """C-27: moves one balance slider (clamped to its range). Returns the value now in force, or None for an
        unknown key or a value that is not a number."""
        spec = SANDBOX_BALANCE.get(key)
        if spec is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number != number or number in (float("inf"), float("-inf")):
            return None
        number = min(spec["max"], max(spec["min"], number))
        self.balance[key] = number
        if key == "cost_decay":
            # The usual value leaves the normal rule alone (the R&D grant is on in the sandbox, so 0.94).
            default = SANDBOX_BALANCE_DEFAULTS["cost_decay"]
            self.cost_decay_override = None if abs(number - default) < 1e-9 else number
        elif key == "growth":
            self.base_demand_growth = number
        elif key == "revenue":
            self.revenue_per_unit = number
        elif key == "breakdown":
            self.breakdown_scale = number / 100.0
        return number

    @property
    def funds(self):
        return self._funds

    @funds.setter
    def funds(self, value):
        self._funds = max(float(value), float(SANDBOX_FUNDS))

    def disruption_probability(self):
        return 0.0

    def aging_breakdown_probability(self):
        if self.breakdown_scale <= 0:
            return 0.0
        return min(MAX_AGE_BREAKDOWN_PROBABILITY, super().aging_breakdown_probability() * self.breakdown_scale)

    def breakdown_risk_probability(self, plant_type):
        if self.breakdown_scale <= 0:
            return 0.0
        return min(MAX_AGE_BREAKDOWN_PROBABILITY, super().breakdown_risk_probability(plant_type) * self.breakdown_scale)

    def _maybe_offer_grant(self, round_played):
        return None

    def _update_emergency(self):
        """The emergency scenario can still be stabilized, but its clock never runs out."""
        em = self.emergency
        if em is None or em["status"] != "active":
            return
        em["hold"] = em["hold"] + 1 if self.total_capacity() >= self.demand else 0
        if em["hold"] >= EMERGENCY_HOLD_ROUNDS:
            em["status"] = "stabilized"


def new_sandbox_state(scenario_id="standard", balance=None):
    """A fresh sandbox grid on the given starting scenario, with every perk on (and, when a scenario change starts the
    practice grid over, the balance sliders carried across)."""
    fresh = SandboxGridState()
    fresh.perks = set(SANDBOX_ALL_PERKS)
    for key, value in (balance or {}).items():
        fresh.set_balance(key, value)
    fresh.apply_scenario(scenario_id if scenario_id in SCENARIOS else "standard")
    return fresh
