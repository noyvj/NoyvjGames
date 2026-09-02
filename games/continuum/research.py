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

    def tier_unlocked(self, tier):
        if tier <= 1:
            return True
        below = sum(1 for node_id in self.researched if self.nodes[node_id].tier == tier - 1)
        return below >= TIER_UNLOCK_REQUIREMENT

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
            below = sum(1 for other in self.researched if self.nodes[other].tier == node.tier - 1)
            short = TIER_UNLOCK_REQUIREMENT - below
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
                    "knowledge_mult", "regen_mult", "extraction_efficiency"):
            totals[key] = max(0.0, totals[key])
        return totals

    # --- save support (Milestone 4) --------------------------------------
    def snapshot(self):
        """JSON-safe record of what has been researched, in order."""
        return list(self.researched)

    def restore(self, researched):
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
# Tribal era only, per Phase 1's "populate just enough nodes to prove the
# system works". Nine nodes across both Tribal tiers and all three branches,
# chosen so that between them they exercise every mechanism the engine has:
# plain prerequisites, tier gating, branch affinity, and every category of
# effect (yield multipliers, land regeneration, storage, housing, and the
# equity/resilience bonuses that only the sustainability score reads).
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
]

NODES = {node.node_id: node for node in NODE_LIST}


def build_tree(current_era=sim.FIRST_ERA, researched=None):
    return ResearchTree(NODES, current_era=current_era, researched=researched)
