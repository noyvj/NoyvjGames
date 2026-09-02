import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, func

from database import Base


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True)
    game_slug = Column(String, nullable=False, index=True)
    # Nullable as of the climate-quartet feedback prompt (Canopy onward):
    # a feedback-prompt row has a `response` but no star rating, and the
    # hub's star-rating widget has a `stars` but no `response`. One row is
    # always at least one of the two — see RatingIn's validation.
    stars = Column(Integer, nullable=True)
    comment = Column(String, nullable=True)
    response = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Save(Base):
    """Save-System-Design.md Phase 1: save codes, no accounts. `id` is a
    Python-generated UUID string rather than Postgres' gen_random_uuid()
    so the type is portable to the sqlite engine the test suite uses —
    same effective uniqueness guarantee, no dialect-specific default.
    `save_data` uses the generic JSON type (stored as JSON, not JSONB) —
    the access pattern here is always a full fetch/overwrite by
    save_code, never a query into the JSON itself, so JSONB's indexing
    benefits don't apply and portable JSON is the simpler choice.
    """

    __tablename__ = "saves"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    save_code = Column(String, unique=True, nullable=False, index=True)
    game_id = Column(String, nullable=False, index=True)
    save_data = Column(JSON, nullable=False)
    # Nullable: a save starts anonymous and only gets a user_id if/when its
    # code is claimed via POST /saves/{save_code}/claim after sign-in.
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class User(Base):
    """ACCOUNTS-AND-FEEDBACK-DESIGN.md Phase 2, revised: username +
    password, not the original magic-link/email design — no email
    provider has been set up, and email accounts are deliberately
    deferred (see planning/ACCOUNTS-AND-FEEDBACK-DESIGN.md). `id` is a
    Python-generated UUID string for the same sqlite-portability reason
    as Save.id above. `username` is stored lowercased (main.py normalizes
    it before every read/write) so two logins that only differ by case
    can't create lookalike duplicate accounts. `password_hash` is never
    the plaintext password — see main.py's `_hash_password`.
    """

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuthSession(Base):
    """The bearer token returned by POST /auth/signup or /auth/login. A
    token has to be checkable against something on every later request,
    so this table is that something. Deliberately simple for MVP: no
    expiry, no rotation, no way to sign out other devices remotely —
    nothing currently invalidates an old bearer token early."""

    __tablename__ = "auth_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AnswerReport(Base):
    """Champ de Mots GRADING-AND-REVIEW-UPDATE.md §14.2.4: the "I think this
    should count" queue. Every written-answer prompt marked wrong can flag
    itself here, storing what was typed against what was marked correct. No
    auto-accept, ever, and no in-game admin UI (champ-de-mots/CLAUDE.md §14.4)
    — a human lists/filters this table directly (GET /answer-reports) and,
    for a genuine miss, hand-adds the phrasing to that catalog item's
    `accepted_fr`/`accepted_en` array themselves (see champ-de-mots/CLAUDE.md's
    Milestone 8 build note) before redeploying. `id` is a Python-generated
    UUID string for the same sqlite-portability reason as Save.id/User.id
    above. `game_id` defaults to this game but isn't hardcoded to it, in case
    another game ever wants the same reporting mechanism. `marked_correct_answer`
    is a JSON list (there can be more than one accepted phrasing already).
    """

    __tablename__ = "answer_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id = Column(String, nullable=False, index=True)
    item_id = Column(String, nullable=False, index=True)
    submitted_answer = Column(String, nullable=False)
    marked_correct_answer = Column(JSON, nullable=False)
    topic_type = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Feedback(Base):
    """ACCOUNTS-AND-FEEDBACK-DESIGN.md's site-wide feedback: usable either
    attached to a game (game_id set) or as general site feedback
    (game_id null). Distinct from the pre-existing Rating table above,
    which is the hub's star-rating widget + the climate games' in-game
    feedback prompt — this is the newer, account-aware, site-wide system."""

    __tablename__ = "feedback"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id = Column(String, nullable=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    rating = Column(Integer, nullable=True)
    comment = Column(String, nullable=True)
    is_hidden = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
