"""Who is calling: bearer-token lookup, the admin-token check, the owner account name, the test-user helper.

Layer 2: imports only database, models and standard/third-party packages.
"""

import logging
import os
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import AuthSession, User


logger = logging.getLogger(__name__)


# --- U8: admin access ---
# Admin-only endpoints need an `X-Admin-Token` header matching one of two
# server environment variables: ADMIN_TOKEN (the site owner's password) or
# AI_ADMIN_TOKEN (a separate, independently revocable token for the AI
# sessions that build the site). Fail closed: with neither variable set the
# endpoints answer 503 rather than being open, so a deploy that lands before
# the tokens are configured locks the admin data instead of exposing it.
# Read at request time (not import time) so setting or revoking a variable
# takes effect on the next request/redeploy without code changes.
ADMIN_TOKEN_ENV_VARS = ("ADMIN_TOKEN", "AI_ADMIN_TOKEN")


# The site owner's own account also counts as admin: signed in as this user,
# admin.html needs no separate password. Usernames are stored lowercased and
# unique (see _normalize_username), so only this exact account matches. The
# AI sessions keep using AI_ADMIN_TOKEN, which stays independently revocable.
OWNER_USERNAME = "noyvj"


OWNER_SIGNUP_ENV_VAR = "OWNER_SIGNUP_ALLOWED"


def owner_signup_allowed() -> bool:
    """FY-16: true only while the server environment variable OWNER_SIGNUP_ALLOWED is "1" (or "true").
    Read at request time, so setting or unsetting it needs a redeploy but no code change."""
    return os.environ.get(OWNER_SIGNUP_ENV_VAR, "").strip().lower() in ("1", "true")


def require_admin(
    x_admin_token: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> None:
    if authorization:
        user = get_current_user_optional(authorization, db)
        if user is not None and user.username == OWNER_USERNAME:
            return
    configured = [os.environ.get(name, "") for name in ADMIN_TOKEN_ENV_VARS]
    configured = [value for value in configured if value]
    if not configured:
        raise HTTPException(status_code=503, detail="Admin access is not configured on this server")
    supplied = x_admin_token or ""
    # compare_digest on every configured token (no early exit) keeps the
    # timing independent of which one, if any, matched.
    matches = [secrets.compare_digest(supplied.encode(), value.encode()) for value in configured]
    if not supplied or not any(matches):
        raise HTTPException(status_code=401, detail="Admin token required")


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def get_current_user(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    session = db.query(AuthSession).filter(AuthSession.token == token).first()
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    user = db.query(User).filter(User.id == session.user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user


def get_current_user_optional(
    authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)
) -> Optional[User]:
    """Same lookup as get_current_user, but anonymous callers (no/garbage
    Authorization header) get None back instead of a 401 — used by
    endpoints, like feedback submission, where signing in is optional."""
    if not authorization:
        return None
    try:
        return get_current_user(authorization, db)
    except HTTPException:
        # Logged at debug (not warning) because a garbage/expired token here
        # is routine, not exceptional — this dependency exists specifically
        # so an optional-auth endpoint degrades to anonymous rather than
        # erroring. Kept as a log line rather than nothing, though, so a
        # signed-in user whose requests keep silently landing as anonymous
        # has a server-side trail to check.
        logger.debug("get_current_user_optional: treating request as anonymous, auth failed", exc_info=True)
        return None


def _test_user_ids(db: Session):
    return db.query(User.id).filter(User.is_test.is_(True))
