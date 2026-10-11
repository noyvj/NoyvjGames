"""R-33: anonymous "ghost" settlements (planning/MULTIPLAYER-SCOPING.md, level 2; Continuum is the pilot).

A signed-in player can opt in to publish ONE compact, anonymous per-season series from their settlement
(for Continuum: [season, era, people, score] rows). Another player can press a button and get ONE
random published series from a similar band, to draw as a dashed line beside their own. Nothing is
live: no connection, no ranking, nothing is ever pushed to anyone.

What is stored and shown
  * Only the numbers. The validator accepts a fixed row shape and nothing else, so there is nowhere
    for free text, a username or a save to go. Rows are bounded in length and in every value.
  * One row per (game, account) in `ghost_series`, replaced on re-publish, removed by one DELETE.
    The account id is kept only to enforce that, to delete it and to never show you your own series;
    it is never returned. Reads join `users` so a row whose account has been deleted is never served,
    and a publish sweeps such orphans away.
  * Anonymous: the ghost carries a random row id (so it can be reported), its scenario, hard-mode
    flag, final era and the series. No username, no handle, no dates.

Rules
  * Server-enforced opt-in: a publish must say `opt_in: true` and needs an account (like boards.py).
    A test account is accepted-but-ignored, and never read back.
  * Small-group suppression: no ghost is served until at least MIN_VISIBLE OTHER accounts have a
    visible published series for the game (so a lone publisher can never be matched to a viewer).
  * Band: the same scenario and hard-mode flag, and a final era within ERA_BAND of the caller's era.
    One match is picked at random with an injectable RNG (tests fix it); a `exclude` id avoids showing
    the same one twice in a row when there is another.
  * Moderation: a Report button writes a `ghost_reports` row (a fixed reason, nothing about the
    reporter). REPORT_HIDE_AT reports from different addresses hide a ghost pending review; the owner
    can hide or unhide any ghost and list the reports from the admin routes. Nothing is deleted
    silently.
  * Every write is rate limited with the shared FailureLimiter, per account and per address.
  * Every clock read goes through current_time(), so tests inject a fake clock.

The routes are built by make_router(...) and registered by one line in main.py. To add another game,
call register_ghost_game(...) with its row shape.
"""

import math
import random
import re
import time
from typing import Any, Callable, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, StrictBool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import GhostReport, GhostSeries, User
from stats import MIN_BUCKET
from throttle import FailureLimiter

MIN_VISIBLE = MIN_BUCKET  # no ghost until this many OTHER visible published series exist
ERA_BAND = 1  # a ghost's final era may differ from the caller's by at most this
REPORT_HIDE_AT = 3  # distinct-address reports that hide a ghost until the owner reviews it
REPORT_REASONS = ("implausible", "offensive", "other")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
SCENARIO_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
GHOST_ID_RE = re.compile(r"^[0-9a-fA-F-]{8,64}$")

GHOST_GAMES: dict = {}


def register_ghost_game(game_id: str, *, min_seasons: int, max_seasons: int, max_era: int,
                        max_people: float = 10_000_000.0, max_score: float = 100.0) -> dict:
    """Allow a game to publish ghosts. Each series row is [season, era, people, score]."""
    if not (isinstance(game_id, str) and ID_RE.match(game_id)):
        raise ValueError(f"bad game id {game_id!r}")
    if not (1 <= min_seasons <= max_seasons <= 1000):
        raise ValueError("need 1 <= min_seasons <= max_seasons <= 1000")
    if max_era < 0:
        raise ValueError("max_era must be >= 0")
    config = {
        "min_seasons": int(min_seasons), "max_seasons": int(max_seasons), "max_era": int(max_era),
        "max_people": float(max_people), "max_score": float(max_score),
    }
    GHOST_GAMES[game_id] = config
    return config


def unregister_ghost_game(game_id: str) -> None:
    GHOST_GAMES.pop(game_id, None)


