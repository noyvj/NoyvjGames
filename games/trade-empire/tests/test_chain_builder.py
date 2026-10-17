"""J-5: Chain Builder, a separate puzzle mode. What is pinned here: the recipe table and the 24 authored puzzles are
well formed; an exhaustive search proves EVERY puzzle solvable and gives its par, which must equal the stored par
and the stored par chain; the flow rules (round trips per cycle, source and refinery caps, whole refinery runs,
shared capacity served in listed order, the fleet limit); the medals; the three goals and the hint ladder; saves
(only when non-default, validated entry by entry, old saves unchanged); and that a puzzle sets the real game aside
and puts it back byte-identically, with nothing ticking, earned or lost."""
import json
import random
import sys
import types
from fractions import Fraction
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent


def dump(data):
    return json.dumps(data, sort_keys=True)


def puzzle_ids():
    # Collected before any game module exists, so read the ids from the data file the same way the module does.
    import re
    from .pagefiles import game_source
    text = game_source()
    return re.findall(r'^    \{"id": "([a-z_]+)", "chapter": \d', text, flags=re.M)


PUZZLE_IDS = puzzle_ids()


def played_game(env, ticks=60):
    m = env.module
    m.total_profit = 6000
    m.research_points = 400.0
    for node in ("automation_slot", "fast_ships"):
        env.unlock_research(node)
    env.purchase_ship("5")
    env.load()
    env.depart("verdant")
    env.tick(8)
    env.automate("2")
    env.tick(ticks)
    return m


def put_on_board(m, plan):
    """Fills the board from [[sites, ships], ...]."""
    for index, (sites, ships) in enumerate(plan):
        for stage, site_id in enumerate(sites):
            assert m.chain_set_site(index, stage, site_id)
        m.chain_plan[index]["ships"][:] = list(ships)


# --- the data ---------------------------------------------------------------------------------------------------

def test_there_are_24_puzzles_in_four_chapters_of_six(game_env):
    m = game_env.module
    assert len(m.CHAIN_PUZZLES) == 24 and len(PUZZLE_IDS) == 24
    assert [p["chapter"] for p in m.CHAIN_PUZZLES] == [c for c in (1, 2, 3, 4) for _ in range(6)]
    assert len(set(m.CHAIN_IDS)) == 24
    assert {1, 2, 3, 4} == set(m.CHAIN_CHAPTERS)


def test_the_recipe_table_is_its_own_and_every_path_is_short(game_env):
    m = game_env.module
    main_goods = set(m.SELL_PRICE)
    intermediates = {g for g in m.CHAIN_GOODS if g not in m.CHAIN_RAW_GOODS and any(r["from"] == g for r in m.CHAIN_RECIPES.values())}
    assert intermediates and not (intermediates & main_goods), "intermediate goods exist only in this mode"
    for good, recipe in m.CHAIN_RECIPES.items():
        assert recipe["from"] in m.CHAIN_GOODS and good in m.CHAIN_GOODS
        assert recipe["take"] >= 1 and recipe["make"] >= 1 and recipe["name"]
        path = m.chain_path(good)
        assert path[0] in m.CHAIN_RAW_GOODS and path[-1] == good and 2 <= len(path) <= m.CHAIN_MAX_STAGES
    assert m.chain_path("ore") == ["ore"] and m.chain_path("nonsense") == []
    assert m.chain_path("machinery") == ["ore", "alloy", "machinery"]


def test_main_economy_goods_do_not_gain_a_recipe_or_a_price(game_env):
    m = game_env.module
    assert "alloy" not in m.SELL_PRICE and "flour" not in m.SELL_PRICE and "coolant" not in m.SELL_PRICE


@pytest.mark.parametrize("puzzle_id", PUZZLE_IDS)
def test_every_puzzle_is_well_formed(game_env, puzzle_id):
    m = game_env.module
    p = m.CHAIN_BY_ID[puzzle_id]
    assert p["title"].strip() and len(p["blurb"]) >= 30
    assert 2 <= p["cargo"] <= 8 and 4 <= p["fleet"] <= 12
    assert 1 <= len(p["products"]) <= m.CHAIN_MAX_PRODUCTS
    kinds = {s["kind"] for s in p["sites"].values()}
    assert kinds <= {"source", "refinery", "port"}
    positions = [s["pos"] for s in p["sites"].values()]
    assert len(set(positions)) == len(positions), "no two sites on one spot"
    for product in p["products"]:
        assert p["sites"][product["port"]]["kind"] == "port"
        assert 1 <= product["need"] <= product["want"]
        path = m.chain_path(product["good"])
        assert path and len(path) <= m.CHAIN_MAX_STAGES
    for site in p["sites"].values():
        if site["kind"] == "source":
            assert site["good"] in m.CHAIN_RAW_GOODS and site["cap"] > 0
        if site["kind"] == "refinery":
            assert site["recipes"] and all(r in m.CHAIN_RECIPES for r in site["recipes"]) and site["cap"] > 0
    chapter = p["chapter"]
    if chapter in (1, 2):
        assert len(p["products"]) == 1
    if chapter == 3:
        assert len(p["products"]) == 2, "every shared-refiner puzzle is a two-order puzzle"
    if chapter == 1:
        assert all(len(m.chain_path(q["good"])) == 1 for q in p["products"])
    if chapter == 2:
        assert all(len(m.chain_path(q["good"])) == 2 for q in p["products"])


# --- the solver: every puzzle is solvable and its par is proved ---------------------------------------------------

