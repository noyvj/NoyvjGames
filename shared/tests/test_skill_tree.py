"""shared/skill_tree.py: the Python rules of the shared skill-tree component
(planning/TODO.md W-3). The JavaScript mirror is pinned to the same results in
test_skill_tree_browser.py."""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import skill_tree as st  # noqa: E402

# Shaped like Trade Empire's charter tree (two branches, one node with two prerequisites).
TREE = {
    "id": "charter", "title": "Charter perks", "currency": "charter points",
    "branches": [{"id": "routes", "title": "Routes"}, {"id": "automation", "title": "Automation"}],
    "nodes": [
        {"id": "lanes", "branch": "routes", "cost": 1, "label": "Surveyed Lanes", "description": "+1 cargo.", "requires": []},
        {"id": "waystation", "branch": "routes", "cost": 2, "label": "Waystation", "description": "Posts cheaper.", "requires": ["lanes"], "effect": "post_discount"},
        {"id": "convoy", "branch": "routes", "cost": 3, "label": "Standing Convoy", "description": "Ship 1 automated.", "requires": ["waystation", "orders"]},
        {"id": "orders", "branch": "automation", "cost": 1, "label": "Standing Orders", "description": "Automation 20% cheaper."},
        {"id": "lab", "branch": "automation", "cost": 2, "label": "Lab Automation", "description": "Research faster.", "requires": ["orders"]},
    ],
}


def test_the_sample_tree_is_valid_and_tiers_follow_depth():
    assert st.validate(TREE) == []
    assert [st.tier_of(TREE, i) for i in ("lanes", "waystation", "convoy", "orders", "lab")] == [1, 2, 3, 1, 2]
    assert st.tier_of(TREE, "nope") == 0


def test_a_declared_tier_wins_over_depth():
    tree = copy.deepcopy(TREE)
    tree["nodes"][1]["tier"] = 4
    assert st.tier_of(tree, "waystation") == 4
    assert st.tier_of(tree, "convoy") == 5


def test_validate_reports_each_kind_of_bad_data():
    assert st.validate({}) == ["tree has no nodes"]
    bad = {"nodes": [
        {"id": "a", "cost": 0, "label": "A"},
        {"id": "a", "cost": 1, "label": "A2"},
        {"id": "b", "cost": 1.5, "label": "B", "requires": ["ghost"]},
        {"id": "c", "cost": 1, "label": "C", "requires": ["c"]},
        {"id": "d", "cost": 1},
        {"cost": 1, "label": "no id"},
    ]}
    text = " | ".join(st.validate(bad))
    for part in ("duplicate node id a", "node a needs an integer cost", "node b needs an integer cost",
                 "unknown node ghost", "requires itself", "node d needs a label", "no string id"):
        assert part in text


def test_validate_finds_cycles():
    cyc = {"nodes": [
        {"id": "x", "cost": 1, "label": "X", "requires": ["y"]},
        {"id": "y", "cost": 1, "label": "Y", "requires": ["x"]},
        {"id": "z", "cost": 1, "label": "Z"},
    ]}
    errors = st.validate(cyc)
    assert len(errors) == 1 and "cycle" in errors[0] and "x, y" in errors[0]


def test_status_values():
    assert st.status(TREE, [], "lanes", 5) == "available"
    assert st.status(TREE, [], "waystation", 5) == "locked"
    assert st.status(TREE, ["lanes"], "waystation", 1) == "unaffordable"  # earned 1, lanes already spent it
    assert st.status(TREE, ["lanes"], "waystation", 3) == "available"
    assert st.status(TREE, ["lanes"], "lanes", 3) == "owned"
    assert st.status(TREE, [], "convoy", None) == "locked"
    assert st.status(TREE, [], "ghost", None) == "locked"
    assert st.status(TREE, [], "lanes", None) == "available", "unlimited points"


def test_buy_follows_prerequisites_and_costs_and_does_not_mutate():
    owned = []
    r = st.buy(TREE, owned, "waystation", 10)
    assert not r["ok"] and r["reason"] == "locked" and owned == []
    r = st.buy(TREE, owned, "lanes", 10)
    assert r["ok"] and r["owned"] == ["lanes"] and r["spent"] == 1 and r["points_left"] == 9 and owned == []
    r2 = st.buy(TREE, r["owned"], "lanes", 10)
    assert not r2["ok"] and r2["reason"] == "owned"
    r3 = st.buy(TREE, r["owned"], "waystation", 2)
    assert not r3["ok"] and r3["reason"] == "points"
    assert st.buy(TREE, [], "ghost", 10)["reason"] == "unknown"
    assert st.buy(TREE, [], 5, 10)["reason"] == "unknown"


