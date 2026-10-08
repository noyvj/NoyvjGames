"""Z-7 / Y-1: the player profile data model and the public profile.

Pure helpers over the `user_profiles` table; main.py owns the routes and the rate limits.

What is stored per account (all of it numbers, game slugs and short ids, never free text):
  * is_public        the one switch behind profile.html?u=name. Default OFF.
  * favourite_game   a game slug the owner picked (or none: the page then shows the most played).
  * games            slug -> {seconds, achievements}. Fed by shared/profile.js at save time:
                     seconds are ADDED (the helper sends the time since its last successful post),
                     achievements take the HIGHER of the old and new count (starting a new game
                     never lowers a profile).
  * streaks          "<slug>:<label>" -> the longest value ever reported.
  * event_badges     seasonal badge ids ("halloween-2026"); the label is derived from the id here,
                     never taken from the client, so a public page can only show wording made here.
Badges beyond the seasonal ones are computed from the numbers (see MILESTONES), so there is one
definition and nothing to forge. The public view never contains an email, a save, a save code, a
session token or the account's internal id.
"""

import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, StrictBool, StrictInt, field_validator
from sqlalchemy.orm import Session

from models import User, UserProfile

GAME_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
STREAK_LABEL_RE = re.compile(r"^[a-z0-9_]{1,40}$")
EVENT_BADGE_RE = re.compile(r"^[a-z0-9-]{1,64}$")

MAX_GAMES = 60
MAX_STREAKS = 40
MAX_EVENT_BADGES = 60
MAX_ADD_SECONDS = 4 * 3600          # one update can credit at most four hours
MAX_ACHIEVEMENTS_PER_GAME = 1000
MAX_STREAK_VALUE = 100_000
MAX_SECONDS_PER_GAME = 100_000 * 3600


class ProgressIn(BaseModel):
    game: str
    add_seconds: StrictInt = Field(default=0, ge=0, le=MAX_ADD_SECONDS)
    achievements: Optional[StrictInt] = Field(default=None, ge=0, le=MAX_ACHIEVEMENTS_PER_GAME)
    streaks: Optional[dict] = None

    @field_validator("game")
    @classmethod
    def game_slug(cls, value: str) -> str:
        if not GAME_SLUG_RE.match(value):
            raise ValueError("game must be a game slug such as 'canopy'")
        return value

    @field_validator("streaks")
    @classmethod
    def streak_shape(cls, value: Optional[dict]) -> Optional[dict]:
        if value is None:
            return None
        if len(value) > 10:
            raise ValueError("at most 10 streaks per update")
        clean = {}
        for label, number in value.items():
            if not isinstance(label, str) or not STREAK_LABEL_RE.match(label):
                raise ValueError("a streak label must be lowercase letters, numbers and _")
            if isinstance(number, bool) or not isinstance(number, int) or not 0 <= number <= MAX_STREAK_VALUE:
                raise ValueError("a streak value must be a whole number from 0 to %d" % MAX_STREAK_VALUE)
            clean[label] = number
        return clean


