"""Recursive refinery expansion: what it takes to refine the resources that
are short, from the Foundry recipes in REFINERY_RECIPES."""

from .test_tracker import _find_row, _reset_to_known_state


def _all_text(node):
    parts = [node.textContent or "", node.innerHTML or ""]
    for child in node.children:
        parts.append(_all_text(child))
    return " ".join(parts)


def test_every_refined_resource_has_a_recipe(game_env):
    m = game_env.module
    refined = {n for n, where in m.RESOURCE_LOCATIONS.items() if where.startswith("Refined from")}
    assert refined <= set(m.REFINERY_RECIPES)


def test_recipe_shape_is_sane(game_env):
    m = game_env.module
    for name, recipe in m.REFINERY_RECIPES.items():
        assert recipe["output"] > 0 and recipe["credits"] > 0, name
        assert recipe["primary"] in recipe["ingredients"], name
        # the primary raw material maps one to one onto the output
        assert recipe["ingredients"][recipe["primary"]] == recipe["output"], name
        assert all(qty > 0 for qty in recipe["ingredients"].values()), name


def test_plan_rounds_up_to_whole_crafts(game_env):
    m = game_env.module
    plan = m.refinery_plan("Pyrotic Alloy", 25)
    assert plan["crafts"] == 2 and plan["produces"] == 40
    assert plan["ingredients"] == {"Pyrol": 40, "Cryotic": 400, "Rubedo": 100}
    assert plan["credits"] == 2000 and plan["primary"] == "Pyrol"


def test_raw_on_hand_reduces_only_the_primary_material(game_env):
    m = game_env.module
    plan = m.refinery_plan("Pyrotic Alloy", 20, raw_have=15)
    assert plan["ingredients"]["Pyrol"] == 5
    assert plan["ingredients"]["Cryotic"] == 200
    covered = m.refinery_plan("Pyrotic Alloy", 20, raw_have=500)
    assert "Pyrol" not in covered["ingredients"] and covered["crafts"] == 1


def test_no_plan_when_nothing_short_or_not_refined(game_env):
    m = game_env.module
    assert m.refinery_plan("Pyrotic Alloy", 0) is None
    assert m.refinery_plan("Ferrite", 100) is None
    assert m.refinery_plan("Nonsense", 5) is None


def test_resource_rows_carry_the_plan_only_while_short(game_env):
    m = game_env.module
    _reset_to_known_state(m, parts={"Phahd Scaffold": {"owned": 0, "target": 1}})
    _, rows = m.calculate()
    pyrotic = next(r for r in rows if r["name"] == "Pyrotic Alloy")
    assert pyrotic["refinery"]["crafts"] == 3  # needs 60, 20 per craft
    ferrite_like = next(r for r in rows if r["name"] == "Grokdrul")
    assert ferrite_like["refinery"] is None
    m.state["inventory"]["Pyrotic Alloy"] = {"built": 60, "raw": 0}
    _, rows = m.calculate()
    assert next(r for r in rows if r["name"] == "Pyrotic Alloy")["refinery"] is None


def test_totals_sum_across_resources_and_include_credits(game_env):
    m = game_env.module
    _reset_to_known_state(m, parts={"Phahd Scaffold": {"owned": 0, "target": 1}})
    _, rows = m.calculate()
    totals = m.refinery_totals(rows)
    assert totals["Pyrol"] == 60
    assert totals["Cryotic"] == 600
    assert totals["Credits"] == sum(r["refinery"]["credits"] for r in rows if r["refinery"])


def test_rendered_row_and_summary_show_the_breakdown(game_env):
    m = game_env.module
    _reset_to_known_state(m, parts={"Phahd Scaffold": {"owned": 0, "target": 1}})
    m.render()
    row = _find_row(game_env.elements["resources-body"], "data-resource", "Pyrotic Alloy")
    text = _all_text(row)
    assert "refine: 3 craft(s)" in text and "Pyrol ×60" in text
    box = game_env.elements["refinery-summary"]
    assert box.hidden is False and "Pyrol ×60" in box.textContent


def test_summary_hidden_when_nothing_to_refine(game_env):
    m = game_env.module
    _reset_to_known_state(m)
    m.render()
    assert game_env.elements["refinery-summary"].hidden is True
