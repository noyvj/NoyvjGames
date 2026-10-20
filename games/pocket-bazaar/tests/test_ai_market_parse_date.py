"""Tests for market.parse_date()."""


import market


def test_parse_date_returns_tuple_for_a_valid_date():
    assert market.parse_date("2026-10-11") == (2026, 10, 11)


def test_parse_date_handles_leap_year_feb_twenty_ninth():
    assert market.parse_date("2028-02-29") == (2028, 2, 29)
    assert market.parse_date("2027-02-29") is None


def test_parse_date_returns_none_for_invalid_inputs():
    assert market.parse_date("not a date") is None
    assert market.parse_date("") is None
    assert market.parse_date(5) is None
