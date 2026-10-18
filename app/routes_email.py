"""The optional account email: GET/PUT /users/me/email."""

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User


router = APIRouter()


# --- U9: optional account email ---
EMAIL_MAX_LENGTH = 254
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmailIn(BaseModel):
    email: Optional[str] = None


@router.get("/users/me/email")
def get_my_email(response: Response, current_user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return {"email": current_user.email}


@router.put("/users/me/email")
def put_my_email(
    body: EmailIn,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add, change or remove (null or empty) this account's email."""
    response.headers["Cache-Control"] = "no-store"
    value = (body.email or "").strip().lower()
    if value:
        if len(value) > EMAIL_MAX_LENGTH or not _EMAIL_PATTERN.match(value):
            raise HTTPException(status_code=422, detail="That doesn't look like an email address")
    current_user.email = value or None
    db.commit()
    return {"email": current_user.email}
