import os
from typing import List, Optional

from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Rating

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CodingIsANoyvj ratings API")

DEFAULT_ORIGINS = "https://icecreampuppy44.github.io,http://localhost:8073"
allowed_origins = os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class RatingIn(BaseModel):
    game_slug: str
    stars: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class RatingOut(BaseModel):
    id: int
    game_slug: str
    stars: int
    comment: Optional[str]

    class Config:
        from_attributes = True


@app.post("/ratings", response_model=RatingOut)
def create_rating(rating: RatingIn, db: Session = Depends(get_db)):
    row = Rating(game_slug=rating.game_slug, stars=rating.stars, comment=rating.comment)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.get("/ratings/{game_slug}", response_model=List[RatingOut])
def list_ratings(game_slug: str, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return db.query(Rating).filter(Rating.game_slug == game_slug).order_by(Rating.created_at.desc()).all()
