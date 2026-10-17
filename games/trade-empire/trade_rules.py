"""Fixed numbers and content tables: goods, colonies and their flavour, needs, specialisations, temperaments, plus the plain constants other modules share. No browser calls, no state."""


TICK_INTERVAL_MS = 1000
TRAVEL_TICKS = 5
CARGO_CAPACITY = 10

ORE = "ore"
GRAIN = "grain"
MACHINERY = "machinery"
WATER = "water"
ENERGY = "energy"

# Milestone 13 — the Kepler Cluster's own goods, distinct from the home
# system's five so colony_needing()/colony_producing() stay single-
# valued across the whole galaxy without any good ever being wanted or
# made by two colonies at once.
RARE_METALS = "rare_metals"
BIOMASS = "biomass"
ISOTOPES = "isotopes"

# J13 — the Rift Colonies, a third self-contained triangle gated behind
# "Outer Reaches" (itself gated behind Galaxy Expansion). Same reasoning
# as Kepler's own goods: a third, non-overlapping namespace keeps
# colony_needing()/colony_producing() single-valued fleet-wide with zero
# special-casing.
CRYSTAL = "crystal"
POLYMER = "polymer"
ANTIMATTER = "antimatter"

# J1 — the Umbral Deep, a fourth self-contained triangle gated behind a
# two-step research chain (Deep Survey, then Umbral Reach) that costs more
# than anything before it. Its goods are again a brand-new, non-overlapping
# namespace, and priced above every earlier tier.
NEUTRONIUM = "neutronium"
SUPERFLUID = "superfluid"
AEROGEL = "aerogel"

GOOD_LABEL = {
    ORE: "Ore", GRAIN: "Grain", MACHINERY: "Machinery", WATER: "Water", ENERGY: "Energy",
    RARE_METALS: "Rare Metals", BIOMASS: "Biomass", ISOTOPES: "Isotopes",
    CRYSTAL: "Crystal", POLYMER: "Polymer", ANTIMATTER: "Antimatter",
    NEUTRONIUM: "Neutronium", SUPERFLUID: "Superfluid", AEROGEL: "Aerogel",
}

# Flat per-unit base sell price, before Milestone 4's market multiplier.
SELL_PRICE = {
    ORE: 8, GRAIN: 6, MACHINERY: 10, WATER: 5, ENERGY: 9,
    RARE_METALS: 14, BIOMASS: 8, ISOTOPES: 18,
    CRYSTAL: 20, POLYMER: 12, ANTIMATTER: 26,
    NEUTRONIUM: 34, SUPERFLUID: 24, AEROGEL: 16,
}

# Milestone 2: a third colony turned the fixed A<->B pair into a real
# triangle (Aurum's ore feeds Ferrum, Ferrum's machinery feeds Verdant,
# Verdant's grain feeds Aurum). Milestone 5 adds a second pair (Cryo and
# Helion each need exactly what the other produces) purely to add scale
# — more colonies and routes for the existing ships to manage, not a
# new mechanic. Every ship can already reach every colony, so this
# alone measurably increases how busy manual play gets.
COLONIES = {
    "aurum": {"name": "Aurum Station", "produces": ORE, "needs": GRAIN},
    "verdant": {"name": "Verdant Reach", "produces": GRAIN, "needs": MACHINERY},
    "ferrum": {"name": "Ferrum Forge", "produces": MACHINERY, "needs": ORE},
    "cryo": {"name": "Cryo Vault", "produces": WATER, "needs": ENERGY},
    "helion": {"name": "Helion Array", "produces": ENERGY, "needs": WATER},
}

# Milestone 13 — the Kepler Cluster: a second system, reachable only
# once "galaxy_expansion" is researched. Its own closed three-good
# triangle, exactly like the home system's original one, so it's fully
# self-sufficient in isolation -- the cross-system link only appears
# once a Kepler colony develops (see SECONDARY_NEED below).
EXPANSION_COLONIES = {
    "kepler_a": {"name": "Kepler Alpha", "produces": RARE_METALS, "needs": BIOMASS},
    "kepler_b": {"name": "Kepler Beta", "produces": BIOMASS, "needs": ISOTOPES},
    "kepler_c": {"name": "Kepler Gamma", "produces": ISOTOPES, "needs": RARE_METALS},
}

# J13 — a third system, the Rift Colonies, gated behind "Outer Reaches"
# (which itself requires Galaxy Expansion first) -- same self-contained
# triangle shape as Kepler, just one tier further out. No new mechanic,
# same deliberate "more of what already exists" scope call Milestone 5
# made for the home system's own second pair.
RIFT_COLONIES = {
    "rift_a": {"name": "Rift Colony Alpha", "produces": CRYSTAL, "needs": ANTIMATTER},
    "rift_b": {"name": "Rift Colony Beta", "produces": ANTIMATTER, "needs": POLYMER},
    "rift_c": {"name": "Rift Colony Gamma", "produces": POLYMER, "needs": CRYSTAL},
}

