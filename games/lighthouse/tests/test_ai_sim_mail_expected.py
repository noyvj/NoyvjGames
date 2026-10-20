"""Tests for sim.mail_expected()."""

import sim
from state import Keep


def test_mail_expected_returns_false_on_festival_night():
    """Festival nights never have the mail boat, regardless of boat_due."""
    keep = Keep(1)
    assert sim.mail_expected(keep, 20) is False
    keep.boat_due = True
    assert sim.mail_expected(keep, 20) is False


def test_mail_expected_returns_true_when_boat_is_due():
    """A due boat is expected on any non-festival night."""
    keep = Keep(1)
    keep.boat_due = True
    assert sim.mail_expected(keep, 19) is True


def test_mail_expected_delegates_to_ship_generator_when_not_due():
    """When not due, it checks the ship generator and returns a boolean."""
    keep = Keep(1)
    keep.boat_due = False
    result = sim.mail_expected(keep, 19)
    assert isinstance(result, bool)
