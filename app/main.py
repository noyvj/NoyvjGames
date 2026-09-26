import hashlib
import json
import logging
import os
import secrets
import threading
import time
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import stats
from database import Base, engine, get_db, patch_schema
from models import AnswerReport, AuthSession, Feedback, PageView, Rating, Save, User

logger = logging.getLogger(__name__)

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
        "".join(chars[i:i + SAVE_CODE_GROUP_LEN])
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


# --- Champ de Mots answer reports (GRADING-AND-REVIEW-UPDATE.md §14.2.4) ---
# The "I think this should count" queue: a written answer marked wrong can
# flag itself here. No auto-accept and no in-game admin UI (§14.4's decision)
# — reports are triaged by listing/filtering this table directly, and a
# genuine miss gets hand-added to that catalog item's `accepted_fr`/
# `accepted_en` array (champ-de-mots/CLAUDE.md's Milestone 8 build note).

DEFAULT_ANSWER_REPORT_GAME_ID = "champ-de-mots"


class AnswerReportIn(BaseModel):
    game_id: str = DEFAULT_ANSWER_REPORT_GAME_ID
    item_id: str
    submitted_answer: str
    marked_correct_answer: List[str]
    topic_type: Optional[str] = None

    @model_validator(mode="after")
    def require_the_essentials(self):
        if not self.item_id.strip():
            raise ValueError("item_id is required")
        if not self.submitted_answer.strip():
            raise ValueError("submitted_answer is required")
        if not self.marked_correct_answer:
            raise ValueError("marked_correct_answer must contain at least one answer")
        return self


class AnswerReportOut(BaseModel):
    id: str
    game_id: str
    item_id: str
    submitted_answer: str
    marked_correct_answer: List[str]
    topic_type: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@app.post("/answer-reports", response_model=AnswerReportOut)
