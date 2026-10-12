"""Tests for the assign() function in cast.py."""

import cast
import lore
import ships


def test_normal_assignment_labels_a_ship_with_a_sailor():
    """A normal case where a ship gets labeled with a sailor."""
    seed = 1
    night = 5
    ships_list = ships.ships_for_night(seed, night, ships.mail_scheduled(seed, night))
    original_ids = [s["id"] for s in ships_list]
    cast.assign(seed, night, ships_list)
    new_ids = [s["id"] for s in ships_list]
    assert original_ids == new_ids  # No ships added or removed
    assert any(s.get("who") for s in ships_list)  # At least one ship labeled


def test_mail_ship_keeps_its_name_when_assigned():
    """A mail ship should keep its name when assigned to a sailor who owns a boat."""
    seed = 2
    night = 10
    ships_list = ships.ships_for_night(seed, night, ships.mail_scheduled(seed, night))
    cast.assign(seed, night, ships_list)
    for ship in ships_list:
        if ship.get("who") and ship["kind"] == "mail":
            sailor = lore.SAILORS[ship["who"]]
            if sailor["ship"]:
                assert ship["name"] == sailor["ship"]


def test_edge_case_no_ships_of_correct_kind():
    """Edge case where no ships match the sailor's kind."""
    seed = 3
    night = 1
    ships_list = ships.ships_for_night(seed, night, ships.mail_scheduled(seed, night))
    original_who = [s.get("who") for s in ships_list]
    cast.assign(seed, night, ships_list)
    new_who = [s.get("who") for s in ships_list]
    assert original_who == new_who  # No assignments should happen
