"""Save-code constants and the request/response models shared by the save routes. Layer 2."""

import secrets
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from constants import ID_MAX_LENGTH


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
        "".join(chars[i:i + SAVE_CODE_GROUP_LEN])
        for i in range(0, len(chars), SAVE_CODE_GROUP_LEN)
    ]
    return "-".join(groups)


class SaveIn(BaseModel):
    game_id: str = Field(max_length=ID_MAX_LENGTH)
    save_data: dict


class SaveUpdate(BaseModel):
    save_data: dict


SAVE_SLOTS_PER_GAME = 3
SLOT_NAME_MAX_LENGTH = 40


class SaveOut(BaseModel):
    save_code: str
    game_id: str
    slot: Optional[int] = None
    slot_name: Optional[str] = None
    save_data: dict
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
