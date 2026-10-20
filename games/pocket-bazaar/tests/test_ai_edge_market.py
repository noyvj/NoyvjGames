"""Edge-case tests for market.py public functions."""


import market


def test_valid_date_rejects_empty_and_zero_input():
    assert not market.valid_date("")
    assert not market.valid_date(None)
    assert not market.valid_date(0)
    assert not market.valid_date([])


def test_valid_date_accepts_boundary_dates():
    assert market.valid_date(market.EPOCH)
    assert market.valid_date(market.LAST_DATE)
    assert market.valid_date("2026-10-01")
    assert market.valid_date("2099-12-31")


def test_valid_date_rejects_invalid_formats():
    for bad in ("2026/10/01", "2026-10-1", "2026-10-01x", "20261001", "x", " 2026-10-01"):
        assert not market.valid_date(bad), bad


def test_day_number_returns_one_for_epoch():
    assert market.day_number(market.EPOCH) == 1


def test_day_number_handles_dates_before_and_after_epoch():
    prev = market.add_days(market.EPOCH, -1)
    assert market.day_number(prev) == 0
    nxt = market.add_days(market.EPOCH, 1)
    assert market.day_number(nxt) == 2


def test_playable_accepts_epoch_and_today_as_same():
    assert market.playable(market.EPOCH, market.EPOCH)
    assert market.playable(market.LAST_DATE, market.LAST_DATE)


def test_playable_rejects_out_of_range_dates():
    before = market.add_days(market.EPOCH, -1)
    after = market.add_days(market.LAST_DATE, 1)
    assert not market.playable(before, market.EPOCH)
    assert not market.playable(after, market.LAST_DATE)


def test_add_days_with_zero_returns_same_date():
    for d in (market.EPOCH, "2026-12-31", "2099-12-31"):
        assert market.add_days(d, 0) == d


def test_add_days_crosses_year_boundary():
    dec31 = "2026-12-31"
    jan1 = market.add_days(dec31, 1)
    assert jan1 == "2027-01-01"


def test_add_days_with_negative_value_moves_backwards():
    jan1 = "2027-01-01"
    dec31 = market.add_days(jan1, -1)
    assert dec31 == "2026-12-31"


def test_clean_days_returns_empty_for_junk_input():
    for junk in (None, [], "x", 123):
        assert market.clean_days(junk) == {}


def test_clean_days_drops_invalid_entries_keeps_valid():
    raw = {
        "2026-10-01": {"stars": 3, "served": 5, "total": 8, "coins": 100},
        "bad-date": {"stars": 1, "served": 1, "total": 1, "coins": 1},
        "2026-10-02": {"stars": True, "served": 5, "total": 8, "coins": 60},
    }
    result = market.clean_days(raw)
    assert len(result) == 1 and "2026-10-01" in result


def test_clean_days_respects_max_saved_limit():
    raw = {market.add_days(market.EPOCH, i): {"stars": 1, "served": 1, "total": 1, "coins": 1} for i in range(5000)}
    result = market.clean_days(raw)
    assert len(result) == market.MAX_DAYS_SAVED


def test_merge_record_prefers_higher_stars():
    old = {"stars": 2, "served": 5, "total": 8, "coins": 100}
    new = {"stars": 3, "served": 4, "total": 8, "coins": 50}
    assert market.merge_record(old, new) == new


def test_merge_record_prefers_higher_served_when_stars_equal():
    old = {"stars": 2, "served": 6, "total": 8, "coins": 100}
    new = {"stars": 2, "served": 7, "total": 8, "coins": 50}
    assert market.merge_record(old, new) == new


def test_merge_record_prefers_higher_coins_when_stars_and_served_equal():
    old = {"stars": 2, "served": 6, "total": 8, "coins": 90}
    new = {"stars": 2, "served": 6, "total": 8, "coins": 100}
    assert market.merge_record(old, new) == new


def test_merge_record_returns_old_when_new_is_worse():
    old = {"stars": 3, "served": 8, "total": 8, "coins": 200}
    new = {"stars": 2, "served": 5, "total": 8, "coins": 100}
    assert market.merge_record(old, new) == old
