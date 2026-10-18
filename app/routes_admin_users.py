"""Admin account list and the test-account flag: GET /admin/users, PATCH /admin/users/{user_id}."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, StrictBool
from sqlalchemy import func
from sqlalchemy.orm import Session

import stats
from auth import require_admin
from database import get_db
from models import Save, User


router = APIRouter()


# --- U7: admin account list + test-data flag ---
class AdminUserOut(BaseModel):
    id: str
    username: str
    email: Optional[str]
    is_test: StrictBool
    created_at: Optional[datetime]
    save_count: int


class UserTestFlagIn(BaseModel):
    is_test: StrictBool


@router.get("/admin/users", response_model=List[AdminUserOut])
def admin_list_users(
    response: Response,
    include_test: bool = True,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Every account, newest first, with its email (the admin needs it to
    verify reset requests) and save count. Admin-token only."""
    response.headers["Cache-Control"] = "no-store"
    counts = dict(db.query(Save.user_id, func.count(Save.id)).filter(Save.user_id.isnot(None)).group_by(Save.user_id).all())
    query = db.query(User)
    if not include_test:
        query = query.filter(User.is_test.is_(False))
    users = query.order_by(User.created_at.desc()).all()
    return [
        AdminUserOut(
            id=u.id, username=u.username, email=u.email, is_test=bool(u.is_test),
            created_at=u.created_at, save_count=counts.get(u.id, 0),
        )
        for u in users
    ]


@router.patch("/admin/users/{user_id}", response_model=AdminUserOut)
def admin_flag_user(
    user_id: str,
    body: UserTestFlagIn,
    response: Response,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found")
    user.is_test = body.is_test
    db.commit()
    stats.cache_clear()  # the public aggregates must not keep counting a now-flagged account
    count = db.query(func.count(Save.id)).filter(Save.user_id == user.id).scalar() or 0
    return AdminUserOut(
        id=user.id, username=user.username, email=user.email, is_test=bool(user.is_test),
        created_at=user.created_at, save_count=count,
    )
