import os
from typing import List, Optional

from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from database import Base, engine, get_db, patch_schema
from models import Rating

Base.metadata.create_all(bind=engine)
patch_schema()

app = FastAPI(title="CodingIsANoyvj ratings API")

DEFAULT_ORIGINS = "https://noyvj.github.io,http://localhost:8073"
allowed_origins = os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
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

    class Config:
        from_attributes = True


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
