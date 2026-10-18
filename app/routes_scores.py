"""Opt-in score boards (the rules are in boards.py).

POST /scores, GET /leaderboard..., a player's own scores, leaderboard privacy and the admin hide routes.
"""

from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, StrictBool, StrictFloat, StrictInt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import boards
from auth import get_current_user, get_current_user_optional, require_admin
from database import get_db
from models import ScoreEntry, ScoreProfile, User
from rate_limits import _client_key
from schemas_admin import HiddenFlagIn


router = APIRouter()


# --- General opt-in boards (W-5 / Z-4; the rules are in boards.py) ---
# Anonymous by default ("Player 7F2Q"), one account setting to show the username,
# daily / weekly / all-time windows, opt-in enforced on the server, rows hidden
# below MIN_VISIBLE players, admin can hide a test row. Test accounts never score.


class ScoreSubmit(BaseModel):
    game: str
    board: str
    score: Union[StrictInt, StrictFloat]
    detail: Optional[str] = None
    # The player must have turned the board on; a request without this is refused.
    opt_in: StrictBool = False
    # Optional: only update these windows (e.g. ["alltime"] when re-sending a stored best).
    windows: Optional[List[str]] = None


class LeaderboardPrivacyIn(BaseModel):
    show_username: StrictBool


def _score_board_or_404(game_id: str, board: str) -> dict:
    config = boards.board_config(game_id, board)
    if config is None:
        raise HTTPException(status_code=404, detail="Unknown leaderboard")
    return config


def _default_window(config: dict) -> str:
    return "alltime" if "alltime" in config["windows"] else config["windows"][0]


def _show_username(db: Session, user_id: str) -> bool:
    profile = db.query(ScoreProfile).filter(ScoreProfile.user_id == user_id).first()
    return bool(profile and profile.show_username)


def _visible_scores(db: Session, game_id: str, board: str, window: str, period: str):
    """Rows a visitor may see: not hidden by the admin and not from a test account."""
    return (
        db.query(ScoreEntry)
        .join(User, User.id == ScoreEntry.user_id)
        .filter(
            ScoreEntry.game_id == game_id, ScoreEntry.board == board,
            ScoreEntry.window == window, ScoreEntry.period == period,
            ScoreEntry.is_hidden.is_(False), User.is_test.is_(False),
        )
    )


def _score_rank(db: Session, config: dict, game_id: str, board: str, window: str, period: str, score: float) -> int:
    query = _visible_scores(db, game_id, board, window, period)
    query = query.filter(ScoreEntry.score < score) if config["order"] == "asc" else query.filter(ScoreEntry.score > score)
    return query.count() + 1


@router.get("/leaderboard")
def list_score_boards(response: Response):
    """The registry: every board a game can show, for pickers (the hub page, widgets)."""
    response.headers["Cache-Control"] = "public, max-age=300"
    items = boards.list_boards()
    for item in items:
        item["default_window"] = _default_window(boards.BOARDS[(item["game_id"], item["board"])])
    return {"boards": items, "min_visible": boards.MIN_VISIBLE, "top_n": boards.TOP_N}


