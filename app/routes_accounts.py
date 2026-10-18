"""Accounts: POST /auth/signup and POST /auth/login (username + password, bearer session token)."""

import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import _normalize_username, owner_signup_allowed, OWNER_USERNAME
from database import get_db
from models import AuthSession, User
from passwords import _hash_password, _verify_password
from rate_limits import (
    _client_key, _throttle, LOGIN_FAILURE_LIMITER, LOGIN_IP_FAILURE_LIMITER, SIGNUP_LIMITER,
)


router = APIRouter()


# --- Accounts (ACCOUNTS-AND-FEEDBACK-DESIGN.md Phase 2, revised: username +
# password, not the original magic-link/email design — that needed an
# email provider/API key that hasn't been chosen yet, and was a lot of
# extra infrastructure for a second-pass update. Real email-based
# accounts (verified email, password reset) can still be layered on
# later; nothing downstream (saves, feedback) cares how a user_id was
# proven, only that it was. The tradeoff to be upfront about: with no
# email on file, there is no password-reset path — a forgotten password
# means that account's claimed saves/feedback are unrecoverable.
#
# Passwords are hashed with salted PBKDF2-HMAC-SHA256 using only the
# standard library (hashlib + os + secrets) rather than pulling in a new
# dependency for something this standard. No complexity requirements are
# enforced server-side (the user asked for none) — the frontend shows an
# advisory hint instead of a hard requirement.
SESSION_TOKEN_BYTES = 32


USERNAME_MAX_LENGTH = 64  # enforced at signup only, so a legacy longer name can still sign in
USERNAME_PATTERN = re.compile(r"[\w .-]+", re.UNICODE)


class AuthIn(BaseModel):
    username: str
    password: str = Field(max_length=1024)

    @model_validator(mode="after")
    def require_both(self):
        if not self.username.strip():
            raise ValueError("username is required")
        if not self.password:
            raise ValueError("password is required")
        return self


class AuthOut(BaseModel):
    bearer_token: str
    username: str


# REVIEW(security): AuthSession rows never expire and there is no
# /auth/logout endpoint to revoke a token server-side (models.py's own
# AuthSession docstring flags this). A leaked bearer token — e.g. left in
# localStorage on a shared machine — stays valid forever with no way for the
# user to kill it.
def _start_session(db: Session, user: User) -> str:
    session_token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
    db.add(AuthSession(user_id=user.id, token=session_token))
    db.commit()
    return session_token


def _username_exists(db: Session, username: str) -> bool:
    """Split out from signup() so a test can force the "no existing user"
    branch while a real competing row is already in the database — the only
    practical way to exercise signup's commit-time IntegrityError handling
    below without standing up genuine concurrent requests."""
    return db.query(User).filter(User.username == username).first() is not None


AI_TEST_USERNAME_PREFIX = "aitest"


@router.post("/auth/signup", response_model=AuthOut)
def signup(payload: AuthIn, request: Request, db: Session = Depends(get_db)):
    _throttle(SIGNUP_LIMITER, request, "Too many sign-ups from this address, try again later")
    username = _normalize_username(payload.username)
    if len(username) > USERNAME_MAX_LENGTH:
        raise HTTPException(status_code=422, detail=f"username must be at most {USERNAME_MAX_LENGTH} characters")
    # Letters, digits, spaces and . _ - only for NEW accounts (hub QA found that any string could become a
    # username and be rendered in places like the admin page; older accounts with other characters can still
    # sign in because only signup checks this).
    if not USERNAME_PATTERN.fullmatch(username):
        raise HTTPException(status_code=422, detail="username may only use letters, numbers, spaces and . _ -")
    # FY-16: the owner account's name is reserved. The account already exists in production; this only
    # stops a rebuilt or empty database from letting a stranger register "noyvj" first and inherit the
    # admin access that name carries (require_admin, require_owner). Set OWNER_SIGNUP_ALLOWED=1 in the
    # server environment ONLY while creating the owner account on a fresh database, then unset it.
    if username == OWNER_USERNAME and not owner_signup_allowed():
        raise HTTPException(status_code=403, detail="That username is reserved")
    if _username_exists(db, username):
        raise HTTPException(status_code=409, detail="Username already taken")

    # U7: the dedicated AI testing accounts are recognised by name, so the AIs'
    # test signups never count as real data without anyone having to flag them.
    user = User(
        username=username,
        password_hash=_hash_password(payload.password),
        is_test=username.startswith(AI_TEST_USERNAME_PREFIX),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # The existence check above isn't atomic with this commit — two
        # concurrent signups for the same username can both pass it before
        # either commits. Without this, the second commit would raise an
        # unhandled IntegrityError (bare 500) instead of the same 409 the
        # pre-check above is trying to give; create_save has the equivalent
        # guard for the same class of race on save codes.
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already taken")
    db.refresh(user)

    session_token = _start_session(db, user)
    return AuthOut(bearer_token=session_token, username=user.username)


@router.post("/auth/login", response_model=AuthOut)
def login(payload: AuthIn, request: Request, db: Session = Depends(get_db)):
    username = _normalize_username(payload.username)
    ip = _client_key(request)
    if LOGIN_FAILURE_LIMITER.blocked(username) or LOGIN_IP_FAILURE_LIMITER.blocked(ip):
        raise HTTPException(status_code=429, detail="Too many failed logins, try again in a few minutes")
    user = db.query(User).filter(User.username == username).first()
    if user is None or not _verify_password(payload.password, user.password_hash):
        LOGIN_FAILURE_LIMITER.record_failure(username)
        LOGIN_IP_FAILURE_LIMITER.record_failure(ip)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    LOGIN_FAILURE_LIMITER.clear(username)

    session_token = _start_session(db, user)
    return AuthOut(bearer_token=session_token, username=user.username)
