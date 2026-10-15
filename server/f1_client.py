from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from server.cache import TTLCache

logger = logging.getLogger(__name__)

BASE_URL = "https://api.jolpi.ca/ergast/f1"
TIMEOUT = httpx.Timeout(15.0)

cache = TTLCache(maxsize=500)

_MAX_ATTEMPTS = 3

_client: httpx.AsyncClient | None = None
_inflight: dict[str, asyncio.Task[dict[str, Any]]] = {}


class _UpstreamTemporaryError(Exception):
    """Erreur amont transitoire (429, 5xx) — éligible au retry."""


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=TIMEOUT)
    return _client


async def close_client() -> None:
    """Ferme le client HTTP partagé (appelé au shutdown de l'app)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _now() -> datetime:
    return datetime.now(UTC)


def _current_year() -> int:
    return _now().year


def _weekend_ttl() -> int:
    return 3600 if _now().weekday() >= 4 else 86400


async def _sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


async def _fetch_upstream(url: str) -> dict[str, Any]:
    client = _get_client()
    for attempt in range(_MAX_ATTEMPTS):
        try:
            resp = await client.get(url)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise _UpstreamTemporaryError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            cache.set(url, data, ttl=_weekend_ttl())
            return data
        except (httpx.TransportError, _UpstreamTemporaryError) as e:
            if attempt == _MAX_ATTEMPTS - 1:
                logger.warning(
                    "Erreur API amont jolpica après %d tentatives : %s (%s)",
                    _MAX_ATTEMPTS,
                    e,
                    url,
                )
                raise
            delay = 2**attempt
            logger.info(
                "API amont instable — retry %d/%d dans %ds",
                attempt + 1,
                _MAX_ATTEMPTS - 1,
                delay,
            )
            await _sleep(delay)
    raise RuntimeError("inatteignable")


async def _fetch(path: str) -> dict[str, Any]:
    url = f"{BASE_URL}/{path}"
    cached = cache.get(url)
    if cached is not None:
        return cached
    # Déduplique les appels concurrents vers la même URL (anti cache-stampede)
    task = _inflight.get(url)
    if task is None:
        task = asyncio.create_task(_fetch_upstream(url))
        _inflight[url] = task
        task.add_done_callback(lambda _: _inflight.pop(url, None))
    return await asyncio.shield(task)


async def _fetch_mrdata(path: str) -> dict[str, Any]:
    data = await _fetch(path)
    return data.get("MRData", {})


def _to_int(val: str) -> int:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _short_name(given: str, family: str) -> str:
    if given:
        return f"{given[0]}. {family}"
    return family


# ── Calendar ──────────────────────────────────────────────────────────────────


async def get_calendar(year: int | None = None) -> list[dict[str, Any]]:
    year = year or _current_year()
    mrdata = await _fetch_mrdata(f"{year}.json?limit=30")
    races = (mrdata.get("RaceTable") or {}).get("Races", [])

    result = []
    for r in races:
        result.append(
            {
                "rnd": _to_int(r.get("round", 0)),
                "name": (r.get("raceName") or "").strip(),
                "date": (r.get("date") or "")[:10],
            }
        )
    return result


# ── Driver Standings ──────────────────────────────────────────────────────────


async def get_driver_standings(
    year: int | None = None, round_num: int | None = None
) -> list[dict[str, Any]]:
    year = year or _current_year()
    path = f"{year}/driverStandings.json?limit=40"
    if round_num:
        path = f"{year}/{round_num}/driverStandings.json?limit=40"

    mrdata = await _fetch_mrdata(path)
    standings = (
        (mrdata.get("StandingsTable") or {}).get("StandingsLists") or [{}]
    )[0].get("DriverStandings", [])

    result = []
    for s in standings:
        driver = s.get("Driver", {})
        result.append(
            {
                "pos": _to_int(s.get("position", 0)),
                "name": _short_name(
                    driver.get("givenName", ""), driver.get("familyName", "")
                ),
                "pts": _to_int(s.get("points", 0)),
            }
        )
    return result
