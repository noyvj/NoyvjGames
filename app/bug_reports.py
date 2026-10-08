"""Z-17: in-game "Report a problem" reports (the shared/report-problem.js widget posts here).

The routes, authentication and rate limiting are in main.py; this module holds the request model
(with every size limit), the scrubbing of anything that looks like a secret, and the admin view.

What a report can hold, and why each field is safe to keep:
  * game_id, page (path only), note, schema_version: always sent, shown in the widget's preview.
  * browser, viewport, console_log (<= 20 lines of <= 300 characters), attachment: null unless the
    player ticked the matching box. The attachment object accepts exactly one key, "save_code",
    in the site's save-code shape; anything else is refused, so the column cannot become a dump.
  * user_id: set only when the player was signed in AND ticked "link this to my account".
Console lines are scrubbed on the way in as a second line of defence (the widget scrubs them too):
bearer tokens, token-looking query values, save codes and email addresses are replaced with a marker.
"""

import re
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

ID_MAX_LENGTH = 64
NOTE_MAX_LENGTH = 2000
PAGE_MAX_LENGTH = 300
SMALL_MAX_LENGTH = 300
CONSOLE_MAX_LINES = 20
CONSOLE_LINE_MAX_LENGTH = 300
FIXED_NOTE_MAX_LENGTH = 300
LIST_LIMIT_MAX = 500

# The site's save-code alphabet (main.py SAVE_CODE_ALPHABET): no 0/O, 1/I/L.
SAVE_CODE_RE = re.compile(r"^[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}$")
ATTACHMENT_KEYS = ("save_code",)

REDACTED = "[removed]"
_SECRET_PATTERNS = (
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.I),
    re.compile(r"((?:token|key|secret|password|auth|session)[\w-]*\s*[=:]\s*)[^\s&\"',;]+", re.I),
    re.compile(r"\b[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}\b"),
    re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+"),
)


def scrub_line(line: str) -> str:
    """One console line, cut to the cap, with anything secret-shaped replaced."""
    text = str(line)[: CONSOLE_LINE_MAX_LENGTH * 2]
    text = _SECRET_PATTERNS[0].sub("Bearer " + REDACTED, text)
    text = _SECRET_PATTERNS[1].sub(lambda m: m.group(1) + REDACTED, text)
    text = _SECRET_PATTERNS[2].sub(REDACTED, text)
    text = _SECRET_PATTERNS[3].sub(REDACTED, text)
    return text[:CONSOLE_LINE_MAX_LENGTH]


class BugReportIn(BaseModel):
    game_id: str = Field(min_length=1, max_length=ID_MAX_LENGTH)
    page: Optional[str] = Field(default=None, max_length=PAGE_MAX_LENGTH)
    note: str = Field(min_length=1, max_length=NOTE_MAX_LENGTH)
    schema_version: Optional[str] = Field(default=None, max_length=40)
    browser: Optional[str] = Field(default=None, max_length=SMALL_MAX_LENGTH)
    viewport: Optional[str] = Field(default=None, max_length=40)
    console_log: Optional[List[str]] = Field(default=None, max_length=CONSOLE_MAX_LINES)
    attachment: Optional[dict] = None
    # True = link the report to the signed-in account (needs a valid bearer token to take effect).
    link_account: bool = False

    @field_validator("note")
    @classmethod
    def note_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("note is required")
        return value.strip()

    @field_validator("game_id")
    @classmethod
    def game_id_shape(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
            raise ValueError("game_id may only use letters, numbers and - _ .")
        return value

    @field_validator("page")
    @classmethod
    def page_is_a_path(cls, value: Optional[str]) -> Optional[str]:
        # The path only: a query string or fragment could carry a save code or a token.
        if value is None:
            return None
        return value.split("?", 1)[0].split("#", 1)[0][:PAGE_MAX_LENGTH] or None

    @field_validator("console_log")
    @classmethod
    def console_lines(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return None
        return [scrub_line(line) for line in value]

    @field_validator("attachment")
    @classmethod
    def attachment_shape(cls, value: Optional[dict]) -> Optional[dict]:
        if value is None:
            return None
        extra = [k for k in value if k not in ATTACHMENT_KEYS]
        if extra:
            raise ValueError("attachment may only contain: " + ", ".join(ATTACHMENT_KEYS))
        clean: dict[str, Any] = {}
        if "save_code" in value:
            code = value["save_code"]
            if not isinstance(code, str) or not SAVE_CODE_RE.match(code.strip().upper()):
                raise ValueError("save_code is not a valid save code")
            clean["save_code"] = code.strip().upper()
        return clean or None


class BugReportAdminOut(BaseModel):
    id: str
    game_id: str
    page: Optional[str]
    note: str
    schema_version: Optional[str]
    browser: Optional[str]
    viewport: Optional[str]
    console_log: Optional[List[str]]
    attachment: Optional[dict]
    username: Optional[str] = None
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    is_fixed: bool = False
    fixed_note: Optional[str] = None
    fixed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BugReportPatch(BaseModel):
    resolved: Optional[bool] = None
    fixed: Optional[bool] = None
    note: Optional[str] = Field(default=None, max_length=1000)


def admin_out(row, username: Optional[str] = None) -> BugReportAdminOut:
    return BugReportAdminOut(
        id=row.id, game_id=row.game_id, page=row.page, note=row.note, schema_version=row.schema_version,
        browser=row.browser, viewport=row.viewport, console_log=row.console_log, attachment=row.attachment,
        username=username, is_resolved=bool(row.is_resolved), resolved_at=row.resolved_at,
        is_fixed=bool(row.is_fixed), fixed_note=row.fixed_note, fixed_at=row.fixed_at, created_at=row.created_at,
    )