# Continuum: the series is statlog's per-season rows (max 120 kept), season / era index / people /
# sustainability score. Eight eras (index 0 to 7). Five seasons is the least worth showing anyone.
register_ghost_game("continuum", min_seasons=5, max_seasons=150, max_era=7)


# --- clock and RNG (injectable, so limits and the random pick are testable) ---

_clock: Callable[[], float] = time.time
_rng: random.Random = random.Random()


def current_time() -> float:
    return _clock()


def set_clock(fn: Optional[Callable[[], float]]) -> None:
    global _clock
    _clock = fn if fn is not None else time.time


def set_rng(rng: Optional[random.Random]) -> None:
    """Install a seeded RNG (tests), or restore a fresh one with None."""
    global _rng
    _rng = rng if rng is not None else random.Random()


# --- write throttles (see throttle.py: the "failures" are simply accepted or rejected calls) ---

PUBLISH_LIMIT_PER_HOUR = 30
PUBLISH_IP_LIMIT_PER_HOUR = 60
REJECT_LIMIT_PER_15_MIN = 10
PEER_IP_LIMIT_PER_HOUR = 120
REPORT_IP_LIMIT_PER_HOUR = 20
DELETE_IP_LIMIT_PER_HOUR = 60

PUBLISH_LIMITER = FailureLimiter(max_failures=PUBLISH_LIMIT_PER_HOUR, window_seconds=3600)
PUBLISH_IP_LIMITER = FailureLimiter(max_failures=PUBLISH_IP_LIMIT_PER_HOUR, window_seconds=3600)
REJECT_LIMITER = FailureLimiter(max_failures=REJECT_LIMIT_PER_15_MIN, window_seconds=15 * 60)
PEER_IP_LIMITER = FailureLimiter(max_failures=PEER_IP_LIMIT_PER_HOUR, window_seconds=3600)
REPORT_IP_LIMITER = FailureLimiter(max_failures=REPORT_IP_LIMIT_PER_HOUR, window_seconds=3600)
DELETE_IP_LIMITER = FailureLimiter(max_failures=DELETE_IP_LIMIT_PER_HOUR, window_seconds=3600)
REPORT_ONCE_LIMITER = FailureLimiter(max_failures=1, window_seconds=24 * 3600)  # per (address, ghost)


def reset_throttles() -> None:
    for limiter in (PUBLISH_LIMITER, PUBLISH_IP_LIMITER, REJECT_LIMITER, PEER_IP_LIMITER,
                    REPORT_IP_LIMITER, DELETE_IP_LIMITER, REPORT_ONCE_LIMITER):
        limiter.reset()


# --- validation ---

def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_series(config: dict, raw) -> tuple:
    """(rows, None) with every row cleaned to [season, era, people, score], or (None, why).

    A row is exactly four finite numbers. Season and era are whole numbers (season from 1, strictly
    increasing; era from 0 to the game's top era), people is rounded to a whole number between 0 and
    the game's cap, score between 0 and the cap, rounded to one decimal. Anything else is refused;
    nothing is repaired by guessing."""
    if not isinstance(raw, list):
        return None, "series must be a list of rows"
    if len(raw) < config["min_seasons"]:
        return None, f"series needs at least {config['min_seasons']} seasons"
    if len(raw) > config["max_seasons"]:
        return None, f"series may have at most {config['max_seasons']} seasons"
    rows = []
    last_season = 0
    for item in raw:
        if not isinstance(item, (list, tuple)) or len(item) != 4 or not all(_is_number(v) for v in item):
            return None, "every row must be [season, era, people, score] as finite numbers"
        season, era, people, score = item
        if float(season) != int(season) or float(era) != int(era):
            return None, "season and era must be whole numbers"
        season, era = int(season), int(era)
        if season < 1 or season > 100_000 or season <= last_season:
            return None, "seasons must start at 1 or more and strictly increase"
        if era < 0 or era > config["max_era"]:
            return None, "era is out of range"
        if people < 0 or people > config["max_people"]:
            return None, "people is out of range"
        if score < 0 or score > config["max_score"]:
            return None, "score is out of range"
        last_season = season
        rows.append([season, era, int(round(people)), round(float(score), 1)])
    return rows, None