# J1 — a fourth system, the Umbral Deep, gated behind "Umbral Reach"
# (which requires "Deep Survey", which requires Outer Reaches). Same
# self-contained triangle shape as the two clusters before it -- no new
# mechanic, just one more tier further out. Deliberately not sharing a
# name prefix (unlike "Kepler ..."/"Rift Colony ..."), so the map's default
# first-word label is already unique without an override.
DEEP_COLONIES = {
    "deep_a": {"name": "Nadir Foundry", "produces": NEUTRONIUM, "needs": SUPERFLUID},
    "deep_b": {"name": "Hush Cryostat", "produces": SUPERFLUID, "needs": AEROGEL},
    "deep_c": {"name": "Tenebra Loom", "produces": AEROGEL, "needs": NEUTRONIUM},
}

# All colony metadata, every system -- used for lookups that must stay
# correct regardless of what's unlocked (colony_needing(),
# colony_producing(), labels). Which of these are actually *reachable*
# right now is a separate question, answered by active_colony_ids().
ALL_COLONIES = {**COLONIES, **EXPANSION_COLONIES, **RIFT_COLONIES, **DEEP_COLONIES}

# Milestone 3 — minor flavor text per colony, shown in the colony panel.
COLONY_FLAVOR = {
    "aurum": "A wind-scoured mining outpost — good ore, poor soil. Every grain shipment matters.",
    "verdant": "Lush terraces feed the sector, but its factories run on imported machinery.",
    "ferrum": "The forges never stop, but they run on ore that has to come from somewhere else.",
    "cryo": "A frozen moon's ice reserves, tapped for water — but the pumps need power to run at all.",
    "helion": "A solar array with power to spare, and nothing to cool it but water shipped in from Cryo.",
    "kepler_a": "A newly-charted asteroid belt rich in rare metals — reaching it took the galaxy expansion, and running it still does.",
    "kepler_b": "Vast hydroponic vaults growing biomass for the whole cluster — an engineered ecology this far out, not a natural one.",
    "kepler_c": "Fusion research yards refining isotopes — infrastructure that only exists this far from the core because the expansion made it worth building.",
    "rift_a": "A crystal-lattice quarry at the edge of charted space — Outer Reaches is the only reason a ship can reach it at all.",
    "rift_b": "A containment yard breeding antimatter in vanishingly small, carefully metered batches.",
    "rift_c": "A polymer refinery running on feedstock that has to be shipped in from somewhere else in the Rift.",
    "deep_a": "A foundry working scraps of collapsed star into neutronium, under a sky with nothing in it. Every hour of supply it gets is an hour of light it doesn't have.",
    "deep_b": "A cryostat holding helium at temperatures where it stops behaving like a liquid at all. Aerogel lining is the difference between working and not.",
    "deep_c": "Looms spinning aerogel inside neutronium-lined pressure vessels. The output is almost weightless; getting the vessels here was not.",
}

# Milestone 3 — colony need system v1: each colony's need_satisfaction
# (0..1) decays steadily and is topped up when a ship delivers the
# colony's needed good. Output scales with it — a well-supplied colony
# produces meaningfully more per load than a neglected one, so "keep
# the loop fed" becomes a real incentive, not just flavor text.
STARTING_NEED_SATISFACTION = 0.5
NEED_DECAY_PER_TICK = 0.01
NEED_SATISFACTION_PER_UNIT_DELIVERED = 0.05
# At satisfaction 0.0 a colony produces at half capacity; at 1.0, one
# and a half times — the starting 0.5 satisfaction matches today's flat
# CARGO_CAPACITY exactly, so Milestone 1/2 balance is the neutral point.
MIN_OUTPUT_MULTIPLIER = 0.5
MAX_OUTPUT_MULTIPLIER = 1.5

