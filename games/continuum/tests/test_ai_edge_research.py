"""Edge-case tests for research.py."""


import research
import sim


def test_describe_effects_handles_empty_effects():
    tree = research.build_tree()
    node = next(n for n in tree.nodes.values())
    original_effects = node.effects
    node.effects = {}
    desc = research.describe_effects(node)
    assert desc == ""
    node.effects = original_effects


def test_describe_effects_formats_zero_and_negative_deltas():
    tree = research.build_tree()
    node = next(n for n in tree.nodes.values())
    original_effects = node.effects
    node.effects = {"food_yield_mult": 0.0, "pollution_output_mult": -0.1}
    desc = research.describe_effects(node)
    assert "food yield +0%" in desc
    assert "pollution per factory worker -10%" in desc
    node.effects = original_effects


def test_unlock_estimate_returns_none_for_missing_node():
    tree = research.build_tree()
    assert research.unlock_estimate(tree, "does_not_exist") is None


def test_unlock_estimate_returns_none_when_already_researched():
    tree = research.build_tree(researched={"foraging_lore"})
    assert research.unlock_estimate(tree, "foraging_lore") is None


def test_build_tree_accepts_custom_era_and_researched():
    tree_default = research.build_tree()
    tree_custom = research.build_tree(current_era="classical", researched={"foraging_lore"})

    assert tree_default.current_era == sim.FIRST_ERA
    assert tree_custom.current_era == "classical"
    assert tree_custom.is_researched("foraging_lore") is True
    assert tree_default.is_researched("foraging_lore") is False


def test_cost_of_handles_zero_and_high_multipliers():
    tree = research.build_tree()
    node_id = next(n.node_id for n in tree.nodes.values() if n.branch == "provision")

    base_cost = tree.cost_of(node_id)
    assert base_cost > 0

    tree_empty = research.build_tree()
    tree_empty.cost_mults = {}
    assert tree_empty.cost_of(node_id) == base_cost

    tree_discount = research.build_tree()
    tree_discount.cost_mults = {"provision": 0.5}
    assert tree_discount.cost_of(node_id) < base_cost

    tree_inflate = research.build_tree()
    tree_inflate.cost_mults = {"provision": 2.0}
    assert tree_inflate.cost_of(node_id) > base_cost


def test_can_afford_with_empty_resources():
    tree = research.build_tree()
    node_id = next(n.node_id for n in tree.nodes.values() if not tree.is_researched(n.node_id))

    resources = {}
    assert tree.can_afford(node_id, resources) is False

    resources["knowledge"] = 0.0
    assert tree.can_afford(node_id, resources) is False
