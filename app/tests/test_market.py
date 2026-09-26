"""Warframe.market price proxy for the Warframe tracker."""

import market
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _order(price, status="ingame", kind="sell", visible=True):
    return {"type": kind, "platinum": price, "visible": visible, "user": {"status": status, "ingameName": "someone"}}


def setup_function():
    market.cache_clear()


def test_lowest_sell_prefers_live_sellers():
    orders = [_order(3, "offline"), _order(8, "online"), _order(6, "ingame"), _order(2, "offline")]
    assert market.lowest_sell(orders) == {"lowest_sell": 6, "orders": 4}


def test_lowest_sell_falls_back_to_any_status_and_ignores_junk():
    orders = [_order(4, "offline"), _order(9, "offline"), _order(1, "ingame", kind="buy"), _order(1, "ingame", visible=False),
              _order(0), _order(True), _order("5"), "junk", None]
    assert market.lowest_sell(orders) == {"lowest_sell": 4, "orders": 2}
    assert market.lowest_sell([]) is None
    assert market.lowest_sell("nope") is None
    assert market.lowest_sell([_order(5, kind="buy")]) is None


def test_only_whitelisted_slugs_are_ever_fetched():
    calls = []
    assert market.price_for("../../evil", fetch=lambda s: calls.append(s)) is None
    assert market.price_for("ferrite", fetch=lambda s: calls.append(s)) is None
    assert calls == []


def test_price_is_cached_and_expires():
    clock = [1000.0]
    calls = []

    def fetch(slug):
        calls.append(slug)
        return [_order(7)]

    now = lambda: clock[0]  # noqa: E731
    assert market.price_for("tear_azurite", fetch, now) == {"lowest_sell": 7, "orders": 1}
    assert market.price_for("tear_azurite", fetch, now) == {"lowest_sell": 7, "orders": 1}
    assert calls == ["tear_azurite"]
    clock[0] += market.MARKET_CACHE_SECONDS + 1
    market.price_for("tear_azurite", fetch, now)
    assert calls == ["tear_azurite", "tear_azurite"]


def test_upstream_failure_means_no_price_not_an_error():
    def boom(slug):
        raise OSError("down")

    assert market.price_for("heart_nyth", boom) is None
    prices = market.all_prices(fetch=boom, sleep=lambda s: None)
    assert prices == {}


def test_all_prices_spaces_uncached_calls_only():
    slept = []
    prices = market.all_prices(fetch=lambda s: [_order(2)], sleep=slept.append)
    assert set(prices) == set(market.MARKET_SLUGS)
    assert len(slept) == len(market.MARKET_SLUGS)
    slept.clear()
    market.all_prices(fetch=lambda s: [_order(2)], sleep=slept.append)
    assert slept == []


def test_endpoint_returns_only_prices_and_is_cacheable(monkeypatch):
    monkeypatch.setattr(market, "all_prices", lambda: {"tear_azurite": {"lowest_sell": 5, "orders": 3}})
    resp = client.get("/market/prices")
    assert resp.status_code == 200
    assert resp.json() == {"prices": {"tear_azurite": {"lowest_sell": 5, "orders": 3}}}
    assert "max-age" in resp.headers["cache-control"]
