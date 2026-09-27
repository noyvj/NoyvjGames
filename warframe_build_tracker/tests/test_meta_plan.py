"""Batch B #1: the meta build planner (whole chain for a named build, one completion bar)."""

import wf_plans

from .helpers import all_text, find_all, known_state


def _plan(m, name="177"):
    combo = next(c for c in m.all_combos() if c["name"] == name)
    components, _ = m.calculate()
    return wf_plans.meta_plan(combo, components, m.state["inventory"], m.RECIPES, m.refinery_plan)


def test_finished_build_reads_complete(game_env):
    m = game_env.module
    known_state(m)
    plan = _plan(m)
    assert plan["complete"] and plan["percent"] == 100 and plan["rows"] == []
    assert "every part is built" in wf_plans.meta_text(plan)


def test_chain_lists_parts_resources_refinery_and_credits(game_env):
    m = game_env.module
    known_state(m, parts={"Propa Scaffold": {"owned": 0}})
    plan = _plan(m)
    assert plan["built"] == ["Raplak Prism", "Certus Brace"] and plan["to_farm"] == ["Propa Scaffold"]
    need = {r["name"]: r["need"] for r in plan["rows"]}
    assert need == {"Atmo Systems": 2, "Calda Toroid": 3, "Hespazym Alloy": 30, "Tromyzon Entroplasma": 6}
    hespazym = next(r for r in plan["rows"] if r["name"] == "Hespazym Alloy")
    expected = m.refinery_plan("Hespazym Alloy", 30, 0)
    assert hespazym["refinery"] == expected and plan["credits"] == expected["credits"] > 0
    assert plan["percent"] == 67  # two of three parts built, nothing held for the third
    text = wf_plans.meta_text(plan)
    assert "Still to farm: Propa Scaffold" in text and "Hespazym Alloy x30" in text and "Credits for refining" in text


def test_bar_counts_half_a_part_for_holding_its_resources(game_env):
    m = game_env.module
    inventory = {"Atmo Systems": {"built": 2}, "Calda Toroid": {"built": 3}, "Hespazym Alloy": {"built": 30},
                 "Tromyzon Entroplasma": {"built": 6}}
    known_state(m, parts={"Propa Scaffold": {"owned": 0}}, inventory=inventory)
    plan = _plan(m)
    assert plan["percent"] == 83 and plan["credits"] == 0 and not plan["complete"]
    assert "Every resource for the remaining parts is on hand" in wf_plans.meta_text(plan)
    m.state["inventory"]["Atmo Systems"]["built"] = 1  # half of one of four resources: coverage 7/8
    assert _plan(m)["percent"] == round((2 + 0.5 * (1 + 1 + 1 + 0.5) / 4) / 3 * 100)


def test_custom_combos_can_be_planned_and_planning_changes_no_needs(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0}})
    m.add_combo("Mine", ["Rahn Prism", "Raplak Prism"])
    before = m.calculate()
    plan = _plan(m, "Mine")
    assert plan["to_farm"] == ["Rahn Prism"] and plan["combo"]["source"] == "your own list"
    assert m.calculate() == before


def test_ui_select_renders_bar_and_text(game_env):
    m = game_env.module
    known_state(m, parts={"Propa Scaffold": {"owned": 0}})
    els = game_env.elements
    assert els["meta-select"].value == "177"
    bars = find_all(els["meta-bar"], class_name="progress")
    assert bars and bars[0].attributes["aria-valuenow"] == "67"
    assert "67%" in all_text(els["meta-bar"])
    assert "Propa Scaffold" in els["meta-text"].textContent
    m.add_combo("Mine", ["Raplak Prism"])
    m.render()
    els["meta-select"].value = "Mine"
    els["meta-select"].dispatch("change", None)
    assert "Mine (amp" in els["meta-text"].textContent and "every part is built" in els["meta-text"].textContent
    assert m._planner.ui["meta"] == "Mine"
