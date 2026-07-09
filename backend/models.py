from sqlalchemy import Column, DateTime, Integer, String, func

from database import Base


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True)
    game_slug = Column(String, nullable=False, index=True)
    stars = Column(Integer, nullable=False)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
