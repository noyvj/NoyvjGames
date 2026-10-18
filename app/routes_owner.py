"""Owner-only notes: GET/PUT /owner/notes/{key} (the ideas sheet answers, game notes, playtest notes)."""

import json
import re

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from auth import get_current_user, OWNER_USERNAME, require_admin
from database import get_db
from models import OwnerNote, User


router = APIRouter()


# --- owner notes: small named JSON documents (the ideas page's answers) -------------------
# Written ONLY by the owner account (bearer token of OWNER_USERNAME); read by the owner or by
# anyone holding an admin token (the AI sessions' AI_ADMIN_TOKEN), via require_admin. Keys are
# a short fixed shape and the value size is capped, so this cannot become a general store.
OWNER_NOTE_KEY = re.compile(r"^[a-z0-9-]{1,40}$")
OWNER_NOTE_MAX_BYTES = 1_000_000


def require_owner(user: User = Depends(get_current_user)) -> User:
    if user.username != OWNER_USERNAME:
        raise HTTPException(status_code=403, detail="Owner account only")
    return user


def _owner_note_key(key: str) -> str:
    if not OWNER_NOTE_KEY.match(key):
        raise HTTPException(status_code=422, detail="Invalid note key")
    return key


@router.get("/owner/notes/{key}")
def get_owner_note(
    key: str,
    response: Response,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    row = db.get(OwnerNote, _owner_note_key(key))
    if row is None:
        return {"key": key, "value": None, "updated_at": None}
    return {
        "key": key,
        "value": json.loads(row.value_json),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.put("/owner/notes/{key}")
def put_owner_note(
    key: str,
    payload: dict,
    response: Response,
    _owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    key = _owner_note_key(key)
    if "value" not in payload:
        raise HTTPException(status_code=422, detail="Body must be {\"value\": ...}")
    text = json.dumps(payload["value"], separators=(",", ":"))
    if len(text.encode("utf-8")) > OWNER_NOTE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Note too large")
    row = db.get(OwnerNote, key)
    if row is None:
        db.add(OwnerNote(key=key, value_json=text))
    else:
        row.value_json = text
    db.commit()
    row = db.get(OwnerNote, key)
    return {"key": key, "updated_at": row.updated_at.isoformat() if row.updated_at else None}
