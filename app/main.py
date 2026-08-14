import os
import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import Base, engine, get_db, patch_schema
from models import Rating, Save

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

    class Config:
        from_attributes = True


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
