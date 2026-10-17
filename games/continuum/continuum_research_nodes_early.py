"""Research nodes, part 1 of 3: Tribal, Agrarian and Classical (early and late tiers).
Part of the split of the old single-file research.py: see "File map" in games/continuum/CLAUDE.md.
"""

from continuum_research_tree import ResearchNode, era_tiers


# --- the shipped tree --------------------------------------------------
# Tribal (Phase 1), Agrarian (Milestone 8), Classical (Milestone 9),
# Medieval (Milestone 10), Industrial (Milestone 11) and Digital
# (Milestone 12) so far. Tribal's nine nodes, per Phase 1's "populate just
# enough nodes to prove the system works", exercise every mechanism the
# engine has: plain prerequisites, tier gating, branch affinity, and every
# category of effect (yield multipliers, land regeneration, storage,
# housing, and the equity/resilience bonuses that only the sustainability
# score reads). Agrarian's six nodes prove the tree extends cleanly across
# an era boundary: every one of them chains a prerequisite back into a
# specific Tribal tier-2 node, so an early emphasis keeps echoing into a
# second era exactly the way "Council of Elders" already proved it could
# within one. Classical's six nodes repeat the same proof a second time,
# this time chaining back into Agrarian's own late tier. Medieval's six
# nodes repeat it a third time, chaining back into Classical's own late
# tier. Industrial's six nodes repeat it a fourth time, chaining back into
# Medieval's own late tier. Digital's six nodes repeat it a fifth time,
# chaining back into Industrial's own late tier — each branch now has an
# unbroken chain six eras deep (Tribal → Agrarian → Classical → Medieval →
# Industrial → Digital), and the community branch's min_affinity keeps
# compounding by exactly one at each step: `elders_council` (2),
# `market_custom` (3), `civic_assembly` (4), `municipal_charter` (5),
# `free_city_charter` (6), `factory_acts` (7), `public_health_acts` (8),
# `participatory_planning` (9), `digital_commons_charter` (10) — an
# emphasis that keeps compounding, not just echoing once.
_TRIBAL_TIERS = era_tiers("tribal")