@pytest.mark.parametrize("puzzle_id", PUZZLE_IDS)
def test_every_puzzle_is_solvable_and_the_stored_par_is_the_exhaustive_best(game_env, puzzle_id):
    m = game_env.module
    p = m.CHAIN_BY_ID[puzzle_id]
    solved = m.chain_solve(p)
    assert solved is not None, "an unsolvable puzzle"
    assert solved["valid"] >= 2 and solved["evaluated"] >= solved["valid"]
    assert solved["score"] == m.chain_par(p), "the stored par is not the proven best"
    assert [[list(s), list(n)] for s, n in zip(p["best"]["sites"], p["best"]["ships"])] == solved["plan"], \
        "the stored par chain is not the one the search finds"
    assert solved["ships"] == sum(sum(n) for n in p["best"]["ships"]) <= p["fleet"]


@pytest.mark.parametrize("puzzle_id", PUZZLE_IDS)
def test_the_stored_par_chain_runs_to_exactly_par(game_env, puzzle_id):
    m = game_env.module
    p = m.CHAIN_BY_ID[puzzle_id]
    result = m.chain_evaluate(p, [[s, n] for s, n in zip(p["best"]["sites"], p["best"]["ships"])])
    assert result["ok"] and result["met"]
    assert result["score"] == m.chain_par(p)
    assert m.chain_medal_for(p, sum(result["credited"]), result["ships"]) == "gold"


@pytest.mark.parametrize("puzzle_id", PUZZLE_IDS)
def test_no_chain_beats_par_and_par_is_not_the_only_way_to_solve(game_env, puzzle_id):
    """A second, independent search that goes through the public evaluator (not the solver's fast path)."""
    m = game_env.module
    p = m.CHAIN_BY_ID[puzzle_id]
    option_lists = [m.chain_options(p, i) for i in range(len(p["products"]))]
    scores = []
    import itertools
    for combo in itertools.product(*option_lists):
        sizes = [len(c) for c in combo]
        for allocation in m._chain_compositions(sum(sizes), p["fleet"]):
            plan, at = [], 0
            for chosen, size in zip(combo, sizes):
                plan.append([chosen, list(allocation[at:at + size])])
                at += size
            result = m.chain_evaluate(p, plan)
            assert result["ok"]
            if result["met"]:
                scores.append(result["score"])
    assert max(scores) == m.chain_par(p)
    assert sum(1 for s in scores if s >= m.chain_silver_score(p)) >= 1
    assert len(scores) >= 2


def test_the_search_is_deterministic_and_uses_no_clock_or_randomness(game_env):
    m = game_env.module
    p = m.CHAIN_BY_ID["mill_and_pack"]
    random.seed(1)
    first = m.chain_solve(p)
    random.seed(99)
    second = m.chain_solve(p)
    assert first == second
    # The Chain Builder is the four trade_chain_*.py / trade_modes.py modules (it was one block of the old game.py).
    block = "\n".join((GAME_DIR / f"trade_{name}.py").read_text(encoding="utf-8")
                      for name in ("chain_rules", "chain_logic", "chain_ui", "modes"))
    assert "random." not in block and "time." not in block and "Date" not in block


def test_an_unsolvable_puzzle_is_reported_as_none(game_env):
    m = game_env.module
    p = json.loads(json.dumps(m.CHAIN_BY_ID["first_delivery"], default=list))
    p["sites"] = {k: dict(v, pos=tuple(v["pos"])) for k, v in p["sites"].items()}
    p["products"][0]["need"] = 9999
    p["products"][0]["want"] = 9999
    assert m.chain_solve(p) is None


# --- the flow rules -----------------------------------------------------------------------------------------------

def test_a_leg_moves_cargo_times_whole_round_trips(game_env):
    m = game_env.module
    p = m.CHAIN_BY_ID["first_delivery"]  # Cinder Mine (3,1) to Port Vesper (1,0): 3 steps, 4 round trips, cargo 4
    assert m.chain_distance(p, "cinder", "vesper") == 3
    assert m.chain_trips(p, "cinder", "vesper") == 24 // 6 == 4
    one = m.chain_evaluate(p, [[["cinder"], [1]]])
    assert one["delivered"] == [16] and one["legs"][0][0]["per_ship"] == 16
    two = m.chain_evaluate(p, [[["cinder"], [2]]])
    assert two["delivered"] == [30], "the seam only supplies 30 a cycle"
    assert two["legs"][0][0]["capacity"] == 32 and two["legs"][0][0]["moved"] == 30


def test_a_refinery_makes_whole_runs_from_what_arrives(game_env):
    m = game_env.module
    p = m.CHAIN_BY_ID["ore_to_alloy"]  # Smelting: 2 ore make 1 alloy
    plan = [[["cinder", "kiln"], [1, 1]]]
    result = m.chain_evaluate(p, plan)
    first, second = result["legs"][0]
    assert first["made"] == first["moved"] // 2
    assert second["moved"] == min(second["capacity"], first["made"])
    assert result["delivered"] == [second["moved"]]


def test_the_refinery_cap_limits_what_it_takes_in(game_env):
    m = game_env.module
    p = m.CHAIN_BY_ID["ore_to_alloy"]
    cap = p["sites"]["kiln"]["cap"]
    result = m.chain_evaluate(p, [[["cinder", "kiln"], [7, 1]]])  # a flood of ore into a small smelter
    assert result["legs"][0][0]["moved"] > cap
    assert result["legs"][0][0]["made"] == cap // 2


def test_shared_capacity_goes_to_the_first_order_listed(game_env):
    m = game_env.module
    p = m.CHAIN_BY_ID["one_smelter_two_orders"]  # both orders pass the Kiln Station, which takes in 24 a cycle
    both = m.chain_evaluate(p, [[["cinder", "kiln"], [2, 2]], [["cinder", "kiln", "roll"], [2, 2, 1]]])
    assert both["ok"]
    first, second = both["legs"]
    assert first[0]["made"] == 12, "the first order uses the whole smelter: 24 ore make 12 alloy"
    assert second[0]["moved"] == 42 and second[0]["made"] == 0, "the second order's ore finds the smelter full"
    assert both["delivered"] == [12, 0] and both["met"] is False
    alone = m.chain_evaluate(p, [[["cinder", "kiln"], [2, 2]], [["cinder", "anvil", "roll"], [2, 2, 1]]])
    assert alone["delivered"][1] > 0, "a second smelter frees the second order"


