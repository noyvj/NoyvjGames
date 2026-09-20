"""Cross-game aggregate stats (planning/TODO.md Z1) — pure helpers.

Everything here is pure (no DB, no FastAPI) so it is trivially testable;
main.py owns the routes and the single SELECT that feeds these functions.

Privacy rules (enforced here, not left to callers):
  * No bucket built from fewer than MIN_BUCKET saves is ever returned.
    That applies to the whole game (save count), to each achievement
    (a rarity figure needs >= MIN_BUCKET saves *of that game* overall, and
    an achievement earned by fewer than MIN_BUCKET saves is reported as
    suppressed rather than as "1 of 40"), and to each numeric field
    (needs >= MIN_BUCKET valid values).
  * Numeric fields never expose min/max (those ARE one player's value at
    small N) — only mean and interior percentiles.
  * Only whitelisted fields are read at all (STATS_FIELDS below), and
    only numbers are read from them. Nothing string-valued from a save
    (names, notes, save codes) can ever reach a response.
"""

import math
import re
import time
from typing import Any, Iterable, Optional

MIN_BUCKET = 3

# Newest saves win once a game has more than this many; bounds memory/time
# per request on Neon. Plenty at this site's scale.
MAX_SAVES_SCANNED = 5000

CACHE_TTL_SECONDS = 60

PERCENTILE_POINTS = (10, 25, 50, 75, 90)

ACHIEVEMENT_ID_RE = re.compile(r"^[a-z0-9_]{1,64}$")

# Per-game whitelist of numeric fields games have opted into. A key is a
# top-level field of that game's get_state() dict, or a dotted path into
# nested dicts (max STATS_MAX_PATH_DEPTH parts, e.g. "region.temperature").
# To opt a new field in, add it here — no other backend change. Seeded by
# reading each games/<slug>/game.py get_state(). Field values that are not
# finite real numbers (strings, null, bool, NaN/Infinity, lists) in a given
# save are silently skipped for that save.
STATS_MAX_PATH_DEPTH = 3
STATS_FIELDS: dict[str, tuple[str, ...]] = {
    "sol": (
        "prestige_level", "total_ticks", "total_manual_clicks",
        "lifetime_generators_built", "lifetime_recyclers_built",
        "lifetime_trade_routes_built", "lifetime_sky_cities_built",
        "governor_purchase_count", "research_progress",
    ),
    "canopy": (
        "total_income", "community_relations", "total_replants",
        "total_recoveries", "stakeholder_grants_count", "highland_income",
    ),
    "grid": (
        "round_number", "funds", "emissions", "best_clean_streak",
        "lifetime_revenue", "maintenance_actions_count",
    ),
    "tide": (
        "season", "funds", "acidity", "sea_level", "cumulative_damage",
        "max_funds_ever", "min_fish_yield_ever", "max_acidity_ever",
    ),
    "aftermath": (
        "run_number", "event_index", "resources", "resilience_capacity",
        "growth_capacity", "damage_taken",
    ),
    "herd": (
        "round_number", "funds", "herd_size", "methane",
        "plant_pivot_investment", "max_pressure_fraction_seen",
    ),
    "thaw": (
        "region.round_number", "region.funds", "region.temperature",
        "region.average_acceleration_factor",
    ),
    "loop": (
        "cycle_number", "funds", "total_extracted", "total_produced",
        "best_closed_loop_streak", "chains_completed_count",
        "lifetime_investment_spend", "lifetime_export_revenue",
        "lifetime_circular_fraction",
    ),
    "drift": (
        "round_number", "funds", "total_arrivals", "integrated_population",
        "best_stable_streak", "cumulative_services_investment",
        "cumulative_integration_contribution",
    ),
    "trade-empire": (
        "total_profit", "research_points", "total_sales_count",
        "max_profit_ever",
    ),
    "continuum": (
        "current_state.city.season", "current_state.city.population",
        "current_state.city.land_health", "current_state.city.pollution",
        "current_state.city.sprawl", "current_state.city.fed_fraction",
    ),
    "champ-de-mots": ("current_day",),
}


