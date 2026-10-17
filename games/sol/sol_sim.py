"""The per-tick simulation of one world: Governor step, incoming trade restore and _simulate_planet."""

import sol_runstate as runstate
from sol_charter import stamp_bonus
from sol_doctrines import _doctrine_step
from sol_econ import (
    _yield_multiplier, generator_cost, production_multiplier, recycler_cost, terraform_rate,
    update_ecology_display, update_generator_display,
)
from sol_observatory import rival_pressure
from sol_rules import (
    ECOLOGY_MAX, PLANETS, SPECIALIZATION_OUTPUT_BONUS, SPECIALIZATION_OUTPUT_DECAY_PENALTY,
    SPECIALIZATION_STABILITY_DECAY_CUT, TERRAFORM_MAX, TICK_INTERVAL_MS, TRADE_ROUTE_RESTORE_PER_SEC,
    _sandbox_active, _specialization, governor_settings, planet_state, prestige_has,
)
from sol_runmods import (
    MUTATOR_BLIND_BUDGET_CAP, MUTATOR_ONE_WAY_FACTOR, MUTATOR_THIN_DECAY_FACTOR, anomaly_factor,
    megaproject_factor, mutator_active, sky_city_bonus_per_city,
)
from sol_scarcity import scarcity_decay, scarcity_yield
from sol_util import clamp


# --- Prestige / New Game+ (A1) ---


def governor_step():
    # Autonomously manages every real economy the player is currently NOT
    # on, using the shared priority/budget config — e.g. while on Earth,
    # Mars is governed; while on Mars or any undeveloped body, Earth (and
    # Mars, if that's not where the player is either) keeps running. This
    # loop is already N-planet generic: it governs everything in PLANETS
    # except current_planet, however many real economies that ends up being.
    governed_planets = [planet for planet in PLANETS if planet != runstate.current_planet]
    if not governed_planets:
        return

    runstate.governor_tick_count += 1

    for planet in governed_planets:
        if _sandbox_active():
            continue  # A15: costs are zero in sandbox, so the Governor would buy without limit
        if _doctrine_step(planet):
            continue  # A-7: a Doctrine rule paused the Governor's own buying here
        # A7: each world may carry its own personality preset; otherwise it
        # follows the global dial exactly as before.
        priority, budget_pct = governor_settings(planet)
        if mutator_active("blind_governor"):
            priority, budget_pct = "balance", min(budget_pct, MUTATOR_BLIND_BUDGET_CAP)
        if priority == "growth":
            buy_generator_turn = True
        elif priority == "ecology":
            buy_generator_turn = False
        else:  # "balance" — alternate turns between the two buildings
            buy_generator_turn = runstate.governor_tick_count % 2 == 0
        state = planet_state[planet]
        budget = state["resource_count"] * (budget_pct / 100)

        if buy_generator_turn:
            cost = generator_cost(planet)
            if cost <= budget:
                state["resource_count"] -= cost
                state["generator_count"] += 1
                runstate.governor_purchase_count += 1
                runstate.lifetime_generators_built += 1
                runstate.any_generator_ever_built = True
                if not runstate._dry_run:
                    update_generator_display(planet)
        else:
            cost = recycler_cost(planet)
            if cost <= budget:
                state["resource_count"] -= cost
                state["recycler_count"] += 1
                runstate.governor_purchase_count += 1
                runstate.lifetime_recyclers_built += 1
                if not runstate._dry_run:
                    update_ecology_display(planet)


def _incoming_trade_restore(planet):
    # Sums contributions from every OTHER real economy that has routes
    # targeting this planet — generic over however many senders exist,
    # not just a single hardcoded partner.
    total = 0.0
    for sender in PLANETS:
        if sender == planet:
            continue
        count = planet_state[sender]["trade_routes"].get(planet, 0)
        total += count * TRADE_ROUTE_RESTORE_PER_SEC * (TICK_INTERVAL_MS / 1000)
    if mutator_active("one_way_trade"):
        total *= MUTATOR_ONE_WAY_FACTOR
    return total * anomaly_factor("trade") * (1 - rival_pressure(planet))


def _simulate_planet(planet, incoming_trade_restore):
    cfg = PLANETS[planet]
    state = planet_state[planet]

    if state["generator_count"] > 0:
        multiplier = production_multiplier(planet)
        if multiplier > 0:
            # Sky City bonus (Milestone 10): a no-op multiplier of exactly 1
            # on planets without the sky city keys (the other six planets).
            sky_city_bonus = 1 + sky_city_bonus_per_city(planet) * state.get("sky_city_count", 0)
            spec = _specialization(planet)
            produced = (
                state["generator_count"]
                * cfg["generator_rate"]
                * sky_city_bonus
                * (TICK_INTERVAL_MS / 1000)
                * multiplier
                * _yield_multiplier()
                * anomaly_factor("produce")
                * megaproject_factor("produce")
                * (1 + stamp_bonus(planet))
                * scarcity_yield(planet)
                * (1 + SPECIALIZATION_OUTPUT_BONUS if spec == "output" else 1)
                * (1.2 if prestige_has("governors_mandate") and planet != runstate.current_planet else 1)
            )
            state["resource_count"] += produced
            runstate.lifetime_resources_generated_by_automation += produced
            # A11: only counts as "governed" (generated while away) when this
            # ISN'T the planet the player is currently standing on -- the
            # Governor Report panel's whole point is showing what happened
            # elsewhere while you were busy somewhere else.
            if planet != runstate.current_planet:
                state["governed_resource_generated"] += produced

    decay = state["generator_count"] * cfg["ecology_decay_per_generator_per_sec"] * (TICK_INTERVAL_MS / 1000)
    if prestige_has("eco_conscious"):
        decay *= 0.85
    if mutator_active("thin_atmosphere"):
        decay *= MUTATOR_THIN_DECAY_FACTOR
    decay *= anomaly_factor("decay")
    decay *= scarcity_decay()
    spec = _specialization(planet)
    if spec == "output":
        decay *= 1 + SPECIALIZATION_OUTPUT_DECAY_PENALTY
    elif spec == "stability":
        decay *= 1 - SPECIALIZATION_STABILITY_DECAY_CUT
    restore = state["recycler_count"] * cfg["recycler_restore_per_sec"] * (TICK_INTERVAL_MS / 1000) * anomaly_factor("recycle") * megaproject_factor("recycle")
    state["ecology_health"] = clamp(
        state["ecology_health"] - decay + restore + incoming_trade_restore, 0.0, ECOLOGY_MAX
    )

    state["terraform_progress"] = clamp(
        state["terraform_progress"] + terraform_rate(planet) * (TICK_INTERVAL_MS / 1000),
        0.0,
        TERRAFORM_MAX,
    )
