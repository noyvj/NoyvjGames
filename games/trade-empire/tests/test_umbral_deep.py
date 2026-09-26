"""J1: a fourth self-contained cluster, the Umbral Deep, gated behind a
two-step research chain (Deep Survey, then Umbral Reach) that costs more
than any earlier cluster's gate. Same shape as Kepler and the Rift
Colonies (own goods, closed triangle, colony state created only on
unlock), plus the save-safety a new cluster needs: nothing new is written
for a save that hasn't reached it, and every value read back is validated.
"""
import math

import pytest

DEEP = ["deep_a", "deep_b", "deep_c"]


def _unlock_chain(module):
    module.research_points = 1_000_000
    for node in ("galaxy_expansion", "outer_reaches", "deep_survey", "umbral_reach"):
        assert module.unlock_research(node) is True


# --- gating -----------------------------------------------------------


def test_the_deep_is_locked_by_default(game_env):
    module = game_env.module
    for colony_id in DEEP:
        assert colony_id not in module.active_colony_ids()
        assert colony_id not in module.colony_states


def test_the_research_gate_is_costlier_than_every_earlier_cluster_gate(game_env):
    nodes = game_env.module.RESEARCH_NODES
    assert nodes["umbral_reach"]["cost"] > nodes["outer_reaches"]["cost"] > nodes["galaxy_expansion"]["cost"]
    # Plus a prerequisite step of its own: the whole chain costs more than
    # the Rift's gate by a wide margin, not just by one node's price.
    chain = nodes["deep_survey"]["cost"] + nodes["umbral_reach"]["cost"]
    assert chain > 2 * nodes["outer_reaches"]["cost"]
    assert nodes["umbral_reach"]["cost"] == max(node["cost"] for node in nodes.values() if "excludes" not in node)


def test_the_chain_requires_outer_reaches_then_deep_survey(game_env):
    module = game_env.module
    module.research_points = 1_000_000
    assert module.RESEARCH_NODES["deep_survey"]["requires"] == "outer_reaches"
    assert module.RESEARCH_NODES["umbral_reach"]["requires"] == "deep_survey"
    assert module.unlock_research("umbral_reach") is False
    assert module.unlock_research("deep_survey") is False  # Outer Reaches not yet researched
    module.unlock_research("galaxy_expansion")
    module.unlock_research("outer_reaches")
    assert module.unlock_research("umbral_reach") is False  # Deep Survey still missing
    assert module.unlock_research("deep_survey") is True
    assert module.umbral_reach_unlocked() is False  # Deep Survey alone opens nothing
    assert all(c not in module.active_colony_ids() for c in DEEP)
    assert module.unlock_research("umbral_reach") is True
    assert module.umbral_reach_unlocked() is True


def test_unlocking_costs_the_research_points_and_needs_enough_of_them(game_env):
    module = game_env.module
    module.unlocked_research.update({"galaxy_expansion", "outer_reaches", "deep_survey"})
    module.research_points = module.RESEARCH_NODES["umbral_reach"]["cost"] - 1
    assert module.can_unlock_research("umbral_reach") is False
    module.research_points += 1
    assert module.unlock_research("umbral_reach") is True
    assert module.research_points == 0


def test_unlocking_makes_the_cluster_reachable_and_creates_colony_state(game_env):
    module = game_env.module
    _unlock_chain(module)
    for colony_id in DEEP:
        assert colony_id in module.active_colony_ids()
        assert module.colony_states[colony_id].need_satisfaction == module.STARTING_NEED_SATISFACTION


def test_fleet_priority_ignores_the_deep_before_it_is_unlocked(game_env):
    module = game_env.module
    module.set_fleet_priority(True)
    game_env.tick(50)
    assert module.most_urgent_colony() in module.COLONIES


def test_ship_cannot_depart_to_the_deep_before_unlock(game_env):
    ship = game_env.ship("1")
    ship.load()
    assert ship.depart("deep_a") is False
    assert ship.docked


def test_a_ship_can_depart_to_the_deep_once_unlocked(game_env):
    module = game_env.module
    _unlock_chain(module)
    ship = game_env.ship("1")
    ship.load()
    assert ship.depart("deep_a") is True
    assert ship.in_transit


