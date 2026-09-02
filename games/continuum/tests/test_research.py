"""Milestone 3 — research tree engine.

The design doc calls the tree "the game's backbone, not a side system", and
asks for a tier/layer structure designed up front so that six later eras
don't force a retrofit of the tree's shape. So most of this file tests the
*engine* against synthetic trees — unlock logic, prerequisite checking,
tier gating, era gating, branch affinity, effect aggregation, and structural
validation — and only a handful of tests touch the shipped Tribal-era
nodes, which exist to prove the engine end to end rather than to be the
final content.
"""

import pytest

import research
import sim
import sustainability


def node(node_id, **kwargs):
    """A research node with sensible defaults, for synthetic test trees."""
    kwargs.setdefault("name", node_id.replace("_", " ").title())
    kwargs.setdefault("era", "tribal")
    kwargs.setdefault("tier", 1)
    kwargs.setdefault("branch", "craft")
    kwargs.setdefault("cost", 1.0)
    return research.ResearchNode(node_id, **kwargs)


def tree_of(*nodes):
    return research.ResearchTree({n.node_id: n for n in nodes})


# --- tier structure ----------------------------------------------------
def test_the_tier_map_covers_every_era_in_order(game_env):
    """Tiers are allocated to eras up front, so a later era's nodes have a
    home already rather than needing the tree reshaped around them."""
    seen = []
    for era in sim.ERA_ORDER:
        tiers = research.era_tiers(era)
        assert len(tiers) == research.TIERS_PER_ERA
        seen.extend(tiers)

    assert seen == sorted(seen)  # ascending, no overlaps
    assert seen == list(range(1, len(sim.ERA_ORDER) * research.TIERS_PER_ERA + 1))
    assert research.TOTAL_TIERS == len(seen)


def test_every_tier_maps_back_to_its_era(game_env):
    for era in sim.ERA_ORDER:
        for tier in research.era_tiers(era):
            assert research.tier_era(tier) == era


def test_branches_run_across_every_era(game_env):
    """Three continuous branches rather than per-era categories — this is
    what lets an early choice still mean something six eras later."""
    assert len(research.BRANCHES) >= 3
    for branch in research.BRANCHES:
        assert branch in research.BRANCH_LABEL


# --- unlock logic ------------------------------------------------------
def test_first_tier_nodes_are_available_immediately(game_env):
    tree = tree_of(node("a"), node("b"))

    assert tree.is_available("a") is True
    assert tree.is_available("b") is True


def test_a_node_is_not_available_once_it_is_researched(game_env):
    tree = tree_of(node("a"))
    tree.research("a", {"knowledge": 10.0})

    assert tree.is_researched("a") is True
    assert tree.is_available("a") is False
    assert "a" not in [n.node_id for n in tree.available_nodes()]


def test_prerequisites_gate_availability(game_env):
    tree = tree_of(
        node("a"),
        node("b"),
        node("child", tier=2, prerequisites=("a",)),
    )
    resources = {"knowledge": 100.0}

    # Tier 2 needs enough of tier 1 done first, *and* the prerequisite.
    assert tree.is_available("child") is False
    tree.research("a", resources)
    assert tree.is_available("child") is False  # tier still locked
    tree.research("b", resources)
    assert tree.is_available("child") is True


def test_a_missing_prerequisite_is_reported_by_name(game_env):
    tree = tree_of(
        node("a"),
        node("b"),
        node("c"),
        node("child", tier=2, prerequisites=("a",)),
    )
    resources = {"knowledge": 100.0}
    tree.research("b", resources)
    tree.research("c", resources)  # tier 2 is open, but "a" is still missing

    reasons = tree.missing_requirements("child")

    assert tree.tier_unlocked(2) is True
    assert any(tree.nodes["a"].name in reason for reason in reasons)


def test_a_tier_opens_only_after_enough_of_the_previous_one(game_env):
    nodes = [node(f"t1_{i}") for i in range(4)]
    tree = tree_of(*nodes, node("t2", tier=2))
    resources = {"knowledge": 100.0}

    assert tree.tier_unlocked(1) is True
    assert tree.tier_unlocked(2) is False

    for i in range(research.TIER_UNLOCK_REQUIREMENT):
        tree.research(f"t1_{i}", resources)

    assert tree.tier_unlocked(2) is True
    assert tree.is_available("t2") is True


def test_branch_affinity_gates_later_nodes(game_env):
    """The doc's "early emphasis has visible echoes later" mechanism: some
    nodes need a track record in a branch, not just a single prerequisite."""
    tree = tree_of(
        node("c1", branch="community"),
        node("c2", branch="community"),
        node("k1", branch="craft"),
        node("council", tier=2, branch="community", min_affinity={"community": 2}),
    )
    resources = {"knowledge": 100.0}

    tree.research("k1", resources)
    tree.research("c1", resources)
    assert tree.tier_unlocked(2) is True
    assert tree.affinity("community") == 1
    assert tree.is_available("council") is False
    assert any("community" in reason.lower() for reason in tree.missing_requirements("council"))

    tree.research("c2", resources)
    assert tree.affinity("community") == 2
    assert tree.is_available("council") is True


