"""GET /users/me and the account-synced settings (theme, text scale, reduced motion)."""

import json

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User


router = APIRouter()


# --- Y31: account-synced site-wide settings ---
# Only these keys, with these exact value shapes, are ever stored, so the
# column can't become a dumping ground. Anything else in a request is
# ignored, and an out-of-range or wrong-typed value rejects the whole request.
SETTINGS_TEXT_SCALE_MIN = 0.85
SETTINGS_TEXT_SCALE_MAX = 1.5


def _validate_settings(payload: dict) -> dict:
    clean: dict = {}
    if "theme" in payload:
        if payload["theme"] not in ("light", "dark"):
            raise HTTPException(status_code=422, detail="theme must be 'light' or 'dark'")
        clean["theme"] = payload["theme"]
    if "text_scale" in payload:
        value = payload["text_scale"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not (
            SETTINGS_TEXT_SCALE_MIN <= value <= SETTINGS_TEXT_SCALE_MAX
        ):
            raise HTTPException(
                status_code=422,
                detail=f"text_scale must be a number from {SETTINGS_TEXT_SCALE_MIN} to {SETTINGS_TEXT_SCALE_MAX}",
            )
        clean["text_scale"] = float(value)
    if "reduced_motion" in payload:
        if not isinstance(payload["reduced_motion"], bool):
            raise HTTPException(status_code=422, detail="reduced_motion must be true or false")
        clean["reduced_motion"] = payload["reduced_motion"]
    if "lite_mode" in payload:
        if not isinstance(payload["lite_mode"], bool):
            raise HTTPException(status_code=422, detail="lite_mode must be true or false")
        clean["lite_mode"] = payload["lite_mode"]
    return clean


def _stored_settings(user: User) -> dict:
    """The saved settings, re-validated on the way out so a hand-edited row
    can never hand a client something outside the whitelist."""
    if not user.settings_json:
        return {}
    try:
        data = json.loads(user.settings_json)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    try:
        return _validate_settings(data)
    except HTTPException:
        return {}


@router.get("/users/me")
def get_me(response: Response, current_user: User = Depends(get_current_user)):
    """Who does this bearer token belong to? Used by shared/owner-gate.js to
    keep the unlisted owner pages (admin, ideas sheet, Warframe tracker) to
    one account. Returns only the username."""
    response.headers["Cache-Control"] = "no-store"
    return {"username": current_user.username}


@router.get("/users/me/settings")
def get_my_settings(response: Response, current_user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return {"settings": _stored_settings(current_user)}


@router.put("/users/me/settings")
def put_my_settings(
    payload: dict,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Merges the given keys into this account's stored settings (a client
    that only changed the theme sends only the theme)."""
    response.headers["Cache-Control"] = "no-store"
    merged = {**_stored_settings(current_user), **_validate_settings(payload)}
    current_user.settings_json = json.dumps(merged)
    db.commit()
    return {"settings": merged}