def test_a_source_is_shared_between_orders(game_env):
    m = game_env.module
    p = m.CHAIN_BY_ID["one_smelter_two_orders"]  # Cinder Mine supplies 90 a cycle
    both = m.chain_evaluate(p, [[["cinder", "kiln"], [2, 2]], [["cinder", "kiln", "roll"], [2, 2, 1]]])
    assert both["legs"][0][0]["moved"] == 48 and both["legs"][1][0]["moved"] == 42
    assert both["legs"][0][0]["moved"] + both["legs"][1][0]["moved"] == p["sites"]["cinder"]["cap"]


def test_the_fleet_limit_is_enforced(game_env):
    m = game_env.module
    p = m.CHAIN_BY_ID["first_delivery"]
    result = m.chain_evaluate(p, [[["cinder"], [p["fleet"] + 1]]])
    assert not result["ok"] and "fleet" in result["reason"]


@pytest.mark.parametrize("plan, words", [
    ([], "every order"),
    ([[["cinder"], [1]], [["cinder"], [1]]], "every order"),
    ([[["cinder", "brack"], [1, 1]]], "number of steps"),
    ([[["vesper"], [1]]], "site that can do"),
    ([[["nowhere"], [1]]], "site that can do"),
    ([[[None], [1]]], "site that can do"),
    ([[["cinder"], [0]]], "at least one ship"),
    ([[["cinder"], [True]]], "at least one ship"),
    ([[["cinder"], [1.5]]], "at least one ship"),
    ([[["cinder"], [-2]]], "at least one ship"),
    ("not a plan", "every order"),
    ([["cinder"]], "not well formed"),
])
def test_malformed_plans_are_refused_with_a_reason(game_env, plan, words):
    m = game_env.module
    result = m.chain_evaluate(m.CHAIN_BY_ID["first_delivery"], plan)
    assert result["ok"] is False and words in result["reason"] and result["score"] is None


def test_a_site_cannot_be_used_twice_in_one_chain(game_env):
    m = game_env.module
    p = m.CHAIN_BY_ID["mill_and_pack"]
    result = m.chain_evaluate(p, [[["low", "mill"], [1, 1]], [["low", "mill", "mill"], [1, 1, 1]]])
    assert not result["ok"] and "twice" in result["reason"]


def test_a_leg_too_long_for_a_round_trip_is_refused(game_env):
    m = game_env.module
    p = json.loads(json.dumps(m.CHAIN_BY_ID["first_delivery"], default=list))
    p["sites"] = {k: dict(v, pos=tuple(v["pos"])) for k, v in p["sites"].items()}
    p["sites"]["cinder"]["pos"] = (30, 30)
    result = m.chain_evaluate(p, [[["cinder"], [1]]])
    assert not result["ok"] and "too long" in result["reason"]
    assert m.chain_options(p, 0) == [["brack"]]


def test_the_port_credits_only_up_to_what_it_wants(game_env):
    m = game_env.module
    p = m.CHAIN_BY_ID["first_delivery"]
    result = m.chain_evaluate(p, [[["brack"], [p["fleet"]]]])
    assert result["delivered"] == [48] and p["products"][0]["want"] == 36
    assert result["credited"] == [p["products"][0]["want"]]
    assert result["score"] == Fraction(p["products"][0]["want"], p["fleet"])


# --- medals ---------------------------------------------------------------------------------------------------

def test_gold_is_par_silver_is_within_the_margin_and_bronze_is_any_solve(game_env):
    m = game_env.module
    p = m.CHAIN_BY_ID["first_delivery"]  # par 15 per ship
    assert m.chain_par(p) == 15 and m.CHAIN_SILVER_PERCENT == 85
    assert m.chain_medal_for(p, 30, 2) == "gold"
    assert m.chain_medal_for(p, 51, 4) == "silver"  # 12.75 = exactly 85% of 15
    assert m.chain_medal_for(p, 50, 4) == "bronze"  # 12.5
    assert m.chain_medal_for(p, 24, 5) == "bronze"
    assert m.chain_silver_score(p) == Fraction(255, 20)


# --- the screen: entering, the board, the goals, locking in ----------------------------------------------------

def test_it_starts_closed_and_empty(game_env):
    m = game_env.module
    assert m.chain_active is None and m.chain_open is False
    assert game_env.elements["chain-panel"].hidden is True
    assert game_env.elements["chain-board"].hidden is True
    assert m.records["chain_best"] == {}


def test_the_window_toggle_opens_the_panel_with_the_picker(game_env):
    game_env.elements["chain-toggle-button"].dispatch("click", None)
    e = game_env.elements
    assert e["chain-panel"].hidden is False and e["chain-board"].hidden is True
    assert "Solved 0 of 24" in e["chain-progress"].innerText
    assert "Pick a puzzle" in e["chain-status"].innerText
    assert e["chain-toggle-button"].attributes["aria-expanded"] == "true"
    e["chain-toggle-button"].dispatch("click", None)
    assert e["chain-panel"].hidden is True


def test_entering_a_puzzle_shows_the_board_with_three_goals(game_env):
    m = game_env.module
    assert m.chain_enter("ore_to_alloy") is True
    e = game_env.elements
    assert e["chain-board"].hidden is False and e["chain-leave-button"].hidden is False
    assert "Ore to Alloy" in e["chain-title"].innerText and "Chapter 2" in e["chain-title"].innerText
    goals = [e[f"chain-goal-{i}"].innerText for i in range(3)]
    assert all(g.startswith("○ Not yet: ") for g in goals)
    assert "Meet every order" in goals[0] and "Silver" in goals[1] and "Gold" in goals[2]
    assert "<svg" in e["chain-map"].innerHTML and "Cinder Mine" in e["chain-map"].innerHTML
    assert e["chain-p0-block"].hidden is False and e["chain-p1-block"].hidden is True
    assert [e[f"chain-p0-s{k}-row"].hidden for k in range(3)] == [False, False, True]
    assert e["chain-product-0-tab"].hidden is True, "tabs appear only for two orders"
    assert e["chain-lock-button"].disabled is True