# --- request bodies ---

class GhostPublish(BaseModel):
    game: str
    scenario: str
    hard: StrictBool = False
    series: List[Any]
    # The player must have turned publishing on; a request without this is refused.
    opt_in: StrictBool = False


class GhostReportIn(BaseModel):
    game: str
    ghost_id: str
    reason: str = "other"


class GhostHideIn(BaseModel):
    hidden: StrictBool


# --- queries ---

def _visible(db: Session, game_id: str):
    """Rows a visitor may be shown: not hidden and not from a test account (the inner join to users also
    drops any row whose account no longer exists)."""
    return (
        db.query(GhostSeries)
        .join(User, User.id == GhostSeries.user_id)
        .filter(GhostSeries.game_id == game_id, GhostSeries.is_hidden.is_(False), User.is_test.is_(False))
    )


def purge_orphans(db: Session) -> int:
    """Deletes ghost rows whose account is gone (belt and braces next to the database cascade)."""
    removed = db.query(GhostSeries).filter(~GhostSeries.user_id.in_(select(User.id))).delete(synchronize_session=False)
    if removed:
        db.commit()
    return int(removed)


def pick_ghost(db: Session, game_id: str, *, scenario: str, hard: bool, era: int,
               caller_id: Optional[str] = None, exclude: Optional[str] = None) -> dict:
    """The read rule, kept out of the route so tests can call it. Returns {"ghost": row-or-None,
    "reason": None | "too_few" | "no_match"}."""
    base = _visible(db, game_id)
    if caller_id:
        base = base.filter(GhostSeries.user_id != caller_id)
    if base.count() < MIN_VISIBLE:
        return {"ghost": None, "reason": "too_few"}
    pool = base.filter(
        GhostSeries.scenario == scenario, GhostSeries.hard.is_(bool(hard)),
        GhostSeries.era >= era - ERA_BAND, GhostSeries.era <= era + ERA_BAND,
    ).order_by(GhostSeries.id.asc()).all()
    if exclude and len(pool) > 1:
        pool = [row for row in pool if row.id != exclude]
    if not pool:
        return {"ghost": None, "reason": "no_match"}
    return {"ghost": _rng.choice(pool), "reason": None}


def public_ghost(row: GhostSeries) -> dict:
    """The only shape a ghost is ever sent in: no account id, no username, no dates."""
    return {
        "id": row.id, "scenario": row.scenario, "hard": bool(row.hard), "era": int(row.era),
        "seasons": int(row.seasons), "series": row.series_json,
    }


# --- the routes ---

