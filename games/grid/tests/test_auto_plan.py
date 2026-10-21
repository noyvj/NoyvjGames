import json
from pathlib import Path

from .pagefiles import page_text

# Auto-plan suggestion, panel and button (R4-GRMO-7). The tests use game_env so the module is loaded
# against the fake page (grid_coach needs `js`) and no global state leaks into the next test.


def test_fresh_game_suggests_hydro(game_env):
    result = game_env.module.auto_plan_suggestion()
    assert result["plant"] == "hydro"
    assert result["text"] == (
        "Build one Hydro plant for 150 funds. It adds 40 capacity and closes 40 of the 110 shortfall "
        "expected next round."
    )


def test_enough_capacity_suggests_nothing(game_env):
    game_env.state.plant_counts["nuclear"] = 2
    result = game_env.module.auto_plan_suggestion()
    assert result["plant"] is None
    assert result["text"] == "Nothing to build this round: capacity 200 already covers next round's demand of 110."


def test_too_little_funds_says_to_save_up(game_env):
    game_env.state.funds = 50
    result = game_env.module.auto_plan_suggestion()
    assert result["plant"] is None
    assert result["text"] == "Save up: the cheapest renewable plant costs 70 and you have 50. Next round is 110 short."


def test_funds_100_suggests_wind(game_env):
    game_env.state.funds = 100
    assert game_env.module.auto_plan_suggestion()["plant"] == "wind"


def test_autoplan_markup_is_in_the_page_and_the_desktop_zone():
    text = page_text()
    for element_id in ("autoplan-panel", "autoplan-text", "autoplan-build-button"):
        assert f'id="{element_id}"' in text
    config = json.loads((Path(__file__).resolve().parents[1] / "pc-config.json").read_text(encoding="utf-8"))
    assert "#autoplan-panel" in config["zones"]["side"]


def test_render_shows_the_suggestion_and_enables_the_button(game_env):
    game_env.module.render()
    assert game_env.elements["autoplan-text"].innerText.startswith("Build one Hydro plant")
    assert game_env.elements["autoplan-build-button"].disabled is False


def test_render_disables_the_button_when_nothing_is_affordable(game_env):
    game_env.state.funds = 0
    game_env.module.render()
    assert game_env.elements["autoplan-text"].innerText.startswith("Save up:")
    assert game_env.elements["autoplan-build-button"].disabled is True
    assert game_env.elements["autoplan-build-button"].title == "Nothing to build right now."


def test_clicking_the_button_builds_the_suggested_plant(game_env):
    game_env.elements["autoplan-build-button"].dispatch("click", None)
    assert game_env.state.plant_counts["hydro"] == 1
    assert game_env.state.funds == 350


def test_clicking_the_button_builds_nothing_when_nothing_is_suggested(game_env):
    game_env.state.funds = 0
    game_env.elements["autoplan-build-button"].dispatch("click", None)
    assert all(count == 0 for count in game_env.state.plant_counts.values())
    assert game_env.state.funds == 0
