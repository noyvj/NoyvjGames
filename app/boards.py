"""The general, game-agnostic opt-in board system (planning/TODO.md W-5 and Z-4).

Served by POST /scores and GET /leaderboard/{game}/{board} in main.py. It sits
beside the four legacy boards in leaderboards.py (SOL, Signal, Aftermath, Herd:
their rows live in `leaderboard_entries`, their PUT/GET /leaderboards routes and
public-username behaviour are unchanged) and is the path new boards should use.

Differences from the legacy boards:
  * Daily, weekly and all-time windows (UTC), chosen per board.
  * Anonymous by default: rows read "Player 7F2Q" (a per-game hash of the
    account id). One account setting (`show_username`) switches that account's
    rows to its username; it is off until the player turns it on.
  * Server-enforced opt-in: a submission must say `opt_in: true` and needs an
    account. Nothing is ever stored for a player who did not tick the box, and
    one DELETE removes everything.
  * Small-group suppression: a board window lists no rows until at least
    MIN_VISIBLE players are on it (a player still sees their own entry).
  * Per-board bounds, optional whole-number scores, throttled writes, and an
    admin hide for test rows.
  * Every clock read goes through current_time(), so tests inject a fake clock.

To add a game's board: one register_board(...) call below. The system adds two
NEW tables (`score_entries`, `score_profiles`) which create_all builds on start,
so no patch_schema() statement is needed.

Scores come from the client, so these are friendly boards, not anti-cheat ones:
the bounds only stop absurd values, and one row is kept per account per window
(their best).
"""

import hashlib
import hmac
import math
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Optional

from leaderboards import clean_detail, valid_score  # noqa: F401  (clean_detail re-exported for main.py)
from stats import MIN_BUCKET
from throttle import FailureLimiter

WINDOWS = ("daily", "weekly", "alltime")  # canonical order, also the display order
MIN_VISIBLE = MIN_BUCKET  # a window with fewer visible players than this lists no rows
TOP_N = 10
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")

BOARDS: dict[tuple[str, str], dict] = {}


def register_board(
    game_id: str,
    board: str,
    *,
    label: str,
    order: str,
    low: float,
    high: float,
    windows=WINDOWS,
    integer: bool = False,
    unit: str = "",
) -> dict:
    """Add (or replace) a board in the registry and return its config.

    order: "desc" higher is better, "asc" lower is better. low/high: the accepted
    score range (a client cannot post outside it). integer: reject fractional
    scores. windows: any of "daily", "weekly", "alltime" (the first listed, in
    canonical order, is the default view). Raises ValueError on a malformed
    definition, so a typo fails at import time rather than at a player's first
    submit.
    """
    if not (isinstance(game_id, str) and ID_RE.match(game_id)):
        raise ValueError(f"bad game id {game_id!r}")
    if not (isinstance(board, str) and ID_RE.match(board)):
        raise ValueError(f"bad board id {board!r}")
    if order not in ("asc", "desc"):
        raise ValueError("order must be 'asc' or 'desc'")
    if not (math.isfinite(low) and math.isfinite(high) and low < high):
        raise ValueError("low and high must be finite with low < high")
    windows = tuple(windows)
    if not windows or any(w not in WINDOWS for w in windows) or len(set(windows)) != len(windows):
        raise ValueError(f"windows must be a non-empty subset of {WINDOWS}")
    if not label or not isinstance(label, str):
        raise ValueError("label is required")
    config = {
        "label": label,
        "order": order,
        "low": float(low),
        "high": float(high),
        "windows": tuple(w for w in WINDOWS if w in windows),
        "integer": bool(integer),
        "unit": unit or "",
    }
    BOARDS[(game_id, board)] = config
    return config


def unregister_board(game_id: str, board: str) -> None:
    BOARDS.pop((game_id, board), None)


def board_config(game_id: str, board: str) -> Optional[dict]:
    return BOARDS.get((game_id, board))


def list_boards() -> list:
    return [
        {
            "game_id": g, "board": b, "label": c["label"], "order": c["order"],
            "windows": list(c["windows"]), "integer": c["integer"], "unit": c["unit"],
        }
        for (g, b), c in sorted(BOARDS.items())
    ]


# Boards reserved for games that are built or planned. The bounds are deliberately
# generous guesses: tighten each one when its game is wired up (Last Line is TODO
# T-2, Thaw's is GG-2, Canopy's is GB-19).
register_board("canopy", "community_investment", label="Daily community investment (growth)", order="desc",
               low=0.1, high=1_000_000.0, unit="growth")
register_board("last-line", "endless_best_wave", label="Endless: best wave reached", order="desc",
               low=1, high=10_000, windows=("weekly", "alltime"), integer=True, unit="waves")
register_board("thaw", "hold_the_line", label="Hold the Line: rounds survived", order="desc",
               low=1, high=1_000, windows=("weekly", "alltime"), integer=True, unit="rounds")
# K-10: Continuum's daily challenge (same fixed start for everyone that UTC day, so a daily window is a fair
# "you vs everyone"). Points = 10 x average sustainability + 5 x people + 20 x discoveries + 150 x eras entered.
register_board("continuum", "daily_challenge", label="Daily challenge: points", order="desc",
               low=0, high=1_000_000, windows=("daily",), integer=True, unit="points")


