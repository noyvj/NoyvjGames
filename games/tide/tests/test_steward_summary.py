"""B-23: the save carries a read-only `summary` list for the hub's Climate Steward page (honest, already computed
numbers only; never read back on load)."""

import math


def assert_valid_summary(summary):
    assert isinstance(summary, list) and 1 <= len(summary) <= 4
    for item in summary:
        assert isinstance(item["label"], str) and 1 <= len(item["label"]) <= 40
        assert isinstance(item["value"], (int, float)) and not isinstance(item["value"], bool)
        assert math.isfinite(item["value"])
        assert isinstance(item["unit"], str) and len(item["unit"]) <= 12
        if "note" in item:
            assert isinstance(item["note"], str) and len(item["note"]) <= 80


def by_label(summary):
    return {i["label"]: i for i in summary}


def test_fresh_game_has_a_valid_summary(game_env):
    m = game_env.module
    s = m.get_state()["summary"]
    assert_valid_summary(s)
    rows = by_label(s)
    assert rows["Coastline rows still dry"]["value"] == m.COASTLINE_ROWS
    assert rows["Coastline rows still dry"]["unit"] == f"of {m.COASTLINE_ROWS}"
    assert rows["Seawall tier"]["value"] == 0


def test_rows_dry_follows_the_sea_and_managed_retreat(game_env):
    m = game_env.module
    m.state.sea_level = 1000.0
    assert by_label(m.get_state()["summary"])["Coastline rows still dry"]["value"] == 0
    m.state.sea_level = 0.0
    m.state.retreat_rows = [m.COASTLINE_ROWS - 1]
    assert by_label(m.get_state()["summary"])["Coastline rows still dry"]["value"] == m.COASTLINE_ROWS - 1


def test_tier_and_population_are_the_real_values(game_env):
    m = game_env.module
    m.state.capacity["adaptation"] = 10
    row = by_label(m.get_state()["summary"])["Seawall tier"]
    assert row["value"] == m.state.current_tier_index() and row["note"] == m.state.current_tier()["name"]
    m.state.population = 37
    assert by_label(m.get_state()["summary"])["Settlers housed"]["value"] == 37


def test_summary_is_ignored_on_load(game_env):
    m = game_env.module
    data = m.get_state()
    data["summary"] = [{"label": "x", "value": 999, "unit": ""}]
    assert m.load_state(data) is not False
    assert by_label(m.get_state()["summary"])["Coastline rows still dry"]["value"] == m.COASTLINE_ROWS
