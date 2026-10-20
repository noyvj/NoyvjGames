"""Edge-case tests for unease.py public functions."""

import pytest
from unittest.mock import patch

import data
from mysteries import UNEASE_CAP
import unease


class TestClamp:
    def test_clamp_returns_value_when_inside_bounds(self):
        """clamp returns the input when it is within [0, UNEASE_CAP]."""
        assert unease.clamp(50) == 50

    def test_clamp_returns_zero_for_negative_input(self):
        """clamp returns 0 for any negative value."""
        assert unease.clamp(-10) == 0

    def test_clamp_returns_cap_for_large_input(self):
        """clamp returns UNEASE_CAP for any value exceeding it."""
        assert unease.clamp(UNEASE_CAP + 100) == UNEASE_CAP


class TestMeterAfterNight:
    def test_meter_clamps_negative_result_from_letter_delivery(self):
        """A letter delivered on a low meter should not drop below zero."""
        assert unease.meter_after_night(5, 0, 0, True, False) == 0

    def test_meter_adds_ten_for_worst_condition(self):
        """Worst condition adds exactly 10 to the meter."""
        assert unease.meter_after_night(0, 4, 0, False, False) == 10

    def test_meter_adds_fog_ticks_when_no_worst_condition(self):
        """Fog ticks >= 8 adds 7, otherwise adds 2 when worst_cond != 4."""
        assert unease.meter_after_night(0, 3, 7, False, False) == 2
        assert unease.meter_after_night(0, 3, 8, False, False) == 7


class TestTrifleChance:
    def test_trifle_chance_at_zero_unease(self):
        """Returns the base chance when unease is zero."""
        assert unease.trifle_chance(0) == pytest.approx(0.05)

    def test_trifle_chance_at_cap(self):
        """Returns the maximum chance when unease equals UNEASE_CAP."""
        assert unease.trifle_chance(UNEASE_CAP) == 0.45

    def test_trifle_chance_with_negative_unease(self):
        """Negative unease yields a chance lower than the base rate."""
        assert unease.trifle_chance(-100) < 0.05


class TestOddAllowed:
    def test_odd_not_allowed_on_first_three_nights(self):
        """Nights 1, 2, and 3 never allow odd beats."""
        for n in range(1, 4):
            assert not unease.odd_allowed(n), f"night {n}"

    def test_odd_not_allowed_on_season_start(self):
        """The first night of each season is excluded."""
        assert not unease.odd_allowed(1)
        assert not unease.odd_allowed(data.NIGHTS_PER_SEASON + 1)

    def test_odd_allowed_on_valid_night(self):
        """Night 4 is the first allowed odd night per FIRST_ODD_NIGHT."""
        assert unease.odd_allowed(4)


class TestBeatTick:
    def test_beat_tick_returns_minus_one_for_morning(self):
        """Morning beats always return -1."""
        assert unease.beat_tick(10, "morning") == -1

    @patch("unease.night_len")
    def test_beat_tick_respects_night_len_minus_two(self, mock_len):
        """Returns min(night_len - 2, fraction) to avoid out-of-bounds ticks."""
        mock_len.return_value = 5
        assert unease.beat_tick(10, "dusk") == 0

    @patch("unease.night_len")
    def test_beat_tick_returns_fraction_for_deep(self, mock_len):
        """Deep night tick is exactly half the night length when it fits."""
        mock_len.return_value = 20
        assert unease.beat_tick(10, "deep") == 10


class TestRunLength:
    def test_run_length_zero_for_kind_night(self):
        """Returns 0 if the night has a kind beat."""
        assert unease.run_length(5, {5}, {5}) == 0

    def test_run_length_one_for_isolated_odd_night(self):
        """Returns 1 for a single odd night with no neighbors."""
        assert unease.run_length(5, {5}, set()) == 1

    def test_run_length_counts_consecutive_odd_nights(self):
        """Counts consecutive odd nights correctly across boundaries."""
        odd = {3, 4, 5, 6}
        kind = set()
        assert unease.run_length(4, odd, kind) == 4