# Milestone 9 — evolving needs v2: sustained delivery of a colony's
# primary need develops it further, and development expands what it
# needs rather than ever "finishing" it — a second, cross-cycle need on
# top of the first, per the plan's "no final solved state per colony"
# framing. A colony's own secondary need deliberately reaches into the
# *other* need-cycle (the original triangle vs. the Cryo/Helion pair),
# so growth creates new dependencies linking the two clusters together
# rather than just deepening the one a colony already belongs to.
DEVELOPMENT_THRESHOLD = 100.0
SECONDARY_NEED = {
    "aurum": ENERGY,
    "verdant": WATER,
    "ferrum": ENERGY,
    "cryo": ORE,
    "helion": GRAIN,
    # Milestone 13 — a developed Kepler colony's secondary need reaches
    # all the way back into the home system, the same "links what was
    # previously separate" move Milestone 9 made within one system,
    # applied across the newly-opened distance between two.
    "kepler_a": ENERGY,
    "kepler_b": ORE,
    "kepler_c": WATER,
    # J13 — the Rift Colonies' own secondary need reaches back one tier,
    # into the Kepler Cluster, the same "links what was previously
    # separate" move applied one system further out.
    "rift_a": RARE_METALS,
    "rift_b": BIOMASS,
    "rift_c": ISOTOPES,
    # J1 — the Umbral Deep's secondary need reaches back one tier again,
    # into the Rift Colonies' goods.
    "deep_a": ANTIMATTER,
    "deep_b": CRYSTAL,
    "deep_c": POLYMER,
}

# Milestone 10 — colony specialization: distinct strengths/weaknesses
# per colony, reflecting the environment/history each one's flavor text
# already establishes (Aurum's harsh mining outpost earns the strongest
# output bonus and pays for it with the steepest decay; Verdant's easy,
# fertile terraces earn the mildest of each). Environmental, not a
# player choice — it activates automatically once a colony develops
# (Milestone 9's development_level >= 2), rather than being a separate
# unlock system of its own.
SPECIALIZATION = {
    "aurum": {
        "name": "Mining Powerhouse", "output_bonus": 0.25, "decay_multiplier": 1.6,
        "description": "+25% ore output; needs decay 60% faster (harsh, remote environment)",
    },
    "verdant": {
        "name": "Fertile Terraces", "output_bonus": 0.15, "decay_multiplier": 1.2,
        "description": "+15% grain output; needs decay 20% faster (easy growing conditions)",
    },
    "ferrum": {
        "name": "Forge World", "output_bonus": 0.20, "decay_multiplier": 1.4,
        "description": "+20% machinery output; needs decay 40% faster (single-purpose economy)",
    },
    "cryo": {
        "name": "Ice Miner", "output_bonus": 0.20, "decay_multiplier": 1.5,
        "description": "+20% water output; needs decay 50% faster (isolated, power-starved)",
    },
    "helion": {
        "name": "Solar Titan", "output_bonus": 0.15, "decay_multiplier": 1.3,
        "description": "+15% energy output; needs decay 30% faster (nothing grows there)",
    },
    "kepler_a": {
        "name": "Deep-Core Extractor", "output_bonus": 0.20, "decay_multiplier": 1.5,
        "description": "+20% rare metals output; needs decay 50% faster (unforgiving frontier belt)",
    },
    "kepler_b": {
        "name": "Hydroponic Vaults", "output_bonus": 0.15, "decay_multiplier": 1.2,
        "description": "+15% biomass output; needs decay 20% faster (engineered, well-tended ecology)",
    },
    "kepler_c": {
        "name": "Fusion Yards", "output_bonus": 0.20, "decay_multiplier": 1.4,
        "description": "+20% isotopes output; needs decay 40% faster (high-maintenance research infrastructure)",
    },
    "rift_a": {
        "name": "Lattice Quarry", "output_bonus": 0.25, "decay_multiplier": 1.6,
        "description": "+25% crystal output; needs decay 60% faster (edge-of-map, barely supplied)",
    },
    "rift_b": {
        "name": "Containment Yard", "output_bonus": 0.20, "decay_multiplier": 1.5,
        "description": "+20% antimatter output; needs decay 50% faster (a small batch is already a lot to keep stable)",
    },
    "rift_c": {
        "name": "Feedstock Refinery", "output_bonus": 0.20, "decay_multiplier": 1.4,
        "description": "+20% polymer output; needs decay 40% faster (every input is imported)",
    },
    # J1 — the highest-reward, highest-maintenance profiles in the game:
    # the furthest colonies pay the most and are the hardest to keep fed.
    "deep_a": {
        "name": "Collapsed-Star Smelter", "output_bonus": 0.30, "decay_multiplier": 1.7,
        "description": "+30% neutronium output; needs decay 70% faster (no sunlight, no margin for error)",
    },
    "deep_b": {
        "name": "Absolute-Zero Works", "output_bonus": 0.25, "decay_multiplier": 1.6,
        "description": "+25% superfluid output; needs decay 60% faster (the cold only holds while it is being tended)",
    },
    "deep_c": {
        "name": "Weightless Looms", "output_bonus": 0.25, "decay_multiplier": 1.5,
        "description": "+25% aerogel output; needs decay 50% faster (delicate output, heavy-duty inputs)",
    },
}


