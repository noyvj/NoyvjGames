"""Continuum — research tree engine.

Milestone 3 of Phase 1. The design doc calls this the game's backbone and
asks for the *shape* of the tree to be settled before nodes get written,
so that six later eras extend it instead of forcing a retrofit. That shape
is the first half of this file; the Tribal-era nodes at the bottom are
deliberately few, and exist to prove the engine end to end.

## The tier structure (the proposal the doc asks for)

One continuous tree spanning all seven eras, cut into **two tiers per era**
— an early and a late layer — for **14 tiers total**. Tier numbers are
global and ascending, so "tier 7" means one thing forever and a node never
has to be renumbered when a later era is written.

A tier opens once `TIER_UNLOCK_REQUIREMENT` nodes in the tier immediately
below it are researched. That's a soft gate, not a wall: it doesn't matter
*which* nodes, so a player can specialise and still progress, while a
player who researches nothing stays where they are. Era gating sits on top
— a node from an era the settlement hasn't reached is never available,
however much knowledge is banked.

## The three branches

Branches run the whole length of the tree rather than being per-era
categories, which is what makes the doc's "early choices echo later"
requirement mechanically true:

- **provision** — food, materials, the business of getting things
- **community** — social organisation, equity, culture
- **craft** — tools, technique, infrastructure

Two mechanisms carry an early emphasis forward. Ordinary `prerequisites`
chain node to node, and `min_affinity` gates a node on how many nodes in a
branch have been researched at all — so a settlement that has consistently
invested in community unlocks things a settlement that dabbled cannot,
without either path being blocked outright.

## Effects

A node's effects are always expressed as **deltas**, and the tree sums them
onto `sim.NEUTRAL_EFFECTS`. Multiplicative keys sit at a 1.0 base, additive
keys at 0.0, so `{"food_yield_mult": 0.2}` reads as "+20% food" and
`{"housing_bonus": 4}` as "+4 people housed" with no other bookkeeping.
That uniformity is what keeps effect aggregation from becoming a per-key
special case as the tree grows.
"""

import sim

# --- tier structure ----------------------------------------------------
TIERS_PER_ERA = 2
TOTAL_TIERS = len(sim.ERA_ORDER) * TIERS_PER_ERA

# How many nodes of the tier below must be researched before a tier opens.
TIER_UNLOCK_REQUIREMENT = 2


def era_tiers(era):
    """The (ascending) global tier numbers belonging to one era."""
    start = sim.era_index(era) * TIERS_PER_ERA + 1
    return list(range(start, start + TIERS_PER_ERA))


