"""Continuum — city simulation core.

Milestone 1 of Phase 1. This module is the settlement engine: population,
resources, worker allocation, buildings, production, consumption, and the
land-health feedback loop. It is deliberately free of DOM code, of scoring
code, and of research code — `game.py` owns the browser, `sustainability.py`
owns the score, `research.py` owns the tree. Keeping those apart is the
tech note the design doc is most insistent about, since seven eras' worth
of content lands on top of this file.

Two properties are load-bearing for everything that comes later:

1. **Deterministic.** No RNG anywhere in the season loop. Every number a
   season produces is a pure function of the state that went into it, which
   is what makes both testing and the save system's era-snapshot/revisit
   behaviour tractable.
2. **Effects-driven.** Every yield, capacity and rate is multiplied through
   an `effects` dict (see `NEUTRAL_EFFECTS`). Milestone 1 always passes the
   neutral one; Milestone 3's research tree passes an aggregate of the
   player's researched nodes. Building that seam in from the start is what
   stops the research tree from having to reach into the simulation later.

Tribal (Phase 1), Agrarian (Milestone 8), Classical (Milestone 9),
Medieval (Milestone 10), Industrial (Milestone 11) and Digital (Milestone
12) are modelled so far. Era-specific constants live in per-era tables
keyed by era id (see ERA_ROLES/ERA_BUILDINGS) so each remaining era adds a
table entry rather than a second copy of this file — Agrarian's own
Farmers role and Farmland building were the first proof that pattern
actually extends cleanly rather than requiring a rewrite; Classical's
Administrators/Canals extend it a second time, this time with a building
whose bonus depends on the role rather than merely being multiplied by it
(see CANAL_YIELD_BONUS); Medieval's Guildmasters/Public Works extend it a
third time, this time with a building that isn't staffed at all — Public
Works is read only by sustainability.py, not by the production math below
(see PUBLIC_WORKS_COVERAGE_PER_BUILDING). Industrial's Factory Workers/
Sanitation Works extend it a fourth time, and this is the first era where
the new content has a GROWTH-side mechanical consequence, not only a
sustainability-score one: Factory Workers produce `pollution`, a lagged
stock read directly by the population-growth step below (see the
"pollution and industrial growth cost" section), grounded in
continuum-real-world-sources.md's Economic Journal source showing
industrial pollution measurably reducing long-run city growth historically
— see CLAUDE.md's Milestone 11 build notes for the full reasoning.
Digital's Urban Planners/Transit Hubs extend it a fifth time, and this era's
own growth-side consequence deliberately takes a DIFFERENT shape from
Industrial's: instead of a second direct multiplier on GROWTH_RATE,
`state.sprawl` (also a lagged 0..1 stock, produced by unmanaged population
growth per the National Geographic source on urban areas outgrowing their
populations) amplifies how much land pressure the settlement's existing
extraction already creates — reusing the land_health/GROWTH_MIN_LAND_HEALTH
machinery Phase 1 already built rather than stacking a second bespoke
growth-rate lever alongside pollution's. See CLAUDE.md's Milestone 12 build
notes for the full reasoning.

Space Age (Milestone 13) extends it a sixth and FINAL time, and is
deliberately NOT a seventh copy of the growth-vs-extraction shape every
prior era used. Per CLAUDE.md's Milestone 13 build notes, "post-scarcity
off-world infrastructure" changes the KIND of question this era asks, not
just its numbers: Habitat Architects and Habitat Rings never touch
production, growth, or extraction at all. Instead they determine
`habitat_capacity()` — how much of the population is actually served WELL
by the settlement's off-world ring-habitat layout, per the Dagstuhl/
SpaceCHI source's "usability... at scale" framing — which sustainability.py
reads as a brand-new fourth PROVISION (alongside food/shelter/culture) from
Space Age on, not as a bolt-on penalty/bonus function the way every prior
era's adjustment was. This is the game's first era-specific mechanic to
live in `livability()`/`equity()`'s own shared plumbing rather than beside
it.

The Relay Age (R2-K26, the eighth era) is the first era after that "final"
one, and it changes the shape a THIRD way: it is the game's first REGIONAL
mechanic. Space Age's habitat rings are one site; the Relay Age links that
site to a ring of outlying holdings (surface hinterland, orbital platforms,
the first off-world footholds) through Relay Stations and the Wayfinders who
run them. The holdings' residents are part of the population, but they live
at the far end of a supply line: what Relay Stations move is banked trade
`surplus` (the stock that has, until now, only ever been an equity risk if
hoarded), out to the holdings, every season. A holding that is kept supplied
opens up new sustainable land yield for the whole settlement; one that is
not leaves the network worse off than not expanding at all. See
`CityState.holdings_residents()` and the "regional relay network" comment
block below, and CLAUDE.md's "R2-K26: the eighth era (Relay Age)" section.
"""

import continuum_sim_tables
import continuum_sim_numbers
import continuum_sim_city

# sim.py is the public face of the simulation: everything lives in the three parts above (tables, numbers, CityState, in that
# dependency order) and is re-exported here, so `sim.CityState`, `sim.ERA_ORDER`, `sim.GROWTH_RATE` ... work exactly as before.
for _part in (continuum_sim_tables, continuum_sim_numbers, continuum_sim_city):
    for _name, _value in vars(_part).items():
        if not _name.startswith("__"):
            globals()[_name] = _value
del _part, _name, _value