def test_era_gates_nodes_from_eras_the_city_has_not_reached(game_env):
    later_era = sim.ERA_ORDER[1]
    tree = tree_of(
        node("now"),
        node("later", era=later_era, tier=research.era_tiers(later_era)[0]),
    )

    assert tree.is_available("later") is False
    assert "later" not in [n.node_id for n in tree.available_nodes()]

    tree.current_era = later_era
    # Still tier-gated, but no longer era-gated.
    assert any("era" in reason.lower() for reason in tree.missing_requirements("later")) is False


# --- researching -------------------------------------------------------
def test_researching_spends_knowledge(game_env):
    tree = tree_of(node("a", cost=6.0))
    resources = {"knowledge": 10.0}

    assert tree.research("a", resources) is True
    assert resources["knowledge"] == pytest.approx(4.0)
    assert tree.researched == ["a"]


def test_research_is_refused_without_enough_knowledge(game_env):
    tree = tree_of(node("a", cost=6.0))
    resources = {"knowledge": 5.0}

    assert tree.can_afford("a", resources) is False
    assert tree.research("a", resources) is False
    assert resources["knowledge"] == pytest.approx(5.0)
    assert tree.researched == []


def test_an_unavailable_node_cannot_be_researched_however_rich_you_are(game_env):
    tree = tree_of(node("a"), node("locked", tier=2))
    resources = {"knowledge": 1000.0}

    assert tree.research("locked", resources) is False
    assert resources["knowledge"] == pytest.approx(1000.0)


def test_a_node_cannot_be_researched_twice(game_env):
    tree = tree_of(node("a", cost=3.0))
    resources = {"knowledge": 100.0}

    assert tree.research("a", resources) is True
    assert tree.research("a", resources) is False
    assert resources["knowledge"] == pytest.approx(97.0)
    assert tree.researched == ["a"]


# --- effects -----------------------------------------------------------
def test_an_untouched_tree_produces_neutral_effects(game_env):
    tree = tree_of(node("a"))

    assert tree.effects() == sim.NEUTRAL_EFFECTS


def test_effects_are_deltas_that_accumulate(game_env):
    tree = tree_of(
        node("a", effects={"food_yield_mult": 0.2, "equity_bonus": 0.1}),
        node("b", effects={"food_yield_mult": 0.3, "housing_bonus": 4.0}),
    )
    resources = {"knowledge": 100.0}
    tree.research("a", resources)
    tree.research("b", resources)

    effects = tree.effects()

    # Multiplicative keys start at 1.0 and take deltas; additive at 0.0.
    assert effects["food_yield_mult"] == pytest.approx(1.5)
    assert effects["equity_bonus"] == pytest.approx(0.1)
    assert effects["housing_bonus"] == pytest.approx(4.0)
    assert effects["materials_yield_mult"] == pytest.approx(1.0)


def test_effects_reach_the_simulation(game_env):
    tree = tree_of(node("lore", effects={"food_yield_mult": 0.5}))
    tree.research("lore", {"knowledge": 100.0})

    plain = sim.CityState().advance_season()["food_gathered"]
    boosted = sim.CityState().advance_season(tree.effects())["food_gathered"]

    assert boosted == pytest.approx(plain * 1.5)


def test_effects_reach_the_sustainability_score(game_env):
    tree = tree_of(node("custom", effects={"equity_bonus": 0.2}))
    state = sim.CityState()
    state.fed_fraction = 0.5  # leave headroom for the bonus to show

    before = sustainability.score(state)
    tree.research("custom", {"knowledge": 100.0})

    assert sustainability.score(state, tree.effects()) > before


# --- structural validation ---------------------------------------------
def test_the_shipped_tree_is_structurally_valid(game_env):
    assert research.build_tree().validate() == []


def test_validation_catches_an_unknown_prerequisite(game_env):
    tree = tree_of(node("a", tier=2, prerequisites=("ghost",)))

    problems = tree.validate()

    assert any("ghost" in problem for problem in problems)


def test_validation_catches_a_prerequisite_from_a_later_tier(game_env):
    tree = tree_of(node("early", prerequisites=("late",)), node("late", tier=2))

    assert any("tier" in problem for problem in tree.validate())


def test_validation_catches_a_cycle(game_env):
    tree = tree_of(
        node("a", prerequisites=("b",)),
        node("b", prerequisites=("a",)),
    )

    assert any("cycle" in problem.lower() for problem in tree.validate())