def test_the_board_follows_the_chain_and_the_goals_tick_over(game_env):
    m = game_env.module
    m.chain_enter("ore_to_alloy")
    p = m.CHAIN_BY_ID["ore_to_alloy"]
    e = game_env.elements
    best_sites, best_ships = p["best"]["sites"][0], p["best"]["ships"][0]
    for stage, site_id in enumerate(best_sites):
        e[f"chain-p0-s{stage}-select"].value = site_id
        e[f"chain-p0-s{stage}-select"].dispatch("change", None)
    assert m.chain_draft_complete()
    for stage, ships in enumerate(best_ships):
        for _ in range(ships - 1):
            e[f"chain-p0-l{stage}-up-button"].dispatch("click", None)
    result = m.chain_draft_result()
    assert result["met"] and result["score"] == m.chain_par(p)
    goals = [e[f"chain-goal-{i}"].innerText for i in range(3)]
    assert all(g.startswith("✓ Done: ") for g in goals)
    assert e["chain-lock-button"].disabled is False
    assert "Your score" in e["chain-result"].innerHTML and "Every order is met" in e["chain-result"].innerHTML


def test_a_met_but_poor_chain_ticks_only_the_first_goal(game_env):
    m = game_env.module
    m.chain_enter("first_delivery")
    put_on_board(m, [[["brack"], [4]]])
    m.render_chain()
    result = m.chain_draft_result()
    assert result["met"] and result["score"] < m.chain_silver_score(m.CHAIN_BY_ID["first_delivery"])
    e = game_env.elements
    assert e["chain-goal-0"].innerText.startswith("✓") and e["chain-goal-1"].innerText.startswith("○") \
        and e["chain-goal-2"].innerText.startswith("○")


def test_ship_buttons_stop_at_one_and_at_the_fleet(game_env):
    m = game_env.module
    m.chain_enter("ore_to_alloy")
    fleet = m.CHAIN_BY_ID["ore_to_alloy"]["fleet"]
    assert m.chain_adjust_ships(0, 0, -1) is False
    for _ in range(40):
        m.chain_adjust_ships(0, 0, 1)
    assert m.chain_ships_on_board() == fleet
    assert m.chain_adjust_ships(0, 1, 1) is False
    m.render_chain()
    assert game_env.elements["chain-p0-l0-up-button"].disabled is True
    assert game_env.elements["chain-p0-l0-down-button"].disabled is False
    assert m.chain_adjust_ships(0, 0, 2) is False and m.chain_adjust_ships(0, 9, 1) is False and m.chain_adjust_ships(5, 0, 1) is False


def test_set_site_refuses_a_site_that_does_not_fit(game_env):
    m = game_env.module
    m.chain_enter("ore_to_alloy")
    assert m.chain_set_site(0, 0, "kiln") is False  # a refinery cannot be the source
    assert m.chain_set_site(0, 1, "cinder") is False
    assert m.chain_set_site(0, 1, "vesper") is False
    assert m.chain_set_site(0, 1, "nope") is False and m.chain_set_site(0, 1, 5) is False
    assert m.chain_set_site(0, 7, "kiln") is False and m.chain_set_site(3, 0, "kiln") is False
    assert m.chain_set_site(0, 0, "cinder") and m.chain_set_site(0, 1, "kiln")
    assert m.chain_set_site(0, 1, "") and m.chain_plan[0]["sites"] == ["cinder", None]


def test_a_map_click_fills_the_first_fitting_step_and_a_second_click_takes_it_out(game_env):
    m = game_env.module
    m.chain_enter("ore_to_alloy")
    assert m.chain_pick_site("kiln") and m.chain_plan[0]["sites"] == [None, "kiln"]
    assert m.chain_pick_site("cinder") and m.chain_plan[0]["sites"] == ["cinder", "kiln"]
    assert m.chain_pick_site("anvil") and m.chain_plan[0]["sites"] == ["cinder", "anvil"], "replaces the only fitting step"
    assert m.chain_pick_site("anvil") and m.chain_plan[0]["sites"] == ["cinder", None]
    assert m.chain_pick_site("vesper") is False, "ports are fixed"
    assert m.chain_pick_site("nope") is False


def test_map_clicks_go_to_the_chosen_order(game_env):
    m = game_env.module
    m.chain_enter("mill_and_pack")
    assert m.chain_tab == 0
    game_env.elements["chain-product-1-tab"].dispatch("click", None)
    assert m.chain_tab == 1
    assert game_env.elements["chain-product-1-tab"].attributes["aria-pressed"] == "true"
    assert m.chain_pick_site("low")
    assert m.chain_plan[1]["sites"][0] == "low" and m.chain_plan[0]["sites"][0] is None


def test_the_map_click_handler_reads_the_site_from_the_event(game_env):
    m = game_env.module
    m.chain_enter("ore_to_alloy")
    node = types.SimpleNamespace(getAttribute=lambda name: "cinder")
    target = types.SimpleNamespace(closest=lambda selector: node if selector == "[data-site]" else None)
    game_env.elements["chain-map"].dispatch("click", types.SimpleNamespace(target=target))
    assert m.chain_plan[0]["sites"][0] == "cinder"
    game_env.elements["chain-map"].dispatch("click", types.SimpleNamespace(target=types.SimpleNamespace(closest=lambda s: None)))
    game_env.elements["chain-map"].dispatch("click", None)
    assert m.chain_plan[0]["sites"][0] == "cinder"


