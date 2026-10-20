"""Tests for neighbours.batch_size()."""

import sim
from neighbours import batch_size


def test_batch_size_at_era_zero():
    assert batch_size(0) == 4


def test_batch_size_at_mid_era():
    # Era index 3 corresponds to the fourth era (e.g., Medieval).
    assert batch_size(3) == 10


def test_batch_size_caps_at_max_era():
    max_idx = len(sim.ERA_ORDER) - 1
    expected = 4 + 2 * max_idx
    assert batch_size(max_idx + 100) == expected
