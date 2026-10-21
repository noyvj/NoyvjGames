import grid_coach
import grid_runstate as runstate


def test_fresh_game_hydro():
    from grid_state import GridState
    s = GridState()
    runstate.state = s
    runstate.state.funds = 500

    result = grid_coach.auto_plan_suggestion()

    assert result["plant"] == "hydro"
    assert result["text"] == "Build one Hydro plant for 150 funds. It adds 40 capacity and closes 40 of the 110 shortfall expected next round."


def test_nuclear_capacity_covers_demand():
    from grid_state import GridState
    s = GridState()
    runstate.state = s
    runstate.state.plant_counts["nuclear"] = 2

    result = grid_coach.auto_plan_suggestion()

    assert result["plant"] is None
    assert result["text"] == "Nothing to build this round: capacity 200 already covers next round's demand of 110."


def test_insufficient_funds():
    from grid_state import GridState
    s = GridState()
    runstate.state = s
    runstate.state.funds = 50

    result = grid_coach.auto_plan_suggestion()

    assert result["plant"] is None
    assert result["text"] == "Save up: the cheapest renewable plant costs 70 and you have 50. Next round is 110 short."


def test_funds_100_wins_wind():
    from grid_state import GridState
    s = GridState()
    runstate.state = s
    runstate.state.funds = 100

    result = grid_coach.auto_plan_suggestion()

    assert result["plant"] == "wind"