def test_validation_catches_an_unknown_effect_key(game_env):
    tree = tree_of(node("a", effects={"invented_bonus": 1.0}))

    assert any("invented_bonus" in problem for problem in tree.validate())


def test_validation_catches_a_tier_that_does_not_belong_to_its_era(game_env):
    tree = tree_of(node("a", era="tribal", tier=research.TOTAL_TIERS))

    assert any("era" in problem.lower() for problem in tree.validate())


# --- the shipped Tribal-era content ------------------------------------
def test_the_tribal_era_has_nodes_in_both_of_its_tiers(game_env):
    tree = research.build_tree()
    tribal_tiers = research.era_tiers("tribal")

    for tier in tribal_tiers:
        assert [n for n in tree.nodes.values() if n.tier == tier]


def test_every_shipped_node_is_reachable_from_an_empty_tree(game_env):
    """No orphan content: playing well enough must be able to reach every
    Tribal node, or it may as well not be in the file."""
    tree = research.build_tree()
    resources = {"knowledge": 10_000.0}

    for _ in range(len(tree.nodes)):
        available = tree.available_nodes()
        if not available:
            break
        for candidate in available:
            tree.research(candidate.node_id, resources)

    assert len(tree.researched) == len(tree.nodes)


def test_the_shipped_tree_exercises_every_gating_mechanism(game_env):
    """The Tribal set is small, but it has to prove the engine end to end."""
    tree = research.build_tree()
    assert any(n.prerequisites for n in tree.nodes.values())
    assert any(n.min_affinity for n in tree.nodes.values())
    assert len({n.branch for n in tree.nodes.values()}) == len(research.BRANCHES)
    assert len({n.tier for n in tree.nodes.values()}) == research.TIERS_PER_ERA


# --- UI ----------------------------------------------------------------
def test_the_research_panel_lists_nodes_and_reports_knowledge(game_env):
    assert "Knowledge" in game_env.elements["research-status-display"].innerText
    assert game_env.elements["research-list"].children


def test_clicking_a_research_button_researches_the_node(game_env):
    state = game_env.state
    state.resources["knowledge"] = 500.0
    game_env.module.render()

    first = game_env.module.tree.available_nodes()[0]
    game_env.elements[f"research-{first.node_id}"].dispatch("click", None)

    assert game_env.module.tree.is_researched(first.node_id) is True
    assert state.resources["knowledge"] < 500.0


def test_research_buttons_are_disabled_without_the_knowledge_to_pay(game_env):
    state = game_env.state
    state.resources["knowledge"] = 0.0
    game_env.module.render()

    first = game_env.module.tree.available_nodes()[0]
    assert game_env.elements[f"research-{first.node_id}"].disabled is True

    state.resources["knowledge"] = 500.0
    game_env.module.render()
    assert game_env.elements[f"research-{first.node_id}"].disabled is False


def test_researched_nodes_feed_back_into_the_settlement(game_env):
    """End to end through the browser layer: research something, and the
    season that follows is run with its effects applied."""
    state = game_env.state
    state.resources["knowledge"] = 500.0
    game_env.module.render()

    game_env.elements["research-foraging_lore"].dispatch("click", None)

    assert game_env.module.current_effects()["food_yield_mult"] > 1.0

    baseline = sim.CityState().advance_season()["food_gathered"]
    game_env.advance_season()

    assert state.last_report["food_gathered"] > baseline


def test_rendering_the_research_panel_destroys_the_proxy_it_replaces(game_env):
    """render_research() rebuilds every row from scratch each render (see its
    own docstring) — including a fresh create_proxy()-wrapped click handler
    for every unresearched node's Study button. A real Pyodide proxy isn't
    garbage-collected on its own; leaving the previous render's proxy
    unreferenced without destroying it is a real, slow memory leak over a
    play session. render_research() must destroy the proxy for a given node
    before replacing it with the next render's."""
    module = game_env.module
    first = module.tree.available_nodes()[0]

    module.render()
    proxies = module._research_button_proxies
    assert first.node_id in proxies
    first_proxy = proxies[first.node_id]
    assert first_proxy.destroyed is False

    module.render()
    second_proxy = proxies[first.node_id]

    assert first_proxy.destroyed is True
    assert second_proxy is not first_proxy
    assert second_proxy.destroyed is False


def test_a_researched_nodes_proxy_is_destroyed_once_it_no_longer_needs_one(game_env):
    """Once a node is researched its button no longer gets a click handler
    at all (it's disabled and reads "Known") — the proxy that used to back
    it has to be destroyed and dropped rather than left dangling forever."""
    module = game_env.module
    state = game_env.state
    state.resources["knowledge"] = 500.0
    module.render()

    first = module.tree.available_nodes()[0]
    proxy = module._research_button_proxies[first.node_id]

    game_env.elements[f"research-{first.node_id}"].dispatch("click", None)

    assert proxy.destroyed is True
    assert first.node_id not in module._research_button_proxies
