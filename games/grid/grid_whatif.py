"""The career what-if strategies (replaying a run under canned strategies) and the Career panel's what-if rows.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

try:
    from js import document
except ImportError:
    document = None

from grid_rules import (
    AGE_GRACE_PERIOD, CAREER_MIN_ROUNDS, FOSSIL_TYPES, GENERATION_TYPES, PLANT_CAPACITY, RENEWABLE_TYPES,
)
from grid_state import GridState


# C-3 -- the post-run "what if" analyzer. Because every random draw of a run comes from the run's
# seed (see SEED_GAME), a finished run can be replayed on a fresh grid with the same seed, scenario,
# toggles and loadout under three canned strategies and see how each would have ended, facing the
# same weather and disruption rolls. The strategies are simple bots, not optimal play: they are
# there to show what a different philosophy would have cost or earned.
WHATIF_STRATEGIES = [
    ("renewables_early", "All-renewable early"),
    ("no_retire", "Never retire, grow with fossil"),
    ("storage_first", "Storage first"),
]
WHATIF_MAX_ROUNDS = 100
WHATIF_BUILDS_PER_ROUND = 12


def _whatif_grid(source):
    grid = GridState()
    grid.seed = source.seed
    grid.perks = set(source.perks)
    grid.start_option = source.start_option
    grid.steeper_demand_growth_enabled = source.steeper_demand_growth_enabled
    grid.weather_variability_enabled = source.weather_variability_enabled
    grid.apply_scenario(source.scenario)
    return grid


def _cost_per_capacity(grid, plant_type):
    return grid.plant_cost(plant_type) / PLANT_CAPACITY[plant_type]


def _whatif_build_toward(grid, candidates):
    """Build the cheapest-per-capacity candidate while capacity is short of next round's demand."""
    target = grid.demand + grid.demand_growth_this_round()
    for _ in range(WHATIF_BUILDS_PER_ROUND):
        if grid.total_capacity() >= target:
            return
        pick = min(candidates, key=lambda t: _cost_per_capacity(grid, t))
        if not grid.build_plant(pick):
            return


def _whatif_upkeep(grid):
    oldest = grid.oldest_vulnerable_plant()
    if oldest is not None and grid.plant_age[oldest] >= AGE_GRACE_PERIOD:
        if grid.funds >= grid.maintenance_cost(oldest) * 3:
            grid.maintain_plant(oldest)


def _whatif_turn(grid, key):
    if grid.policy_lever_available:
        if key == "no_retire":
            grid.decline_policy()
        else:
            grid.enact_policy("renewable_subsidy")
    if grid.grant_offer is not None:
        grid.decline_grant()
    _whatif_upkeep(grid)
    renewables = [t for t in GENERATION_TYPES if t in RENEWABLE_TYPES]
    if key == "no_retire":
        # Business as usual: keep every plant and meet new demand with the cheapest fossil capacity.
        _whatif_build_toward(grid, list(FOSSIL_TYPES))
        return
    if key == "storage_first" and grid.cumulative_built["battery"] == 0:
        grid.build_plant("battery")
    if key == "renewables_early" and grid.round_number >= 3:
        # Retire a fossil unit once the rest of the fleet still covers demand without it.
        for fossil in ("coal", "gas"):
            if grid.plant_counts[fossil] > 0 and grid.total_capacity() - PLANT_CAPACITY[fossil] >= grid.demand:
                grid.retire_plant(fossil)
                break
    _whatif_build_toward(grid, renewables)
    if key == "storage_first" and grid.plant_counts["battery"] > 0:
        grid.set_arbitrage_mode("discharge" if grid.total_capacity() < grid.demand else "charge")


def simulate_strategy(source, key, rounds):
    """Replay `rounds` rounds of the run `source` (a GridState) under one canned strategy."""
    grid = _whatif_grid(source)
    for _ in range(max(0, min(rounds, WHATIF_MAX_ROUNDS))):
        _whatif_turn(grid, key)
        grid.advance_round()
    return {
        "id": key,
        "grade": grid.benchmark_grade() or "F",
        "funds": max(0, int(round(grid.funds))),
        "score": round(grid.score(), 1),
    }


def what_if_results(source):
    """The three what-if rows for a run, or [] when it is too short to count."""
    rounds = source.round_number - 1
    if rounds < CAREER_MIN_ROUNDS:
        return []
    return [simulate_strategy(source, key, rounds) for key, _label in WHATIF_STRATEGIES]


def career_whatif_rows(record):
    """(label, grade, funds, score) rows: the run itself first, then each strategy."""
    if record is None or not record.get("whatif"):
        return []
    labels = dict(WHATIF_STRATEGIES)
    rows = [("You", record["grade"], record["funds"], record["score"])]
    for entry in record["whatif"]:
        rows.append((labels[entry["id"]], entry["grade"], entry["funds"], entry["score"]))
    return rows


def career_whatif_verdict(record):
    rows = career_whatif_rows(record)
    if not rows:
        return "Finish a run of at least 5 rounds and the same seed is replayed here under three other strategies."
    order = "ABCDF"
    best = min(rows, key=lambda r: (order.index(r[1]), -r[3], -r[2]))
    if best[0] == "You":
        return "Your own play beat all three canned strategies on grade and clean score."
    return f"{best[0]} would have done best: grade {best[1]}, clean score {best[3]:.0f}/100, final funds {best[2]}."


def render_career_whatif(history):
    container = document.getElementById("career-whatif")
    verdict_el = document.getElementById("career-whatif-verdict")
    container.innerHTML = ""
    latest = next((r for r in reversed(history) if r.get("whatif")), None)
    verdict_el.innerText = career_whatif_verdict(latest)
    if latest is None:
        return
    seed_note = f" (seed {latest['seed']})" if latest.get("seed") else ""
    head = document.createElement("div")
    head.className = "shadow-row shadow-row--head"
    for text in (f"Strategy{seed_note}", "Grade", "Funds", "Clean score"):
        cell = document.createElement("span")
        cell.innerText = text
        head.appendChild(cell)
    container.appendChild(head)
    for label, grade, funds, score in career_whatif_rows(latest):
        line = document.createElement("div")
        line.className = "shadow-row"
        for text in (label, grade, str(funds), f"{score:.0f}/100"):
            cell = document.createElement("span")
            cell.innerText = text
            line.appendChild(cell)
        container.appendChild(line)
