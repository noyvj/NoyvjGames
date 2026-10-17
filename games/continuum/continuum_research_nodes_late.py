"""Research nodes, part 3 of 3: Space Age, Relay Age and the late-tier expansion nodes (K21b).
Part of the split of the old single-file research.py: see "File map" in games/continuum/CLAUDE.md.
"""

from continuum_research_tree import ResearchNode, era_tiers


_NODES_SPACE_TO_END = [
    # --- Space Age, early (Milestone 13) --- Three nodes, one per branch,
    # each chaining a prerequisite back into the LATE Digital tier (tier 12)
    # of the same branch — the same "early tier of a new era chains to the
    # late tier of the one before it" pattern Milestones 8-12 all used, now
    # proven across a sixth (and final) era boundary. Unlike every prior
    # era's early trio, none of these three touch a growth/extraction/
    # pollution-style effect key at all -- per CLAUDE.md's Milestone 13
    # build notes, Space Age's mechanic is deliberately NOT a seventh copy
    # of that shape, so its research content follows suit.
    ResearchNode(
        "modular_habitat_design",
        "Modular Habitat Design",
        era="space",
        tier=era_tiers("space")[0],
        branch="craft",
        cost=145.0,
        prerequisites=("transit_oriented_design",),
        effects={"habitat_layout_bonus": 0.2},
        blurb=(
            "Transit-Oriented Design was the last lesson learned about arranging a city around how "
            "people actually move through it while there was still a city around it to arrange. Out "
            "here there's no surrounding city to lean on — only whatever the module's own layout "
            "provides, from the first ring built."
        ),
    ),
    ResearchNode(
        "closed_loop_life_support",
        "Closed-Loop Life Support",
        era="space",
        tier=era_tiers("space")[0],
        branch="provision",
        cost=145.0,
        prerequisites=("circular_resource_systems",),
        effects={"extraction_efficiency": -0.15, "regen_mult": 0.1},
        blurb=(
            "Circular Resource Systems taught the settlement to need less in the first place; this "
            "closes the loop the rest of the way, because out here there is no 'away' left for "
            "anything to spoil into, and no untouched land waiting somewhere else to make up the "
            "difference."
        ),
    ),
    ResearchNode(
        "settlers_compact",
        "Settlers' Compact",
        era="space",
        tier=era_tiers("space")[0],
        branch="community",
        cost=155.0,
        prerequisites=("digital_commons_charter",),
        min_affinity={"community": 11},
        effects={"equity_bonus": 0.1, "habitat_layout_bonus": 0.1},
        blurb=(
            "Every charter before this one assumed a city that already existed to be governed. This "
            "is the first one written for people who have to agree on how a place should work before "
            "the place has finished being built at all. Only reachable by a settlement that kept "
            "investing in community across seven eras running now."
        ),
    ),
    # --- Space Age, late ---
    ResearchNode(
        "space_syntax_planning",
        "Space Syntax Planning",
        era="space",
        tier=era_tiers("space")[1],
        branch="craft",
        cost=170.0,
        prerequisites=("modular_habitat_design",),
        effects={"habitat_layout_bonus": 0.25},
        blurb=(
            "A formal discipline for reading how a layout's own geometry shapes whether people can "
            "actually find, use, and gather in the spaces built for them — Modular Habitat Design "
            "gave the settlement rings to build; this is what tells it whether any given ring will "
            "actually work before the mistake is load-bearing."
        ),
    ),
    ResearchNode(
        "full_cycle_reclamation",
        "Full-Cycle Reclamation",
        era="space",
        tier=era_tiers("space")[1],
        branch="provision",
        cost=170.0,
        prerequisites=("closed_loop_life_support",),
        effects={"extraction_efficiency": -0.2, "materials_yield_mult": 0.15},
        blurb=(
            "The end of a line that started with Seasonal Rounds noticing the land needed rest "
            "between harvests. Closed-Loop Life Support kept almost everything moving through the "
            "loop instead of out of it; this is the settlement finally needing almost nothing from "
            "outside itself at all."
        ),
    ),
    ResearchNode(
        "off_world_founding_charter",
        "Off-World Founding Charter",
        era="space",
        tier=era_tiers("space")[1],
        branch="community",
        cost=190.0,
        prerequisites=("settlers_compact",),
        min_affinity={"community": 12},
        effects={"equity_bonus": 0.1, "resilience_bonus": 0.1},
        blurb=(
            "Settlers' Compact was the first draft, written under pressure, before anyone knew "
            "whether it would hold. This is the settlement deciding it did, and writing down why — "
            "the same instinct Elders' Council had, seven eras and one entire world ago. Only "
            "reachable by a settlement that kept investing in community across all seven eras of its "
            "whole history."
        ),
    ),
    # --- Relay Age, early (R2-K26) --- Three nodes, one per branch, each
    # chaining a prerequisite back into the LATE Space Age tier (tier 14) of
    # the same branch -- the same "early tier of a new era chains to the late
    # tier of the one before it" pattern every earlier era used, now across a
    # seventh era boundary. Their effects are about the relay network
    # (throughput, surplus, and the equity of the holdings), not a new growth
    # stock.
    ResearchNode(
        "relay_route_surveying",
        "Relay Route Surveying",
        era="relay",
        tier=era_tiers("relay")[0],
        branch="craft",
        cost=210.0,
        prerequisites=("space_syntax_planning",),
        effects={"relay_bonus": 0.25},
        blurb=(
            "Space Syntax Planning read how a layout shapes the people inside it; this reads the "
            "same thing one scale up, at the level of the routes between places. Where a link "
            "runs, and how often anything moves along it, decides whether a holding at the far "
            "end is a settlement or an afterthought."
        ),
    ),
    ResearchNode(
        "regional_surplus_exchange",
        "Regional Surplus Exchange",
        era="relay",
        tier=era_tiers("relay")[0],
        branch="provision",
        cost=210.0,
        prerequisites=("full_cycle_reclamation",),
        effects={"surplus_conversion_bonus": 0.2, "food_yield_mult": 0.1},
        blurb=(
            "Full-Cycle Reclamation stopped anything leaving the loop; this opens the loop to a "
            "region. A standing arrangement to bank what one site over-produces so another can "
            "draw on it - the oldest idea in the tree, surplus, put to work across distance."
        ),
    ),
    ResearchNode(
        "regional_compact",
        "Regional Compact",
        era="relay",
        tier=era_tiers("relay")[0],
        branch="community",
        cost=225.0,
        prerequisites=("off_world_founding_charter",),
        min_affinity={"community": 13},
        effects={"equity_bonus": 0.1, "relay_bonus": 0.1},
        blurb=(
            "Every charter so far governed one place. This one governs the relationship between "
            "places: what the core owes the holdings that were founded from it, and what they owe "
            "back. Only reachable by a settlement that kept investing in community across every "
            "era it has lived through."
        ),
    ),
    # --- Relay Age, late ---
    ResearchNode(
        "autonomous_hauling",
        "Autonomous Hauling",
        era="relay",
        tier=era_tiers("relay")[1],
        branch="craft",
        cost=250.0,
        prerequisites=("relay_route_surveying",),
        effects={"relay_bonus": 0.3, "tool_yield_mult": 0.1},
        blurb=(
            "Relay Route Surveying decided where the links run; this puts machines on them, so "
            "that carrying a season's supplies to a holding stops depending on how many people "
            "the core can spare to do it."
        ),
    ),
    ResearchNode(
        "closed_supply_loops",
        "Closed Supply Loops",
        era="relay",
        tier=era_tiers("relay")[1],
        branch="provision",
        cost=250.0,
        prerequisites=("regional_surplus_exchange",),
        effects={"surplus_conversion_bonus": 0.2, "extraction_efficiency": -0.15},
        blurb=(
            "The holdings stop being a place the core sends things to and start being part of the "
            "loop: what they grow and reclaim comes back along the same links. A region that needs "
            "less from any one place is a region that leans less on the land at home."
        ),
    ),
    ResearchNode(
        "federated_holdings_charter",
        "Federated Holdings Charter",
        era="relay",
        tier=era_tiers("relay")[1],
        branch="community",
        cost=270.0,
        prerequisites=("regional_compact",),
        min_affinity={"community": 14},
        effects={"equity_bonus": 0.1, "resilience_bonus": 0.1},
        blurb=(
            "The Regional Compact settled what the core owes; this gives the holdings a standing "
            "voice in deciding it. The last charter in the tree, and, like Elders' Council at the "
            "very start of it, a group of people deciding that being counted is not optional."
        ),
    ),
    # --- K21b: late-tier expansion (Milestone 25) --- Nine extra nodes, one or
    # two per era from Agrarian on, all in each era's LATE tier (early tiers
    # stay at exactly three nodes, one per branch, which several era tests
    # pin). Each chains into a node already in that era, so the tree grows
    # sideways (more choices per tier) without opening a new gate.
    ResearchNode(
        "storehouse_rotation",
        "Storehouse Rotation",
        era="agrarian",
        tier=era_tiers("agrarian")[1],
        branch="provision",
        cost=22.0,
        prerequisites=('crop_rotation',),
        effects={'food_storage_bonus': 25.0, 'surplus_conversion_bonus': 0.1},
        blurb='Grain moved through the stores in turn, oldest first, so less of a good harvest is lost before anyone eats it.',
    ),
    ResearchNode(
        "civic_records",
        "Civic Records",
        era="classical",
        tier=era_tiers("classical")[1],
        branch="community",
        cost=36.0,
        prerequisites=('temple_administration',),
        effects={'knowledge_mult': 0.15, 'equity_bonus': 0.04},
        blurb="Who owes what, who holds which plot, what was promised. Written down once, so it no longer depends on anyone's memory or goodwill.",
    ),
    ResearchNode(
        "almshouses",
        "Almshouses",
        era="medieval",
        tier=era_tiers("medieval")[1],
        branch="community",
        cost=52.0,
        prerequisites=('municipal_charter',),
        effects={'resilience_bonus': 0.08, 'equity_bonus': 0.05},
        blurb='A roof and a meal for people who can no longer work for either. The town starts to count its weakest members as its own concern.',
    ),
    ResearchNode(
        "tenement_reform",
        "Tenement Reform",
        era="industrial",
        tier=era_tiers("industrial")[1],
        branch="community",
        cost=80.0,
        prerequisites=('factory_acts',),
        effects={'housing_bonus': 8.0, 'equity_bonus': 0.05},
        blurb="Minimum room sizes, windows, and a water tap per building. The mill's neighbours are finally allowed to live somewhere that is not just cheap.",
    ),
    ResearchNode(
        "materials_recovery",
        "Materials Recovery",
        era="industrial",
        tier=era_tiers("industrial")[1],
        branch="provision",
        cost=78.0,
        prerequisites=('steam_power',),
        effects={'materials_yield_mult': 0.1, 'extraction_efficiency': -0.08, 'pollution_output_mult': -0.1},
        blurb='Scrap sorted and fed back in instead of dumped. The works needs less from the ground and leaves less behind.',
    ),
    ResearchNode(
        "open_data_portals",
        "Open Data Portals",
        era="digital",
        tier=era_tiers("digital")[1],
        branch="community",
        cost=105.0,
        prerequisites=('participatory_planning',),
        effects={'knowledge_mult': 0.25, 'equity_bonus': 0.04},
        blurb="The settlement's own numbers, published where anyone can read and question them. A planning decision now has to survive being checked.",
    ),
    ResearchNode(
        "urban_farms_and_green_roofs",
        "Urban Farms & Green Roofs",
        era="digital",
        tier=era_tiers("digital")[1],
        branch="provision",
        cost=110.0,
        prerequisites=('smart_utilities',),
        effects={'food_yield_mult': 0.15, 'regen_mult': 0.1},
        blurb='Food grown on rooftops and vacant lots, close to where it is eaten. Less of the surrounding land is asked to do all the work.',
    ),
    ResearchNode(
        "orbital_agronomy",
        "Orbital Agronomy",
        era="space",
        tier=era_tiers("space")[1],
        branch="provision",
        cost=165.0,
        prerequisites=('closed_loop_life_support',),
        effects={'food_yield_mult': 0.2, 'regen_mult': 0.1},
        blurb='Crops bred for narrow light, recycled water and no weather at all. The habitat feeds itself on a schedule it sets.',
    ),
    ResearchNode(
        "habitat_commons",
        "Habitat Commons",
        era="space",
        tier=era_tiers("space")[1],
        branch="community",
        cost=175.0,
        prerequisites=('settlers_compact',),
        effects={'equity_bonus': 0.08, 'habitat_layout_bonus': 0.1},
        blurb='Shared space designed in from the first ring rather than left over. Where people meet becomes a thing the layout is built around.',
    ),
]
