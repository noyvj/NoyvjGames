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


def test_year_action():
    import json
    from game import handle, get_state

    _prog("presidents-sample")["learned"].update({"e-washington-oath", "c-bastille"})
    try:
        res = json.loads(handle(json.dumps({"action": "year", "year": 1789})))
        assert res["ok"] is True
        assert res["year"]["label"] == "1789"
        assert [e["id"] for e in res["year"]["entries"]] == ["e-washington-oath", "c-bastille"]

        res2 = json.loads(handle(json.dumps({"action": "year", "year": -431})))
        assert res2["ok"] is True
        assert res2["year"]["label"] == "431 BCE"
        assert res2["year"]["entries"] == []

        for bad_year in [0, 5000]:
            res_bad = json.loads(handle(json.dumps({"action": "year", "year": bad_year})))
            assert res_bad["ok"] is False

        res_str = json.loads(handle(json.dumps({"action": "year", "year": "1789"})))
        assert res_str["ok"] is False

        state_before = get_state()
        handle(json.dumps({"action": "year", "year": 1789}))
        state_after = get_state()
        assert state_before == state_after
    finally:
        _prog("presidents-sample")["learned"].difference_update({"e-washington-oath", "c-bastille"})
