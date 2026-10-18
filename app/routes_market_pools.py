"""Market prices, community pools and the page-view counter."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

import market
import pools
from database import get_db
from models import PageView, PoolDay
from rate_limits import _client_key, _throttle, PAGEVIEW_LIMITER


router = APIRouter()


@router.get("/market/prices")
def market_prices(response: Response):
    """Lowest online sell price (platinum) for the tracker's tradeable
    resources, cached for ten minutes (see market.py)."""
    response.headers["Cache-Control"] = "public, max-age=300"
    return {"prices": market.all_prices()}


# --- Shared community pools (see pools.py) ---


class PoolContribution(BaseModel):
    amount: float


def _pool_or_404(game_id: str, pool: str) -> dict:
    config = pools.pool_config(game_id, pool)
    if config is None:
        raise HTTPException(status_code=404, detail="Unknown pool")
    return config


def _pool_summary(db: Session, game_id: str, pool: str, config: dict) -> dict:
    rows = db.query(PoolDay).filter(PoolDay.game_id == game_id, PoolDay.pool == pool).all()
    today = pools.today_utc()
    total_all = sum(r.total for r in rows)
    best = max(rows, key=lambda r: r.total, default=None)
    today_row = next((r for r in rows if r.day == today), None)
    recent = sorted(rows, key=lambda r: r.day, reverse=True)[: pools.RECENT_DAYS]
    return {
        "game_id": game_id,
        "pool": pool,
        "label": config["label"],
        "today": {"day": today, "total": today_row.total if today_row else 0.0, "contributions": today_row.contributions if today_row else 0},
        "total": total_all,
        "best_day": {"day": best.day, "total": best.total} if best else None,
        "recent_days": [{"day": r.day, "total": r.total} for r in recent],
    }


@router.get("/pools/{game_id}/{pool}")
def get_pool(game_id: str, pool: str, response: Response, db: Session = Depends(get_db)):
    config = _pool_or_404(game_id, pool)
    response.headers["Cache-Control"] = "public, max-age=30"
    return _pool_summary(db, game_id, pool, config)


@router.post("/pools/{game_id}/{pool}")
def add_to_pool(game_id: str, pool: str, payload: PoolContribution, request: Request, response: Response, db: Session = Depends(get_db)):
    config = _pool_or_404(game_id, pool)
    response.headers["Cache-Control"] = "no-store"
    amount = pools.valid_amount(config, payload.amount)
    if amount is None:
        raise HTTPException(status_code=422, detail="amount is outside this pool's accepted range")
    client = _client_key(request)
    if pools.rate_limited(client):
        raise HTTPException(status_code=429, detail="Too many contributions, try again later")
    today = pools.today_utc()
    row = db.query(PoolDay).filter(PoolDay.game_id == game_id, PoolDay.pool == pool, PoolDay.day == today).first()
    if row is None:
        row = PoolDay(game_id=game_id, pool=pool, day=today, total=0.0, contributions=0)
        db.add(row)
    row.total = (row.total or 0.0) + amount
    row.contributions = (row.contributions or 0) + 1
    db.commit()
    return _pool_summary(db, game_id, pool, config)


@router.post("/stats/pageview")
def stats_pageview(request: Request, db: Session = Depends(get_db)):
    """Y29: records one opt-in hub visit and returns the running total.
    No identifying detail is stored -- a bare insert, then a count(*). The
    address is used only for the in-memory rate limit and never kept."""
    _throttle(PAGEVIEW_LIMITER, request)
    db.add(PageView())
    db.commit()
    total = db.query(PageView).count()
    return {"total": total}
