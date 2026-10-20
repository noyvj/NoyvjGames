"""Edge-case tests for naming.py."""

import naming


def test_sanitise_handles_non_string_and_empty_input():
    assert naming.sanitise(None) == ""
    assert naming.sanitise(5) == ""
    assert naming.sanitise("") == ""


def test_sanitise_clamps_to_max_length():
    long_input = "a" * 100
    result = naming.sanitise(long_input)
    assert len(result) == naming.MAX_LEN


def test_get_returns_empty_string_for_non_dict_and_missing_key():
    assert naming.get("not a dict") == ""
    assert naming.get({}) == ""


def test_set_name_clears_key_when_sanitised_result_is_empty():
    ui = {"settlement_name": "Old"}
    naming.set_name(ui, "   ")
    assert "settlement_name" not in ui


def test_suggest_falls_back_for_unknown_era_and_invalid_seed_types():
    name_from_unknown_era = naming.suggest("unknown_era", 0)
    assert len(name_from_unknown_era) > 0
    name_from_bool_seed = naming.suggest("tribal", True)
    assert len(name_from_bool_seed) > 0


def test_title_and_with_name_handle_empty_strings():
    assert naming.title("") == "Continuum"
    assert naming.with_name("", "Founded") == "Founded"