def test_a_chain_cannot_use_one_site_in_two_steps_of_the_same_order(game_env):
    m = game_env.module
    m.chain_enter("mill_and_pack")
    assert m.chain_set_site(1, 1, "mill")  # the rations order: flour at the mill...
    assert m.chain_set_site(1, 2, "mill") is False, "...and the same mill again is refused"
    assert m.chain_set_site(1, 2, "press")


def test_lock_in_needs_a_chain_that_meets_every_order(game_env):
    m = game_env.module
    m.chain_enter("first_delivery")
    assert m.chain_lock_in() is False
    put_on_board(m, [[["cinder"], [1]]])  # 16 a cycle against a need of 24
    assert m.chain_lock_in() is False
    assert m.chain_best_text("first_delivery") == "Best: not solved yet"


def test_locking_in_keeps_the_best_and_a_worse_one_does_not_replace_it(game_env):
    m = game_env.module
    m.chain_enter("first_delivery")
    put_on_board(m, [[["cinder"], [2]]])
    assert m.chain_lock_in() is True
    assert m.chain_done["medal"] == "gold" and m.chain_done["improved"] is True
    assert "Gold" in m.chain_best_text("first_delivery") and "15.00 per ship" in m.chain_best_text("first_delivery")
    put_on_board(m, [[["brack"], [3]]])  # 36 delivered by 3 ships = 12 per ship
    assert m.chain_lock_in() is True
    assert m.chain_done["improved"] is False
    m.render_chain()
    assert "Your saved best is better" in game_env.elements["chain-status"].innerText
    assert m._chain_real_best()["first_delivery"] == {"units": 30, "ships": 2}


def test_a_tie_with_fewer_ships_is_an_improvement(game_env):
    m = game_env.module
    assert m._chain_better(30, 2, {"units": 60, "ships": 4}) is True
    assert m._chain_better(60, 4, {"units": 30, "ships": 2}) is False
    assert m._chain_better(31, 2, {"units": 30, "ships": 2}) is True
    assert m._chain_better(1, 1, None) is True


def test_changing_the_board_clears_the_locked_in_banner(game_env):
    m = game_env.module
    m.chain_enter("first_delivery")
    put_on_board(m, [[["cinder"], [2]]])
    m.chain_lock_in()
    assert m.chain_done is not None
    m.chain_adjust_ships(0, 0, 1)
    assert m.chain_done is None


def test_the_clear_button_empties_the_board(game_env):
    m = game_env.module
    m.chain_enter("ore_to_alloy")
    put_on_board(m, [[["cinder", "kiln"], [3, 2]]])
    game_env.elements["chain-clear-button"].dispatch("click", None)
    assert m.chain_plan == [{"sites": [None, None], "ships": [1, 1]}]


def test_two_order_puzzles_show_two_blocks_and_tabs(game_env):
    m = game_env.module
    m.chain_enter("crowded_forge")
    e = game_env.elements
    assert e["chain-p1-block"].hidden is False
    assert e["chain-product-0-tab"].hidden is False and e["chain-product-1-tab"].hidden is False
    assert [e[f"chain-p0-s{k}-row"].hidden for k in range(3)] == [False, False, False]
    assert "Order 1" in e["chain-p0-title"].innerText and "Order 2" in e["chain-p1-title"].innerText


def test_the_select_lists_only_sites_that_fit_the_step(game_env):
    m = game_env.module
    m.chain_enter("ore_to_alloy")
    html = game_env.elements["chain-p0-s0-select"].innerHTML
    assert "Cinder Mine" in html and "Kiln Station" not in html and "Port Vesper" not in html
    html = game_env.elements["chain-p0-s1-select"].innerHTML
    assert "Kiln Station" in html and "Anvil Yard" in html and "Cinder Mine" not in html


def test_the_screen_is_not_rewritten_when_nothing_changed(game_env):
    m = game_env.module
    m.chain_enter("ore_to_alloy")
    game_env.elements["chain-map"].innerHTML = "SENTINEL"
    m.render()
    m.render_chain()
    assert game_env.elements["chain-map"].innerHTML == "SENTINEL", "a once-a-second render must not rebuild an unchanged board"
    m.chain_pick_site("cinder")
    m.render_chain()
    assert "<svg" in game_env.elements["chain-map"].innerHTML


def test_distances_text_lists_every_usable_leg(game_env):
    m = game_env.module
    text = m.chain_distances_text(m.CHAIN_BY_ID["ore_to_alloy"])
    assert "Cinder Mine to Kiln Station: 4 steps" in text and "Kiln Station to Port Vesper" in text
    assert "round trips a cycle" in text and "units per ship" in text


# --- hints: each rung opens only on a press ---------------------------------------------------------------------

def test_the_hint_ladder_opens_one_rung_per_press(game_env):
    m = game_env.module
    m.chain_enter("ore_to_alloy")
    e = game_env.elements
    p = m.CHAIN_BY_ID["ore_to_alloy"]
    assert e["chain-hint-button"].innerText == "Would you like a suggestion?"
    assert all(e[f"chain-hint-{i}-text"].hidden for i in range(3)) and all(e[f"chain-hint-{i}-text"].innerText == "" for i in range(3))
    e["chain-hint-button"].dispatch("click", None)
    assert e["chain-hint-0-text"].hidden is False and e["chain-hint-1-text"].hidden is True
    assert "Smelting turns 2 Ore into 1 Alloy" in e["chain-hint-0-text"].innerText
    assert e["chain-hint-button"].innerText == "Would you like another suggestion?"
    e["chain-hint-button"].dispatch("click", None)
    assert all(name in e["chain-hint-1-text"].innerText for name in ("Cinder Mine", "Kiln Station"))
    assert e["chain-hint-2-text"].hidden is True and e["chain-hint-2-text"].innerText == ""
    assert e["chain-hint-button"].innerText == "Would you like the ships as well?"
    e["chain-hint-button"].dispatch("click", None)
    ships = p["best"]["ships"][0]
    assert f"{ships[0]}, {ships[1]}" in e["chain-hint-2-text"].innerText
    assert m.chain_plan[0]["sites"] == [None, None], "nothing is placed until the last press"
    assert e["chain-hint-button"].innerText == "Place the par chain on the board"
    e["chain-hint-button"].dispatch("click", None)
    assert m.chain_plan[0]["sites"] == p["best"]["sites"][0] and m.chain_plan[0]["ships"] == p["best"]["ships"][0]
    assert m.chain_draft_result()["score"] == m.chain_par(p)


