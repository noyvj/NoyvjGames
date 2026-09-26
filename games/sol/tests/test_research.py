"""Research (U10): a real tree per distance level instead of a bar filled 50
Iron at a time. Level 1 (Near Bodies) and level 2 (Far Bodies) are 20-node
trees that split and rejoin and end at the level's final node, which is what
unlocks the bodies. Node costs vary but each level totals the old bar's cost."""

import pytest


def _m(game_env):
    return game_env.module


def _buy_path(game_env, target_id):
    """Buys every prerequisite of `target_id` (and it) for free-enough Iron."""
    m = _m(game_env)
    order = []

    def visit(node_id):
        if node_id in order or node_id in m.researched_nodes:
            return
        node = m.RESEARCH_NODE_BY_ID[node_id]
        for req in node["requires"]:
            visit(req)
        order.append(node_id)

    visit(target_id)
    for node_id in order:
        game_env.earth["resource_count"] = 10_000
        game_env.research_node(node_id)


def _complete_level(game_env, level):
    m = _m(game_env)
    for i in range(level + 1):
        _buy_path(game_env, m.RESEARCH_TIERS[i]["final"])


# --- shape of the data -------------------------------------------------

def test_two_levels_of_twenty_nodes(game_env):
    m = _m(game_env)
    assert len(m.RESEARCH_TIERS) == 2
    for level in range(2):
        assert sum(1 for n in m.RESEARCH_NODES if n["tier"] == level) == 20


def test_each_level_costs_the_same_total_as_the_old_bar(game_env):
    m = _m(game_env)
    assert m.RESEARCH_TIERS[0]["target"] == 1000
    assert m.RESEARCH_TIERS[1]["target"] == 5000


def test_level_names_and_unlocks(game_env):
    m = _m(game_env)
    assert m.RESEARCH_TIERS[0]["name"] == "Near Bodies"
    assert set(m.RESEARCH_TIERS[0]["unlocks"]) == {"Moon", "Mars"}
    assert m.RESEARCH_TIERS[1]["name"] == "Far Bodies"
    assert set(m.RESEARCH_TIERS[1]["unlocks"]) == {"Venus", "AsteroidBelt", "Pluto", "JupiterMoons", "SaturnMoons"}


def test_every_requirement_exists_and_the_graph_has_no_cycles(game_env):
    m = _m(game_env)
    for node in m.RESEARCH_NODES:
        for req in node["requires"]:
            assert req in m.RESEARCH_NODE_BY_ID
    seen = set()
    remaining = list(m.RESEARCH_NODES)
    while remaining:
        ready = [n for n in remaining if all(r in seen for r in n["requires"])]
        assert ready, "cycle or unreachable node"
        seen.update(n["id"] for n in ready)
        remaining = [n for n in remaining if n["id"] not in seen]


def test_the_tree_splits_and_rejoins(game_env):
    m = _m(game_env)
    for level in range(2):
        nodes = [n for n in m.RESEARCH_NODES if n["tier"] == level]
        assert any(len(n["requires"]) >= 2 for n in nodes), "no join in level %d" % level
        children = {}
        for n in nodes:
            for r in n["requires"]:
                children.setdefault(r, []).append(n["id"])
        assert any(len(c) >= 2 for c in children.values()), "no split in level %d" % level


def test_each_level_ends_at_its_final_node(game_env):
    m = _m(game_env)
    assert m.RESEARCH_TIERS[0]["final"] == "near_bodies"
    assert m.RESEARCH_TIERS[1]["final"] == "far_bodies"
    for level, tier in enumerate(m.RESEARCH_TIERS):
        nodes = [n for n in m.RESEARCH_NODES if n["tier"] == level]
        assert nodes[-1]["id"] == tier["final"]
        others_requiring_final = [n for n in nodes if tier["final"] in n["requires"]]
        assert others_requiring_final == []


def test_costs_vary_within_a_level(game_env):
    m = _m(game_env)
    assert len({n["cost"] for n in m.RESEARCH_NODES if n["tier"] == 0}) > 1
    assert len({n["cost"] for n in m.RESEARCH_NODES if n["tier"] == 1}) > 1


def test_most_nodes_have_no_dead_ids_and_effect_keys_are_known(game_env):
    m = _m(game_env)
    for n in m.RESEARCH_NODES:
        assert set(n["effects"]) <= {"yield_pct", "machinery_discount", "route_discount"}
    assert any(n["effects"] for n in m.RESEARCH_NODES)


# --- initial state and display -----------------------------------------

def test_starts_with_nothing_researched(game_env):
    m = _m(game_env)
    assert m.researched_nodes == set() and m.completed_tiers == 0 and m.research_progress == 0.0
    assert m.unlocked_bodies == set()
    assert game_env.elements["research-progress"].innerText == "0 / 1000"
    assert game_env.elements["research-bar"].style.width == "0.0%"
    assert "Near Bodies" in game_env.elements["research-label"].innerText


