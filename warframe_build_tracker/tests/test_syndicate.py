"""Syndicate layer: refined resources' blueprints are standing-gated."""

from .test_refinery import _all_text
from .test_tracker import _find_row, _reset_to_known_state


def _short_pyrotic(m):
    _reset_to_known_state(m, parts={"Phahd Scaffold": {"owned": 0, "target": 1}},
                          inventory={"Heart Nyth": {"built": 5, "raw": 0}, "Seram Beetle Shell": {"built": 9, "raw": 0},
                                     "Grokdrul": {"built": 99, "raw": 0}})
    m.state["blueprints"] = {}


def test_every_refined_resource_has_a_source(game_env):
    m = game_env.module
    assert set(m.SYNDICATE_SOURCES) == set(m.REFINERY_RECIPES)
    for name, source in m.SYNDICATE_SOURCES.items():
        assert source["standing"] > 0 and source["faction"] and source["vendor"] and source["rank"], name


def test_ownership_is_explicit_or_inferred_from_stock(game_env):
    m = game_env.module
    _reset_to_known_state(m)
    m.state["blueprints"] = {}
    assert m.blueprint_owned("Pyrotic Alloy") is False
    m.state["inventory"]["Pyrotic Alloy"] = {"built": 5, "raw": 0}
    assert m.blueprint_owned("Pyrotic Alloy") is True  # stock proves it
    m.state["blueprints"]["Pyrotic Alloy"] = False
    assert m.blueprint_owned("Pyrotic Alloy") is False  # an explicit untick wins


def test_standing_needed_counts_only_short_unowned_blueprints(game_env):
    m = game_env.module
    _short_pyrotic(m)
    _, rows = m.calculate()
    assert m.standing_needed(rows) == {"Ostron": 500}
    m.state["blueprints"]["Pyrotic Alloy"] = True
    assert m.standing_needed(rows) == {}
    assert m.syndicate_text(rows) == ""


def test_text_lists_each_faction(game_env):
    m = game_env.module
    rows = [
        {"name": "Pyrotic Alloy", "built_short": 5},
        {"name": "Marquise Thyst", "built_short": 3},
        {"name": "Hespazym Alloy", "built_short": 1},
        {"name": "Ferrite", "built_short": 99},
    ]
    _reset_to_known_state(game_env.module)
    m.state["blueprints"] = {}
    assert m.syndicate_text(rows) == "Blueprint standing still to earn: Ostron 500 · Solaris United 16,000."


def test_row_shows_the_source_and_checkbox_drives_the_summary(game_env):
    m = game_env.module
    _short_pyrotic(m)
    m.render()
    row = _find_row(game_env.elements["resources-body"], "data-resource", "Pyrotic Alloy")
    assert "Old Man Suumbaat (Ostron), 500 standing, rank Neutral" in _all_text(row)
    assert "Ostron 500" in game_env.elements["syndicate-summary"].textContent
    box = _find_checkbox(row)
    box.checked = True
    box.dispatch("change", None)
    assert m.state["blueprints"]["Pyrotic Alloy"] is True
    assert game_env.elements["syndicate-summary"].hidden is True


def _find_checkbox(node):
    if node.attributes.get("class") == "blueprint-input" or getattr(node, "className", "") == "blueprint-input":
        return node
    for child in node.children:
        found = _find_checkbox(child)
        if found is not None:
            return found
    return None


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    _reset_to_known_state(m)
    m.state["blueprints"] = {}
    assert "blueprints" not in m.get_state()
    m.state["blueprints"] = {"Pyrotic Alloy": True}
    saved = m.get_state()
    m.state["blueprints"] = {}
    m.load_state(saved)
    assert m.state["blueprints"] == {"Pyrotic Alloy": True}
    m.load_state({"blueprints": {"Pyrotic Alloy": "yes", "Nonsense": True, "Tear Azurite": False}})
    assert m.state["blueprints"] == {"Tear Azurite": False}
    m.load_state({"blueprints": [1, 2]})
    assert m.state["blueprints"] == {}
