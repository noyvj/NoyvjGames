"""Personal-best records (kept in localStorage, never in the save) and the small helpers that read saved numbers safely."""

import copy
import math


# ---------------------------------------------------------------------------
# Lifetime records (survive a charter renewal, like captains_met and the ledger).
# One small validated dict instead of a handful of loose globals; saved under
# "records" only once something in it is non-default.
# ---------------------------------------------------------------------------
RECORDS_COUNT_MAX = 1_000_000


def _fresh_records():
    return {
        "dark_runs": 0, "weather_events": 0, "expeditions": 0, "expedition_nothing_streak": 0,
        "expedition_since_curio": 0, "curios": [], "exchange_fills": 0, "hubs_set": 0,
        "meridian_contests": 0, "meridian_answers": 0, "cartel_moves": 0, "crisis_best": {}, "chain_best": {},
    }


records = _fresh_records()


def _records_for_save():
    """The records worth saving, or an empty dict when nothing was ever recorded."""
    fresh = _fresh_records()
    return {key: copy.deepcopy(value) for key, value in records.items() if value != fresh[key]}


def _saved_int(value, low, high, default=0):
    """A save's whole number, or `default` if it isn't a real int (never bool) in range."""
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


def _saved_float(value, low, high, default):
    """A save's number, or `default` if it isn't a real, finite, in-range one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if not math.isfinite(value) or not low <= value <= high:
        return default
    return float(value)
