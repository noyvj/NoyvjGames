"""Public cross-game aggregate stats (percentiles, achievement rarity).

Read-only, small groups suppressed; see stats.py.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

import stats
from auth import _test_user_ids
from database import get_db
from models import Save


router = APIRouter()


# --- Cross-game aggregate stats (TODO.md Z1) ---
# Public, read-only, aggregates only: no usernames, save codes, raw saves or
# any string from a save ever leaves this section. See stats.py for the
# privacy rules (small-N suppression at MIN_BUCKET, no min/max) and for the
# per-game STATS_FIELDS whitelist games opt numeric fields into. Reads the
# existing `saves` table only — zero per-game backend changes. One SELECT of
# just `save_data` for the game (newest MAX_SAVES_SCANNED), decoded and
# aggregated in Python because the blobs are opaque, possibly adversarial
# JSON that portable SQL can't safely cast; cached per game in-process.
STATS_CACHE_CONTROL = "public, max-age=300"


def _game_saves(db: Session, game_id: str) -> list:
    cached = stats.cache_get(game_id)
    if cached is not None:
        return cached
    rows = (
        db.query(Save.save_data)
        .filter(Save.game_id == game_id)
        .filter(or_(Save.user_id.is_(None), ~Save.user_id.in_(_test_user_ids(db))))
        .order_by(Save.updated_at.desc())
        .limit(stats.MAX_SAVES_SCANNED)
        .all()
    )
    saves = [stats.slim_save(game_id, r[0]) for r in rows]
    stats.cache_put(game_id, saves)
    return saves


def _require_known_game(game_id: str) -> None:
    if game_id not in stats.STATS_FIELDS:
        raise HTTPException(status_code=404, detail="Unknown game")


@router.get("/stats/games")
def stats_games(response: Response):
    response.headers["Cache-Control"] = STATS_CACHE_CONTROL
    return {
        "min_bucket": stats.MIN_BUCKET,
        "games": {g: list(f) for g, f in stats.STATS_FIELDS.items()},
    }


@router.get("/stats/games/{game_id}")
def stats_game(game_id: str, response: Response, db: Session = Depends(get_db)):
    _require_known_game(game_id)
    response.headers["Cache-Control"] = STATS_CACHE_CONTROL
    return stats.summarize_game(game_id, _game_saves(db, game_id))


@router.get("/stats/games/{game_id}/percentile")
def stats_game_percentile(
    game_id: str, field: str, value: float, response: Response, db: Session = Depends(get_db)
):
    _require_known_game(game_id)
    if field not in stats.STATS_FIELDS[game_id]:
        raise HTTPException(status_code=404, detail="Field is not enabled for stats")
    if value != value or value in (float("inf"), float("-inf")):
        raise HTTPException(status_code=422, detail="value must be a finite number")
    response.headers["Cache-Control"] = STATS_CACHE_CONTROL
    values = stats.field_values(_game_saves(db, game_id), field)
    if len(values) < stats.MIN_BUCKET:
        return {"game_id": game_id, "field": field, "suppressed": True, "min_bucket": stats.MIN_BUCKET, "count": None, "percentile": None}
    return {
        "game_id": game_id,
        "field": field,
        "suppressed": False,
        "min_bucket": stats.MIN_BUCKET,
        "count": len(values),
        "percentile": stats.percentile_of(values, value),
    }


@router.get("/stats/achievements")
def stats_achievements(response: Response, db: Session = Depends(get_db)):
    """Every game's achievement rarity in one call (the hub dashboard case)."""
    response.headers["Cache-Control"] = STATS_CACHE_CONTROL
    out = {}
    for game_id in stats.known_games():
        summary = stats.summarize_game(game_id, _game_saves(db, game_id))
        out[game_id] = {
            "suppressed": summary["suppressed"],
            "save_count": summary["save_count"],
            "achievements": summary["achievements"],
        }
    return {"min_bucket": stats.MIN_BUCKET, "games": out}