# --- data / identity ----------------------------------------------------


def test_the_deep_is_a_closed_triangle_of_its_own_new_goods(game_env):
    module = game_env.module
    produced = {c["produces"] for c in module.DEEP_COLONIES.values()}
    needed = {c["needs"] for c in module.DEEP_COLONIES.values()}
    assert produced == needed and len(produced) == 3
    for other in (module.COLONIES, module.EXPANSION_COLONIES, module.RIFT_COLONIES):
        other_goods = {c["produces"] for c in other.values()} | {c["needs"] for c in other.values()}
        assert produced.isdisjoint(other_goods)


def test_good_lookups_stay_single_valued_across_all_four_systems(game_env):
    module = game_env.module
    for good in module.SELL_PRICE:
        assert len([c for c in module.ALL_COLONIES.values() if c["needs"] == good]) <= 1
        assert len([c for c in module.ALL_COLONIES.values() if c["produces"] == good]) <= 1
    for good in (module.NEUTRONIUM, module.SUPERFLUID, module.AEROGEL):
        assert module.colony_producing(good) in DEEP
        assert module.colony_needing(good) in DEEP


def test_its_goods_are_priced_above_every_earlier_cluster_tier(game_env):
    module = game_env.module
    earlier = [
        module.SELL_PRICE[g] for c in (module.COLONIES, module.EXPANSION_COLONIES, module.RIFT_COLONIES)
        for colony in c.values() for g in (colony["produces"],)
    ]
    assert module.SELL_PRICE[module.NEUTRONIUM] > max(earlier)
    assert module.SELL_PRICE[module.NEUTRONIUM] > module.SELL_PRICE[module.SUPERFLUID] > module.SELL_PRICE[module.AEROGEL]
    for good in (module.NEUTRONIUM, module.SUPERFLUID, module.AEROGEL):
        assert good in module.GOOD_LABEL and good in module.market_multiplier
        assert good in module.good_profit_total and good in module.price_history


def test_every_deep_colony_has_full_metadata(game_env):
    module = game_env.module
    for colony_id in DEEP:
        assert module.COLONY_FLAVOR[colony_id]
        assert module.SPECIALIZATION[colony_id]["name"]
        assert module.SECONDARY_NEED[colony_id] in module.SELL_PRICE
        assert colony_id in module.NODE_POSITIONS
    # The furthest colonies are the highest-reward, highest-maintenance ones.

    def spec(colonies, key):
        return [module.SPECIALIZATION[c][key] for c in colonies]
    assert max(spec(DEEP, "output_bonus")) > max(spec(module.RIFT_COLONIES, "output_bonus"))
    assert max(spec(DEEP, "decay_multiplier")) > max(spec(module.RIFT_COLONIES, "decay_multiplier"))


def test_secondary_needs_reach_back_into_the_rift(game_env):
    module = game_env.module
    rift_goods = {c["produces"] for c in module.RIFT_COLONIES.values()}
    assert {module.SECONDARY_NEED[c] for c in DEEP} == rift_goods


def test_a_developed_deep_colony_takes_a_rift_good_as_its_secondary_need(game_env):
    module = game_env.module
    _unlock_chain(module)
    state = module.colony_states["deep_a"]
    state.development_level = 2
    state.secondary_need_satisfaction = 0.0
    ship = game_env.ship("1")
    ship.location = "rift_a"  # produces crystal
    ship.load()
    module.colony_states["deep_b"].development_level = 2
    module.colony_states["deep_b"].secondary_need_satisfaction = 0.0
    assert ship.depart("deep_b")
    for _ in range(module.travel_ticks() + 5):
        module.tick()
        if ship.docked:
            break
    assert ship.location == "deep_b"
    assert module.colony_states["deep_b"].secondary_need_satisfaction > 0.0


# --- map / render ---------------------------------------------------------


def test_map_positions_fit_the_canvas_and_do_not_overlap(game_env):
    module = game_env.module
    positions = module.NODE_POSITIONS
    for cid, (x, y) in positions.items():
        assert module.NODE_RADIUS <= x <= module.CANVAS_WIDTH - module.NODE_RADIUS, cid
        assert module.NODE_RADIUS <= y <= module.CANVAS_HEIGHT - module.NODE_RADIUS, cid
    ids = list(positions)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            assert math.dist(positions[a], positions[b]) > 2 * module.NODE_RADIUS, (a, b)


