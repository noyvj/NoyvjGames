"""Site-wide feedback and its admin moderation.

POST/GET /feedback (with its per-address rate limit), the admin routes that list and hide feedback and ratings,
and GET /admin/stats.
"""

import threading
import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator, StrictBool
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from auth import _test_user_ids, get_current_user_optional, require_admin
from constants import ID_MAX_LENGTH, TEXT_MAX_LENGTH
from database import get_db
from models import Feedback, Rating, Save, User
from rate_limits import _client_key
from schemas_admin import HiddenFlagIn


router = APIRouter()


# --- Site-wide feedback (ACCOUNTS-AND-FEEDBACK-DESIGN.md) ---
# Distinct from the Rating table (routes_core.py: the hub's star widget + each
# climate game's in-game feedback prompt): this is the newer,
# account-aware system that also covers feedback not tied to any game.

FEEDBACK_RATE_LIMIT_PER_HOUR = 5


# In-process only, per the design doc's own "keep it minimal for now"
# stance — resets on every deploy/restart and isn't shared across
# multiple server instances. Good enough to blunt casual spam; build a
# real (e.g. Redis-backed) limiter only if abuse actually shows up.
# REVIEW(performance): every distinct IP that has ever POSTed to /feedback
# stays as a key in this dict for the life of the process — stale IPs are
# never purged, only their timestamp lists are filtered. Unbounded growth in
# theory; negligible at this site's actual traffic, and capped in practice by
# the fact it already resets on every deploy/restart.
_feedback_submission_log: dict[str, list[float]] = {}


# This is a sync def, so FastAPI runs concurrent requests from the same IP
# on separate threadpool threads — without a lock, the read-check-append
# below isn't atomic: multiple threads could each read `recent` before any
# of them writes the appended list back, letting more than
# FEEDBACK_RATE_LIMIT_PER_HOUR requests through under a concurrent burst
# from one IP. A plain in-process lock is enough here, matching the dict's
# own "in-process only, resets on restart, good enough to blunt casual spam"
# stance right below — this isn't trying to be a distributed rate limiter.
_feedback_submission_lock = threading.Lock()


def _check_feedback_rate_limit(client_ip: str) -> None:
    now = time.time()
    window_start = now - 3600
    with _feedback_submission_lock:
        recent = [t for t in _feedback_submission_log.get(client_ip, []) if t > window_start]
        if len(recent) >= FEEDBACK_RATE_LIMIT_PER_HOUR:
            raise HTTPException(status_code=429, detail="Too many submissions — try again later")
        recent.append(now)
        _feedback_submission_log[client_ip] = recent
        if len(_feedback_submission_log) > 5000:  # drop addresses whose whole window has passed
            for stale in [ip for ip, ts in _feedback_submission_log.items() if not ts or ts[-1] <= window_start]:
                del _feedback_submission_log[stale]


class FeedbackIn(BaseModel):
    game_id: Optional[str] = Field(default=None, max_length=ID_MAX_LENGTH)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=TEXT_MAX_LENGTH)

    @model_validator(mode="after")
    def require_rating_or_comment(self):
        if self.rating is None and not self.comment:
            raise ValueError("provide either rating or comment")
        return self


class FeedbackOut(BaseModel):
    id: str
    game_id: Optional[str]
    user_id: Optional[str]
    rating: Optional[int]
    comment: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackPublicOut(BaseModel):
    """What the public listing shows: no account identifier of any kind."""
    id: str
    game_id: Optional[str]
    rating: Optional[int]
    comment: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post("/feedback", response_model=FeedbackOut)
