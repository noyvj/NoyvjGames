import hashlib
import os
import secrets
import time
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import Base, engine, get_db, patch_schema
from models import AuthSession, Feedback, Rating, Save, User

Base.metadata.create_all(bind=engine)
patch_schema()

app = FastAPI(title="CodingIsANoyvj ratings API")

DEFAULT_ORIGINS = "https://noyvj.github.io,http://localhost:8073"
allowed_origins = os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)


class RatingIn(BaseModel):
    game_slug: str
    # Both optional: the hub's star-rating widget sends stars (+ optional
    # comment); a per-game feedback prompt (Canopy onward) sends response
    # instead. A submission needs at least one of the two — see below.
    stars: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = None
    response: Optional[str] = None

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


@app.post("/ratings", response_model=RatingOut)
def create_rating(rating: RatingIn, db: Session = Depends(get_db)):
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


@app.get("/ratings/{game_slug}", response_model=List[RatingOut])
def list_ratings(game_slug: str, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return db.query(Rating).filter(Rating.game_slug == game_slug).order_by(Rating.created_at.desc()).all()


# --- Save system (SAVE-SYSTEM-DESIGN.md Phase 1: save codes, no accounts) ---

# Unambiguous alphabet — no 0/O, 1/I/L — so a code is safe to read aloud,
# handwrite, or misread on a small screen. Grouped XXXX-XXXX for the same
# reason a phone number is grouped, not because 8 chars need it.
SAVE_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
SAVE_CODE_GROUP_LEN = 4
SAVE_CODE_GROUPS = 2
SAVE_CODE_GENERATION_ATTEMPTS = 5


def _generate_save_code() -> str:
    chars = [secrets.choice(SAVE_CODE_ALPHABET) for _ in range(SAVE_CODE_GROUP_LEN * SAVE_CODE_GROUPS)]
    groups = [
        "".join(chars[i : i + SAVE_CODE_GROUP_LEN])
        for i in range(0, len(chars), SAVE_CODE_GROUP_LEN)
    ]
    return "-".join(groups)


class SaveIn(BaseModel):
    game_id: str
    save_data: dict


class SaveUpdate(BaseModel):
    save_data: dict


class SaveOut(BaseModel):
    save_code: str
    game_id: str
    save_data: dict
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


@app.post("/saves", response_model=SaveOut)
def create_save(payload: SaveIn, db: Session = Depends(get_db)):
    # Collision check on insert, per the design doc: generate, try to
    # commit, and on a unique-constraint hit (astronomically unlikely at
    # this keyspace size, but cheap to guard) roll back and regenerate.
    for _ in range(SAVE_CODE_GENERATION_ATTEMPTS):
        row = Save(save_code=_generate_save_code(), game_id=payload.game_id, save_data=payload.save_data)
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(row)
        return row
    raise HTTPException(status_code=500, detail="Could not generate a unique save code — try again")


@app.get("/saves/{save_code}", response_model=SaveOut)
def get_save(save_code: str, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    row = db.query(Save).filter(Save.save_code == save_code).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Save code not found")
    return row


@app.put("/saves/{save_code}", response_model=SaveOut)
def update_save(save_code: str, payload: SaveUpdate, db: Session = Depends(get_db)):
    row = db.query(Save).filter(Save.save_code == save_code).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Save code not found")
    row.save_data = payload.save_data
    db.commit()
    db.refresh(row)
    return row


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
PBKDF2_ITERATIONS = 600_000  # OWASP's 2023 minimum recommendation for PBKDF2-HMAC-SHA256
PBKDF2_ALGORITHM = "sha256"
PASSWORD_SALT_BYTES = 16


def _hash_password(password: str) -> str:
    salt = os.urandom(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(PBKDF2_ALGORITHM, password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac(PBKDF2_ALGORITHM, password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return secrets.compare_digest(actual, expected)


def _normalize_username(username: str) -> str:
    return username.strip().lower()


class AuthIn(BaseModel):
    username: str
    password: str

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


def _start_session(db: Session, user: User) -> str:
    session_token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
    db.add(AuthSession(user_id=user.id, token=session_token))
    db.commit()
    return session_token


@app.post("/auth/signup", response_model=AuthOut)
def signup(payload: AuthIn, db: Session = Depends(get_db)):
    username = _normalize_username(payload.username)
    if db.query(User).filter(User.username == username).first() is not None:
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(username=username, password_hash=_hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    session_token = _start_session(db, user)
    return AuthOut(bearer_token=session_token, username=user.username)


@app.post("/auth/login", response_model=AuthOut)
def login(payload: AuthIn, db: Session = Depends(get_db)):
    username = _normalize_username(payload.username)
    user = db.query(User).filter(User.username == username).first()
    if user is None or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    session_token = _start_session(db, user)
    return AuthOut(bearer_token=session_token, username=user.username)


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
        return None


@app.post("/saves/{save_code}/claim", response_model=SaveOut)
def claim_save(save_code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(Save).filter(Save.save_code == save_code).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Save code not found")
    row.user_id = current_user.id
    db.commit()
    db.refresh(row)
    return row


@app.get("/users/me/saves", response_model=List[SaveOut])
def list_my_saves(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Save).filter(Save.user_id == current_user.id).order_by(Save.updated_at.desc()).all()


# --- Site-wide feedback (ACCOUNTS-AND-FEEDBACK-DESIGN.md) ---
# Distinct from the Rating table above (the hub's star widget + each
# climate game's in-game feedback prompt): this is the newer,
# account-aware system that also covers feedback not tied to any game.

FEEDBACK_RATE_LIMIT_PER_HOUR = 5

# In-process only, per the design doc's own "keep it minimal for now"
# stance — resets on every deploy/restart and isn't shared across
# multiple server instances. Good enough to blunt casual spam; build a
# real (e.g. Redis-backed) limiter only if abuse actually shows up.
_feedback_submission_log: dict[str, list[float]] = {}


def _check_feedback_rate_limit(client_ip: str) -> None:
    now = time.time()
    window_start = now - 3600
    recent = [t for t in _feedback_submission_log.get(client_ip, []) if t > window_start]
    if len(recent) >= FEEDBACK_RATE_LIMIT_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many submissions — try again later")
    recent.append(now)
    _feedback_submission_log[client_ip] = recent


class FeedbackIn(BaseModel):
    game_id: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = None

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


@app.post("/feedback", response_model=FeedbackOut)
def create_feedback(
    payload: FeedbackIn,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    _check_feedback_rate_limit(request.client.host if request.client else "unknown")
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


@app.get("/feedback", response_model=List[FeedbackOut])
def list_feedback(response: Response, game_id: Optional[str] = None, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    query = db.query(Feedback).filter(Feedback.is_hidden.is_(False))
    query = query.filter(Feedback.game_id.is_(None)) if game_id is None else query.filter(Feedback.game_id == game_id)
    return query.order_by(Feedback.created_at.desc()).all()