def test_the_two_prerequisite_node_needs_both():
    owned = ["lanes", "waystation"]
    assert st.missing_requirements(TREE, owned, "convoy") == ["orders"]
    assert not st.can_buy(TREE, owned, "convoy", 99)
    owned = st.buy(TREE, owned, "orders", 99)["owned"]
    assert st.missing_requirements(TREE, owned, "convoy") == []
    assert st.can_buy(TREE, owned, "convoy", 99)
    assert not st.can_buy(TREE, owned, "convoy", 4), "costs 3 with only 1 point left"


def test_the_whole_tree_is_buyable_with_exactly_its_total_cost_in_any_legal_order():
    total = st.totals(TREE, [])["total_cost"]
    assert total == 9
    owned = []
    for node in ("orders", "lab", "lanes", "waystation", "convoy"):
        result = st.buy(TREE, owned, node, total)
        assert result["ok"], node
        owned = result["owned"]
    t = st.totals(TREE, owned, total)
    assert t["complete"] and t["points_left"] == 0 and t["remaining_cost"] == 0 and t["owned_count"] == 5


def test_refund_one_only_when_nothing_owned_needs_it():
    owned = ["lanes", "waystation"]
    assert not st.can_refund(TREE, owned, "lanes")
    r = st.refund(TREE, owned, "lanes")
    assert not r["ok"] and r["reason"] == "needed" and r["owned"] == owned
    r = st.refund(TREE, owned, "waystation")
    assert r["ok"] and r["owned"] == ["lanes"] and r["refunded"] == 2
    assert st.refund(TREE, ["lanes"], "lab")["reason"] == "not-owned"


def test_refund_all_empties_the_tree_and_returns_the_whole_spend():
    owned = ["orders", "lab", "lanes"]
    r = st.refund_all(TREE, owned)
    assert r == {"ok": True, "owned": [], "refunded": 4, "reason": ""}
    assert owned == ["orders", "lab", "lanes"]
    assert st.refund_all(TREE, [])["refunded"] == 0


def test_spent_ignores_duplicates_and_unknown_ids():
    assert st.spent(TREE, ["lanes", "lanes", "ghost", 7]) == 1
    assert st.points_left(TREE, ["lanes"], 5) == 4
    assert st.points_left(TREE, ["lanes"], None) is None


def test_sanitize_owned_cleans_a_tampered_save():
    assert st.sanitize_owned(TREE, ["lanes", "lanes", "ghost", 3, None, ["x"]], 99) == ["lanes"]
    # waystation without lanes loses its footing; convoy goes with it
    assert st.sanitize_owned(TREE, ["waystation", "convoy", "orders"], 99) == ["orders"]
    assert st.sanitize_owned(TREE, "not a list", 5) == []
    assert st.sanitize_owned(TREE, None) == []


def test_sanitize_owned_overspend_clears_or_trims():
    owned = ["lanes", "waystation", "orders", "lab"]  # costs 1+2+1+2 = 6
    assert st.sanitize_owned(TREE, owned, 4) == []
    assert st.sanitize_owned(TREE, owned, 4, overspend="trim") == ["lanes", "waystation", "orders"]
    assert st.sanitize_owned(TREE, owned, 3, overspend="trim") == ["lanes", "waystation"]
    assert st.sanitize_owned(TREE, owned, 6) == owned
    # trimming a prerequisite takes its dependents with it
    assert st.sanitize_owned(TREE, ["lanes", "waystation"], 0, overspend="trim") == []


def test_effects_come_back_in_tree_order_with_default_effect_ids():
    assert st.effects(TREE, ["lab", "waystation", "lanes"]) == ["lanes", "post_discount", "lab"]
    assert st.has_effect(TREE, ["waystation"], "post_discount")
    assert not st.has_effect(TREE, [], "post_discount")


def test_totals_by_branch():
    t = st.totals(TREE, ["lanes", "orders", "lab"], 10)
    assert t["owned_count"] == 3 and t["node_count"] == 5 and t["spent"] == 4 and t["points_left"] == 6
    assert t["by_branch"]["routes"] == {"owned": 1, "nodes": 3, "spent": 1, "cost": 6}
    assert t["by_branch"]["automation"] == {"owned": 2, "nodes": 2, "spent": 3, "cost": 3}
    assert not t["complete"]
    assert st.totals({"nodes": []}, [])["complete"] is False


def test_functions_are_deterministic():
    runs = [st.buy(TREE, ["lanes"], "waystation", 5) for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]