def test_hints_start_again_with_every_new_puzzle(game_env):
    m = game_env.module
    m.chain_enter("ore_to_alloy")
    m.chain_hint_press()
    m.chain_hint_press()
    assert m.chain_hint_rung == 2
    m.chain_enter("mill_choice")
    assert m.chain_hint_rung == 0
    m.render_chain()
    assert all(game_env.elements[f"chain-hint-{i}-text"].hidden for i in range(3))


def test_the_hint_names_match_the_stored_par_chain_for_every_puzzle(game_env):
    m = game_env.module
    for p in m.CHAIN_PUZZLES:
        second = m.chain_hint_text(p, 2)
        for names in p["best"]["sites"]:
            assert all(p["sites"][s]["name"] in second for s in names)
        third = m.chain_hint_text(p, 3)
        assert f"{sum(sum(n) for n in p['best']['ships'])} ships in all" in third
        assert m.chain_hint_text(p, 1)


# --- the real game is set aside and comes back byte-identical ---------------------------------------------------------

def test_a_puzzle_sets_the_real_game_aside_and_leaving_restores_it_byte_identically(game_env):
    m = played_game(game_env)
    before = dump(m.get_state())
    assert m.get_state()["unlocked_research"], "the real game has history"
    m.chain_enter("one_smelter_two_orders")
    assert m.sandbox_is_active() and m.chain_active == "one_smelter_two_orders"
    assert dump(m.get_state()) == before, "a save made inside a puzzle is the real game"
    put_on_board(m, [[["cinder", "kiln"], [2, 2]], [["cinder", "anvil", "roll"], [2, 1, 1]]])
    game_env.tick(120)
    m.chain_leave()
    assert not m.sandbox_is_active() and m.chain_active is None
    assert dump(m.get_state()) == before


def test_nothing_ticks_while_a_puzzle_is_open(game_env):
    m = played_game(game_env)
    m.chain_enter("first_delivery")
    snapshot = dump(m.get_state())
    points = m.research_points
    sales = m.total_sales_count
    game_env.tick(200)
    assert (m.research_points, m.total_sales_count) == (points, sales)
    assert dump(m.get_state()) == snapshot
    m.chain_leave()
    game_env.tick(1)
    assert m.research_points > points, "the real game runs again once the puzzle is left"


def test_a_locked_in_medal_is_kept_in_the_real_game_and_nothing_else_changes(game_env):
    m = played_game(game_env)
    before = json.loads(dump(m.get_state()))
    m.chain_enter("first_delivery")
    put_on_board(m, [[["cinder"], [2]]])
    assert m.chain_lock_in()
    during = json.loads(dump(m.get_state()))
    assert during["records"]["chain_best"] == {"first_delivery": {"units": 30, "ships": 2}}
    m.chain_leave()
    after = json.loads(dump(m.get_state()))
    assert after["records"]["chain_best"] == {"first_delivery": {"units": 30, "ships": 2}}
    assert after["achievements_earned"] == before["achievements_earned"] + ["chain_first"] or \
        set(after["achievements_earned"]) == set(before["achievements_earned"]) | {"chain_first"}
    for state in (before, during, after):
        state.pop("records", None)
        state.pop("achievements_earned", None)
    assert dump(before) == dump(during) == dump(after)
    assert m.records["chain_best"]["first_delivery"] == {"units": 30, "ships": 2}


def test_the_credits_label_says_the_corporation_is_set_aside(game_env):
    m = game_env.module
    m.chain_enter("first_delivery")
    assert "set aside" in game_env.elements["profit-display-text"].innerText
    assert m.total_profit < 1000, "no sandbox top-up in a puzzle"
    m.chain_leave()
    assert "set aside" not in game_env.elements["profit-display-text"].innerText


def test_entering_a_puzzle_from_the_sandbox_or_a_crisis_goes_back_through_the_real_game(game_env):
    m = played_game(game_env, ticks=20)
    before = dump(m.get_state())
    m.sandbox_enter()
    assert m.chain_enter("first_delivery") is True
    assert m.chain_active and m.crisis_active is None
    m.crisis_enter("grain_famine")
    assert m.chain_active is None and m.crisis_active == "grain_famine"
    m.chain_enter("first_delivery")
    assert m.crisis_active is None
    m.sandbox_enter()
    assert m.chain_active is None and m.sandbox_is_active() and m.crisis_active is None
    m.sandbox_leave()
    assert dump(m.get_state()) == before


def test_switching_puzzles_keeps_the_same_set_aside_game(game_env):
    m = played_game(game_env, ticks=20)
    before = dump(m.get_state())
    m.chain_enter("first_delivery")
    aside = m._sandbox_real
    m.chain_enter("thin_seam")
    assert m._sandbox_real is aside and m.chain_active == "thin_seam"
    m.chain_leave()
    assert dump(m.get_state()) == before


def test_loading_a_save_inside_a_puzzle_leaves_it(game_env):
    m = played_game(game_env, ticks=20)
    saved = json.loads(dump(m.get_state()))
    m.chain_enter("first_delivery")
    assert m.load_state(saved) is True
    assert m.chain_active is None and not m.sandbox_is_active()
    assert dump(m.get_state()) == dump(saved)