# --- the clock (injectable, so windows and throttles are testable) ---

_clock: Callable[[], float] = time.time


def current_time() -> float:
    return _clock()


def set_clock(fn: Optional[Callable[[], float]]) -> None:
    """Install a fake clock (tests), or restore the real one with None."""
    global _clock
    _clock = fn if fn is not None else time.time


def _utc(now: float) -> datetime:
    return datetime.fromtimestamp(now, tz=timezone.utc)


def window_period(window: str, now: float) -> str:
    """The period key a score made at `now` belongs to: the UTC date for daily,
    the ISO week ("2026-W41", weeks start on Monday) for weekly, "all" for all-time."""
    moment = _utc(now)
    if window == "daily":
        return moment.strftime("%Y-%m-%d")
    if window == "weekly":
        year, week, _ = moment.isocalendar()
        return f"{year}-W{week:02d}"
    if window == "alltime":
        return "all"
    raise ValueError(f"unknown window {window!r}")


_DAILY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_WEEKLY_RE = re.compile(r"^(\d{4})-W(\d{2})$")


def valid_period(window: str, period: str, now: float) -> bool:
    """True if `period` is a real period key of this window that is not in the future."""
    if window == "alltime":
        return period == "all"
    if window == "daily":
        if not _DAILY_RE.match(period):
            return False
        try:
            date.fromisoformat(period)
        except ValueError:
            return False
        return period <= window_period("daily", now)
    if window == "weekly":
        match = _WEEKLY_RE.match(period)
        if not match:
            return False
        try:
            date.fromisocalendar(int(match.group(1)), int(match.group(2)), 1)
        except ValueError:
            return False
        return period <= window_period("weekly", now)
    return False


def prune_cutoffs(now: float) -> dict:
    """Oldest period keys worth keeping: daily rows for 90 days, weekly for about a
    year. Older rows are deleted opportunistically on a submit; all-time is kept."""
    moment = _utc(now)
    year, week, _ = (moment - timedelta(days=370)).isocalendar()
    return {
        "daily": (moment - timedelta(days=90)).strftime("%Y-%m-%d"),
        "weekly": f"{year}-W{week:02d}",
    }


# --- scores ---

def valid_board_score(config: dict, score) -> Optional[float]:
    """The score as a float if it is a finite number inside the board's range (and
    a whole number on an `integer` board); None otherwise."""
    value = valid_score(config, score)
    if value is None:
        return None
    if config.get("integer") and not value.is_integer():
        return None
    return value


def is_better(config: dict, new: float, old: float) -> bool:
    return new < old if config["order"] == "asc" else new > old


# --- the privacy tier ---

_NAME_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # 32 symbols, none that look like 0/O/1/I/L


def _salt() -> bytes:
    return os.environ.get("LEADERBOARD_SALT", "noyvjgames-board-salt-v1").encode()


def anon_name(user_id: str, game_id: str, length: int = 4) -> str:
    """A stable anonymous handle like 'Player 7F2Q'. Hashed per game, so the same
    account reads as a different handle on every game (no linking across them), and
    the handle cannot be turned back into a username."""
    digest = hmac.new(_salt(), f"{game_id}:{user_id}".encode(), hashlib.sha256).digest()
    return "Player " + "".join(_NAME_ALPHABET[b % 32] for b in digest[:length])


def public_names(rows: list, game_id: str) -> list:
    """rows: [(user_id, username, show_username)]. Returns each row's display name.
    Two different anonymous players that would share a handle both get a longer one."""
    names = [username if show else anon_name(user_id, game_id) for user_id, username, show in rows]
    owners: dict[str, set] = {}
    for (user_id, _, _), name in zip(rows, names):
        owners.setdefault(name, set()).add(user_id)
    return [
        anon_name(user_id, game_id, 8) if (not show and len(owners[name]) > 1) else name
        for (user_id, _, show), name in zip(rows, names)
    ]


# --- write throttles (in-process sliding windows, see throttle.py) ---
# FailureLimiter is a per-key event counter; here the "failures" are simply
# accepted or rejected submissions. A flood from one account or address is
# refused with 429; a client probing the score bounds is cut off sooner.

SUBMIT_LIMIT_PER_HOUR = 60
SUBMIT_IP_LIMIT_PER_HOUR = 200
REJECT_LIMIT_PER_15_MIN = 10

SUBMIT_LIMITER = FailureLimiter(max_failures=SUBMIT_LIMIT_PER_HOUR, window_seconds=3600)
SUBMIT_IP_LIMITER = FailureLimiter(max_failures=SUBMIT_IP_LIMIT_PER_HOUR, window_seconds=3600)
REJECT_LIMITER = FailureLimiter(max_failures=REJECT_LIMIT_PER_15_MIN, window_seconds=15 * 60)


def reset_throttles() -> None:
    SUBMIT_LIMITER.reset()
    SUBMIT_IP_LIMITER.reset()
    REJECT_LIMITER.reset()
