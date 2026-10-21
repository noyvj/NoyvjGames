"""The "same year" lookup: only moments the player has already found are listed, so no puzzle answer leaks.

Every test uses the g / p fixtures (tests/conftest.py), which reset the engine to a brand-new player, so no test
depends on what an earlier one learned.
"""
from actions import year_moments

LEARNED = {"e-washington-oath", "c-bastille"}


def learn(g, ids=LEARNED):
    g._prog("presidents-sample")["learned"].update(ids)


def test_year_moments_1789(g):
    learn(g)
    assert [x["id"] for x in year_moments(1789)] == ["e-washington-oath", "c-bastille"]


def test_year_moments_1803_empty_because_not_learned(g):
    learn(g)
    assert year_moments(1803) == []


def test_year_moments_negative(g):
    learn(g)
    assert year_moments(-431) == []


def test_year_moments_date_label(g):
    learn(g, {"e-washington-oath"})
    entry = year_moments(1789)[0]
    assert entry["id"] == "e-washington-oath"
    assert entry["date_label"] == "30 April 1789"
    assert entry["set"] == "presidents-sample"
    assert entry["kind"] == "event"


def test_nothing_is_listed_for_a_new_player(g):
    """No leak: an unfound moment never appears, even for the exact year of its date."""
    assert year_moments(1789) == []
    assert year_moments(1863) == []


def test_a_moment_with_an_end_year_is_listed_for_every_year_in_its_range(g):
    learn(g, {"e-washington-oath"})
    g.SETS["presidents-sample"].events["e-washington-oath"]["end"] = "1792"
    assert [x["id"] for x in year_moments(1791)] == ["e-washington-oath"]
    assert year_moments(1793) == []


def test_year_action_label_and_entries(g, p):
    learn(g)
    r = p.call("year", year=1789)
    assert r["ok"] is True
    assert r["year"]["label"] == "1789"
    assert [e["id"] for e in r["year"]["entries"]] == ["e-washington-oath", "c-bastille"]


def test_year_action_bce_label(g, p):
    learn(g)
    r = p.call("year", year=-431)
    assert r["ok"] is True
    assert r["year"]["label"] == "431 BCE"
    assert r["year"]["entries"] == []


def test_year_action_refuses_zero_out_of_range_and_non_integers(g, p):
    for bad in (0, 5000, -3001, "1789", 1789.0, True, None):
        assert p.call("year", year=bad)["ok"] is False, bad
    assert p.call("year")["ok"] is False


def test_year_action_is_read_only(g, p):
    learn(g)
    before = g.get_state()
    p.call("year", year=1789)
    p.call("year", year=-431)
    assert g.get_state() == before
    assert "year" in g.READ_ONLY


def test_year_action_is_documented_in_the_engine_docstring(g):
    assert "year {year}" in g.__doc__