def test_map_labels_are_unique_across_every_colony(game_env):
    module = game_env.module
    labels = [module.colony_map_label(c) for c in module.ALL_COLONIES]
    assert len(labels) == len(set(labels))


def test_locked_deep_stays_off_the_map_and_unlocked_is_drawn(game_env):
    module = game_env.module
    module.render()
    ctx = game_env.elements["map-canvas"].getContext("2d")
    drawn = {text for n, (text, x, y) in ((n, a) for n, a in ctx.calls if n == "fillText")}
    assert not drawn & {"Nadir", "Hush", "Tenebra"}
    assert all(c not in dict(module.route_edges()) for c in DEEP)
    ctx.calls.clear()
    _unlock_chain(module)
    module.render()
    drawn = {text for n, (text, x, y) in ((n, a) for n, a in ctx.calls if n == "fillText")}
    assert {"Nadir", "Hush", "Tenebra"} <= drawn
    edges = module.route_edges()
    assert {("deep_a", "deep_c"), ("deep_b", "deep_a"), ("deep_c", "deep_b")} <= set(edges)


def test_panels_are_hidden_until_unlocked_then_shown(game_env):
    module = game_env.module
    module.render()
    assert game_env.elements["expansion3-colonies-panel"].hidden is True
    assert game_env.elements["expansion3-market-panel"].hidden is True
    _unlock_chain(module)
    module.render()
    assert game_env.elements["expansion3-colonies-panel"].hidden is False
    assert game_env.elements["expansion3-market-panel"].hidden is False
    assert game_env.elements["colony-deep_a-name"].innerText == "Nadir Foundry"
    assert game_env.elements["colony-deep_a-flavor"].innerText == module.COLONY_FLAVOR["deep_a"]
    assert game_env.elements["ship-1-depart-deep_a-button"].innerText == "Depart to Nadir Foundry"


def test_research_rows_render_for_the_new_nodes_with_prerequisite_hints(game_env):
    module = game_env.module
    module.render()
    assert "Deep Survey" in game_env.elements["research-deep_survey-status"].innerText
    assert "requires Outer Reaches" in game_env.elements["research-deep_survey-status"].innerText
    assert "requires Deep Survey" in game_env.elements["research-umbral_reach-status"].innerText
    assert game_env.elements["research-umbral_reach-unlock-button"].disabled is True


def test_almanac_lists_the_deep_goods_only_once_reachable(game_env):
    module = game_env.module
    assert not any(row["system"] == "Umbral Deep" for row in module.almanac_rows())
    _unlock_chain(module)
    rows = {row["good"]: row for row in module.almanac_rows()}
    assert rows["Neutronium"]["made_by"] == "Nadir Foundry"
    assert rows["Neutronium"]["needed_by"] == "Tenebra Loom"
    assert rows["Neutronium"]["system"] == "Umbral Deep"


# --- systems, trade posts, diplomacy --------------------------------------


def test_colonies_are_labelled_with_their_own_system(game_env):
    module = game_env.module
    assert module._system_label_for_colony("aurum") == "Home system"
    assert module._system_label_for_colony("kepler_a") == "Kepler Cluster"
    assert module._system_label_for_colony("rift_a") == "Rift Colonies"
    for colony_id in DEEP:
        assert module._system_label_for_colony(colony_id) == "Umbral Deep"


def test_the_deep_is_the_fourth_trade_post_system_and_needs_umbral_reach(game_env):
    module = game_env.module
    assert module.TRADE_POST_SYSTEMS[-1] == "Umbral Deep"
    module.unlocked_research.update({"galaxy_expansion", "outer_reaches", "deep_survey"})
    assert module._system_is_reachable("Rift Colonies") is True
    assert module._system_is_reachable("Umbral Deep") is False
    module.trade_posts[:] = ["Home system", "Kepler Cluster", "Rift Colonies"]
    assert module.next_trade_post_system() is None
    module.unlocked_research.add("umbral_reach")
    assert module.next_trade_post_system() == "Umbral Deep"


