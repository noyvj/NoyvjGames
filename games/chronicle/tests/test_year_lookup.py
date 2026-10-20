from actions import year_moments
from core import _prog


def test_year_moments_1789():
    _prog("presidents-sample")["learned"].update({"e-washington-oath", "c-bastille"})
    try:
        result = [x["id"] for x in year_moments(1789)]
        assert result == ["e-washington-oath", "c-bastille"]
    finally:
        _prog("presidents-sample")["learned"].difference_update({"e-washington-oath", "c-bastille"})


def test_year_moments_1803_empty():
    result = year_moments(1803)
    assert result == []


def test_year_moments_negative():
    result = year_moments(-431)
    assert result == []


def test_year_moments_date_label():
    _prog("presidents-sample")["learned"].update({"e-washington-oath"})
    try:
        result = year_moments(1789)
        washington_entry = next(x for x in result if x["id"] == "e-washington-oath")
        assert washington_entry["date_label"] == "30 April 1789"
    finally:
        _prog("presidents-sample")["learned"].difference_update({"e-washington-oath"})
