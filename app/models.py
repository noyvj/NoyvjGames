import uuid

from sqlalchemy import JSON, Column, DateTime, Integer, String, func

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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