_NODES_TRIBAL_TO_CLASSICAL = [
    # --- Tribal, early ---
    ResearchNode(
        "fire_keeping",
        "Fire-Keeping",
        era="tribal",
        tier=_TRIBAL_TIERS[0],
        branch="craft",
        cost=4.0,
        effects={"food_yield_mult": 0.15, "culture_bonus": 0.25},
        blurb="A fire kept alive through the night. Warmth, cooked food, a reason to sit together.",
    ),
    ResearchNode(
        "foraging_lore",
        "Foraging Lore",
        era="tribal",
        tier=_TRIBAL_TIERS[0],
        branch="provision",
        cost=4.0,
        effects={"food_yield_mult": 0.2},
        blurb="Which plants, which slopes, which weeks. Knowledge that makes the same land yield more.",
    ),
    ResearchNode(
        "shared_hearth",
        "Shared Hearth",
        era="tribal",
        tier=_TRIBAL_TIERS[0],
        branch="community",
        cost=4.0,
        effects={"equity_bonus": 0.08, "culture_bonus": 0.5},
        blurb="One fire for everyone rather than a fire for each family. A choice, not an accident.",
    ),
    # --- Tribal, late ---
    ResearchNode(
        "stone_knapping",
        "Stone Knapping",
        era="tribal",
        tier=_TRIBAL_TIERS[1],
        branch="craft",
        cost=8.0,
        prerequisites=("fire_keeping",),
        effects={"tool_yield_mult": 0.4, "materials_yield_mult": 0.1},
        blurb="Worked edges instead of found ones. Crafters get far more from the same stone.",
    ),
    ResearchNode(
        "seasonal_rounds",
        "Seasonal Rounds",
        era="tribal",
        tier=_TRIBAL_TIERS[1],
        branch="provision",
        cost=8.0,
        prerequisites=("foraging_lore",),
        effects={"regen_mult": 0.25, "extraction_efficiency": -0.1},
        blurb="Move on before a place is stripped, and come back to find it whole. The land keeps up.",
    ),
    ResearchNode(
        "kinship_custom",
        "Kinship Custom",
        era="tribal",
        tier=_TRIBAL_TIERS[1],
        branch="community",
        cost=8.0,
        prerequisites=("shared_hearth",),
        effects={"equity_bonus": 0.12, "resilience_bonus": 0.05},
        blurb="Who owes what to whom, and who is owed care. Nobody falls all the way through.",
    ),
    ResearchNode(
        "storage_craft",
        "Storage Craft",
        era="tribal",
        tier=_TRIBAL_TIERS[1],
        branch="craft",
        cost=10.0,
        prerequisites=("stone_knapping",),
        effects={"food_storage_bonus": 20.0, "resilience_bonus": 0.05},
        blurb="Lined pits and sealed vessels. A good season stops being wasted on the next bad one.",
    ),
    ResearchNode(
        "banked_shelters",
        "Banked Shelters",
        era="tribal",
        tier=_TRIBAL_TIERS[1],
        branch="craft",
        cost=10.0,
        prerequisites=("stone_knapping",),
        effects={"housing_bonus": 4.0},
        blurb="Earth banked against the walls. The same shelters hold more people through the cold.",
    ),
    ResearchNode(
        "elders_council",
        "Council of Elders",
        era="tribal",
        tier=_TRIBAL_TIERS[1],
        branch="community",
        cost=12.0,
        prerequisites=("kinship_custom",),
        min_affinity={"community": 2},
        effects={"equity_bonus": 0.1, "resilience_bonus": 0.1, "knowledge_mult": 0.25},
        blurb=(
            "Decisions made in the open, by people who remember. Only reachable by a settlement "
            "that has invested in community all along — the first place an early emphasis "
            "visibly changes what is on offer later."
        ),
    ),
    # --- Agrarian, early (Milestone 8) --- Six nodes proving the tree
    # extends cleanly across an era boundary: every prerequisite below
    # chains back into a specific Tribal-tier-2 node, so a settlement's
    # early emphasis keeps echoing exactly the way Phase 1's "Council of
    # Elders" already proved it could within one era.
    ResearchNode(
        "plow_and_furrow",
        "Plow and Furrow",
        era="agrarian",
        tier=era_tiers("agrarian")[0],
        branch="craft",
        cost=14.0,
        prerequisites=("stone_knapping",),
        effects={"food_yield_mult": 0.25},
        blurb="Turned soil holds water and nutrients a scraped surface never could. Farmers feel it first.",
    ),
    ResearchNode(
        "seed_selection",
        "Seed Selection",
        era="agrarian",
        tier=era_tiers("agrarian")[0],
        branch="provision",
        cost=14.0,
        prerequisites=("seasonal_rounds",),
        effects={"food_yield_mult": 0.15, "regen_mult": 0.1},
        blurb="Keeping back the best of this year's harvest to plant next year's. The land answers back, too.",
    ),
    ResearchNode(
        "communal_granaries",
        "Communal Granaries",
        era="agrarian",
        tier=era_tiers("agrarian")[0],
        branch="community",
        cost=16.0,
        prerequisites=("kinship_custom",),
        effects={"food_storage_bonus": 30.0, "equity_bonus": 0.06},
        blurb="A surplus kept in the open, not behind one family's wall. Storage and fairness, in one building.",
    ),
    # --- Agrarian, late ---
    ResearchNode(
        "irrigation_channels",
        "Irrigation Channels",
        era="agrarian",
        tier=era_tiers("agrarian")[1],
        branch="craft",
        cost=20.0,
        prerequisites=("plow_and_furrow",),
        effects={"food_yield_mult": 0.2, "extraction_efficiency": -0.1},
        blurb="Water carried to the field instead of the field carried to water. More reaches more, for less.",
    ),
    ResearchNode(
        "crop_rotation",
        "Crop Rotation",
        era="agrarian",
        tier=era_tiers("agrarian")[1],
        branch="provision",
        cost=20.0,
        prerequisites=("seed_selection",),
        effects={"regen_mult": 0.3, "extraction_efficiency": -0.15},
        blurb="Different fields rest in turn instead of one field never resting at all. Seasonal Rounds, grown up.",
    ),
    ResearchNode(
        "market_custom",
        "Market Custom",
        era="agrarian",
        tier=era_tiers("agrarian")[1],
        branch="community",
        cost=22.0,
        prerequisites=("communal_granaries",),
        min_affinity={"community": 3},
        effects={"surplus_conversion_bonus": 0.2, "equity_bonus": 0.08},
        blurb=(
            "Fair trade becomes custom, not just courtesy — more of what would spoil finds its way to "
            "someone who needs it. Only reachable by a settlement that has invested in community all "
            "along, the same way Council of Elders was."
        ),
    ),
    # --- Classical, early (Milestone 9) --- Three nodes, one per branch,
    # each chaining a prerequisite back into the LATE Agrarian tier (tier 4)
    # of the same branch — the same "early tier of a new era chains to the
    # late tier of the one before it" pattern Milestone 8's own tier-3 nodes
    # used against Tribal's tier 2, now proven to hold across a second era
    # boundary rather than being a one-off.
    ResearchNode(
        "canal_engineering",
        "Canal Engineering",
        era="classical",
        tier=era_tiers("classical")[0],
        branch="craft",
        cost=26.0,
        prerequisites=("irrigation_channels",),
        effects={"extraction_efficiency": -0.1, "canal_yield_bonus": 0.2},
        blurb=(
            "Water measured and channeled by design instead of dug by feel. Irrigation Channels carried "
            "water to one field; this carries it, and the planning behind it, to the whole city."
        ),
    ),
    ResearchNode(
        "managed_irrigation",
        "Managed Irrigation",
        era="classical",
        tier=era_tiers("classical")[0],
        branch="provision",
        cost=26.0,
        prerequisites=("crop_rotation",),
        effects={"food_yield_mult": 0.2},
        blurb=(
            "Rotation told a field when to rest; this tells a whole network of fields when to drink. "
            "The same idea, scaled past what one farmer could ever coordinate alone."
        ),
    ),
    ResearchNode(
        "temple_administration",
        "Temple Administration",
        era="classical",
        tier=era_tiers("classical")[0],
        branch="community",
        cost=28.0,
        prerequisites=("market_custom",),
        effects={"equity_bonus": 0.08, "knowledge_mult": 0.15},
        blurb=(
            "Grain counted, water rights recorded, disputes written down rather than remembered. "
            "Market Custom's fair trade becomes an institution rather than a habit."
        ),
    ),
    # --- Classical, late ---
    ResearchNode(
        "monumental_masonry",
        "Monumental Masonry",
        era="classical",
        tier=era_tiers("classical")[1],
        branch="craft",
        cost=34.0,
        prerequisites=("canal_engineering",),
        effects={"housing_bonus": 6.0, "materials_yield_mult": 0.1},
        blurb=(
            "Stone raised in courses, not stacked by hand — walls and stores built to outlast whoever "
            "built them. The kind of city a canal network can actually feed."
        ),
    ),
    ResearchNode(
        "trade_networks",
        "Trade Networks",
        era="classical",
        tier=era_tiers("classical")[1],
        branch="provision",
        cost=34.0,
        prerequisites=("managed_irrigation",),
        effects={"food_yield_mult": 0.1, "surplus_conversion_bonus": 0.15},
        blurb=(
            "A managed surplus is worth more once it can travel — caravans reaching further than any "
            "one settlement's own fields, the way Market Custom's fairness once reached only as far as "
            "one granary."
        ),
    ),
    ResearchNode(
        "civic_assembly",
        "Civic Assembly",
        era="classical",
        tier=era_tiers("classical")[1],
        branch="community",
        cost=38.0,
        prerequisites=("temple_administration",),
        min_affinity={"community": 4},
        effects={"equity_bonus": 0.1, "resilience_bonus": 0.1},
        blurb=(
            "Decisions made in the open again, at city scale this time — Council of Elders and Market "
            "Custom both feeding into something bigger. Only reachable by a settlement that kept "
            "investing in community across three eras running, not just one."
        ),
    ),
]
