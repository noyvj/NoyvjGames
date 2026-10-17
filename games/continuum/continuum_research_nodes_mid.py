"""Research nodes, part 2 of 3: Medieval, Industrial and Digital (early and late tiers).
Part of the split of the old single-file research.py: see "File map" in games/continuum/CLAUDE.md.
"""

from continuum_research_tree import ResearchNode, era_tiers


_NODES_MEDIEVAL_TO_DIGITAL = [
    # --- Medieval, early (Milestone 10) --- Three nodes, one per branch,
    # each chaining a prerequisite back into the LATE Classical tier
    # (tier 6) of the same branch — the same "early tier of a new era
    # chains to the late tier of the one before it" pattern Milestones 8-9
    # both used, now proven across a third era boundary rather than being
    # a one-off or a two-off.
    ResearchNode(
        "guild_workshops",
        "Guild Workshops",
        era="medieval",
        tier=era_tiers("medieval")[0],
        branch="craft",
        cost=42.0,
        prerequisites=("monumental_masonry",),
        effects={"tool_yield_mult": 0.2},
        blurb=(
            "A trade taught the same way twice, by people who do nothing else. Monumental Masonry "
            "raised the walls this city stands behind; this is who keeps everything inside them running."
        ),
    ),
    ResearchNode(
        "trade_zoning",
        "Zoned Trades",
        era="medieval",
        tier=era_tiers("medieval")[0],
        branch="provision",
        cost=42.0,
        prerequisites=("trade_networks",),
        effects={"extraction_efficiency": -0.1},
        blurb=(
            "Tanning, dyeing, slaughtering — kept downstream and downwind of the water everyone "
            "drinks, by rule rather than by luck. Trade Networks still reaches just as far; it simply "
            "doesn't run through the well anymore."
        ),
    ),
    ResearchNode(
        "municipal_charter",
        "Municipal Charter",
        era="medieval",
        tier=era_tiers("medieval")[0],
        branch="community",
        cost=45.0,
        prerequisites=("civic_assembly",),
        min_affinity={"community": 5},
        effects={"public_works_bonus": 0.25},
        blurb=(
            "A right to govern its own affairs, granted rather than assumed — Civic Assembly's open "
            "decisions become the settlement's own to make, including what it chooses to build against "
            "a bad season before one arrives. Only reachable by a settlement that kept investing in "
            "community across four eras running now."
        ),
    ),
    # --- Medieval, late ---
    ResearchNode(
        "master_guilds",
        "Master Guilds",
        era="medieval",
        tier=era_tiers("medieval")[1],
        branch="craft",
        cost=50.0,
        prerequisites=("guild_workshops",),
        effects={"tool_yield_mult": 0.2, "housing_bonus": 4.0},
        blurb=(
            "A guild hall is a workshop and a meeting place both — Guild Workshops taught the trade; "
            "this is where the trade governs itself, sets its own standards, and houses whoever it "
            "trains."
        ),
    ),
    ResearchNode(
        "public_sanitation",
        "Public Sanitation",
        era="medieval",
        tier=era_tiers("medieval")[1],
        branch="provision",
        cost=50.0,
        prerequisites=("trade_zoning",),
        effects={"regen_mult": 0.15, "extraction_efficiency": -0.1},
        blurb=(
            "Waste fines and a clean well are the same policy seen from two different ends. Zoned "
            "Trades kept the worst of it away from the water; this is what actually keeps the water "
            "clean."
        ),
    ),
    ResearchNode(
        "free_city_charter",
        "Free City Charter",
        era="medieval",
        tier=era_tiers("medieval")[1],
        branch="community",
        cost=55.0,
        prerequisites=("municipal_charter",),
        min_affinity={"community": 6},
        effects={"equity_bonus": 0.1, "public_works_bonus": 0.15},
        blurb=(
            "Self-governance made permanent rather than granted anew each generation. Municipal "
            "Charter proved the settlement could run itself for a while; this is the settlement "
            "deciding it always will."
        ),
    ),
    # --- Industrial, early (Milestone 11) --- Three nodes, one per branch,
    # each chaining a prerequisite back into the LATE Medieval tier (tier 8)
    # of the same branch — the same "early tier of a new era chains to the
    # late tier of the one before it" pattern Milestones 8-10 all used, now
    # proven across a fourth era boundary rather than being a one-off, a
    # two-off, or a three-off.
    ResearchNode(
        "smoke_abatement",
        "Smoke Abatement",
        era="industrial",
        tier=era_tiers("industrial")[0],
        branch="craft",
        cost=60.0,
        prerequisites=("master_guilds",),
        effects={"pollution_output_mult": -0.15, "tool_yield_mult": 0.1},
        blurb=(
            "The same guild discipline Master Guilds trained into every workshop, turned toward "
            "what a factory throws off rather than only what it makes. Less smoke per worker, not "
            "fewer workers."
        ),
    ),
    ResearchNode(
        "steam_power",
        "Steam Power",
        era="industrial",
        tier=era_tiers("industrial")[0],
        branch="provision",
        cost=60.0,
        prerequisites=("public_sanitation",),
        effects={"materials_yield_mult": 0.2},
        blurb=(
            "A furnace turning water into force instead of just heat. Public Sanitation kept the "
            "water clean; this is what the settlement does with the water once it's boiling."
        ),
    ),
    ResearchNode(
        "factory_acts",
        "Factory Acts",
        era="industrial",
        tier=era_tiers("industrial")[0],
        branch="community",
        cost=65.0,
        prerequisites=("free_city_charter",),
        min_affinity={"community": 7},
        effects={"equity_bonus": 0.1, "resilience_bonus": 0.05},
        blurb=(
            "Rules on hours, age, and conditions, won rather than granted — the self-governance "
            "Free City Charter made permanent is what makes rules like this enforceable at all. "
            "Only reachable by a settlement that kept investing in community across five eras "
            "running now."
        ),
    ),
    # --- Industrial, late ---
    ResearchNode(
        "sanitation_engineering",
        "Sanitation Engineering",
        era="industrial",
        tier=era_tiers("industrial")[1],
        branch="craft",
        cost=75.0,
        prerequisites=("smoke_abatement",),
        effects={"pollution_output_mult": -0.15, "sanitation_bonus": 0.25},
        blurb=(
            "Smoke Abatement cut what a workshop throws off at the source; this is the drains, "
            "filters and waste systems built to actually absorb what's left, at the scale a "
            "factory floor produces it."
        ),
    ),
    ResearchNode(
        "assembly_lines",
        "Assembly Lines",
        era="industrial",
        tier=era_tiers("industrial")[1],
        branch="provision",
        cost=75.0,
        prerequisites=("steam_power",),
        effects={"materials_yield_mult": 0.3},
        blurb=(
            "Work broken into repeatable steps instead of one worker doing all of it. Steam Power "
            "gave the settlement the force; this is what actually multiplies it."
        ),
    ),
    ResearchNode(
        "public_health_acts",
        "Public Health Acts",
        era="industrial",
        tier=era_tiers("industrial")[1],
        branch="community",
        cost=85.0,
        prerequisites=("factory_acts",),
        min_affinity={"community": 8},
        effects={"equity_bonus": 0.1, "sanitation_bonus": 0.15},
        blurb=(
            "Slums and disease made public, and made the settlement's own problem to solve rather "
            "than each household's alone — the real historical hinge that modern urban planning as "
            "a discipline grew out of. Factory Acts protected the worker; this is what protects "
            "the neighborhood they go home to."
        ),
    ),
    # --- Digital, early (Milestone 12) --- Three nodes, one per branch,
    # each chaining a prerequisite back into the LATE Industrial tier
    # (tier 10) of the same branch — the same "early tier of a new era
    # chains to the late tier of the one before it" pattern Milestones 8-11
    # all used, now proven across a fifth era boundary rather than being a
    # one-off, a two-off, a three-off, or a four-off.
    ResearchNode(
        "data_driven_zoning",
        "Data-Driven Zoning",
        era="digital",
        tier=era_tiers("digital")[0],
        branch="craft",
        cost=95.0,
        prerequisites=("sanitation_engineering",),
        effects={"transit_bonus": 0.2, "extraction_efficiency": -0.1},
        blurb=(
            "Land use mapped and modelled instead of guessed at — the same discipline "
            "Sanitation Engineering brought to drains and filters, turned toward where the next "
            "resident actually goes."
        ),
    ),
    ResearchNode(
        "smart_utilities",
        "Smart Utilities",
        era="digital",
        tier=era_tiers("digital")[0],
        branch="provision",
        cost=95.0,
        prerequisites=("assembly_lines",),
        effects={"materials_yield_mult": 0.15, "extraction_efficiency": -0.1},
        blurb=(
            "Water, power and waste routed by what's actually being used, not by fixed guesswork. "
            "Assembly Lines multiplied what a factory floor could make; this is the same "
            "efficiency turned toward what the whole settlement runs on."
        ),
    ),
    ResearchNode(
        "participatory_planning",
        "Participatory Planning",
        era="digital",
        tier=era_tiers("digital")[0],
        branch="community",
        cost=100.0,
        prerequisites=("public_health_acts",),
        min_affinity={"community": 9},
        effects={"equity_bonus": 0.1, "sprawl_output_mult": -0.1},
        blurb=(
            "Zoning decided with the people who'll live with them, not just for them — the direct "
            "descendant of Public Health Acts making the neighborhood everyone's problem to solve. "
            "Only reachable by a settlement that kept investing in community across six eras "
            "running now."
        ),
    ),
    # --- Digital, late ---
    ResearchNode(
        "transit_oriented_design",
        "Transit-Oriented Design",
        era="digital",
        tier=era_tiers("digital")[1],
        branch="craft",
        cost=115.0,
        prerequisites=("data_driven_zoning",),
        effects={"transit_bonus": 0.3, "sprawl_output_mult": -0.15},
        blurb=(
            "Dense, walkable neighborhoods built around a transit stop instead of a road out of "
            "town. Data-Driven Zoning mapped where growth was heading; this is what actually "
            "redirects it inward instead of outward."
        ),
    ),
    ResearchNode(
        "circular_resource_systems",
        "Circular Resource Systems",
        era="digital",
        tier=era_tiers("digital")[1],
        branch="provision",
        cost=115.0,
        prerequisites=("smart_utilities",),
        effects={"materials_yield_mult": 0.2, "extraction_efficiency": -0.15},
        blurb=(
            "What used to be waste becomes the next batch of material instead. Smart Utilities "
            "routed what the settlement already had more carefully; this is the settlement "
            "needing less of it in the first place."
        ),
    ),
    ResearchNode(
        "digital_commons_charter",
        "Digital Commons Charter",
        era="digital",
        tier=era_tiers("digital")[1],
        branch="community",
        cost=130.0,
        prerequisites=("participatory_planning",),
        min_affinity={"community": 10},
        effects={"equity_bonus": 0.1, "resilience_bonus": 0.1},
        blurb=(
            "Open data and open decisions made a standing right rather than a one-time "
            "consultation — Participatory Planning proved the settlement would listen once; this "
            "is the settlement committing to keep doing it. Only reachable by a settlement that "
            "kept investing in community across six eras running now."
        ),
    ),
]
