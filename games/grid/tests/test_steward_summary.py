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
    assert rows["Rounds played"]["value"] == len(m.state.clean_fraction_log)
    assert rows["Renewable share of capacity"]["unit"] == "%"


def test_renewable_share_is_the_real_capacity_share(game_env):
    m = game_env.module
    for t in m.state.plant_counts:
        m.state.plant_counts[t] = 0
    m.state.plant_counts["solar"] = 2
    assert by_label(m.get_state()["summary"])["Renewable share of capacity"]["value"] == 100
    m.state.plant_counts["coal"] = 2
    expected = round(m.renewable_capacity_share() * 100)
    assert by_label(m.get_state()["summary"])["Renewable share of capacity"]["value"] == expected
    assert 0 < expected < 100


def test_plants_built_counts_cumulative_builds(game_env):
    m = game_env.module
    m.state.cumulative_built["solar"] = 3
    m.state.cumulative_built["wind"] = 2
    assert by_label(m.get_state()["summary"])["Plants built"]["value"] == sum(m.state.cumulative_built.values())


def test_summary_is_ignored_on_load(game_env):
    m = game_env.module
    data = m.get_state()
    data["summary"] = [{"label": "x", "value": 999, "unit": ""}]
    assert m.load_state(data) is not False
    assert all(i["value"] != 999 for i in m.get_state()["summary"])
