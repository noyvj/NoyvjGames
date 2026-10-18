"""A signed-in player's saves: claiming a save code, the save slots per game, and save snapshots.

Snapshots are the save "time machine" (see snapshots.py for the database helpers).
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import snapshots
from auth import get_current_user
from constants import ID_MAX_LENGTH
from database import get_db
from models import Save, SaveSnapshot, User
from rate_limits import SNAPSHOT_LIMITER
from schemas_saves import (
    _generate_save_code, SAVE_CODE_GENERATION_ATTEMPTS, SAVE_SLOTS_PER_GAME, SaveOut, SLOT_NAME_MAX_LENGTH,
)


router = APIRouter()


@router.post("/saves/{save_code}/claim", response_model=SaveOut)
def claim_save(save_code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(Save).filter(Save.save_code == save_code).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Save code not found")
    # An unclaimed save (user_id is None) can be claimed by anyone with the
    # code — that's the intended "claim your anonymous save" flow. But once
    # it's claimed, only the same account may claim it again (a harmless
    # no-op re-claim, e.g. a retried request); a save code that's already
    # someone else's must not be silently reassignable to a different
    # account, which is exactly what SAVE-SYSTEM-DESIGN.md's "nobody loses a
    # save by signing up" invariant is promising *not* to allow.
    if row.user_id is not None and row.user_id != current_user.id:
        raise HTTPException(status_code=409, detail="This save is already claimed by another account")
    if row.user_id is None:
        # U3: a newly claimed save takes the first free slot for its game.
        # With all slots taken it is refused rather than silently dropped
        # into a slot-less limbo; the player picks a slot to overwrite instead.
        _ensure_slots(db, current_user.id)
        taken = _taken_slots(db, current_user.id, row.game_id)
        free = [n for n in range(1, SAVE_SLOTS_PER_GAME + 1) if n not in taken]
        if not free:
            raise HTTPException(status_code=409, detail="All save slots for this game are full")
        row.slot = free[0]
        row.slot_name = f"Save {free[0]}"
    row.user_id = current_user.id
    db.commit()
    db.refresh(row)
    return row


# REVIEW(security), not yet resolved — flagged for a real decision rather
# than a unilateral fix, since it changes user-facing behavior: claiming a
# save doesn't restrict or rotate save_code — GET/PUT /saves/{save_code}
# (routes_core.py) stay open to anyone who still has the code, even after it's been
# claimed to an account. Whoever had the code before claiming keeps full
# read/write access indefinitely. Fixing this for real means deciding
# whether claiming should rotate the code (breaking anyone else who has it,
# including a legitimate "show a friend your save" use) or add a separate
# ownership check to GET/PUT themselves (which would end anonymous sharing
# of a claimed save's code entirely) — worth deciding deliberately, not
# guessing.
def _taken_slots(db: Session, user_id: str, game_id: str) -> set:
    rows = db.query(Save.slot).filter(Save.user_id == user_id, Save.game_id == game_id, Save.slot.isnot(None)).all()
    return {r[0] for r in rows}


def _ensure_slots(db: Session, user_id: str) -> None:
    """U3 migration, done lazily per account: claimed saves from before slots
    existed have no slot. Per game, the most recently updated becomes slot 1
    (the account's existing save keeps its place, nothing lost), the next
    ones fill slots 2 and 3, and any beyond that stay slot-less but are
    still listed."""
    unslotted = (
        db.query(Save)
        .filter(Save.user_id == user_id, Save.slot.is_(None))
        .order_by(Save.updated_at.desc())
        .all()
    )
    if not unslotted:
        return
    changed = False
    for row in unslotted:
        taken = _taken_slots(db, user_id, row.game_id)
        free = [n for n in range(1, SAVE_SLOTS_PER_GAME + 1) if n not in taken]
        if not free:
            continue
        row.slot = free[0]
        row.slot_name = row.slot_name or f"Save {free[0]}"
        db.flush()
        changed = True
    if changed:
        db.commit()


@router.get("/users/me/saves", response_model=List[SaveOut])
def list_my_saves(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    _ensure_slots(db, current_user.id)
    return db.query(Save).filter(Save.user_id == current_user.id).order_by(Save.updated_at.desc()).all()


class SlotSaveIn(BaseModel):
    save_data: dict
    name: Optional[str] = None


@router.put("/users/me/saves/{game_id}/slots/{slot}", response_model=SaveOut)
def put_slot_save(
    game_id: str,
    slot: int,
    payload: SlotSaveIn,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """U3: write this account's save for `game_id` into slot 1-3, creating it
    the first time and overwriting it after. The name is optional and only
    changes when given."""
    response.headers["Cache-Control"] = "no-store"
    if not 1 <= slot <= SAVE_SLOTS_PER_GAME:
        raise HTTPException(status_code=422, detail=f"slot must be from 1 to {SAVE_SLOTS_PER_GAME}")
    if not game_id or len(game_id) > ID_MAX_LENGTH:
        raise HTTPException(status_code=422, detail=f"game_id must be 1 to {ID_MAX_LENGTH} characters")
    name = None
    if payload.name is not None:
        name = payload.name.strip()[:SLOT_NAME_MAX_LENGTH] or None
    _ensure_slots(db, current_user.id)
    row = (
        db.query(Save)
        .filter(Save.user_id == current_user.id, Save.game_id == game_id, Save.slot == slot)
        .first()
    )
    if row is not None:
        row.save_data = payload.save_data
        if name:
            row.slot_name = name
        # Saving identical data changes no column, so onupdate would not fire and "latest save" could pick
        # the wrong slot: bump the timestamp explicitly.
        row.updated_at = func.now()
        db.commit()
        db.refresh(row)
        return row
    for _ in range(SAVE_CODE_GENERATION_ATTEMPTS):
        row = Save(
            save_code=_generate_save_code(), game_id=game_id, save_data=payload.save_data,
            user_id=current_user.id, slot=slot, slot_name=name or f"Save {slot}",
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(row)
        return row
    raise HTTPException(status_code=500, detail="Could not generate a unique save code — try again")


# --- Z-10: save snapshots (the save widget's "time machine") ---
# The last SNAPSHOTS_PER_SLOT automatic snapshots of this account's game state, per game and slot
# (slot 0 = no numbered slot active). The widget writes one before a Load / New Game / restore
# overwrites the current state and on autosave at most every 10 minutes; the list and the one-row
# fetch feed its "Restore an earlier state" list. Helpers and caps are in snapshots.py.


class SnapshotIn(BaseModel):
    game_id: str = Field(min_length=1, max_length=ID_MAX_LENGTH)
    slot: int = 0
    summary: Optional[str] = Field(default=None, max_length=1000)
    save_data: dict


def _snapshot_out(row: SaveSnapshot, with_data: bool = False) -> dict:
    out = snapshots.meta(row)
    if with_data:
        out["save_data"] = row.save_data
    return out


@router.post("/users/me/snapshots")
def create_snapshot(
    payload: SnapshotIn,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    if payload.slot not in snapshots.SLOT_RANGE:
        raise HTTPException(status_code=422, detail="slot must be from 0 to 3")
    if not payload.save_data:
        raise HTTPException(status_code=422, detail="An empty state is never snapshotted")
    if snapshots.json_size(payload.save_data) > snapshots.SNAPSHOT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="This state is too large to snapshot")
    if SNAPSHOT_LIMITER.blocked(current_user.id):
        raise HTTPException(status_code=429, detail="Too many snapshots, try again later")
    SNAPSHOT_LIMITER.record_failure(current_user.id)
    row = snapshots.add_snapshot(
        db, current_user.id, payload.game_id, payload.slot, payload.summary, payload.save_data)
    return _snapshot_out(row)


@router.get("/users/me/snapshots")
def list_snapshots(
    response: Response,
    game_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """This account's snapshots, newest first, without the state itself (fetch one by id)."""
    response.headers["Cache-Control"] = "no-store"
    return [_snapshot_out(r) for r in snapshots.list_for(db, current_user.id, game_id)]


def _own_snapshot(db: Session, user: User, snapshot_id: str) -> SaveSnapshot:
    row = db.query(SaveSnapshot).filter(SaveSnapshot.id == snapshot_id, SaveSnapshot.user_id == user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return row


@router.get("/users/me/snapshots/{snapshot_id}")
def get_snapshot(
    snapshot_id: str,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    return _snapshot_out(_own_snapshot(db, current_user, snapshot_id), with_data=True)


@router.delete("/users/me/snapshots/{snapshot_id}")
def delete_snapshot(
    snapshot_id: str,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    db.delete(_own_snapshot(db, current_user, snapshot_id))
    db.commit()
    return {"deleted": True}
