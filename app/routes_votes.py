"""What's New 'was this helpful?' votes and the admin vote summary."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, StrictBool
from sqlalchemy.orm import Session

import account_data
from auth import get_current_user_optional, require_admin
from database import get_db
from models import User
from rate_limits import _client_key
from throttle import FailureLimiter


router = APIRouter()


# --- Y-24: "was this helpful?" on What's New entries ---
# One vote per entry per account (signed in) or per anonymous browser token (the
# X-Vote-Token header, a random string the browser makes up). Voting again changes
# the vote. Tallies are admin-only (GET /admin/whats-new-votes).

VOTE_LIMITER = FailureLimiter(max_failures=60, window_seconds=60 * 60)  # votes per address per hour (counted as "failures")


def _vote_voter(entry_id: str, user: Optional[User], token: Optional[str]) -> tuple:
    if not account_data.ENTRY_ID_RE.match(entry_id):
        raise HTTPException(status_code=422, detail="Unknown What's New entry id")
    voter = account_data.voter_for(user, token)
    if voter is None:
        raise HTTPException(status_code=422, detail="Sign in or send a valid X-Vote-Token header")
    return voter


class HelpfulVoteIn(BaseModel):
    helpful: StrictBool


@router.put("/whats-new/votes/{entry_id}")
def put_whats_new_vote(
    entry_id: str,
    body: HelpfulVoteIn,
    request: Request,
    response: Response,
    x_vote_token: Optional[str] = Header(default=None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    voter_key, user_id = _vote_voter(entry_id, current_user, x_vote_token)
    where = _client_key(request)
    if VOTE_LIMITER.blocked(where):
        raise HTTPException(status_code=429, detail="Too many votes, try again later")
    VOTE_LIMITER.record_failure(where)
    row = account_data.cast_vote(db, entry_id, voter_key, user_id, body.helpful)
    return {"entry_id": entry_id, "helpful": bool(row.helpful)}


@router.delete("/whats-new/votes/{entry_id}")
def delete_whats_new_vote(
    entry_id: str,
    request: Request,
    response: Response,
    x_vote_token: Optional[str] = Header(default=None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Take the vote back (the thumb pressed twice)."""
    response.headers["Cache-Control"] = "no-store"
    voter_key, _user_id = _vote_voter(entry_id, current_user, x_vote_token)
    where = _client_key(request)
    if VOTE_LIMITER.blocked(where):
        raise HTTPException(status_code=429, detail="Too many votes, try again later")
    VOTE_LIMITER.record_failure(where)
    return {"entry_id": entry_id, "removed": account_data.retract_vote(db, entry_id, voter_key)}


@router.get("/admin/whats-new-votes")
def admin_whats_new_votes(
    response: Response,
    hide_test: bool = True,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    return {"entries": account_data.vote_tallies(db, hide_test)}
