"""Champ de Mots answer reports ("I think this should count") and their admin triage routes."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import require_admin
from constants import ID_MAX_LENGTH
from database import get_db
from models import AnswerReport
from rate_limits import _throttle, ANSWER_REPORT_LIMITER


router = APIRouter()


# --- Champ de Mots answer reports (GRADING-AND-REVIEW-UPDATE.md §14.2.4) ---
# The "I think this should count" queue: a written answer marked wrong can
# flag itself here. No auto-accept and no in-game admin UI (§14.4's decision)
# — reports are triaged by listing/filtering this table directly, and a
# genuine miss gets hand-added to that catalog item's `accepted_fr`/
# `accepted_en` array (champ-de-mots/CLAUDE.md's Milestone 8 build note).

DEFAULT_ANSWER_REPORT_GAME_ID = "champ-de-mots"


class AnswerReportIn(BaseModel):
    game_id: str = Field(default=DEFAULT_ANSWER_REPORT_GAME_ID, max_length=ID_MAX_LENGTH)
    item_id: str = Field(max_length=200)
    submitted_answer: str = Field(max_length=500)
    marked_correct_answer: List[str] = Field(max_length=20)
    topic_type: Optional[str] = Field(default=None, max_length=ID_MAX_LENGTH)

    @model_validator(mode="after")
    def require_the_essentials(self):
        if not self.item_id.strip():
            raise ValueError("item_id is required")
        if not self.submitted_answer.strip():
            raise ValueError("submitted_answer is required")
        if not self.marked_correct_answer:
            raise ValueError("marked_correct_answer must contain at least one answer")
        if any(len(answer) > 500 for answer in self.marked_correct_answer):
            raise ValueError("each marked_correct_answer entry must be at most 500 characters")
        return self


class AnswerReportOut(BaseModel):
    id: str
    game_id: str
    item_id: str
    submitted_answer: str
    marked_correct_answer: List[str]
    topic_type: Optional[str]
    created_at: datetime
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    is_fixed: bool = False
    fixed_note: Optional[str] = None
    fixed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReportResolveIn(BaseModel):
    resolved: bool


class ReportFixedIn(BaseModel):
    fixed: bool
    note: Optional[str] = None


@router.post("/answer-reports", response_model=AnswerReportOut)
def create_answer_report(payload: AnswerReportIn, request: Request, db: Session = Depends(get_db)):
    _throttle(ANSWER_REPORT_LIMITER, request)
    row = AnswerReport(
        game_id=payload.game_id,
        item_id=payload.item_id,
        submitted_answer=payload.submitted_answer,
        marked_correct_answer=payload.marked_correct_answer,
        topic_type=payload.topic_type,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/answer-reports", response_model=List[AnswerReportOut])
def list_answer_reports(
    response: Response,
    _admin: None = Depends(require_admin),
    game_id: Optional[str] = None,
    topic_type: Optional[str] = None,
    item_id: Optional[str] = None,
    resolved: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    query = db.query(AnswerReport)
    if resolved is not None:
        query = query.filter(AnswerReport.is_resolved.is_(resolved))
    if game_id is not None:
        query = query.filter(AnswerReport.game_id == game_id)
    if topic_type is not None:
        query = query.filter(AnswerReport.topic_type == topic_type)
    if item_id is not None:
        query = query.filter(AnswerReport.item_id == item_id)
    return query.order_by(AnswerReport.created_at.desc()).all()


@router.patch("/answer-reports/{report_id}", response_model=AnswerReportOut)
def resolve_answer_report(
    report_id: str,
    body: ReportResolveIn,
    response: Response,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """U6: mark a report done (or reopen it). Admin-token only."""
    response.headers["Cache-Control"] = "no-store"
    row = db.query(AnswerReport).filter(AnswerReport.id == report_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")
    row.is_resolved = body.resolved
    row.resolved_at = func.now() if body.resolved else None
    db.commit()
    db.refresh(row)
    return row


@router.patch("/answer-reports/{report_id}/fixed", response_model=AnswerReportOut)
def mark_answer_report_fixed(
    report_id: str,
    body: ReportFixedIn,
    response: Response,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Tick or untick "fixed" on a report, with a one-line note of what changed.
    Admin token (owner bearer or the AI token) only. Does not touch `is_resolved`."""
    response.headers["Cache-Control"] = "no-store"
    row = db.query(AnswerReport).filter(AnswerReport.id == report_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")
    row.is_fixed = body.fixed
    row.fixed_note = (body.note or "").strip()[:300] or None if body.fixed else None
    row.fixed_at = func.now() if body.fixed else None
    db.commit()
    db.refresh(row)
    return row
