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
    assert rows["Warming held back"]["unit"] == "\u00b0C"
    assert rows["Rounds played"]["value"] == 0


def test_numbers_are_the_real_region_values(game_env):
    m = game_env.module
    m.region.counterfactual_temperature = 3.0
    m.region.temperature = 2.0
    m.region.restored_total = 0.4
    m.region.round_number = 8
    rows = by_label(m.get_state()["summary"])
    assert rows["Warming held back"]["value"] == 1.0
    assert rows["Warming pulled back by restoration"]["value"] == 0.4
    assert rows["Rounds played"]["value"] == 7


def test_negative_savings_never_show_below_zero(game_env):
    m = game_env.module
    m.region.counterfactual_temperature = 1.0
    m.region.temperature = 2.0
    assert by_label(m.get_state()["summary"])["Warming held back"]["value"] == 0


def test_summary_is_ignored_on_load(game_env):
    m = game_env.module
    data = m.get_state()
    data["summary"] = [{"label": "x", "value": 999, "unit": ""}]
    m.load_state(data)
    assert all(i["value"] != 999 for i in m.get_state()["summary"])