def test_the_leave_button_and_the_sandbox_button_both_end_a_puzzle(game_env):
    m = game_env.module
    m.chain_enter("first_delivery")
    game_env.elements["chain-leave-button"].dispatch("click", None)
    assert m.chain_active is None and not m.sandbox_is_active()
    m.chain_enter("first_delivery")
    m.sandbox_leave()
    assert m.chain_active is None
    m.render_chain()
    assert game_env.elements["chain-board"].hidden is True


def test_entering_an_unknown_puzzle_does_nothing(game_env):
    m = game_env.module
    for bad in ("nope", None, 3, ""):
        assert m.chain_enter(bad) is False
    assert not m.sandbox_is_active() and m.chain_active is None


def test_the_page_script_is_told_when_a_puzzle_starts_and_ends(game_env):
    m = game_env.module
    syncs = []
    sys.modules["js"].window = types.SimpleNamespace(NoyvjSandbox=types.SimpleNamespace(sync=lambda: syncs.append(m.sandbox_active)))
    try:
        m.chain_enter("first_delivery")
        assert syncs == [True]
    finally:
        del sys.modules["js"].window


# --- saves ----------------------------------------------------------------------------------------------------

def test_a_fresh_save_has_no_chain_data_and_an_old_save_loads_unchanged(game_env):
    m = game_env.module
    state = m.get_state()
    assert "records" not in state, "nothing is written until something is recorded"
    assert m.load_state(json.loads(dump(state))) is True
    assert m.records["chain_best"] == {}
    assert dump(m.get_state()) == dump(state)


def test_a_recorded_best_survives_a_save_and_load(game_env):
    m = game_env.module
    m.records["chain_best"]["thin_seam"] = {"units": 40, "ships": 5}
    saved = json.loads(dump(m.get_state()))
    assert saved["records"] == {"chain_best": {"thin_seam": {"units": 40, "ships": 5}}}
    m.records["chain_best"].clear()
    m.load_state(saved)
    assert m.records["chain_best"] == {"thin_seam": {"units": 40, "ships": 5}}


@pytest.mark.parametrize("raw", [
    "nonsense", 7, [], None,
    {"nope": {"units": 30, "ships": 2}},
    {"first_delivery": {"units": 31, "ships": 2}},  # 15.5 per ship is above par
    {"first_delivery": {"units": 30, "ships": 0}},
    {"first_delivery": {"units": 30, "ships": 99}},
    {"first_delivery": {"units": 10, "ships": 1}},  # fewer units than the order needs
    {"first_delivery": {"units": 999, "ships": 6}},  # more than the port takes
    {"first_delivery": {"units": True, "ships": 2}},
    {"first_delivery": {"units": "30", "ships": 2}},
    {"first_delivery": {"units": 30.0, "ships": 2}},
    {"first_delivery": [30, 2]},
    {"first_delivery": None},
    {5: {"units": 30, "ships": 2}},
])
def test_tampered_bests_are_dropped(game_env, raw):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["records"] = {"chain_best": raw}
    m.load_state(state)
    assert m.records["chain_best"] == {}


def test_good_entries_survive_next_to_bad_ones(game_env):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["records"] = {"chain_best": {
        "first_delivery": {"units": 30, "ships": 2, "extra": "ignored"},
        "thin_seam": {"units": 1, "ships": 1},
        "ore_to_alloy": {"units": 8, "ships": 2},
    }}
    m.load_state(state)
    assert m.records["chain_best"] == {"first_delivery": {"units": 30, "ships": 2}, "ore_to_alloy": {"units": 8, "ships": 2}}


def test_bests_survive_a_charter_renewal(game_env):
    m = game_env.module
    m.records["chain_best"]["first_delivery"] = {"units": 30, "ships": 2}
    m.endgame_reached = True
    m.found_new_corporation()
    assert m.records["chain_best"] == {"first_delivery": {"units": 30, "ships": 2}}


# --- achievements ---------------------------------------------------------------------------------------------

def test_four_new_achievements_with_story_chapters(game_env):
    m = game_env.module
    ids = {a["id"] for a in m.ACHIEVEMENTS}
    assert {"chain_first", "chain_par", "chain_shared", "chain_master"} <= ids
    story = {c["id"] for c in json.loads((GAME_DIR / "story.json").read_text(encoding="utf-8"))["chapters"]}
    assert {"chain_first", "chain_par", "chain_shared", "chain_master"} <= story


def _par_entry(m, p):
    result = m.chain_evaluate(p, [[s, n] for s, n in zip(p["best"]["sites"], p["best"]["ships"])])
    return {"units": sum(result["credited"]), "ships": result["ships"]}


def test_first_link_comes_with_any_solve(game_env):
    m = game_env.module
    assert "chain_first" not in m.achievement_ids_earned()
    m.records["chain_best"]["thin_seam"] = {"units": 40, "ships": 5}
    assert "chain_first" in m.achievement_ids_earned()


def test_at_par_needs_five_golds_and_shows_progress(game_env):
    m = game_env.module
    chapter1 = [p["id"] for p in m.CHAIN_PUZZLES if p["chapter"] == 1]
    for pid in chapter1[:4]:
        m.records["chain_best"][pid] = _par_entry(m, m.CHAIN_BY_ID[pid])
    assert "chain_par" not in m.achievement_ids_earned()
    assert {a["id"]: a["progress"] for a in m.achievements_summary()}["chain_par"] == (4, 5)
    m.records["chain_best"][chapter1[4]] = _par_entry(m, m.CHAIN_BY_ID[chapter1[4]])
    assert "chain_par" in m.achievement_ids_earned()


def test_silver_and_bronze_do_not_count_toward_at_par(game_env):
    m = game_env.module
    for pid in [p["id"] for p in m.CHAIN_PUZZLES][:6]:
        entry = _par_entry(m, m.CHAIN_BY_ID[pid])
        m.records["chain_best"][pid] = {"units": entry["units"], "ships": entry["ships"] + 1}
    assert m._chain_gold_count() == 0 and "chain_par" not in m.achievement_ids_earned()


