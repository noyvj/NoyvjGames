"""Tests for view.notice_for: the notice board listing ships and extras for a given night."""

import ships
import sim
from state import Keep
from view import notice_for


def keep_at(night=1, seed=3):
    k = Keep(seed)
    k.night = night
    sim.to_evening(k)
    return k


def test_notice_for_returns_correct_number_of_entries():
    """Normal case: the number of entries matches ships_for_night exactly."""
    for night in (1, 10, 25):
        k = keep_at(night, seed=7)
        result = notice_for(k, night, True)
        expected_count = len(ships.ships_for_night(k.seed, night, True))
        assert len(result) == expected_count


def test_notice_for_entries_have_required_keys_and_types():
    """Normal case: every entry contains the expected keys and correct types."""
    for night in (1, 20):
        k = keep_at(night, seed=99)
        result = notice_for(k, night, True)
        assert len(result) > 0
        for entry in result:
            assert isinstance(entry["kind"], str)
            assert isinstance(entry["label"], str)
            assert isinstance(entry["icon"], str)
            assert isinstance(entry["name"], str)
            assert isinstance(entry["block"], int)
            assert isinstance(entry["block_label"], str)
            assert isinstance(entry["at"], str)
            assert isinstance(entry["need"], int)
            assert entry["who_name"] is None or isinstance(entry["who_name"], str)


def test_notice_for_mail_flag_affects_ships():
    """Normal case: setting mail=False removes the supply boat from the notice."""
    k = keep_at(5, seed=123)
    with_mail = notice_for(k, 5, True)
    without_mail = notice_for(k, 5, False)
    assert len(with_mail) == len(without_mail) + 1


def test_notice_for_who_name_is_none_when_story_off():
    """Edge case: who_name is None when story is disabled."""
    k = keep_at(5, seed=42)
    k.quiet = True
    result = notice_for(k, 5, True)
    for entry in result:
        assert entry["who_name"] is None
