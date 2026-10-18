"""In-game 'Report a problem' reports: POST /bug-reports and the admin triage routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

import bug_reports
from auth import get_current_user_optional, require_admin
from database import get_db
from models import BugReport, User
from rate_limits import _throttle, BUG_REPORT_LIMITER


router = APIRouter()


# --- Z-17: in-game "Report a problem" (shared/report-problem.js) ---
# Public POST (rate limited per address, every field size-limited in bug_reports.py), admin-only
# list and triage. The widget previews exactly what it will send and sends optional parts only when
# the player ticked them; the server just stores what arrives, so a null field means "not attached".


@router.post("/bug-reports")
def create_bug_report(
    payload: bug_reports.BugReportIn,
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    _throttle(BUG_REPORT_LIMITER, request, "Too many reports from this address, try again later")
    row = BugReport(
        game_id=payload.game_id,
        page=payload.page,
        note=payload.note,
        schema_version=payload.schema_version,
        browser=payload.browser,
        viewport=payload.viewport,
        console_log=payload.console_log,
        attachment=payload.attachment,
        # Linked only when the player asked for it AND is signed in; otherwise the report is anonymous.
        user_id=current_user.id if (payload.link_account and current_user is not None) else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "received": True}


@router.get("/admin/bug-reports", response_model=List[bug_reports.BugReportAdminOut])
def admin_list_bug_reports(
    response: Response,
    game_id: Optional[str] = None,
    resolved: Optional[bool] = None,
    fixed: Optional[bool] = None,
    limit: int = 200,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Newest first, with the linked username when the player chose to link the report."""
    response.headers["Cache-Control"] = "no-store"
    limit = max(1, min(bug_reports.LIST_LIMIT_MAX, limit))
    query = db.query(BugReport)
    if game_id is not None:
        query = query.filter(BugReport.game_id == game_id)
    if resolved is not None:
        query = query.filter(BugReport.is_resolved.is_(resolved))
    if fixed is not None:
        query = query.filter(BugReport.is_fixed.is_(fixed))
    rows = query.order_by(BugReport.created_at.desc(), BugReport.id).limit(limit).all()
    ids = {r.user_id for r in rows if r.user_id}
    names = dict(db.query(User.id, User.username).filter(User.id.in_(ids)).all()) if ids else {}
    return [bug_reports.admin_out(r, names.get(r.user_id)) for r in rows]


@router.patch("/admin/bug-reports/{report_id}", response_model=bug_reports.BugReportAdminOut)
def admin_patch_bug_report(
    report_id: str,
    body: bug_reports.BugReportPatch,
    response: Response,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Tick or untick resolved (the owner dealt with it) and fixed (a change was made because of it,
    with an optional one-line note), exactly like the answer reports. Only the keys sent change."""
    response.headers["Cache-Control"] = "no-store"
    row = db.query(BugReport).filter(BugReport.id == report_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if body.resolved is not None:
        row.is_resolved = body.resolved
        row.resolved_at = func.now() if body.resolved else None
    if body.fixed is not None:
        row.is_fixed = body.fixed
        row.fixed_at = func.now() if body.fixed else None
        row.fixed_note = ((body.note or "").strip()[: bug_reports.FIXED_NOTE_MAX_LENGTH] or None) if body.fixed else None
    db.commit()
    db.refresh(row)
    username = db.query(User.username).filter(User.id == row.user_id).scalar() if row.user_id else None
    return bug_reports.admin_out(row, username)
