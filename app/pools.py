"""Shared community pools (TODO.md H11; also the base for the daily community plot).

A pool is an anonymous running total the players of one game add to, kept per
UTC day so a "today" figure and a "best day ever" exist. Privacy and safety:
  * No account is needed and nothing personal is stored: a row is only
    (game, pool, day, total, contribution count).
  * Every request is capped (POOLS[...]["max_per_request"]) and rate limited per
    client address in-process, so one browser cannot inflate a total.
  * Totals are client-reported like the leaderboards, so a pool is a friendly
    shared counter, not an anti-cheat number.

To add a pool, add one entry to POOLS: no schema change.
"""

import math
import threading
import time
from datetime import datetime, timezone
from typing import Optional

POOLS: dict[tuple[str, str], dict] = {
    # Loop: surplus recovered material donated to the regional recycling network.
    ("loop", "recovered_units"): {"max_per_request": 500.0, "label": "Regional recycling pool (units)"},
    # Canopy: the daily community plot everyone waters together (GB19).
    ("canopy", "community_plot"): {"max_per_request": 60.0, "label": "Community plot (growth)"},
}

RATE_LIMIT_PER_HOUR = 120
RECENT_DAYS = 7

_request_log: dict[str, list[float]] = {}
_lock = threading.Lock()


def pool_config(game_id: str, pool: str) -> Optional[dict]:
    return POOLS.get((game_id, pool))


def today_utc(now: Optional[float] = None) -> str:
    return datetime.fromtimestamp(now if now is not None else time.time(), tz=timezone.utc).strftime("%Y-%m-%d")


def valid_amount(config: dict, amount) -> Optional[float]:
    """The amount as a float if it is a finite number in (0, max_per_request]."""
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        return None
    if not math.isfinite(amount) or amount <= 0 or amount > config["max_per_request"]:
        return None
    return float(amount)


def rate_limited(client: str, now: Optional[float] = None) -> bool:
    """True (and does not record) once this client has made RATE_LIMIT_PER_HOUR
    accepted contributions in the last hour."""
    now = time.time() if now is None else now
    with _lock:
        recent = [t for t in _request_log.get(client, []) if now - t < 3600]
        if len(recent) >= RATE_LIMIT_PER_HOUR:
            _request_log[client] = recent
            return True
        recent.append(now)
        _request_log[client] = recent
        return False


def reset_rate_limits() -> None:
    with _lock:
        _request_log.clear()