@router.get("/leaderboard/{game_id}/{board}")
def get_score_board(
    game_id: str,
    board: str,
    response: Response,
    window: Optional[str] = None,
    period: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    config = _score_board_or_404(game_id, board)
    response.headers["Cache-Control"] = "no-store"
    now = boards.current_time()
    window = window or _default_window(config)
    if window not in config["windows"]:
        raise HTTPException(status_code=422, detail="this board has no such window")
    if period is None:
        period = boards.window_period(window, now)
    elif not boards.valid_period(window, period, now):
        raise HTTPException(status_code=422, detail="bad period for this window")
    base = _visible_scores(db, game_id, board, window, period)
    total = base.count()
    suppressed = total < boards.MIN_VISIBLE
    entries = []
    if not suppressed:
        order = ScoreEntry.score.asc() if config["order"] == "asc" else ScoreEntry.score.desc()
        rows = (
            base.add_columns(User.username, ScoreProfile.show_username)
            .outerjoin(ScoreProfile, ScoreProfile.user_id == ScoreEntry.user_id)
            .order_by(order, ScoreEntry.updated_at.asc(), ScoreEntry.id.asc())
            .limit(boards.TOP_N)
            .all()
        )
        names = boards.public_names([(e.user_id, username, bool(show)) for e, username, show in rows], game_id)
        for i, ((entry, _username, _show), name) in enumerate(zip(rows, names)):
            entries.append({
                "rank": i + 1, "name": name, "score": entry.score, "detail": entry.detail or "",
                "you": current_user is not None and entry.user_id == current_user.id,
            })
    mine = None
    shows_username = None
    if current_user is not None:
        shows_username = _show_username(db, current_user.id)
        own = (
            _visible_scores(db, game_id, board, window, period)
            .filter(ScoreEntry.user_id == current_user.id)
            .first()
        )
        if own is not None:
            mine = {
                "score": own.score, "detail": own.detail or "",
                "rank": _score_rank(db, config, game_id, board, window, period, own.score),
                "name": current_user.username if shows_username else boards.anon_name(current_user.id, game_id),
            }
    return {
        "game_id": game_id, "board": board, "label": config["label"], "order": config["order"],
        "unit": config["unit"], "windows": list(config["windows"]), "window": window, "period": period,
        "min_visible": boards.MIN_VISIBLE, "suppressed": suppressed,
        "total": None if suppressed else total, "entries": entries, "mine": mine,
        "shows_username": shows_username,
    }


def _write_scores(db: Session, config: dict, user: User, payload: ScoreSubmit, score: float, detail: str, targets: list, now: float) -> dict:
    results = {}
    for window in targets:
        period = boards.window_period(window, now)
        entry = (
            db.query(ScoreEntry)
            .filter(
                ScoreEntry.game_id == payload.game, ScoreEntry.board == payload.board,
                ScoreEntry.user_id == user.id, ScoreEntry.window == window, ScoreEntry.period == period,
            )
            .first()
        )
        improved = True
        if entry is None:
            entry = ScoreEntry(
                game_id=payload.game, board=payload.board, user_id=user.id,
                window=window, period=period, score=score, detail=detail,
            )
            db.add(entry)
        elif boards.is_better(config, score, entry.score):
            entry.score = score
            entry.detail = detail
        else:
            improved = False
        results[window] = {"period": period, "improved": improved, "score": entry.score, "hidden": bool(entry.is_hidden)}
    # Keep the table small: old daily and weekly rows of this board go (all-time stays).
    cutoffs = boards.prune_cutoffs(now)
    for window, cutoff in cutoffs.items():
        db.query(ScoreEntry).filter(
            ScoreEntry.game_id == payload.game, ScoreEntry.board == payload.board,
            ScoreEntry.window == window, ScoreEntry.period < cutoff,
        ).delete(synchronize_session=False)
    db.commit()
    return results


@router.post("/scores")
def submit_score(
    payload: ScoreSubmit,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Opt-in submit. The server picks the current UTC day and week itself, so a
    client cannot post into a past period. One best score is kept per window."""
    config = _score_board_or_404(payload.game, payload.board)
    response.headers["Cache-Control"] = "no-store"
    if not payload.opt_in:
        raise HTTPException(status_code=400, detail="opt_in must be true: nothing is posted unless the player turned the board on")
    if current_user.is_test:
        return {"accepted": False, "reason": "test account"}
    now = boards.current_time()
    who, where = f"user:{current_user.id}", _client_key(request)
    if (
        boards.SUBMIT_LIMITER.blocked(who, now) or boards.SUBMIT_IP_LIMITER.blocked(where, now)
        or boards.REJECT_LIMITER.blocked(who, now)
    ):
        raise HTTPException(status_code=429, detail="Too many score submissions, try again later")
    score = boards.valid_board_score(config, payload.score)
    targets = list(config["windows"])
    bad_windows = payload.windows is not None and (
        not payload.windows or any(w not in config["windows"] for w in payload.windows)
    )
    if score is None or bad_windows:
        boards.REJECT_LIMITER.record_failure(who, now)
        if bad_windows:
            raise HTTPException(status_code=422, detail="windows must be a non-empty subset of this board's windows")
        raise HTTPException(status_code=422, detail="score is outside this leaderboard's accepted range")
    if payload.windows is not None:
        targets = [w for w in config["windows"] if w in payload.windows]
    boards.SUBMIT_LIMITER.record_failure(who, now)
    boards.SUBMIT_IP_LIMITER.record_failure(where, now)
    detail = boards.clean_detail(payload.detail)
    results = None
    for _attempt in range(2):  # a concurrent first submit can race the unique constraint once
        try:
            results = _write_scores(db, config, current_user, payload, score, detail, targets, now)
            break
        except IntegrityError:
            db.rollback()
    if results is None:
        raise HTTPException(status_code=409, detail="Could not save the score, please try again")
    for window, result in results.items():
        result["rank"] = None if result.pop("hidden") else _score_rank(
            db, config, payload.game, payload.board, window, result["period"], result["score"]
        )
    return {"accepted": True, "improved": any(r["improved"] for r in results.values()), "results": results}


@router.delete("/scores/{game_id}/{board}")
def remove_my_scores(
    game_id: str,
    board: str,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Opt out of one board: removes every one of this account's rows on it."""
    _score_board_or_404(game_id, board)
    response.headers["Cache-Control"] = "no-store"
    removed = db.query(ScoreEntry).filter(
        ScoreEntry.game_id == game_id, ScoreEntry.board == board, ScoreEntry.user_id == current_user.id,
    ).delete(synchronize_session=False)
    db.commit()
    return {"removed": int(removed)}


@router.get("/users/me/scores")
def list_my_scores(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The caller's own rows for the current day, week and all-time, with ranks
    (the personal-best view; older daily and weekly rows are not listed)."""
    response.headers["Cache-Control"] = "no-store"
    now = boards.current_time()
    current = {w: boards.window_period(w, now) for w in boards.WINDOWS}
    rows = db.query(ScoreEntry).filter(ScoreEntry.user_id == current_user.id).all()
    out = []
    for row in rows:
        config = boards.board_config(row.game_id, row.board)
        if config is None or current.get(row.window) != row.period:
            continue
        out.append({
            "game_id": row.game_id, "board": row.board, "label": config["label"], "unit": config["unit"],
            "window": row.window, "period": row.period, "score": row.score, "detail": row.detail or "",
            "rank": None if row.is_hidden else _score_rank(db, config, row.game_id, row.board, row.window, row.period, row.score),
        })
    out.sort(key=lambda r: (r["game_id"], r["board"], boards.WINDOWS.index(r["window"])))
    return {"scores": out, "show_username": _show_username(db, current_user.id)}


@router.delete("/users/me/scores")
def remove_all_my_scores(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Opt out of every board at once."""
    response.headers["Cache-Control"] = "no-store"
    removed = db.query(ScoreEntry).filter(ScoreEntry.user_id == current_user.id).delete(synchronize_session=False)
    db.commit()
    return {"removed": int(removed)}


@router.get("/users/me/leaderboard-privacy")
def get_leaderboard_privacy(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return {"show_username": _show_username(db, current_user.id)}


@router.put("/users/me/leaderboard-privacy")
def put_leaderboard_privacy(
    body: LeaderboardPrivacyIn,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The one account setting: False (the default) = anonymous 'Player 7F2Q'
    handles on every board, True = this account's username."""
    response.headers["Cache-Control"] = "no-store"
    profile = db.query(ScoreProfile).filter(ScoreProfile.user_id == current_user.id).first()
    if profile is None:
        db.add(ScoreProfile(user_id=current_user.id, show_username=body.show_username))
    else:
        profile.show_username = body.show_username
    db.commit()
    return {"show_username": body.show_username}


class AdminScoreOut(BaseModel):
    id: str
    game_id: str
    board: str
    window: str
    period: str
    score: float
    detail: str
    username: str
    is_test_account: StrictBool
    is_hidden: StrictBool


def _admin_score_out(row: ScoreEntry, user: User) -> AdminScoreOut:
    return AdminScoreOut(
        id=row.id, game_id=row.game_id, board=row.board, window=row.window, period=row.period,
        score=row.score, detail=row.detail or "", username=user.username,
        is_test_account=bool(user.is_test), is_hidden=bool(row.is_hidden),
    )


@router.get("/admin/scores", response_model=List[AdminScoreOut])
def admin_list_scores(
    response: Response,
    game_id: Optional[str] = None,
    board: Optional[str] = None,
    window: Optional[str] = None,
    period: Optional[str] = None,
    include_hidden: bool = True,
    limit: int = 200,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Board rows with the real username (admin only), newest first, so a test
    row can be found and hidden. Hidden rows are included unless asked not to."""
    response.headers["Cache-Control"] = "no-store"
    query = db.query(ScoreEntry, User).join(User, User.id == ScoreEntry.user_id)
    for column, value in ((ScoreEntry.game_id, game_id), (ScoreEntry.board, board), (ScoreEntry.window, window), (ScoreEntry.period, period)):
        if value is not None:
            query = query.filter(column == value)
    if not include_hidden:
        query = query.filter(ScoreEntry.is_hidden.is_(False))
    rows = query.order_by(ScoreEntry.updated_at.desc(), ScoreEntry.id.desc()).limit(max(1, min(limit, 500))).all()
    return [_admin_score_out(row, user) for row, user in rows]


@router.patch("/admin/scores/{score_id}", response_model=AdminScoreOut)
def admin_hide_score(
    score_id: str,
    body: HiddenFlagIn,
    response: Response,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """The "this is a test, hide it" toggle for one board row. Reversible."""
    response.headers["Cache-Control"] = "no-store"
    row = db.query(ScoreEntry).filter(ScoreEntry.id == score_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Score not found")
    row.is_hidden = body.is_hidden
    db.commit()
    user = db.query(User).filter(User.id == row.user_id).first()
    return _admin_score_out(row, user)
