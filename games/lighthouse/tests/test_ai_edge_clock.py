"""Edge-case tests for clock.py."""

import clock
import data


def test_year_night_wraps_at_year_boundary():
    # year_night should be 1..40 regardless of how many years have passed
    assert clock.year_night(1) == 1
    assert clock.year_night(40) == 40
    assert clock.year_night(41) == 1
    assert clock.year_night(80) == 40
    assert clock.year_night(120) == 40
    assert clock.year_night(121) == 1


def test_season_of_and_name_cycle_correctly():
    # Seasons cycle every 10 nights within a year
    for night in range(1, 41):
        s_idx = clock.season_of(night)
        assert 0 <= s_idx <= 3
        name = clock.season_name(night)
        assert name == data.SEASONS[s_idx]


def test_night_len_respects_season_data():
    # Winter nights are longest, summer shortest per data.NIGHT_LEN
    assert clock.night_len(1) == data.NIGHT_LEN[0]  # Spring
    assert clock.night_len(11) == data.NIGHT_LEN[1]  # Summer
    assert clock.night_len(21) == data.NIGHT_LEN[2]  # Autumn
    assert clock.night_len(31) == data.NIGHT_LEN[3]  # Winter


def test_block_of_and_end_cover_full_night():
    # block_of returns 0, 1, or 2
    for night in (1, 31):
        length = clock.night_len(night)
        for tick in range(length + 1):
            b = clock.block_of(night, tick)
            assert b in (0, 1, 2)
            end = clock.block_end(night, b)
            if tick < length:
                assert tick < end
        # Check that the last block ends exactly at night length
        assert clock.block_end(night, 2) == length


def test_clock_minutes_wraps_at_1440():
    # clock_minutes should always be 0..1439
    for night in (1, 11, 21, 31):
        start = data.NIGHT_START_MIN[clock.season_of(night)]
        length = clock.night_len(night)
        for tick in range(length + 1):
            minutes = clock.clock_minutes(night, tick)
            assert 0 <= minutes < 1440
            # Verify it matches the formula modulo 1440
            expected = (start + tick * data.TICK_MINUTES) % 1440
            assert minutes == expected


def test_clock_label_formats_correctly():
    for night in (1, 31):
        clock.night_len(night)
        label = clock.clock_label(night, 0)
        assert len(label) == 5 and ":" in label
        parts = label.split(":")
        assert len(parts[0]) == 2 and len(parts[1]) == 2


def test_darkness_bounds_and_clamp():
    # darkness should be between 0.0 and 1.0, and clamp at the edges
    for night in (1, 31):
        length = clock.night_len(night)
        for tick in range(length + 1):
            d = clock.darkness(night, tick)
            assert 0.0 <= d <= 1.0
        # At the very end of the night, darkness should clamp to 0.0
        assert clock.darkness(night, length) == 0.0
        # At dusk (tick=0), it should be > 0 but < 1
        assert 0.0 < clock.darkness(night, 0) < 1.0
