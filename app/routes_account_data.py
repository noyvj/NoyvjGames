"""A player's data export and account deletion: GET /users/me/export, DELETE /users/me."""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

import account_data
from auth import _normalize_username, get_current_user, OWNER_USERNAME
from database import get_db
from models import User


router = APIRouter()


# --- Y-14: download or delete everything held for the signed-in account ---
# The helpers (and the list of what is and is not linked to an account) are in
# account_data.py. Both routes act only on the caller's own account.


@router.get("/users/me/export")
def export_my_data(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Everything the server holds for this account as one JSON document. No
    password hash and no session token is ever included."""
    response.headers["Cache-Control"] = "no-store"
    return account_data.build_export(db, current_user)


class DeleteAccountIn(BaseModel):
    # The player types their own username; the server checks it again, so a
    # stray request with a stolen token and no knowledge of the form still fails.
    confirm_username: str


@router.delete("/users/me")
def delete_my_account(
    body: DeleteAccountIn,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently deletes the account and every row linked to it (sessions,
    saves and slots, leaderboard rows, score profile, feedback written while
    signed in, What's New votes). Cannot be undone. The owner account is refused:
    once deleted, its name would be free for anyone to sign up with and inherit
    the admin access that name carries."""
    response.headers["Cache-Control"] = "no-store"
    if current_user.username == OWNER_USERNAME:
        raise HTTPException(status_code=403, detail="The owner account cannot be deleted here")
    if _normalize_username(body.confirm_username) != current_user.username:
        raise HTTPException(status_code=422, detail="Type your username exactly to confirm")
    removed = account_data.delete_account(db, current_user)
    return {"deleted": True, "removed": removed}
