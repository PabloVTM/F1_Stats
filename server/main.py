from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException

from server.f1_client import (
    get_calendar,
    get_driver_standings,
)
from server.rate_limit import RateLimitMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(
    title="F1 Stats API",
    description="Données F1 simplifiées pour ESP32 — une requête = une donnée",
    version="1.0.0",
)
app.add_middleware(RateLimitMiddleware, max_requests=30, window_seconds=60)


@app.get("/api/v1/calendar")
async def calendar(year: int | None = None):
    """Calendrier complet de la saison (dates, circuits, sessions)."""
    try:
        return {"cal": await get_calendar(year)}
    except Exception as e:
        raise HTTPException(503, f"Erreur API F1: {e}")


@app.get("/api/v1/next")
async def next_weekend(year: int | None = None):
    """Prochain GP au calendrier."""
    try:
        cal = await get_calendar(year)
        now = datetime.now(UTC)
        today = now.strftime("%Y-%m-%d")
        for r in cal:
            if r["date"] >= today:
                return {"next": r}
        return {"next": cal[-1] if cal else None}
    except Exception as e:
        raise HTTPException(503, f"Erreur API F1: {e}")


@app.get("/api/v1/standings")
async def driver_standings(year: int | None = None, round: int | None = None):
    """Classement pilotes (position, nom, points)."""
    try:
        return {"drv": await get_driver_standings(year, round)}
    except Exception as e:
        raise HTTPException(503, f"Erreur API F1: {e}")


@app.get("/api/v1/health")
async def health():
    return {"ok": True, "ts": datetime.now(UTC).isoformat()}