def test_rift_is_not_treated_as_reachable_just_because_of_the_deep_check(game_env):
    module = game_env.module
    module.unlocked_research.add("umbral_reach")  # tampered: skipped the rest of the chain
    assert module._system_is_reachable("Rift Colonies") is False


def test_a_delivery_between_the_rift_and_the_deep_counts_as_cross_system(game_env):
    module = game_env.module
    _unlock_chain(module)
    ship = game_env.ship("1")
    ship.location = "rift_a"
    ship.load()
    before = module.cross_system_units
    ship.depart("deep_b")
    for _ in range(module.travel_ticks() + 5):
        module.tick()
        if ship.docked:
            break
    assert module.cross_system_units > before


def test_a_full_deep_trip_pays_neutronium_prices(game_env):
    module = game_env.module
    _unlock_chain(module)
    ship = game_env.ship("1")
    ship.location = "deep_a"
    ship.load()
    assert ship.cargo_good == module.NEUTRONIUM
    profit_before = module.total_profit
    ship.depart("deep_c")
    for _ in range(module.travel_ticks() + 5):
        module.tick()
        if ship.docked:
            break
    assert module.total_profit > profit_before
    assert module.colony_states["deep_c"].cumulative_delivered > 0


# --- save / load ------------------------------------------------------------


def test_a_save_that_never_reached_the_deep_carries_nothing_about_it(game_env):
    module = game_env.module
    saved = module.get_state()
    assert not any("deep" in colony_id for colony_id in saved["colony_states"])
    assert "umbral_reach" not in saved["unlocked_research"] and "deep_survey" not in saved["unlocked_research"]
    assert "neutronium" not in saved["stockpile"]


def test_save_round_trip_keeps_the_deep_and_its_colony_state(game_env):
    module = game_env.module
    _unlock_chain(module)
    module.colony_states["deep_b"].need_satisfaction = 0.8
    module.colony_states["deep_b"].development_level = 2
    module.colony_states["deep_b"].cumulative_delivered = 130.0
    module.stockpile[module.NEUTRONIUM] = 3
    saved = module.get_state()
    assert {"umbral_reach", "deep_survey"} <= set(saved["unlocked_research"])
    assert set(DEEP) <= set(saved["colony_states"])
    module.load_state({"unlocked_research": []})  # wipe back to locked
    assert "deep_b" not in module.colony_states
    module.load_state(saved)
    assert module.umbral_reach_unlocked()
    assert module.colony_states["deep_b"].need_satisfaction == pytest.approx(0.8)
    assert module.colony_states["deep_b"].development_level == 2
    assert module.stockpile[module.NEUTRONIUM] == 3


def test_loading_a_save_without_the_deep_prunes_its_colonies(game_env):
    module = game_env.module
    _unlock_chain(module)
    assert "deep_a" in module.colony_states
    saved = module.get_state()
    saved["unlocked_research"] = ["galaxy_expansion", "outer_reaches"]
    module.load_state(saved)
    for colony_id in DEEP:
        assert colony_id not in module.colony_states
        assert colony_id not in module.active_colony_ids()
    assert "rift_a" in module.colony_states  # the earlier clusters are untouched


def test_a_ship_saved_at_a_locked_deep_colony_is_sent_home(game_env):
    module = game_env.module
    saved = module.get_state()
    saved["ships"]["1"].update({"location": "deep_a", "cargo_good": "neutronium", "cargo_qty": 9})
    saved["ships"]["2"].update(
        {"location": None, "origin": "deep_a", "destination": "deep_b", "transit_ticks_remaining": 2, "transit_total_ticks": 5}
    )
    module.load_state(saved)
    for ship_id in ("1", "2"):
        ship = module.ships[ship_id]
        assert ship.location == "aurum" and ship.cargo_qty == 0 and ship.cargo_good is None
        assert ship.origin is None and ship.destination is None and ship.transit_ticks_remaining == 0
    module.ships["1"].load()  # would have raised KeyError before the sanitising step


def test_a_ship_saved_inside_an_unlocked_deep_is_kept(game_env):
    module = game_env.module
    _unlock_chain(module)
    module.ships["1"].location = "deep_a"
    saved = module.get_state()
    module.load_state(saved)
    assert module.ships["1"].location == "deep_a"


