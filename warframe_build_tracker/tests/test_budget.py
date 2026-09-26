"""Batch A #3: credits and endo budget beside the refinery plan."""

from .helpers import click, known_state


def _rows(m, short=3, raw_have=0):
    return [{"name": "Heart Nyth", "built_short": short, "raw_have": raw_have,
             "refinery": m.refinery_plan("Heart Nyth", short, raw_have)}]


def test_farm_limited_when_credits_cover_it(game_env):
    m = game_env.module
    m.state["budget"] = {"credits": 20000, "endo": 0}
    status = m.budget_status(_rows(m))
    assert status["needed"] == 10000 and status["materials"] == {"Nyth": 3}
    assert status["limit"] == "farming" and status["short"] == 0
    assert "Farm-limited" in m.budget_text(_rows(m))


def test_credit_limited_and_both(game_env):
    m = game_env.module
    m.state["budget"] = {"credits": 4000, "endo": 0}
    assert m.budget_status(_rows(m))["limit"] == "both"
    assert "short 6,000 credits" in m.budget_text(_rows(m))
    # raw Nyth on hand means nothing left to gather: credits alone limit it
    status = m.budget_status(_rows(m, raw_have=3))
    assert status["limit"] == "credits" and status["short"] == 6000
    assert "Credit-limited: short 6,000" in m.budget_text(_rows(m, raw_have=3))


def test_nothing_limiting_and_not_entered(game_env):
    m = game_env.module
    m.state["budget"] = {"credits": 50000, "endo": 0}
    assert m.budget_status(_rows(m, raw_have=3))["limit"] == "none"
    m.state["budget"] = {"credits": 0, "endo": 0}
    assert m.budget_status(_rows(m, raw_have=3))["limit"] == "unknown"
    assert "Enter credits on hand" in m.budget_text(_rows(m, raw_have=3))
    assert m.budget_text([]) == ""


def test_endo_is_only_shown(game_env):
    m = game_env.module
    m.state["budget"] = {"credits": 0, "endo": 12000}
    text = m.budget_text([])
    assert "Endo on hand: 12,000" in text and "no live data" in text


def test_inputs_persist_and_show_in_the_summary(game_env):
    m = game_env.module
    known_state(m, parts={"Phahd Scaffold": {"owned": 0, "target": 1}},
                inventory={"Grokdrul": {"built": 99}, "Seram Beetle Shell": {"built": 9}, "Pyrotic Alloy": {"built": 99}})
    els = game_env.elements
    els["budget-credits-input"].value = "4000"
    els["budget-endo-input"].value = "250"
    els["budget-credits-input"].dispatch("change", None)
    assert m.state["budget"] == {"credits": 4000, "endo": 250}
    assert els["budget-summary"].hidden is False
    assert "Credit-limited" in els["budget-summary"].textContent or "both" in els["budget-summary"].textContent.lower()
    assert "Endo on hand: 250" in els["budget-summary"].textContent
    els["budget-credits-input"].value = "-5"
    els["budget-credits-input"].dispatch("change", None)
    assert m.state["budget"]["credits"] == 0
    els["budget-credits-input"].value = "abc"
    els["budget-credits-input"].dispatch("change", None)
    assert m.state["budget"]["credits"] == 0
    click(els["reset-button"])  # reset leaves the budget alone


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    assert "budget" not in m.get_state()
    m.state["budget"] = {"credits": 5, "endo": 0}
    saved = m.get_state()
    m.state["budget"] = {"credits": 0, "endo": 0}
    m.load_state(saved)
    assert m.state["budget"] == {"credits": 5, "endo": 0}
    m.load_state({"budget": {"credits": -1, "endo": "9", "extra": 1}})
    assert m.state["budget"] == {"credits": 0, "endo": 0}
    m.load_state({"budget": {"credits": True, "endo": 10 ** 12}})
    assert m.state["budget"] == {"credits": 0, "endo": 0}
    m.load_state({"budget": 5})
    assert m.state["budget"] == {"credits": 0, "endo": 0}
