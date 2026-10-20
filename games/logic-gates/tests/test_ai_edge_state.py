"""Edge-case tests for state.py: limits, clamping, rejection, and default handling."""

import levels
import state


def test_clean_record_handles_non_dict_and_empty_dict():
    # Non-dict input returns a fresh default record
    rec = state.clean_record("garbage")
    assert rec == state.new_record()
    # Empty dict also returns defaults
    rec = state.clean_record({})
    assert rec == state.new_record()


def test_clean_record_clamps_and_rejects_chips():
    # Boolean chips are rejected (treated as None)
    rec = state.clean_record({"chips": True})
    assert rec["chips"] is None
    # Float chips are clamped to 0-500
    rec = state.clean_record({"chips": -1.5})
    assert rec["chips"] == 0
    rec = state.clean_record({"chips": 600.9})
    assert rec["chips"] == 500
    # Valid int chips pass through
    rec = state.clean_record({"chips": 42})
    assert rec["chips"] == 42


def test_clean_record_par_depends_on_solved():
    # par is True only when solved is True and par key is True
    rec = state.clean_record({"solved": False, "par": True})
    assert rec["par"] is False
    rec = state.clean_record({"solved": True, "par": True})
    assert rec["par"] is True


def test_clean_record_clamps_hints():
    # Hints are clamped to MAX_HINT (3) and 0
    rec = state.clean_record({"hints": -5})
    assert rec["hints"] == 0
    rec = state.clean_record({"hints": 10})
    assert rec["hints"] == state.MAX_HINT


def test_clean_tier_record_rejects_boolean_chips():
    # Boolean chips should be rejected for tier records too
    rec = state.clean_tier_record({"chips": False, "par": True})
    assert rec["chips"] is None
    assert rec["par"] is True  # par does not depend on solved in tiers


def test_clean_circuit_limits_chips_and_rejects_invalid_types():
    level = levels.BY_ID["straight-through"]
    allowed = ["not", "and", "or"]
    # Non-dict data returns empty circuit
    circ = state.clean_circuit([], level, allowed)
    assert circ == state.empty_circuit()
    # Too many chips are dropped
    chips = [{"id": i + 1, "type": "not"} for i in range(level["cap"] + 5)]
    circ = state.clean_circuit({"chips": chips}, level, allowed)
    assert len(circ["chips"]) == level["cap"]
    # Invalid chip type is dropped
    circ = state.clean_circuit({"chips": [{"id": 1, "type": "invalid"}]}, level, allowed)
    assert not circ["chips"]


def test_meta_to_dict_returns_empty_for_default_meta():
    meta = state.new_meta()
    out = state.meta_to_dict(meta)
    assert out == {}


def test_meta_to_dict_includes_only_non_defaults():
    meta = state.new_meta()
    meta["levels"]["straight-through"] = dict(state.new_record(), solved=True, chips=0, par=True)
    meta["stats"]["chips"] = 1
    out = state.meta_to_dict(meta)
    assert "levels" in out and "straight-through" in out["levels"]
    assert "stats" in out and out["stats"]["chips"] == 1
    # Default keys should not appear
    assert "found" not in out
    assert "current" not in out


def test_clean_meta_clamps_stats_and_filters_found():
    data = {
        "stats": {"chips": -10, "wires": 2e7, "flips": 5},
        "found": [True, -1, 300, 10.5, 42]
    }
    meta = state.clean_meta(data)
    assert meta["stats"]["chips"] == 0
    assert meta["stats"]["wires"] == state.COUNTER_MAX
    assert meta["stats"]["flips"] == 5
    # found should be sorted unique ints in range
    assert meta["found"] == [42]


def test_merge_meta_keeps_better_records():
    mine = state.new_meta()
    theirs = state.new_meta()
    mine["levels"]["straight-through"] = dict(state.new_record(), solved=True, chips=5, par=False)
    theirs["levels"]["straight-through"] = dict(state.new_record(), solved=False, chips=3, par=True)
    merged = state.merge_meta(mine, theirs)
    # solved is union (or), chips is min, par is union (or)
    assert merged["levels"]["straight-through"]["solved"] is True
    assert merged["levels"]["straight-through"]["chips"] == 3
    assert merged["levels"]["straight-through"]["par"] is True