def make_router(*, get_db: Callable, get_current_user: Callable, get_current_user_optional: Callable,
                require_admin: Callable, client_key: Callable) -> APIRouter:
    """Builds the router; main.py passes in its own dependencies (avoids importing main from here)."""
    router = APIRouter()

    def _config_or_404(game_id: str) -> dict:
        config = GHOST_GAMES.get(game_id)
        if config is None:
            raise HTTPException(status_code=404, detail="This game does not publish ghosts")
        return config

    @router.post("/ghosts")
    def publish_ghost(payload: GhostPublish, request: Request, response: Response,
                      current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        """Opt-in publish (replaces this account's earlier series for the game)."""
        config = _config_or_404(payload.game)
        response.headers["Cache-Control"] = "no-store"
        if not payload.opt_in:
            raise HTTPException(status_code=400, detail="opt_in must be true: nothing is published unless the player turned it on")
        if current_user.is_test:
            return {"accepted": False, "reason": "test account"}
        now = current_time()
        who, where = f"user:{current_user.id}", client_key(request)
        if PUBLISH_LIMITER.blocked(who, now) or PUBLISH_IP_LIMITER.blocked(where, now) or REJECT_LIMITER.blocked(who, now):
            raise HTTPException(status_code=429, detail="Too many publishes, try again later")
        rows, problem = validate_series(config, payload.series)
        if rows is None or not SCENARIO_RE.match(payload.scenario or ""):
            REJECT_LIMITER.record_failure(who, now)
            raise HTTPException(status_code=422, detail=problem or "scenario is not a valid id")
        PUBLISH_LIMITER.record_failure(who, now)
        PUBLISH_IP_LIMITER.record_failure(where, now)
        era = rows[-1][1]
        for _attempt in range(2):  # a concurrent first publish can race the unique constraint once
            try:
                row = db.query(GhostSeries).filter(
                    GhostSeries.game_id == payload.game, GhostSeries.user_id == current_user.id).first()
                if row is None:
                    db.add(GhostSeries(
                        game_id=payload.game, user_id=current_user.id, scenario=payload.scenario,
                        hard=bool(payload.hard), era=era, seasons=len(rows), series_json=rows))
                else:
                    row.scenario, row.hard, row.era = payload.scenario, bool(payload.hard), era
                    row.seasons, row.series_json = len(rows), rows
                db.commit()
                break
            except IntegrityError:
                db.rollback()
        else:
            raise HTTPException(status_code=409, detail="Could not publish, please try again")
        purge_orphans(db)
        return {"accepted": True, "seasons": len(rows), "era": era}

    @router.get("/ghosts/{game_id}/mine")
    def my_ghost(game_id: str, response: Response, current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
        """Whether this account has a published series (the settings switch shows it)."""
        _config_or_404(game_id)
        response.headers["Cache-Control"] = "no-store"
        row = db.query(GhostSeries).filter(
            GhostSeries.game_id == game_id, GhostSeries.user_id == current_user.id).first()
        if row is None:
            return {"published": False}
        return {"published": True, "seasons": int(row.seasons), "era": int(row.era), "hidden": bool(row.is_hidden)}

    @router.delete("/ghosts/{game_id}")
    def unpublish_ghost(game_id: str, request: Request, response: Response,
                        current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        """Opt out: removes this account's published series."""
        _config_or_404(game_id)
        response.headers["Cache-Control"] = "no-store"
        now, where = current_time(), client_key(request)
        if DELETE_IP_LIMITER.blocked(where, now):
            raise HTTPException(status_code=429, detail="Too many requests, try again later")
        DELETE_IP_LIMITER.record_failure(where, now)
        removed = db.query(GhostSeries).filter(
            GhostSeries.game_id == game_id, GhostSeries.user_id == current_user.id).delete(synchronize_session=False)
        db.commit()
        return {"removed": int(removed)}

    @router.get("/ghosts/{game_id}/peer")
    def peer_ghost(game_id: str, request: Request, response: Response, scenario: str = "standard",
                   era: int = 0, hard: bool = False, exclude: Optional[str] = None,
                   current_user: Optional[User] = Depends(get_current_user_optional),
                   db: Session = Depends(get_db)):
        """One anonymous published series from the caller's band, at random, never the caller's own.
        Always 200: {"ghost": null, "reason": "too_few" | "no_match"} when there is nothing to show."""
        config = _config_or_404(game_id)
        response.headers["Cache-Control"] = "no-store"
        now, where = current_time(), client_key(request)
        if PEER_IP_LIMITER.blocked(where, now):
            raise HTTPException(status_code=429, detail="Too many requests, try again later")
        PEER_IP_LIMITER.record_failure(where, now)
        if not SCENARIO_RE.match(scenario or "") or era < 0 or era > config["max_era"]:
            raise HTTPException(status_code=422, detail="scenario or era is not valid")
        if exclude is not None and not GHOST_ID_RE.match(exclude):
            exclude = None
        picked = pick_ghost(db, game_id, scenario=scenario, hard=hard, era=era,
                            caller_id=current_user.id if current_user else None, exclude=exclude)
        if picked["ghost"] is None:
            return {"ghost": None, "reason": picked["reason"], "min_visible": MIN_VISIBLE}
        return {"ghost": public_ghost(picked["ghost"]), "reason": None, "min_visible": MIN_VISIBLE}

    @router.post("/ghosts/report")
    def report_ghost(payload: GhostReportIn, request: Request, response: Response, db: Session = Depends(get_db)):
        """Reports one ghost. Stores the ghost id and a reason from a fixed list, nothing about the
        reporter. The same address reporting the same ghost twice in a day counts once."""
        _config_or_404(payload.game)
        response.headers["Cache-Control"] = "no-store"
        if payload.reason not in REPORT_REASONS:
            raise HTTPException(status_code=422, detail=f"reason must be one of {', '.join(REPORT_REASONS)}")
        if not GHOST_ID_RE.match(payload.ghost_id):
            raise HTTPException(status_code=404, detail="Unknown ghost")
        now, where = current_time(), client_key(request)
        if REPORT_IP_LIMITER.blocked(where, now):
            raise HTTPException(status_code=429, detail="Too many reports, try again later")
        row = db.query(GhostSeries).filter(
            GhostSeries.id == payload.ghost_id, GhostSeries.game_id == payload.game).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Unknown ghost")
        REPORT_IP_LIMITER.record_failure(where, now)
        once_key = f"{where}|{row.id}"
        if REPORT_ONCE_LIMITER.blocked(once_key, now):
            return {"reported": True, "counted": False}
        REPORT_ONCE_LIMITER.record_failure(once_key, now)
        db.add(GhostReport(game_id=payload.game, ghost_id=row.id, reason=payload.reason))
        row.report_count = int(row.report_count or 0) + 1
        if row.report_count >= REPORT_HIDE_AT:
            row.is_hidden = True
        db.commit()
        return {"reported": True, "counted": True}

    @router.get("/admin/ghost-reports")
    def admin_ghost_reports(response: Response, resolved: Optional[bool] = None,
                            _admin: None = Depends(require_admin), db: Session = Depends(get_db)):
        """Reports with a summary of the ghost each one is about (never the owner)."""
        response.headers["Cache-Control"] = "no-store"
        query = db.query(GhostReport)
        if resolved is not None:
            query = query.filter(GhostReport.is_resolved.is_(resolved))
        out = []
        for report in query.order_by(GhostReport.created_at.desc(), GhostReport.id.desc()).limit(200).all():
            ghost = db.query(GhostSeries).filter(GhostSeries.id == report.ghost_id).first()
            out.append({
                "id": report.id, "game_id": report.game_id, "ghost_id": report.ghost_id, "reason": report.reason,
                "is_resolved": bool(report.is_resolved),
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "ghost": None if ghost is None else {
                    "scenario": ghost.scenario, "hard": bool(ghost.hard), "era": ghost.era, "seasons": ghost.seasons,
                    "is_hidden": bool(ghost.is_hidden), "report_count": int(ghost.report_count or 0),
                },
            })
        return {"reports": out}

    @router.post("/admin/ghost-reports/{report_id}/resolve")
    def admin_resolve_ghost_report(report_id: str, response: Response, _admin: None = Depends(require_admin),
                                   db: Session = Depends(get_db)):
        response.headers["Cache-Control"] = "no-store"
        report = db.query(GhostReport).filter(GhostReport.id == report_id).first()
        if report is None:
            raise HTTPException(status_code=404, detail="Unknown report")
        report.is_resolved = True
        db.commit()
        return {"id": report.id, "is_resolved": True}

    @router.put("/admin/ghosts/{ghost_id}/hidden")
    def admin_hide_ghost(ghost_id: str, body: GhostHideIn, response: Response, _admin: None = Depends(require_admin),
                         db: Session = Depends(get_db)):
        """Hide (or restore) one ghost. Hiding never deletes it, so a mistake is undone by hidden=false."""
        response.headers["Cache-Control"] = "no-store"
        row = db.query(GhostSeries).filter(GhostSeries.id == ghost_id).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Unknown ghost")
        row.is_hidden = body.hidden
        if not body.hidden:
            row.report_count = 0
        db.commit()
        return {"id": row.id, "is_hidden": bool(row.is_hidden)}

    return router