# J19 -- colony loyalty. A colony left chronically under-served (need
# satisfaction below NEGLECT_THRESHOLD for NEGLECT_DEMAND_TICKS in a row)
# makes a one-time concession demand. Granting it costs CONCESSION_COST
# credits and restores CONCESSION_SATISFACTION_BOOST of need satisfaction;
# ignoring it costs nothing, the demand simply lapses after
# DEMAND_WINDOW_TICKS and can only come back after DEMAND_COOLDOWN_TICKS.
# It's an offer that rewards attention, never a punishment.
NEGLECT_THRESHOLD = 0.25
NEGLECT_DEMAND_TICKS = 40
DEMAND_WINDOW_TICKS = 30
DEMAND_COOLDOWN_TICKS = 60
CONCESSION_COST = 80
CONCESSION_SATISFACTION_BOOST = 0.3


# J-25 -- colony temperaments. Each colony's mood follows its trade history
# (see ColonyState.temperament()) and changes how it treats the player:
# Grateful colonies pay a small premium on sales delivered there, Demanding
# ones answer a granted concession more strongly, and Opportunistic ones (the
# starting mood) take an Invest at a discount while their need is low. Nothing
# is ever marked down, so the base economy only moves up.
TEMPERAMENT_COUNT_MAX = 1_000_000
TEMPERAMENT_MARK = {"circle": "\u25cf", "triangle": "\u25b2", "square": "\u25a0"}
GRATEFUL_DELIVERED = 50.0
DEMANDING_LAPSED_DEMANDS = 2
DEFAULT_TEMPERAMENT = "opportunistic"
OPPORTUNIST_INVEST_DISCOUNT = 0.75
OPPORTUNIST_NEED_BELOW = 0.5
TEMPERAMENTS = {
    "grateful": {
        "label": "Grateful", "glyph": "circle", "premium": 0.04, "concession_boost": CONCESSION_SATISFACTION_BOOST,
        "why": "well supplied, so it pays +4% on every sale delivered there",
    },
    "demanding": {
        "label": "Demanding", "glyph": "triangle", "premium": 0.0, "concession_boost": 0.45,
        "why": "two demands went unanswered, but a granted concession now restores 45% satisfaction",
    },
    "opportunistic": {
        "label": "Opportunistic", "glyph": "square", "premium": 0.0, "concession_boost": CONCESSION_SATISFACTION_BOOST,
        "why": "new or undecided, and it takes an Invest at a 25% discount whenever its need is under 50%",
    },
}


# Milestone 6 — automation v1: a limited number of ships can be bought
# into fully autonomous operation. An automated ship loads whatever its
# current colony produces and departs for whichever colony needs it,
# every tick, with no further input — "a route can run itself." Slots
# are capped and each one costs real profit, so automating the whole
# fleet at once isn't free or immediate.
AUTOMATION_COST = 150


# J6 — a 5th/6th purchasable ship. Both exist from module load (so
# get_state()/load_state()'s existing generic per-ship loops need no
# special-casing) but start unpurchased/hidden behind a one-time credit
# cost -- SHIP_PURCHASE_COST below, enforced by can_purchase_ship()/
# purchase_ship() and Ship.load()/depart()'s own "purchased" guard.
# Sequential: the 6th requires the 5th already bought, same "one tier at
# a time" shape as the research tree's own prerequisite edges.
PURCHASABLE_SHIP_IDS = ("5", "6")

TRADE_POST_COST = 400
TRADE_POST_INCOME_PER_TICK = 2


# J7 -- colony investment: spend credits to push an undeveloped colony
# toward its Level 2 development (the same progress deliveries build),
# so surplus credits can accelerate growth and specialization. It costs
# more per unit than the credits a delivery earns, so it speeds a colony up
# without replacing supplying it. Repeatable until the colony is developed.
COLONY_INVEST_COST = 60


# Milestone 14 — endgame: a soft win-state, not a stopping point. Once
# the fleet is fully automated, Fleet Priority is switched on, and the
# Kepler Cluster is unlocked, the player has built exactly what the
# game's whole arc was pointing at -- a self-running, multi-system
# economy. Rather than literally simulating "hundreds of worlds" as
# real per-colony DOM/state (impractical, and not actually more
# meaningful to look at than a handful of well-simulated ones), that
# scale is narrated as an abstracted, ever-growing background galaxy
# that the player's own pattern has visibly spread to -- a deliberate,
# documented scope cut in favor of a satisfying number over a hollow
# multiplication of unreachable colonies.
ENDGAME_BACKGROUND_WORLD_CAP = 500
ENDGAME_BACKGROUND_WORLDS_PER_TICK = 2
ENDGAME_BACKGROUND_REVENUE_PER_WORLD = 0.4

GUILD_FIRST_OFFER_TICKS = 40
GUILD_COOLDOWN_TICKS = 60  # quiet time after a contract resolves or lapses

GUILD_REWARD_MULTIPLIER = 1.6  # bonus credits = units x current price x this
