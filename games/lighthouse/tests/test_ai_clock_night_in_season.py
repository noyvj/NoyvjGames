"""Test the night_in_season() function from clock.py."""

import clock


def test_night_in_season_returns_1_for_first_night_of_season():
    """Night 1, 11, 21, 31 should all be the first night of their season."""
    for night in [1, 11, 21, 31]:
        assert clock.night_in_season(night) == 1


def test_night_in_season_returns_5_for_middle_of_season():
    """Night 5, 15, 25, 35 should all be the fifth night of their season."""
    for night in [5, 15, 25, 35]:
        assert clock.night_in_season(night) == 5


def test_night_in_season_returns_10_for_last_night_of_season():
    """Night 10, 20, 30, 40 should all be the tenth night of their season."""
    for night in [10, 20, 30, 40]:
        assert clock.night_in_season(night) == 10
