"""Continuum -- Z-18: the practice sandbox's rules (no DOM).

A sandbox settlement is a separate `save.Campaign`, so the player's real settlement is never touched
(game.py points its module-level `campaign`/`state`/`tree`/`chronicle` at this one while the sandbox is
on, then back). The rules:

- every research node is already known, so every tool of every era is open;
- the player picks the era to practise in (`new_campaign(era)`), with a ready-made small town for it;
- resources are not binding: after every season `relief()` tops food, materials, tools and knowledge up;
- no collapse: `relief()` also keeps the land, pollution and sprawl in a livable range, keeps everybody
  fed and housed, and never lets the population fall below `MIN_PEOPLE`, so the score never reaches the
  collapse line and `dynasty.is_collapsed()` can never be true;
- nothing is banked, filed or posted from here (game.py guards every storage write and board report).

Everything is deterministic, like the rest of the engine.
"""

import sim

SANDBOX_POPULATION = 40
MIN_PEOPLE = 20
MATERIALS_FLOOR = 400.0
TOOLS_FLOOR = 25.0
KNOWLEDGE_FLOOR = 400.0
LAND_FLOOR = 0.6
POLLUTION_CEILING = 0.35
SPRAWL_CEILING = 0.35
SHELTER_FLOOR = 10


def era_choices():
    return list(sim.ERA_ORDER)


def clean_era(era):
    return era if era in sim.ERA_ORDER else sim.FIRST_ERA


def _starting_town(state, era):
    """A small, balanced town for the era: every building the era has, some people in every job."""
    roles = sim.roles_for_era(era)
    buildings = sim.buildings_for_era(era)
    state.population = SANDBOX_POPULATION
    for key in state.buildings:
        state.buildings[key] = 0
    for key in buildings:
        state.buildings[key] = 2
    state.buildings["shelter"] = SHELTER_FLOOR
    state.buildings["granary"] = 3
    for key in state.allocation:
        state.allocation[key] = 0
    per_role = max(1, SANDBOX_POPULATION // (len(roles) + 1))
    for role in roles:
        state.allocation[role] = per_role
    state.clamp_allocation()


def new_campaign(era, save_module=None):
    """A fresh sandbox campaign in `era` with every research node known."""
    import save

    era = clean_era(era)
    campaign = (save_module or save).Campaign()
    state = campaign.state
    state.era = era
    campaign.furthest_era = era
    campaign.tree.current_era = era
    campaign.tree.restore(list(campaign.tree.nodes))
    _starting_town(state, era)
    state.fed_fraction = 1.0
    state.land_health = 1.0
    campaign.ui = {}
    relief(state, campaign.tree.effects())
    campaign.log.bootstrap(state, campaign.tree, campaign.tree.effects())
    return campaign


def relief(state, effects=None):
    """Called after every season in the sandbox (and once at the start): makes resources non-binding and the
    settlement impossible to collapse. Changes only stocks and floors, never the rules themselves."""
    effects = effects if effects is not None else sim.NEUTRAL_EFFECTS
    resources = state.resources
    resources["materials"] = max(resources["materials"], MATERIALS_FLOOR)
    resources["tools"] = max(resources["tools"], TOOLS_FLOOR)
    resources["knowledge"] = max(resources["knowledge"], KNOWLEDGE_FLOOR)
    resources["food"] = max(resources["food"], state.food_storage_capacity(effects))
    state.land_health = max(state.land_health, LAND_FLOOR)
    state.pollution = min(state.pollution, POLLUTION_CEILING)
    state.sprawl = min(state.sprawl, SPRAWL_CEILING)
    state.fed_fraction = 1.0
    state.population = max(state.population, MIN_PEOPLE)
    # Enough shelter for everyone, so overcrowding can never drag the score down.
    while state.housing_capacity(effects) < state.population and state.buildings["shelter"] < 10_000:
        state.buildings["shelter"] += 1
    return state
