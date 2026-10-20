"""Edge-case tests for ships.py."""

import ships
from data import FIRST_MAIL_NIGHT


def test_mail_nights_before_returns_empty_for_pre_mail_night():
    """mail_nights_before should return an empty list when night is before the first mail night."""
    seed = 1
    result = ships.mail_nights_before(seed, FIRST_MAIL_NIGHT - 1)
    assert result == []


def test_mail_scheduled_false_before_first_mail():
    """mail_scheduled should be False for any night strictly before the first scheduled mail night."""
    seed = 42
    assert ships.mail_scheduled(seed, FIRST_MAIL_NIGHT - 1) is False


def test_next_mail_night_starts_at_first_mail_for_zero_input():
    """next_mail_night with night=0 should return the first mail night."""
    seed = 1
    result = ships.next_mail_night(seed, 0)
    assert result == FIRST_MAIL_NIGHT


def test_ships_for_night_includes_mail_when_flagged():
    """When mail=True, ships_for_night must include a ship with kind 'mail'."""
    seed = 1
    night = 5
    default_ships = ships.ships_for_night(seed, night)
    assert not any(s["kind"] == "mail" for s in default_ships)

    mail_ships = ships.ships_for_night(seed, night, mail=True)
    assert any(s["kind"] == "mail" for s in mail_ships)


def test_block_of_arrival_handles_zero_and_max_clamping():
    """block_of_arrival should return 0 for zero arrival and clamp to 2 for large arrival."""
    ship_zero = {"arrive": 0}
    assert ships.block_of_arrival(10, ship_zero) == 0

    ship_large = {"arrive": 99}
    assert ships.block_of_arrival(10, ship_large) == 2
