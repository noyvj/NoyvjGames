from sqlalchemy import Column, DateTime, Integer, String, func

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
