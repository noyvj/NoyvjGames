"""Player profiles: the owner's view/editor under /users/me/profile and the public GET /profiles/{username}."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

import profiles
from auth import _normalize_username, get_current_user
from database import get_db
from models import User
from rate_limits import _throttle, PROFILE_LOOKUP_LIMITER, PROFILE_UPDATE_LIMITER


router = APIRouter()


# --- Z-7 / Y-1: the player profile (see profiles.py) ---
# GET/PUT /users/me/profile is the signed-in owner's view and editor; GET /profiles/{username} is
# the public page's data and answers 404 for "no such account" and "profile not public" alike.
PROFILE_NOT_PUBLIC = "There is no public profile with that name."


@router.get("/users/me/profile")
def get_my_profile(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return profiles.summarize(current_user, profiles.get_row(db, current_user.id), viewer="owner")


@router.put("/users/me/profile")
def put_my_profile(
    payload: profiles.ProfilePut,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Merge the keys sent: is_public (the switch), favourite_game (null clears), event_badges (ids
    only) and progress ({game, add_seconds, achievements, streaks}, the shared/profile.js update).
    Progress posts are rate limited per account."""
    response.headers["Cache-Control"] = "no-store"
    if payload.progress is not None:
        if PROFILE_UPDATE_LIMITER.blocked(current_user.id):
            raise HTTPException(status_code=429, detail="Too many profile updates, try again later")
        PROFILE_UPDATE_LIMITER.record_failure(current_user.id)
    row = profiles.apply_put(db, current_user, payload)
    return profiles.summarize(current_user, row, viewer="owner")


@router.post("/users/me/profile/backfill")
def backfill_my_profile(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """GN-7: raise the profile's achievement counts (and seasonal badges) from the account's existing saves.
    Counts only go up; nothing is lowered. Rate limited like other profile writes."""
    response.headers["Cache-Control"] = "no-store"
    if PROFILE_UPDATE_LIMITER.blocked(current_user.id):
        raise HTTPException(status_code=429, detail="Too many profile updates, try again later")
    PROFILE_UPDATE_LIMITER.record_failure(current_user.id)
    raised = profiles.backfill_from_saves(db, current_user)
    row = profiles.get_row(db, current_user.id)
    return {"updated": raised, "profile": profiles.summarize(current_user, row, viewer="owner")}


@router.get("/profiles/{username}")
def get_public_profile(username: str, request: Request, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    _throttle(PROFILE_LOOKUP_LIMITER, request)
    found = profiles.public_profile(db, _normalize_username(username))
    if found is None:
        raise HTTPException(status_code=404, detail=PROFILE_NOT_PUBLIC)
    return found