def test_only_the_root_is_available_at_first(game_env):
    m = _m(game_env)
    available = [n["id"] for n in m.RESEARCH_NODES if m.research_node_status(n) == "available"]
    assert available == ["survey"]


def test_level_two_is_locked_until_level_one_is_done(game_env):
    m = _m(game_env)
    assert m.research_node_status(m.RESEARCH_NODE_BY_ID["far_survey"]) == "locked"


# --- buying nodes -------------------------------------------------------

def test_buying_a_node_spends_its_iron_and_marks_it(game_env):
    m = _m(game_env)
    game_env.earth["resource_count"] = 100
    game_env.research_node("survey")
    assert "survey" in m.researched_nodes
    assert game_env.earth["resource_count"] == 100 - m.RESEARCH_NODE_BY_ID["survey"]["cost"]
    assert m.research_progress == m.RESEARCH_NODE_BY_ID["survey"]["cost"]


def test_cannot_buy_without_enough_iron(game_env):
    m = _m(game_env)
    game_env.earth["resource_count"] = 5
    game_env.research_node("survey")
    assert "survey" not in m.researched_nodes and game_env.earth["resource_count"] == 5


def test_cannot_buy_a_locked_node_or_buy_twice_or_unknown(game_env):
    m = _m(game_env)
    game_env.earth["resource_count"] = 10_000
    game_env.research_node("better_picks")  # needs survey first
    assert "better_picks" not in m.researched_nodes
    game_env.research_node("survey")
    iron = game_env.earth["resource_count"]
    game_env.research_node("survey")
    assert game_env.earth["resource_count"] == iron
    game_env.research_node("no_such_node")
    game_env.panel_click("research-node-list")  # no data-node at all
    assert m.researched_nodes == {"survey"}


def test_a_join_needs_every_parent(game_env):
    m = _m(game_env)
    _buy_path(game_env, "pneumatic_drills")
    game_env.earth["resource_count"] = 10_000
    game_env.research_node("automation_basics")  # also needs smelter_design
    assert "automation_basics" not in m.researched_nodes
    _buy_path(game_env, "smelter_design")
    game_env.research_node("automation_basics")
    assert "automation_basics" in m.researched_nodes


def test_finishing_the_final_node_unlocks_the_bodies(game_env):
    m = _m(game_env)
    _buy_path(game_env, "space_travel")
    assert m.completed_tiers == 0 and m.unlocked_bodies == set()
    game_env.earth["resource_count"] = 10_000
    game_env.research_node("near_bodies")
    assert m.completed_tiers == 1
    assert {"Moon", "Mars"} <= m.unlocked_bodies
    assert "far_survey" in [n["id"] for n in m.RESEARCH_NODES if m.research_node_status(n) == "available"]
    assert "Far Bodies" in game_env.elements["research-label"].innerText


def test_completing_everything_shows_the_terminal_state(game_env):
    m = _m(game_env)
    _complete_level(game_env, 1)
    assert m.completed_tiers == 2
    assert game_env.elements["research-progress"].innerText == "All Tiers Unlocked"
    assert game_env.elements["research-node-list"].children == []
    assert {"Venus", "Pluto", "SaturnMoons"} <= m.unlocked_bodies


def test_research_works_during_an_ecological_collapse(game_env):
    m = _m(game_env)
    m.planet_state["Earth"]["ecology_health"] = 0.0
    game_env.earth["resource_count"] = 100
    game_env.research_node("survey")
    assert "survey" in m.researched_nodes


def test_node_list_renders_rows_with_buttons(game_env):
    m = _m(game_env)
    game_env.earth["resource_count"] = 100
    m.update_research_display()
    rows = game_env.elements["research-node-list"].children
    assert len(rows) == 20
    buttons = [c for row in rows for c in row.children if getattr(c, "className", "").endswith("research-node-button")]
    assert len(buttons) == 20
    survey_button = buttons[0]
    assert survey_button.disabled is False
    assert buttons[1].disabled is True  # locked


def test_progress_bar_tracks_invested_iron(game_env):
    game_env.earth["resource_count"] = 1000
    game_env.research_node("survey")
    assert game_env.elements["research-progress"].innerText == "20 / 1000"
    assert game_env.elements["research-bar"].style.width == "2.0%"


# --- effects ------------------------------------------------------------

def test_yield_nodes_raise_manual_and_automated_yield(game_env):
    m = _m(game_env)
    assert m.research_yield_multiplier() == 1.0
    _buy_path(game_env, "pneumatic_drills")
    expected = 1.0 + (1 + 2) / 100  # better_picks + pneumatic_drills
    assert m.research_yield_multiplier() == pytest.approx(expected)
    before = game_env.earth["resource_count"]
    game_env.click()
    assert game_env.earth["resource_count"] - before == pytest.approx(expected)


