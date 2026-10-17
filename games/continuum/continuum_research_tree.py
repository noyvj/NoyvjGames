"""The research tree engine: tier structure, ResearchNode and ResearchTree (prerequisites, affinity, effects, save support,
structural validation). No node data here. Ask for this file to change how the tree behaves.
Part of the split of the old single-file research.py: see "File map" in games/continuum/CLAUDE.md.
"""

import sim


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
        # K-6: era doctrines make some branches cheaper. {branch: multiplier}; set by
        # the game each render from the doctrines it holds (never saved), empty by default.
        self.cost_mults = {}

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

    def cost_of(self, node_id):
        """What a node costs right now: its base cost times its branch's doctrine multiplier
        (K-6), to one decimal place so the price shown is the price paid."""
        node = self.nodes[node_id]
        mult = self.cost_mults.get(node.branch, 1.0)
        if mult == 1.0:
            return node.cost
        return round(node.cost * mult, 1)

    def can_afford(self, node_id, resources):
        return resources.get("knowledge", 0.0) >= self.cost_of(node_id)

    # --- mutation -------------------------------------------------------
    def research(self, node_id, resources):
        """Spends knowledge and records the discovery. False if refused."""
        if node_id not in self.nodes:
            return False
        if not self.is_available(node_id):
            return False
        if not self.can_afford(node_id, resources):
            return False
        resources["knowledge"] -= self.cost_of(node_id)
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