@pytest.mark.parametrize("bad", [
    "umbral_reach", 7, None, {"umbral_reach": 1}, True,
    [["umbral_reach"]], [{"a": 1}], [None, 3, 4.5, True, "nonsense"], [["deep_survey"], "umbral_reach", "x" * 5000],
])
def test_tampered_unlocked_research_never_crashes_or_invents_research(game_env, bad):
    module = game_env.module
    saved = module.get_state()
    saved["unlocked_research"] = bad
    assert module.load_state(saved) is True
    assert module.unlocked_research <= set(module.RESEARCH_NODES)
    assert module.umbral_reach_unlocked() is (isinstance(bad, list) and "umbral_reach" in bad)


def test_tampered_unlocked_research_keeps_only_real_string_ids(game_env):
    module = game_env.module
    saved = module.get_state()
    saved["unlocked_research"] = ["fast_ships", ["hauler"], 5, "not_a_node", "fast_ships"]
    module.load_state(saved)
    assert module.unlocked_research == {"fast_ships"}


@pytest.mark.parametrize("field,bad", [
    ("need_satisfaction", True), ("need_satisfaction", "0.9"), ("need_satisfaction", 5.0),
    ("need_satisfaction", -0.5), ("need_satisfaction", float("nan")), ("need_satisfaction", float("inf")),
    ("need_satisfaction", None), ("need_satisfaction", [0.5]), ("need_satisfaction", {"x": 1}),
    ("secondary_need_satisfaction", True), ("secondary_need_satisfaction", 2), ("secondary_need_satisfaction", "x"),
    ("cumulative_delivered", True), ("cumulative_delivered", -1), ("cumulative_delivered", float("nan")),
    ("cumulative_delivered", 10**12), ("cumulative_delivered", "100"),
    ("development_level", True), ("development_level", 9), ("development_level", 0), ("development_level", 1.5),
    ("development_level", "2"), ("development_level", None),
    ("neglect_ticks", True), ("neglect_ticks", -3), ("neglect_ticks", 10**9), ("neglect_ticks", "5"),
])
def test_tampered_deep_colony_fields_fall_back_to_defaults(game_env, field, bad):
    module = game_env.module
    _unlock_chain(module)
    saved = module.get_state()
    saved["colony_states"]["deep_c"][field] = bad
    assert module.load_state(saved) is True
    state = module.colony_states["deep_c"]
    fresh = module.ColonyState("deep_c")
    assert getattr(state, field) == getattr(fresh, field)
    assert 0.0 <= state.need_satisfaction <= 1.0
    assert 0.0 <= state.secondary_need_satisfaction <= 1.0
    assert state.development_level in (1, 2)


def test_non_dict_colony_and_ship_entries_are_ignored_not_fatal(game_env):
    module = game_env.module
    _unlock_chain(module)
    saved = module.get_state()
    saved["colony_states"]["deep_a"] = ["not", "a", "dict"]
    saved["colony_states"]["deep_b"] = 5
    saved["ships"]["1"] = "junk"
    saved["ships"]["2"] = [1, 2]
    assert module.load_state(saved) is True
    assert module.colony_states["deep_a"].development_level == 1
    saved["ships"] = "junk"
    assert module.load_state(saved) is True


def test_in_range_values_survive_a_load_untouched(game_env):
    module = game_env.module
    _unlock_chain(module)
    saved = module.get_state()
    saved["colony_states"]["deep_a"].update(
        {"need_satisfaction": 1, "secondary_need_satisfaction": 0, "cumulative_delivered": 250, "development_level": 2, "neglect_ticks": 7}
    )
    module.load_state(saved)
    state = module.colony_states["deep_a"]
    assert (state.need_satisfaction, state.secondary_need_satisfaction, state.cumulative_delivered) == (1.0, 0.0, 250.0)
    assert state.development_level == 2 and state.neglect_ticks == 7


def test_trade_post_in_the_deep_round_trips(game_env):
    module = game_env.module
    module.trade_posts[:] = ["Home system", "Umbral Deep"]
    saved = module.get_state()
    module.trade_posts[:] = []
    module.load_state(saved)
    assert module.trade_posts == ["Home system", "Umbral Deep"]
