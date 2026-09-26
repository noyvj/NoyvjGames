"""Warframe.market price lookup for the Warframe build tracker.

warframe.market's API sends no CORS headers, so a static page cannot call it
from the browser. This module lets the backend fetch it instead, for a small
fixed whitelist of item slugs (the tracker's tradeable resources), cache the
answer, and hand the browser just a lowest-sell price per item.

Rules: only whitelisted slugs are ever requested (nothing user-supplied reaches
the upstream URL); one upstream request per slug per MARKET_CACHE_SECONDS at
most, spaced out to stay under the API's rate limit; every failure returns
"no price" rather than an error; nothing about any trader is ever passed on.
"""

import json
import threading
import time
import urllib.request
from typing import Callable, Optional

MARKET_SLUGS = (
    "esher_devar", "goblite_tears", "heart_nyth", "marquise_thyst", "marquise_veridos",
    "radiant_zodian", "star_amarast", "star_crimzian", "tear_azurite",
)
MARKET_CACHE_SECONDS = 600
UPSTREAM = "https://api.warframe.market/v2/orders/item/{slug}"
REQUEST_SPACING_SECONDS = 0.4
REQUEST_TIMEOUT_SECONDS = 8

_cache: dict[str, tuple[float, Optional[dict]]] = {}
_lock = threading.Lock()


def lowest_sell(orders) -> Optional[dict]:
    """The cheapest visible sell order from someone in game or online, else the
    cheapest of any status. {"lowest_sell": platinum, "orders": count} or None
    if there are no usable sell orders."""
    if not isinstance(orders, list):
        return None
    sells = []
    for order in orders:
        if not isinstance(order, dict) or order.get("type") != "sell" or order.get("visible") is False:
            continue
        price = order.get("platinum")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
            continue
        user = order.get("user") if isinstance(order.get("user"), dict) else {}
        sells.append((price, user.get("status")))
    if not sells:
        return None
    live = [price for price, status in sells if status in ("ingame", "online")]
    return {"lowest_sell": min(live or [price for price, _ in sells]), "orders": len(sells)}


def _fetch_orders(slug: str):
    request = urllib.request.Request(
        UPSTREAM.format(slug=slug), headers={"Language": "en", "Accept": "application/json", "User-Agent": "NoyvjGames-tracker"}
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:  # noqa: S310 -- fixed https host, whitelisted slug
        return json.loads(response.read().decode("utf-8")).get("data")


def price_for(slug: str, fetch: Callable[[str], object] = _fetch_orders, now: Callable[[], float] = time.time) -> Optional[dict]:
    """One slug's cached price (None if unknown slug, or no price)."""
    if slug not in MARKET_SLUGS:
        return None
    with _lock:
        hit = _cache.get(slug)
        if hit and now() - hit[0] < MARKET_CACHE_SECONDS:
            return hit[1]
    try:
        result = lowest_sell(fetch(slug))
    except Exception:  # noqa: BLE001 -- any upstream failure means "no price", never an error
        result = None
    with _lock:
        _cache[slug] = (now(), result)
    return result


def all_prices(fetch: Callable[[str], object] = _fetch_orders, now: Callable[[], float] = time.time, sleep=time.sleep) -> dict:
    """{slug: {"lowest_sell", "orders"}} for every whitelisted slug that has a
    price. Slugs that need an upstream call are spaced REQUEST_SPACING_SECONDS
    apart; cached ones are free."""
    prices = {}
    for slug in MARKET_SLUGS:
        with _lock:
            fresh = slug in _cache and now() - _cache[slug][0] < MARKET_CACHE_SECONDS
        if not fresh:
            sleep(REQUEST_SPACING_SECONDS)
        price = price_for(slug, fetch, now)
        if price is not None:
            prices[slug] = price
    return prices


def cache_clear() -> None:
    with _lock:
        _cache.clear()
