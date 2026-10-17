"""Tests for state.clean_tier_record()."""

import state


def test_valid_record_returns_clamped_chips_and_true_par():
    data = state.new_tier_record()
    data["chips"] = 42
    data["par"] = True
    rec = state.clean_tier_record(data)
    assert rec == {"chips": 42, "par": True}


def test_out_of_bounds_chips_is_clamped_to_range():
    data_high = state.new_tier_record()
    data_high["chips"] = 600
    rec_high = state.clean_tier_record(data_high)
    assert rec_high["chips"] == 500

    data_low = state.new_tier_record()
    data_low["chips"] = -10
    rec_low = state.clean_tier_record(data_low)
    assert rec_low["chips"] == 0


def test_non_dict_input_returns_default_record():
    rec = state.clean_tier_record("garbage")
    assert rec == {"chips": None, "par": False}
