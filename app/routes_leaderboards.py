"""Opt-in leaderboards, original per-game form: /leaderboards/{game_id}/{board}."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

import leaderboards
from auth import _test_user_ids, get_current_user, get_current_user_optional
from database import get_db
from models import LeaderboardEntry, User


router = APIRouter()


# --- Opt-in community leaderboards (see leaderboards.py for the rules) ---


class LeaderboardSubmit(BaseModel):
    score: float
    detail: Optional[str] = None


def _board_or_404(game_id: str, board: str) -> dict:
    config = leaderboards.board_config(game_id, board)
    if config is None:
        raise HTTPException(status_code=404, detail="Unknown leaderboard")
    return config


def _board_order(config: dict):
    return LeaderboardEntry.score.asc() if config["order"] == "asc" else LeaderboardEntry.score.desc()


def _rank_of(db: Session, config: dict, game_id: str, board: str, score: float) -> int:
    """1 + the number of visible entries strictly better than `score`."""
    query = (
        db.query(func.count(LeaderboardEntry.id))
        .filter(LeaderboardEntry.game_id == game_id, LeaderboardEntry.board == board)
        .filter(~LeaderboardEntry.user_id.in_(_test_user_ids(db)))
    )
    query = query.filter(LeaderboardEntry.score < score) if config["order"] == "asc" else query.filter(LeaderboardEntry.score > score)
    return int(query.scalar() or 0) + 1


@router.get("/leaderboards/{game_id}/{board}")
def get_leaderboard(
    game_id: str,
    board: str,
    response: Response,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    config = _board_or_404(game_id, board)
    response.headers["Cache-Control"] = "no-store"
    rows = (
        db.query(LeaderboardEntry, User.username)
        .join(User, User.id == LeaderboardEntry.user_id)
        .filter(LeaderboardEntry.game_id == game_id, LeaderboardEntry.board == board)
        .filter(User.is_test.is_(False))
        .order_by(_board_order(config), LeaderboardEntry.updated_at.asc())
        .limit(leaderboards.TOP_N)
        .all()
    )
    entries = [
        {"rank": i + 1, "username": username, "score": entry.score, "detail": entry.detail or ""}
        for i, (entry, username) in enumerate(rows)
    ]
    mine = None
    if current_user is not None:
        own = (
            db.query(LeaderboardEntry)
            .filter(
                LeaderboardEntry.game_id == game_id,
                LeaderboardEntry.board == board,
                LeaderboardEntry.user_id == current_user.id,
            )
            .first()
        )
        if own is not None:
            mine = {
                "score": own.score,
                "detail": own.detail or "",
                "rank": _rank_of(db, config, game_id, board, own.score),
            }
    return {"game_id": game_id, "board": board, "label": config["label"], "order": config["order"], "entries": entries, "mine": mine}


@router.put("/leaderboards/{game_id}/{board}")
def submit_leaderboard_score(
    game_id: str,
    board: str,
    payload: LeaderboardSubmit,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Opts the signed-in player in (or updates them): a row is kept only if
    the new score beats their stored best, so re-submitting is harmless."""
    config = _board_or_404(game_id, board)
    response.headers["Cache-Control"] = "no-store"
    score = leaderboards.valid_score(config, payload.score)
    if score is None:
        raise HTTPException(status_code=422, detail="score is outside this leaderboard's accepted range")
    detail = leaderboards.clean_detail(payload.detail)
    if current_user.is_test:
        return {"accepted": False, "reason": "test account"}
    entry = (
        db.query(LeaderboardEntry)
        .filter(
            LeaderboardEntry.game_id == game_id,
            LeaderboardEntry.board == board,
            LeaderboardEntry.user_id == current_user.id,
        )
        .first()
    )
    improved = True
    if entry is None:
        entry = LeaderboardEntry(game_id=game_id, board=board, user_id=current_user.id, score=score, detail=detail)
        db.add(entry)
    elif leaderboards.is_better(config, score, entry.score):
        entry.score = score
        entry.detail = detail
    else:
        improved = False
    db.commit()
    return {
        "accepted": True,
        "improved": improved,
        "score": entry.score,
        "rank": _rank_of(db, config, game_id, board, entry.score),
    }


@router.delete("/leaderboards/{game_id}/{board}")
def remove_leaderboard_entry(
    game_id: str,
    board: str,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Opt out: removes this account's row from the board."""
    _board_or_404(game_id, board)
    response.headers["Cache-Control"] = "no-store"
    removed = (
        db.query(LeaderboardEntry)
        .filter(
            LeaderboardEntry.game_id == game_id,
            LeaderboardEntry.board == board,
            LeaderboardEntry.user_id == current_user.id,
        )
        .delete()
    )
    db.commit()
    return {"removed": bool(removed)}