def test_shared_foundry_needs_all_of_chapter_three(game_env):
    m = game_env.module
    chapter3 = [p["id"] for p in m.CHAIN_PUZZLES if p["chapter"] == 3]
    for pid in chapter3[:5]:
        m.records["chain_best"][pid] = _par_entry(m, m.CHAIN_BY_ID[pid])
    assert "chain_shared" not in m.achievement_ids_earned()
    assert {a["id"]: a["progress"] for a in m.achievements_summary()}["chain_shared"] == (5, 6)
    m.records["chain_best"][chapter3[5]] = _par_entry(m, m.CHAIN_BY_ID[chapter3[5]])
    assert "chain_shared" in m.achievement_ids_earned()


def test_chain_master_needs_all_24(game_env):
    m = game_env.module
    for p in m.CHAIN_PUZZLES[:-1]:
        m.records["chain_best"][p["id"]] = _par_entry(m, p)
    assert "chain_master" not in m.achievement_ids_earned()
    assert {a["id"]: a["progress"] for a in m.achievements_summary()}["chain_master"] == (23, 24)
    last = m.CHAIN_PUZZLES[-1]
    m.records["chain_best"][last["id"]] = _par_entry(m, last)
    assert {"chain_first", "chain_par", "chain_shared", "chain_master"} <= set(m.achievement_ids_earned())


def test_nothing_is_earned_inside_a_puzzle_until_it_is_left(game_env):
    m = game_env.module
    m.chain_enter("first_delivery")
    put_on_board(m, [[["cinder"], [2]]])
    m.chain_lock_in()
    assert "chain_first" not in m.achievement_ids_earned()
    m.chain_leave()
    assert "chain_first" in m.achievement_ids_earned()


# --- the picker on the shared level select --------------------------------------------------------------------

class FakeLevelSelect:
    def __init__(self):
        self.created = []
        self.state = None
        self.opened = 0

    def create(self, options):
        self.created.append(options)
        parent = self

        class Screen:
            def setState(self, state):
                parent.state = state

            def setLevels(self, levels):
                parent.levels = levels

            def open(self):
                parent.opened += 1

        return Screen()


def install_level_select():
    fake = FakeLevelSelect()
    obj = types.SimpleNamespace(create=fake.create)
    sys.modules["js"].window = types.SimpleNamespace(NoyvjLevels=obj)
    sys.modules["js"].Object = types.SimpleNamespace(fromEntries=None)
    sys.modules["pyodide.ffi"].to_js = lambda value, dict_converter=None: value
    return fake


def remove_level_select():
    del sys.modules["js"].window
    del sys.modules["js"].Object
    del sys.modules["pyodide.ffi"].to_js


def test_the_picker_builds_one_level_per_puzzle_and_starts_a_puzzle(game_env):
    m = game_env.module
    fake = install_level_select()
    try:
        game_env.elements["chain-pick-button"].dispatch("click", None)
        assert fake.opened == 1 and len(fake.created) == 1
        options = fake.created[0]
        assert options["domId"] == "chain-select" and len(options["levels"]) == 24
        assert [lv["id"] for lv in options["levels"]] == list(m.CHAIN_IDS)
        kinds = [lv["kind"] for lv in options["levels"]]
        assert kinds.count("mechanic") == 3 and kinds[0] == "level" and kinds[6] == kinds[12] == kinds[18] == "mechanic"
        assert options["state"] == {"done": [], "best": {}}
        options["onStart"]("ore_to_alloy")
        assert m.chain_active == "ore_to_alloy"
        game_env.elements["chain-pick-button"].dispatch("click", None)
        assert len(fake.created) == 1, "the screen is built once"
    finally:
        remove_level_select()


def test_the_picker_state_shows_solved_puzzles_with_their_medal(game_env):
    m = game_env.module
    m.records["chain_best"]["first_delivery"] = {"units": 30, "ships": 2}
    m.records["chain_best"]["thin_seam"] = {"units": 40, "ships": 5}
    state = m.chain_levels_state()
    assert state["done"] == ["first_delivery", "thin_seam"]
    assert state["best"]["first_delivery"]["text"].startswith("★ Gold")
    assert state["best"]["thin_seam"]["value"] == 8.0
    assert all(len(b["text"]) <= 60 for b in state["best"].values())


def test_without_the_shared_script_the_picker_falls_back_to_the_next_unsolved_puzzle(game_env):
    m = game_env.module
    m.records["chain_best"]["first_delivery"] = {"units": 30, "ships": 2}
    game_env.elements["chain-pick-button"].dispatch("click", None)
    assert m.chain_active == "thin_seam"


# --- markup ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["index.html", "pc.html"])
def test_both_pages_carry_the_chain_builder(name):
    html = (GAME_DIR / name).read_text(encoding="utf-8")
    for needle in ("chain-toggle-button", "chain-panel", "chain-board", "chain-hint-button", "chain-goal-2",
                   "chain-map", "shared/level-select.js", 'id="chain-p1-s2-select"'):
        assert needle in html, (name, needle)


def test_the_hint_button_starts_with_the_agreed_question():
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert 'id="chain-hint-button" class="secondary" type="button">Would you like a suggestion?</button>' in html


def test_the_desktop_menu_and_window_list_include_the_chain_builder():
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    assert ["chain-panel", "chain-toggle-button", "Chain Builder"] in cfg["windows"]
    empire = next(g for g in cfg["toolbar"]["menu"] if g["heading"] == "Empire")
    assert "chain-toggle-button" in empire["ids"]


def test_the_question_mark_help_lists_the_chain_window():
    from .pagefiles import page_text
    html = page_text("index.html")
    assert '{ toggle: "chain-toggle-button", panel: "chain-panel" }' in html
