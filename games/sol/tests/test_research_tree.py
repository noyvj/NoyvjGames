"""Tests for A16: a small research-tree diagram (games/sol/game.py's
update_research_tree_display()) instead of the single flat progress bar --
one card per tier, in order, each labeled Completed/In Progress/Locked and
listing which bodies it unlocks."""


def _tier(game_env, index):
    return game_env.module.RESEARCH_TIERS[index]


def _all_texts(element):
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


def _node_classes(game_env):
    tree = game_env.elements["research-tree"]
    return [child.className for child in tree.children if "research-tree-node" in child.className]


def test_tree_renders_one_node_per_tier(game_env):
    module = game_env.module
    assert len(_node_classes(game_env)) == len(module.RESEARCH_TIERS)


def test_first_tier_starts_in_progress_and_rest_locked(game_env):
    classes = _node_classes(game_env)
    assert "research-tree-node--current" in classes[0]
    for other in classes[1:]:
        assert "research-tree-node--locked" in other


def test_tier_becomes_completed_after_funding_it_fully(game_env):
    module = game_env.module
    tier = _tier(game_env, 0)
    game_env.earth["resource_count"] = tier["target"]
    for _ in range(tier["target"] // module.RESEARCH_FUND_COST):
        game_env.fund_research()

    classes = _node_classes(game_env)
    assert "research-tree-node--completed" in classes[0]
    assert "research-tree-node--current" in classes[1]


def test_node_lists_its_unlocked_bodies_by_display_name(game_env):
    tree = game_env.elements["research-tree"]
    texts = _all_texts(tree)
    assert any("Moon" in text and "Mars" in text for text in texts)
    assert any("Jupiter's Moons" in text for text in texts)


def test_tree_has_a_connecting_arrow_between_tiers(game_env):
    module = game_env.module
    tree = game_env.elements["research-tree"]
    arrow_count = sum(1 for child in tree.children if child.className == "research-tree-arrow")
    assert arrow_count == len(module.RESEARCH_TIERS) - 1


def test_tree_updates_live_after_funding_from_a_tick_triggered_render(game_env):
    """update_research_tree_display() is called from on_fund_research() and
    _full_render(), not tick() (research state can't change passively) --
    this pins that the tree is actually wired into the funding action."""
    module = game_env.module
    tier = _tier(game_env, 0)
    game_env.earth["resource_count"] = tier["target"]
    for _ in range(tier["target"] // module.RESEARCH_FUND_COST):
        game_env.fund_research()
    classes = _node_classes(game_env)
    assert "research-tree-node--completed" in classes[0]
