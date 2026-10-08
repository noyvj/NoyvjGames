"""Z-10: the save "time machine" (backend half). Pure database helpers; main.py owns the routes,
authentication and rate limiting.

A snapshot is a copy of a game's state the save widget took just before something overwrote it
(Load, New Game, a restore) or on a slow autosave. Each (account, game, slot) keeps the newest
SNAPSHOTS_PER_SLOT, so taking a sixth deletes the oldest. `slot` 0 means no numbered slot was
active. The whole account is also capped (MAX_SNAPSHOTS_PER_ACCOUNT) so arbitrary game ids cannot
grow the table without bound.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import SaveSnapshot

SNAPSHOTS_PER_SLOT = 5
MAX_SNAPSHOTS_PER_ACCOUNT = 300  # 15 games x 4 slot values x 5, with a little room
SNAPSHOT_MAX_BYTES = 1_000_000   # a larger state is refused (the save itself still works)
SUMMARY_MAX_LENGTH = 200
SLOT_RANGE = range(0, 4)         # 0 = no numbered slot, 1-3 = a save slot


def json_size(data) -> int:
    return len(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def clean_summary(text: Optional[str]) -> Optional[str]:
    """One line, trimmed, at most SUMMARY_MAX_LENGTH characters."""
    if text is None:
        return None
    one_line = " ".join(str(text).split())
    return one_line[:SUMMARY_MAX_LENGTH] or None


def meta(row: SaveSnapshot) -> dict:
    return {
        "id": row.id, "game_id": row.game_id, "slot": row.slot, "size": row.size,
        "summary": row.summary, "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_for(db: Session, user_id: str, game_id: Optional[str] = None) -> list:
    query = db.query(SaveSnapshot).filter(SaveSnapshot.user_id == user_id)
    if game_id:
        query = query.filter(SaveSnapshot.game_id == game_id)
    return query.order_by(SaveSnapshot.created_at.desc(), SaveSnapshot.id).all()


def add_snapshot(db: Session, user_id: str, game_id: str, slot: int, summary: Optional[str], data: dict) -> SaveSnapshot:
    """Stores a snapshot, then deletes whatever is beyond the per-slot and per-account caps
    (oldest first). Taking the same state twice in a row for a slot is a no-op that returns the
    existing newest row, so a retried request never makes a duplicate."""
    newest = (
        db.query(SaveSnapshot)
        .filter(SaveSnapshot.user_id == user_id, SaveSnapshot.game_id == game_id, SaveSnapshot.slot == slot)
        .order_by(SaveSnapshot.created_at.desc())
        .first()
    )
    if newest is not None and newest.save_data == data:
        return newest
    row = SaveSnapshot(
        user_id=user_id, game_id=game_id, slot=slot, size=json_size(data),
        summary=clean_summary(summary), save_data=data, created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    stale = (
        db.query(SaveSnapshot)
        .filter(SaveSnapshot.user_id == user_id, SaveSnapshot.game_id == game_id, SaveSnapshot.slot == slot)
        .order_by(SaveSnapshot.created_at.desc(), SaveSnapshot.id)
        .offset(SNAPSHOTS_PER_SLOT)
        .all()
    )
    for old in stale:
        db.delete(old)
    over = (
        db.query(SaveSnapshot)
        .filter(SaveSnapshot.user_id == user_id)
        .order_by(SaveSnapshot.created_at.desc(), SaveSnapshot.id)
        .offset(MAX_SNAPSHOTS_PER_ACCOUNT)
        .all()
    )
    for old in over:
        if old is not row:
            db.delete(old)
    db.commit()
    db.refresh(row)
    return row
