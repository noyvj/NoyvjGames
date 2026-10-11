"""H-3: the multi-cycle planner (a what-if on a copy of the chain, committed one cycle at a time)."""

import pytest


def add(env, kind, times=1):
    for _ in range(times):
        env.elements[f"planner-add-{kind}-button"].dispatch("click", None)


def choose(env, element_id, value):
    env.elements[element_id].value = str(value)
    env.elements[element_id].dispatch("change", None)


def test_an_empty_plan_previews_doing_nothing(game_env):
    module = game_env.module
    rows = module.simulate_plan()
    assert len(rows) == 3
    assert [r["cycle"] for r in rows] == [1, 2, 3]
    assert all(r["bought"] == {} and r["short"] == {} for r in rows)
    assert rows[0]["fraction"] == 0.0 and rows[0]["extraction"] == 50.0
    assert "Doing nothing" in game_env.elements["planner-summary"].innerText


def test_the_preview_never_changes_the_real_chain(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 400.0
    add(game_env, "recycle", 3)
    before = chain._snapshot()
    module.simulate_plan()
    module.render()
    assert chain._snapshot() == before
    assert chain.cycle_number == 1 and chain.funds == 400.0


def test_purchases_move_the_projected_numbers(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 400.0
    add(game_env, "recycle", 4)  # 4 x 5 units = 20 of 50
    rows = module.simulate_plan()
    assert rows[0]["bought"] == {"recycle": 4}
    assert rows[0]["fraction"] == pytest.approx(0.4)
    assert rows[0]["extraction"] == pytest.approx(30.0)
    assert rows[0]["bill"] == pytest.approx(30.0 * module.EXTRACTION_COST_PER_UNIT)
    assert rows[1]["fraction"] == pytest.approx(0.4)  # the purchase keeps supplying later cycles
    # funds follow the real rules: 400 - 120 spent + (250 sales - 60 bill)
    assert rows[0]["funds"] == pytest.approx(400 - 120 + 250 - 60)


def test_the_plan_matches_what_really_happens(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 400.0
    add(game_env, "recycle", 2)
    choose(game_env, "planner-slot-select", 1)
    add(game_env, "reuse", 3)
    rows = module.simulate_plan()
    commit = game_env.elements["planner-commit-button"]
    commit.dispatch("click", None)  # cycle 1's picks
    game_env.advance_cycle()
    assert module.chain.circular_fraction_log[0] == pytest.approx(rows[0]["fraction"])
    assert module.chain.funds == pytest.approx(rows[0]["funds"])
    commit.dispatch("click", None)  # the plan shifted: cycle 2's picks are now this cycle's
    assert module.chain.circular_fraction_this_cycle() == pytest.approx(rows[1]["fraction"])
    game_env.advance_cycle()
    assert module.chain.funds == pytest.approx(rows[1]["funds"])


def test_purchases_it_cannot_afford_are_marked(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 60.0
    add(game_env, "recycle", 5)  # 150 funds wanted, 60 held: two bought
    rows = module.simulate_plan()
    assert rows[0]["bought"] == {"recycle": 2} and rows[0]["short"] == {"recycle": 3}
    assert "cannot afford" in game_env.elements["planner-table"].innerHTML


def test_the_horizon_is_three_four_or_five_and_trims_the_plan(game_env):
    module = game_env.module
    choose(game_env, "planner-horizon-select", 5)
    assert module.planner_horizon == 5 and len(module.simulate_plan()) == 5
    choose(game_env, "planner-slot-select", 4)
    add(game_env, "repair")
    assert module.plan_total(4) == 1
    choose(game_env, "planner-horizon-select", 3)
    assert module.plan_total(4) == 0 and module.plan_added == []
    assert module.planner_slot == 2 or module.planner_slot < 3
    choose(game_env, "planner-horizon-select", 9)  # not an allowed value: ignored
    assert module.planner_horizon == 3


def test_a_slot_outside_the_window_is_refused(game_env):
    module = game_env.module
    assert module.plan_add("repair", slot=3) is False
    assert module.plan_add("repair", slot=-1) is False
    assert module.plan_add("nonsense", slot=0) is False
    assert module.plan_total(0) == 0


def test_a_slot_holds_at_most_twenty(game_env):
    module = game_env.module
    for _ in range(module.PLANNER_MAX_PER_SLOT):
        assert module.plan_add("repair") is True
    assert module.plan_add("repair") is False
    add(game_env, "reuse")
    assert "full" in game_env.elements["planner-message"].innerText


def test_undo_takes_back_the_latest_and_clear_empties(game_env):
    module = game_env.module
    add(game_env, "repair", 2)
    add(game_env, "reuse")
    game_env.elements["planner-undo-button"].dispatch("click", None)
    assert module.plan[0] == {"repair": 2}
    game_env.elements["planner-clear-button"].dispatch("click", None)
    assert module.plan[0] == {} and module.plan_added == []
    assert game_env.elements["planner-undo-button"].disabled is True


def test_commit_buys_this_cycles_picks_and_keeps_the_later_ones(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 400.0
    add(game_env, "recycle", 2)
    choose(game_env, "planner-slot-select", 1)
    add(game_env, "reuse")
    game_env.elements["planner-commit-button"].dispatch("click", None)
    assert chain.circularity_investment["recycle"] == 2 and chain.funds == pytest.approx(340.0)
    assert module.plan[0] == {} and module.plan[1] == {"reuse": 1}
    assert "Bought: Recycling x2." in game_env.elements["planner-message"].innerText
    assert chain.lifetime_investment_spend == pytest.approx(60.0)  # the ordinary purchase rules


def test_commit_stops_when_funds_run_out(game_env):
    chain = game_env.chain
    chain.funds = 60.0
    add(game_env, "recycle", 5)
    game_env.elements["planner-commit-button"].dispatch("click", None)
    assert chain.circularity_investment["recycle"] == 2


def test_commit_with_nothing_planned_says_so(game_env):
    game_env.module.on_planner_commit()
    assert "Nothing is planned" in game_env.elements["planner-message"].innerText


def test_commit_asks_first_over_the_spend_threshold(game_env, monkeypatch):
    module, chain = game_env.module, game_env.chain
    asked = []
    monkeypatch.setattr(module, "_setting_number", lambda name, default=0: 50 if name == "confirmThreshold" else default)
    monkeypatch.setattr(module, "_confirm_dialog_ask", lambda **kw: asked.append(kw))
    chain.funds = 300.0
    add(game_env, "recycle", 6)  # 180 of 300 funds
    game_env.elements["planner-commit-button"].dispatch("click", None)
    assert len(asked) == 1 and "Spend 180 of 300" in asked[0]["message"]
    assert chain.circularity_investment["recycle"] == 0
    asked[0]["on_confirm"]()
    assert chain.circularity_investment["recycle"] == 6


def test_advancing_a_cycle_shifts_the_plan_down(game_env):
    module = game_env.module
    choose(game_env, "planner-slot-select", 1)
    add(game_env, "reuse", 2)
    game_env.advance_cycle()
    assert module.plan[0] == {"reuse": 2} and module.plan[1] == {}
    assert module.plan_added == [(0, "reuse"), (0, "reuse")]


def test_a_new_chain_or_a_load_clears_the_plan(game_env):
    module = game_env.module
    add(game_env, "repair", 2)
    game_env.reset_chain()
    assert module.plan[0] == {}
    add(game_env, "repair")
    module.load_state(module.get_state())
    assert module.plan[0] == {}


def test_the_plan_is_never_saved(game_env):
    module = game_env.module
    add(game_env, "repair", 2)
    assert not any("plan" in key for key in module.get_state())


def test_the_preview_uses_modes_and_shocks_of_the_real_chain(game_env):
    module, chain = game_env.module, game_env.chain
    chain.challenge_mode = True  # supply counts at 65%
    chain.funds = 400.0
    add(game_env, "recycle", 4)
    rows = module.simulate_plan()
    assert rows[0]["fraction"] == pytest.approx(0.4 * module.CHALLENGE_MODE_SUPPLY_MULTIPLIER)


def test_the_commit_button_shows_the_cost(game_env):
    chain = game_env.chain
    chain.funds = 400.0
    add(game_env, "reuse", 2)
    assert game_env.elements["planner-commit-button"].innerText == "Commit this cycle's picks (50)"
    assert game_env.elements["planner-commit-button"].disabled is False
