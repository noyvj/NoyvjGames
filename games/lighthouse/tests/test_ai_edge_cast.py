"""Edge-case tests for cast.py."""

import cast
import ships


def test_assign_with_empty_ships_list():
    """Passing an empty list of ships should return an empty list unchanged."""
    seed = 1
    night = 5
    result = cast.assign(seed, night, [])
    assert result == []


def test_assign_with_negative_seed():
    """A negative seed should be handled gracefully without crashing."""
    seed = -1
    night = 5
    ships_list = ships.ships_for_night(seed, night, ships.mail_scheduled(seed, night))
    cast.assign(seed, night, ships_list)
    assert len(ships_list) > 0


def test_assign_with_very_large_seed():
    """A very large seed value should not cause overflow or errors."""
    seed = 2**31 - 1
    night = 5
    ships_list = ships.ships_for_night(seed, night, ships.mail_scheduled(seed, night))
    cast.assign(seed, night, ships_list)
    assert len(ships_list) > 0


def test_assign_all_ships_already_labeled():
    """If all ships already have a 'who' key, assign should leave them unchanged."""
    seed = 1
    night = 5
    ships_list = ships.ships_for_night(seed, night, ships.mail_scheduled(seed, night))
    for ship in ships_list:
        ship["who"] = "existing"
    original_who = [s.get("who") for s in ships_list]
    cast.assign(seed, night, ships_list)
    new_who = [s.get("who") for s in ships_list]
    assert original_who == new_who


def test_assign_respects_max_per_night_limit():
    """At most MAX_PER_NIGHT (2) non-mail ships should be assigned per night."""
    seed = 100
    night = 50
    ships_list = ships.ships_for_night(seed, night, ships.mail_scheduled(seed, night))
    cast.assign(seed, night, ships_list)
    non_mail_assigned = sum(1 for s in ships_list if s.get("who") and s["kind"] != "mail")
    assert non_mail_assigned <= cast.MAX_PER_NIGHT
