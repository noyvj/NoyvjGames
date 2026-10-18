"""The simplest public routes.

GET /health (the hub footer's status dot), star ratings and per-game responses (/ratings...) and anonymous
save codes (/saves).
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from constants import ID_MAX_LENGTH, TEXT_MAX_LENGTH
from database import engine, get_db
from models import Rating, Save
from rate_limits import _client_key, _throttle, RATING_LIMITER, SAVE_CODE_MISS_LIMITER, SAVE_CREATE_LIMITER
from schemas_saves import _generate_save_code, SAVE_CODE_GENERATION_ATTEMPTS, SaveIn, SaveOut, SaveUpdate


logger = logging.getLogger(__name__)


router = APIRouter()


class RatingIn(BaseModel):
    game_slug: str = Field(max_length=ID_MAX_LENGTH)
    # Both optional: the hub's star-rating widget sends stars (+ optional
    # comment); a per-game feedback prompt (Canopy onward) sends response
    # instead. A submission needs at least one of the two — see below.
    stars: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=TEXT_MAX_LENGTH)
    response: Optional[str] = Field(default=None, max_length=TEXT_MAX_LENGTH)

    @model_validator(mode="after")
    def require_stars_or_response(self):
        if self.stars is None and not self.response:
            raise ValueError("provide either stars or response")
        return self


class RatingOut(BaseModel):
    id: int
    game_slug: str
    stars: Optional[int]
    comment: Optional[str]
    response: Optional[str]

    model_config = ConfigDict(from_attributes=True)


@router.get("/health")
def health(response: Response):
    """Y-27: tiny read-only status check behind the hub footer's status dot.

    Always answers 200 (the dot reads the body, so an amber state is not an
    HTTP failure): "ok" when the database answers a bare SELECT 1, otherwise
    "degraded" with db false, which is what the hub explains as "ratings and
    saves may be unavailable". No tables are read or written and nothing
    about users or data is exposed.
    """
    response.headers["Cache-Control"] = "no-store"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": True}
    except Exception:
        logger.exception("health check: database not answering")
        return {"status": "degraded", "db": False}


@router.post("/ratings", response_model=RatingOut)
def create_rating(rating: RatingIn, request: Request, db: Session = Depends(get_db)):
    _throttle(RATING_LIMITER, request)
    row = Rating(
        game_slug=rating.game_slug,
        stars=rating.stars,
        comment=rating.comment,
        response=rating.response,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# Y-31: the hub's star averages in ONE small response instead of one download of every rating row
# per game. Public, aggregates only (no comments, no ids), hidden rows left out. `stars` rows only:
# in-game feedback-prompt rows (stars NULL, a text `response`) never count towards an average.
# Test data is handled the way it always was for ratings: an admin hides the row (is_hidden), which
# ratings have no account link to do any other way. A short cache keeps a busy hub cheap; the hub
# bypasses it for the one request that follows the visitor's own submission.
RATINGS_SUMMARY_CACHE_CONTROL = "public, max-age=60"


@router.get("/ratings-summary")
def ratings_summary(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = RATINGS_SUMMARY_CACHE_CONTROL
    rows = (
        db.query(Rating.game_slug, Rating.stars, func.count(Rating.id))
        .filter(Rating.stars.isnot(None), Rating.is_hidden.is_(False))
        .group_by(Rating.game_slug, Rating.stars)
        .all()
    )
    games: dict = {}
    for slug, stars, n in rows:
        if not isinstance(stars, int) or not 1 <= stars <= 5:
            continue
        entry = games.setdefault(slug, {"count": 0, "total": 0, "distribution": {str(i): 0 for i in range(1, 6)}})
        entry["distribution"][str(stars)] += int(n)
        entry["count"] += int(n)
        entry["total"] += stars * int(n)
    return {
        "games": {
            slug: {
                "average": round(e["total"] / e["count"], 4),
                "count": e["count"],
                "distribution": e["distribution"],
            }
            for slug, e in sorted(games.items())
        }
    }


@router.get("/ratings/{game_slug}", response_model=List[RatingOut])
def list_ratings(game_slug: str, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return (
        db.query(Rating)
        .filter(Rating.game_slug == game_slug, Rating.is_hidden.is_(False))
        .order_by(Rating.created_at.desc())
        .all()
    )


@router.post("/saves", response_model=SaveOut)
def create_save(payload: SaveIn, request: Request, db: Session = Depends(get_db)):
    _throttle(SAVE_CREATE_LIMITER, request)
    # Collision check on insert, per the design doc: generate, try to
    # commit, and on a unique-constraint hit (astronomically unlikely at
    # this keyspace size, but cheap to guard) roll back and regenerate.
    for _ in range(SAVE_CODE_GENERATION_ATTEMPTS):
        row = Save(save_code=_generate_save_code(), game_id=payload.game_id, save_data=payload.save_data)
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            # Logged at warning (not exception/error) because this is the
            # expected, designed-for outcome of a code collision — only worth
            # a closer look if it happens often enough in the logs to suggest
            # something other than bad luck at this keyspace size (e.g. a
            # real DB/connectivity problem masquerading as a collision).
            logger.warning("create_save: IntegrityError on save_code, retrying", exc_info=True)
            db.rollback()
            continue
        db.refresh(row)
        return row
    raise HTTPException(status_code=500, detail="Could not generate a unique save code — try again")


@router.get("/saves/{save_code}", response_model=SaveOut)
def get_save(save_code: str, request: Request, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    ip = _client_key(request)
    if SAVE_CODE_MISS_LIMITER.blocked(ip):
        raise HTTPException(status_code=429, detail="Too many unknown save codes, try again in a few minutes")
    row = db.query(Save).filter(Save.save_code == save_code).first()
    if row is None:
        SAVE_CODE_MISS_LIMITER.record_failure(ip)
        raise HTTPException(status_code=404, detail="Save code not found")
    return row


@router.put("/saves/{save_code}", response_model=SaveOut)
def update_save(save_code: str, payload: SaveUpdate, db: Session = Depends(get_db)):
    row = db.query(Save).filter(Save.save_code == save_code).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Save code not found")
    row.save_data = payload.save_data
    db.commit()
    db.refresh(row)
    return row
