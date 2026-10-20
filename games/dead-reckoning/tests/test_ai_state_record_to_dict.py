import state
from state import new_record


def test_record_to_dict_returns_empty_for_fresh_record():
    """A fresh record matches all defaults, so nothing is stored."""
    rec = new_record()
    assert state.record_to_dict(rec) == {}


def test_record_to_dict_keeps_only_non_default_values():
    """Only keys that differ from the fresh record are returned."""
    rec = new_record()
    rec["stars"] = 3
    rec["attempts"] = 5
    res = state.record_to_dict(rec)
    assert res == {"stars": 3, "attempts": 5}


def test_record_to_dict_excludes_defaults_even_when_present():
    """Explicitly setting a key to its default value must not include it."""
    rec = new_record()
    rec["stars"] = 0
    rec["best_error_nm"] = None
    res = state.record_to_dict(rec)
    assert "stars" not in res and "best_error_nm" not in res
