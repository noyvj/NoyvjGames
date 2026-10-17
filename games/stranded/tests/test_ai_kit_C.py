"""Tests for kit.C(), the choice builder."""

import kit


def test_C_builds_a_choice_dict_with_all_args():
    """Normal case: all arguments provided, including conditions and deltas."""
    c = kit.C("Hello there", "I'm fine, thanks.", "d2a", fx="t1 h-1", need="bit&!battery&t4&h<5", set="helped", get="note")
    assert c["text"] == "Hello there"
    assert c["reply"] == [(None, "I'm fine, thanks.")]
    assert c["to"] == ((None, "d2a"),)
    assert c["fx"] == (1, 0, -1)
    assert c["need"] == {"all": ["bit"], "none": ["battery"], "min": {"trust": 4}, "max": {"hope": 5}}
    assert c["set"] == ("helped",)
    assert c["get"] == ("note",)


def test_C_handles_list_of_replies_and_conditional_routes():
    """Normal case: reply and to are lists, parsing multiple items."""
    c = kit.C("What now?", ["I don't know.", "?bit|You can try."], ["need>scene1", "scene2"])
    assert len(c["reply"]) == 2
    assert c["reply"][0] == (None, "I don't know.")
    assert c["reply"][1] == ({"all": ["bit"], "none": [], "min": {}, "max": {}}, "You can try.")
    assert c["to"] == (({"all": ["need"], "none": [], "min": {}, "max": {}}, "scene1"), (None, "scene2"))


def test_C_defaults_for_optional_args():
    """Edge case: empty strings for optional arguments yield default values."""
    c = kit.C("Hi", "Bye", "d1a")
    assert c["fx"] == (0, 0, 0)
    assert c["need"] is None
    assert c["set"] == ()
    assert c["get"] == ()
