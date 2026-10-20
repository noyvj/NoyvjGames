"""Edge-case tests for neighbours.py."""

import pytest

import neighbours
import sim


def test_clean_clamps_attitude_to_bounds():
    raw = {"slots": {sid: {"attitude": 100} for sid in neighbours.SLOT_IDS}}
    record = neighbours.clean(raw)
    assert all(slot["attitude"] == neighbours.ATTITUDE_MAX for slot in record["slots"].values())

    raw = {"slots": {sid: {"attitude": -50} for sid in neighbours.SLOT_IDS}}
    record = neighbours.clean(raw)
    assert all(slot["attitude"] == neighbours.ATTITUDE_MIN for slot in record["slots"].values())


def test_clean_clamps_lease_values():
    raw = {
        "lease": {"holder": "you", "until": 10**8, "pending": 10**6, "auctions": 10**6}
    }
    record = neighbours.clean(raw)
    assert record["lease"]["until"] == 10**7
    assert record["lease"]["pending"] == 10**5
    assert record["lease"]["auctions"] == 10**5


def test_trade_rate_with_extreme_attitudes():
    # Attitude below minimum should still clamp the rate to its floor of 0.4
    assert neighbours.trade_rate(-100) == pytest.approx(0.4)
    # Attitude above maximum grows linearly without an upper cap in the function itself
    assert neighbours.trade_rate(100) > neighbours.trade_rate(50)


def test_batch_size_with_negative_and_large_era_index():
    # Negative era index should clamp to 0, giving base batch size
    assert neighbours.batch_size(-5) == 4
    # Zero era index gives base batch size
    assert neighbours.batch_size(0) == 4
    # Large era index clamps to the last era's batch size
    max_batch = neighbours.batch_size(len(sim.ERA_ORDER) - 1)
    assert neighbours.batch_size(1000) == max_batch


def test_place_bid_rejects_zero_and_negative():
    ui = {"neighbours": neighbours.default()}
    resources = {"materials": 100.0}
    ok, _ = neighbours.place_bid(ui, 0, resources, 1, 0)
    assert ok is False
    ok, _ = neighbours.place_bid(ui, -5, resources, 1, 0)
    assert ok is False


def test_place_bid_clamps_to_max_and_checks_resources():
    ui = {"neighbours": neighbours.default()}
    resources = {"materials": 50.0}
    # Amount larger than available materials should be rejected
    ok, _ = neighbours.place_bid(ui, 10**6, resources, 1, 0)
    assert ok is False
    # Amount exactly matching available materials should succeed
    ok, _ = neighbours.place_bid(ui, 50.0, resources, 1, 0)
    assert ok


def test_ai_bid_clamps_to_minimum_one():
    # High attitude reduces the bid significantly; ensure it never drops below 1
    low_bid = neighbours.ai_bid(7, "n1", 0, 100, 0)
    assert low_bid >= 1
    # Negative attitude increases the bid
    high_bid = neighbours.ai_bid(7, "n1", 0, -100, 0)
    assert high_bid > low_bid


def test_next_share_candidate_handles_empty_and_invalid_inputs():
    record = neighbours.default()
    # Empty researched list returns None
    assert neighbours.next_share_candidate(record, "n1", [], {}) is None
    # Missing costs for all nodes returns None
    assert neighbours.next_share_candidate(record, "n1", ["a"], {}) is None
    # Invalid node types are skipped
    assert neighbours.next_share_candidate(record, "n1", [123, None], {"a": 10}) is None