def create_answer_report(payload: AnswerReportIn, db: Session = Depends(get_db)):
    row = AnswerReport(
        game_id=payload.game_id,
        item_id=payload.item_id,
        submitted_answer=payload.submitted_answer,
        marked_correct_answer=payload.marked_correct_answer,
        topic_type=payload.topic_type,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.get("/answer-reports", response_model=List[AnswerReportOut])
def list_answer_reports(
    response: Response,
    game_id: Optional[str] = None,
    topic_type: Optional[str] = None,
    item_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    query = db.query(AnswerReport)
    if game_id is not None:
        query = query.filter(AnswerReport.game_id == game_id)
    if topic_type is not None:
        query = query.filter(AnswerReport.topic_type == topic_type)
    if item_id is not None:
        query = query.filter(AnswerReport.item_id == item_id)
    return query.order_by(AnswerReport.created_at.desc()).all()


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
        # A malformed stored_hash (bad migration, hand-edited row) is a
        # server-side data problem, not a user typing the wrong password —
        # worth its own log line so the two failure modes don't get
        # conflated when someone's login reports keep failing.
        logger.warning("_verify_password: stored_hash is malformed, treating as a failed login", exc_info=True)
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


@app.post("/auth/signup", response_model=AuthOut)
def signup(payload: AuthIn, db: Session = Depends(get_db)):
    username = _normalize_username(payload.username)
    if _username_exists(db, username):
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(username=username, password_hash=_hash_password(payload.password))
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
        # Logged at debug (not warning) because a garbage/expired token here
        # is routine, not exceptional — this dependency exists specifically
        # so an optional-auth endpoint degrades to anonymous rather than
        # erroring. Kept as a log line rather than nothing, though, so a
        # signed-in user whose requests keep silently landing as anonymous
        # has a server-side trail to check.
        logger.debug("get_current_user_optional: treating request as anonymous, auth failed", exc_info=True)
        return None


@app.post("/saves/{save_code}/claim", response_model=SaveOut)
def claim_save(save_code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(Save).filter(Save.save_code == save_code).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Save code not found")
    # An unclaimed save (user_id is None) can be claimed by anyone with the
    # code — that's the intended "claim your anonymous save" flow. But once
    # it's claimed, only the same account may claim it again (a harmless
    # no-op re-claim, e.g. a retried request); a save code that's already
    # someone else's must not be silently reassignable to a different
    # account, which is exactly what SAVE-SYSTEM-DESIGN.md's "nobody loses a
    # save by signing up" invariant is promising *not* to allow.
    if row.user_id is not None and row.user_id != current_user.id:
        raise HTTPException(status_code=409, detail="This save is already claimed by another account")
    row.user_id = current_user.id
    db.commit()
    db.refresh(row)
    return row


# REVIEW(security), not yet resolved — flagged for a real decision rather
# than a unilateral fix, since it changes user-facing behavior: claiming a
# save doesn't restrict or rotate save_code — GET/PUT /saves/{save_code}
# above stay open to anyone who still has the code, even after it's been
# claimed to an account. Whoever had the code before claiming keeps full
# read/write access indefinitely. Fixing this for real means deciding
# whether claiming should rotate the code (breaking anyone else who has it,
# including a legitimate "show a friend your save" use) or add a separate
# ownership check to GET/PUT themselves (which would end anonymous sharing
# of a claimed save's code entirely) — worth deciding deliberately, not
# guessing.
@app.get("/users/me/saves", response_model=List[SaveOut])
def list_my_saves(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return db.query(Save).filter(Save.user_id == current_user.id).order_by(Save.updated_at.desc()).all()


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


@app.get("/users/me/settings")
def get_my_settings(response: Response, current_user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return {"settings": _stored_settings(current_user)}


@app.put("/users/me/settings")
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


# --- Site-wide feedback (ACCOUNTS-AND-FEEDBACK-DESIGN.md) ---
# Distinct from the Rating table above (the hub's star widget + each
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


# --- Admin aggregate stats (TODO.md L8) ---
# Backs the unlisted admin.html page's Overview panel. `admin.html`'s own
# comment already establishes the precedent this follows: every number
# here is a count, never a row of actual user content (no usernames,
# emails, save contents, or comment text) — accounts and saves had no
# aggregate-count endpoint before this, only per-user (/users/me/saves)
# or per-code (/saves/{code}) lookups, neither of which can answer "how
# many, total". Unauthenticated and public like every other endpoint
# admin.html already calls, for the same reason: a bare count isn't
# meaningfully sensitive at this site's scale, and gating it behind auth
# would need inventing an admin-role concept (there isn't one — see
# models.py's User) for very little actual protection.
class AdminStatsOut(BaseModel):
    total_users: int
    total_saves: int
    saves_by_game: dict[str, int]


@app.get("/admin/stats", response_model=AdminStatsOut)
def admin_stats(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_saves = db.query(func.count(Save.id)).scalar() or 0
    saves_by_game = dict(
        db.query(Save.game_id, func.count(Save.id)).group_by(Save.game_id).all()
    )
    return AdminStatsOut(total_users=total_users, total_saves=total_saves, saves_by_game=saves_by_game)


# --- Cross-game aggregate stats (TODO.md Z1) ---
# Public, read-only, aggregates only: no usernames, save codes, raw saves or
# any string from a save ever leaves this section. See stats.py for the
# privacy rules (small-N suppression at MIN_BUCKET, no min/max) and for the
# per-game STATS_FIELDS whitelist games opt numeric fields into. Reads the
# existing `saves` table only — zero per-game backend changes. One SELECT of
# just `save_data` for the game (newest MAX_SAVES_SCANNED), decoded and
# aggregated in Python because the blobs are opaque, possibly adversarial
# JSON that portable SQL can't safely cast; cached per game in-process.
STATS_CACHE_CONTROL = "public, max-age=300"


def _game_saves(db: Session, game_id: str) -> list:
    cached = stats.cache_get(game_id)
    if cached is not None:
        return cached
    rows = (
        db.query(Save.save_data)
        .filter(Save.game_id == game_id)
        .order_by(Save.updated_at.desc())
        .limit(stats.MAX_SAVES_SCANNED)
        .all()
    )
    saves = [r[0] for r in rows]
    stats.cache_put(game_id, saves)
    return saves


def _require_known_game(game_id: str) -> None:
    if game_id not in stats.STATS_FIELDS:
        raise HTTPException(status_code=404, detail="Unknown game")


@app.get("/stats/games")
def stats_games(response: Response):
    response.headers["Cache-Control"] = STATS_CACHE_CONTROL
    return {
        "min_bucket": stats.MIN_BUCKET,
        "games": {g: list(f) for g, f in stats.STATS_FIELDS.items()},
    }


@app.get("/stats/games/{game_id}")
def stats_game(game_id: str, response: Response, db: Session = Depends(get_db)):
    _require_known_game(game_id)
    response.headers["Cache-Control"] = STATS_CACHE_CONTROL
    return stats.summarize_game(game_id, _game_saves(db, game_id))


@app.get("/stats/games/{game_id}/percentile")
def stats_game_percentile(
    game_id: str, field: str, value: float, response: Response, db: Session = Depends(get_db)
):
    _require_known_game(game_id)
    if field not in stats.STATS_FIELDS[game_id]:
        raise HTTPException(status_code=404, detail="Field is not enabled for stats")
    if value != value or value in (float("inf"), float("-inf")):
        raise HTTPException(status_code=422, detail="value must be a finite number")
    response.headers["Cache-Control"] = STATS_CACHE_CONTROL
    values = stats.field_values(_game_saves(db, game_id), field)
    if len(values) < stats.MIN_BUCKET:
        return {"game_id": game_id, "field": field, "suppressed": True, "min_bucket": stats.MIN_BUCKET, "count": None, "percentile": None}
    return {
        "game_id": game_id,
        "field": field,
        "suppressed": False,
        "min_bucket": stats.MIN_BUCKET,
        "count": len(values),
        "percentile": stats.percentile_of(values, value),
    }


@app.get("/stats/achievements")
def stats_achievements(response: Response, db: Session = Depends(get_db)):
    """Every game's achievement rarity in one call (the hub dashboard case)."""
    response.headers["Cache-Control"] = STATS_CACHE_CONTROL
    out = {}
    for game_id in stats.known_games():
        summary = stats.summarize_game(game_id, _game_saves(db, game_id))
        out[game_id] = {
            "suppressed": summary["suppressed"],
            "save_count": summary["save_count"],
            "achievements": summary["achievements"],
        }
    return {"min_bucket": stats.MIN_BUCKET, "games": out}


@app.post("/stats/pageview")
def stats_pageview(db: Session = Depends(get_db)):
    """Y29: records one opt-in hub visit and returns the running total.
    No identifying detail is ever taken from the request -- a bare insert,
    then a count(*), is the entire implementation."""
    db.add(PageView())
    db.commit()
    total = db.query(PageView).count()
    return {"total": total}