def test_machinery_discount_makes_miners_cheaper(game_env):
    m = _m(game_env)
    m.planet_state["Earth"]["generator_count"] = 10
    m.planet_state["Earth"]["recycler_count"] = 10
    full_gen, full_rec = m.generator_cost("Earth"), m.recycler_cost("Earth")
    _buy_path(game_env, "smelter_design")
    assert m.generator_cost("Earth") < full_gen
    assert m.recycler_cost("Earth") < full_rec


def test_route_discount_makes_routes_cheaper(game_env):
    m = _m(game_env)
    full = m.trade_route_cost("Earth", "Mars")
    m.researched_nodes.update(["regolith_bricks"])
    assert m.trade_route_cost("Earth", "Mars") < full


def test_deep_research_perk_discounts_node_costs(game_env):
    m = _m(game_env)
    m.prestige_nodes.add("deep_research")
    node = m.RESEARCH_NODE_BY_ID["survey"]
    assert m.research_node_cost(node) == 14  # ceil(20 / 1.5)


def test_sandbox_makes_nodes_free(game_env):
    m = _m(game_env)
    m._sandbox_active = lambda: True
    game_env.earth["resource_count"] = 0
    game_env.research_node("survey")
    assert "survey" in m.researched_nodes


# --- save / load / migration -------------------------------------------

def test_save_round_trip_keeps_nodes(game_env):
    m = _m(game_env)
    _buy_path(game_env, "automation_basics")
    data = m.serialize_state()
    assert set(data["researched_nodes"]) == m.researched_nodes
    m.researched_nodes.clear()
    m._recompute_research()
    m.deserialize_state(data)
    assert "automation_basics" in m.researched_nodes and m.research_progress > 0


def test_tampered_nodes_are_pruned_to_a_valid_tree(game_env):
    m = _m(game_env)
    data = m.serialize_state()
    data["researched_nodes"] = ["automation_basics", "bogus", 7, None, "far_bodies", "far_survey"]
    m.deserialize_state(data)
    assert m.researched_nodes == set()  # every one was missing prerequisites or unknown
    data["researched_nodes"] = ["survey", "better_picks", "better_picks", "orbital_mechanics"]
    m.deserialize_state(data)
    assert m.researched_nodes == {"survey", "better_picks"}


def test_non_list_nodes_field_falls_back_to_the_legacy_path(game_env):
    m = _m(game_env)
    data = m.serialize_state()
    data["researched_nodes"] = "survey"
    data["completed_tiers"] = 0
    data["research_progress"] = 0.0
    m.deserialize_state(data)
    assert m.researched_nodes == set()


def test_legacy_save_with_a_completed_tier_keeps_it(game_env):
    m = _m(game_env)
    data = m.serialize_state()
    del data["researched_nodes"]
    data["completed_tiers"] = 1
    data["research_progress"] = 0.0
    data["unlocked_bodies"] = ["Moon", "Mars"]
    m.deserialize_state(data)
    assert m.completed_tiers == 1
    assert all(n["id"] in m.researched_nodes for n in m.RESEARCH_NODES if n["tier"] == 0)
    assert "far_survey" not in m.researched_nodes


def test_legacy_partial_progress_becomes_nodes_and_refunds_the_rest(game_env):
    m = _m(game_env)
    data = m.serialize_state()
    del data["researched_nodes"]
    data["completed_tiers"] = 0
    data["research_progress"] = 250.0
    iron_before = data["planet_state"]["Earth"]["resource_count"]
    m.deserialize_state(data)
    spent = sum(m.RESEARCH_NODE_BY_ID[n]["cost"] for n in m.researched_nodes)
    assert 0 < spent <= 250 and "near_bodies" not in m.researched_nodes
    assert m.planet_state["Earth"]["resource_count"] == pytest.approx(iron_before + (250.0 - spent))
    assert m.research_progress == spent


def test_legacy_migration_never_finishes_a_level_from_partial_progress(game_env):
    m = _m(game_env)
    data = m.serialize_state()
    del data["researched_nodes"]
    data["completed_tiers"] = 0
    data["research_progress"] = 999.0
    m.deserialize_state(data)
    assert m.completed_tiers == 0 and "near_bodies" not in m.researched_nodes


def test_bad_legacy_values_are_harmless(game_env):
    m = _m(game_env)
    for bad in ("x", None, float("nan"), -5, True):
        data = m.serialize_state()
        del data["researched_nodes"]
        data["completed_tiers"] = 0
        data["research_progress"] = bad
        m.deserialize_state(data)
        assert m.researched_nodes == set()


def test_prestige_clears_research(game_env):
    m = _m(game_env)
    _complete_level(game_env, 1)
    m.researched_nodes.clear()
    m._recompute_research()
    assert m.completed_tiers == 0 and m.research_progress == 0.0
