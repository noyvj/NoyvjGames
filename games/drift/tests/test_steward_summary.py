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
    assert rows["Wellbeing score"]["unit"] == "of 100"
    assert rows["Newcomers integrated"]["value"] == 0
    assert rows["Rounds played"]["value"] == 0


def test_numbers_are_the_real_region_values(game_env):
    m = game_env.module
    m.region.total_arrivals = 100.0
    m.region.integrated_population = 40.0
    m.region.round_number = 5
    rows = by_label(m.get_state()["summary"])
    assert rows["Newcomers integrated"]["value"] == 40
    assert rows["Wellbeing score"]["value"] == round(m.region.wellbeing_score())
    assert rows["Rounds played"]["value"] == 4


def test_summary_is_ignored_on_load(game_env):
    m = game_env.module
    data = m.get_state()
    data["summary"] = [{"label": "x", "value": 999, "unit": ""}]
    m.load_state(data)
    assert all(i["value"] != 999 for i in m.get_state()["summary"])