class ProfilePut(BaseModel):
    """Every key is optional; only the keys sent change (like PUT /users/me/settings)."""
    is_public: Optional[StrictBool] = None
    favourite_game: Optional[str] = None      # null clears it; check model_fields_set to tell "absent"
    progress: Optional[ProgressIn] = None
    event_badges: Optional[List[str]] = Field(default=None, max_length=MAX_EVENT_BADGES)

    @field_validator("favourite_game")
    @classmethod
    def favourite_slug(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        if not GAME_SLUG_RE.match(value):
            raise ValueError("favourite_game must be a game slug such as 'canopy'")
        return value

    @field_validator("event_badges")
    @classmethod
    def badge_ids(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return None
        return [v for v in value if isinstance(v, str) and EVENT_BADGE_RE.match(v)]


# --- badges ------------------------------------------------------------------------------------

# (id, label, how you get it, test over the summary numbers)
MILESTONES = (
    ("first-steps", "First steps", "Earned a first achievement.", lambda s: s["total_achievements"] >= 1),
    ("achiever-10", "Ten achievements", "Earned 10 achievements across the site.", lambda s: s["total_achievements"] >= 10),
    ("achiever-50", "Fifty achievements", "Earned 50 achievements across the site.", lambda s: s["total_achievements"] >= 50),
    ("achiever-100", "One hundred achievements", "Earned 100 achievements across the site.", lambda s: s["total_achievements"] >= 100),
    ("explorer-3", "Tried three games", "Played 3 different games.", lambda s: s["games_played"] >= 3),
    ("explorer-8", "Tried eight games", "Played 8 different games.", lambda s: s["games_played"] >= 8),
    ("explorer-14", "Tried a lot of games", "Played 14 different games.", lambda s: s["games_played"] >= 14),
    ("time-1h", "An hour in", "Played for an hour in total.", lambda s: s["total_seconds"] >= 3600),
    ("time-10h", "Ten hours in", "Played for 10 hours in total.", lambda s: s["total_seconds"] >= 10 * 3600),
    ("time-100h", "A hundred hours in", "Played for 100 hours in total.", lambda s: s["total_seconds"] >= 100 * 3600),
    ("streak-7", "A streak of seven", "A longest streak of 7 or more in any game.", lambda s: s["longest_streak"] >= 7),
    ("streak-30", "A streak of thirty", "A longest streak of 30 or more in any game.", lambda s: s["longest_streak"] >= 30),
)


def event_badge_label(badge_id: str) -> str:
    """'halloween-2026' -> 'Halloween 2026'. Built from the id alone."""
    return " ".join(part.capitalize() if not part.isdigit() else part for part in badge_id.split("-") if part)


# --- reading and writing -----------------------------------------------------------------------


def get_row(db: Session, user_id: str) -> Optional[UserProfile]:
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()


def _clean_games(raw) -> dict:
    out = {}
    if isinstance(raw, dict):
        for slug, entry in raw.items():
            if isinstance(slug, str) and GAME_SLUG_RE.match(slug) and isinstance(entry, dict):
                out[slug] = {"seconds": int(entry.get("seconds") or 0), "achievements": int(entry.get("achievements") or 0)}
    return out


def _clean_streaks(raw) -> dict:
    out = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(key, str) and ":" in key and isinstance(value, int) and not isinstance(value, bool):
                out[key] = value
    return out


def summarize(user: User, row: Optional[UserProfile], viewer: str = "public", now: Optional[datetime] = None) -> dict:
    """The profile as plain data. `viewer` is "owner" (adds is_public) or "public"."""
    games = _clean_games(row.games_json if row else None)
    streaks = _clean_streaks(row.streaks_json if row else None)
    events = [b for b in ((row.event_badges_json if row else None) or []) if isinstance(b, str) and EVENT_BADGE_RE.match(b)]
    total_seconds = sum(g["seconds"] for g in games.values())
    total_achievements = sum(g["achievements"] for g in games.values())
    played = [slug for slug, g in games.items() if g["seconds"] > 0 or g["achievements"] > 0]
    longest = max(streaks.values()) if streaks else 0
    numbers = {
        "total_seconds": total_seconds, "total_achievements": total_achievements,
        "games_played": len(played), "longest_streak": longest,
    }
    most_played = None
    if played:
        most_played = sorted(played, key=lambda s: (-games[s]["seconds"], -games[s]["achievements"], s))[0]
    explicit = row.favourite_game if row and row.favourite_game else None
    badges = [
        {"id": bid, "label": label, "detail": detail, "kind": "milestone"}
        for bid, label, detail, test in MILESTONES if test(numbers)
    ]
    badges += [
        {"id": b, "label": event_badge_label(b), "detail": "A seasonal event badge.", "kind": "event"}
        for b in sorted(events)
    ]
    member_since = user.created_at.date().isoformat() if getattr(user, "created_at", None) else None
    out = {
        "username": user.username,
        "member_since": member_since,
        "favourite_game": explicit or most_played,
        "favourite_is_most_played": bool(not explicit and most_played),
        "games": sorted(
            ({"game": slug, **g} for slug, g in games.items() if g["seconds"] > 0 or g["achievements"] > 0),
            key=lambda e: (-e["achievements"], -e["seconds"], e["game"]),
        ),
        "total_seconds": total_seconds,
        "total_achievements": total_achievements,
        "games_played": len(played),
        "streaks": sorted(
            ({"game": key.split(":", 1)[0], "label": key.split(":", 1)[1], "value": value}
             for key, value in streaks.items() if value > 0),
            key=lambda e: (-e["value"], e["game"], e["label"]),
        )[:10],
        "badges": badges,
    }
    if viewer == "owner":
        out["is_public"] = bool(row.is_public) if row else False
        out["favourite_game_choice"] = explicit
    return out


def public_profile(db: Session, username: str) -> Optional[dict]:
    """The public view for a (normalised) username, or None when there is no such account or its
    owner has not turned the profile on. The caller answers both the same way, so the response
    never says whether an account exists."""
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        return None
    row = get_row(db, user.id)
    if row is None or not row.is_public:
        return None
    return summarize(user, row, viewer="public")


def apply_put(db: Session, user: User, payload: ProfilePut) -> UserProfile:
    """Merge the keys the payload set into the account's profile row (creating it on first use)."""
    row = get_row(db, user.id)
    if row is None:
        row = UserProfile(user_id=user.id, is_public=False)
        db.add(row)
    sent = payload.model_fields_set
    if "is_public" in sent and payload.is_public is not None:
        row.is_public = bool(payload.is_public)
    if "favourite_game" in sent:
        row.favourite_game = payload.favourite_game
    if payload.event_badges:
        merged = set(_clean_event_badges(row.event_badges_json)) | set(payload.event_badges)
        row.event_badges_json = sorted(merged)[:MAX_EVENT_BADGES]
    if payload.progress is not None:
        _apply_progress(row, payload.progress)
    db.commit()
    db.refresh(row)
    return row


def _clean_event_badges(raw) -> list:
    return [b for b in (raw or []) if isinstance(b, str) and EVENT_BADGE_RE.match(b)]


def _apply_progress(row: UserProfile, progress: ProgressIn) -> None:
    games = _clean_games(row.games_json)
    if progress.game not in games and len(games) >= MAX_GAMES:
        return
    entry = games.get(progress.game) or {"seconds": 0, "achievements": 0}
    entry["seconds"] = min(entry["seconds"] + progress.add_seconds, MAX_SECONDS_PER_GAME)
    if progress.achievements is not None:
        entry["achievements"] = max(entry["achievements"], progress.achievements)
    games[progress.game] = entry
    row.games_json = games       # a fresh dict, so SQLAlchemy sees the JSON column change
    if progress.streaks:
        streaks = _clean_streaks(row.streaks_json)
        for label, number in progress.streaks.items():
            key = f"{progress.game}:{label}"
            if key in streaks or len(streaks) < MAX_STREAKS:
                streaks[key] = max(streaks.get(key, 0), number)
        row.streaks_json = streaks


def export_block(db: Session, user: User) -> dict:
    """The account export's profile section: the owner's own view plus the raw switches."""
    row = get_row(db, user.id)
    out = summarize(user, row, viewer="owner")
    out["updated_at"] = row.updated_at.isoformat() if row is not None and row.updated_at else None
    return out
