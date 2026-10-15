from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, HTTPException, Query

from server.f1_client import close_client, get_calendar, get_driver_standings
from server.rate_limit import RateLimitMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_UPSTREAM_ERROR = "Service F1 temporairement indisponible"

# Docs Swagger/OpenAPI désactivées par défaut en prod (opt-in via env)
_ENABLE_DOCS = os.getenv("F1_ENABLE_DOCS", "").lower() in ("1", "true", "yes")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_client()


app = FastAPI(
    title="F1 Stats API",
    description="Données F1 simplifiées pour ESP32 — une requête = une donnée",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs" if _ENABLE_DOCS else None,
    openapi_url="/openapi.json" if _ENABLE_DOCS else None,
    redoc_url=None,
)
app.add_middleware(RateLimitMiddleware, max_requests=30, window_seconds=60)


@app.get("/api/v1/calendar")
async def calendar(year: int | None = Query(None, ge=1950, le=2100)):
    """Calendrier complet de la saison (dates, circuits, sessions)."""
    try:
        return {"cal": await get_calendar(year)}
    except Exception:
        logger.exception("Erreur sur /api/v1/calendar")
        raise HTTPException(503, _UPSTREAM_ERROR)


@app.get("/api/v1/next")
async def next_weekend(year: int | None = Query(None, ge=1950, le=2100)):
    """Prochain GP au calendrier."""
    try:
        cal = await get_calendar(year)
        now = datetime.now(UTC)
        today = now.strftime("%Y-%m-%d")
        for r in cal:
            if r["date"] >= today:
                return {"next": r}
        # Hors saison : sans année explicite, basculer sur le 1er GP de N+1
        if year is None:
            try:
                next_cal = await get_calendar(now.year + 1)
            except httpx.HTTPError:
                logger.info("Calendrier N+1 indisponible — fallback saison courante")
                next_cal = []
            if next_cal:
                return {"next": next_cal[0]}
        return {"next": cal[-1] if cal else None}
    except Exception:
        logger.exception("Erreur sur /api/v1/next")
        raise HTTPException(503, _UPSTREAM_ERROR)


@app.get("/api/v1/standings")
async def driver_standings(
    year: int | None = Query(None, ge=1950, le=2100),
    round: int | None = Query(None, ge=1, le=30),
):
    """Classement pilotes (position, nom, points)."""
    try:
        return {"drv": await get_driver_standings(year, round)}
    except Exception:
        logger.exception("Erreur sur /api/v1/standings")
        raise HTTPException(503, _UPSTREAM_ERROR)


@app.get("/api/v1/health")
async def health():
    return {"ok": True, "ts": datetime.now(UTC).isoformat()}