def create_feedback(
    payload: FeedbackIn,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    _check_feedback_rate_limit(_client_key(request))
    row = Feedback(
        game_id=payload.game_id,
        user_id=current_user.id if current_user else None,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/feedback", response_model=List[FeedbackPublicOut])
def list_feedback(response: Response, game_id: Optional[str] = None, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    query = db.query(Feedback).filter(Feedback.is_hidden.is_(False))
    query = query.filter(Feedback.game_id.is_(None)) if game_id is None else query.filter(Feedback.game_id == game_id)
    return query.order_by(Feedback.created_at.desc()).all()


# --- UX-9: admin "this is a test, hide it" toggle for feedback rows ---
# Hidden rows disappear from the public reads (GET /feedback, GET
# /ratings/{slug}) but stay visible to admin, with the flag, so the toggle
# can be reversed. Two tables hold feedback: `feedback` (hub site feedback and
# per-game feedback form) and `ratings` (star widget + in-game yes/no prompt).
class AdminFeedbackOut(BaseModel):
    id: str
    game_id: Optional[str]
    rating: Optional[int]
    comment: Optional[str]
    is_hidden: StrictBool
    created_at: Optional[datetime]


class AdminRatingOut(BaseModel):
    id: int
    game_slug: str
    stars: Optional[int]
    comment: Optional[str]
    response: Optional[str]
    is_hidden: StrictBool
    created_at: Optional[datetime]


def _admin_feedback_out(row: Feedback) -> AdminFeedbackOut:
    return AdminFeedbackOut(
        id=row.id, game_id=row.game_id, rating=row.rating, comment=row.comment,
        is_hidden=bool(row.is_hidden), created_at=row.created_at,
    )


def _admin_rating_out(row: Rating) -> AdminRatingOut:
    return AdminRatingOut(
        id=row.id, game_slug=row.game_slug, stars=row.stars, comment=row.comment,
        response=row.response, is_hidden=bool(row.is_hidden), created_at=row.created_at,
    )


@router.get("/admin/feedback", response_model=List[AdminFeedbackOut])
def admin_list_feedback(
    response: Response,
    include_hidden: bool = True,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Every site/game feedback row (all games and general), newest first."""
    response.headers["Cache-Control"] = "no-store"
    query = db.query(Feedback)
    if not include_hidden:
        query = query.filter(Feedback.is_hidden.is_(False))
    return [_admin_feedback_out(r) for r in query.order_by(Feedback.created_at.desc()).all()]


@router.patch("/admin/feedback/{feedback_id}", response_model=AdminFeedbackOut)
def admin_hide_feedback(
    feedback_id: str,
    body: HiddenFlagIn,
    response: Response,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    row = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    row.is_hidden = body.is_hidden
    db.commit()
    return _admin_feedback_out(row)


@router.get("/admin/ratings", response_model=List[AdminRatingOut])
def admin_list_ratings(
    response: Response,
    game_slug: Optional[str] = None,
    include_hidden: bool = True,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Every ratings-table row (star widget and in-game yes/no prompt)."""
    response.headers["Cache-Control"] = "no-store"
    query = db.query(Rating)
    if game_slug is not None:
        query = query.filter(Rating.game_slug == game_slug)
    if not include_hidden:
        query = query.filter(Rating.is_hidden.is_(False))
    return [_admin_rating_out(r) for r in query.order_by(Rating.created_at.desc(), Rating.id.desc()).all()]


@router.patch("/admin/ratings/{rating_id}", response_model=AdminRatingOut)
def admin_hide_rating(
    rating_id: int,
    body: HiddenFlagIn,
    response: Response,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    row = db.query(Rating).filter(Rating.id == rating_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Rating not found")
    row.is_hidden = body.is_hidden
    db.commit()
    return _admin_rating_out(row)


# --- Admin aggregate stats (TODO.md L8) ---
# Backs the unlisted admin.html page's Overview panel. Every number here is
# a count, never a row of user content. Admin-only (require_admin).
class AdminStatsOut(BaseModel):
    total_users: int
    total_saves: int
    saves_by_game: dict[str, int]


@router.get("/admin/stats", response_model=AdminStatsOut)
def admin_stats(
    response: Response,
    hide_test: bool = True,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """U7: test accounts and their saves are left out by default."""
    response.headers["Cache-Control"] = "no-store"
    users_query = db.query(func.count(User.id))
    saves_query = db.query(func.count(Save.id))
    by_game_query = db.query(Save.game_id, func.count(Save.id))
    if hide_test:
        users_query = users_query.filter(User.is_test.is_(False))
        not_test = or_(Save.user_id.is_(None), ~Save.user_id.in_(_test_user_ids(db)))
        saves_query = saves_query.filter(not_test)
        by_game_query = by_game_query.filter(not_test)
    total_users = users_query.scalar() or 0
    total_saves = saves_query.scalar() or 0
    saves_by_game = dict(by_game_query.group_by(Save.game_id).all())
    return AdminStatsOut(total_users=total_users, total_saves=total_saves, saves_by_game=saves_by_game)
