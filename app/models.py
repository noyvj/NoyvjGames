import uuid

from sqlalchemy import Text, JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, false, func

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
    # Admin "this is a test, hide it" flag: hidden rows are skipped by the
    # public GET /ratings/{slug} but still listed (with the flag) to admin.
    is_hidden = Column(Boolean, nullable=False, default=False, server_default=false())
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
    # U3: signed-in accounts get up to SAVE_SLOTS_PER_GAME numbered slots per
    # game. NULL slot = an anonymous save, or a claimed one not yet slotted.
    slot = Column(Integer, nullable=True)
    slot_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SaveSnapshot(Base):
    """Z-10, the save "time machine": the last few automatic snapshots of a signed-in player's
    game state, taken by the save widget just before something overwrites it (Load, New Game,
    a restore) and on autosave. Capped to SNAPSHOTS_PER_SLOT per (account, game, slot) by
    deleting the oldest (see snapshots.py). `slot` is 1-3 for a numbered save slot and 0 when
    no slot was active. `size` is the JSON size in bytes and `summary` a one-line description
    the widget made. A brand-new table, so create_all builds it and patch_schema() needs no
    statement. Removed with the account (account_data.delete_account) and part of its export."""

    __tablename__ = "save_snapshots"
    __table_args__ = (Index("ix_save_snapshots_owner", "user_id", "game_id", "slot"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    game_id = Column(String, nullable=False)
    slot = Column(Integer, nullable=False, default=0, server_default="0")
    size = Column(Integer, nullable=False, default=0, server_default="0")
    summary = Column(String, nullable=True)
    save_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


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
    # Y31: this account's site-wide preferences (theme, text scale, reduced
    # motion) as a JSON string. Nullable: NULL means "never synced", which
    # clients treat as "keep whatever this device has". Only main.py's
    # whitelist validation ever writes it, so it never holds anything else.
    settings_json = Column(Text, nullable=True)
    # U9: optional email, used only so the site owner can verify a password-
    # reset request by hand. Visible to the admin, never to other players and
    # never in any public stat. NULL = none given.
    email = Column(String, nullable=True)
    # U7: marks an account (and, via user_id, its saves) as test data, hidden
    # from the admin view by default and excluded from the public stats.
    is_test = Column(Boolean, nullable=False, default=False, server_default=false())


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
    # U6: an admin marks a report done once it has been dealt with. Set only by
    # the admin-token-protected PATCH /answer-reports/{id}.
    is_resolved = Column(Boolean, nullable=False, default=False, server_default=false())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    # "Fixed" is separate from "done": done means the owner has dealt with a
    # report; fixed means the game's data or code was actually changed because
    # of it (set with PATCH /answer-reports/{id}/fixed, which also takes the AI
    # admin token, so the AI session can tick it itself and say what it did).
    is_fixed = Column(Boolean, nullable=False, default=False, server_default=false())
    fixed_note = Column(String, nullable=True)
    fixed_at = Column(DateTime(timezone=True), nullable=True)


class Feedback(Base):
    """ACCOUNTS-AND-FEEDBACK-DESIGN.md's site-wide feedback: usable either
    attached to a game (game_id set) or as general site feedback
    (game_id null). Distinct from the pre-existing Rating table above,
    which is the hub's star-rating widget + the climate games' in-game
    feedback prompt — this is the newer, account-aware, site-wide system."""

    __tablename__ = "feedback"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id = Column(String, nullable=True, index=True)
    # Indexed (patch_schema() adds it to the live table): account export and
    # deletion filter feedback by user.
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    rating = Column(Integer, nullable=True)
    comment = Column(String, nullable=True)
    is_hidden = Column(Boolean, nullable=False, default=False, server_default=false())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LeaderboardEntry(Base):
    """Opt-in community leaderboards (see leaderboards.py): one row per
    (game, board, account) holding that account's best score. A row exists
    only because the player chose to submit it; deleting it is opting out."""

    __tablename__ = "leaderboard_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id = Column(String, nullable=False, index=True)
    board = Column(String, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    detail = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PoolDay(Base):
    """One community pool's running total for one UTC day (see pools.py):
    anonymous, no account or address is stored."""

    __tablename__ = "pool_days"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id = Column(String, nullable=False, index=True)
    pool = Column(String, nullable=False, index=True)
    day = Column(String, nullable=False, index=True)  # "YYYY-MM-DD" (UTC)
    total = Column(Float, nullable=False, default=0.0)
    contributions = Column(Integer, nullable=False, default=0)


class PageView(Base):
    """Y29 (planning/TODO.md): one row per opt-in hub visit -- a plain
    row-count table rather than a single incrementing counter row, so a
    POST is a plain insert with no read-modify-write race to worry about.
    Deliberately carries nothing else: no IP, user agent, path, or session
    identifier, per Y29's own "not a third-party tracker" requirement --
    a row's mere existence is the entire signal."""

    __tablename__ = "pageviews"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OwnerNote(Base):
    """A small named JSON document that belongs to the site owner (for now: the ideas page's
    answers, key "ideas-answers"). Written only by the owner account, readable by the owner
    and by the AI sessions' admin token, so answers typed on the site do not need exporting by
    hand. One row per key; the value is stored as JSON text and capped in size by the endpoint."""

    __tablename__ = "owner_notes"

    key = Column(String, primary_key=True)
    value_json = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ScoreEntry(Base):
    """General opt-in board rows (see boards.py): one row per (game, board,
    account, window, period) holding that account's best score in that window.
    A row exists only because the player opted in; the table stores the account
    id (never shown) and the score. `window` is daily/weekly/alltime and
    `period` the UTC date, ISO week or "all". `is_hidden` is the admin's "this is
    a test, hide it" flag: hidden rows vanish from the public board, its ranks
    and its small-group count."""

    __tablename__ = "score_entries"
    __table_args__ = (
        UniqueConstraint("game_id", "board", "user_id", "window", "period", name="uq_score_entry"),
        Index("ix_score_entries_board_window", "game_id", "board", "window", "period"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id = Column(String, nullable=False)
    board = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    window = Column(String, nullable=False)
    period = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    detail = Column(String, nullable=True)
    is_hidden = Column(Boolean, nullable=False, default=False, server_default=false())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ScoreProfile(Base):
    """The one account-level board setting: show the username instead of an
    anonymous 'Player 7F2Q' handle. A separate small table (not a users column)
    so the live database needs no schema patch. No row means the default: anonymous."""

    __tablename__ = "score_profiles"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    show_username = Column(Boolean, nullable=False, default=False, server_default=false())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HelpfulVote(Base):
    """Y-24: the "was this helpful?" thumbs on a What's New entry. One row per
    (entry, voter): `voter_key` is "u:<user id>" for a signed-in account or
    "a:<token>" for an anonymous browser (a random string the browser makes up;
    it identifies nothing). Voting again changes the vote, never adds a second.
    `user_id` is set only for account votes, so deleting the account removes them
    and the admin tallies can leave test accounts out. A brand-new table, so
    create_all builds it and no patch_schema() statement is needed."""

    __tablename__ = "helpful_votes"
    __table_args__ = (UniqueConstraint("entry_id", "voter_key", name="uq_helpful_vote"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    entry_id = Column(String, nullable=False, index=True)
    voter_key = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    helpful = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
