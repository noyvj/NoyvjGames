"""Edge-case tests for casekit.C."""

from casekit import C


def test_truth_accepts_string_and_converts_to_tuple():
    """truth as a single string should be wrapped into a one-element tuple."""
    case = C("t-1", "Test House", "villa", "glimmer", ("glimmer",), (("hall",),))
    assert case["truth"] == ("glimmer",)


def test_truth_accepts_list_and_converts_to_tuple():
    """truth as a list of strings should be converted to a tuple."""
    case = C("t-2", "Test House", "villa", ["pacer", "tangle"], ("glimmer",), (("hall",),))
    assert case["truth"] == ("pacer", "tangle")


def test_restless_handles_empty_input():
    """restless as an empty list should result in an empty tuple."""
    case = C("t-3", "Test House", "villa", "glimmer", (), [])
    assert case["restless"] == ()


def test_features_defaults_to_empty_dict_when_none():
    """features passed as None should default to an empty dictionary."""
    case = C("t-4", "Test House", "villa", "glimmer", (), ((),), features=None)
    assert case["features"] == {}


def test_keepsake_returns_none_when_missing_and_tuple_when_present():
    """keepsake should be None when omitted, and a tuple when provided."""
    case_no = C("t-5", "Test House", "villa", "glimmer", (), ((),))
    assert case_no["keepsake"] is None

    case_yes = C("t-6", "Test House", "villa", "glimmer", (), ((),), keepsake=("bedroom", "handmirror", "curious"))
    assert case_yes["keepsake"] == ("bedroom", "handmirror", "curious")
