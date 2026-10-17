"""Continuum — research tree engine.

Milestone 3 of Phase 1. The design doc calls this the game's backbone and
asks for the *shape* of the tree to be settled before nodes get written,
so that six later eras extend it instead of forcing a retrofit. That shape
is the first half of this file; the Tribal-era nodes at the bottom are
deliberately few, and exist to prove the engine end to end.

## The tier structure (the proposal the doc asks for)

One continuous tree spanning all eight eras, cut into **two tiers per era**
— an early and a late layer — for **16 tiers total**. Tier numbers are
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
import continuum_research_tree
import continuum_research_nodes_early
import continuum_research_nodes_mid
import continuum_research_nodes_late

# research.py is the public face of the research tree: the engine (ResearchNode, ResearchTree, tiers) is in
# continuum_research_tree and the node data in the three continuum_research_nodes_* parts (era by era, in that order).
# Everything is re-exported here, so `research.ResearchTree`, `research.BRANCHES`, `research.NODE_LIST` ... work as before.
for _part in (continuum_research_tree, continuum_research_nodes_early, continuum_research_nodes_mid, continuum_research_nodes_late):
    for _name, _value in vars(_part).items():
        if not _name.startswith("__"):
            globals()[_name] = _value
del _part, _name, _value

# --- the shipped tree --------------------------------------------------
NODE_LIST = _NODES_TRIBAL_TO_CLASSICAL + _NODES_MEDIEVAL_TO_DIGITAL + _NODES_SPACE_TO_END

NODES = {node.node_id: node for node in NODE_LIST}

# K12: plain-language names for every effect key, so a node's exact numeric
# effect can be shown right in the tree (tooltip + a line on the row).
# Multiplier-style keys read as percentages, capacity-style keys as flat
# amounts. `pollution_output_mult`/`sprawl_output_mult`/`extraction_
# efficiency` are "lower is better" keys, so a negative delta is shown as a
# reduction, not a penalty.
EFFECT_LABELS = {
    "food_yield_mult": ("food yield", "pct"),
    "materials_yield_mult": ("materials yield", "pct"),
    "tool_yield_mult": ("tool output", "pct"),
    "knowledge_mult": ("knowledge output", "pct"),
    "regen_mult": ("land recovery", "pct"),
    "extraction_efficiency": ("land pressure per harvest", "pct"),
    "food_storage_bonus": ("food storage", "flat"),
    "housing_bonus": ("people housed", "flat"),
    "culture_bonus": ("gathering space", "flat"),
    "equity_bonus": ("equity", "score"),
    "resilience_bonus": ("resilience", "score"),
    "surplus_conversion_bonus": ("surplus banked from spoilage", "pct"),
    "canal_yield_bonus": ("canal yield", "pct"),
    "public_works_bonus": ("public works coverage", "pct"),
    "pollution_output_mult": ("pollution per factory worker", "pct"),
    "sanitation_bonus": ("sanitation absorption", "pct"),
    "sprawl_output_mult": ("sprawl from growth", "pct"),
    "transit_bonus": ("transit hub absorption", "pct"),
    "habitat_layout_bonus": ("habitat layout quality", "pct"),
    "relay_bonus": ("relay throughput", "pct"),
}


def describe_effects(node):
    """K12: 'food yield +20%, land recovery +25%' for one node."""
    parts = []
    for key, delta in node.effects.items():
        label, kind = EFFECT_LABELS.get(key, (key, "flat"))
        if kind == "pct":
            parts.append(f"{label} {delta * 100:+.0f}%")
        elif kind == "score":
            parts.append(f"{label} {delta * 100:+.0f} points")
        else:
            parts.append(f"{label} {delta:+.0f}")
    return ", ".join(parts)


def unlock_estimate(tree, node_id):
    """K23: roughly how much knowledge it takes to open a tier-gated node.

    Only meaningful when the tier gate is what is holding the node back: the
    sum of the cheapest still-unresearched, currently-available nodes in the
    tier below that would close the gap, plus the node's own cost. Returns
    None when something else (era, prerequisites, branch affinity) is the
    blocker, or the gap cannot be closed from what is available right now.
    An estimate, not a promise: it ignores what those nodes unlock.
    """
    node = tree.nodes.get(node_id)
    if node is None or tree.is_researched(node_id) or not tree.era_reached(node.era):
        return None
    if tree.tier_unlocked(node.tier):
        return None
    short = TIER_UNLOCK_REQUIREMENT - tree.researched_in_tier(node.tier - 1)
    candidates = sorted(
        tree.cost_of(n.node_id) for n in tree.nodes.values()
        if n.tier == node.tier - 1 and not tree.is_researched(n.node_id) and tree.is_available(n.node_id)
    )
    if len(candidates) < short:
        return None
    return sum(candidates[:short]) + tree.cost_of(node_id)


def build_tree(current_era=sim.FIRST_ERA, researched=None):
    return ResearchTree(NODES, current_era=current_era, researched=researched)
