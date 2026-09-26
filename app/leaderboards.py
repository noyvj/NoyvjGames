"""Opt-in community leaderboards (TODO.md A29, E23, F21).

Privacy and trust rules, kept deliberately simple:
  * Nothing is ever published unless a signed-in player opts in by submitting
    a score; removing the entry is one DELETE.
  * The only thing shown is the player's existing public username, the score,
    and a short detail string. Never an email, save code or raw save.
  * Test accounts (users.is_test) are excluded from every board.
  * Scores are supplied by the client, so this is a friendly leaderboard, not
    a tamper-proof one: values are only range-checked, and a board keeps one
    row per account (their best).

To add a board, add one entry to BOARDS: no schema change needed.
"""

import math
from typing import Optional

# order: "asc" = lower is better (fastest time), "desc" = higher is better.
# low/high: the accepted score range; anything outside is rejected.
BOARDS: dict[tuple[str, str], dict] = {
    # SOL: total ticks played when the whole system is first terraformed.
    ("sol", "fastest_completion"): {
        "order": "asc", "low": 1.0, "high": 100_000_000.0, "label": "Fastest full completion (ticks)",
    },
    # Aftermath: the average event severity of a run that ended with resources left.
    ("aftermath", "hardest_schedule"): {
        "order": "desc", "low": 0.1, "high": 10.0, "label": "Hardest schedule survived (average severity)",
    },
    # Herd: score minus the pure-growth counterfactual's score.
    ("herd", "decoupling_gap"): {
        "order": "desc", "low": 0.0, "high": 1_000_000_000.0, "label": "Best decoupling gap",
    },
}

TOP_N = 10
DETAIL_MAX_LENGTH = 60


def board_config(game_id: str, board: str) -> Optional[dict]:
    return BOARDS.get((game_id, board))


def valid_score(config: dict, score) -> Optional[float]:
    """The score as a float if it is a finite number inside the board's range."""
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return None
    if not math.isfinite(score):
        return None
    if score < config["low"] or score > config["high"]:
        return None
    return float(score)


def clean_detail(detail) -> str:
    """A short, single-line, printable detail string (never raises)."""
    if not isinstance(detail, str):
        return ""
    text = "".join(ch for ch in detail if ch.isprintable()).strip()
    return text[:DETAIL_MAX_LENGTH]


def is_better(config: dict, new: float, old: float) -> bool:
    return new < old if config["order"] == "asc" else new > old
