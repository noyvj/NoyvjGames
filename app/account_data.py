"""Account data export and deletion (Y-14), admin time series (Y-13) and the
What's New "was this helpful?" votes (Y-24). Pure database helpers: main.py owns
the routes, the authentication and the rate limiting.

What the server holds about an account (and so what export and delete cover):
  users, auth_sessions, saves (claimed and slotted), leaderboard_entries,
  score_entries, score_profiles, feedback written while signed in, helpful_votes
  cast while signed in.
What it does NOT link to an account, so cannot export or remove by account:
  ratings (the hub's star widget and in-game prompts), answer_reports (Le Champ de
  Mots), pool_days totals and the opt-in visit counter. None of those rows carries
  a user id. terms.html says so in plain words.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import stats
from models import (
    AnswerReport, AuthSession, Feedback, HelpfulVote, LeaderboardEntry, PageView, Rating, Save,
    ScoreEntry, ScoreProfile, User,
)

# ---------------------------------------------------------------- export / delete

EXPORT_FORMAT = 1


def _iso(value) -> Optional[str]:
    return value.isoformat() if value is not None else None


def build_export(db: Session, user: User, now: Optional[datetime] = None) -> dict:
    """Everything the server holds for this account, as plain JSON-able data.
    Never includes the password hash or any session token."""
    now = now or datetime.now(timezone.utc)
    saves = db.query(Save).filter(Save.user_id == user.id).order_by(Save.game_id, Save.slot, Save.created_at).all()
    achievements: dict[str, list[str]] = {}
    for row in saves:
        earned = sorted(stats.extract_achievements(row.save_data))
        if earned:
            merged = set(achievements.get(row.game_id, [])) | set(earned)
            achievements[row.game_id] = sorted(merged)
    feedback = db.query(Feedback).filter(Feedback.user_id == user.id).order_by(Feedback.created_at).all()
    legacy_boards = db.query(LeaderboardEntry).filter(LeaderboardEntry.user_id == user.id).all()
    scores = db.query(ScoreEntry).filter(ScoreEntry.user_id == user.id).order_by(
        ScoreEntry.game_id, ScoreEntry.board, ScoreEntry.window, ScoreEntry.period).all()
    profile = db.query(ScoreProfile).filter(ScoreProfile.user_id == user.id).first()
    votes = db.query(HelpfulVote).filter(HelpfulVote.user_id == user.id).order_by(HelpfulVote.created_at).all()
    sessions = db.query(func.count(AuthSession.id)).filter(AuthSession.user_id == user.id).scalar() or 0
    return {
        "format": EXPORT_FORMAT,
        "exported_at": now.isoformat(),
        "note": (
            "Everything the NoyvjGames server holds that is linked to this account. Save codes in here can open "
            "and overwrite their saves, so keep this file private. Star ratings, answer reports, community pool "
            "totals and the visit counter are not linked to any account, so they are not in this file."
        ),
        "account": {
            "username": user.username,
            "email": user.email,
            "created_at": _iso(user.created_at),
            "settings": _settings_of(user),
            "signed_in_sessions": int(sessions),
        },
        "saves": [
            {
                "save_code": r.save_code, "game_id": r.game_id, "slot": r.slot, "slot_name": r.slot_name,
                "created_at": _iso(r.created_at), "updated_at": _iso(r.updated_at), "save_data": r.save_data,
            }
            for r in saves
        ],
        "achievements": achievements,
        "feedback": [
            {"game_id": r.game_id, "rating": r.rating, "comment": r.comment, "created_at": _iso(r.created_at)}
            for r in feedback
        ],
        "leaderboards": {
            "show_username": bool(profile.show_username) if profile is not None else False,
            "legacy_entries": [
                {"game_id": r.game_id, "board": r.board, "score": r.score, "detail": r.detail,
                 "updated_at": _iso(r.updated_at)}
                for r in legacy_boards
            ],
            "score_entries": [
                {"game_id": r.game_id, "board": r.board, "window": r.window, "period": r.period,
                 "score": r.score, "detail": r.detail, "updated_at": _iso(r.updated_at)}
                for r in scores
            ],
        },
        "whats_new_votes": [
            {"entry_id": r.entry_id, "helpful": bool(r.helpful), "updated_at": _iso(r.updated_at)} for r in votes
        ],
    }


def _settings_of(user: User) -> dict:
    import json

    if not user.settings_json:
        return {}
    try:
        value = json.loads(user.settings_json)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def delete_account(db: Session, user: User) -> dict:
    """Permanently removes the account and every row linked to it, in one
    transaction (all or nothing). Returns how many rows went from each table."""
    uid = user.id
    removed = {}
    # Child rows first, so no foreign key ever points at a user that is gone.
    for label, model in (
        ("sessions", AuthSession),
        ("saves", Save),
        ("leaderboard_entries", LeaderboardEntry),
        ("score_entries", ScoreEntry),
        ("feedback", Feedback),
        ("whats_new_votes", HelpfulVote),
    ):
        removed[label] = db.query(model).filter(model.user_id == uid).delete(synchronize_session=False)
    removed["score_profile"] = db.query(ScoreProfile).filter(ScoreProfile.user_id == uid).delete(synchronize_session=False)
    db.query(User).filter(User.id == uid).delete(synchronize_session=False)
    db.commit()
    db.expire_all()
    stats.cache_clear()  # the public aggregates must stop counting the deleted saves
    return removed


# ---------------------------------------------------------------- admin time series

SERIES_LABELS = {
    "plays": "Plays (saves written or updated)",
    "saves": "New saves",
    "signups": "Sign-ups",
    "feedback": "Site feedback",
    "ratings": "Ratings and prompts",
    "reports": "Answer reports",
    "visits": "Counted visits (opt-in)",
}
MIN_DAYS, MAX_DAYS, DEFAULT_DAYS = 7, 90, 30


def clamp_days(days: Optional[int]) -> int:
    if days is None:
        return DEFAULT_DAYS
    return max(MIN_DAYS, min(MAX_DAYS, days))


def _day_key(value) -> str:
    return value.isoformat() if hasattr(value, "isoformat") and not isinstance(value, str) else str(value)[:10]


def _per_day(db: Session, column, since: datetime, *filters) -> dict:
    day = func.date(column)
    rows = db.query(day, func.count()).filter(column >= since, *filters).group_by(day).all()
    return {_day_key(d): int(n) for d, n in rows if d is not None}


def timeseries(db: Session, days: Optional[int] = None, hide_test: bool = True, today: Optional[datetime] = None) -> dict:
    """Daily counts for the last `days` UTC days (today included), one list per
    series, zero-filled, oldest first. With hide_test, rows from accounts flagged
    is_test and rows an admin hid (is_hidden) are left out, matching the other
    admin counts."""
    days = clamp_days(days)
    today = (today or datetime.now(timezone.utc)).astimezone(timezone.utc)
    first = today.date() - timedelta(days=days - 1)
    since = datetime(first.year, first.month, first.day, tzinfo=timezone.utc)
    labels = [(first + timedelta(days=i)).isoformat() for i in range(days)]

    test_ids = db.query(User.id).filter(User.is_test.is_(True))
    not_test_user = or_(Save.user_id.is_(None), ~Save.user_id.in_(test_ids))
    save_filters = (not_test_user,) if hide_test else ()
    user_filters = (User.is_test.is_(False),) if hide_test else ()
    feedback_filters = (
        (Feedback.is_hidden.is_(False), or_(Feedback.user_id.is_(None), ~Feedback.user_id.in_(test_ids)))
        if hide_test else ()
    )
    rating_filters = (Rating.is_hidden.is_(False),) if hide_test else ()

    raw = {
        "plays": _per_day(db, Save.updated_at, since, *save_filters),
        "saves": _per_day(db, Save.created_at, since, *save_filters),
        "signups": _per_day(db, User.created_at, since, *user_filters),
        "feedback": _per_day(db, Feedback.created_at, since, *feedback_filters),
        "ratings": _per_day(db, Rating.created_at, since, *rating_filters),
        "reports": _per_day(db, AnswerReport.created_at, since),
        "visits": _per_day(db, PageView.created_at, since),
    }
    series = {}
    for name, counts in raw.items():
        values = [counts.get(label, 0) for label in labels]
        series[name] = {"label": SERIES_LABELS[name], "counts": values, "total": sum(values)}
    return {
        "days": labels,
        "hide_test": hide_test,
        "series": series,
        "notes": {
            "plays": "No table records plays. This counts saves that were created or updated that day, which is the nearest honest signal.",
            "reports": "The site feedback form has no bug-report category, so the only report table is Le Champ de Mots answer reports.",
            "errors": "Nothing on the server records errors (no table, no log endpoint), so there is no top-errors table.",
        },
    }


# ---------------------------------------------------------------- What's New votes

ENTRY_ID_RE = re.compile(r"^(game|site)-\d{4}-\d{2}-\d{2}-[0-9a-f]{8}$")
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def voter_for(user: Optional[User], token: Optional[str]) -> Optional[tuple]:
    """(voter_key, user_id) for this caller, or None when neither a valid account
    nor a valid anonymous token was given."""
    if user is not None:
        return f"u:{user.id}", user.id
    if token and TOKEN_RE.match(token):
        return f"a:{token}", None
    return None


def cast_vote(db: Session, entry_id: str, voter_key: str, user_id: Optional[str], helpful: bool) -> HelpfulVote:
    """Upsert: one row per entry and voter, the latest answer wins."""
    for attempt in range(2):
        row = db.query(HelpfulVote).filter(HelpfulVote.entry_id == entry_id, HelpfulVote.voter_key == voter_key).first()
        if row is None:
            row = HelpfulVote(entry_id=entry_id, voter_key=voter_key, user_id=user_id, helpful=helpful)
            db.add(row)
        else:
            row.helpful = helpful
            row.updated_at = func.now()
        try:
            db.commit()
        except IntegrityError:
            # Two first votes from the same voter raced past the lookup above; the
            # loser retries once and takes the update branch (a bare 500 otherwise).
            db.rollback()
            if attempt:
                raise
            continue
        db.refresh(row)
        return row


def retract_vote(db: Session, entry_id: str, voter_key: str) -> int:
    n = db.query(HelpfulVote).filter(HelpfulVote.entry_id == entry_id, HelpfulVote.voter_key == voter_key).delete(
        synchronize_session=False)
    db.commit()
    return int(n)


def vote_tallies(db: Session, hide_test: bool = True) -> list:
    """[{entry_id, up, down}] busiest first. Votes by test accounts are left out
    while hide_test is on."""
    query = db.query(HelpfulVote.entry_id, HelpfulVote.helpful, func.count())
    if hide_test:
        test_ids = db.query(User.id).filter(User.is_test.is_(True))
        query = query.filter(or_(HelpfulVote.user_id.is_(None), ~HelpfulVote.user_id.in_(test_ids)))
    tally: dict[str, dict] = {}
    for entry_id, helpful, n in query.group_by(HelpfulVote.entry_id, HelpfulVote.helpful).all():
        slot = tally.setdefault(entry_id, {"entry_id": entry_id, "up": 0, "down": 0})
        slot["up" if helpful else "down"] += int(n)
    return sorted(tally.values(), key=lambda t: (-(t["up"] + t["down"]), t["entry_id"]))
