"""Admin time series: GET /admin/timeseries."""

from typing import Optional

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

import account_data
from auth import require_admin
from database import get_db


router = APIRouter()


# --- Y-13: admin daily time series ---


@router.get("/admin/timeseries")
def admin_timeseries(
    response: Response,
    days: Optional[int] = None,
    hide_test: bool = True,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Daily counts (UTC dates, zero-filled) of plays, new saves, sign-ups,
    feedback, ratings, answer reports and counted visits for the last 7 to 90
    days (default 30). Counts only, never rows. Test accounts and hidden rows
    are left out unless hide_test=false."""
    response.headers["Cache-Control"] = "no-store"
    return account_data.timeseries(db, days, hide_test)