def tier_era(tier):
    """The era a global tier number belongs to."""
    return sim.ERA_ORDER[(tier - 1) // TIERS_PER_ERA]


# --- branches ----------------------------------------------------------
BRANCHES = ["provision", "community", "craft"]

BRANCH_LABEL = {
    "provision": "Provision",
    "community": "Community",
    "craft": "Craft",
}


class ResearchNode:
    """One discovery. Pure data — the tree does all the reasoning."""

    def __init__(
        self,
        node_id,
        name,
        era=sim.FIRST_ERA,
        tier=1,
        branch="craft",
        cost=1.0,
        prerequisites=(),
        min_affinity=None,
        effects=None,
        blurb="",
    ):
        self.node_id = node_id
        self.name = name
        self.era = era
        self.tier = tier
        self.branch = branch
        self.cost = cost
        self.prerequisites = tuple(prerequisites)
        self.min_affinity = dict(min_affinity or {})
        self.effects = dict(effects or {})
        self.blurb = blurb


class ResearchTree:
    """The engine. Generic over any set of nodes, in any era."""

    def __init__(self, nodes, current_era=sim.FIRST_ERA, researched=None):
        self.nodes = dict(nodes)
        self.current_era = current_era
        # A list rather than a set: it is JSON-native for the save file, and
        # its order is the order things were discovered, which the Phase 2
        # log system will want.
        self.researched = list(researched or [])

    # --- queries --------------------------------------------------------
    def is_researched(self, node_id):
        return node_id in self.researched

    def affinity(self, branch):
        """How many researched nodes belong to a branch."""
        return sum(1 for node_id in self.researched if self.nodes[node_id].branch == branch)

    def researched_in_tier(self, tier):
        """How many researched nodes sit in one tier.

        Both the gate (`tier_unlocked`) and the explanation the UI shows for
        a closed gate (`missing_requirements`) are counted from here, so the
        two can't drift apart into saying different things.
        """
        return sum(1 for node_id in self.researched if self.nodes[node_id].tier == tier)

    def tier_unlocked(self, tier):
        if tier <= 1:
            return True
        return self.researched_in_tier(tier - 1) >= TIER_UNLOCK_REQUIREMENT

    def era_reached(self, era):
        return sim.era_index(era) <= sim.era_index(self.current_era)

    def missing_requirements(self, node_id):
        """Human-readable reasons a node can't be researched right now.

        Doubles as the UI's explanation text and as what the tests assert
        against, so there's one description of "why not" rather than two.
        """
        node = self.nodes[node_id]
        reasons = []

        if not self.era_reached(node.era):
            reasons.append(f"The settlement hasn't reached the {sim.ERA_LABEL[node.era]} era.")

        if not self.tier_unlocked(node.tier):
            short = TIER_UNLOCK_REQUIREMENT - self.researched_in_tier(node.tier - 1)
            reasons.append(f"Needs {short} more discoveries from the tier below.")

        for prereq in node.prerequisites:
            if prereq not in self.researched:
                reasons.append(f"Requires {self.nodes[prereq].name}.")

        for branch, needed in node.min_affinity.items():
            have = self.affinity(branch)
            if have < needed:
                reasons.append(
                    f"Requires {needed} discoveries in {BRANCH_LABEL[branch]} — you have {have}."
                )

        return reasons

    def is_available(self, node_id):
        if self.is_researched(node_id):
            return False
        return not self.missing_requirements(node_id)

    def available_nodes(self):
        return [n for n in self.nodes.values() if self.is_available(n.node_id)]

    def researched_nodes(self):
        return [self.nodes[node_id] for node_id in self.researched]

    def visible_nodes(self):
        """What the UI lists: everything from eras the settlement has reached.

        Locked-but-visible nodes are deliberately included — a research tree
        the player can't see the shape of isn't a tree, it's a queue.
        """
        nodes = [n for n in self.nodes.values() if self.era_reached(n.era)]
        return sorted(nodes, key=lambda n: (n.tier, BRANCHES.index(n.branch), n.name))

    def can_afford(self, node_id, resources):
        return resources.get("knowledge", 0.0) >= self.nodes[node_id].cost

    # --- mutation -------------------------------------------------------
    def research(self, node_id, resources):
        """Spends knowledge and records the discovery. False if refused."""
        if node_id not in self.nodes:
            return False
        if not self.is_available(node_id):
            return False
        if not self.can_afford(node_id, resources):
            return False
        resources["knowledge"] -= self.nodes[node_id].cost
        self.researched.append(node_id)
        return True

    # --- effects --------------------------------------------------------
    def effects(self):
        """All researched nodes' deltas summed onto the neutral baseline."""
        totals = dict(sim.NEUTRAL_EFFECTS)
        for node_id in self.researched:
            for key, delta in self.nodes[node_id].effects.items():
                if key in totals:
                    totals[key] += delta
        # Multiplier floors — no accumulation of penalties can make a yield
        # negative, whatever a future era's trade-off nodes look like.
        for key in ("food_yield_mult", "materials_yield_mult", "tool_yield_mult",
                    "knowledge_mult", "regen_mult", "extraction_efficiency",
                    "pollution_output_mult", "sprawl_output_mult"):
            totals[key] = max(0.0, totals[key])
        return totals

    # --- save support (Milestone 4) --------------------------------------
    def snapshot(self):
        """JSON-safe record of what has been researched, in order."""
        return list(self.researched)

    def restore(self, researched):
        """Takes only ids this build actually has a node for.

        Tolerating a non-list here rather than at each call site: both
        callers in save.py feed this straight out of a save dict, which can
        be truncated or hand-edited, and a half-restored tree is worse than
        an empty one.
        """
        if not isinstance(researched, list):
            researched = []
        self.researched = [node_id for node_id in researched if node_id in self.nodes]

    # --- structural validation -------------------------------------------
    def validate(self):
        """Problems with the tree's *shape*, as a list of strings.

        Content bugs in a 14-tier tree are cheap to make and expensive to
        find by playing, so the shipped tree is asserted valid in the test
        suite rather than trusted.
        """
        problems = []

        for node_id, node in self.nodes.items():
            if node.node_id != node_id:
                problems.append(f"{node_id}: id mismatch ({node.node_id}).")
            if node.era not in sim.ERA_ORDER:
                problems.append(f"{node_id}: unknown era {node.era}.")
            elif node.tier not in era_tiers(node.era):
                problems.append(
                    f"{node_id}: tier {node.tier} does not belong to the {node.era} era."
                )
            if node.branch not in BRANCHES:
                problems.append(f"{node_id}: unknown branch {node.branch}.")
            if node.cost < 0:
                problems.append(f"{node_id}: negative cost.")

            for prereq in node.prerequisites:
                if prereq not in self.nodes:
                    problems.append(f"{node_id}: unknown prerequisite {prereq}.")
                elif self.nodes[prereq].tier > node.tier:
                    problems.append(
                        f"{node_id}: prerequisite {prereq} sits in a later tier."
                    )

            for branch in node.min_affinity:
                if branch not in BRANCHES:
                    problems.append(f"{node_id}: affinity on unknown branch {branch}.")

            for key in node.effects:
                if key not in sim.NEUTRAL_EFFECTS:
                    problems.append(f"{node_id}: unknown effect key {key}.")

        problems.extend(self._cycle_problems())
        return problems

    def _cycle_problems(self):
        """Depth-first cycle detection over the prerequisite graph."""
        problems = []
        WHITE, GREY, BLACK = 0, 1, 2
        colour = {node_id: WHITE for node_id in self.nodes}

        def visit(node_id, path):
            colour[node_id] = GREY
            for prereq in self.nodes[node_id].prerequisites:
                if prereq not in self.nodes:
                    continue
                if colour[prereq] == GREY:
                    problems.append(
                        "Prerequisite cycle: " + " -> ".join(path + [node_id, prereq])
                    )
                elif colour[prereq] == WHITE:
                    visit(prereq, path + [node_id])
            colour[node_id] = BLACK

        for node_id in self.nodes:
            if colour[node_id] == WHITE:
                visit(node_id, [])
        return problems


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

NODE_LIST = [
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
]

NODES = {node.node_id: node for node in NODE_LIST}


def build_tree(current_era=sim.FIRST_ERA, researched=None):
    return ResearchTree(NODES, current_era=current_era, researched=researched)