def known_games() -> list[str]:
    return sorted(STATS_FIELDS)


def _finite_number(value: Any) -> Optional[float]:
    # bool is an int subclass in Python; a flag is not a score.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        f = float(value)
    except (OverflowError, ValueError):
        return None
    return f if math.isfinite(f) else None


def extract_number(save_data: Any, path: str) -> Optional[float]:
    """Follow a dotted path through nested dicts; None if any hop is
    missing/not a dict or the leaf isn't a finite real number."""
    node = save_data
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return _finite_number(node)


def extract_achievements(save_data: Any) -> set[str]:
    """The set of well-formed achievement ids a save claims. Tolerates a
    missing key, a non-list, non-string entries, and junk ids."""
    if not isinstance(save_data, dict):
        return set()
    raw = save_data.get("achievements_earned")
    if not isinstance(raw, list):
        return set()
    return {a for a in raw if isinstance(a, str) and ACHIEVEMENT_ID_RE.match(a)}


def percentile_of(sorted_values: list[float], value: float) -> float:
    """Mid-rank percentile (0-100) of `value` within a sorted list: the
    share strictly below plus half the share tied. A value below everything
    is ~0, above everything ~100, and a value equal to all of them is 50.
    Requires a non-empty list."""
    if not sorted_values:
        raise ValueError("percentile_of needs at least one value")
    from bisect import bisect_left, bisect_right

    below = bisect_left(sorted_values, value)
    upto = bisect_right(sorted_values, value)
    return round(100.0 * (below + (upto - below) / 2.0) / len(sorted_values), 2)


def _quantile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolated quantile, q in [0, 100]."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (q / 100.0) * (len(sorted_values) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def field_values(saves: Iterable[Any], path: str) -> list[float]:
    return sorted(v for v in (extract_number(s, path) for s in saves) if v is not None)


def summarize_field(sorted_values: list[float]) -> Optional[dict]:
    """None (suppressed) below MIN_BUCKET values. Never includes min/max."""
    if len(sorted_values) < MIN_BUCKET:
        return None
    return {
        "count": len(sorted_values),
        "mean": round(sum(sorted_values) / len(sorted_values), 4),
        "percentiles": {
            f"p{p}": round(_quantile(sorted_values, p), 4) for p in PERCENTILE_POINTS
        },
    }


def summarize_game(game_id: str, saves: list[Any]) -> dict:
    """Full per-game aggregate from a list of decoded save_data values.
    Below MIN_BUCKET saves, only {"save_count": null-ish suppressed flag}
    is returned — nothing derived."""
    n = len(saves)
    if n < MIN_BUCKET:
        return {
            "game_id": game_id,
            "suppressed": True,
            "min_bucket": MIN_BUCKET,
            "save_count": None,
            "achievements": {},
            "fields": {},
        }

    tally: dict[str, int] = {}
    for s in saves:
        for a in extract_achievements(s):
            tally[a] = tally.get(a, 0) + 1
    achievements = {}
    suppressed_achievements = 0
    for aid, count in sorted(tally.items()):
        if count < MIN_BUCKET:
            suppressed_achievements += 1
            continue
        achievements[aid] = {"earned_pct": round(100.0 * count / n, 2), "earned_count": count}

    fields = {}
    for path in STATS_FIELDS.get(game_id, ()):
        summary = summarize_field(field_values(saves, path))
        if summary is not None:
            fields[path] = summary

    return {
        "game_id": game_id,
        "suppressed": False,
        "min_bucket": MIN_BUCKET,
        "save_count": n,
        "achievements": achievements,
        "achievements_suppressed_count": suppressed_achievements,
        "fields": fields,
    }


# --- tiny in-process TTL cache (per game). Same "in-process only, resets on
# restart" stance as main.py's feedback rate limiter; reads are cheap enough
# that a per-instance cache is all this needs.
_cache: dict[str, tuple[float, list]] = {}


def cache_get(key: str) -> Optional[list]:
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]
    return None


def cache_put(key: str, value: list) -> None:
    _cache[key] = (time.time(), value)


def cache_clear() -> None:
    _cache.clear()
