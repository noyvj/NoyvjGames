"""K-6: era doctrines."""

import pytest

import doctrines
import dynasty
import research
import sim

from .test_space_age_era import push_to_agrarian


def test_the_four_doctrines_discount_known_branches_and_stay_small():
    assert set(doctrines.DOCTRINES) == {"maritime", "highland", "caravan", "scholarly"}
    for info in doctrines.DOCTRINES.values():
        assert set(info["discounts"]) <= set(research.BRANCHES)
        assert 0 < sum(info["discounts"].values()) <= 24
        assert all(0 < p <= 15 for p in info["discounts"].values())
        for key in info["effects"]:
            assert key in sim.NEUTRAL_EFFECTS and key in research.EFFECT_LABELS


def test_choosing_is_one_per_era_after_the_first_and_final():
    ui = {}
    assert doctrines.is_open(ui, "tribal") is False
    assert doctrines.choose(ui, "tribal", "maritime")[0] is False
    assert doctrines.choose(ui, "agrarian", "nope")[0] is False
    assert doctrines.is_open(ui, "agrarian")
    assert doctrines.choose(ui, "agrarian", "maritime") == (True, "")
    assert doctrines.choose(ui, "agrarian", "highland")[0] is False
    assert doctrines.is_open(ui, "agrarian") is False and doctrines.is_open(ui, "classical")
    assert doctrines.history(ui) == [("agrarian", "maritime")]


@pytest.mark.parametrize("raw", [None, 5, [], {"chosen": []}, {"chosen": {"tribal": "maritime", "zzz": "maritime",
                                                                          "agrarian": "bogus", 4: "caravan"}}])
def test_hostile_records_clean_to_no_doctrines(raw):
    assert doctrines.clean(raw) == {"chosen": {}}


def test_each_kind_counts_once_and_a_second_adoption_entrenches_it():
    ui = {}
    doctrines.choose(ui, "agrarian", "maritime")
    one = doctrines.discounts(ui)
    assert one["provision"] == 15 and one["community"] == 5 and one["craft"] == 0
    doctrines.choose(ui, "classical", "maritime")
    two = doctrines.discounts(ui)
    assert two["provision"] == 22.5 and two["community"] == 7.5
    doctrines.choose(ui, "medieval", "maritime")
    assert doctrines.discounts(ui)["provision"] == 22.5  # entrenching stops at half again
    assert doctrines.effect_deltas(ui)["food_storage_bonus"] == pytest.approx(6.0)


def test_discounts_are_capped_and_the_dynasty_edge_deepens_main_branches():
    ui = {}
    for era, doctrine in zip(sim.ERA_ORDER[1:], ["maritime", "scholarly", "maritime", "scholarly", "highland", "highland", "caravan"]):
        doctrines.choose(ui, era, doctrine)
    assert max(doctrines.discounts(ui).values()) <= doctrines.MAX_DISCOUNT_PERCENT
    small = {}
    doctrines.choose(small, "agrarian", "maritime")
    assert doctrines.discounts(small, edge=5)["provision"] == 20
    assert doctrines.discounts(small, edge=5)["community"] == 5  # only a main branch gets the edge
    assert doctrines.cost_multipliers({}) == {}


def test_the_research_tree_charges_the_discounted_price_it_shows():
    tree = research.build_tree()
    base = tree.nodes["foraging_lore"].cost
    tree.cost_mults = {"provision": 0.85}
    node = next(n for n in tree.nodes.values() if n.branch == "provision" and n.era == "tribal" and not n.prerequisites)
    price = tree.cost_of(node.node_id)
    assert price == pytest.approx(round(node.cost * 0.85, 1))
    resources = {"knowledge": price}
    assert tree.can_afford(node.node_id, resources) and tree.research(node.node_id, resources)
    assert resources["knowledge"] == pytest.approx(0.0, abs=1e-9)
    other = next(n for n in tree.nodes.values() if n.branch == "craft")
    assert tree.cost_of(other.node_id) == other.cost
    assert base > 0


def test_adopting_in_the_game_writes_the_log_and_cheapens_the_study_button(game_env):
    module = game_env.module
    el = game_env.elements
    el["doctrines-toggle-button"].dispatch("click", None)
    assert "begin with your first era transition" in el["doctrines-status"].innerText
    assert el["doctrine-maritime-button"].disabled is True
    push_to_agrarian(game_env)
    assert game_env.state.era == "agrarian"
    el["doctrines-toggle-button"].dispatch("click", None)
    el["doctrines-toggle-button"].dispatch("click", None)
    assert "(choose)" in el["doctrines-toggle-button"].innerText or el["doctrines-panel"].hidden is False
    node = next(n for n in module.tree.visible_nodes() if n.branch == "provision" and module.tree.is_available(n.node_id)
                and not module.tree.is_researched(n.node_id))
    before_price = module.tree.cost_of(node.node_id)
    el["doctrine-maritime-button"].dispatch("click", None)
    assert doctrines.chosen_for(module.campaign.ui, "agrarian") == "maritime"
    assert module.tree.cost_of(node.node_id) < before_price
    assert f"Study ({module.tree.cost_of(node.node_id):g})" == el[f"research-{node.node_id}"].innerText
    entries = module.founders_entries()
    assert any("Doctrine of the Maritime adopted" in e["note"] for e in entries)
    assert el["doctrine-highland-button"].disabled is True  # final for the era
    assert module.current_effects()["food_storage_bonus"] >= sim.NEUTRAL_EFFECTS["food_storage_bonus"] + 4.0


def test_doctrines_stay_on_in_comparable_runs_but_the_dynasty_edge_rests(game_env):
    module = game_env.module
    module.campaign.ui[dynasty.KEY] = {"earned": 20, "owned": ["schools_of_thought"]}
    doctrines.choose(module.campaign.ui, "agrarian", "caravan")
    module._sync_tree_costs()
    assert module.tree.cost_mults["community"] == pytest.approx(0.8)  # 15 + 5 edge
    module._challenge_utc_today_override = "2026-10-08"
    game_env.elements["challenge-toggle-button"].dispatch("click", None)
    game_env.elements["challenge-daily-start-button"].dispatch("click", None)
    assert module._resting() is True
    module._sync_tree_costs()
    assert module.tree.cost_mults["community"] == pytest.approx(0.85)  # the doctrine stays, the perk's edge rests
