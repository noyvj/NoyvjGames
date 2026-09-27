"""Batch B #9: the "am I wasting anything?" audit."""

import wf_insight

from .helpers import all_text, known_state


def _audit(m):
    _c, resources = m.calculate()
    return wf_insight.waste_audit(resources, m.state["inventory"], list(m.RESOURCE_LOCATIONS), m.REFINERY_RECIPES,
                                  m.blueprint_owned, m.resource_usage)


def test_a_quiet_state_flags_nothing(game_env):
    m = game_env.module
    known_state(m)
    audit = _audit(m)
    assert audit == {"overstock": [], "idle": [], "refinable": [], "blueprints": []}
    assert wf_insight.audit_lines(audit) == ["Nothing stands out: no overstock, no refinable raw stock, no idle blueprints."]


def test_overstock_needs_both_the_ratio_and_the_spare_units(game_env):
    m = game_env.module
    # Ooltha Strike needs Fish Scales 25 (Iradite 20, Pyrotic Alloy 60, Tear Azurite 10)
    known_state(m, parts={"Ooltha Strike": {"owned": 0}},
                inventory={"Fish Scales": {"built": 40, "raw": 20}, "Iradite": {"built": 39}, "Pyrotic Alloy": {"built": 130},
                           "Tear Azurite": {"built": 12, "raw": 8}})
    flagged = {o["name"]: o for o in _audit(m)["overstock"]}
    assert flagged["Fish Scales"] == {"name": "Fish Scales", "have": 60, "need": 25, "spare": 35}  # built + raw pooled
    assert "Pyrotic Alloy" in flagged and flagged["Pyrotic Alloy"]["spare"] == 70
    assert "Iradite" not in flagged  # 39 is under twice 20
    assert "Tear Azurite" in flagged  # 20 is exactly twice 10 with exactly the 10 spare units: flagged
    m.state["inventory"]["Tear Azurite"] = {"built": 12, "raw": 7}
    assert "Tear Azurite" not in {o["name"] for o in _audit(m)["overstock"]}  # 19: under twice the need


def test_stock_no_unfinished_part_needs_is_listed_as_idle(game_env):
    m = game_env.module
    known_state(m, inventory={"Ferrite": {"built": 900}, "Circuits": {"built": 3}})
    idle = _audit(m)["idle"]
    assert idle == [{"name": "Ferrite", "have": 900}]  # 3 Circuits is under the 10-unit floor
    assert "Held but no unfinished part needs it any more: Ferrite (900)" in "\n".join(wf_insight.audit_lines(_audit(m)))


def test_refinable_raw_stock(game_env):
    m = game_env.module
    known_state(m, parts={"Ooltha Strike": {"owned": 0}}, inventory={"Tear Azurite": {"built": 0, "raw": 35}})
    refinable = _audit(m)["refinable"]
    assert len(refinable) == 1
    item = refinable[0]
    assert item["name"] == "Tear Azurite" and item["primary"] == "Azurite" and item["raw"] == 35
    recipe = m.REFINERY_RECIPES["Tear Azurite"]
    assert item["crafts"] == 35 // recipe["ingredients"]["Azurite"] and item["makes"] == item["crafts"] * recipe["output"]
    assert item["short"] == 10
    assert "Only the raw material was checked" in "\n".join(wf_insight.audit_lines(_audit(m)))
    m.state["inventory"]["Tear Azurite"]["raw"] = 3  # not enough for one craft
    assert _audit(m)["refinable"] == []
    m.state["inventory"]["Tear Azurite"] = {"built": 10, "raw": 35}  # nothing short any more
    assert _audit(m)["refinable"] == []


def test_blueprint_marked_owned_but_the_resource_is_not_needed(game_env):
    m = game_env.module
    known_state(m)
    m.state["blueprints"] = {"Tear Azurite": True, "Esher Devar": False}
    audit = _audit(m)
    assert audit["blueprints"] == [{"name": "Tear Azurite", "used_anywhere": True}]
    known_state(m, parts={"Ooltha Strike": {"owned": 0}})
    m.state["blueprints"] = {"Tear Azurite": True}
    assert _audit(m)["blueprints"] == []  # an unfinished part needs it again
    assert wf_insight.audit_lines({"overstock": [], "idle": [], "refinable": [],
                                   "blueprints": [{"name": "X", "used_anywhere": False}]})[0].endswith("No part on your list uses it at all.")


def test_ui_shows_the_lines_and_changes_no_needs(game_env):
    m = game_env.module
    known_state(m, inventory={"Ferrite": {"built": 900}})
    before = m.calculate()
    assert "Ferrite (900)" in all_text(game_env.elements["audit-list"])
    assert m.calculate() == before
