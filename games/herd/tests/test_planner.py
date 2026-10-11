"""F-7 dry-run planner (planning/TODO.md "GF + F. Herd")."""

import copy
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent


def _snapshot(farm):
    return json.dumps(farm_state(farm), sort_keys=True, default=str)


def farm_state(farm):
    return {k: v for k, v in vars(farm).items()}


def _click(env, id_):
    env.elements[id_].dispatch("click", None)


def _queue(env, lever, offset, count):
    env.elements["plan-lever-select"].value = lever
    env.elements["plan-round-select"].value = str(offset)
    env.elements["plan-count-select"].value = str(count)
    _click(env, "plan-add-button")


def test_a_projection_never_touches_the_real_farm(game_env):
    m = game_env.module
    game_env.farm.funds = 500.0
    game_env.grow_herd()
    before = copy.deepcopy(farm_state(game_env.farm))
    state_before = json.dumps(m.get_state(), sort_keys=True)
    m.add_plan_step(0, "capture", 2)
    m.add_plan_step(1, "herd", 5)
    m.project_plan()
    after = farm_state(game_env.farm)
    assert after == before
    assert json.dumps(m.get_state(), sort_keys=True) == state_before


def test_an_empty_plan_matches_doing_nothing(game_env):
    m = game_env.module
    game_env.farm.herd_size = 4
    result = m.project_plan([], 5)
    assert result["rows"] == result["idle"] and result["skipped"] == []
    assert len(result["rows"]) == 5


def test_projection_matches_really_playing_the_same_moves(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 400.0
    farm.herd_size = 3
    result = m.project_plan([[0, "capture", 2], [2, "herd", 2]], 4)
    real = m.clone_farm(farm)
    for offset in range(4):
        if offset == 0:
            real.invest_decoupling("capture")
            real.invest_decoupling("capture")
        if offset == 2:
            real.grow_herd()
            real.grow_herd()
        real.advance_round()
        row = result["rows"][offset]
        assert row["funds"] == pytest.approx(real.funds) and row["score"] == pytest.approx(real.score())
        assert row["per_round"] == pytest.approx(real.methane_this_round())


def test_the_plan_shows_the_counterfactual_for_reference(game_env):
    m = game_env.module
    game_env.farm.herd_size = 5
    game_env.farm.funds = 300.0
    result = m.project_plan([[0, "capture", 3]], 5)
    last = result["rows"][-1]
    assert "baseline" in last and last["baseline"] != last["score"]
    assert last["per_round"] < result["idle"][-1]["per_round"]  # decoupling lowers methane per round


def test_unaffordable_steps_are_skipped_and_said(game_env):
    m = game_env.module
    game_env.farm.funds = 30.0
    result = m.project_plan([[0, "capture", 5]], 5)
    assert any("not bought" in line for line in result["skipped"])
    assert "not bought" in m.plan_summary_message(result)


def test_the_cap_limits_a_planned_herd(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 100000.0
    farm.regional_cap_enabled = True
    result = m.project_plan([[0, "herd", 5]] * 6, 5)
    assert result["rows"][-1]["per_round"] <= m.REGIONAL_CAP + 1e-9


def test_queue_controls_add_remove_clear_and_horizon(game_env):
    m = game_env.module
    _queue(game_env, "feed", 1, 2)
    _queue(game_env, "herd", 0, 1)
    assert m.plan_steps == [[0, "herd", 1], [1, "feed", 2]]  # kept in round order
    assert "Feed Additives x2, 1 round from now" in game_env.elements["plan-queue-list"].innerHTML
    _click(game_env, "plan-undo-button")
    assert len(m.plan_steps) == 1
    _click(game_env, "plan-horizon-10-button")
    assert len(m.project_plan()["rows"]) == 10
    assert game_env.elements["plan-horizon-10-button"].getAttribute("aria-pressed") == "true"
    _click(game_env, "plan-clear-button")
    assert m.plan_steps == [] and game_env.elements["plan-clear-button"].disabled
    _click(game_env, "plan-horizon-5-button")


def test_bad_steps_are_refused(game_env):
    m = game_env.module
    assert not m.add_plan_step(0, "bogus", 1)
    assert not m.add_plan_step(0, "herd", 3)
    assert not m.add_plan_step(10, "herd", 1)
    assert not m.add_plan_step(-1, "herd", 1)
    for _ in range(m.PLAN_MAX_STEPS):
        m.add_plan_step(0, "herd", 1)
    assert not m.add_plan_step(0, "herd", 1)
    game_env.elements["plan-round-select"].value = "x"
    _click(game_env, "plan-add-button")  # junk input is ignored, no crash


def test_output_is_accessible_and_the_chart_uses_line_styles(game_env):
    m = game_env.module
    game_env.farm.herd_size = 3
    result = m.project_plan([[0, "feed", 1]], 5)
    table = m.plan_table_html(result)
    assert "<caption>" in table and 'scope="col"' in table and table.count("<tr>") == 6
    chart = m.plan_chart_svg(result)
    assert "role=\"img\"" in chart and "plan-line--plan" in chart and "plan-line--idle" in chart and "plan-line--base" in chart
    assert ">P<" in chart and ">N<" in chart and ">B<" in chart
    css = (HERE / "style.css").read_text(encoding="utf-8")
    assert "stroke-dasharray" in css[css.index(".plan-line--idle"):css.index(".plan-line--idle") + 80]


def test_planner_is_on_both_pages_and_reachable_on_desktop():
    for page in ("index.html", "pc.html"):
        html = (HERE / page).read_text(encoding="utf-8")
        for rid in ("planner-panel", "plan-add-button", "plan-table", "plan-chart", "plan-horizon-10-button"):
            assert f'id="{rid}"' in html
    cfg = json.loads((HERE / "pc-config.json").read_text(encoding="utf-8"))
    assert "#planner-panel" in cfg["zones"]["side"]
